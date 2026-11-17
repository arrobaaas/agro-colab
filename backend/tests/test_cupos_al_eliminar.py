"""Eliminar una cuenta debe devolver los cupos que ocupaban sus adopciones.

Antes, el borrado quitaba las suscripciones pero no descontaba
arboles.cupos_ocupados: el cupo quedaba ocupado por una cuenta que ya no
existía y nadie más podía adoptarlo.
"""

from conftest import auth, pagar, publicar_arbol, registrar


def cupos_ocupados(cliente, arbol_id):
    """Lo que muestra la API (cuenta suscripciones) y lo que usa la reserva
    (la columna) tienen que coincidir."""
    from database import Arbol, SessionLocal
    mostrado = cliente.get(f"/api/arboles/{arbol_id}").json()["cupos_ocupados"]
    db = SessionLocal()
    try:
        columna = db.query(Arbol).filter(Arbol.id == arbol_id).one().cupos_ocupados
    finally:
        db.close()
    assert mostrado == columna, f"la API muestra {mostrado} y la columna dice {columna}"
    return columna


def id_del_suscriptor(arbol_id):
    from database import SessionLocal, Suscripcion
    db = SessionLocal()
    try:
        return db.query(Suscripcion).filter(Suscripcion.arbol_id == arbol_id).one().usuario_id
    finally:
        db.close()


def test_eliminar_la_propia_cuenta_libera_sus_cupos(cliente, token_agricultor):
    arbol = publicar_arbol(cliente, token_agricultor, cupos=3)
    _, password, token = registrar(cliente, "comprador")
    assert pagar(cliente, token, arbol_id=arbol)["status"] == "success"
    assert cupos_ocupados(cliente, arbol) == 1

    assert cliente.request("DELETE", "/api/perfil", headers=auth(token), json={"password": password}).status_code == 200
    assert cupos_ocupados(cliente, arbol) == 0


def test_el_administrador_al_eliminar_tambien_libera_los_cupos(cliente, token_agricultor, token_admin):
    arbol = publicar_arbol(cliente, token_agricultor, cupos=3)
    _, _, token = registrar(cliente, "comprador")
    assert pagar(cliente, token, arbol_id=arbol)["status"] == "success"
    usuario_id = id_del_suscriptor(arbol)

    assert cliente.delete(f"/api/admin/usuarios/{usuario_id}", headers=auth(token_admin)).status_code == 200
    assert cupos_ocupados(cliente, arbol) == 0


def test_el_cupo_liberado_se_puede_volver_a_adoptar(cliente, token_agricultor):
    # Árbol exclusivo: si el cupo no se libera, nadie más puede adoptarlo nunca
    arbol = publicar_arbol(cliente, token_agricultor, cupos=1)
    _, password, token = registrar(cliente, "comprador")
    assert pagar(cliente, token, arbol_id=arbol)["status"] == "success"
    assert cliente.request("DELETE", "/api/perfil", headers=auth(token), json={"password": password}).status_code == 200

    _, _, otro = registrar(cliente, "comprador")
    r = pagar(cliente, otro, arbol_id=arbol)
    assert r["status"] == "success", r
