"""Registro de eventos de seguridad, reglas de alerta y envío de alertas.

Cada evento se guarda en la tabla eventos_seguridad (30 días) y además se
escribe como una línea JSON en los logs del servidor. Cuando un evento cumple
una regla (por ejemplo, 5 logins fallidos contra una cuenta en 15 minutos) se
envía una alerta por correo y/o webhook, como máximo una vez por hora para la
misma regla y el mismo origen.

Variables de entorno de las alertas (ambas opcionales):
  ALERTA_CORREO        correo que recibe las alertas (usa Brevo, ver notificaciones.py)
  ALERTA_WEBHOOK_URL   webhook de Discord o Slack (https://; http solo hacia localhost)
"""

import html
import json
import logging
import os
import threading
import urllib.error
import urllib.request
from contextvars import ContextVar
from datetime import datetime, timedelta

from database import EventoSeguridad, SessionLocal
from notificaciones import enviar_correo

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

# tipo de evento -> (cuántos, en qué ventana, agrupados por, descripción)
REGLAS = {
    "login_fallido": (5, timedelta(minutes=15), "email", "Posible fuerza bruta contra una cuenta"),
    "token_invalido": (5, timedelta(minutes=10), "ip", "Tokens de sesión falsificados o manipulados"),
    "acceso_denegado": (5, timedelta(minutes=10), "ip", "Intentos repetidos de acceder a datos de otros usuarios"),
    "cuenta_demo": (3, timedelta(minutes=30), "ip", "Intentos repetidos de modificar las cuentas de demostración"),
    "limite_excedido": (1, timedelta(minutes=10), "ip", "Un cliente superó el límite de intentos"),
    "entrada_html": (1, timedelta(minutes=10), "ip", "Intento de inyectar HTML o JavaScript (posible XSS)"),
    "csp_violacion": (1, timedelta(minutes=10), "ip", "El navegador de un visitante bloqueó código no autorizado (CSP)"),
    "recuperacion_fallida": (8, timedelta(minutes=15), "ip", "Muchos códigos de recuperación de contraseña incorrectos"),
    "pago_rechazado": (5, timedelta(minutes=15), "ip", "Muchos pagos rechazados seguidos (posible prueba de tarjetas)"),
}


def registrar_evento(tipo, severidad="info", ip=None, usuario=None, email=None, ruta=None, detalle=""):
    """Guarda un evento de seguridad y dispara una alerta si corresponde.

    Nunca lanza excepciones: un fallo del registro no debe romper la petición.
    """
    contexto = peticion_actual.get()
    ip = ip or contexto.get("ip")
    ruta = ruta or contexto.get("ruta")
    email = email or (usuario.email if usuario is not None else None)
    datos = {
        "momento": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "evento": tipo,
        "severidad": severidad,
        "ip": ip,
        "usuario_id": usuario.id if usuario is not None else None,
        "email": email,
        "ruta": ruta,
        "detalle": (detalle or "")[:300],
    }
    registro.info(json.dumps({"seguridad": datos}, ensure_ascii=False))

    db = SessionLocal()
    try:
        db.add(EventoSeguridad(
            tipo=tipo, severidad=severidad, ip=ip, usuario_id=datos["usuario_id"],
            email=email, ruta=ruta, detalle=datos["detalle"],
        ))
        db.query(EventoSeguridad).filter(
            EventoSeguridad.momento < datetime.utcnow() - RETENCION
        ).delete(synchronize_session=False)
        db.commit()

        alerta = _alerta_pendiente(db, tipo, severidad, ip, email)
        if alerta:
            clave, descripcion, cantidad = alerta
            db.add(EventoSeguridad(tipo="alerta_enviada", severidad="advertencia", ip=ip, email=email, ruta=ruta, detalle=clave))
            db.commit()
            threading.Thread(
                target=_enviar_alerta, args=(descripcion, cantidad, datos), daemon=True
            ).start()
    except Exception as error:  # noqa: BLE001 - el registro nunca debe romper la petición
        registro.error("No se pudo registrar el evento de seguridad %s: %s", tipo, error)
        db.rollback()
    finally:
        db.close()


def _alerta_pendiente(db, tipo, severidad, ip, email):
    """Devuelve (clave, descripción, cantidad) si el evento debe generar una
    alerta que no se haya enviado en la última hora; si no, None."""
    regla = REGLAS.get(tipo)
    if regla is None and severidad != "critica":
        return None

    if regla:
        cantidad_minima, ventana, agrupar_por, descripcion = regla
        valor = email if agrupar_por == "email" else ip
        columna = EventoSeguridad.email if agrupar_por == "email" else EventoSeguridad.ip
        cantidad = db.query(EventoSeguridad).filter(
            EventoSeguridad.tipo == tipo,
            columna == valor,
            EventoSeguridad.momento >= datetime.utcnow() - ventana,
        ).count()
        if cantidad < cantidad_minima:
            return None
    else:
        descripcion, valor, cantidad = f"Evento crítico: {tipo}", ip, 1

    clave = f"{tipo}:{valor}"
    ya_enviada = db.query(EventoSeguridad).filter(
        EventoSeguridad.tipo == "alerta_enviada",
        EventoSeguridad.detalle == clave,
        EventoSeguridad.momento >= datetime.utcnow() - SILENCIO_ENTRE_ALERTAS,
    ).first()
    return None if ya_enviada else (clave, descripcion, cantidad)


def _enviar_alerta(descripcion, cantidad, datos):
    texto = (
        f"🚨 Alerta de seguridad Agro-Colab: {descripcion}\n"
        f"Evento: {datos['evento']} ({datos['severidad']}) · {cantidad} en la ventana de la regla\n"
        f"IP: {datos['ip'] or '-'} · Cuenta: {datos['email'] or '-'}\n"
        f"Ruta: {datos['ruta'] or '-'} · Detalle: {datos['detalle'] or '-'}\n"
        f"Hora (UTC): {datos['momento']}"
    )

    correo = os.getenv("ALERTA_CORREO")
    if correo:
        enviar_correo(
            correo, "Administración", f"[Agro-Colab] Alerta de seguridad: {descripcion}",
            "<pre style='font-family:monospace'>" + html.escape(texto) + "</pre>",
        )

    webhook = os.getenv("ALERTA_WEBHOOK_URL", "")
    # Solo https (o http hacia la propia máquina, para pruebas locales)
    if webhook.startswith(("https://", "http://127.0.0.1", "http://localhost")):
        # "content" lo lee Discord y "text" lo lee Slack
        cuerpo = json.dumps({"content": texto, "text": texto}).encode("utf-8")
        peticion = urllib.request.Request(
            webhook, data=cuerpo, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            urllib.request.urlopen(peticion, timeout=10).close()
        except (urllib.error.URLError, TimeoutError) as error:
            registro.error("No se pudo enviar la alerta al webhook: %s", error)

    if not correo and not webhook:
        registro.warning("Alerta sin destino (configura ALERTA_CORREO o ALERTA_WEBHOOK_URL): %s", descripcion)


def resumen(horas: int = 24, limite: int = 50) -> dict:
    """Datos para el panel de monitoreo."""
    db = SessionLocal()
    try:
        desde = datetime.utcnow() - timedelta(hours=horas)
        recientes = db.query(EventoSeguridad).filter(EventoSeguridad.momento >= desde)
        por_tipo = {}
        por_severidad = {"info": 0, "advertencia": 0, "critica": 0}
        for evento in recientes:
            por_tipo[evento.tipo] = por_tipo.get(evento.tipo, 0) + 1
            # Las alertas son consecuencia de otros eventos: no se cuentan dos veces
            if evento.tipo != "alerta_enviada" and evento.severidad in por_severidad:
                por_severidad[evento.severidad] += 1
        ultimos = (
            db.query(EventoSeguridad).order_by(EventoSeguridad.id.desc()).limit(limite).all()
        )
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
                for e in ultimos
            ],
        }
    finally:
        db.close()
