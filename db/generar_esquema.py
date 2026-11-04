"""Genera db/esquema.sql desde los modelos de backend/database.py.

Uso, desde la raíz del repositorio:  python db/generar_esquema.py
Una prueba automatizada comprueba que el archivo coincida con los modelos.
"""

import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENCABEZADO = """-- Esquema de la base de datos de Agro-Colab para PostgreSQL.
-- Archivo generado por db/generar_esquema.py: no editar a mano.
-- Uso:  createdb agrocolab && psql -d agrocolab -f db/esquema.sql
-- La aplicación también crea este esquema sola al arrancar (backend/main.py).

"""


def esquema_sql() -> str:
    # Importar los modelos no debe abrir ninguna base real
    os.environ["AGROCOLAB_DB_URL"] = f"sqlite:///{tempfile.gettempdir()}/agrocolab-esquema.db"
    sys.path.insert(0, str(RAIZ / "backend"))

    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateIndex, CreateTable

    from database import Base

    dialecto = postgresql.dialect()
    bloques = []
    for tabla in Base.metadata.sorted_tables:
        sentencias = ["\n".join(
            linea.rstrip() for linea in str(CreateTable(tabla).compile(dialect=dialecto)).strip().replace("\t", "  ").splitlines()
        ) + ";"]
        sentencias += [
            str(CreateIndex(indice).compile(dialect=dialecto)) + ";"
            for indice in sorted(tabla.indexes, key=lambda i: i.name)
        ]
        bloques.append("\n".join(sentencias))
    return ENCABEZADO + "\n\n".join(bloques) + "\n"


if __name__ == "__main__":
    destino = RAIZ / "db" / "esquema.sql"
    destino.write_text(esquema_sql(), encoding="utf-8")
    print(f"Escrito {destino}")
