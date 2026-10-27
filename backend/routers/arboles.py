"""Router de árboles (catálogo, adopción y gestión de publicaciones)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core import (
    ArbolRequest, validar_imagen, buscar_especie, componer_nombre,
    normalizar_identificador, serializar_arbol, cupos_ocupados_de, get_db,
)
from database import Arbol, Usuario

router = APIRouter()


@router.get("/api/arboles")
def listar_arboles(db: Session = Depends(get_db)):
    arboles = db.query(Arbol).all()
    return [serializar_arbol(a, db) for a in arboles]


@router.post("/api/arboles")
def crear_arbol(data: ArbolRequest, db: Session = Depends(get_db)):
    # La especie debe existir en el catálogo: no se aceptan nombres libres
    especie = buscar_especie(data.especie)
    if not especie:
        return {"status": "error", "mensaje": "La especie seleccionada no está en el catálogo."}

    # Buscar al productor por nombre
    productor = db.query(Usuario).filter(Usuario.nombre == data.productor).first()
    if not productor:
        return {"status": "error", "mensaje": "Productor no encontrado."}

    # La imagen debe ser del catálogo de la especie o una foto propia válida
    imagen, origen, error = validar_imagen(data.imagen, data.especie)
    if error:
        return {"status": "error", "mensaje": error}

    nuevo_arbol = Arbol(
        nombre=componer_nombre(data.especie, data.identificador),
        especie=data.especie,
        identificador=normalizar_identificador(data.identificador) or None,
        ubicacion=data.ubicacion,
        plan=data.plan,
        tipo_suscripcion=data.tipo_suscripcion,
        cupos_totales=data.cupos_totales,
        cupos_ocupados=0,
        precio_mensual_clp=data.precio_mensual_clp,
        estimacion_cosecha=data.estimacion_cosecha,
        imagen=imagen,
        imagen_origen=origen,
        productor_id=productor.id
    )
    db.add(nuevo_arbol)
    db.commit()
    db.refresh(nuevo_arbol)
    return {
        "status": "success",
        "mensaje": f"Árbol '{nuevo_arbol.nombre}' publicado correctamente.",
        "arbol": serializar_arbol(nuevo_arbol, db)
    }


@router.put("/api/arboles/{arbol_id}")
def actualizar_arbol(arbol_id: int, data: ArbolRequest, db: Session = Depends(get_db)):
    arbol = db.query(Arbol).filter(Arbol.id == arbol_id).first()
    if not arbol:
        return {"status": "error", "mensaje": "Árbol no encontrado."}

    especie = buscar_especie(data.especie)
    if not especie:
        return {"status": "error", "mensaje": "La especie seleccionada no está en el catálogo."}

    imagen, origen, error = validar_imagen(data.imagen, data.especie)
    if error:
        return {"status": "error", "mensaje": error}

    arbol.nombre = componer_nombre(data.especie, data.identificador)
    arbol.especie = data.especie
    arbol.identificador = normalizar_identificador(data.identificador) or None
    arbol.ubicacion = data.ubicacion
    arbol.plan = data.plan
    arbol.tipo_suscripcion = data.tipo_suscripcion
    arbol.cupos_totales = data.cupos_totales
    arbol.precio_mensual_clp = data.precio_mensual_clp
    arbol.estimacion_cosecha = data.estimacion_cosecha
    arbol.imagen = imagen
    arbol.imagen_origen = origen

    db.commit()
    db.refresh(arbol)

    return {
        "status": "success",
        "mensaje": f"Árbol '{arbol.nombre}' actualizado correctamente.",
        "arbol": serializar_arbol(arbol, db)
    }


@router.delete("/api/arboles/{arbol_id}")
def eliminar_arbol(arbol_id: int, db: Session = Depends(get_db)):
    arbol = db.query(Arbol).filter(Arbol.id == arbol_id).first()
    if not arbol:
        return {"status": "error", "mensaje": "Árbol no encontrado."}

    db.delete(arbol)
    db.commit()
    return {"status": "success", "mensaje": f"Árbol '{arbol.nombre}' eliminado correctamente."}
