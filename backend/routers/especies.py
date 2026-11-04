"""Rutas del catálogo de especies."""

from fastapi import APIRouter

from catalogo import listar_especies

router = APIRouter(tags=["Especies"])


@router.get("/api/especies")
def listar_catalogo_especies():
    """Catálogo cerrado de especies con las fotos que el agricultor puede usar."""
    return listar_especies()
