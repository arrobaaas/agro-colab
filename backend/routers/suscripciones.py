"""Router de suscripciones (adopción, cancelación y gestión de cupos)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from core import (
    SuscripcionRequest, resolver_usuario, cupos_ocupados_de, serializar_arbol,
    get_db, especie_de_arbol, buscar_especie,
)
from database import Arbol, Suscripcion, Usuario

router = APIRouter()


@router.post("/api/suscribir")
def suscribir(data: SuscripcionRequest, db: Session = Depends(get_db)):
    arbol = db.query(Arbol).filter(Arbol.id == data.tree_id).first()
    if not arbol:
        return {"status": "error", "mensaje": "Árbol no encontrado."}

    # Buscar al usuario real (por id, correo o nombre)
    usuario = resolver_usuario(db, data.user_id, data.user_name, data.email)
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}

    # El cupo disponible se calcula sobre las suscripciones reales
    ocupados = cupos_ocupados_de(arbol, db)
    if ocupados >= arbol.cupos_totales:
        return {"status": "error", "mensaje": "Cupos agotados para este árbol."}

    # Un mismo usuario no puede ocupar dos cupos del mismo árbol
    ya_suscrito = db.query(Suscripcion).filter(
        Suscripcion.arbol_id == arbol.id,
        Suscripcion.usuario_id == usuario.id
    ).first()
    if ya_suscrito:
        return {
            "status": "error",
            "mensaje": f"Ya estás suscrito a {arbol.nombre}. No puedes ocupar dos cupos del mismo árbol."
        }

    # Crear registro de suscripción con el usuario real
    suscripcion = Suscripcion(usuario_id=usuario.id, arbol_id=data.tree_id)
    db.add(suscripcion)
    db.flush()

    arbol.cupos_ocupados = cupos_ocupados_de(arbol, db)
    db.commit()

    return {
        "status": "success",
        "mensaje": f"¡Suscripción confirmada para {usuario.nombre} en {arbol.nombre}!",
        "arbol": serializar_arbol(arbol, db)
    }


@router.get("/api/mis-arboles/{productor_id}/suscriptores")
def listar_suscriptores(productor_id: int, db: Session = Depends(get_db)):
    """Lista los usuarios suscritos a los árboles de un productor."""
    arboles = (
        db.query(Arbol)
        .options(joinedload(Arbol.productor))
        .filter(Arbol.productor_id == productor_id)
        .all()
    )

    resultado = []
    for arbol in arboles:
        suscripciones = (
            db.query(Suscripcion)
            .options(joinedload(Suscripcion.usuario))
            .filter(Suscripcion.arbol_id == arbol.id)
            .all()
        )
        suscriptores = []
        for s in suscripciones:
            u = s.usuario
            if u:
                suscriptores.append({
                    "suscripcion_id": s.id,
                    "usuario_id": u.id,
                    "nombre": u.nombre,
                    "email": u.email,
                    "telefono": u.telefono,
                    "direccion": u.direccion,
                    "rol": u.rol,
                    "fecha_suscripcion": s.fecha_suscripcion.strftime("%d/%m/%Y") if s.fecha_suscripcion else None
                })

        resultado.append({
            "arbol_id": arbol.id,
            "arbol_nombre": arbol.nombre,
            "cupos_totales": arbol.cupos_totales,
            "cupos_ocupados": len(suscriptores),
            "suscriptores": suscriptores
        })

    return resultado


@router.get("/api/suscripciones/usuario/{usuario_id}")
def listar_suscripciones_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Árboles que un usuario tiene adoptados, para su panel de perfil."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}

    suscripciones = (
        db.query(Suscripcion)
        .options(joinedload(Suscripcion.arbol).joinedload(Arbol.productor))
        .filter(Suscripcion.usuario_id == usuario_id)
        .all()
    )

    arboles = []
    for suscripcion in suscripciones:
        arbol = suscripcion.arbol
        if not arbol:
            continue
        arboles.append({
            "suscripcion_id": suscripcion.id,
            "arbol_id": arbol.id,
            "nombre": arbol.nombre,
            "especie": especie_de_arbol(arbol),
            "especie_nombre": (buscar_especie(especie_de_arbol(arbol)) or {}).get("nombre"),
            "plan": arbol.plan,
            "tipo_suscripcion": arbol.tipo_suscripcion,
            "precio_mensual_clp": arbol.precio_mensual_clp,
            "imagen": arbol.imagen,
            "ubicacion": arbol.ubicacion,
            "estimacion_cosecha": arbol.estimacion_cosecha,
            "cupos_totales": arbol.cupos_totales,
            "cupos_ocupados": cupos_ocupados_de(arbol, db),
            "productor": arbol.productor.nombre if arbol.productor else None,
            "fecha_suscripcion": suscripcion.fecha_suscripcion.strftime("%d/%m/%Y") if suscripcion.fecha_suscripcion else None,
        })

    return {"status": "success", "arboles": arboles}


@router.delete("/api/suscripciones/{suscripcion_id}")
def expulsar_suscriptor(suscripcion_id: int, db: Session = Depends(get_db)):
    """Expulsa a un suscriptor de un árbol y libera su cupo."""
    suscripcion = db.query(Suscripcion).filter(Suscripcion.id == suscripcion_id).first()
    if not suscripcion:
        return {"status": "error", "mensaje": "Suscripción no encontrada."}

    arbol = db.query(Arbol).filter(Arbol.id == suscripcion.arbol_id).first()

    db.delete(suscripcion)
    db.flush()
    if arbol:
        arbol.cupos_ocupados = cupos_ocupados_de(arbol, db)
    db.commit()

    return {"status": "success", "mensaje": "Suscriptor expulsado y cupo liberado."}


@router.post("/api/cancelar-suscripcion")
def cancelar_suscripcion(data: SuscripcionRequest, db: Session = Depends(get_db)):
    arbol = db.query(Arbol).filter(Arbol.id == data.tree_id).first()
    if not arbol:
        return {"status": "error", "mensaje": "Árbol no encontrado."}

    usuario = resolver_usuario(db, data.user_id, data.user_name, data.email)
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}

    # Se busca la suscripción real del usuario: sin esto, cancelar solo
    # bajaba el contador y el usuario seguía suscrito.
    suscripcion = db.query(Suscripcion).filter(
        Suscripcion.arbol_id == arbol.id,
        Suscripcion.usuario_id == usuario.id
    ).first()

    if not suscripcion:
        return {"status": "error", "mensaje": "No hay suscriptores que cancelar."}

    db.delete(suscripcion)
    db.flush()

    arbol.cupos_ocupados = cupos_ocupados_de(arbol, db)
    db.commit()

    return {
        "status": "success",
        "mensaje": f"Suscripción cancelada para {usuario.nombre} en {arbol.nombre}.",
        "arbol": serializar_arbol(arbol, db)
    }
