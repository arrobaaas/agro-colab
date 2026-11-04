"""Consultas sobre árboles."""

from sqlalchemy import func, update
from sqlalchemy.orm import Session, joinedload

from database import Arbol, Pedido, Suscripcion


def listar(db: Session):
    return db.query(Arbol).order_by(Arbol.id).all()


def contar(db: Session) -> int:
    return db.query(Arbol).count()


def por_id(db: Session, arbol_id: int):
    return db.query(Arbol).filter(Arbol.id == arbol_id).first()


def crear(db: Session, **campos) -> Arbol:
    arbol = Arbol(**campos)
    db.add(arbol)
    return arbol


def de_productor(db: Session, productor_id: int):
    return (
        db.query(Arbol)
        .options(joinedload(Arbol.productor))
        .filter(Arbol.productor_id == productor_id)
        .order_by(Arbol.id)
        .all()
    )


def adoptados_por(db: Session, usuario_id: int):
    return (
        db.query(Arbol)
        .join(Suscripcion, Suscripcion.arbol_id == Arbol.id)
        .filter(Suscripcion.usuario_id == usuario_id)
        .order_by(Arbol.id)
        .all()
    )


def publicados_por_usuario(db: Session) -> dict:
    """{productor_id: cantidad de árboles publicados}."""
    return dict(db.query(Arbol.productor_id, func.count()).group_by(Arbol.productor_id).all())


def reservar_cupo(db: Session, arbol_id: int) -> bool:
    """Reserva atómica: el UPDATE condicional bloquea la fila, así dos compras
    simultáneas no pueden quedarse con el último cupo a la vez. Antes se
    contaba y luego se insertaba, y ambas peticiones veían cupo libre."""
    filas = db.execute(
        update(Arbol)
        .where(Arbol.id == arbol_id, Arbol.cupos_ocupados < Arbol.cupos_totales)
        .values(cupos_ocupados=Arbol.cupos_ocupados + 1)
    ).rowcount
    return bool(filas)


def eliminar_con_dependencias(db: Session, arbol: Arbol):
    """Sin esto las suscripciones y sus despachos quedaban apuntando a un
    árbol inexistente."""
    db.query(Suscripcion).filter(Suscripcion.arbol_id == arbol.id).delete(synchronize_session=False)
    db.query(Pedido).filter(Pedido.arbol_id == arbol.id).delete(synchronize_session=False)
    db.delete(arbol)
