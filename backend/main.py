from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI(
    title="AgroColab API",
    description="Plataforma de Agricultura Colaborativa y Trazabilidad Logística"
)

# Permitir peticiones desde el frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- BASES DE DATOS SIMULADAS -----------------

arboles_db = [
    {
        "id": 1,
        "nombre": "Palto Hass #104",
        "tipo_suscripcion": "Compartido",
        "precio_mensual_clp": 12000,
        "cupos_totales": 5,
        "cupos_ocupados": 3,
        "estimacion_cosecha": "45 kg anuales",
        "ubicacion": "Valle del Aconcagua, Región de Valparaíso",
        "imagen": "https://images.unsplash.com/photo-1523049673857-eb18f1d7b578?auto=format&fit=crop&w=600&q=80",
        "productor": "Don Hernán Silva"
    },
    {
        "id": 2,
        "nombre": "Naranjo Valencia #22",
        "tipo_suscripcion": "Exclusivo",
        "precio_mensual_clp": 35000,
        "cupos_totales": 1,
        "cupos_ocupados": 0,
        "estimacion_cosecha": "80 kg anuales",
        "ubicacion": "Curicó, Región del Maule",
        "imagen": "https://images.unsplash.com/photo-1582979512210-99b6a53386f9?auto=format&fit=crop&w=600&q=80",
        "productor": "Familia Morales"
    },
    {
        "id": 3,
        "nombre": "Limonero Eureka #12",
        "tipo_suscripcion": "Compartido",
        "precio_mensual_clp": 8000,
        "cupos_totales": 4,
        "cupos_ocupados": 1,
        "estimacion_cosecha": "35 kg anuales",
        "ubicacion": "Mallarauco, Región Metropolitana",
        "imagen": "https://images.unsplash.com/photo-1590502593747-42a996133562?auto=format&fit=crop&w=600&q=80",
        "productor": "Cooperativa Agrícola Melipilla"
    }
]

USUARIOS_TEST = [
    {
        "email": "comprador@agrocolab.cl",
        "password": "123",
        "nombre": "Camila Soto",
        "rol": "comprador"
    },
    {
        "email": "agricultor@agrocolab.cl",
        "password": "123",
        "nombre": "Hernán Silva",
        "rol": "agricultor"
    }
]

pedidos_db = []

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

# ----------------- ENDPOINTS (RUTAS) -----------------

# 1. Rutas de Árboles
@app.get("/api/arboles")
def listar_arboles():
    return arboles_db

@app.post("/api/suscribir")
def suscribir(data: SuscripcionRequest):
    for arbol in arboles_db:
        if arbol["id"] == data.tree_id:
            if arbol["cupos_ocupados"] < arbol["cupos_totales"]:
                arbol["cupos_ocupados"] += 1
                return {
                    "status": "success",
                    "mensaje": f"¡Suscripción confirmada para {data.user_name} en {arbol['nombre']}!",
                    "arbol": arbol
                }
            return {"status": "error", "mensaje": "Cupos agotados para este árbol."}
    return {"status": "error", "mensaje": "Árbol no encontrado."}

# 2. Rutas de Autenticación (Login)
@app.post("/api/login")
def login(data: LoginRequest):
    for u in USUARIOS_TEST:
        if u["email"] == data.email and u["password"] == data.password and u["rol"] == data.rol:
            return {
                "status": "success",
                "mensaje": f"Bienvenido/a {u['nombre']}",
                "user": {
                    "nombre": u["nombre"],
                    "email": u["email"],
                    "rol": u["rol"]
                }
            }
    return {
        "status": "error",
        "mensaje": "Credenciales inválidas o el rol seleccionado no coincide."
    }

# 3. Rutas de Logística y Pedidos
@app.post("/api/pedidos")
def registrar_pedido(pedido: PedidoRequest):
    nuevo_pedido = pedido.dict()
    nuevo_pedido["id"] = len(pedidos_db) + 1
    nuevo_pedido["codigo_seguimiento"] = f"AGRO-{nuevo_pedido['id']:04d}"
    nuevo_pedido["fecha_registro"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    nuevo_pedido["estado_logistica"] = "En coordinación con huerto de origen"
    
    pedidos_db.append(nuevo_pedido)
    return {
        "status": "success",
        "mensaje": f"Plan contratado con éxito. Código de despacho: {nuevo_pedido['codigo_seguimiento']}",
        "pedido": nuevo_pedido
    }

@app.get("/api/pedidos")
def listar_pedidos():
    return pedidos_db
