"""Registro, inicio de sesión, tokens y recuperación de contraseña."""

from conftest import auth, login


def test_login_cuenta_demo(cliente):
    r = cliente.post("/api/login", json={"email": "comprador@agrocolab.cl", "password": "123", "rol": "comprador"}).json()
    assert r["status"] == "success"
    assert r["user"]["token"]


def test_login_con_rol_equivocado_falla(cliente):
    r = cliente.post("/api/login", json={"email": "comprador@agrocolab.cl", "password": "123", "rol": "agricultor"}).json()
    assert r["status"] == "error"


def test_login_con_contrasena_incorrecta_falla(cliente):
    r = cliente.post("/api/login", json={"email": "comprador@agrocolab.cl", "password": "mala", "rol": "comprador"}).json()
    assert r["status"] == "error"
    assert "token" not in r.get("user", {})


def test_rutas_protegidas_exigen_token(cliente):
    assert cliente.get("/api/pagos").status_code == 401
    assert cliente.get("/api/pedidos").status_code == 401


def test_token_alterado_se_rechaza(cliente, token_comprador):
    usuario_id, expira, firma = token_comprador.split(".")
    falso = f"{int(usuario_id) + 1}.{expira}.{firma}"
    assert cliente.get("/api/pagos", headers=auth(falso)).status_code == 401


def test_registro_y_verificacion(cliente, nuevo_comprador):
    email, password, token = nuevo_comprador
    assert cliente.get("/api/pagos", headers=auth(token)).json()["status"] == "success"


def test_cuenta_sin_verificar_no_recibe_token(cliente):
    r = cliente.post("/api/register", json={
        "nombre": "Sin Verificar", "email": "sinverificar@ejemplo.cl", "password": "clave-segura-1", "rol": "comprador",
    }).json()
    assert r["status"] == "success"
    login_r = cliente.post("/api/login", json={"email": "sinverificar@ejemplo.cl", "password": "clave-segura-1", "rol": "comprador"}).json()
    assert "token" not in login_r["user"]


def test_registro_no_revela_correos_existentes(cliente):
    """Registrar un correo ya usado responde igual que uno nuevo."""
    r = cliente.post("/api/register", json={
        "nombre": "Otra Persona", "email": "comprador@agrocolab.cl", "password": "clave-segura-1", "rol": "comprador",
    }).json()
    assert r["status"] == "success"
    assert "codigo_verificacion" not in r["user"]


def test_contrasena_corta_se_rechaza(cliente):
    r = cliente.post("/api/register", json={
        "nombre": "Clave Corta", "email": "corta@ejemplo.cl", "password": "123", "rol": "comprador",
    })
    assert r.json()["status"] == "error"


# ----------------- Recuperación de contraseña -----------------

def pedir_codigo(cliente, email):
    return cliente.post("/api/recuperar-contrasena", json={"email": email}).json()


def restablecer(cliente, email, codigo, password):
    return cliente.post("/api/restablecer-contrasena", json={"email": email, "codigo": codigo, "password": password}).json()


def test_recuperacion_misma_respuesta_exista_o_no(cliente):
    inexistente = pedir_codigo(cliente, "nadie@ejemplo.cl")
    demo = pedir_codigo(cliente, "comprador@agrocolab.cl")
    assert inexistente["status"] == demo["status"] == "success"
    assert inexistente["mensaje"] == demo["mensaje"]
    assert "codigo_desarrollo" not in demo  # las cuentas demo no se recuperan


def test_recuperacion_completa_cierra_sesiones(cliente, nuevo_comprador):
    email, password, token_viejo = nuevo_comprador
    codigo = pedir_codigo(cliente, email)["codigo_desarrollo"]

    assert restablecer(cliente, email, codigo, "nueva-clave-2")["status"] == "success"
    # El código no se puede reutilizar
    assert restablecer(cliente, email, codigo, "otra-clave-3")["status"] == "error"
    # La sesión anterior quedó cerrada y solo sirve la contraseña nueva
    assert cliente.get("/api/pagos", headers=auth(token_viejo)).status_code == 401
    assert cliente.post("/api/login", json={"email": email, "password": password, "rol": "comprador"}).json()["status"] == "error"
    assert login(cliente, email, "nueva-clave-2")


def test_codigo_se_anula_tras_cinco_errores(cliente, nuevo_comprador):
    email, _, _ = nuevo_comprador
    codigo = pedir_codigo(cliente, email)["codigo_desarrollo"]
    for i in range(1, 6):
        malo = f"{(int(codigo) + i) % 1_000_000:06d}"
        assert restablecer(cliente, email, malo, "nueva-clave-2")["status"] == "error"
    assert restablecer(cliente, email, codigo, "nueva-clave-2")["status"] == "error"


def test_codigo_de_recuperacion_se_guarda_como_hash(cliente, nuevo_comprador):
    from database import SessionLocal, Usuario
    email, _, _ = nuevo_comprador
    codigo = pedir_codigo(cliente, email)["codigo_desarrollo"]
    db = SessionLocal()
    try:
        guardado = db.query(Usuario).filter(Usuario.email == email).first().recuperacion_hash
    finally:
        db.close()
    assert guardado and codigo not in guardado


def test_verificar_la_cuenta_inicia_sesion(cliente):
    """Tras verificar con el código se entra directo, sin volver a escribir
    el correo y la contraseña."""
    email = "entra-directo@ejemplo.cl"
    r = cliente.post("/api/register", json={
        "nombre": "Persona Nueva", "email": email, "password": "clave-segura-1", "rol": "agricultor",
    }).json()
    v = cliente.post("/api/verificar-cuenta", json={"email": email, "codigo": r["user"]["codigo_verificacion"]}).json()
    assert v["status"] == "success", v
    assert v["user"]["rol"] == "agricultor" and v["user"]["email"] == email
    # El token sirve para usar la API de inmediato
    assert cliente.get("/api/pedidos", headers=auth(v["user"]["token"])).status_code == 200


def test_codigo_incorrecto_no_entrega_sesion(cliente):
    email = "codigo-malo@ejemplo.cl"
    r = cliente.post("/api/register", json={
        "nombre": "Persona Nueva", "email": email, "password": "clave-segura-1", "rol": "comprador",
    }).json()
    codigo_malo = "000000" if r["user"]["codigo_verificacion"] != "000000" else "111111"
    v = cliente.post("/api/verificar-cuenta", json={"email": email, "codigo": codigo_malo}).json()
    assert v["status"] == "error" and "user" not in v
