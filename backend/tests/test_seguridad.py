"""Autorización por recurso, validación de entradas y protecciones generales."""

from conftest import auth, login, pagar, publicar_arbol


def test_cabeceras_de_seguridad(cliente):
    r = cliente.get("/api/arboles")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"


def test_solo_el_productor_elimina_su_arbol(cliente, nuevo_agricultor, token_agricultor):
    _, _, token = nuevo_agricultor
    arbol = publicar_arbol(cliente, token)
    # Otro agricultor (el demo) no puede borrarlo; su dueño sí
    assert cliente.delete(f"/api/arboles/{arbol}", headers=auth(token_agricultor)).json()["status"] == "error"
    assert cliente.delete(f"/api/arboles/{arbol}", headers=auth(token)).json()["status"] == "success"


def test_agricultor_demo_no_elimina_arboles(cliente, token_agricultor):
    arbol = publicar_arbol(cliente, token_agricultor)
    assert cliente.delete(f"/api/arboles/{arbol}", headers=auth(token_agricultor)).json()["status"] == "error"


def test_comprador_no_puede_publicar_arboles(cliente, token_comprador):
    import catalogo
    foto = sorted(catalogo.fotos_permitidas("palto_hass"))[0]
    r = cliente.post("/api/arboles", headers=auth(token_comprador), json={
        "especie": "palto_hass", "ubicacion": "Curicó", "plan": "Básico", "tipo_suscripcion": "Compartido",
        "cupos_totales": 3, "precio_mensual_clp": 1000, "estimacion_cosecha_kg": 10, "imagen": foto,
    }).json()
    assert r["status"] == "error"


def test_imagen_fuera_del_catalogo_se_rechaza(cliente, token_agricultor):
    r = cliente.post("/api/arboles", headers=auth(token_agricultor), json={
        "especie": "palto_hass", "ubicacion": "Curicó", "plan": "Básico", "tipo_suscripcion": "Compartido",
        "cupos_totales": 3, "precio_mensual_clp": 1000, "estimacion_cosecha_kg": 10,
        "imagen": "https://sitio-malicioso.example/foto.jpg",
    }).json()
    assert r["status"] == "error"


def test_html_en_las_entradas_se_rechaza(cliente):
    r = cliente.post("/api/register", json={
        "nombre": "<script>alert(1)</script>", "email": "xss@ejemplo.cl", "password": "clave-segura-1", "rol": "comprador",
    })
    assert r.json()["status"] == "error"


def test_no_se_ven_datos_de_otro_usuario(cliente, nuevo_comprador, token_comprador):
    _, _, token = nuevo_comprador
    id_ajeno = int(token_comprador.split(".")[0])
    assert cliente.get(f"/api/usuario/{id_ajeno}", headers=auth(token)).json()["status"] == "error"
    assert cliente.get(f"/api/suscripciones/usuario/{id_ajeno}", headers=auth(token)).status_code in (200, 403)
    r = cliente.get(f"/api/suscripciones/usuario/{id_ajeno}", headers=auth(token)).json()
    assert r.get("status") == "error" or r.get("detail", {}).get("status") == "error"


def test_solo_el_productor_ve_sus_suscriptores(cliente, token_agricultor, token_comprador):
    id_agricultor = int(token_agricultor.split(".")[0])
    r = cliente.get(f"/api/mis-arboles/{id_agricultor}/suscriptores", headers=auth(token_comprador))
    cuerpo = r.json()
    assert r.status_code == 403 or cuerpo.get("status") == "error" or cuerpo.get("detail", {}).get("status") == "error"


def test_cuentas_demo_no_se_modifican(cliente, token_comprador):
    r = cliente.put("/api/perfil", headers=auth(token_comprador), json={
        "nombre": "Nombre Cambiado", "email": "comprador@agrocolab.cl",
    }).json()
    assert r["status"] == "error"
    r = cliente.delete("/api/usuario/comprador@agrocolab.cl", headers=auth(token_comprador)).json()
    assert r["status"] == "error"


def test_eliminar_cuenta_borra_sus_pagos(cliente, token_agricultor, nuevo_comprador):
    from database import Pago, SessionLocal
    email, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor)
    usuario = int(token.split(".")[0])
    assert pagar(cliente, token, arbol_id=arbol)["status"] == "success"
    assert cliente.delete(f"/api/usuario/{email}", headers=auth(token)).json()["status"] == "success"
    db = SessionLocal()
    try:
        assert db.query(Pago).filter(Pago.usuario_id == usuario).count() == 0
    finally:
        db.close()


def test_limite_de_intentos_de_login(cliente):
    respuestas = [
        cliente.post("/api/login", json={"email": "comprador@agrocolab.cl", "password": "mala", "rol": "comprador"})
        for _ in range(9)
    ]
    assert respuestas[-1].status_code == 429


def test_estado_no_expone_claves(cliente):
    r = cliente.get("/api/estado").json()
    assert r["status"] == "success"
    assert set(r) <= {"status", "correo_real", "modo_desarrollo", "variables"}
