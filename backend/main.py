from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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

# ----------------- BASES DE DATOS SIMULADAS -----------------
# Agro-Colab tiene dos líneas de producto:
#   1. Adopción de árbol  -> se compra un cupo de un árbol (plan Básico/Intermedio/Premium).
#   2. Abastecimiento     -> se contrata una canasta de cosecha (plan Dúo/Familiar/B2B).
# Cada árbol declara su plan de adopción, y su stock es el número de cupos disponibles.

arboles_db = [
    {
        "id": 1,
        "nombre": "Palto Hass #104",
        "plan": "Básico",
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
        "plan": "Premium",
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
        "plan": "Intermedio",
        "tipo_suscripcion": "Compartido",
        "precio_mensual_clp": 8000,
        "cupos_totales": 3,
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

# ----------------- ENDPOINTS (RUTAS) -----------------

# 1. Rutas de Árboles
@app.get("/api/arboles")
def listar_arboles():
    return arboles_db

@app.post("/api/arboles")
def crear_arbol(data: ArbolRequest):
    nuevo_arbol = data.dict()
    nuevo_arbol["id"] = max([a["id"] for a in arboles_db], default=0) + 1
    nuevo_arbol["cupos_ocupados"] = 0
    arboles_db.append(nuevo_arbol)
    return {
        "status": "success",
        "mensaje": f"Árbol '{nuevo_arbol['nombre']}' publicado correctamente.",
        "arbol": nuevo_arbol
    }

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

@app.post("/api/cancelar-suscripcion")
def cancelar_suscripcion(data: SuscripcionRequest):
    for arbol in arboles_db:
        if arbol["id"] == data.tree_id:
            if arbol["cupos_ocupados"] > 0:
                arbol["cupos_ocupados"] -= 1
                return {
                    "status": "success",
                    "mensaje": f"Suscripción cancelada para {data.user_name} en {arbol['nombre']}.",
                    "arbol": arbol
                }
            return {"status": "error", "mensaje": "No hay suscriptores que cancelar."}
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

# 4. Rutas de Perfil de Usuario
class PerfilRequest(BaseModel):
    nombre: str
    email: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    password: Optional[str] = None

@app.put("/api/perfil")
def actualizar_perfil(data: PerfilRequest):
    cambios = data.dict(exclude_unset=True)
    # En un sistema real, aquí se actualizaría el usuario en la base de datos
    # Por ahora, retornamos el usuario actualizado simulado
    usuario_actualizado = {
        "nombre": cambios.get("nombre", "Usuario"),
        "email": cambios.get("email", "usuario@agrocolab.cl"),
        "rol": "comprador",
        "telefono": cambios.get("telefono", "+56 9 1234 5678"),
        "direccion": cambios.get("direccion", "Av. Los Aromos 1234")
    }
    return {
        "status": "success",
        "mensaje": "Perfil actualizado correctamente.",
        "user": usuario_actualizado
    }
