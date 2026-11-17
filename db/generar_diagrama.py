"""Genera db/modelo_datos.png desde los modelos de backend/database.py.

Uso, desde la raíz del repositorio:  python db/generar_diagrama.py
Necesita Google Chrome o Chromium para convertir el SVG en PNG. Si no lo
encuentra, deja el SVG en db/modelo_datos.svg.

Las columnas, tipos y claves salen de los modelos, así el diagrama no se
desactualiza cuando cambia el esquema. La posición de cada tabla y el recorrido
de cada relación están fijos aquí abajo.
"""

import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from html import escape
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Medidas en píxeles
ANCHO_TABLA = 548
ALTO_TITULO = 52
ALTO_FILA = 33
RELLENO = 16
COLUMNAS_X = (26, 648, 1270)
ARRIBA = 110

COLOR_TABLA = "#6d28d9"
COLOR_AUDITORIA = "#57534e"
COLOR_LINEA = "#1c1917"
FUENTE = "'DejaVu Sans Mono', 'Liberation Mono', Menlo, Consolas, monospace"
FUENTE_TEXTO = "'Inter', 'DejaVu Sans', 'Liberation Sans', Arial, sans-serif"

# Aclaraciones que no se deducen de los modelos
NOTAS = {
    ("usuarios", "password"): "hash",
    ("pagos", "arbol_id"): "sin FK",
    ("pagos", "pedido_id"): "sin FK",
    ("eventos_seguridad", "usuario_id"): "sin FK",
    ("pedidos", "arbol_id"): "opcional",
}


def cargar_tablas():
    # Importar los modelos no debe abrir ninguna base real
    os.environ["AGROCOLAB_DB_URL"] = f"sqlite:///{tempfile.gettempdir()}/agrocolab-diagrama.db"
    sys.path.insert(0, str(RAIZ / "backend"))
    from sqlalchemy import CheckConstraint, UniqueConstraint
    from sqlalchemy.dialects import postgresql

    from database import Base

    dialecto = postgresql.dialect()
    tablas = {}
    for tabla in Base.metadata.sorted_tables:
        unicas = {
            next(iter(i.columns)).name for i in tabla.indexes if i.unique and len(i.columns) == 1
        } | {
            next(iter(c.columns)).name for c in tabla.constraints
            if isinstance(c, UniqueConstraint) and len(c.columns) == 1
        }
        filas = []
        for col in tabla.columns:
            tipo = col.type.compile(dialect=dialecto).replace(" WITHOUT TIME ZONE", "")
            marca = "PK" if col.primary_key else "FK" if col.foreign_keys else "UQ" if col.name in unicas else ""
            nota = NOTAS.get((tabla.name, col.name))
            filas.append({"marca": marca, "nombre": col.name, "tipo": tipo, "nota": nota})
        # Primero la clave primaria y las foráneas, como se leen en un diagrama
        filas.sort(key=lambda f: {"PK": 0, "FK": 1}.get(f["marca"], 2))
        for c in tabla.constraints:
            if isinstance(c, UniqueConstraint) and len(c.columns) > 1:
                filas.append({"marca": "UQ", "nombre": "(" + ", ".join(x.name for x in c.columns) + ")", "tipo": "", "nota": None})
            if isinstance(c, CheckConstraint):
                texto = str(c.sqltext)
                # "x >= 0 AND x <= y" se lee mejor como "0 ≤ x ≤ y"
                rango = re.fullmatch(r"(\w+) >= (\w+) AND \1 <= (\w+)", texto)
                texto = f"{rango[2]} ≤ {rango[1]} ≤ {rango[3]}" if rango else texto.replace(">=", "≥").replace("<=", "≤")
                filas.append({"marca": "CK", "nombre": texto, "tipo": "", "nota": None, "chica": True})
        tablas[tabla.name] = filas
    return tablas


def alto(filas):
    return ALTO_TITULO + ALTO_FILA * len(filas) + RELLENO


def caja(nombre, filas, x, y, color):
    h = alto(filas)
    partes = [
        f'<rect x="{x}" y="{y}" width="{ANCHO_TABLA}" height="{h}" rx="12" fill="#fff" stroke="{color}" stroke-width="3"/>',
        f'<path d="M{x} {y + ALTO_TITULO} v-{ALTO_TITULO - 12} a12 12 0 0 1 12 -12 h{ANCHO_TABLA - 24} a12 12 0 0 1 12 12 v{ALTO_TITULO - 12} z" fill="{color}"/>',
        f'<text x="{x + 22}" y="{y + 36}" font-family="{FUENTE}" font-size="28" fill="#fff">{escape(nombre)}</text>',
    ]
    colores_marca = {"PK": "#065f46", "FK": "#1d4ed8", "UQ": "#b45309", "CK": "#b91c1c"}
    for i, f in enumerate(filas):
        base = y + ALTO_TITULO + ALTO_FILA * i + 30
        if f["marca"]:
            partes.append(f'<text x="{x + 20}" y="{base}" font-family="{FUENTE}" font-size="22" font-weight="bold" fill="{colores_marca[f["marca"]]}">{f["marca"]}</text>')
        peso = "bold" if f["marca"] in ("PK", "FK", "UQ") else "normal"
        tam = 18 if f.get("chica") else 24
        nombre = f["nombre"] + (f" · {f['nota']}" if f["nota"] and f["nota"] != "hash" else "")
        partes.append(f'<text x="{x + 66}" y="{base}" font-family="{FUENTE}" font-size="{tam}" font-weight="{peso}" fill="#1c1917">{escape(nombre)}</text>')
        tipo = f["tipo"] + (" · hash" if f["nota"] == "hash" else "")
        if tipo:
            partes.append(f'<text x="{x + ANCHO_TABLA - 18}" y="{base}" text-anchor="end" font-family="{FUENTE}" font-size="20" fill="#57534e">{escape(tipo)}</text>')
    return "\n".join(partes), h


def pata_de_gallo(x, y, direccion):
    """Extremo "muchos" de una relación. (x, y) toca el borde de la tabla y
    direccion es hacia dónde entra la línea: 'abajo', 'derecha' o 'izquierda'."""
    d, s = 16, 11
    if direccion == "abajo":
        return f'<path d="M{x - s} {y} L{x} {y - d} L{x + s} {y} M{x} {y} L{x} {y - d}" fill="none" stroke="{COLOR_LINEA}" stroke-width="3"/>'
    if direccion == "derecha":
        return f'<path d="M{x} {y - s} L{x - d} {y} L{x} {y + s} M{x} {y} L{x - d} {y}" fill="none" stroke="{COLOR_LINEA}" stroke-width="3"/>'
    return f'<path d="M{x} {y - s} L{x + d} {y} L{x} {y + s} M{x} {y} L{x + d} {y}" fill="none" stroke="{COLOR_LINEA}" stroke-width="3"/>'


def linea(puntos):
    d = "M" + " L".join(f"{x} {y}" for x, y in puntos)
    return f'<path d="{d}" fill="none" stroke="{COLOR_LINEA}" stroke-width="3"/>'


def etiqueta(x, y, texto, ancla="middle"):
    return f'<text x="{x}" y="{y}" text-anchor="{ancla}" font-family="{FUENTE_TEXTO}" font-size="24" font-weight="600" fill="{COLOR_LINEA}">{escape(texto)}</text>'


def svg(tablas):
    c1, c2, c3 = COLUMNAS_X
    w = ANCHO_TABLA
    partes = []

    # Fila superior
    s_usuarios, h_usuarios = caja("usuarios", tablas["usuarios"], c1, ARRIBA, COLOR_TABLA)
    s_susc, h_susc = caja("suscripciones", tablas["suscripciones"], c2, ARRIBA, COLOR_TABLA)
    s_arboles, h_arboles = caja("arboles", tablas["arboles"], c3, ARRIBA, COLOR_TABLA)
    fondo_usuarios = ARRIBA + h_usuarios
    fondo_arboles = ARRIBA + h_arboles

    # Fila inferior
    y_pagos = fondo_usuarios + 80
    s_pagos, h_pagos = caja("pagos", tablas["pagos"], c1, y_pagos, COLOR_TABLA)
    y_pedidos = fondo_arboles + 80
    s_pedidos, h_pedidos = caja("pedidos", tablas["pedidos"], c3, y_pedidos, COLOR_TABLA)

    # Tablas de auditoría, sin claves foráneas, en un recuadro aparte
    y_cliente = ARRIBA + h_susc + 120
    y_grupo = y_cliente + 60
    s_eventos, h_eventos = caja("eventos_seguridad", tablas["eventos_seguridad"], c2, y_grupo + 56, COLOR_AUDITORIA)
    s_intentos, h_intentos = caja("intentos_acceso", tablas["intentos_acceso"], c2, y_grupo + 56 + h_eventos + 24, COLOR_AUDITORIA)
    alto_grupo = 56 + h_eventos + 24 + h_intentos + 20
    partes.append(f'<rect x="{c2 - 20}" y="{y_grupo}" width="{w + 40}" height="{alto_grupo}" rx="16" fill="#f5f5f4" stroke="#d6d3d1" stroke-width="3"/>')
    partes.append(f'<text x="{c2 + 4}" y="{y_grupo + 38}" font-family="{FUENTE_TEXTO}" font-size="22" font-weight="600" fill="#57534e">SIN CLAVES FORÁNEAS · auditoría y límites</text>')

    # Relaciones
    x_prod_u = c1 + 240
    x_prod_a = c3 + w // 2
    partes.append(linea([(x_prod_u, ARRIBA), (x_prod_u, 56), (x_prod_a, 56), (x_prod_a, ARRIBA)]))
    partes.append(pata_de_gallo(x_prod_a, ARRIBA, "abajo"))
    partes.append(etiqueta((x_prod_u + x_prod_a) // 2, 44, "productor_id 1 : N"))

    y_susc = ARRIBA + ALTO_TITULO + ALTO_FILA * 2
    partes.append(linea([(c1 + w, y_susc), (c2, y_susc)]))
    partes.append(pata_de_gallo(c2, y_susc, "derecha"))
    partes.append(linea([(c3, y_susc), (c2 + w, y_susc)]))
    partes.append(pata_de_gallo(c2 + w, y_susc, "izquierda"))

    x_pagos = c1 + 274
    partes.append(linea([(x_pagos, fondo_usuarios), (x_pagos, y_pagos)]))
    partes.append(pata_de_gallo(x_pagos, y_pagos, "abajo"))
    partes.append(etiqueta(x_pagos + 18, fondo_usuarios + 48, "usuario_id 1 : N", "start"))

    x_quiebre = c3 - 30
    y_entrada = y_pedidos + ALTO_TITULO + ALTO_FILA * 1
    partes.append(linea([(c1 + w, y_cliente), (x_quiebre, y_cliente), (x_quiebre, y_entrada), (c3, y_entrada)]))
    partes.append(pata_de_gallo(c3, y_entrada, "derecha"))
    partes.append(etiqueta((c1 + w + x_quiebre) // 2, y_cliente - 14, "cliente_id 1 : N"))

    x_arbol = c3 + 274
    partes.append(linea([(x_arbol, fondo_arboles), (x_arbol, y_pedidos)]))
    partes.append(pata_de_gallo(x_arbol, y_pedidos, "abajo"))
    partes.append(etiqueta(x_arbol + 18, fondo_arboles + 48, "arbol_id 0..1 : N", "start"))

    partes += [s_usuarios, s_susc, s_arboles, s_pagos, s_pedidos, s_eventos, s_intentos]

    ancho = c3 + w + 26
    alto_total = max(y_pagos + h_pagos, y_pedidos + h_pedidos, y_grupo + alto_grupo) + 30
    cuerpo = "\n".join(partes)
    return ancho, alto_total, (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto_total}" viewBox="0 0 {ancho} {alto_total}">'
        f'<rect width="100%" height="100%" fill="#fff"/>{cuerpo}</svg>'
    )


def recortar_png(ruta, alto_final):
    """Deja solo las primeras filas del PNG. Chrome captura la ventana completa,
    que es más alta que el área visible, así que se pide de más y se recorta.
    Basta con conservar las primeras filas: los filtros de PNG solo miran hacia
    arriba, así que no hace falta decodificar los píxeles."""
    datos = Path(ruta).read_bytes()
    pos, trozos = 8, []
    while pos < len(datos):
        largo = struct.unpack(">I", datos[pos:pos + 4])[0]
        tipo = datos[pos + 4:pos + 8]
        trozos.append((tipo, datos[pos + 8:pos + 8 + largo]))
        pos += 12 + largo
    ihdr = trozos[0][1]
    ancho, alto_actual, profundidad, color, _, _, entrelazado = struct.unpack(">IIBBBBB", ihdr)
    if profundidad != 8 or entrelazado or alto_actual <= alto_final:
        return
    canales = {0: 1, 2: 3, 4: 2, 6: 4}[color]
    pixeles = zlib.decompress(b"".join(c for t, c in trozos if t == b"IDAT"))
    pixeles = pixeles[:(ancho * canales + 1) * alto_final]

    def trozo(tipo, contenido):
        return struct.pack(">I", len(contenido)) + tipo + contenido + struct.pack(">I", zlib.crc32(tipo + contenido))

    nuevo_ihdr = struct.pack(">IIBBBBB", ancho, alto_final, profundidad, color, 0, 0, 0)
    Path(ruta).write_bytes(
        datos[:8] + trozo(b"IHDR", nuevo_ihdr) + trozo(b"IDAT", zlib.compress(pixeles, 9)) + trozo(b"IEND", b"")
    )


def buscar_chrome():
    for nombre in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    return None


if __name__ == "__main__":
    ancho, alto_total, contenido = svg(cargar_tablas())
    chrome = buscar_chrome()
    if not chrome:
        destino = RAIZ / "db" / "modelo_datos.svg"
        destino.write_text(contenido, encoding="utf-8")
        print(f"No se encontró Chrome: escrito {destino}")
        sys.exit(0)
    with tempfile.TemporaryDirectory() as carpeta:
        pagina = Path(carpeta) / "diagrama.html"
        pagina.write_text(
            f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;background:#fff}}</style>{contenido}',
            encoding="utf-8",
        )
        destino = RAIZ / "db" / "modelo_datos.png"
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
             f"--window-size={ancho},{alto_total + 200}", f"--screenshot={destino}", pagina.as_uri()],
            check=True, capture_output=True,
        )
        recortar_png(destino, alto_total)
    print(f"Escrito {destino} ({ancho}x{alto_total})")
