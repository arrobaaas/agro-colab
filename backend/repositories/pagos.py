"""Consultas sobre pagos."""

from sqlalchemy import update
from sqlalchemy.orm import Session

from database import Pago


def nuevo(**campos) -> Pago:
    """Crea el comprobante sin agregarlo a la sesión: si el cupo se agota antes
    de aprobar, no queda rastro de un cobro."""
    return Pago(**campos)


def de_usuario(db: Session, usuario_id: int, limite: int = 50):
    return db.query(Pago).filter(Pago.usuario_id == usuario_id).order_by(Pago.id.desc()).limit(limite).all()


def de_usuario_por_id(db: Session, usuario_id: int, pago_id: int):
    return db.query(Pago).filter(Pago.id == pago_id, Pago.usuario_id == usuario_id).first()


def existe(db: Session, pago_id: int) -> bool:
    return db.query(Pago.id).filter(Pago.id == pago_id).first() is not None


def reclamar(db: Session, pago_id: int, pedido_id: int) -> bool:
    """Asigna el pago a un pedido solo si sigue libre. Es atómico: de dos peticiones
    simultáneas con el mismo pago, una sola lo consigue."""
    return bool(db.execute(
        update(Pago)
        .where(Pago.id == pago_id, Pago.pedido_id.is_(None))
        .values(pedido_id=pedido_id)
        .execution_options(synchronize_session=False)
    ).rowcount)


def disponible_para_plan(db: Session, pago_id: int, usuario_id: int, plan_nombre: str):
    """Pago aprobado, propio, de ese mismo plan y que no se haya usado en otro pedido."""
    return db.query(Pago).filter(
        Pago.id == pago_id,
        Pago.usuario_id == usuario_id,
        Pago.tipo == "plan",
        Pago.estado == "aprobado",
        Pago.plan_nombre == plan_nombre,
        Pago.pedido_id.is_(None),
    ).first()
