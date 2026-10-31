"""Pasarela de pago simulada, adopción de árboles y planes."""

from conftest import TARJETA_SIN_FONDOS, auth, pagar, publicar_arbol


def mis_arboles(cliente, token, usuario_id):
    return [a["arbol_id"] for a in cliente.get(f"/api/suscripciones/usuario/{usuario_id}", headers=auth(token)).json()["arboles"]]


def usuario_id(token):
    return int(token.split(".")[0])


def test_pago_aprobado_adopta_el_arbol(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor, precio=15000)

    r = pagar(cliente, token, arbol_id=arbol)
    assert r["status"] == "success"
    assert r["pago"]["monto_clp"] == 15000  # el monto lo fija el servidor
    assert r["pago"]["ultimos4"] == "4242" and r["pago"]["marca"] == "Visa"
    assert arbol in mis_arboles(cliente, token, usuario_id(token))


def test_pago_rechazado_no_adopta(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor)

    r = pagar(cliente, token, arbol_id=arbol, numero=TARJETA_SIN_FONDOS)
    assert r["status"] == "rechazado"
    assert arbol not in mis_arboles(cliente, token, usuario_id(token))


def test_no_se_puede_adoptar_dos_veces(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor)
    assert pagar(cliente, token, arbol_id=arbol)["status"] == "success"
    assert pagar(cliente, token, arbol_id=arbol)["status"] == "error"


def test_sin_cupos_no_se_cobra(cliente, token_agricultor, token_comprador, nuevo_comprador):
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor, cupos=1)
    assert pagar(cliente, token_comprador, arbol_id=arbol)["status"] == "success"

    r = pagar(cliente, token, arbol_id=arbol)
    assert r["status"] == "error"
    pagos = cliente.get("/api/pagos", headers=auth(token)).json()["pagos"]
    assert not [p for p in pagos if p["arbol_id"] == arbol]


def test_tarjetas_invalidas(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor)
    # Luhn inválido, tarjeta real (no de prueba) y tarjeta vencida, cada una
    # rechazada por su propio motivo
    luhn = pagar(cliente, token, arbol_id=arbol, numero="4242 4242 4242 4241")
    assert luhn["status"] == "error" and "no es válido" in luhn["mensaje"]
    real = pagar(cliente, token, arbol_id=arbol, numero="4111 1111 1111 1111")
    assert real["status"] == "error" and "tarjetas de prueba" in real["mensaje"]
    vencida = pagar(cliente, token, arbol_id=arbol, vencimiento="01/20")
    assert vencida["status"] == "error" and "vencida" in vencida["mensaje"]
    # Ninguna quedó registrada
    assert cliente.get("/api/pagos", headers=auth(token)).json()["pagos"] == []


def test_numero_completo_y_cvv_no_se_guardan(cliente, token_agricultor, nuevo_comprador):
    from database import Pago, SessionLocal
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor)
    pago_id = pagar(cliente, token, arbol_id=arbol)["pago"]["id"]
    db = SessionLocal()
    try:
        pago = db.query(Pago).filter(Pago.id == pago_id).first()
        valores = " ".join(str(v) for v in vars(pago).values())
    finally:
        db.close()
    assert "4242424242424242" not in valores.replace(" ", "")


def test_agricultor_no_puede_pagar(cliente, token_agricultor):
    r = pagar(cliente, token_agricultor, tipo="plan", plan_nombre="Canasta Huerto Esencial")
    assert r["status"] == "error"


PEDIDO = {
    "plan_nombre": "Canasta Huerto Esencial", "cliente_nombre": "Persona", "telefono": "+56911112222",
    "email": "persona@ejemplo.cl", "tipo_destino": "particular", "direccion": "Av. Siempre Viva 742",
    "comuna": "Maipú", "frecuencia_entrega": "semanal",
}


def test_plan_exige_pago_y_no_se_reutiliza(cliente, nuevo_comprador):
    _, _, token = nuevo_comprador
    assert cliente.post("/api/pedidos", headers=auth(token), json=PEDIDO).json()["status"] == "error"

    pago_id = pagar(cliente, token, tipo="plan", plan_nombre="Canasta Huerto Esencial")["pago"]["id"]
    # El pago de un plan no sirve para otro plan
    otro = {**PEDIDO, "plan_nombre": "Lote Gastronómico B2B", "pago_id": pago_id}
    assert cliente.post("/api/pedidos", headers=auth(token), json=otro).json()["status"] == "error"

    con_pago = {**PEDIDO, "pago_id": pago_id}
    assert cliente.post("/api/pedidos", headers=auth(token), json=con_pago).json()["status"] == "success"
    assert cliente.post("/api/pedidos", headers=auth(token), json=con_pago).json()["status"] == "error"


def test_no_se_usa_el_pago_de_otra_persona(cliente, token_comprador, nuevo_comprador):
    _, _, token = nuevo_comprador
    pago_ajeno = pagar(cliente, token_comprador, tipo="plan", plan_nombre="Canasta Huerto Esencial")["pago"]["id"]
    r = cliente.post("/api/pedidos", headers=auth(token), json={**PEDIDO, "pago_id": pago_ajeno}).json()
    assert r["status"] == "error"


def test_cancelar_libera_el_cupo(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    arbol = publicar_arbol(cliente, token_agricultor, cupos=1)
    assert pagar(cliente, token, arbol_id=arbol)["status"] == "success"
    assert cliente.post("/api/cancelar-suscripcion", headers=auth(token), json={"tree_id": arbol}).json()["status"] == "success"
    catalogo = {a["id"]: a for a in cliente.get("/api/arboles").json()}
    assert catalogo[arbol]["cupos_ocupados"] == 0
