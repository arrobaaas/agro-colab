"""Envío de correos con la API HTTP de Brevo.

Se usa HTTP y no SMTP porque algunos hostings bloquean los puertos SMTP.
Variables de entorno:
  BREVO_API_KEY      clave de la API
  CORREO_REMITENTE   correo verificado en Brevo desde el que se envía
"""

import json
import logging
import os
import urllib.error
import urllib.request

registro = logging.getLogger("agrocolab")


def variable(nombre: str) -> str:
    """Valor de una variable de entorno sin espacios: al copiar y pegar la
    clave en Render es fácil arrastrar un espacio o un salto de línea."""
    return os.getenv(nombre, "").strip()


def correo_configurado() -> bool:
    return bool(variable("BREVO_API_KEY") and variable("CORREO_REMITENTE"))


def enviar_correo(destino: str, nombre: str, asunto: str, contenido_html: str) -> bool:
    """Envía un correo. Devuelve True si el proveedor lo aceptó."""
    if not correo_configurado():
        return False

    cuerpo = {
        "sender": {"name": "Agro-Colab", "email": variable("CORREO_REMITENTE")},
        "to": [{"email": destino, "name": nombre}],
        "subject": asunto,
        "htmlContent": contenido_html,
    }
    peticion = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={
            "api-key": variable("BREVO_API_KEY"),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=10) as respuesta:
            return 200 <= respuesta.status < 300
    except urllib.error.HTTPError as error:
        # Brevo explica el motivo del rechazo en el cuerpo de la respuesta
        detalle = error.read().decode("utf-8", errors="replace")[:500]
        registro.error("Brevo rechazó el correo '%s' (%s): %s", asunto, error.code, detalle)
        return False
    except (urllib.error.URLError, TimeoutError) as error:
        registro.error("No se pudo enviar el correo '%s': %s", asunto, error)
        return False
