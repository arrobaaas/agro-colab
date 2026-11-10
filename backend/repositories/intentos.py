"""Intentos del límite de peticiones. Viven en la base y no en memoria: así
sobreviven a un reinicio y valen para todos los procesos del servidor.

Usan el pool auxiliar (database.SessionAuxiliar): una petición que ya tiene una
conexión del pool principal siempre puede conseguir esta otra.
"""

import time

from sqlalchemy import func, select, text

from database import ES_SQLITE, IntentoAcceso, SessionAuxiliar

# Prefijos de las claves que incluyen un correo (ver services/cuentas.py)
PREFIJOS_CON_CORREO = ("login", "registro", "reenvio", "verificar", "recuperar", "restablecer")


def _contar(db, clave: str, ventana_segundos: int, ahora: float) -> int:
    return db.scalar(
        select(func.count()).select_from(IntentoAcceso).where(
            IntentoAcceso.clave == clave,
            IntentoAcceso.momento >= ahora - ventana_segundos,
        )
    )


def registrar_si_permitido(clave: str, maximo: int, ventana_segundos: int) -> bool:
    """Registra un intento y decide si se permite. La clave puede ser una IP o una cuenta."""
    ahora = time.time()
    db = SessionAuxiliar()
    try:
        # Sin este bloqueo, una ráfaga simultánea leería el mismo conteo y
        # superaría el máximo. Se libera solo al terminar la transacción.
        if not ES_SQLITE:
            db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:clave))"), {"clave": clave})
        # Limpieza: nada de lo que se limita usa ventanas de más de un día
        db.query(IntentoAcceso).filter(IntentoAcceso.momento < ahora - 86400).delete(synchronize_session=False)
        if _contar(db, clave, ventana_segundos, ahora) >= maximo:
            db.commit()
            return False
        db.add(IntentoAcceso(clave=clave, momento=ahora))
        db.commit()
        return True
    finally:
        db.close()


def permitido(clave: str, maximo: int, ventana_segundos: int) -> bool:
    """Solo consulta, sin contar este intento: lo usan los límites que únicamente
    suman los fallos."""
    db = SessionAuxiliar()
    try:
        return _contar(db, clave, ventana_segundos, time.time()) < maximo
    finally:
        db.close()


def registrar(clave: str):
    db = SessionAuxiliar()
    try:
        db.add(IntentoAcceso(clave=clave, momento=time.time()))
        db.commit()
    finally:
        db.close()


def borrar_de_correo(email: str):
    """Las claves incluyen el correo: se borran junto con la cuenta."""
    claves = [f"{prefijo}:{email.lower()}" for prefijo in PREFIJOS_CON_CORREO]
    db = SessionAuxiliar()
    try:
        db.query(IntentoAcceso).filter(IntentoAcceso.clave.in_(claves)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
