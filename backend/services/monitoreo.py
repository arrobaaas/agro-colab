"""Monitoreo de seguridad: reportes de CSP y datos del panel."""

import hmac
import os

from errores import NoAutenticado, NoEncontrado
from schemas import ReporteCSP
from seguridad import registrar_evento, resumen

# Esquemas de extensiones del navegador: sus bloqueos no son ataques a la app
ORIGENES_IGNORADOS = ("chrome-extension", "moz-extension", "safari-extension", "safari-web-extension")


def registrar_csp(reporte: ReporteCSP):
    if not reporte.bloqueado.startswith(ORIGENES_IGNORADOS):
        registrar_evento(
            "csp_violacion", "advertencia",
            detalle=f"{reporte.directiva} bloqueó {reporte.bloqueado or 'inline'}"
                    f"{' · ' + reporte.muestra if reporte.muestra else ''} en {reporte.pagina}",
        )


def resumen_protegido(token: str) -> dict:
    esperado = os.getenv("MONITOREO_TOKEN", "")
    if len(esperado) < 24:
        # Sin un token largo configurado, el panel no existe
        raise NoEncontrado("Panel de monitoreo desactivado.")
    if not hmac.compare_digest(token.encode(), esperado.encode()):
        registrar_evento("acceso_denegado", "advertencia", detalle="token del panel de monitoreo incorrecto")
        raise NoAutenticado("Token de monitoreo incorrecto.")
    return resumen()
