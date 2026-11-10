"""Los archivos del repositorio se mantienen al día con el código."""

import json
import re
import subprocess
import sys
from pathlib import Path

import main

RAIZ = Path(__file__).resolve().parent.parent.parent
BACKEND = RAIZ / "backend"
COLECCION = RAIZ / "docs" / "AgroColab.postman_collection.json"


def operaciones_de_la_api() -> set:
    """Las operaciones reales, según el esquema OpenAPI que genera FastAPI."""
    return {
        (metodo.upper(), ruta)
        for ruta, operaciones in main.app.openapi()["paths"].items()
        for metodo in operaciones
    }


def test_la_tabla_de_la_api_coincide_con_las_rutas_reales():
    tabla = (RAIZ / "docs" / "API.md").read_text(encoding="utf-8")
    documentadas = set(re.findall(r"^\| `([A-Z]+)` \| `(/api/[^`]+)` \|", tabla, flags=re.M))
    assert len(documentadas) == 37
    assert documentadas == operaciones_de_la_api()


def test_env_example_declara_todas_las_variables():
    variables = set()
    for archivo in [*BACKEND.glob("*.py"), *BACKEND.glob("*/*.py")]:
        variables |= set(re.findall(r"""(?:getenv|environ\[|variable\(|environ\.get\()\(?["']([A-Z_]+)["']""", archivo.read_text(encoding="utf-8")))
    plantilla = (RAIZ / ".env.example").read_text(encoding="utf-8")
    declaradas = set(re.findall(r"^#?\s*([A-Z_]+)=", plantilla, flags=re.M))
    assert variables
    assert variables - declaradas == set()


def test_las_credenciales_estan_excluidas_del_repositorio():
    reglas = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in reglas and "!.env.example" in reglas


def test_el_script_sql_coincide_con_los_modelos():
    resultado = subprocess.run(
        [sys.executable, "-c", (
            "import runpy; m = runpy.run_path('db/generar_esquema.py');"
            "import sys; sys.stdout.reconfigure(encoding='utf-8'); sys.stdout.write(m['esquema_sql']())"
        )],
        cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", check=True,
    )
    assert resultado.stdout == (RAIZ / "db" / "esquema.sql").read_text(encoding="utf-8")


def _peticiones(nodos):
    for nodo in nodos:
        if "item" in nodo:
            yield from _peticiones(nodo["item"])
        else:
            yield nodo


def test_la_coleccion_funciona_completa(cliente):
    """Ejecuta cada petición en orden y comprueba el código que declara su prueba."""
    coleccion = json.loads(COLECCION.read_text(encoding="utf-8"))
    variables = {v["key"]: v["value"] for v in coleccion["variable"]}

    def sustituir(texto):
        return re.sub(r"\{\{(\w+)\}\}", lambda m: str(variables[m.group(1)]), texto)

    peticiones = list(_peticiones(coleccion["item"]))
    assert len(peticiones) >= 10
    for item in peticiones:
        pedido = item["request"]
        script = "\n".join(item["event"][0]["script"]["exec"])
        esperado = int(re.search(r"have\.status\((\d+)\)", script).group(1))
        ruta = sustituir(pedido["url"]["raw"]).replace(variables["baseUrl"], "")
        cabeceras = {h["key"]: sustituir(h["value"]) for h in pedido["header"]}
        contenido = None
        if "body" in pedido:
            contenido = sustituir(pedido["body"]["raw"])
        respuesta = cliente.request(pedido["method"], ruta, headers=cabeceras, content=contenido)
        assert respuesta.status_code == esperado, f"{item['name']}: {respuesta.status_code} {respuesta.text}"
        for variable, camino in re.findall(r'collectionVariables\.set\("(\w+)", cuerpo\.([\w.]+)\)', script):
            valor = respuesta.json()
            for parte in camino.split("."):
                valor = valor[parte]
            variables[variable] = valor
