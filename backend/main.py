"""Agro-Colab API - aplicacion FastAPI.

La aplicacion se compone de routers (catalogo, arboles, suscripciones, pedidos
y usuarios) e inyecta la logica de dominio desde el modulo `core`.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core import datos_iniciales
from database import engine, Base, asegurar_columnas, migrar_cuentas_antiguas
from routers import arboles, especies, pedidos, suscripciones, usuarios

app = FastAPI(
    title="Agro-Colab API",
    description="Adopción de árboles frutales y abastecimiento directo con trazabilidad"
)

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
    allow_methods=["*"],
    allow_headers=["*"],
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
