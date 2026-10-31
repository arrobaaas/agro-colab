"""Logica de dominio y utilidades compartidas del backend Agro-Colab.

Centraliza la configuración de base de datos, los datos iniciales, los
modelos Pydantic de entrada y las funciones de negocio/serialización que
eran compartidas dentro de la aplicacion FastAPI.
"""

from typing import Annotated, Literal, Optional
from datetime import datetime

import html
import os
import time
import hmac
import hashlib
import secrets

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import AfterValidator, BaseModel, Field, StringConstraints
from sqlalchemy.orm import Session

from database import (
    engine, SessionLocal, Base, Usuario, Arbol, Suscripcion, Pedido, IntentoAcceso,
    hash_password, verify_password, asegurar_columnas, migrar_cuentas_antiguas,
    CUENTAS_DEMO,
)
from notificaciones import correo_configurado, enviar_correo
from seguridad import registrar_evento
from catalogo import (
    CATALOGO_ESPECIES, listar_especies, buscar_especie, fotos_permitidas,
    componer_nombre, normalizar_identificador, foto_de,
)


# ----------------- SEGURIDAD -----------------

# En desarrollo local se permiten respuestas que ayudan a simular la verificación
# de cuenta (el código se imprime y se devuelve para poder probar el flujo).
# En producción jamás se debe exponer el código de verificación.
MODO_DESARROLLO = os.getenv("AGROCOLAB_MOD_MODE", "produccion").lower() == "desarrollo"

def _limitar_intento(clave: str, maximo: int, ventana_segundos: int) -> bool:
    """Registra un intento y decide si se permite. La clave puede ser una IP o
    una cuenta. Los intentos viven en la tabla intentos_acceso."""
    ahora = time.time()
    db = SessionLocal()
    try:
        # Limpieza: nada de lo que se limita usa ventanas de más de un día
        db.query(IntentoAcceso).filter(IntentoAcceso.momento < ahora - 86400).delete(synchronize_session=False)
        recientes = db.query(IntentoAcceso).filter(
            IntentoAcceso.clave == clave,
            IntentoAcceso.momento >= ahora - ventana_segundos,
        ).count()
        if recientes >= maximo:
            db.commit()
            return False
        db.add(IntentoAcceso(clave=clave, momento=ahora))
        db.commit()
        return True
    finally:
        db.close()


def ip_cliente(request: Request) -> str:
    """IP real del cliente.

    En Render la petición llega a través de un proxy: request.client.host es
    la IP del proxy y todos los usuarios compartían el mismo contador (bastaba
    un atacante para bloquear el login de todos). El proxy agrega la IP real
    al final de X-Forwarded-For; los valores anteriores los puede inventar el
    cliente, por eso se toma el último.
    """
    reenviada = request.headers.get("X-Forwarded-For", "")
    if reenviada:
        return reenviada.split(",")[-1].strip()
    return request.client.host if request.client else "0.0.0.0"


def demasiados_intentos():
    return HTTPException(status_code=429, detail={"status": "error", "mensaje": "Demasiados intentos. Intenta más tarde."})


def limitar(clave: str, maximo: int, ventana_segundos: int):
    """Corta la petición si la clave superó el máximo de intentos."""
    if not _limitar_intento(clave, maximo, ventana_segundos):
        registrar_evento("limite_excedido", "advertencia", detalle=clave)
        raise demasiados_intentos()


def limitar_por_ip(maximo: int = 10, ventana_segundos: int = 300):
    """Dependencia de FastAPI que aplica rate limiting por IP a una ruta."""
    def _limiter(request: Request):
        limitar(f"ip:{ip_cliente(request)}:{request.url.path}", maximo, ventana_segundos)
    return _limiter


# ----------------- CORREO -----------------

def plantilla_correo(nombre: str, titulo: str, intro: str, codigo: str = "", pie: str = "") -> str:
    """HTML de los correos con la marca de Agro-Colab.

    Tablas y estilos en línea: los clientes de correo (Gmail, Outlook)
    ignoran las hojas de estilo. Todo texto variable pasa por html.escape.
    """
    bloque_codigo = (
        "<tr><td style='padding:8px 40px 8px'>"
        "<div style='background:#f6f4ee;border-radius:16px;padding:22px;text-align:center;"
        "font-family:Menlo,Consolas,monospace;font-size:34px;letter-spacing:10px;color:#0c1410'>"
        f"{html.escape(codigo)}</div></td></tr>"
        if codigo else ""
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'></head>"
        "<body style='margin:0;background:#f6f4ee;font-family:Inter,Arial,sans-serif'>"
        "<table role='presentation' width='100%' cellpadding='0' cellspacing='0' style='padding:32px 12px'><tr><td align='center'>"
        "<table role='presentation' width='100%' cellpadding='0' cellspacing='0' style='max-width:520px;background:#ffffff;border-radius:24px;overflow:hidden'>"
        "<tr><td style='background:#040806;padding:26px 40px;color:#ffffff;font-size:18px;font-weight:600'>"
        "<span style='color:#34d399'>&#9650;</span>&nbsp; Agro-Colab</td></tr>"
        f"<tr><td style='padding:36px 40px 8px;color:#0c1410;font-size:24px;line-height:1.25'>{html.escape(titulo)}</td></tr>"
        f"<tr><td style='padding:8px 40px 16px;color:#3d4842;font-size:15px;line-height:1.6'>Hola {html.escape(nombre)},<br>{html.escape(intro)}</td></tr>"
        f"{bloque_codigo}"
        f"<tr><td style='padding:16px 40px 36px;color:#67716b;font-size:13px;line-height:1.6'>{html.escape(pie)}</td></tr>"
        "<tr><td style='border-top:1px solid #edeae2;padding:18px 40px;color:#8b938f;font-size:12px'>"
        "Agro-Colab · Proyecto académico INGT1003, Universidad Mayor. Este correo se envió automáticamente; no lo respondas.</td></tr>"
        "</table></td></tr></table></body></html>"
    )


def enviar_codigo_verificacion(destino: str, nombre: str, codigo: str) -> bool:
    """Envía el código de verificación de cuenta por correo."""
    return enviar_correo(
        destino,
        nombre,
        f"Tu código de verificación de Agro-Colab: {codigo}",
        plantilla_correo(
            nombre,
            "Verifica tu cuenta",
            "Para terminar de crear tu cuenta en Agro-Colab, ingresa este código:",
            codigo,
            "El código vence en 30 minutos. Si no creaste una cuenta, ignora este correo.",
        ),
    )


def enviar_codigo_recuperacion(destino: str, nombre: str, codigo: str) -> bool:
    """Envía el código para restablecer la contraseña."""
    return enviar_correo(
        destino,
        nombre,
        f"Restablece tu contraseña de Agro-Colab: {codigo}",
        plantilla_correo(
            nombre,
            "Restablece tu contraseña",
            "Recibimos una solicitud para cambiar la contraseña de tu cuenta. Usa este código:",
            codigo,
            "El código vence en 15 minutos. Si no fuiste tú, ignora este correo: tu contraseña no cambiará.",
        ),
    )


def enviar_aviso_cambio_contrasena(destino: str, nombre: str) -> bool:
    """Avisa que la contraseña cambió, por si no fue el dueño de la cuenta."""
    return enviar_correo(
        destino,
        nombre,
        "Tu contraseña de Agro-Colab cambió",
        plantilla_correo(
            nombre,
            "Tu contraseña cambió",
            "La contraseña de tu cuenta se restableció correctamente y se cerraron las sesiones abiertas.",
            "",
            "Si no fuiste tú, restablécela de inmediato desde «¿Olvidaste tu contraseña?» y escríbenos.",
        ),
    )


# ----------------- TOKENS DE SESIÓN -----------------
# Token firmado con HMAC: "<usuario_id>.<expiracion>.<firma>". Sin él, cualquiera
# podía actuar en nombre de otro usuario con solo enviar su id en la petición.
# En producción AGROCOLAB_SECRET debe estar definido; si no, se genera uno al
# arrancar y las sesiones se invalidan en cada reinicio del servidor.

SECRETO_TOKENS = os.getenv("AGROCOLAB_SECRET") or secrets.token_hex(32)
DURACION_TOKEN_SEGUNDOS = 7 * 24 * 3600

def _firmar(carga: str) -> str:
    return hmac.new(SECRETO_TOKENS.encode(), carga.encode(), hashlib.sha256).hexdigest()

def crear_token(usuario) -> str:
    """Token firmado que incluye el hash de la contraseña del usuario: al
    cambiarla, todos los tokens anteriores dejan de servir."""
    expira = int(time.time()) + DURACION_TOKEN_SEGUNDOS
    carga = f"{usuario.id}.{expira}"
    return f"{carga}.{_firmar(f'{carga}.{usuario.password}')}"


def _partes_token(token: str):
    """Devuelve (usuario_id, expira, firma) o None si el formato no sirve."""
    try:
        usuario_id, expira, firma = token.split(".")
        return int(usuario_id), int(expira), firma
    except (ValueError, AttributeError):
        return None


def _no_autorizado(mensaje: str, codigo: int = 401):
    return HTTPException(status_code=codigo, detail={"status": "error", "mensaje": mensaje})


# ----------------- SESIÓN / BASE DE DATOS -----------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def usuario_actual(request: Request, db: Session = Depends(get_db)) -> Usuario:
    """Dependencia de FastAPI: usuario autenticado según el header Authorization."""
    cabecera = request.headers.get("Authorization", "")
    partes = _partes_token(cabecera[7:]) if cabecera.startswith("Bearer ") else None
    usuario = None
    if partes and partes[1] >= time.time():
        usuario_id, expira, firma = partes
        candidato = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        esperada = _firmar(f"{usuario_id}.{expira}.{candidato.password}") if candidato else ""
        if candidato and hmac.compare_digest(firma, esperada):
            usuario = candidato
        else:
            # Un token vencido es normal; uno con firma que no cuadra fue
            # falsificado, manipulado o pertenece a una contraseña anterior
            registrar_evento("token_invalido", "advertencia", detalle=f"usuario_id={usuario_id}")
    elif cabecera.startswith("Bearer ") and not partes:
        registrar_evento("token_invalido", "advertencia", detalle="formato inválido")
    if not usuario:
        raise _no_autorizado("Tu sesión expiró. Inicia sesión nuevamente.")
    return usuario


def es_cuenta_demo(usuario: Usuario) -> bool:
    """Las credenciales demo están publicadas en el README: cualquiera puede
    usarlas, así que no se permite que las dañen para los demás."""
    return usuario.email in CUENTAS_DEMO


# ----------------- ADMINISTRADOR -----------------

ROL_ADMIN = "administrador"


def es_admin(usuario: Usuario) -> bool:
    return usuario.rol == ROL_ADMIN


def usuario_admin(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    """Dependencia de FastAPI: corta la petición si la sesión no es de un
    administrador."""
    if not es_admin(usuario):
        registrar_evento("acceso_denegado", "advertencia", usuario=usuario, detalle="panel de administración")
        raise _no_autorizado("Solo un administrador puede hacer esto.", 403)
    return usuario


def crear_administrador(db: Session):
    """Crea la cuenta de administrador desde ADMIN_EMAIL y ADMIN_PASSWORD.

    Nadie puede registrarse como administrador: la cuenta solo existe si se
    configuran esas variables en el servidor, y su contraseña no queda en el
    repositorio. Si el correo ya tiene cuenta, se la asciende a
    administrador. La contraseña solo se usa al crearla: después se cambia
    desde el perfil o con la recuperación de contraseña.
    """
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    if not email:
        return
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario:
        if usuario.rol != ROL_ADMIN and not es_cuenta_demo(usuario):
            usuario.rol = ROL_ADMIN
            usuario.verificado = 1
            db.commit()
            print(f"[admin] {email} ahora es administrador")
        return
    if len(password) < 12:
        print("[admin] ADMIN_PASSWORD falta o tiene menos de 12 caracteres: no se creó el administrador")
        return
    db.add(Usuario(
        nombre=os.getenv("ADMIN_NOMBRE", "").strip() or "Administrador",
        email=email, password=hash_password(password), rol=ROL_ADMIN, verificado=1,
        consentimiento_datos=1, fecha_consentimiento=datetime.now(), acepta_terminos=1,
    ))
    db.commit()
    print(f"[admin] cuenta de administrador creada: {email}")


def exigir_mismo_usuario(usuario: Usuario, usuario_id: int):
    """Corta la petición si el usuario autenticado no es el dueño del recurso."""
    if usuario.id != usuario_id:
        registrar_evento("acceso_denegado", "advertencia", usuario=usuario, detalle=f"datos del usuario {usuario_id}")
        raise _no_autorizado("No tienes permiso para ver estos datos.", 403)


def datos_iniciales():
    db = SessionLocal()
    try:
        # Verificar si ya hay datos
        if db.query(Usuario).count() == 0:
            # Crear usuarios de prueba (contraseña hasheada con bcrypt).
            usuarios = [
                Usuario(
                    nombre="Camila Soto", email="comprador@agrocolab.cl",
                    password=hash_password("123"), rol="comprador", verificado=1,
                    consentimiento_datos=1, fecha_consentimiento=datetime.now(),
                    acepta_terminos=1,
                ),
                Usuario(
                    nombre="Hernán Silva", email="agricultor@agrocolab.cl",
                    password=hash_password("123"), rol="agricultor", verificado=1,
                    consentimiento_datos=1, fecha_consentimiento=datetime.now(),
                    acepta_terminos=1,
                ),
            ]
            db.add_all(usuarios)
            db.commit()

        if db.query(Arbol).count() == 0:
            # Crear árboles de prueba (con fotos del catálogo de especies)
            arboles = [
                Arbol(
                    nombre="Palto Hass #104",
                    especie="palto_hass",
                    identificador="#104",
                    plan="Básico",
                    tipo_suscripcion="Compartido",
                    precio_mensual_clp=12000,
                    cupos_totales=5,
                    cupos_ocupados=0,
                    estimacion_cosecha="45 kg anuales",
                    ubicacion="Valle del Aconcagua, Región de Valparaíso",
                    imagen=foto_de("palto_hass", 0),
                    imagen_origen="galeria",
                    productor_id=2
                ),
                Arbol(
                    nombre="Naranjo Valencia #22",
                    especie="naranjo_valencia",
                    identificador="#22",
                    plan="Premium",
                    tipo_suscripcion="Exclusivo",
                    precio_mensual_clp=35000,
                    cupos_totales=1,
                    cupos_ocupados=0,
                    estimacion_cosecha="80 kg anuales",
                    ubicacion="Curicó, Región del Maule",
                    imagen=foto_de("naranjo_valencia", 0),
                    imagen_origen="galeria",
                    productor_id=2
                ),
                Arbol(
                    nombre="Limonero Eureka #12",
                    especie="limonero_eureka",
                    identificador="#12",
                    plan="Intermedio",
                    tipo_suscripcion="Compartido",
                    precio_mensual_clp=8000,
                    cupos_totales=3,
                    cupos_ocupados=0,
                    estimacion_cosecha="35 kg anuales",
                    ubicacion="Mallarauco, Región Metropolitana",
                    imagen=foto_de("limonero_eureka", 0),
                    imagen_origen="galeria",
                    productor_id=2
                ),
            ]
            db.add_all(arboles)
            db.commit()

        crear_administrador(db)
    finally:
        db.close()


# datos_iniciales() no se llama aquí: al importar core.py las tablas todavía
# no existen. main.py la ejecuta después de create_all().

# ----------------- MODELOS DE DATOS (ESQUEMAS) -----------------

def _sin_html(valor):
    """Defensa en profundidad contra XSS: ningún texto de usuario necesita < o >."""
    if valor is not None and ("<" in valor or ">" in valor):
        raise ValueError("no puede contener los caracteres < o >")
    return valor


def Texto(maximo: int, minimo: int = 1):
    """Texto libre: sin espacios sobrantes, con largo acotado y sin HTML."""
    return Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=minimo, max_length=maximo),
        AfterValidator(_sin_html),
    ]


def normalizar_rut(valor):
    """Valida un RUT chileno con su dígito verificador (módulo 11) y lo
    devuelve con formato 76.123.456-0. Acepta puntos, guion y espacios."""
    if valor is None or valor == "":
        return None
    limpio = valor.replace(".", "").replace("-", "").replace(" ", "").upper()
    cuerpo, dv = limpio[:-1], limpio[-1:]
    if not cuerpo.isdigit() or not 7 <= len(cuerpo) <= 8 or dv not in "0123456789K":
        raise ValueError("el formato debe ser como 76.123.456-0")

    suma, factor = 0, 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    esperado = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    if dv != esperado:
        raise ValueError("el dígito verificador no corresponde")

    con_puntos = f"{int(cuerpo):,}".replace(",", ".")
    return f"{con_puntos}-{dv}"


Rut = Annotated[str, StringConstraints(strip_whitespace=True, max_length=15), AfterValidator(normalizar_rut)]

Correo = Annotated[str, StringConstraints(
    strip_whitespace=True, max_length=120, pattern=r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$"
)]
Contrasena = Annotated[str, StringConstraints(min_length=8, max_length=128)]
Rol = Literal["comprador", "agricultor"]
TipoDestino = Literal["particular", "comercial"]
Frecuencia = Literal["semanal", "quincenal", "mensual"]


class SuscripcionRequest(BaseModel):
    # El usuario sale del token de sesión; el cuerpo solo indica el árbol
    tree_id: int = Field(gt=0)

class LoginRequest(BaseModel):
    # Sin largo mínimo: las cuentas demo usan una contraseña corta
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]
    password: Annotated[str, StringConstraints(max_length=128)]
    rol: Rol

class PedidoRequest(BaseModel):
    # plan_nombre y monto_clp los fija el servidor (catálogo de planes o
    # precio del árbol); los del cliente se ignoran
    plan_nombre: Texto(120)
    monto_clp: int = 0
    cliente_nombre: Texto(80)
    telefono: Texto(30)
    email: Correo
    cliente_id: Optional[int] = None  # ignorado: el cliente sale de la sesión
    tipo_destino: TipoDestino
    razon_social: Optional[Texto(120, 0)] = None
    rut: Optional[Rut] = None
    direccion: Texto(200)
    comuna: Texto(80)
    frecuencia_entrega: Frecuencia
    tipo: Literal["abastecimiento", "arbol"] = "abastecimiento"
    arbol_id: Optional[int] = None
    # Plan de abastecimiento: pago aprobado de la pasarela (routers/pagos.py)
    pago_id: Optional[int] = None

class LogisticaRequest(BaseModel):
    """Datos de despacho que se pueden modificar en un pedido existente."""
    tipo_destino: TipoDestino
    razon_social: Optional[Texto(120, 0)] = None
    rut: Optional[Rut] = None
    direccion: Texto(200)
    comuna: Texto(80)
    frecuencia_entrega: Frecuencia

class ArbolRequest(BaseModel):
    nombre: Optional[str] = None  # se compone desde especie + identificador
    especie: Texto(40)
    identificador: Optional[Texto(12, 0)] = None
    ubicacion: Texto(150)
    plan: Literal["Básico", "Intermedio", "Premium"]
    tipo_suscripcion: Literal["Compartido", "Exclusivo"]
    cupos_totales: int = Field(ge=1, le=50)
    precio_mensual_clp: int = Field(ge=0, le=10_000_000)
    # Solo el número de kilos: el servidor arma el texto ("45 kg anuales")
    # para que no haya ambigüedad de unidades (kg, gramos, cajas...)
    estimacion_cosecha_kg: int = Field(ge=1, le=100_000)
    imagen: Texto(500)
    productor: Optional[str] = None  # ignorado: el productor sale de la sesión

class PerfilRequest(BaseModel):
    nombre: Texto(80, 2)
    email: Correo
    telefono: Optional[Texto(30, 0)] = None
    direccion: Optional[Texto(200, 0)] = None
    password: Optional[Contrasena] = None
    # Obligatoria para cambiar la contraseña: con solo el token (por ejemplo,
    # robado) no se puede secuestrar la cuenta
    password_actual: Optional[Annotated[str, StringConstraints(max_length=128)]] = None

class RegistroRequest(BaseModel):
    nombre: Texto(80, 2)
    email: Correo
    password: Contrasena
    rol: Rol
    telefono: Optional[Texto(30, 0)] = None
    direccion: Optional[Texto(200, 0)] = None

class AdminUsuarioRequest(BaseModel):
    """Cambios que el administrador hace en la cuenta de otra persona."""
    nombre: Texto(80, 2)
    email: Correo
    telefono: Optional[Texto(30, 0)] = None
    direccion: Optional[Texto(200, 0)] = None
    verificado: bool
    # Opcional: una contraseña nueva, por ejemplo si la persona perdió acceso a su correo
    password: Optional[Contrasena] = None

class ReenvioRequest(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]

class VerificacionRequest(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]
    codigo: Annotated[str, StringConstraints(pattern=r"^\d{6}$")]

class RecuperacionRequest(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]

class RestablecerRequest(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]
    codigo: Annotated[str, StringConstraints(pattern=r"^\d{6}$")]
    password: Contrasena


# ----------------- VALIDACIÓN DE ESPECIES E IMAGEN -----------------

def texto_cosecha(kilos: int) -> str:
    """Texto que se guarda y se muestra para la cosecha estimada."""
    return f"{kilos:,}".replace(",", ".") + " kg anuales"


def validar_imagen(imagen: str, especie_id: str):
    """Revisa la imagen enviada por el agricultor.

    El catálogo curado es la única fuente de imágenes: así el comprador nunca ve
    una foto que no corresponda al árbol que está adoptando. La validación se
    hace en el servidor, no solo en el formulario.

    Devuelve (imagen, origen, error).
    """
    if not imagen or not imagen.strip():
        return None, None, "Debes elegir una imagen del árbol."

    valor = imagen.strip()

    if valor.startswith("data:"):
        return None, None, "Por ahora las fotos deben elegirse del catálogo de la especie."

    if valor in fotos_permitidas(especie_id):
        return valor, "galeria", None

    return None, None, "La imagen elegida no corresponde a la especie seleccionada."


def especie_de_arbol(arbol) -> Optional[str]:
    """Especie de un árbol. Los árboles antiguos se deducen del nombre."""
    if arbol.especie:
        return arbol.especie
    nombre = (arbol.nombre or "").lower()
    for especie in CATALOGO_ESPECIES:
        if nombre.startswith(especie["nombre"].lower()):
            return especie["id"]
    return None


def identificador_de_arbol(arbol) -> Optional[str]:
    """Identificador del árbol dentro del huerto (ej: '#104')."""
    if arbol.identificador:
        return arbol.identificador
    especie = buscar_especie(especie_de_arbol(arbol))
    if not especie:
        return None
    nombre = arbol.nombre or ""
    return nombre[len(especie["nombre"]):].strip() or None


def cupos_ocupados_de(arbol, db) -> int:
    """Cupos realmente ocupados: cuenta las suscripciones registradas.

    El contador guardado en la tabla se puede desincronizar (por ejemplo, si la
    base se creó con contadores fijos y sin suscripciones reales), y ahí el
    panel del agricultor anuncia suscriptores que no existen. La fuente de
    verdad son siempre las filas de la tabla suscripciones.
    """
    return db.query(Suscripcion).filter(Suscripcion.arbol_id == arbol.id).count()


def serializar_arbol(arbol, db) -> dict:
    """Representación uniforme de un árbol para la API."""
    especie_id = especie_de_arbol(arbol)
    especie = buscar_especie(especie_id)
    return {
        "id": arbol.id,
        "nombre": arbol.nombre,
        "especie": especie_id,
        "especie_nombre": especie["nombre"] if especie else None,
        "identificador": identificador_de_arbol(arbol),
        "plan": arbol.plan,
        "tipo_suscripcion": arbol.tipo_suscripcion,
        "precio_mensual_clp": arbol.precio_mensual_clp,
        "cupos_totales": arbol.cupos_totales,
        "cupos_ocupados": cupos_ocupados_de(arbol, db),
        "estimacion_cosecha": arbol.estimacion_cosecha,
        "ubicacion": arbol.ubicacion,
        "imagen": arbol.imagen,
        "imagen_origen": arbol.imagen_origen or "galeria",
        "productor": arbol.productor.nombre if arbol.productor else None,
        "productor_id": arbol.productor_id,
    }
