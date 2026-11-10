"""Consultas del registro de eventos de seguridad. Cada función usa su propia
sesión: el registro no debe mezclarse con la transacción de la petición. Usan el
pool auxiliar (database.SessionAuxiliar): una petición que ya tiene una conexión
del pool principal siempre puede conseguir esta otra."""

from sqlalchemy import func, or_

from database import EventoSeguridad, SessionAuxiliar


def guardar(limite_antiguedad=None, **campos):
    """Guarda un evento y, si se indica, borra los anteriores a esa fecha."""
    db = SessionAuxiliar()
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
    db = SessionAuxiliar()
    try:
        return db.query(EventoSeguridad).filter(
            EventoSeguridad.tipo == tipo,
            columna == valor,
            EventoSeguridad.momento >= desde,
        ).count()
    finally:
        db.close()


def alerta_enviada_desde(clave: str, desde) -> bool:
    db = SessionAuxiliar()
    try:
        return db.query(EventoSeguridad).filter(
            EventoSeguridad.tipo == "alerta_enviada",
            EventoSeguridad.detalle == clave,
            EventoSeguridad.momento >= desde,
        ).first() is not None
    finally:
        db.close()


def contar_alertas_desde(fecha) -> int:
    db = SessionAuxiliar()
    try:
        return db.query(EventoSeguridad).filter(
            EventoSeguridad.tipo == "alerta_enviada",
            EventoSeguridad.momento >= fecha,
        ).count()
    finally:
        db.close()


def anonimizar(email: str, usuario_id: int):
    """Quita a la persona de los eventos al eliminar su cuenta. Quedan la IP y la
    acción: sirven para detectar ataques durante el plazo de retención."""
    db = SessionAuxiliar()
    try:
        db.query(EventoSeguridad).filter(
            or_(func.lower(EventoSeguridad.email) == email.lower(), EventoSeguridad.usuario_id == usuario_id)
        ).update({"email": None, "usuario_id": None}, synchronize_session=False)
        db.commit()
    finally:
        db.close()


def desde(fecha):
    db = SessionAuxiliar()
    try:
        return db.query(EventoSeguridad).filter(EventoSeguridad.momento >= fecha).all()
    finally:
        db.close()


def ultimos(limite: int):
    db = SessionAuxiliar()
    try:
        return db.query(EventoSeguridad).order_by(EventoSeguridad.id.desc()).limit(limite).all()
    finally:
        db.close()
