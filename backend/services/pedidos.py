"""Reglas de los pedidos: planes de abastecimiento y despachos de cosecha."""

from sqlalchemy.orm import Session

from core import es_cuenta_demo, limitar
from database import Pedido, Usuario
from errores import Conflicto, DatoInvalido, NoEncontrado, Prohibido
from repositories import (
    arboles as repo_arboles, pagos as repo_pagos, pedidos as repo,
    suscripciones as repo_suscripciones, transaccion,
)
from schemas import LogisticaRequest, PedidoRequest
from seguridad import registrar_evento

# Precio de cada plan de abastecimiento. Lo fija el servidor: antes el monto
# venía del navegador y se podía contratar el plan B2B por $1.
PLANES_ABASTECIMIENTO = {
    "Canasta Huerto Esencial": 19900,
    "Cosecha Completa Familiar": 34900,
    "Lote Gastronómico B2B": 89000,
}
# Se facturan a una empresa (ver terminos.html): exigen razón social y RUT
PLANES_COMERCIALES = {"Lote Gastronómico B2B"}

PEDIDOS_POR_HORA = 20


def serializar(p: Pedido) -> dict:
    return {
        "id": p.id,
        "tipo": p.tipo or "abastecimiento",
        "arbol_id": p.arbol_id,
        "plan_nombre": p.plan_nombre,
        "monto_clp": p.monto_clp,
        "tipo_destino": p.tipo_destino,
        "razon_social": p.razon_social,
        "rut": p.rut,
        "direccion": p.direccion,
        "comuna": p.comuna,
        "codigo_postal": p.codigo_postal,
        "telefono_codigo": p.telefono_codigo,
        "telefono": p.telefono,
        "frecuencia_entrega": p.frecuencia_entrega,
        "codigo_seguimiento": p.codigo_seguimiento,
        "fecha_registro": p.fecha_registro.strftime("%d/%m/%Y %H:%M") if p.fecha_registro else None,
        "estado_logistica": p.estado_logistica,
    }


def _validar_logistica(datos, plan_nombre: str, cliente: Usuario):
    """Los tipos y largos ya los valida el esquema (schemas.py)."""
    comercial = datos.tipo_destino == "comercial"
    if comercial and not (datos.razon_social and datos.rut):
        raise DatoInvalido("Completa la razón social y el RUT para el despacho comercial.")
    if plan_nombre in PLANES_COMERCIALES and not comercial:
        raise DatoInvalido("El plan comercial requiere un despacho comercial, con razón social y RUT.")
    if not datos.direccion.strip() or not datos.comuna.strip():
        raise DatoInvalido("Completa la dirección y la comuna de entrega.")
    if datos.telefono_codigo == "+56" and not (len(datos.telefono) == 9 and datos.telefono.startswith("9")):
        raise DatoInvalido("Un celular de Chile tiene 9 dígitos y empieza con 9.")
    # Todos los visitantes ven lo que queda en la cuenta demo: no debe recibir
    # el RUT de nadie
    if comercial and es_cuenta_demo(cliente):
        registrar_evento("cuenta_demo", "advertencia", usuario=cliente, detalle="despacho comercial")
        raise Prohibido("La cuenta de demostración no admite datos comerciales: la comparten todos los visitantes.")


def _propio(db: Session, cliente: Usuario, pedido_id: int) -> Pedido:
    """Un pedido ajeno responde igual que uno inexistente: no se revela que existe."""
    pedido = repo.por_id(db, pedido_id)
    if not pedido or pedido.cliente_id != cliente.id:
        if pedido:
            registrar_evento("acceso_denegado", "advertencia", usuario=cliente, detalle=f"pedido {pedido_id} de otro cliente")
        raise NoEncontrado("Pedido no encontrado.")
    return pedido


def registrar(db: Session, cliente: Usuario, datos: PedidoRequest) -> dict:
    if cliente.rol != "comprador":
        registrar_evento("acceso_denegado", "advertencia", usuario=cliente, detalle="contratar plan sin ser comprador")
        raise Prohibido("Solo los compradores pueden contratar planes.")

    # La cuenta demo la comparten todos los visitantes
    limitar(f"pedido:{cliente.id}", PEDIDOS_POR_HORA * (10 if es_cuenta_demo(cliente) else 1), 3600)

    pago = None
    if datos.tipo == "arbol":
        # El despacho de un árbol solo lo puede pedir quien lo tiene adoptado
        suscrito = repo_suscripciones.de_usuario_y_arbol(db, cliente.id, datos.arbol_id)
        arbol = repo_arboles.por_id(db, datos.arbol_id)
        if not suscrito or not arbol:
            registrar_evento("acceso_denegado", "advertencia", usuario=cliente, detalle=f"despacho del árbol {datos.arbol_id} sin adoptarlo")
            raise Prohibido("No tienes adoptado ese árbol.")
        if repo.despacho_de_arbol(db, cliente.id, arbol.id):
            raise Conflicto("Ese árbol ya tiene un despacho. Modifícalo en lugar de crear otro.")
        plan_nombre = f"Cosecha de {arbol.nombre}"
        monto = arbol.precio_mensual_clp
    else:
        if datos.plan_nombre not in PLANES_ABASTECIMIENTO:
            registrar_evento("plan_inexistente", "advertencia", usuario=cliente, detalle=f"plan pedido: {datos.plan_nombre}")
            raise DatoInvalido("El plan elegido no existe.")
        plan_nombre = datos.plan_nombre
        monto = PLANES_ABASTECIMIENTO[plan_nombre]

    _validar_logistica(datos, plan_nombre, cliente)

    if datos.tipo != "arbol":
        pago = repo_pagos.disponible_para_plan(db, datos.pago_id, cliente.id, plan_nombre) if datos.pago_id else None
        if not pago:
            registrar_evento("acceso_denegado", "advertencia", usuario=cliente, detalle=f"plan sin pago válido (pago {datos.pago_id})")
            raise Conflicto("Para contratar el plan primero debes pagarlo.")

    comercial = datos.tipo_destino == "comercial"
    # El cliente es el usuario de la sesión, no el id o correo del formulario
    pedido = repo.crear_con_id(
        db,
        cliente_id=cliente.id,
        tipo=datos.tipo,
        arbol_id=datos.arbol_id if datos.tipo == "arbol" else None,
        plan_nombre=plan_nombre,
        monto_clp=monto,
        tipo_destino=datos.tipo_destino,
        razon_social=datos.razon_social if comercial else None,
        rut=datos.rut if comercial else None,
        direccion=datos.direccion,
        comuna=datos.comuna,
        codigo_postal=datos.codigo_postal,
        telefono_codigo=datos.telefono_codigo,
        telefono=datos.telefono,
        frecuencia_entrega=datos.frecuencia_entrega,
        estado_logistica="En coordinación con huerto de origen",
    )
    # El código sale del id: con count() + 1 se repetía tras borrar pedidos
    # (la columna es única y el insert fallaba con un error 500).
    pedido.codigo_seguimiento = f"AGRO-{pedido.id:04d}"
    # Reclamo atómico: de dos peticiones simultáneas con el mismo pago, solo una
    # lo consigue, y la otra deshace su pedido
    if pago and not repo_pagos.reclamar(db, pago.id, pedido.id):
        transaccion.deshacer(db)
        raise Conflicto("Ese pago ya se usó en otro pedido.")
    transaccion.confirmar(db)
    transaccion.recargar(db, pedido)
    return {
        "status": "success",
        "mensaje": f"Pedido registrado. Código de despacho: {pedido.codigo_seguimiento}",
        "pedido": serializar(pedido),
    }


def listar(db: Session, cliente: Usuario) -> list:
    # Cada usuario ve solo sus pedidos (antes se listaban las direcciones de todos)
    return [serializar(p) for p in repo.de_cliente(db, cliente.id)]


def obtener(db: Session, cliente: Usuario, pedido_id: int) -> dict:
    return serializar(_propio(db, cliente, pedido_id))


def modificar_logistica(db: Session, cliente: Usuario, pedido_id: int, datos: LogisticaRequest) -> dict:
    """Cambia el destino y la frecuencia de un pedido propio."""
    pedido = _propio(db, cliente, pedido_id)
    _validar_logistica(datos, pedido.plan_nombre, cliente)

    pedido.tipo_destino = datos.tipo_destino
    pedido.razon_social = datos.razon_social if datos.tipo_destino == "comercial" else None
    pedido.rut = datos.rut if datos.tipo_destino == "comercial" else None
    pedido.direccion = datos.direccion
    pedido.comuna = datos.comuna
    pedido.codigo_postal = datos.codigo_postal
    pedido.telefono_codigo = datos.telefono_codigo
    pedido.telefono = datos.telefono
    pedido.frecuencia_entrega = datos.frecuencia_entrega
    transaccion.confirmar(db)
    transaccion.recargar(db, pedido)
    return {
        "status": "success",
        "mensaje": f"Logística actualizada para {pedido.codigo_seguimiento}.",
        "pedido": serializar(pedido),
    }


def cancelar_plan(db: Session, cliente: Usuario, pedido_id: int) -> dict:
    """El despacho de un árbol no se cancela aquí: se elimina junto con la
    suscripción al árbol."""
    pedido = _propio(db, cliente, pedido_id)
    if pedido.tipo == "arbol":
        raise Conflicto("Para dejar un árbol, cancela su suscripción.")

    nombre = pedido.plan_nombre
    transaccion.eliminar(db, pedido)
    transaccion.confirmar(db)
    return {"status": "success", "mensaje": f"Plan {nombre} cancelado."}
