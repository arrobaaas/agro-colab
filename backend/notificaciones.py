"""Envío de correos con la API HTTP de Brevo.

Se usa HTTP y no SMTP porque algunos hostings bloquean los puertos SMTP.
Variables de entorno:
  BREVO_API_KEY      clave de la API
  CORREO_REMITENTE   correo verificado en Brevo desde el que se envía
"""

import html
import http.client
import json
import logging
import os
import threading
import urllib.error
import urllib.request

registro = logging.getLogger("agrocolab")


def variable(nombre: str) -> str:
    """Valor de una variable de entorno sin espacios: al copiar y pegar la
    clave en Render es fácil arrastrar un espacio o un salto de línea."""
    return os.getenv(nombre, "").strip()


def correo_configurado() -> bool:
    return bool(variable("BREVO_API_KEY") and variable("CORREO_REMITENTE"))


def enviar_correo(destino: str, asunto: str, contenido_html: str, nombre: str = "") -> bool:
    """Envía un correo. Devuelve True si el proveedor lo aceptó. El asunto termina
    en los logs si el envío falla: nunca debe llevar un código ni datos personales."""
    if not correo_configurado():
        return False

    cuerpo = {
        "sender": {"name": "Agro-Colab", "email": variable("CORREO_REMITENTE")},
        "to": [{"email": destino, **({"name": nombre} if nombre else {})}],
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
        with urllib.request.urlopen(peticion, timeout=10) as respuesta:  # nosec B310: URL fija y https
            return 200 <= respuesta.status < 300
    except urllib.error.HTTPError as error:
        # Brevo explica el motivo del rechazo en el cuerpo de la respuesta
        detalle = error.read().decode("utf-8", errors="replace")[:500]
        registro.error("Brevo rechazó el correo '%s' (%s): %s", asunto, error.code, detalle)
        return False
    except (urllib.error.URLError, http.client.HTTPException, OSError) as error:
        registro.error("No se pudo enviar el correo '%s': %s", asunto, type(error).__name__)
        return False


def enviar_en_segundo_plano(funcion, *args):
    """Envía sin que la respuesta espere a Brevo: así el tiempo de respuesta no
    revela si una cuenta existe."""
    threading.Thread(target=funcion, args=args, daemon=True).start()


def plantilla_correo(titulo: str, intro: str, codigo: str = "", pie: str = "") -> str:
    """HTML de los correos con la marca de Agro-Colab.

    Tablas y estilos en línea: los clientes de correo (Gmail, Outlook)
    ignoran las hojas de estilo. Todo texto variable pasa por html.escape. No
    incluye el nombre: lo escribe quien registra la cuenta, y se podría usar para
    enviar texto engañoso a un tercero desde el remitente del proyecto.
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
        f"<tr><td style='padding:8px 40px 16px;color:#3d4842;font-size:15px;line-height:1.6'>{html.escape(intro)}</td></tr>"
        f"{bloque_codigo}"
        f"<tr><td style='padding:16px 40px 36px;color:#67716b;font-size:13px;line-height:1.6'>{html.escape(pie)}</td></tr>"
        "<tr><td style='border-top:1px solid #edeae2;padding:18px 40px;color:#8b938f;font-size:12px'>"
        "Agro-Colab · Proyecto académico INGT1003, Universidad Mayor. Este correo se envió automáticamente; no lo respondas.</td></tr>"
        "</table></td></tr></table></body></html>"
    )


def enviar_codigo_verificacion(destino: str, codigo: str) -> bool:
    """Envía el código de verificación de cuenta por correo."""
    return enviar_correo(
        destino,
        "Tu código de verificación de Agro-Colab",
        plantilla_correo(
            "Verifica tu cuenta",
            "Para terminar de crear tu cuenta en Agro-Colab, ingresa este código:",
            codigo,
            "El código vence en 30 minutos. Si no creaste una cuenta, ignora este correo.",
        ),
    )


def enviar_codigo_recuperacion(destino: str, codigo: str) -> bool:
    """Envía el código para restablecer la contraseña."""
    return enviar_correo(
        destino,
        "Restablece tu contraseña de Agro-Colab",
        plantilla_correo(
            "Restablece tu contraseña",
            "Recibimos una solicitud para cambiar la contraseña de tu cuenta. Usa este código:",
            codigo,
            "El código vence en 15 minutos. Si no fuiste tú, ignora este correo: tu contraseña no cambiará.",
        ),
    )


def enviar_aviso_adopcion_cancelada(destino: str, arbol: str) -> bool:
    """Avisa al comprador que perdió su cupo porque el agricultor lo retiró."""
    return enviar_correo(
        destino,
        "Tu adopción en Agro-Colab se canceló",
        plantilla_correo(
            "Tu adopción se canceló",
            f"Tu cupo en {arbol} ya no está activo porque el agricultor lo retiró o eliminó su cuenta.",
            "",
            "Tu comprobante de pago sigue disponible en tu panel. Si tienes dudas, escríbenos.",
        ),
    )


def enviar_aviso_cambio_contrasena(destino: str) -> bool:
    """Avisa que la contraseña cambió, por si no fue el dueño de la cuenta."""
    return enviar_correo(
        destino,
        "Tu contraseña de Agro-Colab cambió",
        plantilla_correo(
            "Tu contraseña cambió",
            "La contraseña de tu cuenta se cambió correctamente y se cerraron las demás sesiones abiertas.",
            "",
            "Si no fuiste tú, restablécela de inmediato desde «¿Olvidaste tu contraseña?» y escríbenos.",
        ),
    )
