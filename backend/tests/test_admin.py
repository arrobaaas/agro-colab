"""Panel de administración: solo el administrador entra, ve las cuentas y
los árboles de cada agricultor, y edita o elimina cuentas comunes."""

from conftest import auth, login, publicar_arbol, ADMIN_EMAIL


def id_de(cliente, token_admin, email):
    usuarios = cliente.get("/api/admin/usuarios", headers=auth(token_admin)).json()["usuarios"]
    return next(u["id"] for u in usuarios if u["email"] == email)


def test_solo_el_administrador_entra_al_panel(cliente, token_comprador, token_agricultor):
    for token in (token_comprador, token_agricultor):
        r = cliente.get("/api/admin/usuarios", headers=auth(token))
        assert r.status_code == 403
    assert cliente.get("/api/admin/usuarios").status_code == 401


def test_nadie_se_registra_como_administrador(cliente):
    r = cliente.post("/api/register", json={
        "nombre": "Intruso", "email": "intruso@ejemplo.cl", "password": "clave-segura-1", "rol": "administrador",
    })
    assert r.status_code == 422


def test_ve_las_cuentas_y_los_arboles_de_un_agricultor(cliente, token_admin, nuevo_agricultor):
    email, _, token = nuevo_agricultor
    arbol_id = publicar_arbol(cliente, token)

    usuarios = cliente.get("/api/admin/usuarios", headers=auth(token_admin)).json()["usuarios"]
    fila = next(u for u in usuarios if u["email"] == email)
    assert fila["rol"] == "agricultor" and fila["arboles_publicados"] == 1
    assert not fila["protegida"]
    assert "password" not in fila
    assert next(u for u in usuarios if u["email"] == ADMIN_EMAIL)["protegida"]

    detalle = cliente.get(f"/api/admin/usuarios/{fila['id']}", headers=auth(token_admin)).json()
    assert [a["id"] for a in detalle["arboles"]] == [arbol_id]


def test_edita_una_cuenta_y_cambia_su_contrasena(cliente, token_admin, nuevo_comprador):
    email, password, token = nuevo_comprador
    usuario_id = id_de(cliente, token_admin, email)
    r = cliente.put(f"/api/admin/usuarios/{usuario_id}", headers=auth(token_admin), json={
        "nombre": "Nombre Corregido", "email": email, "telefono": "+56 9 1111 2222",
        "direccion": "Calle Nueva 123", "verificado": True, "password": "clave-nueva-123",
    }).json()
    assert r["status"] == "success", r

    detalle = cliente.get(f"/api/admin/usuarios/{usuario_id}", headers=auth(token_admin)).json()["usuario"]
    assert detalle["nombre"] == "Nombre Corregido" and detalle["telefono"] == "+56 9 1111 2222"
    # La contraseña nueva funciona, la anterior no, y sus sesiones se cerraron
    assert cliente.get("/api/pedidos", headers=auth(token)).status_code == 401
    assert cliente.post("/api/login", json={"email": email, "password": password, "rol": "comprador"}).json()["status"] == "error"
    login(cliente, email, "clave-nueva-123")


def test_no_repite_el_correo_de_otra_cuenta(cliente, token_admin, nuevo_comprador):
    email, _, _ = nuevo_comprador
    r = cliente.put(f"/api/admin/usuarios/{id_de(cliente, token_admin, email)}", headers=auth(token_admin), json={
        "nombre": "Persona", "email": "COMPRADOR@agrocolab.cl", "verificado": True,
    }).json()
    assert r["status"] == "error"


def test_elimina_una_cuenta_con_sus_arboles(cliente, token_admin, nuevo_agricultor):
    email, password, token = nuevo_agricultor
    arbol_id = publicar_arbol(cliente, token)
    usuario_id = id_de(cliente, token_admin, email)

    r = cliente.delete(f"/api/admin/usuarios/{usuario_id}", headers=auth(token_admin)).json()
    assert r["status"] == "success", r
    assert cliente.get(f"/api/admin/usuarios/{usuario_id}", headers=auth(token_admin)).json()["status"] == "error"
    assert arbol_id not in [a["id"] for a in cliente.get("/api/arboles").json()]


def test_cuentas_demo_y_administradores_protegidas(cliente, token_admin):
    for email in ("comprador@agrocolab.cl", ADMIN_EMAIL):
        usuario_id = id_de(cliente, token_admin, email)
        assert cliente.delete(f"/api/admin/usuarios/{usuario_id}", headers=auth(token_admin)).json()["status"] == "error"
        r = cliente.put(f"/api/admin/usuarios/{usuario_id}", headers=auth(token_admin), json={
            "nombre": "Cambio", "email": email, "verificado": True,
        }).json()
        assert r["status"] == "error"
