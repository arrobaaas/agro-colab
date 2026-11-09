"""Reglas de las cuentas: registro, sesión, recuperación y derechos sobre los datos."""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from core import MODO_DESARROLLO, ROL_ADMIN, crear_token, es_cuenta_demo, limitar
from database import Usuario, es_hash_bcrypt, hash_password, verify_password
from errores import CodigoIncorrecto, NoAutenticado, NoEncontrado, Prohibido, ServicioNoDisponible
from notificaciones import (
    correo_configurado, enviar_aviso_cambio_contrasena, enviar_codigo_recuperacion, enviar_codigo_verificacion,
)
from repositories import suscripciones as repo_suscripciones, transaccion, usuarios as repo
from schemas import (
    EliminarCuentaRequest, LoginRequest, PerfilRequest, RecuperacionRequest, ReenvioRequest, RegistroRequest, RestablecerRequest,
    VerificacionRequest,
)
from seguridad import registrar_evento

VIGENCIA_CODIGO = timedelta(minutes=30)
MENSAJE_REGISTRO = "Te enviamos un código de verificación a tu correo. Revisa también la carpeta de spam."
VIGENCIA_RECUPERACION = timedelta(minutes=15)
MAX_INTENTOS_RECUPERACION = 5
MENSAJE_RECUPERACION = "Si el correo tiene una cuenta, te enviamos un código para restablecer tu contraseña. Revisa también la carpeta de spam."
MENSAJE_CODIGO_INCORRECTO = "Código incorrecto o vencido. Puedes pedir uno nuevo."
# Hash de relleno: si el correo no existe se compara igual contra bcrypt, para
# que la demora de la respuesta no revele qué correos están registrados
HASH_DE_RELLENO = hash_password(secrets.token_hex(16))


def _nuevo_codigo(usuario: Usuario) -> str:
    """Asigna al usuario un código de 6 dígitos que vence en 30 minutos."""
    # secrets y no random: random es predecible y no sirve para códigos
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    usuario.codigo_verificacion = codigo
    usuario.codigo_expira = datetime.utcnow() + VIGENCIA_CODIGO
    return codigo


def _entregar_codigo(usuario: Usuario, codigo: str) -> bool:
    """En desarrollo el código se muestra en consola; en producción se envía
    por correo (nunca se escribe en el log: sería una filtración)."""
    if MODO_DESARROLLO:
        print(f"[desarrollo] código de verificación de {usuario.email}: {codigo}")
        return True
    return enviar_codigo_verificacion(usuario.email, usuario.nombre, codigo)


def _hash_codigo(codigo: str) -> str:
    """El código se guarda como hash: quien lea la base no puede usarlo."""
    return hashlib.sha256(codigo.encode("utf-8")).hexdigest()


def registrar(db: Session, data: RegistroRequest) -> dict:
    limitar(f"registro:{data.email.lower()}", maximo=3, ventana_segundos=3600)

    # Sin envío de correos nadie podría verificar la cuenta: mejor avisarlo
    # que crear cuentas que nunca se podrán usar
    if not MODO_DESARROLLO and not correo_configurado():
        raise ServicioNoDisponible("El registro de cuentas nuevas no está disponible por ahora. Prueba con las cuentas de demostración.")

    # Misma respuesta si el correo ya tiene cuenta: no se revela qué correos
    # están registrados (enumeración de usuarios)
    if repo.por_correo(db, data.email):
        return {"status": "success", "mensaje": MENSAJE_REGISTRO, "user": {"email": data.email}}

    usuario = repo.crear(
        db,
        nombre=data.nombre,
        email=data.email.lower(),
        password=hash_password(data.password),
        rol=data.rol,
        telefono=data.telefono,
        direccion=data.direccion,
        verificado=0,
        consentimiento_datos=1,
        fecha_consentimiento=datetime.now(),
        acepta_terminos=1,
    )
    codigo = _nuevo_codigo(usuario)
    transaccion.confirmar(db)
    transaccion.recargar(db, usuario)

    if not _entregar_codigo(usuario, codigo):
        # Sin el correo la cuenta no se podría verificar: se deshace el registro
        transaccion.eliminar(db, usuario)
        transaccion.confirmar(db)
        raise ServicioNoDisponible("No pudimos enviar el correo de verificación. Intenta nuevamente en unos minutos.")

    registrar_evento("registro", "info", usuario=usuario, detalle=f"rol {usuario.rol}")
    respuesta = {"status": "success", "mensaje": MENSAJE_REGISTRO, "user": {"email": usuario.email}}
    # El código solo se devuelve en desarrollo, para probar el flujo sin correo
    if MODO_DESARROLLO:
        respuesta["user"]["codigo_verificacion"] = codigo
    return respuesta


def reenviar_codigo(db: Session, data: ReenvioRequest) -> dict:
    limitar(f"reenvio:{data.email.lower()}", maximo=3, ventana_segundos=3600)

    respuesta = {"status": "success", "mensaje": "Si la cuenta existe y no está verificada, te enviamos un código nuevo."}
    usuario = repo.por_correo(db, data.email)
    if usuario and not usuario.verificado:
        codigo = _nuevo_codigo(usuario)
        transaccion.confirmar(db)
        _entregar_codigo(usuario, codigo)
        if MODO_DESARROLLO:
            respuesta["codigo_verificacion"] = codigo
    return respuesta


def iniciar_sesion(db: Session, data: LoginRequest) -> dict:
    # Además del límite por IP, un límite por cuenta frena la fuerza bruta
    # repartida entre muchas IPs contra un mismo correo
    limitar(f"login:{data.email.lower()}", maximo=10, ventana_segundos=900)

    # El administrador no tiene botón propio en el login: entra con
    # cualquiera de los dos tipos de cuenta
    usuario = repo.por_correo_y_roles(db, data.email, (data.rol, ROL_ADMIN))

    if not usuario:
        verify_password(data.password, HASH_DE_RELLENO)
    if not usuario or not verify_password(data.password, usuario.password):
        registrar_evento("login_fallido", "advertencia", email=data.email, detalle=f"rol {data.rol}")
        raise NoAutenticado("Credenciales inválidas o el rol seleccionado no coincide.")

    # La cuenta todavía guardaba la contraseña en texto plano: se re-hashea
    # en el primer inicio de sesión correcto.
    if not es_hash_bcrypt(usuario.password):
        usuario.password = hash_password(usuario.password)
        transaccion.confirmar(db)
        transaccion.recargar(db, usuario)
        print(f"[migracion] contraseña re-hasheada para {usuario.email}")

    registrar_evento("login_exitoso", "info", usuario=usuario)

    datos = {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol,
        "verificado": usuario.verificado,
    }
    # El código solo se expone en desarrollo para simular el envío por correo.
    # Nunca debe salir en producción.
    if MODO_DESARROLLO:
        datos["codigo_verificacion"] = usuario.codigo_verificacion
    # Solo una cuenta verificada recibe token para operar con la API
    if usuario.verificado:
        datos["token"] = crear_token(usuario)
    return {"status": "success", "mensaje": f"Bienvenido/a {usuario.nombre}", "user": datos}


def verificar(db: Session, data: VerificacionRequest) -> dict:
    # Un código de 6 dígitos se adivinaría por fuerza bruta sin un límite por cuenta
    limitar(f"verificar:{data.email.lower()}", maximo=5, ventana_segundos=3600)

    usuario = repo.por_correo(db, data.email)
    # Mismo mensaje para cuenta inexistente o código incorrecto: no revela
    # qué correos están registrados
    vigente = bool(usuario and usuario.codigo_expira and usuario.codigo_expira >= datetime.utcnow())
    if not usuario or usuario.verificado or not usuario.codigo_verificacion or not vigente or not hmac.compare_digest(
        usuario.codigo_verificacion, data.codigo
    ):
        registrar_evento("verificacion_fallida", "info", email=data.email)
        raise CodigoIncorrecto(MENSAJE_CODIGO_INCORRECTO)

    usuario.verificado = 1
    usuario.codigo_verificacion = None
    usuario.codigo_expira = None
    transaccion.confirmar(db)
    transaccion.recargar(db, usuario)

    # El código llegó a su correo: eso ya prueba que la cuenta es suya, así
    # que se entrega la sesión y no hay que volver a escribir los datos
    registrar_evento("login_exitoso", "info", usuario=usuario, detalle="al verificar la cuenta")
    return {
        "status": "success",
        "mensaje": f"Cuenta verificada. Bienvenido/a {usuario.nombre}",
        "user": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol,
            "verificado": usuario.verificado,
            "token": crear_token(usuario),
        },
    }


def estado_servicio() -> dict:
    """Indica si el envío real de correos está activo (sin exponer claves).

    El frontend lo usa para avisar antes de registrarse, y sirve para
    comprobar la configuración de Render sin crear una cuenta de prueba.
    """
    return {
        "status": "success",
        "correo_real": correo_configurado(),
        "modo_desarrollo": MODO_DESARROLLO,
        # Solo si cada variable existe (nunca su valor), para saber cuál
        # falta en Render cuando correo_real sale en false
        "variables": {
            "BREVO_API_KEY": bool(os.getenv("BREVO_API_KEY", "").strip()),
            "CORREO_REMITENTE": bool(os.getenv("CORREO_REMITENTE", "").strip()),
        },
    }


def recuperar_contrasena(db: Session, data: RecuperacionRequest) -> dict:
    limitar(f"recuperar:{data.email.lower()}", maximo=3, ventana_segundos=3600)

    if not MODO_DESARROLLO and not correo_configurado():
        raise ServicioNoDisponible("La recuperación de contraseña no está disponible por ahora. Intenta más tarde.")

    respuesta = {"status": "success", "mensaje": MENSAJE_RECUPERACION}

    # Siempre la misma respuesta, exista o no la cuenta: no se revela qué
    # correos están registrados (enumeración de usuarios)
    usuario = repo.por_correo(db, data.email)
    if not usuario or es_cuenta_demo(usuario):
        registrar_evento("recuperacion_solicitada", "info", email=data.email, detalle="sin cuenta o cuenta demo")
        return respuesta

    codigo = f"{secrets.randbelow(1_000_000):06d}"
    usuario.recuperacion_hash = _hash_codigo(codigo)
    usuario.recuperacion_expira = datetime.utcnow() + VIGENCIA_RECUPERACION
    usuario.recuperacion_intentos = 0
    transaccion.confirmar(db)
    registrar_evento("recuperacion_solicitada", "info", usuario=usuario)

    if MODO_DESARROLLO:
        # Solo en desarrollo, para probar sin correo. Nunca en producción.
        print(f"[desarrollo] código de recuperación de {usuario.email}: {codigo}")
        respuesta["codigo_desarrollo"] = codigo
    elif not enviar_codigo_recuperacion(usuario.email, usuario.nombre, codigo):
        raise ServicioNoDisponible("No pudimos enviar el correo. Intenta nuevamente en unos minutos.")
    return respuesta


def restablecer_contrasena(db: Session, data: RestablecerRequest) -> dict:
    limitar(f"restablecer:{data.email.lower()}", maximo=8, ventana_segundos=3600)

    usuario = repo.por_correo(db, data.email)
    if not usuario or not usuario.recuperacion_hash:
        registrar_evento("recuperacion_fallida", "advertencia", email=data.email, detalle="sin código vigente")
        raise CodigoIncorrecto(MENSAJE_CODIGO_INCORRECTO)

    vigente = usuario.recuperacion_expira and usuario.recuperacion_expira >= datetime.utcnow()
    if not vigente or not hmac.compare_digest(usuario.recuperacion_hash, _hash_codigo(data.codigo)):
        # Tras varios intentos el código se anula: 6 dígitos no resisten
        # fuerza bruta sin este tope (además del límite por IP y por cuenta)
        usuario.recuperacion_intentos = (usuario.recuperacion_intentos or 0) + 1
        if not vigente or usuario.recuperacion_intentos >= MAX_INTENTOS_RECUPERACION:
            usuario.recuperacion_hash = None
            usuario.recuperacion_expira = None
        transaccion.confirmar(db)
        registrar_evento("recuperacion_fallida", "advertencia", usuario=usuario, detalle=f"intento {usuario.recuperacion_intentos}")
        raise CodigoIncorrecto(MENSAJE_CODIGO_INCORRECTO)

    # El token de sesión depende del hash de la contraseña (core.crear_token):
    # al cambiarla, todas las sesiones abiertas dejan de valer
    usuario.password = hash_password(data.password)
    usuario.recuperacion_hash = None
    usuario.recuperacion_expira = None
    usuario.recuperacion_intentos = 0
    # Recibir el código prueba que el correo es suyo
    usuario.verificado = 1
    usuario.codigo_verificacion = None
    usuario.codigo_expira = None
    transaccion.confirmar(db)
    registrar_evento("contrasena_restablecida", "info", usuario=usuario)

    if not MODO_DESARROLLO:
        enviar_aviso_cambio_contrasena(usuario.email, usuario.nombre)
    return {"status": "success", "mensaje": "Tu contraseña se restableció. Ya puedes iniciar sesión con la nueva."}


def obtener_perfil(db: Session, solicitante: Usuario, usuario_id: int) -> dict:
    """Trae datos de contacto: solo lo puede ver el propio usuario o un
    productor con quien tenga una suscripción activa."""
    usuario = repo.por_id(db, usuario_id)
    if not usuario:
        raise NoEncontrado("Usuario no encontrado.")

    if solicitante.id != usuario.id and not repo_suscripciones.existe_entre(db, usuario.id, solicitante.id):
        registrar_evento("acceso_denegado", "advertencia", usuario=solicitante, detalle=f"perfil del usuario {usuario_id}")
        raise Prohibido("No tienes permiso para ver este perfil.")

    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "telefono": usuario.telefono,
        "direccion": usuario.direccion,
        "rol": usuario.rol,
        "verificado": usuario.verificado,
    }


def actualizar_perfil(db: Session, usuario: Usuario, data: PerfilRequest) -> dict:
    cambios = data.model_dump(exclude_unset=True)

    # Se edita siempre la cuenta de la sesión. Antes se buscaba por el correo
    # enviado, y cualquiera podía cambiar la contraseña de otra cuenta.
    if data.email != usuario.email:
        registrar_evento("acceso_denegado", "advertencia", usuario=usuario, detalle=f"editar el perfil de {data.email}")
        raise Prohibido("Solo puedes editar tu propio perfil.")
    if es_cuenta_demo(usuario):
        registrar_evento("cuenta_demo", "advertencia", usuario=usuario, detalle="modificar perfil")
        raise Prohibido("La cuenta de demostración no se puede modificar.")

    cambia_password = bool(cambios.get("password"))
    if cambia_password and not (data.password_actual and verify_password(data.password_actual, usuario.password)):
        registrar_evento("cambio_password_fallido", "advertencia", usuario=usuario, detalle="contraseña actual incorrecta")
        raise Prohibido("Para cambiar la contraseña ingresa tu contraseña actual.")

    for campo in ("nombre", "telefono", "direccion"):
        if campo in cambios:
            setattr(usuario, campo, cambios[campo])
    if cambia_password:
        usuario.password = hash_password(cambios["password"])
        registrar_evento("cambio_password", "info", usuario=usuario)

    transaccion.confirmar(db)
    transaccion.recargar(db, usuario)

    datos = {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol,
        "telefono": usuario.telefono,
        "direccion": usuario.direccion,
    }
    # Cambiar la contraseña invalida los tokens anteriores: se entrega uno nuevo
    if cambia_password:
        datos["token"] = crear_token(usuario)
    return {"status": "success", "mensaje": "Perfil actualizado correctamente.", "user": datos}


def eliminar_propia(db: Session, usuario: Usuario, data: EliminarCuentaRequest) -> dict:
    """Derecho a la eliminación de datos (Art. 20 Ley 21.719). La cuenta sale
    del token: el correo, un dato personal, no viaja en la ruta. Se pide la
    contraseña actual: con un token robado no se puede borrar la cuenta."""
    if es_cuenta_demo(usuario):
        registrar_evento("cuenta_demo", "advertencia", usuario=usuario, detalle="eliminar cuenta")
        raise Prohibido("La cuenta de demostración no se puede eliminar.")

    # Sin tope, quien tenga el token podría adivinar la contraseña aquí
    limitar(f"eliminar:{usuario.id}", maximo=5, ventana_segundos=900)
    if not verify_password(data.password, usuario.password):
        registrar_evento("eliminar_cuenta_fallido", "advertencia", usuario=usuario, detalle="contraseña incorrecta")
        raise Prohibido("La contraseña no es correcta. Tu cuenta no se eliminó.")

    registrar_evento("cuenta_eliminada", "info", usuario=usuario)
    repo.borrar_con_sus_datos(db, usuario)
    transaccion.confirmar(db)
    return {"status": "success", "mensaje": "Todos tus datos han sido eliminados correctamente."}
