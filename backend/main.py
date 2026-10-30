"""Agro-Colab API - aplicacion FastAPI.

La aplicacion se compone de routers (catalogo, arboles, suscripciones, pedidos
y usuarios) e inyecta la logica de dominio desde el modulo `core`.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core import datos_iniciales, ip_cliente
from database import engine, Base, asegurar_columnas, migrar_cuentas_antiguas
from routers import arboles, especies, monitoreo, pagos, pedidos, suscripciones, usuarios
from seguridad import peticion_actual, registrar_evento

app = FastAPI(
    title="Agro-Colab API",
    description="Adopción de árboles frutales y abastecimiento directo con trazabilidad"
)

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
}


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
            # siempre un intento de XSS
            muestra = str(errores[0].get("input", ""))[:120]
            registrar_evento("entrada_html", "critica", detalle=f"campo {campo}: {muestra}")
    else:
        mensaje = f"Revisa {nombre}: el valor no es válido."
    return JSONResponse(status_code=422, content={"status": "error", "mensaje": mensaje})


@app.middleware("http")
async def cabeceras_de_seguridad(request: Request, call_next):
    # IP real y ruta disponibles para el registro de eventos de esta petición
    peticion_actual.set({"ip": ip_cliente(request), "ruta": f"{request.method} {request.url.path}"})
    respuesta = await call_next(request)
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["X-Frame-Options"] = "DENY"
    respuesta.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        # Las respuestas traen datos personales: que no queden en cachés
        respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


# Permitir peticiones solo desde los orígenes conocidos del frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://agro-colab.onrender.com",
        # Frontend publicado en GitHub Pages: sin este origen el navegador
        # bloquea todas las llamadas a la API desde la demo en línea.
        "https://arrobaaas.github.io",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Monitoreo-Token"],
)

# Crear tablas y datos iniciales
Base.metadata.create_all(bind=engine)
asegurar_columnas()
migrar_cuentas_antiguas()
datos_iniciales()

app.include_router(especies.router)
app.include_router(arboles.router)
app.include_router(suscripciones.router)
app.include_router(usuarios.router)
app.include_router(pedidos.router)
app.include_router(pagos.router)
app.include_router(monitoreo.router)
