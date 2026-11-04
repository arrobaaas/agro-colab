"""Consultas del registro de eventos de seguridad. Cada función usa su propia
sesión: el registro no debe mezclarse con la transacción de la petición."""

from database import EventoSeguridad, SessionLocal


def guardar(limite_antiguedad=None, **campos):
    """Guarda un evento y, si se indica, borra los anteriores a esa fecha."""
    db = SessionLocal()
    try:
        db.add(EventoSeguridad(**campos))
        if limite_antiguedad is not None:
            db.query(EventoSeguridad).filter(
                EventoSeguridad.momento < limite_antiguedad
            ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def contar_recientes(tipo: str, agrupar_por: str, valor, desde) -> int:
    columna = EventoSeguridad.email if agrupar_por == "email" else EventoSeguridad.ip
    db = SessionLocal()
    try:
        return db.query(EventoSeguridad).filter(
            EventoSeguridad.tipo == tipo,
            columna == valor,
            EventoSeguridad.momento >= desde,
        ).count()
    finally:
        db.close()


def alerta_enviada_desde(clave: str, desde) -> bool:
    db = SessionLocal()
    try:
        return db.query(EventoSeguridad).filter(
            EventoSeguridad.tipo == "alerta_enviada",
            EventoSeguridad.detalle == clave,
            EventoSeguridad.momento >= desde,
        ).first() is not None
    finally:
        db.close()


def desde(fecha):
    db = SessionLocal()
    try:
        return db.query(EventoSeguridad).filter(EventoSeguridad.momento >= fecha).all()
    finally:
        db.close()


def ultimos(limite: int):
    db = SessionLocal()
    try:
        return db.query(EventoSeguridad).order_by(EventoSeguridad.id.desc()).limit(limite).all()
    finally:
        db.close()
