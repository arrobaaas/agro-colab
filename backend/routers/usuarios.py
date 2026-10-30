"""Router de usuarios (registro, login, verificación, perfil y derechos de datos)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import hmac
import secrets

from core import (
    LoginRequest, RegistroRequest, VerificacionRequest, PerfilRequest, ReenvioRequest,
    correo_configurado, enviar_codigo_verificacion,
    hash_password, verify_password, foto_de, get_db, MODO_DESARROLLO, limitar_por_ip, crear_token, usuario_actual,
    limitar, es_cuenta_demo,
)
from seguridad import registrar_evento
from database import Usuario, Arbol, Suscripcion, Pedido, SessionLocal, es_hash_bcrypt

router = APIRouter()


VIGENCIA_CODIGO = timedelta(minutes=30)
MENSAJE_REGISTRO = "Te enviamos un código de verificación a tu correo. Revisa también la carpeta de spam."


def nuevo_codigo(usuario: Usuario) -> str:
    """Asigna al usuario un código de 6 dígitos que vence en 30 minutos."""
    # secrets y no random: random es predecible y no sirve para códigos
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    usuario.codigo_verificacion = codigo
    usuario.codigo_expira = datetime.utcnow() + VIGENCIA_CODIGO
    return codigo


def entregar_codigo(usuario: Usuario, codigo: str) -> bool:
    """En desarrollo el código se muestra en consola; en producción se envía
    por correo (nunca se escribe en el log: sería una filtración)."""
    if MODO_DESARROLLO:
        print(f"[desarrollo] código de verificación de {usuario.email}: {codigo}")
        return True
    return enviar_codigo_verificacion(usuario.email, usuario.nombre, codigo)


@router.post("/api/register", dependencies=[Depends(limitar_por_ip(maximo=5, ventana_segundos=3600))])
def registrar_usuario(data: RegistroRequest, db: Session = Depends(get_db)):
    limitar(f"registro:{data.email.lower()}", maximo=3, ventana_segundos=3600)

    # Sin envío de correos nadie podría verificar la cuenta: mejor avisarlo
    # que crear cuentas que nunca se podrán usar
    if not MODO_DESARROLLO and not correo_configurado():
        return {"status": "error", "mensaje": "El registro de cuentas nuevas no está disponible por ahora. Prueba con las cuentas de demostración."}

    # Misma respuesta si el correo ya tiene cuenta: no se revela qué correos
    # están registrados (enumeración de usuarios)
    existente = db.query(Usuario).filter(Usuario.email == data.email).first()
    if existente:
        return {"status": "success", "mensaje": MENSAJE_REGISTRO, "user": {"email": data.email}}

    nuevo_usuario = Usuario(
        nombre=data.nombre,
        email=data.email,
        password=hash_password(data.password),
        rol=data.rol,
        telefono=data.telefono,
        direccion=data.direccion,
        verificado=0,
        consentimiento_datos=1,
        fecha_consentimiento=datetime.now(),
        acepta_terminos=1
    )
    codigo = nuevo_codigo(nuevo_usuario)
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    if not entregar_codigo(nuevo_usuario, codigo):
        # Sin el correo la cuenta no se podría verificar: se deshace el registro
        db.delete(nuevo_usuario)
        db.commit()
        return {"status": "error", "mensaje": "No pudimos enviar el correo de verificación. Intenta nuevamente en unos minutos."}

    registrar_evento("registro", "info", usuario=nuevo_usuario, detalle=f"rol {nuevo_usuario.rol}")
    respuesta = {"status": "success", "mensaje": MENSAJE_REGISTRO, "user": {"email": nuevo_usuario.email}}
    # El código solo se devuelve en desarrollo, para probar el flujo sin correo
    if MODO_DESARROLLO:
        respuesta["user"]["codigo_verificacion"] = codigo
    return respuesta


@router.post("/api/reenviar-codigo", dependencies=[Depends(limitar_por_ip(maximo=5, ventana_segundos=3600))])
def reenviar_codigo(data: ReenvioRequest, db: Session = Depends(get_db)):
    limitar(f"reenvio:{data.email.lower()}", maximo=3, ventana_segundos=3600)

    respuesta = {"status": "success", "mensaje": "Si la cuenta existe y no está verificada, te enviamos un código nuevo."}
    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
    if usuario and not usuario.verificado:
        codigo = nuevo_codigo(usuario)
        db.commit()
        entregar_codigo(usuario, codigo)
        if MODO_DESARROLLO:
            respuesta["codigo_verificacion"] = codigo
    return respuesta


@router.post("/api/login", dependencies=[Depends(limitar_por_ip(maximo=8, ventana_segundos=300))])
def login(data: LoginRequest, db: Session = Depends(get_db)):
    # Además del límite por IP, un límite por cuenta frena la fuerza bruta
    # repartida entre muchas IPs contra un mismo correo
    limitar(f"login:{data.email.lower()}", maximo=10, ventana_segundos=900)

    usuario = db.query(Usuario).filter(
        Usuario.email == data.email,
        Usuario.rol == data.rol
    ).first()

    if not usuario or not verify_password(data.password, usuario.password):
        registrar_evento("login_fallido", "advertencia", email=data.email, detalle=f"rol {data.rol}")
        return {
            "status": "error",
            "mensaje": "Credenciales inválidas o el rol seleccionado no coincide."
        }

    # La cuenta todavía guardaba la contraseña en texto plano: se re-hashea
    # en el primer inicio de sesión correcto.
    if not es_hash_bcrypt(usuario.password):
        usuario.password = hash_password(usuario.password)
        db.commit()
        db.refresh(usuario)
        print(f"[migracion] contraseña re-hasheada para {usuario.email}")

    registrar_evento("login_exitoso", "info", usuario=usuario)

    usuario_respuesta = {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol,
        "verificado": usuario.verificado,
    }
    # El código solo se expone en desarrollo para simular el envío por correo.
    # Nunca debe salir en producción.
    if MODO_DESARROLLO:
        usuario_respuesta["codigo_verificacion"] = usuario.codigo_verificacion
    # Solo una cuenta verificada recibe token para operar con la API
    if usuario.verificado:
        usuario_respuesta["token"] = crear_token(usuario)

    return {
        "status": "success",
        "mensaje": f"Bienvenido/a {usuario.nombre}",
        "user": usuario_respuesta
    }


@router.post("/api/verificar-cuenta", dependencies=[Depends(limitar_por_ip(maximo=10, ventana_segundos=3600))])
def verificar_cuenta(data: VerificacionRequest, db: Session = Depends(get_db)):
    # Un código de 6 dígitos se adivinaría por fuerza bruta sin un límite por cuenta
    limitar(f"verificar:{data.email.lower()}", maximo=5, ventana_segundos=3600)

    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
    # Mismo mensaje para cuenta inexistente o código incorrecto: no revela
    # qué correos están registrados
    vigente = bool(usuario and usuario.codigo_expira and usuario.codigo_expira >= datetime.utcnow())
    if not usuario or usuario.verificado or not usuario.codigo_verificacion or not vigente or not hmac.compare_digest(
        usuario.codigo_verificacion, data.codigo
    ):
        registrar_evento("verificacion_fallida", "info", email=data.email)
        return {"status": "error", "mensaje": "Código incorrecto o vencido. Puedes pedir uno nuevo."}

    usuario.verificado = 1
    usuario.codigo_verificacion = None
    usuario.codigo_expira = None
    db.commit()

    return {
        "status": "success",
        "mensaje": "Cuenta verificada correctamente. Ya puedes iniciar sesión."
    }


@router.get("/api/usuario/{usuario_id}")
def obtener_usuario(
    usuario_id: int,
    solicitante: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """Perfil de un usuario (para que el agricultor vea a sus suscriptores).

    Trae datos de contacto: solo lo puede ver el propio usuario o un productor
    con quien tenga una suscripción activa.
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}

    if solicitante.id != usuario.id:
        es_su_productor = (
            db.query(Suscripcion)
            .join(Arbol, Suscripcion.arbol_id == Arbol.id)
            .filter(Suscripcion.usuario_id == usuario.id, Arbol.productor_id == solicitante.id)
            .first()
        )
        if not es_su_productor:
            registrar_evento("acceso_denegado", "advertencia", usuario=solicitante, detalle=f"perfil del usuario {usuario_id}")
            return {"status": "error", "mensaje": "No tienes permiso para ver este perfil."}

    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "telefono": usuario.telefono,
        "direccion": usuario.direccion,
        "rol": usuario.rol,
        "verificado": usuario.verificado
    }


@router.put("/api/perfil")
def actualizar_perfil(
    data: PerfilRequest,
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    cambios = data.dict(exclude_unset=True)

    # Se edita siempre la cuenta de la sesión. Antes se buscaba por el correo
    # enviado, y cualquiera podía cambiar la contraseña de otra cuenta.
    if data.email != usuario.email:
        registrar_evento("acceso_denegado", "advertencia", usuario=usuario, detalle=f"editar el perfil de {data.email}")
        return {"status": "error", "mensaje": "Solo puedes editar tu propio perfil."}
    if es_cuenta_demo(usuario):
        registrar_evento("cuenta_demo", "advertencia", usuario=usuario, detalle="modificar perfil")
        return {"status": "error", "mensaje": "La cuenta de demostración no se puede modificar."}

    cambia_password = bool(cambios.get("password"))
    if cambia_password and not (data.password_actual and verify_password(data.password_actual, usuario.password)):
        registrar_evento("cambio_password_fallido", "advertencia", usuario=usuario, detalle="contraseña actual incorrecta")
        return {"status": "error", "mensaje": "Para cambiar la contraseña ingresa tu contraseña actual."}

    # Actualizar campos
    if "nombre" in cambios:
        usuario.nombre = cambios["nombre"]
    if "telefono" in cambios:
        usuario.telefono = cambios["telefono"]
    if "direccion" in cambios:
        usuario.direccion = cambios["direccion"]
    if cambia_password:
        usuario.password = hash_password(cambios["password"])
        registrar_evento("cambio_password", "info", usuario=usuario)

    db.commit()
    db.refresh(usuario)

    respuesta_usuario = {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol,
        "telefono": usuario.telefono,
        "direccion": usuario.direccion
    }
    # Cambiar la contraseña invalida los tokens anteriores: se entrega uno nuevo
    if cambia_password:
        respuesta_usuario["token"] = crear_token(usuario)

    return {
        "status": "success",
        "mensaje": "Perfil actualizado correctamente.",
        "user": respuesta_usuario
    }


@router.delete("/api/usuario/{email}")
def eliminar_usuario(
    email: str,
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """Derecho a la eliminación de datos (Art. 20 Ley 21.719)"""
    # Solo el titular puede borrar su cuenta
    if email != usuario.email:
        registrar_evento("acceso_denegado", "advertencia", usuario=usuario, detalle=f"eliminar la cuenta {email}")
        return {"status": "error", "mensaje": "Solo puedes eliminar tu propia cuenta."}
    if es_cuenta_demo(usuario):
        registrar_evento("cuenta_demo", "advertencia", usuario=usuario, detalle="eliminar cuenta")
        return {"status": "error", "mensaje": "La cuenta de demostración no se puede eliminar."}

    # Eliminar suscripciones del usuario y las de sus árboles publicados
    db.query(Suscripcion).filter(Suscripcion.usuario_id == usuario.id).delete()
    ids_arboles = [a.id for a in db.query(Arbol.id).filter(Arbol.productor_id == usuario.id)]
    if ids_arboles:
        db.query(Suscripcion).filter(Suscripcion.arbol_id.in_(ids_arboles)).delete(synchronize_session=False)

    # Eliminar pedidos del usuario
    db.query(Pedido).filter(Pedido.cliente_id == usuario.id).delete()

    # Eliminar árboles publicados por el usuario (si es agricultor)
    db.query(Arbol).filter(Arbol.productor_id == usuario.id).delete()

    registrar_evento("cuenta_eliminada", "info", usuario=usuario)

    # Finalmente eliminar el usuario
    db.delete(usuario)
    db.commit()

    return {
        "status": "success",
        "mensaje": "Todos tus datos han sido eliminados correctamente."
    }
