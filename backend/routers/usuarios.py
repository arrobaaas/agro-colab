"""Router de usuarios (registro, login, verificación, perfil y derechos de datos)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import random
import string

from core import (
    LoginRequest, RegistroRequest, VerificacionRequest, PerfilRequest,
    hash_password, verify_password, foto_de, get_db,
)
from database import Usuario, Arbol, Suscripcion, Pedido, SessionLocal, es_hash_bcrypt

router = APIRouter()


@router.post("/api/register")
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

    return {
        "status": "success",
        "mensaje": f"Usuario {nuevo_usuario.nombre} registrado correctamente. Revisa tu correo para verificar tu cuenta.",
        "user": {
            "id": nuevo_usuario.id,
            "nombre": nuevo_usuario.nombre,
            "email": nuevo_usuario.email,
            "rol": nuevo_usuario.rol
        },
        "codigo_verificacion": codigo  # En producción, esto NO se retornaría
    }


@router.post("/api/login")
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

    return {
        "status": "success",
        "mensaje": f"Bienvenido/a {usuario.nombre}",
        "user": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol,
            "verificado": usuario.verificado,
            "codigo_verificacion": usuario.codigo_verificacion
        }
    }


@router.post("/api/verificar-cuenta")
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


@router.get("/api/admin/reiniciar-bd")
def reiniciar_bd():
    """Reinicia la base de datos con los datos iniciales (para desarrollo)"""
    db = SessionLocal()
    try:
        # Eliminar datos existentes
        db.query(Suscripcion).delete()
        db.query(Pedido).delete()
        db.query(Arbol).delete()
        db.query(Usuario).delete()
        db.commit()

        # Crear usuarios de prueba con contraseñas hasheadas
        usuarios = [
            Usuario(nombre="Camila Soto", email="comprador@agrocolab.cl", password=hash_password("123"), rol="comprador", verificado=1, consentimiento_datos=1, fecha_consentimiento=datetime.now(), acepta_terminos=1),
            Usuario(nombre="Hernán Silva", email="agricultor@agrocolab.cl", password=hash_password("123"), rol="agricultor", verificado=1, consentimiento_datos=1, fecha_consentimiento=datetime.now(), acepta_terminos=1)
        ]
        db.add_all(usuarios)
        db.commit()

        # Crear árboles de prueba
        arboles = [
            Arbol(nombre="Palto Hass #104", especie="palto_hass", identificador="#104", plan="Básico", tipo_suscripcion="Compartido", precio_mensual_clp=12000, cupos_totales=5, cupos_ocupados=0, estimacion_cosecha="45 kg anuales", ubicacion="Valle del Aconcagua, Región de Valparaíso", imagen=foto_de("palto_hass", 0), imagen_origen="galeria", productor_id=2),
            Arbol(nombre="Naranjo Valencia #22", especie="naranjo_valencia", identificador="#22", plan="Premium", tipo_suscripcion="Exclusivo", precio_mensual_clp=35000, cupos_totales=1, cupos_ocupados=0, estimacion_cosecha="80 kg anuales", ubicacion="Curicó, Región del Maule", imagen=foto_de("naranjo_valencia", 0), imagen_origen="galeria", productor_id=2),
            Arbol(nombre="Limonero Eureka #12", especie="limonero_eureka", identificador="#12", plan="Intermedio", tipo_suscripcion="Compartido", precio_mensual_clp=8000, cupos_totales=3, cupos_ocupados=0, estimacion_cosecha="35 kg anuales", ubicacion="Mallarauco, Región Metropolitana", imagen=foto_de("limonero_eureka", 0), imagen_origen="galeria", productor_id=2)
        ]
        db.add_all(arboles)
        db.commit()

        # Sin suscripciones de prueba: los cupos arrancan en 0 y se llenan
        # cuando alguien adopta un árbol de verdad desde el catálogo.

        return {"status": "success", "mensaje": "Base de datos reiniciada correctamente."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}
    finally:
        db.close()
