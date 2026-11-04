"""Las capas se comprueban leyendo el código: si alguien mezcla responsabilidades,
la integración continua falla.

routers (HTTP) -> services (negocio) -> repositories (datos) -> database
"""

import ast
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
ROUTERS = sorted((BACKEND / "routers").glob("*.py"))
SERVICES = sorted((BACKEND / "services").glob("*.py"))
REPOSITORIES = sorted((BACKEND / "repositories").glob("*.py"))
OPERACIONES_DE_SESION = {"query", "add", "add_all", "delete", "commit", "rollback", "flush", "refresh", "execute", "merge"}


def arbol(archivo: Path):
    return ast.parse(archivo.read_text(encoding="utf-8"))


def importaciones(archivo: Path) -> set:
    """Módulos que importa el archivo, incluidos los submódulos de `from x import y`."""
    modulos = set()
    for nodo in ast.walk(arbol(archivo)):
        if isinstance(nodo, ast.Import):
            modulos.update(n.name for n in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.add(nodo.module)
    return modulos


def operaciones_de_sesion(archivo: Path) -> list:
    """Llamadas como db.query(...) o session.commit() en el archivo."""
    return [
        f"{archivo.name}:{nodo.lineno} {nodo.func.value.id}.{nodo.func.attr}"
        for nodo in ast.walk(arbol(archivo))
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Attribute)
        and isinstance(nodo.func.value, ast.Name)
        and nodo.func.value.id in {"db", "session", "sesion"}
        and nodo.func.attr in OPERACIONES_DE_SESION
    ]


@pytest.mark.parametrize("archivo", [*ROUTERS, *SERVICES, BACKEND / "core.py", BACKEND / "seguridad.py", BACKEND / "main.py"], ids=lambda a: a.name)
def test_las_consultas_viven_solo_en_la_capa_de_datos(archivo):
    assert operaciones_de_sesion(archivo) == []


@pytest.mark.parametrize("archivo", ROUTERS, ids=lambda a: a.name)
def test_los_routers_no_saltan_la_capa_de_negocio(archivo):
    prohibidos = {m for m in importaciones(archivo) if m.startswith("repositories") or m == "sqlalchemy"}
    assert not prohibidos


@pytest.mark.parametrize("archivo", ROUTERS, ids=lambda a: a.name)
def test_los_routers_no_contienen_reglas(archivo):
    """Una ruta solo llama a un servicio: sin condicionales ni ciclos."""
    condicionales = [n.lineno for n in ast.walk(arbol(archivo)) if isinstance(n, (ast.If, ast.For, ast.While, ast.Try))]
    assert condicionales == []


@pytest.mark.parametrize("archivo", SERVICES, ids=lambda a: a.name)
def test_el_negocio_no_conoce_http(archivo):
    prohibidos = {m for m in importaciones(archivo) if m.split(".")[0] in {"fastapi", "starlette", "routers"}}
    assert not prohibidos


@pytest.mark.parametrize("archivo", REPOSITORIES, ids=lambda a: a.name)
def test_los_datos_no_dependen_de_capas_superiores(archivo):
    prohibidos = {m for m in importaciones(archivo) if m.split(".")[0] in {"fastapi", "routers", "services", "core", "seguridad"}}
    assert not prohibidos
