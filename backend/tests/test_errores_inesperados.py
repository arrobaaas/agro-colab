"""Errores que no vienen del usuario: la base caída, un choque entre dos
peticiones simultáneas y un fallo de programación. Todos deben llegar con su
código, con la forma {status, mensaje} y sin exponer detalles internos."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError

from main import app
from services import arboles as servicio_arboles

ORIGEN = "https://arrobaaas.github.io"


@pytest.fixture
def sin_propagar():
    # Como un servidor real: la excepción se convierte en respuesta en vez de
    # reventar la prueba
    return TestClient(app, raise_server_exceptions=False)


def fallar_con(monkeypatch, error):
    def listar(db):
        raise error
    monkeypatch.setattr(servicio_arboles, "listar", listar)


def revisar(respuesta, codigo):
    assert respuesta.status_code == codigo
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "error"
    texto = cuerpo["mensaje"].lower()
    # Nada de nombres de tablas, SQL ni trazas
    for interno in ("select", "arboles", "traceback", "sqlalchemy", "psycopg", "conexión rechazada por"):
        assert interno not in texto
    return cuerpo["mensaje"]


@pytest.mark.parametrize("error", [
    OperationalError("SELECT * FROM arboles", {}, Exception("could not connect to server")),
    InterfaceError("SELECT * FROM arboles", {}, Exception("connection already closed")),
])
def test_base_caida_responde_503(sin_propagar, monkeypatch, error):
    fallar_con(monkeypatch, error)
    mensaje = revisar(sin_propagar.get("/api/arboles"), 503)
    assert "base de datos" in mensaje


def test_choque_de_restriccion_responde_409(sin_propagar, monkeypatch):
    fallar_con(monkeypatch, IntegrityError("INSERT INTO arboles", {}, Exception("duplicate key value")))
    revisar(sin_propagar.get("/api/arboles"), 409)


def test_fallo_de_programacion_responde_500_sin_detalles(sin_propagar, monkeypatch):
    fallar_con(monkeypatch, RuntimeError("detalle interno que no debe salir: arboles.id"))
    mensaje = revisar(sin_propagar.get("/api/arboles"), 500)
    assert "detalle interno" not in mensaje


@pytest.mark.parametrize("error, codigo", [
    (OperationalError("x", {}, Exception("caida")), 503),
    (IntegrityError("x", {}, Exception("duplicado")), 409),
    (RuntimeError("fallo"), 500),
])
def test_los_errores_llevan_cors_para_que_el_navegador_los_lea(sin_propagar, monkeypatch, error, codigo):
    # Sin la cabecera CORS, el navegador oculta el cuerpo y el usuario solo ve
    # "No hay conexión", aunque el servidor haya explicado el problema
    fallar_con(monkeypatch, error)
    r = sin_propagar.get("/api/arboles", headers={"Origin": ORIGEN})
    assert r.status_code == codigo
    assert r.headers.get("access-control-allow-origin") == ORIGEN
    assert r.headers.get("x-content-type-options") == "nosniff"
