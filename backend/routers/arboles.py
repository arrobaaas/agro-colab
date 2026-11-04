"""Rutas de árboles."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core import get_db, usuario_actual
from database import Usuario
from schemas import ArbolRequest
from services import arboles as servicio

router = APIRouter(tags=["Árboles"])


@router.get("/api/arboles")
def listar_arboles(db: Session = Depends(get_db)):
    return servicio.listar(db)


@router.get("/api/arboles/{arbol_id}")
def obtener_arbol(arbol_id: int, db: Session = Depends(get_db)):
    return servicio.obtener(db, arbol_id)


@router.post("/api/arboles", status_code=201)
def crear_arbol(data: ArbolRequest, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.crear(db, usuario, data)


@router.put("/api/arboles/{arbol_id}")
def actualizar_arbol(arbol_id: int, data: ArbolRequest, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.actualizar(db, usuario, arbol_id, data)


@router.delete("/api/arboles/{arbol_id}")
def eliminar_arbol(arbol_id: int, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.eliminar(db, usuario, arbol_id)
