"""Consultas sobre pagos."""

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
