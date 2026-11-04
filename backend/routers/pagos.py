"""Rutas de la pasarela de pago simulada."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core import get_db, usuario_actual
from database import Usuario
from schemas import PagoRequest
from services import pagos as servicio

router = APIRouter(tags=["Pagos"])


@router.post("/api/pagos", status_code=201)
def pagar(datos: PagoRequest, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.pagar(db, usuario, datos)


@router.get("/api/pagos")
def mis_pagos(usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.listar(db, usuario)


@router.get("/api/pagos/{pago_id}")
def obtener_pago(pago_id: int, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.obtener(db, usuario, pago_id)
