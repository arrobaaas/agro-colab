"""Router de monitoreo de seguridad.

- POST /api/seguridad/csp: el navegador avisa cuando la Content-Security-Policy
  bloqueó algo (normalmente, un intento de inyectar código).
- GET /api/seguridad/resumen: datos del panel de monitoreo. Requiere la
  cabecera X-Monitoreo-Token con el valor de la variable MONITOREO_TOKEN; si
  la variable no está definida (o es muy corta) el panel queda desactivado.
"""

import hmac
import os
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, StringConstraints

from core import limitar_por_ip
from seguridad import registrar_evento, resumen

router = APIRouter()

# Esquemas de extensiones del navegador: sus bloqueos no son ataques a la app
ORIGENES_IGNORADOS = ("chrome-extension", "moz-extension", "safari-extension", "safari-web-extension")


class ReporteCSP(BaseModel):
    directiva: Annotated[str, StringConstraints(max_length=100)] = ""
    bloqueado: Annotated[str, StringConstraints(max_length=300)] = ""
    pagina: Annotated[str, StringConstraints(max_length=300)] = ""
    muestra: Optional[Annotated[str, StringConstraints(max_length=120)]] = None


@router.post(
    "/api/seguridad/csp",
    status_code=204,
    dependencies=[Depends(limitar_por_ip(maximo=20, ventana_segundos=600))],
)
def reportar_csp(reporte: ReporteCSP):
    if not reporte.bloqueado.startswith(ORIGENES_IGNORADOS):
        registrar_evento(
            "csp_violacion", "advertencia",
            detalle=f"{reporte.directiva} bloqueó {reporte.bloqueado or 'inline'}"
                    f"{' · ' + reporte.muestra if reporte.muestra else ''} en {reporte.pagina}",
        )
    return Response(status_code=204)


@router.get(
    "/api/seguridad/resumen",
    dependencies=[Depends(limitar_por_ip(maximo=30, ventana_segundos=300))],
)
def resumen_seguridad(x_monitoreo_token: str = Header(default="")):
    esperado = os.getenv("MONITOREO_TOKEN", "")
    if len(esperado) < 24:
        # Sin un token largo configurado, el panel no existe
        raise HTTPException(status_code=404, detail={"status": "error", "mensaje": "Panel de monitoreo desactivado."})
    if not hmac.compare_digest(x_monitoreo_token, esperado):
        registrar_evento("acceso_denegado", "advertencia", detalle="token del panel de monitoreo incorrecto")
        raise HTTPException(status_code=401, detail={"status": "error", "mensaje": "Token de monitoreo incorrecto."})
    return resumen()
