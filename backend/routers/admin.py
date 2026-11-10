"""Rutas del panel de administración. Todas exigen una sesión de administrador."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core import get_db, usuario_admin
from database import Usuario
from schemas import AdminUsuarioRequest
from services import admin as servicio

router = APIRouter(tags=["Administración"])


@router.get("/api/admin/usuarios")
def listar_usuarios(admin: Usuario = Depends(usuario_admin), db: Session = Depends(get_db)):
    return servicio.listar(db, admin)


@router.get("/api/admin/usuarios/{usuario_id}")
def detalle_usuario(usuario_id: int, admin: Usuario = Depends(usuario_admin), db: Session = Depends(get_db)):
    return servicio.detalle(db, admin, usuario_id)


@router.put("/api/admin/usuarios/{usuario_id}")
def editar_usuario(usuario_id: int, data: AdminUsuarioRequest, admin: Usuario = Depends(usuario_admin), db: Session = Depends(get_db)):
    return servicio.editar(db, admin, usuario_id, data)


@router.delete("/api/admin/usuarios/{usuario_id}")
def eliminar_usuario(usuario_id: int, admin: Usuario = Depends(usuario_admin), db: Session = Depends(get_db)):
    return servicio.eliminar(db, admin, usuario_id)
