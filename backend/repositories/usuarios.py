"""Consultas sobre usuarios."""

from datetime import datetime, timedelta

from sqlalchemy import exists, func, or_
from sqlalchemy.orm import Session

from database import Arbol, Pago, Pedido, Suscripcion, Usuario


def por_id(db: Session, usuario_id: int):
    return db.query(Usuario).filter(Usuario.id == usuario_id).first()


def _por_correo(db: Session, email: str):
    """Sin distinguir mayúsculas: el teclado del celular suele escribir la
    primera letra en mayúscula. Si hubiera cuentas antiguas que solo difieren
    en eso, primero va la coincidencia exacta."""
    return db.query(Usuario).filter(
        func.lower(Usuario.email) == email.lower()
    ).order_by((Usuario.email == email).desc())


def por_correo(db: Session, email: str):
    return _por_correo(db, email).first()


def por_correo_y_roles(db: Session, email: str, roles):
    return _por_correo(db, email).filter(or_(*[Usuario.rol == rol for rol in roles])).first()


def por_correo_exacto(db: Session, email: str):
    return db.query(Usuario).filter(Usuario.email == email).first()


def correo_en_otra_cuenta(db: Session, email: str, usuario_id: int):
    return db.query(Usuario).filter(func.lower(Usuario.email) == email.lower(), Usuario.id != usuario_id).first()


def listar(db: Session):
    return db.query(Usuario).order_by(Usuario.id).all()


def contar(db: Session) -> int:
    return db.query(Usuario).count()


def crear(db: Session, **campos) -> Usuario:
    usuario = Usuario(**campos)
    db.add(usuario)
    return usuario


def purgar_sin_verificar(db: Session, antes_de: datetime) -> int:
    """Borra las cuentas que nunca se verificaron y cuyo código ya venció. Solo las
    que no tienen actividad: un administrador puede dejar sin verificar una cuenta
    en uso, y esa no se toca."""
    return db.query(Usuario).filter(
        Usuario.verificado == 0,
        Usuario.codigo_expira < antes_de,
        ~exists().where(Suscripcion.usuario_id == Usuario.id),
        ~exists().where(Pedido.cliente_id == Usuario.id),
        ~exists().where(Pago.usuario_id == Usuario.id),
        ~exists().where(Arbol.productor_id == Usuario.id),
    ).delete(synchronize_session=False)


def limpiar_recuperaciones_vencidas(db: Session, ahora: datetime):
    db.query(Usuario).filter(Usuario.recuperacion_expira < ahora).update(
        {"recuperacion_hash": None, "recuperacion_expira": None, "recuperacion_intentos": 0},
        synchronize_session=False,
    )


def limpiar_cuenta_demo(db: Session, usuario_id: int, antiguedad: timedelta = timedelta(hours=1)):
    """La cuenta demo la comparten todos los visitantes: lo que alguien escribió en
    ella no se conserva, y sus adopciones no dejan el catálogo demo lleno."""
    limite = datetime.utcnow() - antiguedad
    db.query(Pedido).filter(Pedido.cliente_id == usuario_id, Pedido.fecha_registro < limite).delete(synchronize_session=False)
    db.query(Pago).filter(Pago.usuario_id == usuario_id, Pago.fecha < limite).delete(synchronize_session=False)
    viejas = db.query(Suscripcion).filter(Suscripcion.usuario_id == usuario_id, Suscripcion.fecha_suscripcion < limite)
    for arbol_id in [s.arbol_id for s in viejas]:
        db.query(Arbol).filter(Arbol.id == arbol_id, Arbol.cupos_ocupados > 0).update(
            {"cupos_ocupados": Arbol.cupos_ocupados - 1}, synchronize_session=False
        )
    viejas.delete(synchronize_session=False)


def borrar_con_sus_datos(db: Session, usuario: Usuario):
    """Borra la cuenta y todos sus datos, sin confirmar la transacción.

    El orden respeta las claves foráneas. Los despachos de OTROS clientes
    sobre los árboles de esta cuenta también se borran: sin eso, PostgreSQL
    rechaza eliminar el árbol (SQLite no lo detecta).
    """
    ids_arboles = [fila.id for fila in db.query(Arbol.id).filter(Arbol.productor_id == usuario.id)]

    db.query(Suscripcion).filter(Suscripcion.usuario_id == usuario.id).delete(synchronize_session=False)
    if ids_arboles:
        db.query(Suscripcion).filter(Suscripcion.arbol_id.in_(ids_arboles)).delete(synchronize_session=False)
        db.query(Pedido).filter(Pedido.arbol_id.in_(ids_arboles)).delete(synchronize_session=False)
    db.query(Pedido).filter(Pedido.cliente_id == usuario.id).delete(synchronize_session=False)
    db.query(Pago).filter(Pago.usuario_id == usuario.id).delete(synchronize_session=False)
    db.query(Arbol).filter(Arbol.productor_id == usuario.id).delete(synchronize_session=False)
    db.delete(usuario)
