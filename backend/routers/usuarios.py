"""Router de usuarios (registro, login, verificación, perfil y derechos de datos)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import random
import string

from core import (
    LoginRequest, RegistroRequest, VerificacionRequest, PerfilRequest,
    hash_password, verify_password, foto_de, get_db, MODO_DESARROLLO, limitar_por_ip,
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
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Obtiene el perfil público de un usuario (para que el agricultor lo vea)."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}

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
def actualizar_perfil(data: PerfilRequest, db: Session = Depends(get_db)):
    cambios = data.dict(exclude_unset=True)

    # Buscar usuario por email
    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}

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
def eliminar_usuario(email: str, db: Session = Depends(get_db)):
    """Derecho a la eliminación de datos (Art. 20 Ley 21.719)"""
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}

    # Eliminar suscripciones del usuario
    db.query(Suscripcion).filter(Suscripcion.usuario_id == usuario.id).delete()

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
