"""Infraestructura transversal de la API: sesión de base de datos, tokens,
autenticación y límite de intentos. No contiene reglas de negocio."""

import hashlib
import hmac
import ipaddress
import logging
import os
import secrets
import time

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from database import CUENTAS_DEMO, SessionLocal, Usuario
from errores import DemasiadosIntentos, NoAutenticado, Prohibido
from repositories import intentos, usuarios as repo_usuarios
from seguridad import peticion_actual, registrar_evento

# En desarrollo local se permiten respuestas que ayudan a simular la verificación
# de cuenta (el código se imprime y se devuelve para poder probar el flujo).
# En producción jamás se debe exponer el código de verificación.
MODO_DESARROLLO = os.getenv("AGROCOLAB_MOD_MODE", "produccion").lower() == "desarrollo"

# Con este modo cualquiera podría restablecer la contraseña de cualquier cuenta:
# el servidor se niega a arrancar si parece estar en producción. Render define
# la variable RENDER en sus servicios.
if MODO_DESARROLLO and (os.getenv("RENDER") or os.getenv("DATABASE_URL")):
    raise RuntimeError("AGROCOLAB_MOD_MODE=desarrollo no se permite con una base de producción ni en Render.")

# Versión de la política de privacidad y los términos que acepta quien se registra
VERSION_POLITICA = "2026-11"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----------------- LÍMITE DE INTENTOS -----------------

CABECERA_IP = os.getenv("CABECERA_IP_CLIENTE", "").strip()


def _ip_valida(valor: str):
    """La IP normalizada, o None si el valor no es una IP (una cabecera la
    puede escribir cualquiera y termina en los registros)."""
    try:
        return str(ipaddress.ip_address(valor.strip()))
    except ValueError:
        return None


def ip_cliente(request: Request) -> str:
    """IP real del cliente.

    CABECERA_IP_CLIENTE indica la cabecera confiable del despliegue (se elige
    tras comprobar qué llega realmente al servidor). Sin ella se usa el último
    valor de X-Forwarded-For: los anteriores los puede inventar el cliente. Se
    leen todas las líneas de la cabecera porque un intermediario puede agregar
    una aparte, y un valor que no sea una IP se descarta.
    """
    if CABECERA_IP:
        ip = _ip_valida(request.headers.get(CABECERA_IP, ""))
        if ip:
            return ip
    reenviada = ",".join(request.headers.getlist("X-Forwarded-For"))
    if reenviada:
        ip = _ip_valida(reenviada.split(",")[-1])
        if ip:
            return ip
    return request.client.host if request.client else "0.0.0.0"  # nosec B104: es un valor de reserva, no una interfaz


def ip_actual() -> str:
    """IP de la petición en curso, para la capa de negocio (no conoce HTTP)."""
    return peticion_actual.get().get("ip") or "desconocida"


def limitar(clave: str, maximo: int, ventana_segundos: int):
    """Corta la petición si la clave superó el máximo de intentos, y cuenta este."""
    if not intentos.registrar_si_permitido(clave, maximo, ventana_segundos):
        registrar_evento("limite_excedido", "advertencia", detalle=clave)
        raise DemasiadosIntentos("Demasiados intentos. Intenta más tarde.")


def exigir_bajo_el_limite(clave: str, maximo: int, ventana_segundos: int):
    """Como limitar, pero sin contar este intento: se usa cuando solo cuentan
    los fallos, que se anotan después con anotar_fallo."""
    if not intentos.permitido(clave, maximo, ventana_segundos):
        registrar_evento("limite_excedido", "advertencia", detalle=clave)
        raise DemasiadosIntentos("Demasiados intentos. Intenta más tarde.")


def anotar_fallo(clave: str):
    intentos.registrar(clave)


def limitar_por_ip(maximo: int = 10, ventana_segundos: int = 300):
    """Dependencia de FastAPI que aplica el límite de intentos por IP a una ruta."""
    def _limiter(request: Request):
        limitar(f"ip:{ip_cliente(request)}:{request.url.path}", maximo, ventana_segundos)
    return _limiter


# ----------------- TOKENS DE SESIÓN -----------------
# Token firmado con HMAC: "<usuario_id>.<expiracion>.<firma>". Sin él, cualquiera
# podía actuar en nombre de otro usuario con solo enviar su id en la petición.
# En producción AGROCOLAB_SECRET debe estar definido; si no, se genera uno al
# arrancar y las sesiones se invalidan en cada reinicio del servidor.

SECRETO_TOKENS = os.getenv("AGROCOLAB_SECRET") or secrets.token_hex(32)
DURACION_TOKEN_SEGUNDOS = 7 * 24 * 3600

if not MODO_DESARROLLO and len(os.getenv("AGROCOLAB_SECRET", "")) < 32:
    logging.getLogger("agrocolab").warning(
        "AGROCOLAB_SECRET falta o es corta (mínimo 32 caracteres): las sesiones pueden no sobrevivir a un reinicio."
    )


def _firmar(carga: str) -> str:
    return hmac.new(SECRETO_TOKENS.encode(), carga.encode(), hashlib.sha256).hexdigest()


def _firma_de(usuario, carga: str) -> str:
    """La firma depende del hash de la contraseña y de la versión de sesión:
    cambiar cualquiera de los dos invalida todos los tokens anteriores."""
    return _firmar(f"{carga}.{usuario.password}.{usuario.sesion_version or 0}")


def crear_token(usuario) -> str:
    expira = int(time.time()) + DURACION_TOKEN_SEGUNDOS
    carga = f"{usuario.id}.{expira}"
    return f"{carga}.{_firma_de(usuario, carga)}"


def _partes_token(token: str):
    """Devuelve (usuario_id, expira, firma) o None si el formato no sirve."""
    try:
        usuario_id, expira, firma = token.split(".")
        return int(usuario_id), int(expira), firma
    except (ValueError, AttributeError):
        return None


def usuario_actual(request: Request, db: Session = Depends(get_db)) -> Usuario:
    """Dependencia de FastAPI: usuario autenticado según el header Authorization."""
    cabecera = request.headers.get("Authorization", "")
    partes = _partes_token(cabecera[7:]) if cabecera.startswith("Bearer ") else None
    usuario = None
    if partes and partes[1] >= time.time():
        usuario_id, expira, firma = partes
        candidato = repo_usuarios.por_id(db, usuario_id)
        esperada = _firma_de(candidato, f"{usuario_id}.{expira}") if candidato else ""
        # En bytes: con str, compare_digest lanza TypeError ante texto no ASCII
        if candidato and hmac.compare_digest(firma.encode(), esperada.encode()):
            # Una cuenta que el administrador dejó sin verificar pierde la sesión
            if candidato.verificado:
                usuario = candidato
        else:
            # Un token vencido es normal; uno con firma que no cuadra fue
            # falsificado, manipulado o pertenece a una contraseña anterior
            registrar_evento("token_invalido", "advertencia", detalle=f"usuario_id={usuario_id}")
    elif cabecera.startswith("Bearer ") and not partes:
        registrar_evento("token_invalido", "advertencia", detalle="formato inválido")
    if not usuario:
        raise NoAutenticado("Tu sesión expiró. Inicia sesión nuevamente.")
    return usuario


def firmar_codigo(proposito: str, usuario_id: int, codigo: str) -> str:
    """Huella de un código de un solo uso. Un SHA-256 sin clave de 6 dígitos se
    invierte probando un millón de valores: con esta clave, leer la base no basta.
    La clave se deriva del secreto para no reutilizarla entre propósitos."""
    clave = hashlib.sha256(b"agrocolab-codigos:" + SECRETO_TOKENS.encode()).digest()
    return hmac.new(clave, f"{proposito}:{usuario_id}:{codigo}".encode(), hashlib.sha256).hexdigest()


# ----------------- PERMISOS -----------------

ROL_ADMIN = "administrador"


def es_cuenta_demo(usuario: Usuario) -> bool:
    """Las credenciales demo están publicadas en el README: cualquiera puede
    usarlas, así que no se permite que las dañen para los demás."""
    return usuario.email in CUENTAS_DEMO


def es_admin(usuario: Usuario) -> bool:
    return usuario.rol == ROL_ADMIN


def usuario_admin(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    """Dependencia de FastAPI: corta la petición si la sesión no es de un administrador."""
    if not es_admin(usuario):
        registrar_evento("acceso_denegado", "advertencia", usuario=usuario, detalle="panel de administración")
        raise Prohibido("Solo un administrador puede hacer esto.")
    return usuario


def exigir_mismo_usuario(usuario: Usuario, usuario_id: int):
    """Corta la petición si el usuario autenticado no es el dueño del recurso."""
    if usuario.id != usuario_id:
        registrar_evento("acceso_denegado", "advertencia", usuario=usuario, detalle=f"datos del usuario {usuario_id}")
        raise Prohibido("No tienes permiso para ver estos datos.")


def exigir_que_no_sea_demo(usuario: Usuario, accion: str):
    """Las cuentas demo son públicas: no pueden actuar sobre lo que ven los demás."""
    if es_cuenta_demo(usuario):
        registrar_evento("cuenta_demo", "advertencia", usuario=usuario, detalle=accion)
        raise Prohibido("La cuenta de demostración no puede hacer esto: sus credenciales son públicas.")
