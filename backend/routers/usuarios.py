"""Rutas de cuentas: registro, sesión, recuperación y perfil."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core import get_db, limitar_por_ip, usuario_actual
from database import Usuario
from schemas import (
    EliminarCuentaRequest, LoginRequest, PerfilRequest, RecuperacionRequest, ReenvioRequest, RegistroRequest, RestablecerRequest,
    VerificacionRequest,
)
from services import cuentas as servicio

router = APIRouter(tags=["Cuentas"])


@router.post("/api/register", status_code=202, dependencies=[Depends(limitar_por_ip(maximo=5, ventana_segundos=3600))])
def registrar_usuario(data: RegistroRequest, db: Session = Depends(get_db)):
    """202 con el mismo cuerpo aunque el correo ya exista: la cuenta queda
    pendiente de verificar, y la respuesta no revela qué correos están registrados."""
    return servicio.registrar(db, data)


@router.post("/api/reenviar-codigo", dependencies=[Depends(limitar_por_ip(maximo=5, ventana_segundos=3600))])
def reenviar_codigo(data: ReenvioRequest, db: Session = Depends(get_db)):
    return servicio.reenviar_codigo(db, data)


@router.post("/api/login", dependencies=[Depends(limitar_por_ip(maximo=8, ventana_segundos=300))])
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return servicio.iniciar_sesion(db, data)


@router.post("/api/verificar-cuenta", dependencies=[Depends(limitar_por_ip(maximo=10, ventana_segundos=3600))])
def verificar_cuenta(data: VerificacionRequest, db: Session = Depends(get_db)):
    return servicio.verificar(db, data)


@router.get("/api/estado")
def estado_servicio():
    return servicio.estado_servicio()


@router.post("/api/recuperar-contrasena", dependencies=[Depends(limitar_por_ip(maximo=5, ventana_segundos=3600))])
def recuperar_contrasena(data: RecuperacionRequest, db: Session = Depends(get_db)):
    return servicio.recuperar_contrasena(db, data)


@router.post("/api/restablecer-contrasena", dependencies=[Depends(limitar_por_ip(maximo=10, ventana_segundos=3600))])
def restablecer_contrasena(data: RestablecerRequest, db: Session = Depends(get_db)):
    return servicio.restablecer_contrasena(db, data)


@router.get("/api/usuario/{usuario_id}")
def obtener_usuario(usuario_id: int, solicitante: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.obtener_perfil(db, solicitante, usuario_id)


@router.put("/api/perfil")
def actualizar_perfil(data: PerfilRequest, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.actualizar_perfil(db, usuario, data)


@router.delete("/api/perfil")
def eliminar_cuenta(data: EliminarCuentaRequest, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Elimina la cuenta de la sesión y todos sus datos (Art. 20 Ley 21.719).
    Exige la contraseña actual en el cuerpo: {"password": "..."}."""
    return servicio.eliminar_propia(db, usuario, data)
