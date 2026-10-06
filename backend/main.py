from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database import engine, SessionLocal, Base, Usuario, Arbol, Suscripcion, Pedido

app = FastAPI(
    title="Agro-Colab API",
    description="Adopción de árboles frutales y abastecimiento directo con trazabilidad"
)

# Permitir peticiones desde el frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear tablas y datos iniciales
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def datos_iniciales():
    db = SessionLocal()
    try:
        # Verificar si ya hay datos
        if db.query(Usuario).count() == 0:
            # Crear usuarios de prueba
            usuarios = [
                Usuario(nombre="Camila Soto", email="comprador@agrocolab.cl", password="123", rol="comprador"),
                Usuario(nombre="Hernán Silva", email="agricultor@agrocolab.cl", password="123", rol="agricultor")
            ]
            db.add_all(usuarios)
            db.commit()

        if db.query(Arbol).count() == 0:
            # Crear árboles de prueba
            arboles = [
                Arbol(
                    nombre="Palto Hass #104",
                    plan="Básico",
                    tipo_suscripcion="Compartido",
                    precio_mensual_clp=12000,
                    cupos_totales=5,
                    cupos_ocupados=3,
                    estimacion_cosecha="45 kg anuales",
                    ubicacion="Valle del Aconcagua, Región de Valparaíso",
                    imagen="https://images.unsplash.com/photo-1523049673857-eb18f1d7b578?auto=format&fit=crop&w=600&q=80",
                    productor_id=2
                ),
                Arbol(
                    nombre="Naranjo Valencia #22",
                    plan="Premium",
                    tipo_suscripcion="Exclusivo",
                    precio_mensual_clp=35000,
                    cupos_totales=1,
                    cupos_ocupados=0,
                    estimacion_cosecha="80 kg anuales",
                    ubicacion="Curicó, Región del Maule",
                    imagen="https://images.unsplash.com/photo-1582979512210-99b6a53386f9?auto=format&fit=crop&w=600&q=80",
                    productor_id=2
                ),
                Arbol(
                    nombre="Limonero Eureka #12",
                    plan="Intermedio",
                    tipo_suscripcion="Compartido",
                    precio_mensual_clp=8000,
                    cupos_totales=3,
                    cupos_ocupados=1,
                    estimacion_cosecha="35 kg anuales",
                    ubicacion="Mallarauco, Región Metropolitana",
                    imagen="https://images.unsplash.com/photo-1590502593747-42a996133562?auto=format&fit=crop&w=600&q=80",
                    productor_id=2
                )
            ]
            db.add_all(arboles)
            db.commit()
    finally:
        db.close()

datos_iniciales()

# ----------------- MODELOS DE DATOS (ESQUEMAS) -----------------

class SuscripcionRequest(BaseModel):
    user_name: str
    tree_id: int

class LoginRequest(BaseModel):
    email: str
    password: str
    rol: str

class PedidoRequest(BaseModel):
    plan_nombre: str
    monto_clp: int
    cliente_nombre: str
    telefono: str
    email: str
    tipo_destino: str  # "particular" o "comercial"
    razon_social: Optional[str] = None
    rut: Optional[str] = None
    direccion: str
    comuna: str
    frecuencia_entrega: str

class ArbolRequest(BaseModel):
    nombre: str
    ubicacion: str
    plan: str
    tipo_suscripcion: str
    cupos_totales: int
    precio_mensual_clp: int
    estimacion_cosecha: str
    imagen: str
    productor: str

class PerfilRequest(BaseModel):
    nombre: str
    email: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    password: Optional[str] = None

# ----------------- ENDPOINTS (RUTAS) -----------------

# 1. Rutas de Árboles
@app.get("/api/arboles")
def listar_arboles(db: SessionLocal = Depends(get_db)):
    arboles = db.query(Arbol).all()
    return [
        {
            "id": a.id,
            "nombre": a.nombre,
            "plan": a.plan,
            "tipo_suscripcion": a.tipo_suscripcion,
            "precio_mensual_clp": a.precio_mensual_clp,
            "cupos_totales": a.cupos_totales,
            "cupos_ocupados": a.cupos_ocupados,
            "estimacion_cosecha": a.estimacion_cosecha,
            "ubicacion": a.ubicacion,
            "imagen": a.imagen,
            "productor": a.productor.nombre if a.productor else None
        }
        for a in arboles
    ]

@app.post("/api/arboles")
def crear_arbol(data: ArbolRequest, db: SessionLocal = Depends(get_db)):
    # Buscar al productor por nombre
    productor = db.query(Usuario).filter(Usuario.nombre == data.productor).first()
    if not productor:
        return {"status": "error", "mensaje": "Productor no encontrado."}

    nuevo_arbol = Arbol(
        nombre=data.nombre,
        ubicacion=data.ubicacion,
        plan=data.plan,
        tipo_suscripcion=data.tipo_suscripcion,
        cupos_totales=data.cupos_totales,
        cupos_ocupados=0,
        precio_mensual_clp=data.precio_mensual_clp,
        estimacion_cosecha=data.estimacion_cosecha,
        imagen=data.imagen,
        productor_id=productor.id
    )
    db.add(nuevo_arbol)
    db.commit()
    db.refresh(nuevo_arbol)
    return {
        "status": "success",
        "mensaje": f"Árbol '{nuevo_arbol.nombre}' publicado correctamente.",
        "arbol": {
            "id": nuevo_arbol.id,
            "nombre": nuevo_arbol.nombre,
            "plan": nuevo_arbol.plan,
            "tipo_suscripcion": nuevo_arbol.tipo_suscripcion,
            "precio_mensual_clp": nuevo_arbol.precio_mensual_clp,
            "cupos_totales": nuevo_arbol.cupos_totales,
            "cupos_ocupados": nuevo_arbol.cupos_ocupados,
            "estimacion_cosecha": nuevo_arbol.estimacion_cosecha,
            "ubicacion": nuevo_arbol.ubicacion,
            "imagen": nuevo_arbol.imagen,
            "productor": productor.nombre
        }
    }

@app.post("/api/suscribir")
def suscribir(data: SuscripcionRequest, db: SessionLocal = Depends(get_db)):
    arbol = db.query(Arbol).filter(Arbol.id == data.tree_id).first()
    if not arbol:
        return {"status": "error", "mensaje": "Árbol no encontrado."}

    if arbol.cupos_ocupados < arbol.cupos_totales:
        arbol.cupos_ocupados += 1

        # Crear registro de suscripción
        suscripcion = Suscripcion(usuario_id=1, arbol_id=data.tree_id)  # usuario_id temporal
        db.add(suscripcion)
        db.commit()

        return {
            "status": "success",
            "mensaje": f"¡Suscripción confirmada para {data.user_name} en {arbol.nombre}!",
            "arbol": {
                "id": arbol.id,
                "nombre": arbol.nombre,
                "plan": arbol.plan,
                "tipo_suscripcion": arbol.tipo_suscripcion,
                "precio_mensual_clp": arbol.precio_mensual_clp,
                "cupos_totales": arbol.cupos_totales,
                "cupos_ocupados": arbol.cupos_ocupados,
                "estimacion_cosecha": arbol.estimacion_cosecha,
                "ubicacion": arbol.ubicacion,
                "imagen": arbol.imagen,
                "productor": arbol.productor.nombre if arbol.productor else None
            }
        }
    return {"status": "error", "mensaje": "Cupos agotados para este árbol."}

@app.put("/api/arboles/{arbol_id}")
def actualizar_arbol(arbol_id: int, data: ArbolRequest, db: SessionLocal = Depends(get_db)):
    arbol = db.query(Arbol).filter(Arbol.id == arbol_id).first()
    if not arbol:
        return {"status": "error", "mensaje": "Árbol no encontrado."}

    arbol.nombre = data.nombre
    arbol.ubicacion = data.ubicacion
    arbol.plan = data.plan
    arbol.tipo_suscripcion = data.tipo_suscripcion
    arbol.cupos_totales = data.cupos_totales
    arbol.precio_mensual_clp = data.precio_mensual_clp
    arbol.estimacion_cosecha = data.estimacion_cosecha
    arbol.imagen = data.imagen

    db.commit()
    db.refresh(arbol)

    return {
        "status": "success",
        "mensaje": f"Árbol '{arbol.nombre}' actualizado correctamente.",
        "arbol": {
            "id": arbol.id,
            "nombre": arbol.nombre,
            "plan": arbol.plan,
            "tipo_suscripcion": arbol.tipo_suscripcion,
            "precio_mensual_clp": arbol.precio_mensual_clp,
            "cupos_totales": arbol.cupos_totales,
            "cupos_ocupados": arbol.cupos_ocupados,
            "estimacion_cosecha": arbol.estimacion_cosecha,
            "ubicacion": arbol.ubicacion,
            "imagen": arbol.imagen,
            "productor": arbol.productor.nombre if arbol.productor else None
        }
    }

@app.delete("/api/arboles/{arbol_id}")
def eliminar_arbol(arbol_id: int, db: SessionLocal = Depends(get_db)):
    arbol = db.query(Arbol).filter(Arbol.id == arbol_id).first()
    if not arbol:
        return {"status": "error", "mensaje": "Árbol no encontrado."}

    db.delete(arbol)
    db.commit()
    return {"status": "success", "mensaje": f"Árbol '{arbol.nombre}' eliminado correctamente."}

@app.post("/api/cancelar-suscripcion")
def cancelar_suscripcion(data: SuscripcionRequest, db: SessionLocal = Depends(get_db)):
    arbol = db.query(Arbol).filter(Arbol.id == data.tree_id).first()
    if not arbol:
        return {"status": "error", "mensaje": "Árbol no encontrado."}

    if arbol.cupos_ocupados > 0:
        arbol.cupos_ocupados -= 1
        db.commit()

        return {
            "status": "success",
            "mensaje": f"Suscripción cancelada para {data.user_name} en {arbol.nombre}.",
            "arbol": {
                "id": arbol.id,
                "nombre": arbol.nombre,
                "plan": arbol.plan,
                "tipo_suscripcion": arbol.tipo_suscripcion,
                "precio_mensual_clp": arbol.precio_mensual_clp,
                "cupos_totales": arbol.cupos_totales,
                "cupos_ocupados": arbol.cupos_ocupados,
                "estimacion_cosecha": arbol.estimacion_cosecha,
                "ubicacion": arbol.ubicacion,
                "imagen": arbol.imagen,
                "productor": arbol.productor.nombre if arbol.productor else None
            }
        }
    return {"status": "error", "mensaje": "No hay suscriptores que cancelar."}

# 2. Rutas de Autenticación (Login y Registro)
class RegistroRequest(BaseModel):
    nombre: str
    email: str
    password: str
    rol: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None

import random
import string

@app.post("/api/register")
def registrar_usuario(data: RegistroRequest, db: SessionLocal = Depends(get_db)):
    # Verificar si el email ya existe
    existente = db.query(Usuario).filter(Usuario.email == data.email).first()
    if existente:
        return {"status": "error", "mensaje": "El correo electrónico ya está registrado."}

    # Generar código de verificación de 6 dígitos
    codigo = ''.join(random.choices(string.digits, k=6))

    nuevo_usuario = Usuario(
        nombre=data.nombre,
        email=data.email,
        password=data.password,
        rol=data.rol,
        telefono=data.telefono,
        direccion=data.direccion,
        verificado=0,
        codigo_verificacion=codigo
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
            "nombre": nuevo_usuario.nombre,
            "email": nuevo_usuario.email,
            "rol": nuevo_usuario.rol
        },
        "codigo_verificacion": codigo  # En producción, esto NO se retornaría
    }

class VerificacionRequest(BaseModel):
    email: str
    codigo: str

@app.post("/api/verificar-cuenta")
def verificar_cuenta(data: VerificacionRequest, db: SessionLocal = Depends(get_db)):
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

@app.post("/api/login")
def login(data: LoginRequest, db: SessionLocal = Depends(get_db)):
    usuario = db.query(Usuario).filter(
        Usuario.email == data.email,
        Usuario.password == data.password,
        Usuario.rol == data.rol
    ).first()

    if usuario:
        return {
            "status": "success",
            "mensaje": f"Bienvenido/a {usuario.nombre}",
            "user": {
                "nombre": usuario.nombre,
                "email": usuario.email,
                "rol": usuario.rol,
                "verificado": usuario.verificado,
                "codigo_verificacion": usuario.codigo_verificacion
            }
        }
    return {
        "status": "error",
        "mensaje": "Credenciales inválidas o el rol seleccionado no coincide."
    }

# 3. Rutas de Logística y Pedidos
@app.post("/api/pedidos")
def registrar_pedido(pedido: PedidoRequest, db: SessionLocal = Depends(get_db)):
    nuevo_pedido = Pedido(
        cliente_id=1,  # temporal
        plan_nombre=pedido.plan_nombre,
        monto_clp=pedido.monto_clp,
        tipo_destino=pedido.tipo_destino,
        razon_social=pedido.razon_social,
        rut=pedido.rut,
        direccion=pedido.direccion,
        comuna=pedido.comuna,
        frecuencia_entrega=pedido.frecuencia_entrega,
        codigo_seguimiento=f"AGRO-{db.query(Pedido).count() + 1:04d}",
        estado_logistica="En coordinación con huerto de origen"
    )
    db.add(nuevo_pedido)
    db.commit()
    db.refresh(nuevo_pedido)

    return {
        "status": "success",
        "mensaje": f"Plan contratado con éxito. Código de despacho: {nuevo_pedido.codigo_seguimiento}",
        "pedido": {
            "id": nuevo_pedido.id,
            "plan_nombre": nuevo_pedido.plan_nombre,
            "monto_clp": nuevo_pedido.monto_clp,
            "tipo_destino": nuevo_pedido.tipo_destino,
            "direccion": nuevo_pedido.direccion,
            "comuna": nuevo_pedido.comuna,
            "frecuencia_entrega": nuevo_pedido.frecuencia_entrega,
            "codigo_seguimiento": nuevo_pedido.codigo_seguimiento,
            "fecha_registro": nuevo_pedido.fecha_registro.strftime("%d/%m/%Y %H:%M"),
            "estado_logistica": nuevo_pedido.estado_logistica
        }
    }

@app.get("/api/pedidos")
def listar_pedidos(db: SessionLocal = Depends(get_db)):
    pedidos = db.query(Pedido).all()
    return [
        {
            "id": p.id,
            "plan_nombre": p.plan_nombre,
            "monto_clp": p.monto_clp,
            "tipo_destino": p.tipo_destino,
            "direccion": p.direccion,
            "comuna": p.comuna,
            "frecuencia_entrega": p.frecuencia_entrega,
            "codigo_seguimiento": p.codigo_seguimiento,
            "fecha_registro": p.fecha_registro.strftime("%d/%m/%Y %H:%M"),
            "estado_logistica": p.estado_logistica
        }
        for p in pedidos
    ]

# 4. Rutas de Perfil de Usuario
@app.put("/api/perfil")
def actualizar_perfil(data: PerfilRequest, db: SessionLocal = Depends(get_db)):
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
        usuario.password = cambios["password"]

    db.commit()
    db.refresh(usuario)

    return {
        "status": "success",
        "mensaje": "Perfil actualizado correctamente.",
        "user": {
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol,
            "telefono": usuario.telefono,
            "direccion": usuario.direccion
        }
    }
