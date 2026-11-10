"""Panel de administración: ver, editar y eliminar cuentas.

El administrador no puede tocar otras cuentas de administrador ni las cuentas
demo, y cada cambio queda en el registro de seguridad.
"""

from sqlalchemy.orm import Session

from core import MODO_DESARROLLO, es_admin, es_cuenta_demo
from database import Usuario, hash_password
from errores import Conflicto, NoEncontrado, Prohibido
from notificaciones import enviar_aviso_adopcion_cancelada, enviar_aviso_cambio_contrasena, enviar_en_segundo_plano
from repositories import arboles as repo_arboles, pedidos as repo_pedidos, suscripciones as repo_suscripciones, transaccion, usuarios as repo
from schemas import AdminUsuarioRequest
from seguridad import registrar_evento
from services.arboles import serializar as serializar_arbol
from services.cuentas import borrar_rastro


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


def _buscar(db: Session, usuario_id: int) -> Usuario:
    usuario = repo.por_id(db, usuario_id)
    if not usuario:
        raise NoEncontrado("Usuario no encontrado.")
    return usuario


def _exigir_no_protegida(usuario: Usuario):
    if es_admin(usuario):
        raise Prohibido("Las cuentas de administrador no se modifican desde el panel. Usa tu perfil.")
    if es_cuenta_demo(usuario):
        raise Prohibido("Las cuentas de demostración no se modifican: sus credenciales son públicas.")


def listar(db: Session, admin: Usuario) -> dict:
    registrar_evento("lectura_datos", "info", usuario=admin, detalle="lista de cuentas")
    arboles = repo_arboles.publicados_por_usuario(db)
    adopciones = repo_suscripciones.adopciones_por_usuario(db)
    pedidos = repo_pedidos.por_cliente(db)
    return {"status": "success", "usuarios": [_resumen(u, arboles, adopciones, pedidos) for u in repo.listar(db)]}


def detalle(db: Session, admin: Usuario, usuario_id: int) -> dict:
    usuario = _buscar(db, usuario_id)
    registrar_evento("lectura_datos", "info", usuario=admin, detalle=f"cuenta {usuario_id}")
    arboles = repo_arboles.de_productor(db, usuario.id)
    adoptados = repo_arboles.adoptados_por(db, usuario.id)
    resumen = _resumen(
        usuario,
        {usuario.id: len(arboles)},
        {usuario.id: len(adoptados)},
        {usuario.id: repo_pedidos.contar_de_cliente(db, usuario.id)},
    )
    return {
        "status": "success",
        "usuario": resumen,
        "arboles": [serializar_arbol(db, a) for a in arboles],
        "adoptados": [serializar_arbol(db, a) for a in adoptados],
    }


def editar(db: Session, admin: Usuario, usuario_id: int, data: AdminUsuarioRequest) -> dict:
    usuario = _buscar(db, usuario_id)
    _exigir_no_protegida(usuario)

    email = data.email.lower()
    if repo.correo_en_otra_cuenta(db, email, usuario.id):
        raise Conflicto("Ese correo ya pertenece a otra cuenta.")

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
    transaccion.confirmar(db)

    registrar_evento(
        "admin_edicion", "info", usuario=admin,
        detalle=f"cuenta {usuario.id}: {', '.join(cambios) or 'sin cambios'}",
    )
    if data.password and not MODO_DESARROLLO:
        enviar_en_segundo_plano(enviar_aviso_cambio_contrasena, usuario.email)
    return {"status": "success", "mensaje": "Cuenta actualizada correctamente."}


def eliminar(db: Session, admin: Usuario, usuario_id: int) -> dict:
    usuario = _buscar(db, usuario_id)
    _exigir_no_protegida(usuario)

    email, cuenta_id = usuario.email, usuario.id
    # Quienes adoptaron árboles de esta cuenta los pierden: se les avisa
    afectados = [
        (s.usuario.email, s.arbol.nombre)
        for s in repo_suscripciones.de_productor_con_usuario(db, cuenta_id)
        if s.usuario and s.arbol
    ]
    repo.borrar_con_sus_datos(db, usuario)
    transaccion.confirmar(db)
    borrar_rastro(email, cuenta_id)
    registrar_evento("admin_eliminacion", "advertencia", usuario=admin, detalle=f"cuenta {cuenta_id}")
    if not MODO_DESARROLLO:
        for destinatario, arbol in afectados:
            enviar_en_segundo_plano(enviar_aviso_adopcion_cancelada, destinatario, arbol)
    return {"status": "success", "mensaje": "La cuenta y todos sus datos fueron eliminados."}
