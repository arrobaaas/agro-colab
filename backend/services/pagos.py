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

from core import limitar
from database import Pago, Usuario
from errores import Conflicto, DatoInvalido, NoEncontrado, PagoRechazado, Prohibido
from repositories import arboles as repo_arboles, pagos as repo, transaccion
from schemas import PagoRequest
from seguridad import registrar_evento
from services.pedidos import PLANES_ABASTECIMIENTO
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


def pagar(db: Session, usuario: Usuario, datos: PagoRequest) -> dict:
    if usuario.rol != "comprador":
        registrar_evento("acceso_denegado", "advertencia", usuario=usuario, detalle="pagar sin ser comprador")
        raise Prohibido("Solo los compradores pueden pagar.")

    # Frena la prueba masiva de tarjetas desde una misma cuenta
    limitar(f"pago:{usuario.id}", INTENTOS_POR_USUARIO, VENTANA_INTENTOS)

    # 1. Qué se paga: el monto lo fija el servidor, nunca el navegador
    arbol = None
    if datos.tipo == "arbol":
        arbol = repo_arboles.por_id(db, datos.arbol_id)
        if not arbol:
            raise NoEncontrado("El árbol ya no está disponible.")
        # Antes de cobrar: si no puede adoptarlo, no se toca la tarjeta
        exigir_que_pueda_adoptar(db, usuario, arbol)
        concepto, monto = f"Adopción de {arbol.nombre} (primer mes)", arbol.precio_mensual_clp
    else:
        if datos.plan_nombre not in PLANES_ABASTECIMIENTO:
            registrar_evento("plan_inexistente", "advertencia", usuario=usuario, detalle=f"pago de plan: {datos.plan_nombre}")
            raise DatoInvalido("El plan elegido no existe.")
        concepto, monto = f"Plan {datos.plan_nombre} (primer período)", PLANES_ABASTECIMIENTO[datos.plan_nombre]

    # 2. La tarjeta
    numero = datos.numero.replace(" ", "")
    if not luhn_valido(numero):
        raise DatoInvalido("El número de la tarjeta no es válido. Revísalo.")
    if vencida(datos.vencimiento):
        raise DatoInvalido("La tarjeta está vencida.")
    if numero not in TARJETAS_PRUEBA:
        # No se registra nada: puede ser una tarjeta real ingresada por error
        raise DatoInvalido("Esta pasarela es de prueba y solo acepta las tarjetas de prueba indicadas en el formulario.")

    arbol_id = arbol.id if arbol else None
    pago = repo.nuevo(
        usuario_id=usuario.id,
        tipo=datos.tipo,
        arbol_id=arbol_id,
        plan_nombre=datos.plan_nombre if datos.tipo == "plan" else None,
        concepto=concepto,
        monto_clp=monto,
        marca=marca_de(numero),
        ultimos4=numero[-4:],
        transaccion=f"TX-{secrets.token_hex(6).upper()}",
    )

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


def listar(db: Session, usuario: Usuario) -> dict:
    return {"status": "success", "pagos": [serializar(p) for p in repo.de_usuario(db, usuario.id)]}


def obtener(db: Session, usuario: Usuario, pago_id: int) -> dict:
    pago = repo.de_usuario_por_id(db, usuario.id, pago_id)
    if not pago:
        raise NoEncontrado("Pago no encontrado.")
    return {"status": "success", "pago": serializar(pago)}
