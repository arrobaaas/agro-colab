"""Rutas de monitoreo de seguridad.

- POST /api/seguridad/csp: el navegador avisa cuando la Content-Security-Policy
  bloqueó algo (normalmente, un intento de inyectar código).
- GET /api/seguridad/resumen: datos del panel de monitoreo. Requiere la
  cabecera X-Monitoreo-Token con el valor de la variable MONITOREO_TOKEN; si
  la variable no está definida (o es muy corta) el panel queda desactivado.
"""

from fastapi import APIRouter, Depends, Header, Response

from core import limitar_por_ip
from schemas import ReporteCSP
from services import monitoreo as servicio

router = APIRouter(tags=["Monitoreo"])


@router.post("/api/seguridad/csp", status_code=204, dependencies=[Depends(limitar_por_ip(maximo=20, ventana_segundos=600))])
def reportar_csp(reporte: ReporteCSP):
    servicio.registrar_csp(reporte)
    return Response(status_code=204)


@router.get("/api/seguridad/resumen", dependencies=[Depends(limitar_por_ip(maximo=30, ventana_segundos=300))])
def resumen_seguridad(x_monitoreo_token: str = Header(default="")):
    return servicio.resumen_protegido(x_monitoreo_token)
