"""Router de la pasarela de pago simulada.

Imita el flujo de una pasarela real (validación de la tarjeta, autorización,
comprobante) sin mover dinero. Solo acepta las tarjetas de prueba de
TARJETAS_PRUEBA: así nadie ingresa una tarjeta real creyendo que funciona.

Del número de la tarjeta solo se guardan la marca y los últimos 4 dígitos;
el número completo y el CVV no se almacenan ni se registran en ningún log.
"""

import secrets
from datetime import datetime
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, StringConstraints
from sqlalchemy.orm import Session

from core import Texto, get_db, limitar, usuario_actual
from database import Arbol, Pago, Usuario
from routers.pedidos import PLANES_ABASTECIMIENTO
from routers.suscripciones import puede_adoptar, reservar_cupo
from seguridad import registrar_evento

router = APIRouter()

# número -> motivo de rechazo (None = aprobada)
TARJETAS_PRUEBA = {
    "4242424242424242": None,
    "5555555555554444": None,
    "4000000000000002": "Fondos insuficientes.",
    "4000000000009995": "Tarjeta bloqueada por el banco emisor.",
}

INTENTOS_POR_USUARIO = 10
VENTANA_INTENTOS = 600  # segundos

NumeroTarjeta = Annotated[str, StringConstraints(strip_whitespace=True, min_length=12, max_length=23, pattern=r"^[\d ]+$")]
Vencimiento = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^(0[1-9]|1[0-2])/\d{2}$")]
Cvv = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{3,4}$")]


class PagoRequest(BaseModel):
    tipo: Literal["arbol", "plan"]
    arbol_id: Optional[int] = None
    plan_nombre: Optional[Texto(120)] = None
    numero: NumeroTarjeta
    titular: Texto(80)
    vencimiento: Vencimiento
    cvv: Cvv


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


def serializar_pago(p: Pago) -> dict:
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


def error(mensaje: str) -> dict:
    return {"status": "error", "mensaje": mensaje}


@router.post("/api/pagos")
def pagar(
    datos: PagoRequest,
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    if usuario.rol != "comprador":
        registrar_evento("acceso_denegado", "advertencia", usuario=usuario, detalle="pagar sin ser comprador")
        return error("Solo los compradores pueden pagar.")

    # Frena la prueba masiva de tarjetas desde una misma cuenta
    limitar(f"pago:{usuario.id}", INTENTOS_POR_USUARIO, VENTANA_INTENTOS)

    # 1. Qué se paga: el monto lo fija el servidor, nunca el navegador
    arbol = None
    if datos.tipo == "arbol":
        arbol = db.query(Arbol).filter(Arbol.id == datos.arbol_id).first()
        if not arbol:
            return error("El árbol ya no está disponible.")
        # Antes de cobrar: si no puede adoptarlo, no se toca la tarjeta
        motivo = puede_adoptar(db, usuario, arbol)
        if motivo:
            return error(motivo)
        concepto, monto = f"Adopción de {arbol.nombre} (primer mes)", arbol.precio_mensual_clp
    else:
        if datos.plan_nombre not in PLANES_ABASTECIMIENTO:
            registrar_evento("plan_inexistente", "advertencia", usuario=usuario, detalle=f"pago de plan: {datos.plan_nombre}")
            return error("El plan elegido no existe.")
        concepto, monto = f"Plan {datos.plan_nombre} (primer período)", PLANES_ABASTECIMIENTO[datos.plan_nombre]

    # 2. La tarjeta
    numero = datos.numero.replace(" ", "")
    if not luhn_valido(numero):
        return error("El número de la tarjeta no es válido. Revísalo.")
    if vencida(datos.vencimiento):
        return error("La tarjeta está vencida.")
    if numero not in TARJETAS_PRUEBA:
        # No se registra nada: puede ser una tarjeta real ingresada por error
        return error("Esta pasarela es de prueba y solo acepta las tarjetas de prueba indicadas en el formulario.")

    pago = Pago(
        usuario_id=usuario.id,
        tipo=datos.tipo,
        arbol_id=arbol.id if arbol else None,
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
        db.add(pago)
        db.commit()
        db.refresh(pago)
        registrar_evento("pago_rechazado", "advertencia", usuario=usuario, detalle=f"{pago.transaccion}: {motivo_rechazo}")
        return {"status": "rechazado", "mensaje": motivo_rechazo, "pago": serializar_pago(pago)}

    # 4. Aprobado: la adopción se confirma en la misma transacción que el
    #    pago. Si el último cupo se lo llevó otra compra, no se cobra.
    if arbol:
        motivo = reservar_cupo(db, usuario, arbol)
        if motivo:
            return error(f"{motivo} No se realizó ningún cobro.")

    pago.estado = "aprobado"
    pago.codigo_autorizacion = f"{secrets.randbelow(10**6):06d}"
    db.add(pago)
    db.commit()
    db.refresh(pago)
    registrar_evento("pago_aprobado", "info", usuario=usuario, detalle=f"{pago.transaccion} por ${pago.monto_clp}")

    return {"status": "success", "mensaje": "Pago aprobado.", "pago": serializar_pago(pago)}


@router.get("/api/pagos")
def mis_pagos(usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    pagos = db.query(Pago).filter(Pago.usuario_id == usuario.id).order_by(Pago.id.desc()).limit(50).all()
    return {"status": "success", "pagos": [serializar_pago(p) for p in pagos]}
