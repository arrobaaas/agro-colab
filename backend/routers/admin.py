"""Router del panel de administración: ver, editar y eliminar cuentas.

Todas las rutas exigen una sesión de administrador (core.usuario_admin).
El administrador no puede tocar otras cuentas de administrador ni las cuentas
demo, y cada cambio queda en el registro de seguridad.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from core import (
    AdminUsuarioRequest, get_db, usuario_admin, es_admin, es_cuenta_demo, hash_password,
    serializar_arbol, enviar_aviso_cambio_contrasena, MODO_DESARROLLO,
)
from database import Usuario, Arbol, Suscripcion, Pedido
from routers.usuarios import borrar_cuenta
from seguridad import registrar_evento

router = APIRouter()


def _conteo(db: Session, columna):
    """{usuario_id: cantidad} de filas agrupadas por la columna indicada."""
    return dict(db.query(columna, func.count()).group_by(columna).all())


def _resumen(usuario: Usuario, arboles: dict, adopciones: dict, pedidos: dict) -> dict:
    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol,
        "telefono": usuario.telefono,
        "direccion": usuario.direccion,
        "verificado": bool(usuario.verificado),
        "fecha_registro": usuario.fecha_consentimiento.isoformat() if usuario.fecha_consentimiento else None,
        "arboles_publicados": arboles.get(usuario.id, 0),
        "adopciones": adopciones.get(usuario.id, 0),
        "pedidos": pedidos.get(usuario.id, 0),
        # El panel no ofrece editar ni eliminar estas cuentas
        "protegida": es_admin(usuario) or es_cuenta_demo(usuario),
    }


def _buscar(db: Session, usuario_id: int):
    return db.query(Usuario).filter(Usuario.id == usuario_id).first()


def _motivo_protegida(usuario: Usuario):
    if es_admin(usuario):
        return "Las cuentas de administrador no se modifican desde el panel. Usa tu perfil."
    if es_cuenta_demo(usuario):
        return "Las cuentas de demostración no se modifican: sus credenciales son públicas."
    return None


@router.get("/api/admin/usuarios")
def listar_usuarios(admin: Usuario = Depends(usuario_admin), db: Session = Depends(get_db)):
    arboles = _conteo(db, Arbol.productor_id)
    adopciones = _conteo(db, Suscripcion.usuario_id)
    pedidos = _conteo(db, Pedido.cliente_id)
    usuarios = db.query(Usuario).order_by(Usuario.id).all()
    return {"status": "success", "usuarios": [_resumen(u, arboles, adopciones, pedidos) for u in usuarios]}


@router.get("/api/admin/usuarios/{usuario_id}")
def detalle_usuario(usuario_id: int, admin: Usuario = Depends(usuario_admin), db: Session = Depends(get_db)):
    usuario = _buscar(db, usuario_id)
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}

    arboles = db.query(Arbol).filter(Arbol.productor_id == usuario.id).order_by(Arbol.id).all()
    adoptados = (
        db.query(Arbol)
        .join(Suscripcion, Suscripcion.arbol_id == Arbol.id)
        .filter(Suscripcion.usuario_id == usuario.id)
        .order_by(Arbol.id)
        .all()
    )
    resumen = _resumen(
        usuario,
        {usuario.id: len(arboles)},
        {usuario.id: len(adoptados)},
        {usuario.id: db.query(Pedido).filter(Pedido.cliente_id == usuario.id).count()},
    )
    return {
        "status": "success",
        "usuario": resumen,
        "arboles": [serializar_arbol(a, db) for a in arboles],
        "adoptados": [serializar_arbol(a, db) for a in adoptados],
    }


@router.put("/api/admin/usuarios/{usuario_id}")
def editar_usuario(
    usuario_id: int,
    data: AdminUsuarioRequest,
    admin: Usuario = Depends(usuario_admin),
    db: Session = Depends(get_db),
):
    usuario = _buscar(db, usuario_id)
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}
    motivo = _motivo_protegida(usuario)
    if motivo:
        return {"status": "error", "mensaje": motivo}

    email = data.email
    repetido = db.query(Usuario).filter(func.lower(Usuario.email) == email.lower(), Usuario.id != usuario.id).first()
    if repetido:
        return {"status": "error", "mensaje": "Ese correo ya pertenece a otra cuenta."}

    cambios = [campo for campo, valor in (
        ("nombre", data.nombre != usuario.nombre),
        ("email", email != usuario.email),
        ("telefono", (data.telefono or None) != usuario.telefono),
        ("direccion", (data.direccion or None) != usuario.direccion),
        ("verificado", data.verificado != bool(usuario.verificado)),
        ("contraseña", bool(data.password)),
    ) if valor]

    usuario.nombre = data.nombre
    usuario.email = email
    usuario.telefono = data.telefono or None
    usuario.direccion = data.direccion or None
    usuario.verificado = 1 if data.verificado else 0
    if data.verificado:
        usuario.codigo_verificacion = None
        usuario.codigo_expira = None
    if data.password:
        # El token depende del hash de la contraseña: sus sesiones se cierran
        usuario.password = hash_password(data.password)
        usuario.recuperacion_hash = None
        usuario.recuperacion_expira = None
    db.commit()

    registrar_evento(
        "admin_edicion", "info", usuario=admin,
        detalle=f"cuenta {usuario.id} ({usuario.email}): {', '.join(cambios) or 'sin cambios'}",
    )
    if data.password and not MODO_DESARROLLO:
        enviar_aviso_cambio_contrasena(usuario.email, usuario.nombre)

    return {"status": "success", "mensaje": "Cuenta actualizada correctamente."}


@router.delete("/api/admin/usuarios/{usuario_id}")
def eliminar_usuario(usuario_id: int, admin: Usuario = Depends(usuario_admin), db: Session = Depends(get_db)):
    usuario = _buscar(db, usuario_id)
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}
    motivo = _motivo_protegida(usuario)
    if motivo:
        return {"status": "error", "mensaje": motivo}

    registrar_evento("admin_eliminacion", "advertencia", usuario=admin, detalle=f"cuenta {usuario.id} ({usuario.email})")
    borrar_cuenta(usuario, db)
    db.commit()
    return {"status": "success", "mensaje": "La cuenta y todos sus datos fueron eliminados."}
