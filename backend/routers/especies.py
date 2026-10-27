"""Router de catálogo de especies."""

from fastapi import APIRouter

from core import listar_especies

router = APIRouter()


@router.get("/api/especies")
def listar_catalogo_especies():
    """Catálogo cerrado de especies con las fotos que el agricultor puede usar."""
    return listar_especies()
