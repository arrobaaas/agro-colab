"""Infraestructura transversal de la API: sesión de base de datos, tokens,
autenticación y límite de intentos. No contiene reglas de negocio."""

import hashlib
import hmac
import logging
import os
import secrets
import time

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from database import CUENTAS_DEMO, SessionLocal, Usuario
from errores import DemasiadosIntentos, NoAutenticado, Prohibido
from repositories import intentos, usuarios as repo_usuarios
from seguridad import registrar_evento

# En desarrollo local se permiten respuestas que ayudan a simular la verificación
# de cuenta (el código se imprime y se devuelve para poder probar el flujo).
# En producción jamás se debe exponer el código de verificación.
MODO_DESARROLLO = os.getenv("AGROCOLAB_MOD_MODE", "produccion").lower() == "desarrollo"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----------------- LÍMITE DE INTENTOS -----------------

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


def limitar(clave: str, maximo: int, ventana_segundos: int):
    """Corta la petición si la clave superó el máximo de intentos."""
    if not intentos.registrar_si_permitido(clave, maximo, ventana_segundos):
        registrar_evento("limite_excedido", "advertencia", detalle=clave)
        raise DemasiadosIntentos("Demasiados intentos. Intenta más tarde.")


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

# Una clave de ejemplo (la de .env.example es pública en el repositorio) o
# demasiado corta permitiría a cualquiera falsificar tokens de sesión: se
# descarta y se usa una aleatoria.
CLAVES_DE_EJEMPLO = {"cambia-esta-clave-por-una-generada"}


def _secreto_tokens() -> str:
    clave = os.getenv("AGROCOLAB_SECRET", "").strip()
    if clave and clave not in CLAVES_DE_EJEMPLO and len(clave) >= 32:
        return clave
    if clave:
        logging.getLogger("agrocolab").warning(
            "AGROCOLAB_SECRET es la clave de ejemplo o tiene menos de 32 caracteres: "
            "se ignora y se usa una aleatoria (las sesiones se cierran al reiniciar)."
        )
    return secrets.token_hex(32)


SECRETO_TOKENS = _secreto_tokens()
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


def usuario_actual(request: Request, db: Session = Depends(get_db)) -> Usuario:
    """Dependencia de FastAPI: usuario autenticado según el header Authorization."""
    cabecera = request.headers.get("Authorization", "")
    partes = _partes_token(cabecera[7:]) if cabecera.startswith("Bearer ") else None
    usuario = None
    if partes and partes[1] >= time.time():
        usuario_id, expira, firma = partes
        candidato = repo_usuarios.por_id(db, usuario_id)
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
        raise NoAutenticado("Tu sesión expiró. Inicia sesión nuevamente.")
    return usuario


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
