"""Reglas de publicación y gestión de árboles."""

from typing import Optional

from sqlalchemy.orm import Session

from catalogo import CATALOGO_ESPECIES, buscar_especie, componer_nombre, fotos_permitidas, normalizar_identificador
from core import es_cuenta_demo, exigir_que_no_sea_demo, limitar
from database import Arbol, Usuario
from errores import Conflicto, DatoInvalido, NoEncontrado, Prohibido
from repositories import arboles as repo, suscripciones as repo_suscripciones, transaccion
from schemas import ArbolRequest
from seguridad import registrar_evento


# Lo que cada plan promete en los términos: cuántas personas comparten el árbol
REGLAS_DE_PLAN = {
    "Básico": (5, "Compartido"),
    "Intermedio": (3, "Compartido"),
    "Premium": (1, "Exclusivo"),
}
# Lo que el comprador pagó: no cambia mientras el árbol tenga suscriptores
CAMPOS_CONGELADOS = ("especie", "plan", "tipo_suscripcion", "cupos_totales", "precio_mensual_clp", "estimacion_cosecha")
PUBLICACIONES_POR_HORA = 20
MAX_ARBOLES_POR_PRODUCTOR = 100


def texto_cosecha(kilos: int) -> str:
    """Texto que se guarda y se muestra para la cosecha estimada."""
    return f"{kilos:,}".replace(",", ".") + " kg anuales"


def validar_imagen(imagen: str, especie_id: str) -> tuple:
    """Revisa la imagen enviada por el agricultor. Devuelve (imagen, origen).

    El catálogo curado es la única fuente de imágenes: así el comprador nunca ve
    una foto que no corresponda al árbol que está adoptando. La validación se
    hace en el servidor, no solo en el formulario.
    """
    if not imagen or not imagen.strip():
        raise DatoInvalido("Debes elegir una imagen del árbol.")
    valor = imagen.strip()
    if valor.startswith("data:"):
        raise DatoInvalido("Por ahora las fotos deben elegirse del catálogo de la especie.")
    if valor in fotos_permitidas(especie_id):
        return valor, "galeria"
    raise DatoInvalido("La imagen elegida no corresponde a la especie seleccionada.")


def especie_de_arbol(arbol) -> Optional[str]:
    """Especie de un árbol. Los árboles antiguos se deducen del nombre."""
    if arbol.especie:
        return arbol.especie
    nombre = (arbol.nombre or "").lower()
    for especie in CATALOGO_ESPECIES:
        if nombre.startswith(especie["nombre"].lower()):
            return especie["id"]
    return None


def identificador_de_arbol(arbol) -> Optional[str]:
    """Identificador del árbol dentro del huerto (ej: '#104')."""
    if arbol.identificador:
        return arbol.identificador
    especie = buscar_especie(especie_de_arbol(arbol))
    if not especie:
        return None
    nombre = arbol.nombre or ""
    return nombre[len(especie["nombre"]):].strip() or None


def cupos_ocupados_de(db: Session, arbol: Arbol) -> int:
    """Cupos realmente ocupados: cuenta las suscripciones registradas.

    El contador guardado se puede desincronizar, y ahí el panel del agricultor
    anuncia suscriptores que no existen. La fuente de verdad son las filas de
    la tabla suscripciones.
    """
    return repo_suscripciones.contar_de_arbol(db, arbol.id)


def serializar(db: Session, arbol: Arbol, ocupados: Optional[int] = None) -> dict:
    """Representación uniforme de un árbol para la API."""
    especie_id = especie_de_arbol(arbol)
    especie = buscar_especie(especie_id)
    return {
        "id": arbol.id,
        "nombre": arbol.nombre,
        "especie": especie_id,
        "especie_nombre": especie["nombre"] if especie else None,
        "identificador": identificador_de_arbol(arbol),
        "plan": arbol.plan,
        "tipo_suscripcion": arbol.tipo_suscripcion,
        "precio_mensual_clp": arbol.precio_mensual_clp,
        "cupos_totales": arbol.cupos_totales,
        "cupos_ocupados": cupos_ocupados_de(db, arbol) if ocupados is None else ocupados,
        "estimacion_cosecha": arbol.estimacion_cosecha,
        "ubicacion": arbol.ubicacion,
        "imagen": arbol.imagen,
        "imagen_origen": arbol.imagen_origen or "galeria",
        "productor": arbol.productor.nombre if arbol.productor else None,
        "productor_id": arbol.productor_id,
        "es_demo": bool(arbol.productor) and es_cuenta_demo(arbol.productor),
    }


def _datos_validados(data: ArbolRequest) -> dict:
    """Valida especie e imagen, y devuelve los campos comunes de crear y editar."""
    if not buscar_especie(data.especie):
        raise DatoInvalido("La especie seleccionada no está en el catálogo.")
    cupos, tipo = REGLAS_DE_PLAN[data.plan]
    if data.cupos_totales != cupos or data.tipo_suscripcion != tipo:
        raise DatoInvalido(f"El plan {data.plan} es {tipo.lower()} y tiene {cupos} cupo{'s' if cupos != 1 else ''}.")
    imagen, origen = validar_imagen(data.imagen, data.especie)
    return {
        "nombre": componer_nombre(data.especie, data.identificador),
        "especie": data.especie,
        "identificador": normalizar_identificador(data.identificador) or None,
        "ubicacion": data.ubicacion,
        "plan": data.plan,
        "tipo_suscripcion": data.tipo_suscripcion,
        "cupos_totales": data.cupos_totales,
        "precio_mensual_clp": data.precio_mensual_clp,
        "estimacion_cosecha": texto_cosecha(data.estimacion_cosecha_kg),
        "imagen": imagen,
        "imagen_origen": origen,
    }


def _propio(db: Session, arbol_id: int, usuario: Usuario) -> Arbol:
    """Solo el productor que publicó el árbol puede gestionarlo."""
    arbol = repo.por_id(db, arbol_id)
    if not arbol:
        raise NoEncontrado("Árbol no encontrado.")
    if arbol.productor_id != usuario.id:
        registrar_evento("acceso_denegado", "advertencia", usuario=usuario, detalle=f"árbol {arbol_id} de otro productor")
        raise Prohibido("Solo el productor del árbol puede modificarlo.")
    return arbol


def listar(db: Session) -> list:
    arboles = repo.listar(db)
    ocupados = repo_suscripciones.contar_por_arbol(db, [a.id for a in arboles])
    return [serializar(db, a, ocupados.get(a.id, 0)) for a in arboles]


def obtener(db: Session, arbol_id: int) -> dict:
    arbol = repo.por_id(db, arbol_id)
    if not arbol:
        raise NoEncontrado("Árbol no encontrado.")
    return serializar(db, arbol)


def crear(db: Session, productor: Usuario, data: ArbolRequest) -> dict:
    # El productor es el usuario de la sesión. Antes se buscaba por el nombre
    # enviado en el formulario, y cualquiera podía publicar a nombre de otro.
    if productor.rol != "agricultor":
        registrar_evento("acceso_denegado", "advertencia", usuario=productor, detalle="publicar árbol sin ser agricultor")
        raise Prohibido("Solo los agricultores pueden publicar árboles.")
    exigir_que_no_sea_demo(productor, "publicar árbol")
    limitar(f"publicar:{productor.id}", PUBLICACIONES_POR_HORA, 3600)
    if repo.contar_de_productor(db, productor.id) >= MAX_ARBOLES_POR_PRODUCTOR:
        raise Conflicto(f"Alcanzaste el máximo de {MAX_ARBOLES_POR_PRODUCTOR} árboles publicados.")

    arbol = repo.crear(db, cupos_ocupados=0, productor_id=productor.id, **_datos_validados(data))
    transaccion.confirmar(db)
    transaccion.recargar(db, arbol)
    return {
        "status": "success",
        "mensaje": f"Árbol '{arbol.nombre}' publicado correctamente.",
        "arbol": serializar(db, arbol),
    }


def actualizar(db: Session, usuario: Usuario, arbol_id: int, data: ArbolRequest) -> dict:
    arbol = _propio(db, arbol_id, usuario)
    exigir_que_no_sea_demo(usuario, f"editar árbol {arbol_id}")
    datos = _datos_validados(data)

    # Quien adoptó pagó por este árbol: especie, plan, cupos, precio y cosecha
    # estimada no cambian mientras tenga suscriptores
    ocupados = cupos_ocupados_de(db, arbol)
    if ocupados and any(getattr(arbol, campo) != datos[campo] for campo in CAMPOS_CONGELADOS):
        raise Conflicto(
            f"El árbol ya tiene {ocupados} suscriptor{'es' if ocupados != 1 else ''}: "
            "no puedes cambiar su especie, plan, cupos, precio ni cosecha estimada."
        )

    for campo, valor in datos.items():
        setattr(arbol, campo, valor)
    transaccion.confirmar(db)
    transaccion.recargar(db, arbol)
    return {
        "status": "success",
        "mensaje": f"Árbol '{arbol.nombre}' actualizado correctamente.",
        "arbol": serializar(db, arbol),
    }


def eliminar(db: Session, usuario: Usuario, arbol_id: int) -> dict:
    arbol = _propio(db, arbol_id, usuario)
    # Las credenciales demo son públicas: borrar los árboles dejaría la demo
    # vacía para todos
    if es_cuenta_demo(usuario):
        registrar_evento("cuenta_demo", "advertencia", usuario=usuario, detalle=f"eliminar árbol {arbol_id}")
        raise Prohibido("La cuenta de demostración no puede eliminar árboles.")

    # Quien adoptó perdería lo que pagó sin enterarse: expulsar le avisa por correo
    if cupos_ocupados_de(db, arbol):
        raise Conflicto("El árbol tiene suscriptores activos. Expúlsalos antes de eliminarlo: se les avisa por correo.")

    nombre = arbol.nombre
    repo.eliminar_con_dependencias(db, arbol)
    transaccion.confirmar(db)
    return {"status": "success", "mensaje": f"Árbol '{nombre}' eliminado correctamente."}
