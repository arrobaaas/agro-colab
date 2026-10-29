"""Router de usuarios (registro, login, verificación, perfil y derechos de datos)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import random
import string

from core import (
    LoginRequest, RegistroRequest, VerificacionRequest, PerfilRequest,
    hash_password, verify_password, foto_de, get_db, MODO_DESARROLLO, limitar_por_ip, crear_token, usuario_actual,
)
from database import Usuario, Arbol, Suscripcion, Pedido, SessionLocal, es_hash_bcrypt

router = APIRouter()


@router.post("/api/register", dependencies=[Depends(limitar_por_ip(maximo=5, ventana_segundos=3600))])
def registrar_usuario(data: RegistroRequest, db: Session = Depends(get_db)):
    # Verificar si el email ya existe
    existente = db.query(Usuario).filter(Usuario.email == data.email).first()
    if existente:
        return {"status": "error", "mensaje": "El correo electrónico ya está registrado."}

    # Generar código de verificación de 6 dígitos
    codigo = ''.join(random.choices(string.digits, k=6))

    nuevo_usuario = Usuario(
        nombre=data.nombre,
        email=data.email,
        password=hash_password(data.password),
        rol=data.rol,
        telefono=data.telefono,
        direccion=data.direccion,
        verificado=0,
        codigo_verificacion=codigo,
        consentimiento_datos=1,
        fecha_consentimiento=datetime.now(),
        acepta_terminos=1
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    # Simular envío de correo (en producción, usar un servicio como SendGrid, Mailgun, etc.)
    print(f"\n{'='*50}")
    print(f"CORREO DE VERIFICACIÓN ENVIADO A: {data.email}")
    print(f"Código de verificación: {codigo}")
    print(f"{'='*50}\n")

    respuesta = {
        "status": "success",
        "mensaje": f"Usuario {nuevo_usuario.nombre} registrado correctamente. Revisa tu correo para verificar tu cuenta.",
        "user": {
            "id": nuevo_usuario.id,
            "nombre": nuevo_usuario.nombre,
            "email": nuevo_usuario.email,
            "rol": nuevo_usuario.rol
        }
    }
    # El código solo se expone en desarrollo para simular el envío por correo.
    # Nunca debe salir en producción.
    if MODO_DESARROLLO:
        respuesta["user"]["codigo_verificacion"] = codigo

    return respuesta


@router.post("/api/login", dependencies=[Depends(limitar_por_ip(maximo=8, ventana_segundos=300))])
def login(data: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(
        Usuario.email == data.email,
        Usuario.rol == data.rol
    ).first()

    if not usuario or not verify_password(data.password, usuario.password):
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
        usuario_respuesta["token"] = crear_token(usuario.id)

    return {
        "status": "success",
        "mensaje": f"Bienvenido/a {usuario.nombre}",
        "user": usuario_respuesta
    }


@router.post("/api/verificar-cuenta", dependencies=[Depends(limitar_por_ip(maximo=10, ventana_segundos=3600))])
def verificar_cuenta(data: VerificacionRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}

    if usuario.verificado:
        return {"status": "error", "mensaje": "La cuenta ya está verificada."}

    if usuario.codigo_verificacion != data.codigo:
        return {"status": "error", "mensaje": "Código de verificación incorrecto."}

    usuario.verificado = 1
    usuario.codigo_verificacion = None
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
        return {"status": "error", "mensaje": "Solo puedes editar tu propio perfil."}

    # Actualizar campos
    if "nombre" in cambios:
        usuario.nombre = cambios["nombre"]
    if "telefono" in cambios:
        usuario.telefono = cambios["telefono"]
    if "direccion" in cambios:
        usuario.direccion = cambios["direccion"]
    if "password" in cambios and cambios["password"]:
        usuario.password = hash_password(cambios["password"])

    db.commit()
    db.refresh(usuario)

    return {
        "status": "success",
        "mensaje": "Perfil actualizado correctamente.",
        "user": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol,
            "telefono": usuario.telefono,
            "direccion": usuario.direccion
        }
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
        return {"status": "error", "mensaje": "Solo puedes eliminar tu propia cuenta."}

    # Eliminar suscripciones del usuario y las de sus árboles publicados
    db.query(Suscripcion).filter(Suscripcion.usuario_id == usuario.id).delete()
    ids_arboles = [a.id for a in db.query(Arbol.id).filter(Arbol.productor_id == usuario.id)]
    if ids_arboles:
        db.query(Suscripcion).filter(Suscripcion.arbol_id.in_(ids_arboles)).delete(synchronize_session=False)

    # Eliminar pedidos del usuario
    db.query(Pedido).filter(Pedido.cliente_id == usuario.id).delete()

    # Eliminar árboles publicados por el usuario (si es agricultor)
    db.query(Arbol).filter(Arbol.productor_id == usuario.id).delete()

    # Finalmente eliminar el usuario
    db.delete(usuario)
    db.commit()

    return {
        "status": "success",
        "mensaje": "Todos tus datos han sido eliminados correctamente."
    }
