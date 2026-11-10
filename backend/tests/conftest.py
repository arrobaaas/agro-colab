"""Configuración común de las pruebas.

Antes de importar la aplicación se fija el entorno: una base temporal
(SQLite, o PostgreSQL con PRUEBAS_DB_URL; nunca la real), modo desarrollo (los códigos de verificación
llegan en la respuesta en vez de por correo) y un secreto fijo para los
tokens. Sin BREVO_API_KEY no se envía ningún correo real.
"""

import itertools
import os
import sys
import tempfile

import pytest

_carpeta = tempfile.mkdtemp(prefix="agrocolab-pruebas-")
# PRUEBAS_DB_URL permite correrlas contra PostgreSQL (así lo hace la
# integración continua); sin ella se usa una base SQLite temporal
os.environ["AGROCOLAB_DB_URL"] = os.getenv("PRUEBAS_DB_URL") or f"sqlite:///{os.path.join(_carpeta, 'pruebas.db')}"
os.environ["AGROCOLAB_MOD_MODE"] = "desarrollo"
os.environ["AGROCOLAB_SECRET"] = "secreto-solo-para-pruebas"
os.environ.pop("BREVO_API_KEY", None)
os.environ.pop("CORREO_REMITENTE", None)
os.environ.pop("ALERTA_CORREO", None)
os.environ.pop("ALERTA_WEBHOOK_URL", None)
# Cuenta de administrador de las pruebas (en producción la definen estas
# mismas variables en Render)
ADMIN_EMAIL = "admin@pruebas.cl"
ADMIN_PASSWORD = "clave-admin-de-pruebas"
os.environ["ADMIN_EMAIL"] = ADMIN_EMAIL
os.environ["ADMIN_PASSWORD"] = ADMIN_PASSWORD

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from services import arboles as servicio_arboles, pagos as servicio_pagos, pedidos as servicio_pedidos  # noqa: E402

# Las pruebas comparten sesiones durante toda la ejecución: estos topes se
# comprueban por separado en test_auditoria.py
servicio_arboles.PUBLICACIONES_POR_HORA = 10_000
servicio_arboles.MAX_ARBOLES_POR_PRODUCTOR = 10_000
servicio_pagos.INTENTOS_POR_USUARIO = 10_000
servicio_pedidos.PEDIDOS_POR_HORA = 10_000

_ips = itertools.count(1)
_correos = itertools.count(1)

TARJETA_OK = "4242 4242 4242 4242"
TARJETA_SIN_FONDOS = "4000 0000 0000 0002"
CONSENTIMIENTO = {"acepta_datos": True, "acepta_terminos": True}


@pytest.fixture
def cliente():
    """Cliente HTTP con una IP propia: los límites de intentos se cuentan
    por IP, así cada prueba parte con su contador en cero."""
    n = next(_ips)
    with TestClient(main.app, headers={"X-Forwarded-For": f"10.0.{n // 250}.{n % 250 + 1}"}) as c:
        yield c


def login(cliente, email, password="123", rol="comprador"):
    r = cliente.post("/api/login", json={"email": email, "password": password, "rol": rol}).json()
    assert r["status"] == "success", r
    return r["user"]["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def _tokens_demo():
    """Sesiones compartidas por toda la ejecución: cuentas reales de cada rol, las
    cuentas demo (lo demo y lo real no se mezclan) y el administrador."""
    with TestClient(main.app, headers={"X-Forwarded-For": "10.255.0.1"}) as c:
        return {
            "comprador": registrar(c, "comprador")[2],
            "agricultor": registrar(c, "agricultor")[2],
            "comprador_demo": login(c, "comprador@agrocolab.cl"),
            "agricultor_demo": login(c, "agricultor@agrocolab.cl", rol="agricultor"),
            "admin": login(c, ADMIN_EMAIL, ADMIN_PASSWORD),
        }


@pytest.fixture
def token_comprador(_tokens_demo):
    return _tokens_demo["comprador"]


@pytest.fixture
def token_agricultor(_tokens_demo):
    return _tokens_demo["agricultor"]


@pytest.fixture
def token_comprador_demo(_tokens_demo):
    return _tokens_demo["comprador_demo"]


@pytest.fixture
def token_agricultor_demo(_tokens_demo):
    return _tokens_demo["agricultor_demo"]


@pytest.fixture
def token_admin(_tokens_demo):
    return _tokens_demo["admin"]


def registrar(cliente, rol):
    """Registra y verifica una cuenta nueva. Devuelve (email, password, token)."""
    email = f"prueba{next(_correos)}@ejemplo.cl"
    password = "clave-segura-1"
    r = cliente.post("/api/register", json={
        "nombre": "Persona de Prueba", "email": email, "password": password, "rol": rol, **CONSENTIMIENTO,
    }).json()
    assert r["status"] == "success", r
    codigo = r["user"]["codigo_verificacion"]
    assert cliente.post("/api/verificar-cuenta", json={"email": email, "codigo": codigo, "password": password}).json()["status"] == "success"
    return email, password, login(cliente, email, password, rol)


@pytest.fixture
def nuevo_comprador(cliente):
    return registrar(cliente, "comprador")


@pytest.fixture
def nuevo_agricultor(cliente):
    return registrar(cliente, "agricultor")


def pagar(cliente, token, tipo="arbol", arbol_id=None, plan_nombre=None, numero=TARJETA_OK, vencimiento="12/39"):
    return cliente.post("/api/pagos", headers=auth(token), json={
        "tipo": tipo, "arbol_id": arbol_id, "plan_nombre": plan_nombre,
        "numero": numero, "titular": "Persona de Prueba", "vencimiento": vencimiento, "cvv": "123",
    }).json()


def publicar_arbol(cliente, token, cupos=3, precio=10000, especie="palto_hass"):
    import catalogo
    foto = sorted(catalogo.fotos_permitidas(especie))[0]
    plan, tipo = {5: ("Básico", "Compartido"), 3: ("Intermedio", "Compartido"), 1: ("Premium", "Exclusivo")}[cupos]
    r = cliente.post("/api/arboles", headers=auth(token), json={
        "especie": especie, "identificador": str(next(_correos)), "ubicacion": "Curicó, Maule",
        "plan": plan, "tipo_suscripcion": tipo, "cupos_totales": cupos,
        "precio_mensual_clp": precio, "estimacion_cosecha_kg": 40, "imagen": foto,
    }).json()
    assert r["status"] == "success", r
    return r["arbol"]["id"]
