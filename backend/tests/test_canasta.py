"""Pago único de toda la canasta (POST /api/pagos/canasta)."""

from conftest import TARJETA_SIN_FONDOS, auth, publicar_arbol
from test_pagos import PEDIDO, mis_arboles, usuario_id

TARJETA = {"numero": "4242 4242 4242 4242", "titular": "Persona", "vencimiento": "12/29", "cvv": "123"}


def pagar_canasta(cliente, token, items, **tarjeta):
    return cliente.post("/api/pagos/canasta", headers=auth(token), json={"items": items, **TARJETA, **tarjeta}).json()


def arbol(id_):
    return {"tipo": "arbol", "arbol_id": id_}


def plan(nombre="Canasta Huerto Esencial"):
    return {"tipo": "plan", "plan_nombre": nombre}


def test_un_solo_cobro_para_toda_la_canasta(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    a1 = publicar_arbol(cliente, token_agricultor, precio=12000)
    a2 = publicar_arbol(cliente, token_agricultor, precio=8000)

    r = pagar_canasta(cliente, token, [arbol(a1), arbol(a2), plan()])
    assert r["status"] == "success"
    assert len(r["pagos"]) == 3
    # El total lo fija el servidor y todos los pagos comparten la transacción
    assert r["total_clp"] == 20000 + r["pagos"][2]["monto_clp"]
    assert [p["transaccion"] for p in r["pagos"]] == [f"{r['transaccion']}-{n}" for n in (1, 2, 3)]
    assert {p["codigo_autorizacion"] for p in r["pagos"]} == {r["codigo_autorizacion"]}
    assert {a1, a2} <= set(mis_arboles(cliente, token, usuario_id(token)))


def test_el_pago_del_plan_sirve_para_su_pedido(cliente, nuevo_comprador):
    _, _, token = nuevo_comprador
    pago_id = pagar_canasta(cliente, token, [plan()])["pagos"][0]["id"]
    r = cliente.post("/api/pedidos", headers=auth(token), json={**PEDIDO, "pago_id": pago_id}).json()
    assert r["status"] == "success"


def test_si_un_arbol_falla_no_se_cobra_nada(cliente, token_agricultor, token_comprador, nuevo_comprador):
    _, _, token = nuevo_comprador
    libre = publicar_arbol(cliente, token_agricultor, cupos=3)
    lleno = publicar_arbol(cliente, token_agricultor, cupos=1)
    assert pagar_canasta(cliente, token_comprador, [arbol(lleno)])["status"] == "success"

    r = pagar_canasta(cliente, token, [arbol(libre), arbol(lleno), plan()])
    assert r["status"] == "error"
    assert cliente.get("/api/pagos", headers=auth(token)).json()["pagos"] == []
    assert libre not in mis_arboles(cliente, token, usuario_id(token))
    catalogo = {a["id"]: a for a in cliente.get("/api/arboles").json()}
    assert catalogo[libre]["cupos_ocupados"] == 0


def test_tarjeta_rechazada_no_adopta_nada(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    a1 = publicar_arbol(cliente, token_agricultor)
    r = pagar_canasta(cliente, token, [arbol(a1), plan()], numero=TARJETA_SIN_FONDOS)
    assert r["status"] == "rechazado"
    assert a1 not in mis_arboles(cliente, token, usuario_id(token))
    pagos = cliente.get("/api/pagos", headers=auth(token)).json()["pagos"]
    assert len(pagos) == 2 and {p["estado"] for p in pagos} == {"rechazado"}


def test_tarjeta_invalida_no_registra_nada(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    a1 = publicar_arbol(cliente, token_agricultor)
    r = pagar_canasta(cliente, token, [arbol(a1)], numero="4111 1111 1111 1111")
    assert r["status"] == "error" and "tarjetas de prueba" in r["mensaje"]
    assert cliente.get("/api/pagos", headers=auth(token)).json()["pagos"] == []


def test_arbol_repetido_o_canasta_vacia(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    a1 = publicar_arbol(cliente, token_agricultor, cupos=3)
    assert pagar_canasta(cliente, token, [arbol(a1), arbol(a1)])["status"] == "error"
    r = cliente.post("/api/pagos/canasta", headers=auth(token), json={"items": [], **TARJETA})
    assert r.status_code == 422
    r = cliente.post("/api/pagos/canasta", headers=auth(token), json={"items": [plan()] * 11, **TARJETA})
    assert r.status_code == 422


def test_plan_inexistente_y_agricultor(cliente, token_agricultor, nuevo_comprador):
    _, _, token = nuevo_comprador
    assert pagar_canasta(cliente, token, [plan("Plan inventado")])["status"] == "error"
    assert pagar_canasta(cliente, token_agricultor, [plan()])["status"] == "error"


def test_sin_sesion_no_paga(cliente):
    r = cliente.post("/api/pagos/canasta", json={"items": [plan()], **TARJETA})
    assert r.status_code == 401


def test_cuenta_demo_no_paga_el_plan_b2b(cliente, token_comprador_demo):
    """El plan B2B exige datos comerciales, que la cuenta demo no admite: se
    rechaza antes de cobrar y no queda un pago sin despacho posible."""
    antes = len(cliente.get("/api/pagos", headers=auth(token_comprador_demo)).json()["pagos"])
    r = pagar_canasta(cliente, token_comprador_demo, [plan(), plan("Lote Gastronómico B2B")])
    assert r["status"] == "error" and "demostración" in r["mensaje"]
    r = cliente.post("/api/pagos", headers=auth(token_comprador_demo),
                     json={"tipo": "plan", "plan_nombre": "Lote Gastronómico B2B", **TARJETA}).json()
    assert r["status"] == "error"
    assert len(cliente.get("/api/pagos", headers=auth(token_comprador_demo)).json()["pagos"]) == antes
    # Un plan particular sí puede pagarlo
    assert pagar_canasta(cliente, token_comprador_demo, [plan()])["status"] == "success"
