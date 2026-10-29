"""Router de logística y pedidos."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core import PedidoRequest, LogisticaRequest, get_db, usuario_actual
from database import Pedido, Suscripcion, Usuario

router = APIRouter()

TIPOS_PEDIDO = ("abastecimiento", "arbol")


def serializar_pedido(p: Pedido) -> dict:
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
        "frecuencia_entrega": p.frecuencia_entrega,
        "codigo_seguimiento": p.codigo_seguimiento,
        "fecha_registro": p.fecha_registro.strftime("%d/%m/%Y %H:%M") if p.fecha_registro else None,
        "estado_logistica": p.estado_logistica,
    }


def validar_logistica(datos) -> str:
    """Devuelve un mensaje de error, o cadena vacía si los datos son válidos."""
    if datos.tipo_destino not in ("particular", "comercial"):
        return "El tipo de destino debe ser particular o comercial."
    if datos.tipo_destino == "comercial" and not (datos.razon_social and datos.rut):
        return "Completa la razón social y el RUT para el despacho comercial."
    if not datos.direccion.strip() or not datos.comuna.strip():
        return "Completa la dirección y la comuna de entrega."
    return ""


@router.post("/api/pedidos")
def registrar_pedido(
    pedido: PedidoRequest,
    cliente: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    if pedido.tipo not in TIPOS_PEDIDO:
        return {"status": "error", "mensaje": "Tipo de pedido no válido."}

    error = validar_logistica(pedido)
    if error:
        return {"status": "error", "mensaje": error}

    # El despacho de un árbol solo lo puede pedir quien lo tiene adoptado
    if pedido.tipo == "arbol":
        suscrito = db.query(Suscripcion).filter(
            Suscripcion.arbol_id == pedido.arbol_id,
            Suscripcion.usuario_id == cliente.id,
        ).first()
        if not suscrito:
            return {"status": "error", "mensaje": "No tienes adoptado ese árbol."}

    # El cliente es el usuario de la sesión, no el id o correo del formulario
    nuevo_pedido = Pedido(
        cliente_id=cliente.id,
        tipo=pedido.tipo,
        arbol_id=pedido.arbol_id if pedido.tipo == "arbol" else None,
        plan_nombre=pedido.plan_nombre,
        monto_clp=pedido.monto_clp,
        tipo_destino=pedido.tipo_destino,
        razon_social=pedido.razon_social,
        rut=pedido.rut,
        direccion=pedido.direccion,
        comuna=pedido.comuna,
        frecuencia_entrega=pedido.frecuencia_entrega,
        estado_logistica="En coordinación con huerto de origen"
    )
    db.add(nuevo_pedido)
    db.flush()
    # El código sale del id: con count() + 1 se repetía tras borrar pedidos
    # (la columna es única y el insert fallaba con un error 500).
    nuevo_pedido.codigo_seguimiento = f"AGRO-{nuevo_pedido.id:04d}"
    db.commit()
    db.refresh(nuevo_pedido)

    return {
        "status": "success",
        "mensaje": f"Pedido registrado. Código de despacho: {nuevo_pedido.codigo_seguimiento}",
        "pedido": serializar_pedido(nuevo_pedido)
    }


@router.get("/api/pedidos")
def listar_pedidos(
    cliente: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    # Cada usuario ve solo sus pedidos (antes se listaban las direcciones de todos)
    pedidos = (
        db.query(Pedido)
        .filter(Pedido.cliente_id == cliente.id)
        .order_by(Pedido.id.desc())
        .all()
    )
    return [serializar_pedido(p) for p in pedidos]


@router.put("/api/pedidos/{pedido_id}")
def modificar_logistica(
    pedido_id: int,
    datos: LogisticaRequest,
    cliente: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """Cambia el destino y la frecuencia de un pedido propio."""
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido or pedido.cliente_id != cliente.id:
        return {"status": "error", "mensaje": "Pedido no encontrado."}

    error = validar_logistica(datos)
    if error:
        return {"status": "error", "mensaje": error}

    pedido.tipo_destino = datos.tipo_destino
    pedido.razon_social = datos.razon_social if datos.tipo_destino == "comercial" else None
    pedido.rut = datos.rut if datos.tipo_destino == "comercial" else None
    pedido.direccion = datos.direccion
    pedido.comuna = datos.comuna
    pedido.frecuencia_entrega = datos.frecuencia_entrega
    db.commit()
    db.refresh(pedido)

    return {
        "status": "success",
        "mensaje": f"Logística actualizada para {pedido.codigo_seguimiento}.",
        "pedido": serializar_pedido(pedido)
    }


@router.delete("/api/pedidos/{pedido_id}")
def cancelar_plan(
    pedido_id: int,
    cliente: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """Cancela un plan de abastecimiento propio.

    El despacho de un árbol no se cancela aquí: se elimina junto con la
    suscripción al árbol.
    """
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido or pedido.cliente_id != cliente.id:
        return {"status": "error", "mensaje": "Pedido no encontrado."}
    if pedido.tipo == "arbol":
        return {"status": "error", "mensaje": "Para dejar un árbol, cancela su suscripción."}

    nombre = pedido.plan_nombre
    db.delete(pedido)
    db.commit()
    return {"status": "success", "mensaje": f"Plan {nombre} cancelado."}
