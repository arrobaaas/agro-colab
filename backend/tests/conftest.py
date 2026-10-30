"""Configuración común de las pruebas.

Antes de importar la aplicación se fija el entorno: una base SQLite
temporal (nunca la real), modo desarrollo (los códigos de verificación
llegan en la respuesta en vez de por correo) y un secreto fijo para los
tokens. Sin BREVO_API_KEY no se envía ningún correo real.
"""

import itertools
import os
import sys
import tempfile

import pytest

_carpeta = tempfile.mkdtemp(prefix="agrocolab-pruebas-")
os.environ["AGROCOLAB_DB_URL"] = f"sqlite:///{os.path.join(_carpeta, 'pruebas.db')}"
os.environ["AGROCOLAB_MOD_MODE"] = "desarrollo"
os.environ["AGROCOLAB_SECRET"] = "secreto-solo-para-pruebas"
os.environ.pop("BREVO_API_KEY", None)
os.environ.pop("CORREO_REMITENTE", None)
os.environ.pop("ALERTA_CORREO", None)
os.environ.pop("ALERTA_WEBHOOK_URL", None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

_ips = itertools.count(1)
_correos = itertools.count(1)

TARJETA_OK = "4242 4242 4242 4242"
TARJETA_SIN_FONDOS = "4000 0000 0000 0002"


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
    """Un solo inicio de sesión por cuenta demo en toda la ejecución: el
    login tiene un límite de 10 intentos por cuenta cada 15 minutos."""
    with TestClient(main.app, headers={"X-Forwarded-For": "10.255.0.1"}) as c:
        return {
            "comprador": login(c, "comprador@agrocolab.cl"),
            "agricultor": login(c, "agricultor@agrocolab.cl", rol="agricultor"),
        }


@pytest.fixture
def token_comprador(_tokens_demo):
    return _tokens_demo["comprador"]


@pytest.fixture
def token_agricultor(_tokens_demo):
    return _tokens_demo["agricultor"]


def registrar(cliente, rol):
    """Registra y verifica una cuenta nueva. Devuelve (email, password, token)."""
    email = f"prueba{next(_correos)}@ejemplo.cl"
    password = "clave-segura-1"
    r = cliente.post("/api/register", json={
        "nombre": "Persona de Prueba", "email": email, "password": password, "rol": rol,
    }).json()
    assert r["status"] == "success", r
    codigo = r["user"]["codigo_verificacion"]
    assert cliente.post("/api/verificar-cuenta", json={"email": email, "codigo": codigo}).json()["status"] == "success"
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
    r = cliente.post("/api/arboles", headers=auth(token), json={
        "especie": especie, "identificador": str(next(_correos)), "ubicacion": "Curicó, Maule",
        "plan": "Básico", "tipo_suscripcion": "Compartido", "cupos_totales": cupos,
        "precio_mensual_clp": precio, "estimacion_cosecha_kg": 40, "imagen": foto,
    }).json()
    assert r["status"] == "success", r
    return r["arbol"]["id"]
