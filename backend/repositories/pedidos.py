"""Consultas sobre pedidos."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import Pedido


def por_id(db: Session, pedido_id: int):
    return db.query(Pedido).filter(Pedido.id == pedido_id).first()


def de_cliente(db: Session, cliente_id: int):
    return db.query(Pedido).filter(Pedido.cliente_id == cliente_id).order_by(Pedido.id.desc()).all()


def contar_de_cliente(db: Session, cliente_id: int) -> int:
    return db.query(Pedido).filter(Pedido.cliente_id == cliente_id).count()


def por_cliente(db: Session) -> dict:
    """{cliente_id: cantidad de pedidos}."""
    return dict(db.query(Pedido.cliente_id, func.count()).group_by(Pedido.cliente_id).all())


def crear_con_id(db: Session, **campos) -> Pedido:
    pedido = Pedido(**campos)
    db.add(pedido)
    db.flush()
    return pedido


def despacho_de_arbol(db: Session, cliente_id: int, arbol_id: int):
    return db.query(Pedido).filter(
        Pedido.cliente_id == cliente_id,
        Pedido.arbol_id == arbol_id,
        Pedido.tipo == "arbol",
    ).first()


def borrar_despacho_de_arbol(db: Session, usuario_id: int, arbol_id: int):
    db.query(Pedido).filter(
        Pedido.cliente_id == usuario_id,
        Pedido.arbol_id == arbol_id,
        Pedido.tipo == "arbol",
    ).delete(synchronize_session=False)
