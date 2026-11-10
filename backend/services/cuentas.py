"""Reglas de las cuentas: registro, sesión, recuperación y derechos sobre los datos."""

import hmac
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from core import (
    MODO_DESARROLLO, ROL_ADMIN, VERSION_POLITICA, anotar_fallo, crear_token, es_admin, es_cuenta_demo,
    exigir_bajo_el_limite, firmar_codigo, ip_actual, limitar,
)
from database import Usuario, es_hash_bcrypt, hash_password, verify_password
from errores import CodigoIncorrecto, Conflicto, NoAutenticado, NoEncontrado, Prohibido, ServicioNoDisponible
from notificaciones import (
    correo_configurado, enviar_aviso_cambio_contrasena, enviar_codigo_recuperacion, enviar_codigo_verificacion,
    enviar_en_segundo_plano,
)
from repositories import (
    eventos as repo_eventos, intentos as repo_intentos, pagos as repo_pagos, pedidos as repo_pedidos,
    suscripciones as repo_suscripciones, transaccion, usuarios as repo,
)
from schemas import (
    EliminarCuentaRequest, LoginRequest, PerfilRequest, RecuperacionRequest, ReenvioRequest, RegistroRequest,
    RestablecerRequest, VerificacionRequest,
)
from seguridad import registrar_evento
from services import pagos as servicio_pagos, pedidos as servicio_pedidos

VIGENCIA_CODIGO = timedelta(minutes=30)
ANTIGUEDAD_SIN_VERIFICAR = timedelta(days=1)
MENSAJE_REGISTRO = "Te enviamos un código de verificación a tu correo. Revisa también la carpeta de spam."
VIGENCIA_RECUPERACION = timedelta(minutes=15)
MAX_INTENTOS_RECUPERACION = 5
MENSAJE_RECUPERACION = "Si el correo tiene una cuenta, te enviamos un código para restablecer tu contraseña. Revisa también la carpeta de spam."
MENSAJE_CODIGO_INCORRECTO = "Código incorrecto o vencido. Puedes pedir uno nuevo."

# Un solo IP: 8 fallos en 5 minutos. Una cuenta: 30 fallos en 15 minutos, más de
# lo que puede sumar una sola IP, para que un atacante solo no bloquee a la víctima.
FALLOS_LOGIN_POR_IP = (8, 300)
FALLOS_LOGIN_POR_CUENTA = (30, 900)

# Se ejecuta bcrypt también si la cuenta no existe: si no, el tiempo de
# respuesta revelaría qué correos están registrados.
_HASH_FICTICIO = hash_password(secrets.token_hex(16))


def _nuevo_codigo(usuario: Usuario) -> str:
    """Asigna al usuario un código de 6 dígitos que vence en 30 minutos."""
    # secrets y no random: random es predecible y no sirve para códigos
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    usuario.codigo_verificacion = firmar_codigo("verificacion", usuario.id, codigo)
    usuario.codigo_expira = datetime.utcnow() + VIGENCIA_CODIGO
    return codigo


def _entregar_codigo(usuario: Usuario, codigo: str):
    """En desarrollo el código se muestra en consola; en producción se envía por
    correo, en segundo plano para que la respuesta tarde lo mismo exista o no la
    cuenta. Nunca se escribe en el log de producción: sería una filtración."""
    if MODO_DESARROLLO:
        print(f"[desarrollo] código de verificación: {codigo}")
        return
    enviar_en_segundo_plano(enviar_codigo_verificacion, usuario.email, codigo)


def registrar(db: Session, data: RegistroRequest) -> dict:
    email = data.email.lower()
    limitar(f"registro:{email}", maximo=3, ventana_segundos=3600)

    # Sin envío de correos nadie podría verificar la cuenta: mejor avisarlo
    # que crear cuentas que nunca se podrán usar
    if not MODO_DESARROLLO and not correo_configurado():
        raise ServicioNoDisponible("El registro de cuentas nuevas no está disponible por ahora. Prueba con las cuentas de demostración.")

    repo.purgar_sin_verificar(db, datetime.utcnow() - ANTIGUEDAD_SIN_VERIFICAR)

    # Se calcula siempre, para que el tiempo no revele si el correo ya existe
    password = hash_password(data.password)
    respuesta = {"status": "success", "mensaje": MENSAJE_REGISTRO, "user": {"email": email}}

    # Misma respuesta si el correo ya tiene cuenta: no se revela qué correos
    # están registrados (enumeración de usuarios)
    existente = repo.por_correo(db, email)
    if existente and (existente.verificado or es_admin(existente)):
        transaccion.confirmar(db)
        return respuesta

    # Una cuenta sin verificar pudo crearla cualquiera con este correo. El nuevo
    # registro la reemplaza: si no, la contraseña del primero seguiría valiendo
    # cuando la dueña del correo la verifique (pre-secuestro de la cuenta).
    usuario = existente or repo.crear(db, email=email, verificado=0)
    usuario.nombre = data.nombre
    usuario.password = password
    usuario.rol = data.rol
    usuario.telefono = data.telefono
    usuario.direccion = data.direccion
    usuario.consentimiento_datos = 1
    usuario.fecha_consentimiento = datetime.utcnow()
    usuario.acepta_terminos = 1
    usuario.politica_privacidad = VERSION_POLITICA
    transaccion.enviar(db)
    codigo = _nuevo_codigo(usuario)
    transaccion.confirmar(db)
    transaccion.recargar(db, usuario)

    _entregar_codigo(usuario, codigo)
    registrar_evento("registro", "info", usuario=usuario, detalle=f"rol {usuario.rol}")
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
    email = data.email.lower()
    clave_ip = f"login-ip:{ip_actual()}"
    clave_cuenta = f"login:{email}"

    # El administrador no tiene botón propio en el login: entra con
    # cualquiera de los dos tipos de cuenta
    usuario = repo.por_correo_y_roles(db, data.email, (data.rol, ROL_ADMIN))
    # La contraseña demo es pública: bloquearla no protege nada y dejaría fuera
    # a todos los visitantes
    demo = bool(usuario and es_cuenta_demo(usuario))

    # Solo cuentan los fallos: los inicios de sesión correctos no gastan el límite
    exigir_bajo_el_limite(clave_ip, *FALLOS_LOGIN_POR_IP)
    if not demo:
        exigir_bajo_el_limite(clave_cuenta, *FALLOS_LOGIN_POR_CUENTA)

    correcta = verify_password(data.password, usuario.password if usuario else _HASH_FICTICIO)
    if not usuario or not correcta:
        anotar_fallo(clave_ip)
        if not demo:
            anotar_fallo(clave_cuenta)
        registrar_evento("login_fallido", "advertencia", email=data.email, detalle=f"rol {data.rol}")
        raise NoAutenticado("Credenciales inválidas o el rol seleccionado no coincide.")

    # La cuenta todavía guardaba la contraseña en texto plano: se re-hashea
    # en el primer inicio de sesión correcto.
    if not es_hash_bcrypt(usuario.password):
        usuario.password = hash_password(usuario.password)
        transaccion.confirmar(db)
        transaccion.recargar(db, usuario)
        print("[migracion] contraseña re-hasheada en el inicio de sesión")

    # Lo que dejaron los visitantes anteriores en la cuenta demo no se conserva
    if demo:
        repo.limpiar_cuenta_demo(db, usuario.id)
        transaccion.confirmar(db)
        transaccion.recargar(db, usuario)

    registrar_evento("login_exitoso", "info", usuario=usuario)

    datos = {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol,
        "verificado": usuario.verificado,
    }
    # El código solo se expone en desarrollo para simular el envío por correo.
    # Nunca debe salir en producción. Se guarda su huella, así que se genera uno nuevo.
    if MODO_DESARROLLO and not usuario.verificado:
        datos["codigo_verificacion"] = _nuevo_codigo(usuario)
        transaccion.confirmar(db)
    # Solo una cuenta verificada recibe token para operar con la API
    if usuario.verificado:
        datos["token"] = crear_token(usuario)
    return {"status": "success", "mensaje": f"Bienvenido/a {usuario.nombre}", "user": datos}


def cerrar_sesion(db: Session, usuario: Usuario) -> dict:
    """Invalida en el servidor todos los tokens de la cuenta. No aplica a las
    cuentas demo: las comparten todos los visitantes."""
    if not es_cuenta_demo(usuario):
        usuario.sesion_version = (usuario.sesion_version or 0) + 1
        transaccion.confirmar(db)
    return {"status": "success", "mensaje": "Sesión cerrada."}


def verificar(db: Session, data: VerificacionRequest) -> dict:
    # Un código de 6 dígitos se adivinaría por fuerza bruta sin un límite por cuenta
    limitar(f"verificar:{data.email.lower()}", maximo=5, ventana_segundos=3600)

    usuario = repo.por_correo(db, data.email)
    # Mismo mensaje para cuenta inexistente o código incorrecto: no revela
    # qué correos están registrados
    vigente = bool(usuario and usuario.codigo_expira and usuario.codigo_expira >= datetime.utcnow())
    codigo_correcto = bool(
        usuario and not usuario.verificado and usuario.codigo_verificacion and vigente
        and hmac.compare_digest(usuario.codigo_verificacion, firmar_codigo("verificacion", usuario.id, data.codigo))
    )
    # La contraseña también se exige: así la verificación solo la completa quien
    # controla el correo y además fijó la contraseña de la cuenta
    if not codigo_correcto or not verify_password(data.password, usuario.password):
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
    """Indica si el envío real de correos está activo, sin revelar nada más de
    la configuración del servidor."""
    return {"status": "success", "correo_real": correo_configurado()}


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
    usuario.recuperacion_hash = firmar_codigo("recuperacion", usuario.id, codigo)
    usuario.recuperacion_expira = datetime.utcnow() + VIGENCIA_RECUPERACION
    usuario.recuperacion_intentos = 0
    transaccion.confirmar(db)
    registrar_evento("recuperacion_solicitada", "info", usuario=usuario)

    if MODO_DESARROLLO:
        # Solo en desarrollo, para probar sin correo. Nunca en producción.
        print(f"[desarrollo] código de recuperación: {codigo}")
        respuesta["codigo_desarrollo"] = codigo
    else:
        enviar_en_segundo_plano(enviar_codigo_recuperacion, usuario.email, codigo)
    return respuesta


def restablecer_contrasena(db: Session, data: RestablecerRequest) -> dict:
    limitar(f"restablecer:{data.email.lower()}", maximo=8, ventana_segundos=3600)

    usuario = repo.por_correo(db, data.email)
    if not usuario or not usuario.recuperacion_hash:
        registrar_evento("recuperacion_fallida", "advertencia", email=data.email, detalle="sin código vigente")
        raise CodigoIncorrecto(MENSAJE_CODIGO_INCORRECTO)

    vigente = usuario.recuperacion_expira and usuario.recuperacion_expira >= datetime.utcnow()
    if not vigente or not hmac.compare_digest(usuario.recuperacion_hash, firmar_codigo("recuperacion", usuario.id, data.codigo)):
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
        enviar_en_segundo_plano(enviar_aviso_cambio_contrasena, usuario.email)
    return {"status": "success", "mensaje": "Tu contraseña se restableció. Ya puedes iniciar sesión con la nueva."}


def obtener_perfil(db: Session, solicitante: Usuario, usuario_id: int) -> dict:
    """Trae datos de contacto: solo lo puede ver el propio usuario o un productor
    con quien tenga una suscripción activa. Lo demás responde igual que un
    usuario inexistente, para no revelar qué ids existen."""
    usuario = repo.por_id(db, usuario_id)
    ajeno = bool(usuario) and solicitante.id != usuario.id
    permitido = bool(usuario) and (not ajeno or repo_suscripciones.existe_entre(db, usuario.id, solicitante.id))
    # Las credenciales demo son públicas: esa cuenta solo ve datos de cuentas demo
    if permitido and ajeno and es_cuenta_demo(solicitante) and not es_cuenta_demo(usuario):
        permitido = False
    if not permitido:
        if usuario:
            registrar_evento("acceso_denegado", "advertencia", usuario=solicitante, detalle=f"perfil del usuario {usuario_id}")
        raise NoEncontrado("Usuario no encontrado.")

    # Quién leyó datos de quién: hace falta para reconstruir un incidente
    if ajeno:
        registrar_evento("lectura_datos", "info", usuario=solicitante, detalle=f"perfil del usuario {usuario_id}")
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
    if data.email.lower() != usuario.email.lower():
        registrar_evento("acceso_denegado", "advertencia", usuario=usuario, detalle="editar el perfil de otra cuenta")
        raise Prohibido("Solo puedes editar tu propio perfil.")
    if es_cuenta_demo(usuario):
        registrar_evento("cuenta_demo", "advertencia", usuario=usuario, detalle="modificar perfil")
        raise Prohibido("La cuenta de demostración no se puede modificar.")

    cambia_password = bool(cambios.get("password"))
    if cambia_password:
        # Con un token robado no se debe poder probar contraseñas sin límite
        limitar(f"cambio-clave:{usuario.id}", maximo=5, ventana_segundos=900)
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

    if cambia_password and not MODO_DESARROLLO:
        enviar_en_segundo_plano(enviar_aviso_cambio_contrasena, usuario.email)

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


def exportar_datos(db: Session, usuario: Usuario) -> dict:
    """Derecho de acceso y portabilidad: una copia de los datos de la cuenta."""
    limitar(f"exportar:{usuario.id}", maximo=5, ventana_segundos=3600)
    registrar_evento("exportacion_datos", "info", usuario=usuario)
    return {
        "status": "success",
        "generado": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "cuenta": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol,
            "telefono": usuario.telefono,
            "direccion": usuario.direccion,
            "fecha_consentimiento": usuario.fecha_consentimiento.isoformat() if usuario.fecha_consentimiento else None,
            "version_politica": usuario.politica_privacidad,
        },
        "adopciones": [
            {
                "arbol": s.arbol.nombre if s.arbol else None,
                "fecha": s.fecha_suscripcion.isoformat() if s.fecha_suscripcion else None,
            }
            for s in repo_suscripciones.de_usuario_con_arbol(db, usuario.id)
        ],
        "pedidos": [servicio_pedidos.serializar(p) for p in repo_pedidos.de_cliente(db, usuario.id)],
        "pagos": [servicio_pagos.serializar(p) for p in repo_pagos.de_usuario(db, usuario.id, limite=None)],
    }


def borrar_rastro(email: str, usuario_id: int):
    """Quita el correo de los registros auxiliares al eliminar una cuenta. El
    registro de seguridad conserva la IP y la acción hasta su plazo de 30 días."""
    repo_eventos.anonimizar(email, usuario_id)
    repo_intentos.borrar_de_correo(email)


def eliminar_propia(db: Session, usuario: Usuario, data: EliminarCuentaRequest) -> dict:
    """Derecho a la eliminación de datos (Ley 21.719). La cuenta sale del token:
    el correo, un dato personal, no viaja en la ruta. Se pide la contraseña para
    que un token robado no baste para borrar la cuenta."""
    if es_cuenta_demo(usuario):
        registrar_evento("cuenta_demo", "advertencia", usuario=usuario, detalle="eliminar cuenta")
        raise Prohibido("La cuenta de demostración no se puede eliminar.")
    # Si la cuenta del administrador desapareciera, su correo quedaría libre para
    # que otra persona lo registrara
    if es_admin(usuario):
        raise Prohibido("La cuenta de administrador no se elimina desde el perfil.")

    limitar(f"eliminar:{usuario.id}", maximo=5, ventana_segundos=900)
    if not verify_password(data.password, usuario.password):
        registrar_evento("eliminar_cuenta_fallido", "advertencia", usuario=usuario, detalle="contraseña incorrecta")
        raise Prohibido("La contraseña no es correcta.")

    # Borrar la cuenta dejaría a esas personas sin lo que pagaron y sin aviso
    if repo_suscripciones.contar_de_productor(db, usuario.id):
        raise Conflicto("Tus árboles tienen suscriptores activos. Avísales y expúlsalos antes de eliminar tu cuenta.")

    email, usuario_id = usuario.email, usuario.id
    repo.borrar_con_sus_datos(db, usuario)
    transaccion.confirmar(db)
    borrar_rastro(email, usuario_id)
    registrar_evento("cuenta_eliminada", "info", detalle=f"usuario {usuario_id}")
    return {
        "status": "success",
        "mensaje": "Eliminamos tu cuenta, tus adopciones, tus pedidos y tus pagos. El registro de seguridad conserva "
                   "la IP y las acciones, sin tu correo, hasta por 30 días.",
    }
