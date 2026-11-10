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


@router.post("/api/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """El límite por IP y por cuenta lo aplica el servicio: solo cuentan los fallos."""
    return servicio.iniciar_sesion(db, data)


@router.post("/api/logout")
def logout(usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Cierra en el servidor todas las sesiones de la cuenta."""
    return servicio.cerrar_sesion(db, usuario)


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


@router.get("/api/perfil/exportar")
def exportar_datos(usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Copia de los datos de la cuenta (derechos de acceso y portabilidad, Ley 21.719)."""
    return servicio.exportar_datos(db, usuario)


@router.delete("/api/perfil")
def eliminar_cuenta(data: EliminarCuentaRequest, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Elimina la cuenta de la sesión y sus datos (derecho de supresión, Ley 21.719)."""
    return servicio.eliminar_propia(db, usuario, data)
