"""Rutas de suscripciones. La adopción se crea con POST /api/pagos."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core import get_db, usuario_actual
from database import Usuario
from services import suscripciones as servicio

router = APIRouter(tags=["Suscripciones"])


@router.get("/api/mis-arboles/{productor_id}/suscriptores")
def listar_suscriptores(productor_id: int, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.listar_suscriptores(db, usuario, productor_id)


@router.get("/api/suscripciones/usuario/{usuario_id}")
def listar_suscripciones_usuario(usuario_id: int, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.listar_de_usuario(db, usuario, usuario_id)


@router.delete("/api/suscripciones/{suscripcion_id}")
def expulsar_suscriptor(suscripcion_id: int, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.expulsar(db, usuario, suscripcion_id)


@router.delete("/api/arboles/{arbol_id}/suscripcion")
def cancelar_suscripcion(arbol_id: int, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Cancela la suscripción propia a un árbol y libera el cupo."""
    return servicio.cancelar(db, usuario, arbol_id)
