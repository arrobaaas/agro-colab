"""Router de logística y pedidos."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core import PedidoRequest, get_db
from database import Pedido, Usuario

router = APIRouter()


@router.post("/api/pedidos")
def registrar_pedido(pedido: PedidoRequest, db: Session = Depends(get_db)):
    # El cliente puede venir identificado por sesión (id) o por correo
    cliente = None
    if pedido.cliente_id is not None:
        cliente = db.query(Usuario).filter(Usuario.id == pedido.cliente_id).first()
    if not cliente:
        cliente = db.query(Usuario).filter(Usuario.email == pedido.email).first()
    if not cliente:
        return {"status": "error", "mensaje": "Cliente no encontrado."}

    nuevo_pedido = Pedido(
        cliente_id=cliente.id,  # identificado con el usuario autenticado
        plan_nombre=pedido.plan_nombre,
        monto_clp=pedido.monto_clp,
        tipo_destino=pedido.tipo_destino,
        razon_social=pedido.razon_social,
        rut=pedido.rut,
        direccion=pedido.direccion,
        comuna=pedido.comuna,
        frecuencia_entrega=pedido.frecuencia_entrega,
        codigo_seguimiento=f"AGRO-{db.query(Pedido).count() + 1:04d}",
        estado_logistica="En coordinación con huerto de origen"
    )
    db.add(nuevo_pedido)
    db.commit()
    db.refresh(nuevo_pedido)

    return {
        "status": "success",
        "mensaje": f"Plan contratado con éxito. Código de despacho: {nuevo_pedido.codigo_seguimiento}",
        "pedido": {
            "id": nuevo_pedido.id,
            "plan_nombre": nuevo_pedido.plan_nombre,
            "monto_clp": nuevo_pedido.monto_clp,
            "tipo_destino": nuevo_pedido.tipo_destino,
            "direccion": nuevo_pedido.direccion,
            "comuna": nuevo_pedido.comuna,
            "frecuencia_entrega": nuevo_pedido.frecuencia_entrega,
            "codigo_seguimiento": nuevo_pedido.codigo_seguimiento,
            "fecha_registro": nuevo_pedido.fecha_registro.strftime("%d/%m/%Y %H:%M"),
            "estado_logistica": nuevo_pedido.estado_logistica
        }
    }


@router.get("/api/pedidos")
def listar_pedidos(db: Session = Depends(get_db)):
    pedidos = db.query(Pedido).all()
    return [
        {
            "id": p.id,
            "plan_nombre": p.plan_nombre,
            "monto_clp": p.monto_clp,
            "tipo_destino": p.tipo_destino,
            "direccion": p.direccion,
            "comuna": p.comuna,
            "frecuencia_entrega": p.frecuencia_entrega,
            "codigo_seguimiento": p.codigo_seguimiento,
            "fecha_registro": p.fecha_registro.strftime("%d/%m/%Y %H:%M"),
            "estado_logistica": p.estado_logistica
        }
        for p in pedidos
    ]
