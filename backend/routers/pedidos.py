"""Rutas de pedidos."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core import get_db, usuario_actual
from database import Usuario
from schemas import LogisticaRequest, PedidoRequest
from services import pedidos as servicio

router = APIRouter(tags=["Pedidos"])


@router.post("/api/pedidos", status_code=201)
def registrar_pedido(pedido: PedidoRequest, cliente: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.registrar(db, cliente, pedido)


@router.get("/api/pedidos")
def listar_pedidos(cliente: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.listar(db, cliente)


@router.get("/api/pedidos/{pedido_id}")
def obtener_pedido(pedido_id: int, cliente: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.obtener(db, cliente, pedido_id)


@router.put("/api/pedidos/{pedido_id}")
def modificar_logistica(pedido_id: int, datos: LogisticaRequest, cliente: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.modificar_logistica(db, cliente, pedido_id, datos)


@router.delete("/api/pedidos/{pedido_id}")
def cancelar_plan(pedido_id: int, cliente: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    return servicio.cancelar_plan(db, cliente, pedido_id)
