"""Agro-Colab API - aplicacion FastAPI.

Arquitectura en capas: routers (HTTP) -> services (negocio) -> repositories
(datos) -> database (modelos y conexión). Este módulo arma la aplicación y es
el único que traduce los errores del dominio a códigos de estado HTTP.
"""

import logging
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import errores
from core import MODO_DESARROLLO, ip_cliente
from database import engine, Base, asegurar_columnas, migrar_cuentas_antiguas
from routers import admin, arboles, especies, monitoreo, pagos, pedidos, suscripciones, usuarios
from seguridad import peticion_actual, registrar_evento
from services.inicio import cargar_datos_iniciales

# La documentación interactiva describe todas las rutas: en producción solo se
# publica si AGROCOLAB_DOCS=1, por ejemplo para una presentación
DOCS_ABIERTOS = MODO_DESARROLLO or os.getenv("AGROCOLAB_DOCS", "") == "1"

app = FastAPI(
    title="Agro-Colab API",
    description="Adopción de árboles frutales y abastecimiento directo con trazabilidad",
    **({} if DOCS_ABIERTOS else {"docs_url": None, "redoc_url": None, "openapi_url": None}),
)

ORIGENES_PRODUCCION = ["https://arrobaaas.github.io"]
ORIGENES_LOCALES = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
# Frontend publicado en GitHub Pages; los orígenes locales solo en desarrollo
ORIGENES = ORIGENES_PRODUCCION + (ORIGENES_LOCALES if MODO_DESARROLLO else [])
# Tamaño máximo de una petición: ningún formulario de la API se acerca a esto
MAX_CUERPO_BYTES = 64 * 1024

# Nombres legibles de los campos para los mensajes de validación
CAMPOS = {
    "nombre": "el nombre", "email": "el correo", "password": "la contraseña",
    "rol": "el tipo de cuenta", "telefono": "el teléfono", "direccion": "la dirección",
    "comuna": "la comuna", "razon_social": "la razón social", "rut": "el RUT",
    "ubicacion": "la ubicación", "estimacion_cosecha": "la estimación de cosecha",
    "cupos_totales": "los cupos", "precio_mensual_clp": "el precio",
    "plan": "el plan", "tipo_suscripcion": "el tipo de suscripción",
    "tipo_destino": "el tipo de destino", "frecuencia_entrega": "la frecuencia",
    "codigo": "el código", "identificador": "el número del árbol",
    "estimacion_cosecha_kg": "la estimación de cosecha (kg)",
    "telefono_codigo": "el código de país", "codigo_postal": "el código postal",
    "acepta_datos": "la aceptación del tratamiento de datos", "acepta_terminos": "la aceptación de los términos",
}


# Un solo lugar decide qué código HTTP corresponde a cada error del dominio
CODIGOS_HTTP = {
    errores.CodigoIncorrecto: 400,
    errores.NoAutenticado: 401,
    errores.PagoRechazado: 402,
    errores.Prohibido: 403,
    errores.NoEncontrado: 404,
    errores.Conflicto: 409,
    errores.DatoInvalido: 422,
    errores.DemasiadosIntentos: 429,
    errores.ServicioNoDisponible: 503,
}

MENSAJES_HTTP = {404: "La ruta solicitada no existe.", 405: "Este verbo no está permitido en esta ruta."}


def respuesta_de_error(codigo: int, mensaje: str, estado: str = "error", **extra) -> JSONResponse:
    """Todos los errores de la API tienen la misma forma: {status, mensaje}."""
    return JSONResponse(status_code=codigo, content={"status": estado, "mensaje": mensaje, **extra})


@app.exception_handler(errores.ErrorDeNegocio)
async def error_de_negocio(request: Request, exc: errores.ErrorDeNegocio):
    return respuesta_de_error(CODIGOS_HTTP[type(exc)], exc.mensaje, exc.estado, **exc.extra)


@app.exception_handler(StarletteHTTPException)
async def error_http(request: Request, exc: StarletteHTTPException):
    """Errores que genera el propio framework, como una ruta inexistente."""
    return respuesta_de_error(exc.status_code, MENSAJES_HTTP.get(exc.status_code, str(exc.detail)))


@app.exception_handler(Exception)
async def error_inesperado(request: Request, exc: Exception):
    """Un fallo no previsto se registra, pero su detalle no se expone al cliente."""
    logging.getLogger("agrocolab").exception("Error no controlado en %s %s", request.method, request.url.path)
    respuesta = respuesta_de_error(500, "Ocurrió un error inesperado. Intenta nuevamente en unos minutos.")
    # Este manejador corre por fuera de los middlewares: sin esto, el navegador
    # bloquearía el error por CORS y la respuesta saldría sin cabeceras
    poner_cabeceras(respuesta, request)
    origen = request.headers.get("origin")
    if origen in ORIGENES:
        respuesta.headers["Access-Control-Allow-Origin"] = origen
        respuesta.headers["Vary"] = "Origin"
    return respuesta


@app.exception_handler(RequestValidationError)
async def error_de_validacion(request: Request, exc: RequestValidationError):
    """Devuelve el error en el formato {status, mensaje} que usa el frontend
    (el formato por defecto de FastAPI no se podía mostrar al usuario)."""
    errores = exc.errors()
    campo = str(errores[0]["loc"][-1]) if errores else ""
    tipo = errores[0].get("type", "") if errores else ""
    nombre = CAMPOS.get(campo, campo or "un dato")
    if tipo == "string_too_short" and campo == "password":
        mensaje = "La contraseña debe tener al menos 8 caracteres."
    elif tipo == "value_error":
        motivo = str(errores[0].get("msg", "")).removeprefix("Value error, ")
        mensaje = f"Revisa {nombre}: {motivo}."
        if "< o >" in motivo:
            # Ningún uso legítimo necesita < o > en estos campos: es casi
            # siempre un intento de XSS. No se guarda el valor: puede ser un dato personal
            registrar_evento("entrada_html", "critica", detalle=f"campo {campo}")
    else:
        mensaje = f"Revisa {nombre}: el valor no es válido."
    return respuesta_de_error(422, mensaje)


class CuerpoDemasiadoGrande(Exception):
    pass


class LimiteDeCuerpo:
    """Corta la lectura de una petición demasiado grande. FastAPI lee el cuerpo
    completo antes de validar y de aplicar el límite de intentos, y uvicorn no
    tiene un tope propio. Se cuenta lo leído porque una petición por partes
    (chunked) no declara su tamaño."""

    def __init__(self, siguiente, maximo: int):
        self.siguiente = siguiente
        self.maximo = maximo

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.siguiente(scope, receive, send)

        declarado = dict(scope["headers"]).get(b"content-length", b"")
        if declarado.isdigit() and int(declarado) > self.maximo:
            return await self._rechazar(scope, receive, send)

        leido = 0

        async def recibir():
            nonlocal leido
            mensaje = await receive()
            if mensaje["type"] == "http.request":
                leido += len(mensaje.get("body", b""))
                if leido > self.maximo:
                    raise CuerpoDemasiadoGrande()
            return mensaje

        await self.siguiente(scope, recibir, send)

    async def _rechazar(self, scope, receive, send):
        await respuesta_de_error(413, "La petición es demasiado grande.")(scope, receive, send)


def poner_cabeceras(respuesta, request: Request):
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["X-Frame-Options"] = "DENY"
    respuesta.headers["Referrer-Policy"] = "no-referrer"
    respuesta.headers["Strict-Transport-Security"] = "max-age=31536000"
    if request.url.path.startswith("/api/"):
        # Las respuestas traen datos personales: que no queden en cachés
        respuesta.headers["Cache-Control"] = "no-store"


app.add_middleware(LimiteDeCuerpo, maximo=MAX_CUERPO_BYTES)


@app.middleware("http")
async def cabeceras_de_seguridad(request: Request, call_next):
    # IP real y ruta disponibles para el registro de eventos de esta petición
    peticion_actual.set({"ip": ip_cliente(request), "ruta": f"{request.method} {request.url.path}"})
    respuesta = await call_next(request)
    poner_cabeceras(respuesta, request)
    return respuesta


# Permitir peticiones solo desde los orígenes conocidos del frontend. La sesión va
# en una cabecera y no en una cookie: no hacen falta credenciales de navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Monitoreo-Token"],
)

# Crear tablas y datos iniciales
Base.metadata.create_all(bind=engine)
asegurar_columnas()
migrar_cuentas_antiguas()
cargar_datos_iniciales()

app.include_router(especies.router)
app.include_router(arboles.router)
app.include_router(suscripciones.router)
app.include_router(usuarios.router)
app.include_router(pedidos.router)
app.include_router(pagos.router)
app.include_router(monitoreo.router)
app.include_router(admin.router)
