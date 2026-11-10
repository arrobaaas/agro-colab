"""Pasarela de pago simulada.

Imita el flujo de una pasarela real (validación de la tarjeta, autorización,
comprobante) sin mover dinero. Solo acepta las tarjetas de prueba de
TARJETAS_PRUEBA: así nadie ingresa una tarjeta real creyendo que funciona.

Del número de la tarjeta solo se guardan la marca y los últimos 4 dígitos;
el número completo y el CVV no se almacenan ni se registran en ningún log.
"""

import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from core import es_cuenta_demo, limitar
from database import Pago, Usuario
from errores import Conflicto, DatoInvalido, NoEncontrado, PagoRechazado, Prohibido
from repositories import arboles as repo_arboles, pagos as repo, transaccion
from schemas import PagoCanastaRequest, PagoRequest
from seguridad import registrar_evento
from services.pedidos import PLANES_ABASTECIMIENTO, PLANES_COMERCIALES
from services.suscripciones import exigir_que_pueda_adoptar, reservar_cupo

# número -> motivo de rechazo (None = aprobada)
TARJETAS_PRUEBA = {
    "4242424242424242": None,
    "5555555555554444": None,
    "4000000000000002": "Fondos insuficientes.",
    "4000000000009995": "Tarjeta bloqueada por el banco emisor.",
}

INTENTOS_POR_USUARIO = 10
VENTANA_INTENTOS = 600  # segundos


def luhn_valido(numero: str) -> bool:
    suma = 0
    for i, digito in enumerate(reversed(numero)):
        n = int(digito)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        suma += n
    return suma % 10 == 0


def marca_de(numero: str) -> str:
    if numero.startswith("4"):
        return "Visa"
    if numero[:2] in {"51", "52", "53", "54", "55"} or 2221 <= int(numero[:4]) <= 2720:
        return "Mastercard"
    if numero[:2] in {"34", "37"}:
        return "American Express"
    return "Tarjeta"


def vencida(vencimiento: str) -> bool:
    mes, anio = vencimiento.split("/")
    hoy = datetime.utcnow()
    return (2000 + int(anio), int(mes)) < (hoy.year, hoy.month)


def serializar(p: Pago) -> dict:
    return {
        "id": p.id,
        "tipo": p.tipo,
        "arbol_id": p.arbol_id,
        "plan_nombre": p.plan_nombre,
        "concepto": p.concepto,
        "monto_clp": p.monto_clp,
        "estado": p.estado,
        "motivo_rechazo": p.motivo_rechazo,
        "marca": p.marca,
        "ultimos4": p.ultimos4,
        "codigo_autorizacion": p.codigo_autorizacion,
        "transaccion": p.transaccion,
        "pedido_id": p.pedido_id,
        "fecha": p.fecha.strftime("%d/%m/%Y %H:%M") if p.fecha else None,
    }


def _exigir_comprador(usuario: Usuario):
    if usuario.rol != "comprador":
        registrar_evento("acceso_denegado", "advertencia", usuario=usuario, detalle="pagar sin ser comprador")
        raise Prohibido("Solo los compradores pueden pagar.")

    # Frena la prueba masiva de tarjetas desde una misma cuenta
    # La cuenta demo la comparten todos los visitantes
    limitar(f"pago:{usuario.id}", INTENTOS_POR_USUARIO * (10 if es_cuenta_demo(usuario) else 1), VENTANA_INTENTOS)


def _que_se_paga(db: Session, usuario: Usuario, tipo: str, arbol_id, plan_nombre):
    """Devuelve (árbol o None, concepto, monto). El monto lo fija el servidor,
    nunca el navegador."""
    if tipo == "arbol":
        arbol = repo_arboles.por_id(db, arbol_id)
        if not arbol:
            raise NoEncontrado("El árbol ya no está disponible.")
        # Antes de cobrar: si no puede adoptarlo, no se toca la tarjeta
        exigir_que_pueda_adoptar(db, usuario, arbol)
        return arbol, f"Adopción de {arbol.nombre} (primer mes)", arbol.precio_mensual_clp
    if plan_nombre not in PLANES_ABASTECIMIENTO:
        registrar_evento("plan_inexistente", "advertencia", usuario=usuario, detalle=f"pago de plan: {plan_nombre}")
        raise DatoInvalido("El plan elegido no existe.")
    # El plan B2B exige razón social y RUT, que la cuenta demo no admite: se
    # rechaza antes de cobrar, para no dejar un pago sin despacho posible
    if plan_nombre in PLANES_COMERCIALES and es_cuenta_demo(usuario):
        registrar_evento("cuenta_demo", "advertencia", usuario=usuario, detalle=f"pago de plan comercial: {plan_nombre}")
        raise Prohibido("La cuenta de demostración no puede contratar el plan comercial: exige razón social y RUT, "
                        "y esta cuenta la comparten todos los visitantes. Crea tu propia cuenta para probarlo.")
    return None, f"Plan {plan_nombre} (primer período)", PLANES_ABASTECIMIENTO[plan_nombre]


def _validar_tarjeta(datos) -> str:
    """Devuelve el número sin espacios, o lanza DatoInvalido."""
    numero = datos.numero.replace(" ", "")
    if not luhn_valido(numero):
        raise DatoInvalido("El número de la tarjeta no es válido. Revísalo.")
    if vencida(datos.vencimiento):
        raise DatoInvalido("La tarjeta está vencida.")
    if numero not in TARJETAS_PRUEBA:
        # No se registra nada: puede ser una tarjeta real ingresada por error
        raise DatoInvalido("Esta pasarela es de prueba y solo acepta las tarjetas de prueba indicadas en el formulario.")
    return numero


def _nuevo_pago(usuario: Usuario, tipo: str, arbol, plan_nombre, concepto: str, monto: int, numero: str, codigo_tx: str) -> Pago:
    return repo.nuevo(
        usuario_id=usuario.id,
        tipo=tipo,
        arbol_id=arbol.id if arbol else None,
        plan_nombre=plan_nombre if tipo == "plan" else None,
        concepto=concepto,
        monto_clp=monto,
        marca=marca_de(numero),
        ultimos4=numero[-4:],
        transaccion=codigo_tx,
    )


def pagar(db: Session, usuario: Usuario, datos: PagoRequest) -> dict:
    _exigir_comprador(usuario)

    # 1. Qué se paga
    arbol, concepto, monto = _que_se_paga(db, usuario, datos.tipo, datos.arbol_id, datos.plan_nombre)

    # 2. La tarjeta
    numero = _validar_tarjeta(datos)
    pago = _nuevo_pago(usuario, datos.tipo, arbol, datos.plan_nombre, concepto, monto, numero,
                       f"TX-{secrets.token_hex(6).upper()}")

    # 3. Autorización simulada
    motivo_rechazo = TARJETAS_PRUEBA[numero]
    if motivo_rechazo:
        pago.estado = "rechazado"
        pago.motivo_rechazo = motivo_rechazo
        transaccion.agregar(db, pago)
        transaccion.confirmar(db)
        transaccion.recargar(db, pago)
        registrar_evento("pago_rechazado", "advertencia", usuario=usuario, detalle=f"{pago.transaccion}: {motivo_rechazo}")
        raise PagoRechazado(motivo_rechazo, pago=serializar(pago))

    # 4. Aprobado: la adopción se confirma en la misma transacción que el
    #    pago. Si el último cupo se lo llevó otra compra, no se cobra.
    if arbol:
        try:
            reservar_cupo(db, usuario, arbol)
        except Conflicto as error:
            raise Conflicto(f"{error.mensaje} No se realizó ningún cobro.") from error

    pago.estado = "aprobado"
    pago.codigo_autorizacion = f"{secrets.randbelow(10**6):06d}"
    transaccion.agregar(db, pago)
    transaccion.confirmar(db)
    transaccion.recargar(db, pago)
    registrar_evento("pago_aprobado", "info", usuario=usuario, detalle=f"{pago.transaccion} por ${pago.monto_clp}")
    return {"status": "success", "mensaje": "Pago aprobado.", "pago": serializar(pago)}


def pagar_canasta(db: Session, usuario: Usuario, datos: PagoCanastaRequest) -> dict:
    """Cobra toda la canasta con una sola tarjeta y una sola transacción.

    Es todo o nada: si un árbol ya no se puede adoptar o se queda sin cupo,
    no se cobra ningún producto. Se guarda un pago por producto, porque cada
    pedido de abastecimiento se enlaza con el pago de su plan. Todos comparten
    la autorización y el código de transacción, con un sufijo por producto
    (TX-ABC123-1, TX-ABC123-2...) porque la columna es única.
    """
    _exigir_comprador(usuario)

    arboles_vistos = set()
    for item in datos.items:
        if item.tipo == "arbol":
            if item.arbol_id in arboles_vistos:
                raise DatoInvalido("Un mismo árbol aparece dos veces en la canasta.")
            arboles_vistos.add(item.arbol_id)

    # 1. Qué se paga: todo se revisa antes de tocar la tarjeta
    lineas = [
        (item, *_que_se_paga(db, usuario, item.tipo, item.arbol_id, item.plan_nombre))
        for item in datos.items
    ]

    # 2. La tarjeta
    numero = _validar_tarjeta(datos)
    codigo_tx = f"TX-{secrets.token_hex(6).upper()}"
    total = sum(monto for _, _, _, monto in lineas)

    # 3. Autorización simulada: un rechazo queda registrado en cada producto
    motivo_rechazo = TARJETAS_PRUEBA[numero]
    if motivo_rechazo:
        pagos = []
        for n, (item, arbol, concepto, monto) in enumerate(lineas, 1):
            pago = _nuevo_pago(usuario, item.tipo, arbol, item.plan_nombre, concepto, monto, numero, f"{codigo_tx}-{n}")
            pago.estado = "rechazado"
            pago.motivo_rechazo = motivo_rechazo
            pagos.append(transaccion.agregar(db, pago))
        transaccion.confirmar(db)
        registrar_evento("pago_rechazado", "advertencia", usuario=usuario, detalle=f"{codigo_tx} (canasta): {motivo_rechazo}")
        raise PagoRechazado(motivo_rechazo, pago=serializar(transaccion.recargar(db, pagos[0])))

    # 4. Aprobado: primero se reservan todos los cupos. Si uno falla, se
    #    deshace todo y no se cobra nada.
    for _, arbol, _, _ in lineas:
        if arbol:
            try:
                reservar_cupo(db, usuario, arbol)
            except Conflicto as error:
                transaccion.deshacer(db)
                raise Conflicto(f"{arbol.nombre}: {error.mensaje} No se realizó ningún cobro.") from error

    autorizacion = f"{secrets.randbelow(10**6):06d}"
    pagos = []
    for n, (item, arbol, concepto, monto) in enumerate(lineas, 1):
        pago = _nuevo_pago(usuario, item.tipo, arbol, item.plan_nombre, concepto, monto, numero, f"{codigo_tx}-{n}")
        pago.estado = "aprobado"
        pago.codigo_autorizacion = autorizacion
        pagos.append(transaccion.agregar(db, pago))
    transaccion.confirmar(db)
    for pago in pagos:
        transaccion.recargar(db, pago)
    registrar_evento("pago_aprobado", "info", usuario=usuario, detalle=f"{codigo_tx} canasta de {len(pagos)} por ${total}")

    return {
        "status": "success",
        "mensaje": "Pago aprobado.",
        "total_clp": total,
        "transaccion": codigo_tx,
        "codigo_autorizacion": autorizacion,
        "pagos": [serializar(p) for p in pagos],
    }


def listar(db: Session, usuario: Usuario) -> dict:
    return {"status": "success", "pagos": [serializar(p) for p in repo.de_usuario(db, usuario.id)]}


def obtener(db: Session, usuario: Usuario, pago_id: int) -> dict:
    pago = repo.de_usuario_por_id(db, usuario.id, pago_id)
    if not pago:
        if repo.existe(db, pago_id):
            registrar_evento("acceso_denegado", "advertencia", usuario=usuario, detalle=f"pago {pago_id} de otro usuario")
        raise NoEncontrado("Pago no encontrado.")
    return {"status": "success", "pago": serializar(pago)}
