"""Operaciones de sesión que usa la capa de negocio para delimitar transacciones."""

from sqlalchemy.orm import Session

from database import SessionLocal


def abrir_sesion() -> Session:
    """Para lo que corre fuera de una petición, como los datos iniciales."""
    return SessionLocal()


def agregar(db: Session, objeto):
    db.add(objeto)
    return objeto


def eliminar(db: Session, objeto):
    db.delete(objeto)


def enviar(db: Session):
    db.flush()


def confirmar(db: Session):
    db.commit()


def deshacer(db: Session):
    db.rollback()


def recargar(db: Session, objeto):
    db.refresh(objeto)
    return objeto
