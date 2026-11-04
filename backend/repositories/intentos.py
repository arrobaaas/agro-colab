"""Intentos del límite de peticiones. Viven en la base y no en memoria: así
sobreviven a un reinicio y valen para todos los procesos del servidor."""

import time

from database import IntentoAcceso, SessionLocal


def registrar_si_permitido(clave: str, maximo: int, ventana_segundos: int) -> bool:
    """Registra un intento y decide si se permite. La clave puede ser una IP o una cuenta."""
    ahora = time.time()
    db = SessionLocal()
    try:
        # Limpieza: nada de lo que se limita usa ventanas de más de un día
        db.query(IntentoAcceso).filter(IntentoAcceso.momento < ahora - 86400).delete(synchronize_session=False)
        recientes = db.query(IntentoAcceso).filter(
            IntentoAcceso.clave == clave,
            IntentoAcceso.momento >= ahora - ventana_segundos,
        ).count()
        if recientes >= maximo:
            db.commit()
            return False
        db.add(IntentoAcceso(clave=clave, momento=ahora))
        db.commit()
        return True
    finally:
        db.close()
