"""Cada prueba cubre un hallazgo de la auditoría de seguridad (auditoria/HALLAZGOS.csv)."""

import json
import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import main
from conftest import CONSENTIMIENTO, TARJETA_OK, auth, login, pagar, publicar_arbol, registrar
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parent.parent
CLAVE = "clave-segura-1"
PEDIDO = {
    "plan_nombre": "Canasta Huerto Esencial", "tipo_destino": "particular", "direccion": "Av. Siempre Viva 742",
    "comuna": "Maipú", "codigo_postal": "8320000", "telefono_codigo": "+56", "telefono": "912345678", "frecuencia_entrega": "semanal",
}
COMERCIAL = {"tipo_destino": "comercial", "razon_social": "Empresa SpA", "rut": "76.123.456-0"}


def _id(token) -> int:
    return int(token.split(".")[0])


def _arbol_demo(cliente, cupos_libres=True) -> int:
    for arbol in cliente.get("/api/arboles").json():
        if arbol["es_demo"] and (not cupos_libres or arbol["cupos_ocupados"] < arbol["cupos_totales"]):
            return arbol["id"]
    raise AssertionError("sin árboles demo libres")


def _sesion():
    from database import SessionLocal
    return SessionLocal()


# ------------------------------------ AC-01, AC-02, AC-06: lo demo y lo real

def test_comprador_real_no_adopta_arbol_demo(cliente, nuevo_comprador):
    _, _, token = nuevo_comprador
    r = cliente.post("/api/pagos", headers=auth(token), json={
        "tipo": "arbol", "arbol_id": _arbol_demo(cliente), "numero": TARJETA_OK, "titular": "Persona",
        "vencimiento": "12/39", "cvv": "123",
    })
    assert r.status_code == 409


def test_comprador_demo_no_adopta_arbol_real(cliente, token_agricultor, token_comprador_demo):
    arbol = publicar_arbol(cliente, token_agricultor)
    r = cliente.post("/api/pagos", headers=auth(token_comprador_demo), json={
        "tipo": "arbol", "arbol_id": arbol, "numero": TARJETA_OK, "titular": "Persona",
        "vencimiento": "12/39", "cvv": "123",
    })
    assert r.status_code == 409


def test_agricultor_demo_no_ve_suscriptores_reales(cliente, nuevo_comprador, token_agricultor_demo):
    """Una adopción real anterior a esta corrección no debe quedar a la vista."""
    from database import Suscripcion
    _, _, token = nuevo_comprador
    arbol = _arbol_demo(cliente)
    db = _sesion()
    try:
        db.add(Suscripcion(usuario_id=_id(token), arbol_id=arbol))
        db.commit()
    finally:
        db.close()

    id_demo = _id(token_agricultor_demo)
    filas = cliente.get(f"/api/mis-arboles/{id_demo}/suscriptores", headers=auth(token_agricultor_demo)).json()
    assert all(s["usuario_id"] != _id(token) for fila in filas for s in fila["suscriptores"])
    assert cliente.get(f"/api/usuario/{_id(token)}", headers=auth(token_agricultor_demo)).status_code == 404


def test_cuenta_demo_no_altera_el_catalogo_ni_expulsa(cliente, token_agricultor_demo):
    arbol = cliente.get("/api/arboles").json()
    demo = next(a for a in arbol if a["es_demo"])
    cuerpo = {
        "especie": demo["especie"], "ubicacion": "Otro sitio", "plan": demo["plan"], "tipo_suscripcion": demo["tipo_suscripcion"],
        "cupos_totales": demo["cupos_totales"], "precio_mensual_clp": 1, "estimacion_cosecha_kg": 1, "imagen": demo["imagen"],
    }
    assert cliente.post("/api/arboles", headers=auth(token_agricultor_demo), json=cuerpo).status_code == 403
    assert cliente.put(f"/api/arboles/{demo['id']}", headers=auth(token_agricultor_demo), json=cuerpo).status_code == 403
    assert cliente.delete("/api/suscripciones/1", headers=auth(token_agricultor_demo)).status_code == 403


def test_cuenta_demo_no_recibe_datos_comerciales(cliente, token_comprador_demo):
    pago = pagar(cliente, token_comprador_demo, tipo="plan", plan_nombre="Canasta Huerto Esencial")["pago"]["id"]
    r = cliente.post("/api/pedidos", headers=auth(token_comprador_demo), json={**PEDIDO, **COMERCIAL, "pago_id": pago})
    assert r.status_code == 403


def test_lo_de_la_cuenta_demo_se_limpia_al_entrar(cliente, token_comprador_demo):
    from database import Pedido
    pago = pagar(cliente, token_comprador_demo, tipo="plan", plan_nombre="Canasta Huerto Esencial")["pago"]["id"]
    pedido = cliente.post("/api/pedidos", headers=auth(token_comprador_demo), json={**PEDIDO, "pago_id": pago}).json()["pedido"]["id"]
    db = _sesion()
    try:
        db.query(Pedido).filter(Pedido.id == pedido).update({"fecha_registro": datetime.utcnow() - timedelta(hours=2)})
        db.commit()
    finally:
        db.close()
    login(cliente, "comprador@agrocolab.cl")
    assert cliente.get(f"/api/pedidos/{pedido}", headers=auth(token_comprador_demo)).status_code == 404


# ------------------------------------ AC-03: administrador

def _crear_administrador(monkeypatch, email, password):
    from services import inicio
    monkeypatch.setenv("ADMIN_EMAIL", email)
    monkeypatch.setenv("ADMIN_PASSWORD", password)
    db = _sesion()
    try:
        inicio.crear_administrador(db)
    finally:
        db.close()


def _sin_verificar(cliente, email, password=CLAVE):
    return cliente.post("/api/register", json={
        **CONSENTIMIENTO, "nombre": "Atacante", "email": email, "password": password, "rol": "comprador",
    }).json()


def test_cuenta_sin_verificar_no_se_asciende_con_su_contrasena(cliente, monkeypatch):
    email = "futuro-admin@ejemplo.cl"
    _sin_verificar(cliente, email)
    _crear_administrador(monkeypatch, email, "una-clave-larga-del-servidor")
    assert cliente.post("/api/login", json={"email": email, "password": CLAVE, "rol": "comprador"}).status_code == 401
    r = cliente.post("/api/login", json={"email": email, "password": "una-clave-larga-del-servidor", "rol": "comprador"}).json()
    assert r["user"]["rol"] == "administrador"


def test_cuenta_sin_verificar_no_se_asciende_sin_contrasena_valida(cliente, monkeypatch):
    email = "otro-admin@ejemplo.cl"
    _sin_verificar(cliente, email)
    _crear_administrador(monkeypatch, email, "corta")
    r = cliente.post("/api/login", json={"email": email, "password": CLAVE, "rol": "comprador"}).json()
    assert r["user"]["rol"] == "comprador" and "token" not in r["user"]


def test_cuenta_verificada_se_asciende(cliente, monkeypatch):
    email, password, _ = registrar(cliente, "comprador")
    _crear_administrador(monkeypatch, email, "")
    r = cliente.post("/api/login", json={"email": email, "password": password, "rol": "comprador"}).json()
    assert r["user"]["rol"] == "administrador"


def test_administrador_no_se_autoelimina(cliente, token_admin):
    r = cliente.request("DELETE", "/api/perfil", headers=auth(token_admin), json={"password": "clave-admin-de-pruebas"})
    assert r.status_code == 403


# ------------------------------------ AC-04: pre-secuestro de cuentas

def test_la_contrasena_del_primer_registro_no_sobrevive(cliente):
    email = "victima@ejemplo.cl"
    _sin_verificar(cliente, email, "clave-del-atacante")
    codigo = _sin_verificar(cliente, email, "clave-de-la-victima")["user"]["codigo_verificacion"]
    assert cliente.post("/api/verificar-cuenta", json={"email": email, "codigo": codigo, "password": "clave-de-la-victima"}).status_code == 200
    assert cliente.post("/api/login", json={"email": email, "password": "clave-del-atacante", "rol": "comprador"}).status_code == 401
    assert cliente.post("/api/login", json={"email": email, "password": "clave-de-la-victima", "rol": "comprador"}).status_code == 200


def test_verificar_exige_la_contrasena_de_quien_se_registro(cliente):
    """Si el atacante se registra después, la víctima tiene el código, pero la cuenta
    tiene otra contraseña: la verificación no se completa."""
    email = "victima-2@ejemplo.cl"
    codigo = _sin_verificar(cliente, email, "clave-del-atacante")["user"]["codigo_verificacion"]
    r = cliente.post("/api/verificar-cuenta", json={"email": email, "codigo": codigo, "password": "clave-de-la-victima"})
    assert r.status_code == 400


def test_cuenta_verificada_no_se_reemplaza(cliente):
    email, password, _ = registrar(cliente, "comprador")
    _sin_verificar(cliente, email, "clave-del-atacante")
    assert cliente.post("/api/login", json={"email": email, "password": "clave-del-atacante", "rol": "comprador"}).status_code == 401
    assert cliente.post("/api/login", json={"email": email, "password": password, "rol": "comprador"}).status_code == 200


# ------------------------------------ AC-05, AC-39, AC-40: configuración

def _arrancar(entorno):
    return subprocess.run(
        [sys.executable, "-c", "import core"], cwd=BACKEND, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **entorno},
    )


@pytest.mark.parametrize("variable", ["RENDER", "DATABASE_URL"])
def test_modo_desarrollo_no_arranca_en_produccion(variable):
    resultado = _arrancar({"AGROCOLAB_MOD_MODE": "desarrollo", variable: "postgresql://x/y"})
    assert resultado.returncode != 0 and "AGROCOLAB_MOD_MODE" in resultado.stderr


def test_secreto_corto_avisa_en_produccion():
    resultado = _arrancar({"AGROCOLAB_MOD_MODE": "produccion", "AGROCOLAB_SECRET": "corto"})
    assert resultado.returncode == 0 and "AGROCOLAB_SECRET" in resultado.stderr


@pytest.mark.parametrize("url, avisa", [
    ("sqlite:///x.db", False),
    ("postgresql+psycopg://u:c@dpg-interno/b", False),
    ("postgresql+psycopg://u:c@localhost:5432/b", False),
    ("postgresql+psycopg://u:c@neon.tech/b?sslmode=require", False),
    ("postgresql+psycopg://u:c@neon.tech/b", True),
])
def test_avisa_si_una_base_externa_no_exige_tls(url, avisa):
    from database import sin_tls_exigido
    assert sin_tls_exigido(url) is avisa


# ------------------------------------ AC-07, AC-08: límites

def test_inicios_de_sesion_correctos_no_gastan_el_limite(cliente):
    email, password, _ = registrar(cliente, "comprador")
    respuestas = [cliente.post("/api/login", json={"email": email, "password": password, "rol": "comprador"}) for _ in range(14)]
    assert {r.status_code for r in respuestas} == {200}


def test_fallos_desde_otras_ips_no_bloquean_a_la_duena(cliente):
    email, password, _ = registrar(cliente, "comprador")
    for i in range(8):
        cliente.post("/api/login", json={"email": email, "password": "mala", "rol": "comprador"}, headers={"X-Forwarded-For": "10.200.0.9"})
    r = cliente.post("/api/login", json={"email": email, "password": password, "rol": "comprador"}, headers={"X-Forwarded-For": "10.200.0.10"})
    assert r.status_code == 200


def test_la_cuenta_demo_no_se_puede_bloquear(cliente):
    for i in range(31):
        cliente.post("/api/login", json={"email": "comprador@agrocolab.cl", "password": "mala", "rol": "comprador"}, headers={"X-Forwarded-For": f"10.201.{i // 8}.1"})
    r = cliente.post("/api/login", json={"email": "comprador@agrocolab.cl", "password": "123", "rol": "comprador"}, headers={"X-Forwarded-For": "10.201.99.1"})
    assert r.status_code == 200


def test_x_forwarded_for_usa_el_ultimo_valor_y_descarta_lo_que_no_es_ip():
    from starlette.requests import Request
    from core import ip_cliente

    def pedir(*valores):
        cabeceras = [(b"x-forwarded-for", v.encode()) for v in valores]
        return ip_cliente(Request({"type": "http", "headers": cabeceras, "client": ("192.0.2.1", 1)}))

    assert pedir("1.1.1.1, 2.2.2.2") == "2.2.2.2"
    assert pedir("1.1.1.1", "2.2.2.2") == "2.2.2.2"
    assert pedir("<script>") == "192.0.2.1"
    assert pedir() == "192.0.2.1"


def test_cabecera_ip_configurada_tiene_prioridad(monkeypatch):
    import core
    from starlette.requests import Request
    monkeypatch.setattr(core, "CABECERA_IP", "True-Client-IP")
    peticion = Request({"type": "http", "client": ("192.0.2.1", 1), "headers": [
        (b"true-client-ip", b"203.0.113.5"), (b"x-forwarded-for", b"1.1.1.1"),
    ]})
    assert core.ip_cliente(peticion) == "203.0.113.5"


# ------------------------------------ AC-09, AC-10, AC-11: alertas y eventos

def test_tope_global_de_alertas(monkeypatch):
    import seguridad
    monkeypatch.setattr(seguridad.eventos, "contar_recientes", lambda *a: 99)
    monkeypatch.setattr(seguridad.eventos, "alerta_enviada_desde", lambda *a: False)
    monkeypatch.setattr(seguridad.eventos, "contar_alertas_desde", lambda *a: seguridad.MAX_ALERTAS_POR_HORA)
    assert seguridad._alerta_pendiente("login_fallido", "advertencia", "1.1.1.1", "a@b.cl") is None


def test_alerta_por_webhook_no_menciona_ni_enlaza():
    import seguridad
    texto = seguridad._neutralizar("@everyone <!channel> [clic](https://malo.example)")
    assert "@everyone" not in texto and "<" not in texto and "[" not in texto


def test_alerta_enviada_no_lleva_correo_ni_ip_completos(monkeypatch):
    import seguridad
    capturado = {}

    class Respuesta:
        def close(self):
            pass

    def abrir(peticion, timeout):
        capturado["cuerpo"] = json.loads(peticion.data)
        return Respuesta()

    monkeypatch.setenv("ALERTA_WEBHOOK_URL", "https://webhook.invalido/x")
    monkeypatch.setattr(seguridad.urllib.request, "urlopen", abrir)
    seguridad._enviar_alerta("Prueba", 1, {
        "evento": "x", "severidad": "advertencia", "ip": seguridad.enmascarar_ip("203.0.113.9"),
        "email": seguridad.enmascarar_correo("persona@ejemplo.cl"), "ruta": "/", "detalle": "@everyone", "momento": "ahora",
    })
    assert capturado["cuerpo"]["allowed_mentions"] == {"parse": []}
    assert "persona@ejemplo.cl" not in capturado["cuerpo"]["content"] and "203.0.113.9" not in capturado["cuerpo"]["content"]


def test_un_fallo_del_correo_no_impide_el_webhook(monkeypatch):
    import seguridad
    enviado = []

    class Respuesta:
        def close(self):
            pass

    def falla(*a, **k):
        raise ConnectionResetError()

    monkeypatch.setenv("ALERTA_CORREO", "x@y.cl")
    monkeypatch.setenv("ALERTA_WEBHOOK_URL", "https://webhook.invalido/x")
    monkeypatch.setattr(seguridad, "enviar_correo", falla)
    monkeypatch.setattr(seguridad.urllib.request, "urlopen", lambda p, timeout: enviado.append(1) or Respuesta())
    seguridad._enviar_alerta("Prueba", 1, {"evento": "x", "severidad": "info", "ip": None, "email": None, "ruta": None, "detalle": "", "momento": ""})
    assert enviado


def test_rafaga_de_tokens_invalidos_no_inserta_una_fila_por_peticion(cliente):
    from database import EventoSeguridad
    ip = "10.210.0.1"
    for _ in range(70):
        cliente.get("/api/pagos", headers={"Authorization": "Bearer 1.9999999999.x", "X-Forwarded-For": ip})
    db = _sesion()
    try:
        filas = db.query(EventoSeguridad).filter(EventoSeguridad.ip == ip, EventoSeguridad.tipo == "token_invalido").count()
    finally:
        db.close()
    # El tope es de 30 por minuto, y la ráfaga puede cruzar de un minuto a otro
    assert filas <= 60


def test_eventos_e_intentos_tienen_un_pool_propio():
    from database import SessionAuxiliar, SessionLocal
    assert SessionAuxiliar.kw["bind"] is not SessionLocal.kw["bind"]


# ------------------------------------ AC-12, AC-13: tamaño y abuso

def test_cuerpo_grande_responde_413(cliente):
    r = cliente.post("/api/login", content=b"x" * 70_000, headers={"Content-Type": "application/json"})
    assert r.status_code == 413 and r.json()["status"] == "error"
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_cuerpo_por_partes_no_se_lee_completo(cliente):
    def partes():
        for _ in range(10):
            yield b"x" * 10_000
    r = cliente.post("/api/login", content=partes(), headers={"Content-Type": "application/json"})
    assert r.status_code in (400, 413)


def test_publicar_tiene_limite(cliente, nuevo_agricultor, monkeypatch):
    from services import arboles
    monkeypatch.setattr(arboles, "PUBLICACIONES_POR_HORA", 2)
    _, _, token = nuevo_agricultor
    for _ in range(2):
        publicar_arbol(cliente, token)
    import catalogo
    foto = sorted(catalogo.fotos_permitidas("palto_hass"))[0]
    r = cliente.post("/api/arboles", headers=auth(token), json={
        "especie": "palto_hass", "ubicacion": "Curicó", "plan": "Premium", "tipo_suscripcion": "Exclusivo",
        "cupos_totales": 1, "precio_mensual_clp": 1000, "estimacion_cosecha_kg": 10, "imagen": foto,
    })
    assert r.status_code == 429


def test_segundo_despacho_del_mismo_arbol_responde_409(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor)
    assert pagar(cliente, token, arbol_id=arbol)["status"] == "success"
    cuerpo = {**PEDIDO, "tipo": "arbol", "arbol_id": arbol}
    assert cliente.post("/api/pedidos", headers=auth(token), json=cuerpo).status_code == 201
    assert cliente.post("/api/pedidos", headers=auth(token), json=cuerpo).status_code == 409


# ------------------------------------ AC-14, AC-15, AC-16, AC-17: enumeración y datos en logs

def test_login_ejecuta_bcrypt_aunque_la_cuenta_no_exista(cliente, monkeypatch):
    from services import cuentas
    llamadas = []
    original = cuentas.verify_password
    monkeypatch.setattr(cuentas, "verify_password", lambda p, h: llamadas.append(h) or original(p, h))
    cliente.post("/api/login", json={"email": "no-existe@ejemplo.cl", "password": "x", "rol": "comprador"})
    assert llamadas == [cuentas._HASH_FICTICIO]


def test_registro_repetido_tambien_calcula_el_hash(cliente, monkeypatch):
    from services import cuentas
    email, _, _ = registrar(cliente, "comprador")
    llamadas = []
    original = cuentas.hash_password
    monkeypatch.setattr(cuentas, "hash_password", lambda p: llamadas.append(p) or original(p))
    _sin_verificar(cliente, email)
    assert llamadas == [CLAVE]


def test_los_codigos_no_se_guardan_en_claro_ni_con_un_hash_sin_clave(cliente):
    import hashlib
    from database import Usuario
    email = "codigo@ejemplo.cl"
    codigo = _sin_verificar(cliente, email)["user"]["codigo_verificacion"]
    db = _sesion()
    try:
        guardado = db.query(Usuario).filter(Usuario.email == email).first().codigo_verificacion
    finally:
        db.close()
    assert guardado != codigo and guardado != hashlib.sha256(codigo.encode()).hexdigest()


def test_el_asunto_de_los_correos_no_lleva_el_codigo(monkeypatch):
    import notificaciones
    asuntos = []
    monkeypatch.setattr(notificaciones, "enviar_correo", lambda destino, asunto, html, nombre="": asuntos.append((asunto, html)) or True)
    notificaciones.enviar_codigo_verificacion("a@b.cl", "123456")
    notificaciones.enviar_codigo_recuperacion("a@b.cl", "654321")
    assert "123456" not in asuntos[0][0] and "654321" not in asuntos[1][0]
    assert "123456" in asuntos[0][1] and "654321" in asuntos[1][1]


def test_una_desconexion_de_brevo_no_rompe_el_envio(monkeypatch):
    import http.client
    import notificaciones

    def desconecta(*a, **k):
        raise http.client.RemoteDisconnected("cerrado")

    monkeypatch.setenv("BREVO_API_KEY", "clave")
    monkeypatch.setenv("CORREO_REMITENTE", "a@b.cl")
    monkeypatch.setattr(notificaciones.urllib.request, "urlopen", desconecta)
    assert notificaciones.enviar_correo("c@d.cl", "Asunto", "<p>x</p>") is False


def test_los_logs_enmascaran_correo_e_ip(caplog):
    import seguridad
    capturas = []
    manejador = logging.Handler()
    manejador.emit = lambda registro: capturas.append(registro.getMessage())
    seguridad.registro.addHandler(manejador)
    try:
        seguridad.registrar_evento("prueba_log", ip="203.0.113.77", email="persona@ejemplo.cl")
    finally:
        seguridad.registro.removeHandler(manejador)
    assert capturas and "persona@ejemplo.cl" not in capturas[0] and "203.0.113.77" not in capturas[0]


def test_entrada_con_html_no_se_guarda_en_los_eventos(cliente):
    from database import EventoSeguridad
    ip = "10.211.0.1"
    cliente.post("/api/register", headers={"X-Forwarded-For": ip}, json={
        **CONSENTIMIENTO, "nombre": "<b>dato-personal</b>", "email": "html@ejemplo.cl", "password": CLAVE, "rol": "comprador",
    })
    db = _sesion()
    try:
        detalles = [e.detalle for e in db.query(EventoSeguridad).filter(EventoSeguridad.ip == ip, EventoSeguridad.tipo == "entrada_html")]
    finally:
        db.close()
    assert detalles and not any("dato-personal" in d for d in detalles)


# ------------------------------------ AC-18, AC-19, AC-34, AC-35, AC-43: privacidad

@pytest.mark.parametrize("campos", [{}, {"acepta_datos": True}, {"acepta_datos": False, "acepta_terminos": True}])
def test_registro_sin_consentimiento_responde_422(cliente, campos):
    r = cliente.post("/api/register", json={
        "nombre": "Sin Consentir", "email": "sin-consentir@ejemplo.cl", "password": CLAVE, "rol": "comprador", **campos,
    })
    assert r.status_code == 422


def test_registro_guarda_la_version_de_la_politica(cliente):
    from core import VERSION_POLITICA
    from database import Usuario
    email = "politica@ejemplo.cl"
    _sin_verificar(cliente, email)
    db = _sesion()
    try:
        assert db.query(Usuario).filter(Usuario.email == email).first().politica_privacidad == VERSION_POLITICA
    finally:
        db.close()


def test_eliminar_cuenta_borra_intentos_y_anonimiza_eventos(cliente, nuevo_comprador):
    from database import EventoSeguridad, IntentoAcceso
    email, password, token = nuevo_comprador
    cliente.post("/api/login", json={"email": email, "password": "mala", "rol": "comprador"})
    assert cliente.request("DELETE", "/api/perfil", headers=auth(token), json={"password": password}).status_code == 200
    db = _sesion()
    try:
        assert db.query(EventoSeguridad).filter(EventoSeguridad.email == email).count() == 0
        assert db.query(IntentoAcceso).filter(IntentoAcceso.clave == f"login:{email}").count() == 0
    finally:
        db.close()


def test_borrar_cuenta_exige_la_contrasena(cliente, nuevo_comprador):
    _, _, token = nuevo_comprador
    assert cliente.request("DELETE", "/api/perfil", headers=auth(token), json={"password": "mala"}).status_code == 403
    assert cliente.request("DELETE", "/api/perfil", headers=auth(token), json={}).status_code == 422
    assert cliente.get("/api/pagos", headers=auth(token)).status_code == 200


def test_cuentas_sin_verificar_antiguas_se_purgan(cliente):
    from database import Usuario
    from repositories import usuarios as repo
    email = "antigua@ejemplo.cl"
    _sin_verificar(cliente, email)
    db = _sesion()
    try:
        db.query(Usuario).filter(Usuario.email == email).update({"codigo_expira": datetime.utcnow() - timedelta(days=2)})
        db.commit()
        repo.purgar_sin_verificar(db, datetime.utcnow() - timedelta(days=1))
        db.commit()
        assert db.query(Usuario).filter(Usuario.email == email).count() == 0
    finally:
        db.close()


def test_pedido_particular_no_guarda_razon_social_ni_rut(cliente, nuevo_comprador):
    _, _, token = nuevo_comprador
    pago = pagar(cliente, token, tipo="plan", plan_nombre="Canasta Huerto Esencial")["pago"]["id"]
    r = cliente.post("/api/pedidos", headers=auth(token), json={**PEDIDO, "pago_id": pago, "razon_social": "X", "rut": "76.123.456-0"}).json()
    assert r["pedido"]["razon_social"] is None and r["pedido"]["rut"] is None


def test_exportar_devuelve_solo_lo_propio(cliente, token_agricultor, nuevo_comprador, token_comprador):
    email, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor)
    assert pagar(cliente, token, arbol_id=arbol)["status"] == "success"
    copia = cliente.get("/api/perfil/exportar", headers=auth(token)).json()
    assert copia["cuenta"]["email"] == email and len(copia["adopciones"]) == 1 and len(copia["pagos"]) == 1
    otra = cliente.get("/api/perfil/exportar", headers=auth(token_comprador)).json()
    assert otra["cuenta"]["email"] != email


def test_la_lectura_de_datos_de_terceros_queda_registrada(cliente, nuevo_agricultor, nuevo_comprador):
    from database import EventoSeguridad
    _, _, productor = nuevo_agricultor
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, productor)
    assert pagar(cliente, token, arbol_id=arbol)["status"] == "success"
    assert cliente.get(f"/api/usuario/{_id(token)}", headers=auth(productor)).status_code == 200
    db = _sesion()
    try:
        assert db.query(EventoSeguridad).filter(EventoSeguridad.tipo == "lectura_datos", EventoSeguridad.usuario_id == _id(productor)).count() >= 1
    finally:
        db.close()


# ------------------------------------ AC-20, AC-21, AC-44: negocio

def test_arbol_con_suscriptores_no_se_borra(cliente, nuevo_agricultor, nuevo_comprador):
    _, _, productor = nuevo_agricultor
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, productor)
    assert pagar(cliente, token, arbol_id=arbol)["status"] == "success"
    assert cliente.delete(f"/api/arboles/{arbol}", headers=auth(productor)).status_code == 409


def test_agricultor_con_suscriptores_no_se_autoelimina(cliente, nuevo_agricultor, nuevo_comprador):
    _, password, productor = nuevo_agricultor
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, productor)
    assert pagar(cliente, token, arbol_id=arbol)["status"] == "success"
    assert cliente.request("DELETE", "/api/perfil", headers=auth(productor), json={"password": password}).status_code == 409


def test_expulsar_avisa_al_comprador(cliente, nuevo_agricultor, nuevo_comprador, monkeypatch):
    from services import suscripciones
    email, _, token = nuevo_comprador
    _, _, productor = nuevo_agricultor
    avisos = []
    monkeypatch.setattr(suscripciones, "MODO_DESARROLLO", False)
    monkeypatch.setattr(suscripciones, "enviar_en_segundo_plano", lambda funcion, *args: avisos.append(args))
    arbol = publicar_arbol(cliente, productor)
    assert pagar(cliente, token, arbol_id=arbol)["status"] == "success"
    fila = cliente.get(f"/api/mis-arboles/{_id(productor)}/suscriptores", headers=auth(productor)).json()[0]
    assert cliente.delete(f"/api/suscripciones/{fila['suscriptores'][0]['suscripcion_id']}", headers=auth(productor)).status_code == 200
    assert avisos and avisos[0][0] == email


@pytest.mark.parametrize("plan, tipo, cupos", [
    ("Premium", "Exclusivo", 50), ("Premium", "Compartido", 1), ("Básico", "Compartido", 3), ("Intermedio", "Exclusivo", 3),
])
def test_cada_plan_impone_sus_cupos_y_su_tipo(cliente, token_agricultor, plan, tipo, cupos):
    import catalogo
    foto = sorted(catalogo.fotos_permitidas("palto_hass"))[0]
    r = cliente.post("/api/arboles", headers=auth(token_agricultor), json={
        "especie": "palto_hass", "ubicacion": "Curicó", "plan": plan, "tipo_suscripcion": tipo, "cupos_totales": cupos,
        "precio_mensual_clp": 1000, "estimacion_cosecha_kg": 10, "imagen": foto,
    })
    assert r.status_code == 422


def test_precio_cero_se_rechaza(cliente, token_agricultor):
    import catalogo
    foto = sorted(catalogo.fotos_permitidas("palto_hass"))[0]
    r = cliente.post("/api/arboles", headers=auth(token_agricultor), json={
        "especie": "palto_hass", "ubicacion": "Curicó", "plan": "Básico", "tipo_suscripcion": "Compartido", "cupos_totales": 5,
        "precio_mensual_clp": 0, "estimacion_cosecha_kg": 10, "imagen": foto,
    })
    assert r.status_code == 422


def test_plan_b2b_exige_destino_comercial(cliente, nuevo_comprador):
    _, _, token = nuevo_comprador
    plan = "Lote Gastronómico B2B"
    pago = pagar(cliente, token, tipo="plan", plan_nombre=plan)["pago"]["id"]
    assert cliente.post("/api/pedidos", headers=auth(token), json={**PEDIDO, "plan_nombre": plan, "pago_id": pago}).status_code == 422
    r = cliente.post("/api/pedidos", headers=auth(token), json={**PEDIDO, **COMERCIAL, "plan_nombre": plan, "pago_id": pago})
    assert r.status_code == 201
    logistica = {k: v for k, v in PEDIDO.items() if k != "plan_nombre"}
    assert cliente.put(f"/api/pedidos/{r.json()['pedido']['id']}", headers=auth(token), json=logistica).status_code == 422


# ------------------------------------ AC-22, AC-23, AC-42: carreras

def _en_paralelo(funciones):
    resultados = [None] * len(funciones)

    def correr(i, f):
        resultados[i] = f()

    hilos = [threading.Thread(target=correr, args=(i, f)) for i, f in enumerate(funciones)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return resultados


def test_reclamar_un_pago_es_atomico(cliente, nuevo_comprador):
    from repositories import pagos as repo_pagos
    _, _, token = nuevo_comprador
    pago = pagar(cliente, token, tipo="plan", plan_nombre="Canasta Huerto Esencial")["pago"]["id"]
    db = _sesion()
    try:
        assert repo_pagos.reclamar(db, pago, 999_001) is True
        db.commit()
        assert repo_pagos.reclamar(db, pago, 999_002) is False
        db.commit()
    finally:
        db.close()


def test_mismo_pago_en_paralelo_crea_un_solo_pedido(cliente, nuevo_comprador):
    _, _, token = nuevo_comprador
    pago = pagar(cliente, token, tipo="plan", plan_nombre="Canasta Huerto Esencial")["pago"]["id"]
    cuerpo = {**PEDIDO, "pago_id": pago}

    def pedir():
        with TestClient(main.app, headers={"X-Forwarded-For": "10.220.0.1"}) as c:
            return c.post("/api/pedidos", headers=auth(token), json=cuerpo).status_code

    codigos = _en_paralelo([pedir for _ in range(4)])
    assert codigos.count(201) == 1
    assert len(cliente.get("/api/pedidos", headers=auth(token)).json()) == 1


def test_compras_simultaneas_del_ultimo_cupo(cliente, token_agricultor):
    arbol = publicar_arbol(cliente, token_agricultor, cupos=1)
    tokens = [registrar(cliente, "comprador")[2] for _ in range(3)]

    def comprar(token):
        with TestClient(main.app, headers={"X-Forwarded-For": "10.221.0.1"}) as c:
            return pagar(c, token, arbol_id=arbol)["status"]

    estados = _en_paralelo([lambda t=t: comprar(t) for t in tokens])
    assert estados.count("success") == 1
    fila = cliente.get(f"/api/arboles/{arbol}").json()
    assert fila["cupos_ocupados"] == 1


def test_liberar_dos_veces_descuenta_una_sola_vez(cliente, token_agricultor, nuevo_comprador):
    from database import Arbol, Suscripcion
    from repositories import arboles as repo_arboles, suscripciones as repo
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor)
    assert pagar(cliente, token, arbol_id=arbol)["status"] == "success"
    db = _sesion()
    try:
        suscripcion = db.query(Suscripcion).filter(Suscripcion.arbol_id == arbol).first().id
        for _ in range(2):
            if repo.borrar(db, suscripcion):
                repo_arboles.liberar_cupo(db, arbol)
        db.commit()
        assert db.query(Arbol).filter(Arbol.id == arbol).first().cupos_ocupados == 0
    finally:
        db.close()


def test_la_base_impide_la_sobreventa(cliente, token_agricultor):
    from database import Arbol
    from sqlalchemy.exc import IntegrityError
    arbol = publicar_arbol(cliente, token_agricultor, cupos=1)
    db = _sesion()
    try:
        with pytest.raises(IntegrityError):
            db.query(Arbol).filter(Arbol.id == arbol).update({"cupos_ocupados": 2})
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_rafaga_no_supera_el_limite():
    from repositories import intentos
    clave = f"rafaga:{time.time()}"
    resultados = _en_paralelo([lambda: intentos.registrar_si_permitido(clave, 3, 60) for _ in range(5)])
    # SQLite serializa de otra forma: la garantía estricta se comprueba en PostgreSQL
    from database import ES_SQLITE
    if not ES_SQLITE:
        assert resultados.count(True) == 3
    assert intentos.registrar_si_permitido(clave, 3, 60) is False


# ------------------------------------ AC-27, AC-33, AC-37, AC-38: sesiones y errores

def test_logout_invalida_el_token(cliente, nuevo_comprador):
    _, _, token = nuevo_comprador
    assert cliente.post("/api/logout", headers=auth(token)).status_code == 200
    assert cliente.get("/api/pagos", headers=auth(token)).status_code == 401


def test_logout_de_la_cuenta_demo_no_cierra_a_los_demas(cliente, token_comprador_demo):
    assert cliente.post("/api/logout", headers=auth(token_comprador_demo)).status_code == 200
    assert cliente.get("/api/pagos", headers=auth(token_comprador_demo)).status_code == 200


def test_quitar_la_verificacion_cierra_la_sesion(cliente, token_admin, nuevo_comprador):
    email, _, token = nuevo_comprador
    r = cliente.put(f"/api/admin/usuarios/{_id(token)}", headers=auth(token_admin), json={
        "nombre": "Persona de Prueba", "email": email, "verificado": False,
    })
    assert r.status_code == 200
    assert cliente.get("/api/pagos", headers=auth(token)).status_code == 401


def test_cambiar_contrasena_tiene_limite(cliente, nuevo_comprador):
    email, _, token = nuevo_comprador
    cuerpo = {"nombre": "Persona", "email": email, "password": "clave-nueva-12", "password_actual": "mala"}
    codigos = [cliente.put("/api/perfil", headers=auth(token), json=cuerpo).status_code for _ in range(6)]
    assert codigos[-1] == 429


def test_token_vencido_y_firma_alterada(cliente, token_comprador):
    usuario, expira, firma = token_comprador.split(".")
    otra = ("0" if firma[0] != "0" else "1") + firma[1:]
    assert cliente.get("/api/pagos", headers=auth(f"{usuario}.{expira}.{otra}")).status_code == 401
    assert cliente.get("/api/pagos", headers=auth(f"{usuario}.{int(expira) + 1}.{firma}")).status_code == 401
    assert cliente.get("/api/pagos", headers=auth(f"{usuario}.1.{firma}")).status_code == 401
    assert cliente.get("/api/pagos", headers=auth(f"{usuario}.{expira}")).status_code == 401


@pytest.mark.parametrize("password", ["a" * 73, "ñ" * 40])
def test_contrasena_de_mas_de_72_bytes_responde_422(cliente, password):
    r = cliente.post("/api/register", json={
        **CONSENTIMIENTO, "nombre": "Persona", "email": "larga@ejemplo.cl", "password": password, "rol": "comprador",
    })
    assert r.status_code == 422


def test_token_no_ascii_responde_401(cliente, token_comprador):
    usuario, expira, _ = token_comprador.split(".")
    r = cliente.get("/api/pagos", headers={"Authorization": f"Bearer {usuario}.{expira}.é".encode("latin-1")})
    assert r.status_code == 401


def test_token_de_monitoreo_no_ascii_responde_401(cliente, monkeypatch):
    monkeypatch.setenv("MONITOREO_TOKEN", "t" * 24)
    r = cliente.get("/api/seguridad/resumen", headers={"X-Monitoreo-Token": "é".encode("latin-1")})
    assert r.status_code == 401


def test_codigo_con_digitos_de_otro_alfabeto_responde_422(cliente):
    r = cliente.post("/api/verificar-cuenta", json={"email": "x@y.cl", "codigo": "٠١٢٣٤٥", "password": "x"})
    assert r.status_code == 422


def test_perfil_ajeno_responde_igual_que_uno_inexistente(cliente, nuevo_comprador, token_comprador):
    _, _, token = nuevo_comprador
    ajeno = cliente.get(f"/api/usuario/{_id(token_comprador)}", headers=auth(token))
    inexistente = cliente.get("/api/usuario/99999999", headers=auth(token))
    assert ajeno.status_code == inexistente.status_code == 404 and ajeno.json() == inexistente.json()


def test_put_de_pedido_ajeno_responde_404(cliente, nuevo_comprador, token_comprador):
    _, _, token = nuevo_comprador
    pago = pagar(cliente, token, tipo="plan", plan_nombre="Canasta Huerto Esencial")["pago"]["id"]
    pedido = cliente.post("/api/pedidos", headers=auth(token), json={**PEDIDO, "pago_id": pago}).json()["pedido"]["id"]
    logistica = {k: v for k, v in PEDIDO.items() if k != "plan_nombre"}
    assert cliente.put(f"/api/pedidos/{pedido}", headers=auth(token_comprador), json=logistica).status_code == 404


def test_campos_extra_no_se_asignan(cliente, nuevo_comprador):
    email, _, token = nuevo_comprador
    r = cliente.put("/api/perfil", headers=auth(token), json={
        "nombre": "Persona", "email": email, "rol": "administrador", "verificado": 0, "sesion_version": 9,
    })
    assert r.status_code == 200 and r.json()["user"]["rol"] == "comprador"
    assert cliente.get("/api/pagos", headers=auth(token)).status_code == 200


def test_422_no_refleja_la_tarjeta(cliente, nuevo_comprador):
    _, _, token = nuevo_comprador
    r = cliente.post("/api/pagos", headers=auth(token), json={
        "tipo": "plan", "plan_nombre": "Canasta Huerto Esencial", "numero": "4242424242424242", "titular": "Persona",
        "vencimiento": "13/99", "cvv": "9876",
    })
    assert r.status_code == 422 and "4242" not in r.text and "9876" not in r.text


# ------------------------------------ AC-29, AC-30, AC-31: HTTP

def test_cors_solo_admite_el_frontend():
    assert "https://arrobaaas.github.io" in main.ORIGENES
    assert all(o.startswith(("https://arrobaaas.github.io", "http://localhost", "http://127.0.0.1")) for o in main.ORIGENES)
    assert main.ORIGENES_PRODUCCION == ["https://arrobaaas.github.io"]


def test_produccion_cierra_docs_y_origenes_locales():
    codigo = (
        "import main; from fastapi.testclient import TestClient; c = TestClient(main.app); "
        "print(c.get('/docs').status_code, c.get('/openapi.json').status_code, 'http://localhost:3000' in main.ORIGENES)"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo], cwd=BACKEND, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "AGROCOLAB_MOD_MODE": "produccion", "AGROCOLAB_DOCS": ""},
    )
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip().endswith("404 404 False")


def test_errores_500_llevan_cabeceras_y_cors(monkeypatch):
    from services import arboles as servicio

    def rompe(db):
        raise RuntimeError("detalle interno")

    monkeypatch.setattr(servicio, "listar", rompe)
    with TestClient(main.app, raise_server_exceptions=False) as c:
        r = c.get("/api/arboles", headers={"Origin": "https://arrobaaas.github.io"})
    assert r.status_code == 500 and "detalle interno" not in r.text
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Strict-Transport-Security"]
    assert r.headers["Access-Control-Allow-Origin"] == "https://arrobaaas.github.io"
    assert r.json()["status"] == "error"


def test_estado_no_revela_la_configuracion(cliente):
    assert set(cliente.get("/api/estado").json()) == {"status", "correo_real"}


# ------------------------------------ AC-26, AC-41, AC-47, AC-49

def test_pago_ajeno_deja_rastro(cliente, nuevo_comprador, token_comprador):
    from database import EventoSeguridad
    _, _, token = nuevo_comprador
    pago = pagar(cliente, token, tipo="plan", plan_nombre="Canasta Huerto Esencial")["pago"]["id"]
    assert cliente.get(f"/api/pagos/{pago}", headers=auth(token_comprador)).status_code == 404
    db = _sesion()
    try:
        assert db.query(EventoSeguridad).filter(EventoSeguridad.detalle == f"pago {pago} de otro usuario").count() == 1
    finally:
        db.close()


def test_requirements_fijados():
    for nombre in ("requirements.txt", "requirements-dev.txt"):
        for linea in (BACKEND / nombre).read_text(encoding="utf-8").splitlines():
            if linea.strip() and not linea.startswith("-r"):
                assert "==" in linea, linea


def test_existe_el_procedimiento_de_incidentes():
    assert (BACKEND.parent / "docs" / "INCIDENTES.md").exists()


def test_todas_las_paginas_cargan_font_awesome_con_integridad():
    paginas = [BACKEND.parent / "404.html", *(BACKEND.parent / "frontend").glob("*.html")]
    for pagina in paginas:
        texto = pagina.read_text(encoding="utf-8")
        assert 'font-awesome/6.4.0/css/all.min.css" integrity="sha512-' in texto, pagina.name
        assert "unsafe-eval" not in texto and "images.unsplash.com" not in texto


def test_admin_normaliza_el_correo(cliente, token_admin, nuevo_comprador):
    from database import Usuario
    email, _, token = nuevo_comprador
    nuevo = email.replace("prueba", "NORMALIZADO")
    r = cliente.put(f"/api/admin/usuarios/{_id(token)}", headers=auth(token_admin), json={
        "nombre": "Persona de Prueba", "email": nuevo, "verificado": True,
    })
    assert r.status_code == 200
    db = _sesion()
    try:
        assert db.query(Usuario).filter(Usuario.id == _id(token)).first().email == nuevo.lower()
    finally:
        db.close()


def test_cuenta_demo_no_se_elimina_ni_con_la_contrasena(cliente, token_comprador_demo):
    assert cliente.request("DELETE", "/api/perfil", headers=auth(token_comprador_demo), json={"password": "123"}).status_code == 403
