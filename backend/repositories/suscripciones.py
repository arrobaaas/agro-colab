"""Consultas sobre suscripciones."""

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from database import Arbol, Suscripcion


def por_id(db: Session, suscripcion_id: int):
    return db.query(Suscripcion).filter(Suscripcion.id == suscripcion_id).first()


def de_usuario_y_arbol(db: Session, usuario_id: int, arbol_id: int):
    return db.query(Suscripcion).filter(
        Suscripcion.arbol_id == arbol_id,
        Suscripcion.usuario_id == usuario_id,
    ).first()


def contar_de_arbol(db: Session, arbol_id: int) -> int:
    return db.query(Suscripcion).filter(Suscripcion.arbol_id == arbol_id).count()


def de_arbol_con_usuario(db: Session, arbol_id: int):
    return (
        db.query(Suscripcion)
        .options(joinedload(Suscripcion.usuario))
        .filter(Suscripcion.arbol_id == arbol_id)
        .all()
    )


def de_usuario_con_arbol(db: Session, usuario_id: int):
    return (
        db.query(Suscripcion)
        .options(joinedload(Suscripcion.arbol).joinedload(Arbol.productor))
        .filter(Suscripcion.usuario_id == usuario_id)
        .all()
    )


def adopciones_por_usuario(db: Session) -> dict:
    """{usuario_id: cantidad de árboles adoptados}."""
    return dict(db.query(Suscripcion.usuario_id, func.count()).group_by(Suscripcion.usuario_id).all())


def existe_entre(db: Session, usuario_id: int, productor_id: int) -> bool:
    """True si el usuario adoptó algún árbol de ese productor."""
    return (
        db.query(Suscripcion)
        .join(Arbol, Suscripcion.arbol_id == Arbol.id)
        .filter(Suscripcion.usuario_id == usuario_id, Arbol.productor_id == productor_id)
        .first()
    ) is not None


def contar_por_arbol(db: Session, ids_arboles: list) -> dict:
    """{arbol_id: suscripciones}, en una sola consulta para todo el catálogo."""
    return dict(
        db.query(Suscripcion.arbol_id, func.count())
        .filter(Suscripcion.arbol_id.in_(ids_arboles))
        .group_by(Suscripcion.arbol_id)
        .all()
    )


def contar_de_productor(db: Session, productor_id: int) -> int:
    return (
        db.query(Suscripcion)
        .join(Arbol, Suscripcion.arbol_id == Arbol.id)
        .filter(Arbol.productor_id == productor_id)
        .count()
    )


def de_productor_con_usuario(db: Session, productor_id: int):
    """Suscripciones a los árboles de un productor, para avisarles si los pierden."""
    return (
        db.query(Suscripcion)
        .options(joinedload(Suscripcion.usuario), joinedload(Suscripcion.arbol))
        .join(Arbol, Suscripcion.arbol_id == Arbol.id)
        .filter(Arbol.productor_id == productor_id)
        .all()
    )


def borrar(db: Session, suscripcion_id: int) -> bool:
    """True si este DELETE fue el que borró la fila."""
    return bool(db.query(Suscripcion).filter(Suscripcion.id == suscripcion_id).delete(synchronize_session=False))


def crear_sin_confirmar(db: Session, usuario_id: int, arbol_id: int) -> bool:
    """Agrega la suscripción. Devuelve False si el índice único la rechaza
    porque otra petición del mismo usuario se adelantó."""
    try:
        db.add(Suscripcion(usuario_id=usuario_id, arbol_id=arbol_id))
        db.flush()
        return True
    except IntegrityError:
        db.rollback()
        return False
