"""Cada resultado usa el código HTTP que corresponde, y todos los errores
tienen la misma forma: {status, mensaje}."""

import catalogo
from conftest import CONSENTIMIENTO, ADMIN_EMAIL, TARJETA_OK, TARJETA_SIN_FONDOS, auth, publicar_arbol


def arbol_valido(**cambios):
    foto = sorted(catalogo.fotos_permitidas("palto_hass"))[0]
    return {
        "especie": "palto_hass", "ubicacion": "Curicó, Maule", "plan": "Básico", "tipo_suscripcion": "Compartido",
        "cupos_totales": 5, "precio_mensual_clp": 1000, "estimacion_cosecha_kg": 10, "imagen": foto, **cambios,
    }


def pago(tipo="plan", numero=TARJETA_OK, **cambios):
    return {
        "tipo": tipo, "plan_nombre": "Canasta Huerto Esencial" if tipo == "plan" else None, "numero": numero,
        "titular": "Persona", "vencimiento": "12/39", "cvv": "123", **cambios,
    }


PEDIDO = {
    "plan_nombre": "Canasta Huerto Esencial", "tipo_destino": "particular", "direccion": "Av. Siempre Viva 742",
    "comuna": "Maipú", "codigo_postal": "8320000", "telefono_codigo": "+56", "telefono": "912345678", "frecuencia_entrega": "semanal",
}
LOGISTICA = {"tipo_destino": "particular", "direccion": "Calle Nueva 1", "comuna": "Macul", "codigo_postal": "8320000", "telefono_codigo": "+56", "telefono": "912345678", "frecuencia_entrega": "mensual"}


def error(respuesta, codigo, estado="error"):
    assert respuesta.status_code == codigo, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["status"] == estado and cuerpo["mensaje"], cuerpo
    assert "detail" not in cuerpo
    return cuerpo


# ------------------------------------ éxitos

def test_crear_responde_201(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    r = cliente.post("/api/arboles", headers=auth(token_agricultor), json=arbol_valido())
    assert r.status_code == 201 and r.json()["arbol"]["id"]

    r = cliente.post("/api/pagos", headers=auth(token), json=pago())
    assert r.status_code == 201
    r = cliente.post("/api/pedidos", headers=auth(token), json={**PEDIDO, "pago_id": r.json()["pago"]["id"]})
    assert r.status_code == 201 and r.json()["pedido"]["codigo_seguimiento"].startswith("AGRO-")


def test_registro_responde_202_exista_o_no_el_correo(cliente):
    nueva = cliente.post("/api/register", json={**CONSENTIMIENTO,
        "nombre": "Persona Nueva", "email": "contrato-202@ejemplo.cl", "password": "clave-segura-1", "rol": "comprador",
    })
    repetida = cliente.post("/api/register", json={**CONSENTIMIENTO,
        "nombre": "Otra Persona", "email": "comprador@agrocolab.cl", "password": "clave-segura-1", "rol": "comprador",
    })
    assert nueva.status_code == repetida.status_code == 202


def test_lectura_individual_de_recursos(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor)
    assert cliente.get(f"/api/arboles/{arbol}").json()["id"] == arbol

    pago_id = cliente.post("/api/pagos", headers=auth(token), json=pago()).json()["pago"]["id"]
    assert cliente.get(f"/api/pagos/{pago_id}", headers=auth(token)).json()["pago"]["id"] == pago_id
    pedido = cliente.post("/api/pedidos", headers=auth(token), json={**PEDIDO, "pago_id": pago_id}).json()["pedido"]["id"]
    assert cliente.get(f"/api/pedidos/{pedido}", headers=auth(token)).json()["id"] == pedido


def test_ciclo_completo_del_pedido_persiste(cliente, nuevo_comprador):
    _, _, token = nuevo_comprador
    pago_id = cliente.post("/api/pagos", headers=auth(token), json=pago()).json()["pago"]["id"]
    pedido = cliente.post("/api/pedidos", headers=auth(token), json={**PEDIDO, "pago_id": pago_id}).json()["pedido"]["id"]

    r = cliente.put(f"/api/pedidos/{pedido}", headers=auth(token), json=LOGISTICA)
    assert r.status_code == 200
    assert cliente.get(f"/api/pedidos/{pedido}", headers=auth(token)).json()["comuna"] == "Macul"

    assert cliente.delete(f"/api/pedidos/{pedido}", headers=auth(token)).status_code == 200
    error(cliente.get(f"/api/pedidos/{pedido}", headers=auth(token)), 404)
    assert cliente.get("/api/pedidos", headers=auth(token)).json() == []


# ------------------------------------ 400, 401, 402

def test_codigo_de_verificacion_incorrecto_responde_400(cliente):
    error(cliente.post("/api/verificar-cuenta", json={"email": "nadie@ejemplo.cl", "codigo": "000000", "password": "x"}), 400)
    error(cliente.post("/api/restablecer-contrasena", json={
        "email": "nadie@ejemplo.cl", "codigo": "000000", "password": "clave-segura-1",
    }), 400)


def test_sin_credenciales_validas_responde_401(cliente):
    error(cliente.post("/api/arboles", json=arbol_valido()), 401)
    error(cliente.get("/api/pedidos", headers=auth("token.falso.firma")), 401)
    error(cliente.post("/api/login", json={"email": "nadie@ejemplo.cl", "password": "mala", "rol": "comprador"}), 401)


def test_sin_token_se_responde_401_antes_de_validar_el_cuerpo(cliente):
    """La autenticación se resuelve antes que el cuerpo: no se le informa a
    quien no tiene sesión qué le falta a su petición."""
    error(cliente.post("/api/arboles", json={}), 401)


def test_tarjeta_rechazada_responde_402_con_el_comprobante(cliente, nuevo_comprador):
    _, _, token = nuevo_comprador
    cuerpo = error(cliente.post("/api/pagos", headers=auth(token), json=pago(numero=TARJETA_SIN_FONDOS)), 402, "rechazado")
    assert cuerpo["pago"]["estado"] == "rechazado" and cuerpo["pago"]["ultimos4"] == "0002"


# ------------------------------------ 403

def test_sin_permiso_responde_403(cliente, token_comprador, token_agricultor, nuevo_agricultor):
    _, _, token_otro = nuevo_agricultor
    error(cliente.post("/api/arboles", headers=auth(token_comprador), json=arbol_valido()), 403)
    error(cliente.post("/api/pagos", headers=auth(token_agricultor), json=pago()), 403)
    error(cliente.post("/api/pedidos", headers=auth(token_agricultor), json=PEDIDO), 403)
    error(cliente.get("/api/admin/usuarios", headers=auth(token_comprador)), 403)

    arbol = publicar_arbol(cliente, token_agricultor)
    error(cliente.put(f"/api/arboles/{arbol}", headers=auth(token_otro), json=arbol_valido()), 403)
    error(cliente.delete(f"/api/arboles/{arbol}", headers=auth(token_otro)), 403)


def test_despacho_de_un_arbol_no_adoptado_responde_403(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor)
    error(cliente.post("/api/pedidos", headers=auth(token), json={**PEDIDO, "tipo": "arbol", "arbol_id": arbol}), 403)


def test_cambiar_contrasena_sin_la_actual_responde_403(cliente, nuevo_comprador):
    email, _, token = nuevo_comprador
    error(cliente.put("/api/perfil", headers=auth(token), json={
        "nombre": "Persona", "email": email, "password": "otra-clave-segura",
    }), 403)
    error(cliente.put("/api/perfil", headers=auth(token), json={"nombre": "Persona", "email": "otro@ejemplo.cl"}), 403)


# ------------------------------------ 404, 405

def test_recurso_inexistente_responde_404(cliente, token_agricultor, token_comprador, token_admin):
    error(cliente.get("/api/arboles/999999"), 404)
    error(cliente.put("/api/arboles/999999", headers=auth(token_agricultor), json=arbol_valido()), 404)
    error(cliente.delete("/api/arboles/999999", headers=auth(token_agricultor)), 404)
    error(cliente.delete("/api/arboles/999999/suscripcion", headers=auth(token_comprador)), 404)
    error(cliente.delete("/api/suscripciones/999999", headers=auth(token_agricultor)), 404)
    error(cliente.get("/api/pedidos/999999", headers=auth(token_comprador)), 404)
    error(cliente.put("/api/pedidos/999999", headers=auth(token_comprador), json=LOGISTICA), 404)
    error(cliente.delete("/api/pedidos/999999", headers=auth(token_comprador)), 404)
    error(cliente.get("/api/pagos/999999", headers=auth(token_comprador)), 404)
    error(cliente.get("/api/usuario/999999", headers=auth(token_comprador)), 404)
    error(cliente.get("/api/admin/usuarios/999999", headers=auth(token_admin)), 404)
    error(cliente.post("/api/pagos", headers=auth(token_comprador), json=pago("arbol", arbol_id=999999)), 404)


def test_recursos_ajenos_responden_404_sin_revelar_que_existen(cliente, nuevo_comprador, token_comprador):
    _, _, token = nuevo_comprador
    pago_id = cliente.post("/api/pagos", headers=auth(token), json=pago()).json()["pago"]["id"]
    pedido = cliente.post("/api/pedidos", headers=auth(token), json={**PEDIDO, "pago_id": pago_id}).json()["pedido"]["id"]
    error(cliente.get(f"/api/pagos/{pago_id}", headers=auth(token_comprador)), 404)
    error(cliente.get(f"/api/pedidos/{pedido}", headers=auth(token_comprador)), 404)
    error(cliente.delete(f"/api/pedidos/{pedido}", headers=auth(token_comprador)), 404)


def test_no_suscrito_cancela_responde_404(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor)
    error(cliente.delete(f"/api/arboles/{arbol}/suscripcion", headers=auth(token)), 404)


def test_ruta_y_verbo_inexistentes(cliente):
    error(cliente.get("/api/nada"), 404)
    error(cliente.patch("/api/arboles"), 405)


# ------------------------------------ 409

def test_conflictos_con_el_estado_actual_responden_409(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor, cupos=1)
    adopcion = pago("arbol", arbol_id=arbol)

    error(cliente.post("/api/pedidos", headers=auth(token), json=PEDIDO), 409)  # plan sin pago
    assert cliente.post("/api/pagos", headers=auth(token), json=adopcion).status_code == 201
    error(cliente.post("/api/pagos", headers=auth(token), json=adopcion), 409)  # adoptar dos veces
    despacho = {**PEDIDO, "tipo": "arbol", "arbol_id": arbol}
    pedido = cliente.post("/api/pedidos", headers=auth(token), json=despacho)
    assert pedido.status_code == 201
    error(cliente.delete(f"/api/pedidos/{pedido.json()['pedido']['id']}", headers=auth(token)), 409)  # es un despacho


def test_sin_cupos_responde_409_y_no_cobra(cliente, token_agricultor, token_comprador, nuevo_comprador):
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor, cupos=1)
    assert cliente.post("/api/pagos", headers=auth(token_comprador), json=pago("arbol", arbol_id=arbol)).status_code == 201
    error(cliente.post("/api/pagos", headers=auth(token), json=pago("arbol", arbol_id=arbol)), 409)
    assert cliente.get("/api/pagos", headers=auth(token)).json()["pagos"] == []


def test_lo_vendido_no_cambia_con_suscriptores_responde_409(cliente, nuevo_agricultor, nuevo_comprador, token_comprador):
    _, _, token_productor = nuevo_agricultor
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_productor, cupos=5, precio=1000)
    for t in (token, token_comprador):
        assert cliente.post("/api/pagos", headers=auth(t), json=pago("arbol", arbol_id=arbol)).status_code == 201
    error(cliente.put(f"/api/arboles/{arbol}", headers=auth(token_productor), json=arbol_valido(precio_mensual_clp=999_999)), 409)
    assert cliente.put(f"/api/arboles/{arbol}", headers=auth(token_productor), json=arbol_valido(ubicacion="Otro huerto", estimacion_cosecha_kg=40)).status_code == 200


def test_correo_repetido_en_el_panel_responde_409(cliente, token_admin, nuevo_comprador):
    email, _, _ = nuevo_comprador
    usuarios = cliente.get("/api/admin/usuarios", headers=auth(token_admin)).json()["usuarios"]
    usuario_id = next(u["id"] for u in usuarios if u["email"] == email)
    error(cliente.put(f"/api/admin/usuarios/{usuario_id}", headers=auth(token_admin), json={
        "nombre": "Persona", "email": ADMIN_EMAIL, "verificado": True,
    }), 409)


# ------------------------------------ 422 y 429

def test_datos_invalidos_responden_422(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    error(cliente.post("/api/arboles", headers=auth(token_agricultor), json=arbol_valido(cupos_totales=0)), 422)
    error(cliente.post("/api/arboles", headers=auth(token_agricultor), json=arbol_valido(especie="inexistente")), 422)
    error(cliente.post("/api/arboles", headers=auth(token_agricultor), json=arbol_valido(imagen="https://otro.example/a.jpg")), 422)
    error(cliente.get("/api/arboles/abc"), 422)
    error(cliente.post("/api/pagos", headers=auth(token), json=pago(plan_nombre="Plan Inventado")), 422)
    error(cliente.post("/api/pagos", headers=auth(token), json=pago(numero="4242 4242 4242 4241")), 422)
    error(cliente.post("/api/pedidos", headers=auth(token), json={**PEDIDO, "plan_nombre": "Plan Inventado"}), 422)
    comercial_incompleto = {**PEDIDO, "tipo_destino": "comercial"}
    error(cliente.post("/api/pedidos", headers=auth(token), json=comercial_incompleto), 422)


def test_superar_el_limite_responde_429(cliente):
    respuestas = [
        cliente.post("/api/login", json={"email": "limite@ejemplo.cl", "password": "mala", "rol": "comprador"})
        for _ in range(9)
    ]
    assert [r.status_code for r in respuestas[:8]] == [401] * 8
    error(respuestas[8], 429)


# ------------------------------------ eliminación de cuentas

def test_eliminar_un_agricultor_borra_los_despachos_de_sus_arboles(cliente, token_admin, nuevo_agricultor, nuevo_comprador):
    """Regresión: en PostgreSQL la clave foránea de pedidos.arbol_id hacía
    fallar el borrado con un 500 si otro cliente tenía un despacho del árbol."""
    email_agricultor, _, token_agricultor = nuevo_agricultor
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor)
    assert cliente.post("/api/pagos", headers=auth(token), json=pago("arbol", arbol_id=arbol)).status_code == 201
    despacho = {**PEDIDO, "tipo": "arbol", "arbol_id": arbol}
    assert cliente.post("/api/pedidos", headers=auth(token), json=despacho).status_code == 201

    usuarios = cliente.get("/api/admin/usuarios", headers=auth(token_admin)).json()["usuarios"]
    usuario_id = next(u["id"] for u in usuarios if u["email"] == email_agricultor)
    assert cliente.delete(f"/api/admin/usuarios/{usuario_id}", headers=auth(token_admin)).status_code == 200

    error(cliente.get(f"/api/arboles/{arbol}"), 404)
    assert cliente.get("/api/pedidos", headers=auth(token)).json() == []
    # El comprobante del comprador se conserva
    assert [p["arbol_id"] for p in cliente.get("/api/pagos", headers=auth(token)).json()["pagos"]] == [arbol]


def test_cuenta_eliminada_deja_de_funcionar(cliente, nuevo_comprador):
    email, password, token = nuevo_comprador
    assert cliente.request("DELETE", "/api/perfil", headers=auth(token), json={"password": "clave-segura-1"}).status_code == 200
    error(cliente.get("/api/pedidos", headers=auth(token)), 401)
    error(cliente.post("/api/login", json={"email": email, "password": password, "rol": "comprador"}), 401)


# ------------------------------------ suscriptores y perfiles

def test_el_productor_ve_y_expulsa_a_sus_suscriptores(cliente, nuevo_agricultor, nuevo_comprador, token_agricultor):
    _, _, token_productor = nuevo_agricultor
    email, _, token = nuevo_comprador
    productor_id = int(token_productor.split(".")[0])
    arbol = publicar_arbol(cliente, token_productor, cupos=1)
    assert cliente.post("/api/pagos", headers=auth(token), json=pago("arbol", arbol_id=arbol)).status_code == 201

    fila = cliente.get(f"/api/mis-arboles/{productor_id}/suscriptores", headers=auth(token_productor)).json()[0]
    assert fila["cupos_ocupados"] == 1 and fila["suscriptores"][0]["email"] == email
    suscripcion = fila["suscriptores"][0]["suscripcion_id"]

    # Otro productor no puede expulsarlo ni saber que existe; el dueño sí, y el cupo se libera
    error(cliente.delete(f"/api/suscripciones/{suscripcion}", headers=auth(token_agricultor)), 404)
    assert cliente.delete(f"/api/suscripciones/{suscripcion}", headers=auth(token_productor)).status_code == 200
    assert cliente.get(f"/api/arboles/{arbol}").json()["cupos_ocupados"] == 0
    error(cliente.delete(f"/api/suscripciones/{suscripcion}", headers=auth(token_productor)), 404)


def test_el_productor_ve_el_perfil_de_su_suscriptor_y_de_nadie_mas(cliente, nuevo_agricultor, nuevo_comprador, token_agricultor):
    _, _, token_productor = nuevo_agricultor
    email, _, token = nuevo_comprador
    usuario_id = int(token.split(".")[0])
    arbol = publicar_arbol(cliente, token_productor)

    error(cliente.get(f"/api/usuario/{usuario_id}", headers=auth(token_productor)), 404)
    assert cliente.post("/api/pagos", headers=auth(token), json=pago("arbol", arbol_id=arbol)).status_code == 201
    assert cliente.get(f"/api/usuario/{usuario_id}", headers=auth(token_productor)).json()["email"] == email
    error(cliente.get(f"/api/usuario/{usuario_id}", headers=auth(token_agricultor)), 404)


def test_actualizar_el_perfil_y_la_contrasena(cliente, nuevo_comprador):
    email, password, token = nuevo_comprador
    r = cliente.put("/api/perfil", headers=auth(token), json={
        "nombre": "Nombre Nuevo", "email": email, "telefono": "+56 9 2222 3333",
        "password": "clave-nueva-456", "password_actual": password,
    })
    assert r.status_code == 200 and r.json()["user"]["nombre"] == "Nombre Nuevo"
    # El token anterior deja de servir y se entrega uno nuevo
    error(cliente.get("/api/pedidos", headers=auth(token)), 401)
    assert cliente.get("/api/pedidos", headers=auth(r.json()["user"]["token"])).status_code == 200


# ------------------------------------ monitoreo

def test_panel_de_monitoreo_exige_su_token(cliente, monkeypatch):
    monkeypatch.delenv("MONITOREO_TOKEN", raising=False)
    error(cliente.get("/api/seguridad/resumen"), 404)  # sin token configurado, el panel no existe

    secreto = "token-de-pruebas-de-veinticuatro"
    monkeypatch.setenv("MONITOREO_TOKEN", secreto)
    error(cliente.get("/api/seguridad/resumen", headers={"X-Monitoreo-Token": "incorrecto"}), 401)
    r = cliente.get("/api/seguridad/resumen", headers={"X-Monitoreo-Token": secreto})
    assert r.status_code == 200 and "por_severidad" in r.json()


def test_reporte_de_csp_responde_204(cliente):
    r = cliente.post("/api/seguridad/csp", json={"directiva": "script-src", "bloqueado": "inline", "pagina": "/"})
    assert r.status_code == 204 and not r.content
