"""Logica de dominio y utilidades compartidas del backend Agro-Colab.

Centraliza la configuración de base de datos, los datos iniciales, los
modelos Pydantic de entrada y las funciones de negocio/serialización que
eran compartidas dentro de la aplicacion FastAPI.
"""

from typing import Optional
from datetime import datetime

import os
import time
import hmac
import hashlib
import secrets
from collections import defaultdict

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import (
    engine, SessionLocal, Base, Usuario, Arbol, Suscripcion, Pedido,
    hash_password, verify_password, asegurar_columnas, migrar_cuentas_antiguas,
)
from catalogo import (
    CATALOGO_ESPECIES, listar_especies, buscar_especie, fotos_permitidas,
    componer_nombre, normalizar_identificador, foto_de,
)


# ----------------- SEGURIDAD -----------------

# En desarrollo local se permiten respuestas que ayudan a simular la verificación
# de cuenta (el código se imprime y se devuelve para poder probar el flujo).
# En producción jamás se debe exponer el código de verificación.
MODO_DESARROLLO = os.getenv("AGROCOLAB_MOD_MODE", "produccion").lower() == "desarrollo"

_intentos_por_ip: dict = defaultdict(list)

def _limitar_intento(ip: str, maximo: int, ventana_segundos: int) -> bool:
    """Registra un intento fallido-ish de autenticación y decide si se permite.
    Es un contador simple en memoria por IP (suficiente para este proyecto)."""
    ahora = time.monotonic()
    ventana = [t for t in _intentos_por_ip.get(ip, []) if ahora - t < ventana_segundos]
    if len(ventana) >= maximo:
        return False
    _intentos_por_ip[ip] = ventana + [ahora]
    return True

def limitar_por_ip(maximo: int = 10, ventana_segundos: int = 300):
    """Dependencia de FastAPI que aplica rate limiting a una ruta."""
    def _limiter(request: Request):
        ip = request.client.host if request.client else "0.0.0.0"
        if not _limitar_intento(ip, maximo, ventana_segundos):
            raise HTTPException(status_code=429, detail={"status": "error", "mensaje": "Demasiados intentos. Intenta más tarde."})
        return None
    return _limiter


# ----------------- TOKENS DE SESIÓN -----------------
# Token firmado con HMAC: "<usuario_id>.<expiracion>.<firma>". Sin él, cualquiera
# podía actuar en nombre de otro usuario con solo enviar su id en la petición.
# En producción AGROCOLAB_SECRET debe estar definido; si no, se genera uno al
# arrancar y las sesiones se invalidan en cada reinicio del servidor.

SECRETO_TOKENS = os.getenv("AGROCOLAB_SECRET") or secrets.token_hex(32)
DURACION_TOKEN_SEGUNDOS = 7 * 24 * 3600

def _firmar(carga: str) -> str:
    return hmac.new(SECRETO_TOKENS.encode(), carga.encode(), hashlib.sha256).hexdigest()

def crear_token(usuario_id: int) -> str:
    expira = int(time.time()) + DURACION_TOKEN_SEGUNDOS
    carga = f"{usuario_id}.{expira}"
    return f"{carga}.{_firmar(carga)}"

def leer_token(token: str) -> Optional[int]:
    """Devuelve el id del usuario si el token es válido y no ha expirado."""
    try:
        usuario_id, expira, firma = token.split(".")
        if not hmac.compare_digest(firma, _firmar(f"{usuario_id}.{expira}")):
            return None
        if int(expira) < time.time():
            return None
        return int(usuario_id)
    except (ValueError, AttributeError):
        return None


def _no_autorizado(mensaje: str, codigo: int = 401):
    return HTTPException(status_code=codigo, detail={"status": "error", "mensaje": mensaje})


# ----------------- SESIÓN / BASE DE DATOS -----------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def usuario_actual(request: Request, db: Session = Depends(get_db)) -> Usuario:
    """Dependencia de FastAPI: usuario autenticado según el header Authorization."""
    cabecera = request.headers.get("Authorization", "")
    token = cabecera[7:] if cabecera.startswith("Bearer ") else ""
    usuario_id = leer_token(token) if token else None
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first() if usuario_id else None
    if not usuario:
        raise _no_autorizado("Tu sesión expiró. Inicia sesión nuevamente.")
    return usuario


def exigir_mismo_usuario(usuario: Usuario, usuario_id: int):
    """Corta la petición si el usuario autenticado no es el dueño del recurso."""
    if usuario.id != usuario_id:
        raise _no_autorizado("No tienes permiso para ver estos datos.", 403)


def datos_iniciales():
    db = SessionLocal()
    try:
        # Verificar si ya hay datos
        if db.query(Usuario).count() == 0:
            # Crear usuarios de prueba (contraseña hasheada con bcrypt).
            usuarios = [
                Usuario(
                    nombre="Camila Soto", email="comprador@agrocolab.cl",
                    password=hash_password("123"), rol="comprador", verificado=1,
                    consentimiento_datos=1, fecha_consentimiento=datetime.now(),
                    acepta_terminos=1,
                ),
                Usuario(
                    nombre="Hernán Silva", email="agricultor@agrocolab.cl",
                    password=hash_password("123"), rol="agricultor", verificado=1,
                    consentimiento_datos=1, fecha_consentimiento=datetime.now(),
                    acepta_terminos=1,
                ),
            ]
            db.add_all(usuarios)
            db.commit()

        if db.query(Arbol).count() == 0:
            # Crear árboles de prueba (con fotos del catálogo de especies)
            arboles = [
                Arbol(
                    nombre="Palto Hass #104",
                    especie="palto_hass",
                    identificador="#104",
                    plan="Básico",
                    tipo_suscripcion="Compartido",
                    precio_mensual_clp=12000,
                    cupos_totales=5,
                    cupos_ocupados=0,
                    estimacion_cosecha="45 kg anuales",
                    ubicacion="Valle del Aconcagua, Región de Valparaíso",
                    imagen=foto_de("palto_hass", 0),
                    imagen_origen="galeria",
                    productor_id=2
                ),
                Arbol(
                    nombre="Naranjo Valencia #22",
                    especie="naranjo_valencia",
                    identificador="#22",
                    plan="Premium",
                    tipo_suscripcion="Exclusivo",
                    precio_mensual_clp=35000,
                    cupos_totales=1,
                    cupos_ocupados=0,
                    estimacion_cosecha="80 kg anuales",
                    ubicacion="Curicó, Región del Maule",
                    imagen=foto_de("naranjo_valencia", 0),
                    imagen_origen="galeria",
                    productor_id=2
                ),
                Arbol(
                    nombre="Limonero Eureka #12",
                    especie="limonero_eureka",
                    identificador="#12",
                    plan="Intermedio",
                    tipo_suscripcion="Compartido",
                    precio_mensual_clp=8000,
                    cupos_totales=3,
                    cupos_ocupados=0,
                    estimacion_cosecha="35 kg anuales",
                    ubicacion="Mallarauco, Región Metropolitana",
                    imagen=foto_de("limonero_eureka", 0),
                    imagen_origen="galeria",
                    productor_id=2
                ),
            ]
            db.add_all(arboles)
            db.commit()
    finally:
        db.close()


# datos_iniciales() no se llama aquí: al importar core.py las tablas todavía
# no existen. main.py la ejecuta después de create_all().

# ----------------- MODELOS DE DATOS (ESQUEMAS) -----------------

class SuscripcionRequest(BaseModel):
    # El usuario sale del token de sesión; el cuerpo solo indica el árbol
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
    cliente_id: Optional[int] = None  # ignorado: el cliente sale de la sesión
    tipo_destino: str  # "particular" o "comercial"
    razon_social: Optional[str] = None
    rut: Optional[str] = None
    direccion: str
    comuna: str
    frecuencia_entrega: str
    tipo: str = "abastecimiento"  # "abastecimiento" o "arbol"
    arbol_id: Optional[int] = None

class LogisticaRequest(BaseModel):
    """Datos de despacho que se pueden modificar en un pedido existente."""
    tipo_destino: str
    razon_social: Optional[str] = None
    rut: Optional[str] = None
    direccion: str
    comuna: str
    frecuencia_entrega: str

class ArbolRequest(BaseModel):
    nombre: Optional[str] = None  # se compone desde especie + identificador
    especie: str
    identificador: Optional[str] = None
    ubicacion: str
    plan: str
    tipo_suscripcion: str
    cupos_totales: int
    precio_mensual_clp: int
    estimacion_cosecha: str
    imagen: str
    productor: Optional[str] = None  # ignorado: el productor sale de la sesión

class PerfilRequest(BaseModel):
    nombre: str
    email: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    password: Optional[str] = None

class RegistroRequest(BaseModel):
    nombre: str
    email: str
    password: str
    rol: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None

class VerificacionRequest(BaseModel):
    email: str
    codigo: str


# ----------------- VALIDACIÓN DE ESPECIES E IMAGEN -----------------

def validar_imagen(imagen: str, especie_id: str):
    """Revisa la imagen enviada por el agricultor.

    El catálogo curado es la única fuente de imágenes: así el comprador nunca ve
    una foto que no corresponda al árbol que está adoptando. La validación se
    hace en el servidor, no solo en el formulario.

    Devuelve (imagen, origen, error).
    """
    if not imagen or not imagen.strip():
        return None, None, "Debes elegir una imagen del árbol."

    valor = imagen.strip()

    if valor.startswith("data:"):
        return None, None, "Por ahora las fotos deben elegirse del catálogo de la especie."

    if valor in fotos_permitidas(especie_id):
        return valor, "galeria", None

    return None, None, "La imagen elegida no corresponde a la especie seleccionada."


def especie_de_arbol(arbol) -> Optional[str]:
    """Especie de un árbol. Los árboles antiguos se deducen del nombre."""
    if arbol.especie:
        return arbol.especie
    nombre = (arbol.nombre or "").lower()
    for especie in CATALOGO_ESPECIES:
        if nombre.startswith(especie["nombre"].lower()):
            return especie["id"]
    return None


def identificador_de_arbol(arbol) -> Optional[str]:
    """Identificador del árbol dentro del huerto (ej: '#104')."""
    if arbol.identificador:
        return arbol.identificador
    especie = buscar_especie(especie_de_arbol(arbol))
    if not especie:
        return None
    nombre = arbol.nombre or ""
    return nombre[len(especie["nombre"]):].strip() or None


def cupos_ocupados_de(arbol, db) -> int:
    """Cupos realmente ocupados: cuenta las suscripciones registradas.

    El contador guardado en la tabla se puede desincronizar (por ejemplo, si la
    base se creó con contadores fijos y sin suscripciones reales), y ahí el
    panel del agricultor anuncia suscriptores que no existen. La fuente de
    verdad son siempre las filas de la tabla suscripciones.
    """
    return db.query(Suscripcion).filter(Suscripcion.arbol_id == arbol.id).count()


def serializar_arbol(arbol, db) -> dict:
    """Representación uniforme de un árbol para la API."""
    especie_id = especie_de_arbol(arbol)
    especie = buscar_especie(especie_id)
    return {
        "id": arbol.id,
        "nombre": arbol.nombre,
        "especie": especie_id,
        "especie_nombre": especie["nombre"] if especie else None,
        "identificador": identificador_de_arbol(arbol),
        "plan": arbol.plan,
        "tipo_suscripcion": arbol.tipo_suscripcion,
        "precio_mensual_clp": arbol.precio_mensual_clp,
        "cupos_totales": arbol.cupos_totales,
        "cupos_ocupados": cupos_ocupados_de(arbol, db),
        "estimacion_cosecha": arbol.estimacion_cosecha,
        "ubicacion": arbol.ubicacion,
        "imagen": arbol.imagen,
        "imagen_origen": arbol.imagen_origen or "galeria",
        "productor": arbol.productor.nombre if arbol.productor else None,
        "productor_id": arbol.productor_id,
    }
