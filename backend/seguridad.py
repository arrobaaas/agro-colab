"""Registro de eventos de seguridad, reglas de alerta y envío de alertas.

Cada evento se guarda en la tabla eventos_seguridad (30 días) y además se
escribe como una línea JSON en los logs del servidor, con el correo y la IP
enmascarados. Cuando un evento cumple una regla (por ejemplo, 5 logins fallidos
contra una cuenta en 15 minutos) se envía una alerta por correo y/o webhook,
como máximo una vez por hora para la misma regla y el mismo origen, y con un
tope global por hora.

Variables de entorno de las alertas (ambas opcionales):
  ALERTA_CORREO        correo que recibe las alertas (usa Brevo, ver notificaciones.py)
  ALERTA_WEBHOOK_URL   webhook de Discord o Slack (https://; http solo hacia localhost)
"""

import html
import http.client
import ipaddress
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from contextvars import ContextVar
from datetime import datetime, timedelta

from notificaciones import enviar_correo
from repositories import eventos

registro = logging.getLogger("agrocolab.seguridad")
if not registro.handlers:
    _salida = logging.StreamHandler()
    _salida.setFormatter(logging.Formatter("%(message)s"))
    registro.addHandler(_salida)
    registro.setLevel(logging.INFO)
    registro.propagate = False

# IP y ruta de la petición en curso; las fija el middleware de main.py para
# no tener que pasarlas a mano a cada registrar_evento
peticion_actual: ContextVar[dict] = ContextVar("peticion_actual", default={})

RETENCION = timedelta(days=30)
SILENCIO_ENTRE_ALERTAS = timedelta(hours=1)
# Tope global: con correos o IPs distintos, el silencio por origen no frena el
# envío, y una avalancha de alertas agotaría la cuota de correo del servicio
MAX_ALERTAS_POR_HORA = 20
# Un mismo tipo de evento desde una misma IP: lo que supere esto no se guarda
MAX_EVENTOS_POR_MINUTO = 30

# tipo de evento -> reglas (cuántos, en qué ventana, agrupados por, descripción)
REGLAS = {
    "login_fallido": [
        (5, timedelta(minutes=15), "email", "Posible fuerza bruta contra una cuenta"),
        (6, timedelta(minutes=15), "ip", "Muchos logins fallidos desde una IP (posible prueba de contraseñas)"),
    ],
    "token_invalido": [(5, timedelta(minutes=10), "ip", "Tokens de sesión falsificados o manipulados")],
    "acceso_denegado": [(5, timedelta(minutes=10), "ip", "Intentos repetidos de acceder a datos de otros usuarios")],
    "cuenta_demo": [(3, timedelta(minutes=30), "ip", "Intentos repetidos de modificar las cuentas de demostración")],
    "limite_excedido": [(1, timedelta(minutes=10), "ip", "Un cliente superó el límite de intentos")],
    "entrada_html": [(1, timedelta(minutes=10), "ip", "Intento de inyectar HTML o JavaScript (posible XSS)")],
    "csp_violacion": [(3, timedelta(minutes=10), "ip", "El navegador de un visitante bloqueó código no autorizado (CSP)")],
    "recuperacion_fallida": [(8, timedelta(minutes=15), "ip", "Muchos códigos de recuperación de contraseña incorrectos")],
    "verificacion_fallida": [(4, timedelta(hours=1), "email", "Muchos códigos de verificación incorrectos contra una cuenta")],
    "pago_rechazado": [(5, timedelta(minutes=15), "ip", "Muchos pagos rechazados seguidos (posible prueba de tarjetas)")],
}

_muestreo = {}
_muestreo_candado = threading.Lock()


def _dentro_del_muestreo(tipo, ip) -> bool:
    """Evita que un solo cliente escriba una fila y una línea de log por petición."""
    minuto = int(time.time() // 60)
    with _muestreo_candado:
        if len(_muestreo) > 10_000:
            _muestreo.clear()
        clave = (tipo, ip, minuto)
        _muestreo[clave] = _muestreo.get(clave, 0) + 1
        return _muestreo[clave] <= MAX_EVENTOS_POR_MINUTO


def enmascarar_correo(correo):
    """Los logs y las alertas salen del sistema: no llevan el correo completo."""
    if not correo or "@" not in correo:
        return "***" if correo else None
    usuario, dominio = correo.rsplit("@", 1)
    return f"{usuario[:2]}***@{dominio}"


def enmascarar_ip(ip):
    try:
        direccion = ipaddress.ip_address(ip or "")
    except ValueError:
        return "***" if ip else None
    if direccion.version == 4:
        return ".".join(str(direccion).split(".")[:3]) + ".x"
    return ":".join(direccion.exploded.split(":")[:3]) + "::"


def registrar_evento(tipo, severidad="info", ip=None, usuario=None, email=None, ruta=None, detalle=""):
    """Guarda un evento de seguridad y dispara una alerta si corresponde.

    Nunca lanza excepciones: un fallo del registro no debe romper la petición.
    """
    contexto = peticion_actual.get()
    ip = ip or contexto.get("ip")
    ruta = ruta or contexto.get("ruta")
    if not _dentro_del_muestreo(tipo, ip):
        return
    email = email or (usuario.email if usuario is not None else None)
    datos = {
        "momento": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "evento": tipo,
        "severidad": severidad,
        "ip": enmascarar_ip(ip),
        "usuario_id": usuario.id if usuario is not None else None,
        "email": enmascarar_correo(email),
        "ruta": ruta,
        "detalle": (detalle or "")[:300],
    }
    registro.info(json.dumps({"seguridad": datos}, ensure_ascii=False))

    try:
        eventos.guardar(
            limite_antiguedad=datetime.utcnow() - RETENCION,
            tipo=tipo, severidad=severidad, ip=ip, usuario_id=datos["usuario_id"],
            email=email, ruta=ruta, detalle=datos["detalle"],
        )

        alerta = _alerta_pendiente(tipo, severidad, ip, email)
        if alerta:
            clave, descripcion, cantidad = alerta
            eventos.guardar(tipo="alerta_enviada", severidad="advertencia", ip=ip, email=email, ruta=ruta, detalle=clave)
            threading.Thread(
                target=_enviar_alerta, args=(descripcion, cantidad, datos), daemon=True
            ).start()
    except Exception as error:  # noqa: BLE001 - el registro nunca debe romper la petición
        registro.error("No se pudo registrar el evento de seguridad %s: %s", tipo, error)


def _alerta_pendiente(tipo, severidad, ip, email):
    """Devuelve (clave, descripción, cantidad) si el evento debe generar una
    alerta que no se haya enviado en la última hora; si no, None."""
    reglas = REGLAS.get(tipo)
    if not reglas and severidad != "critica":
        return None

    candidatas = []
    for cantidad_minima, ventana, agrupar_por, descripcion in reglas or []:
        valor = email if agrupar_por == "email" else ip
        cantidad = eventos.contar_recientes(tipo, agrupar_por, valor, datetime.utcnow() - ventana)
        if cantidad >= cantidad_minima:
            candidatas.append((f"{tipo}:{agrupar_por}:{valor}", descripcion, cantidad))
    if not reglas:
        candidatas.append((f"{tipo}:ip:{ip}", f"Evento crítico: {tipo}", 1))

    hace_una_hora = datetime.utcnow() - SILENCIO_ENTRE_ALERTAS
    for clave, descripcion, cantidad in candidatas:
        if not eventos.alerta_enviada_desde(clave, hace_una_hora):
            if eventos.contar_alertas_desde(hace_una_hora) >= MAX_ALERTAS_POR_HORA:
                return None
            return clave, descripcion, cantidad
    return None


def _neutralizar(texto: str) -> str:
    """El detalle y el correo los escribe el atacante: no deben poder mencionar a
    todo el canal (@everyone, <!channel>) ni formatear enlaces en Discord o Slack."""
    return texto.replace("@", "@​").replace("<", "‹").replace(">", "›").replace("[", "(").replace("]", ")")


def _enviar_alerta(descripcion, cantidad, datos):
    """Se ejecuta en un hilo aparte. El IP y el correo ya vienen enmascarados: el
    detalle completo se consulta en el panel de monitoreo."""
    texto = (
        f"🚨 Alerta de seguridad Agro-Colab: {descripcion}\n"
        f"Evento: {datos['evento']} ({datos['severidad']}) · {cantidad} en la ventana de la regla\n"
        f"IP: {datos['ip'] or '-'} · Cuenta: {datos['email'] or '-'}\n"
        f"Ruta: {datos['ruta'] or '-'} · Detalle: {datos['detalle'] or '-'}\n"
        f"Hora (UTC): {datos['momento']}"
    )

    correo = os.getenv("ALERTA_CORREO")
    if correo:
        try:
            enviar_correo(
                correo, f"[Agro-Colab] Alerta de seguridad: {descripcion}",
                "<pre style='font-family:monospace'>" + html.escape(texto) + "</pre>",
                nombre="Administración",
            )
        except Exception as error:  # noqa: BLE001 - un fallo del correo no debe impedir el webhook
            registro.error("No se pudo enviar la alerta por correo: %s", type(error).__name__)

    webhook = os.getenv("ALERTA_WEBHOOK_URL", "")
    # Solo https (o http hacia la propia máquina, para pruebas locales)
    if webhook.startswith(("https://", "http://127.0.0.1", "http://localhost")):
        seguro = _neutralizar(texto)
        # "content" lo lee Discord y "text" lo lee Slack
        cuerpo = json.dumps({"content": seguro, "text": seguro, "allowed_mentions": {"parse": []}}).encode("utf-8")
        peticion = urllib.request.Request(
            webhook, data=cuerpo, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            urllib.request.urlopen(peticion, timeout=10).close()  # nosec B310: esquema comprobado arriba y URL de una variable de entorno
        except (urllib.error.URLError, http.client.HTTPException, OSError) as error:
            registro.error("No se pudo enviar la alerta al webhook: %s", type(error).__name__)

    if not correo and not webhook:
        registro.warning("Alerta sin destino (configura ALERTA_CORREO o ALERTA_WEBHOOK_URL): %s", descripcion)


def resumen(horas: int = 24, limite: int = 50) -> dict:
    """Datos para el panel de monitoreo."""
    fecha = datetime.utcnow() - timedelta(hours=horas)
    por_tipo = {}
    por_severidad = {"info": 0, "advertencia": 0, "critica": 0}
    for evento in eventos.desde(fecha):
        por_tipo[evento.tipo] = por_tipo.get(evento.tipo, 0) + 1
        # Las alertas son consecuencia de otros eventos: no se cuentan dos veces
        if evento.tipo != "alerta_enviada" and evento.severidad in por_severidad:
            por_severidad[evento.severidad] += 1
    return {
        "status": "success",
        "horas": horas,
        "por_tipo": por_tipo,
        "por_severidad": por_severidad,
        "alertas": por_tipo.get("alerta_enviada", 0),
        "alertas_configuradas": bool(os.getenv("ALERTA_CORREO") or os.getenv("ALERTA_WEBHOOK_URL")),
        "eventos": [
            {
                "momento": e.momento.isoformat(timespec="seconds") + "Z" if e.momento else None,
                "tipo": e.tipo,
                "severidad": e.severidad,
                "ip": e.ip,
                "email": e.email,
                "ruta": e.ruta,
                "detalle": e.detalle,
            }
            for e in eventos.ultimos(limite)
        ],
    }
