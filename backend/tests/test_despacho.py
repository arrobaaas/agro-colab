"""El despacho guarda el celular con su código de país y el código postal."""

import pytest

from conftest import auth, pagar

PEDIDO = {
    "plan_nombre": "Canasta Huerto Esencial", "tipo_destino": "particular", "direccion": "Av. Siempre Viva 742",
    "comuna": "Maipú", "codigo_postal": "9250000", "telefono_codigo": "+56", "telefono": "9 1234-5678",
    "frecuencia_entrega": "semanal",
}


def _pedir(cliente, token, **cambios):
    pago = pagar(cliente, token, tipo="plan", plan_nombre="Canasta Huerto Esencial")["pago"]["id"]
    return cliente.post("/api/pedidos", headers=auth(token), json={**PEDIDO, "pago_id": pago, **cambios})


def test_el_pedido_guarda_el_contacto_de_despacho(cliente, nuevo_comprador):
    _, _, token = nuevo_comprador
    pedido = _pedir(cliente, token).json()["pedido"]
    assert (pedido["codigo_postal"], pedido["telefono_codigo"], pedido["telefono"]) == ("9250000", "+56", "912345678")
    guardado = cliente.get(f"/api/pedidos/{pedido['id']}", headers=auth(token)).json()
    assert guardado["telefono"] == "912345678"
    exportado = cliente.get("/api/perfil/exportar", headers=auth(token)).json()
    assert exportado["pedidos"][0]["codigo_postal"] == "9250000"


def test_modificar_la_logistica_cambia_el_contacto(cliente, nuevo_comprador):
    _, _, token = nuevo_comprador
    pedido = _pedir(cliente, token).json()["pedido"]["id"]
    datos = {k: v for k, v in PEDIDO.items() if k != "plan_nombre"}
    r = cliente.put(f"/api/pedidos/{pedido}", headers=auth(token), json={
        **datos, "telefono_codigo": "+54", "telefono": "1123456789", "codigo_postal": "8320000",
    }).json()["pedido"]
    assert (r["telefono_codigo"], r["telefono"], r["codigo_postal"]) == ("+54", "1123456789", "8320000")


@pytest.mark.parametrize("campo", ["codigo_postal", "telefono_codigo", "telefono"])
def test_los_datos_de_contacto_son_obligatorios(cliente, nuevo_comprador, campo):
    _, _, token = nuevo_comprador
    cuerpo = {k: v for k, v in PEDIDO.items() if k != campo}
    assert cliente.post("/api/pedidos", headers=auth(token), json=cuerpo).status_code == 422


@pytest.mark.parametrize("cambios", [
    {"codigo_postal": "123"},
    {"codigo_postal": "12345678"},
    {"codigo_postal": "<script>"},
    {"codigo_postal": "٠١٢٣٤٥٦"},
    {"telefono_codigo": "+999"},
    {"telefono": "12345"},
    {"telefono": "abc1234567"},
    {"telefono": "<b>912345678</b>"},
    {"telefono_codigo": "+54", "telefono": "1" * 16},
])
def test_datos_invalidos_responden_422_sin_gastar_el_pago(cliente, nuevo_comprador, cambios):
    _, _, token = nuevo_comprador
    r = cliente.post("/api/pedidos", headers=auth(token), json={**PEDIDO, "pago_id": 1, **cambios})
    assert r.status_code == 422 and r.json()["status"] == "error"


@pytest.mark.parametrize("telefono", ["812345678", "91234567", "9123456789"])
def test_celular_de_chile_exige_9_digitos_y_empezar_con_9(cliente, nuevo_comprador, telefono):
    _, _, token = nuevo_comprador
    r = _pedir(cliente, token, telefono=telefono)
    assert r.status_code == 422 and "9 dígitos" in r.json()["mensaje"]


def test_otros_paises_no_usan_la_regla_de_chile(cliente, nuevo_comprador):
    _, _, token = nuevo_comprador
    assert _pedir(cliente, token, telefono_codigo="+51", telefono="812345678").status_code == 201
