"""Reglas de adopción: cupos, cancelación y expulsión.

El usuario sale siempre del token, nunca del cuerpo de la petición, para que
nadie pueda suscribir, cancelar o ver datos ajenos.
"""

from sqlalchemy.orm import Session

from catalogo import buscar_especie
from core import MODO_DESARROLLO, es_cuenta_demo, exigir_mismo_usuario, exigir_que_no_sea_demo
from database import Arbol, Usuario
from errores import Conflicto, NoEncontrado
from notificaciones import enviar_aviso_adopcion_cancelada, enviar_en_segundo_plano
from repositories import arboles as repo_arboles, pedidos as repo_pedidos, suscripciones as repo, transaccion
from seguridad import registrar_evento
from services.arboles import cupos_ocupados_de, especie_de_arbol, serializar as serializar_arbol


def _mensaje_ya_suscrito(arbol: Arbol) -> str:
    return f"Ya estás suscrito a {arbol.nombre}. No puedes ocupar dos cupos del mismo árbol."


def exigir_que_pueda_adoptar(db: Session, usuario: Usuario, arbol: Arbol):
    """Revisa, antes de cobrar, si el usuario puede adoptar el árbol."""
    # Lo demo y lo real no se mezclan: las credenciales demo son públicas, así que
    # cualquiera vería los datos de quien adopte un árbol de la cuenta demo, y el
    # comprador demo ocuparía los cupos de agricultores reales.
    arbol_demo = bool(arbol.productor) and es_cuenta_demo(arbol.productor)
    if arbol_demo and not es_cuenta_demo(usuario):
        raise Conflicto("Este árbol es de demostración y no se puede adoptar con una cuenta real. Elige el árbol de un agricultor real.")
    if es_cuenta_demo(usuario) and not arbol_demo:
        raise Conflicto("La cuenta de demostración solo puede adoptar los árboles de demostración.")

    if repo.de_usuario_y_arbol(db, usuario.id, arbol.id):
        raise Conflicto(_mensaje_ya_suscrito(arbol))
    if cupos_ocupados_de(db, arbol) >= arbol.cupos_totales:
        raise Conflicto("Cupos agotados para este árbol.")


def reservar_cupo(db: Session, usuario: Usuario, arbol: Arbol):
    """Crea la suscripción sin confirmar la transacción: el cupo se reserva en
    la misma transacción que registra el pago aprobado. Si no se puede, deshace
    la transacción y lanza Conflicto. Se llama antes de agregar nada más a la sesión.
    """
    # Un mismo usuario no puede ocupar dos cupos del mismo árbol
    if repo.de_usuario_y_arbol(db, usuario.id, arbol.id):
        raise Conflicto(_mensaje_ya_suscrito(arbol))

    mensaje_ya_suscrito = _mensaje_ya_suscrito(arbol)
    if not repo_arboles.reservar_cupo(db, arbol.id):
        transaccion.deshacer(db)
        raise Conflicto("Cupos agotados para este árbol.")
    if not repo.crear_sin_confirmar(db, usuario.id, arbol.id):
        raise Conflicto(mensaje_ya_suscrito)


def _quitar(db: Session, suscripcion, arbol: Arbol):
    """Sin la suscripción, el despacho de la cosecha de ese árbol ya no aplica.
    El cupo solo se libera si este DELETE fue el que borró la fila: así, dos
    peticiones simultáneas no pueden liberar el mismo cupo dos veces."""
    usuario_id, arbol_id = suscripcion.usuario_id, arbol.id
    repo_pedidos.borrar_despacho_de_arbol(db, usuario_id, arbol_id)
    if repo.borrar(db, suscripcion.id):
        repo_arboles.liberar_cupo(db, arbol_id)


def listar_suscriptores(db: Session, usuario: Usuario, productor_id: int) -> list:
    """Incluye datos de contacto, por eso solo el propio productor puede verla."""
    exigir_mismo_usuario(usuario, productor_id)
    demo = es_cuenta_demo(usuario)

    resultado = []
    total = 0
    for arbol in repo_arboles.de_productor(db, productor_id):
        suscriptores = [
            {
                "suscripcion_id": s.id,
                "usuario_id": s.usuario.id,
                "nombre": s.usuario.nombre,
                "email": s.usuario.email,
                "telefono": s.usuario.telefono,
                "direccion": s.usuario.direccion,
                "rol": s.usuario.rol,
                "fecha_suscripcion": s.fecha_suscripcion.strftime("%d/%m/%Y") if s.fecha_suscripcion else None,
            }
            for s in repo.de_arbol_con_usuario(db, arbol.id)
            # Las credenciales demo son públicas: esa cuenta no ve a personas reales
            if s.usuario and (not demo or es_cuenta_demo(s.usuario))
        ]
        total += len(suscriptores)
        resultado.append({
            "arbol_id": arbol.id,
            "arbol_nombre": arbol.nombre,
            "cupos_totales": arbol.cupos_totales,
            "cupos_ocupados": len(suscriptores),
            "suscriptores": suscriptores,
        })
    # Quién leyó datos de quién: hace falta para reconstruir un incidente
    if total:
        registrar_evento("lectura_datos", "info", usuario=usuario, detalle=f"{total} suscriptores")
    return resultado


def listar_de_usuario(db: Session, usuario: Usuario, usuario_id: int) -> dict:
    """Árboles que un usuario tiene adoptados, para su panel."""
    exigir_mismo_usuario(usuario, usuario_id)

    adoptados = []
    for suscripcion in repo.de_usuario_con_arbol(db, usuario_id):
        arbol = suscripcion.arbol
        if not arbol:
            continue
        adoptados.append({
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
            "cupos_ocupados": cupos_ocupados_de(db, arbol),
            "productor": arbol.productor.nombre if arbol.productor else None,
            "fecha_suscripcion": suscripcion.fecha_suscripcion.strftime("%d/%m/%Y") if suscripcion.fecha_suscripcion else None,
        })
    return {"status": "success", "arboles": adoptados}


def expulsar(db: Session, usuario: Usuario, suscripcion_id: int) -> dict:
    """Solo el productor dueño del árbol puede expulsar suscriptores. A los demás
    se les responde igual que si no existiera, para no revelar qué ids existen."""
    exigir_que_no_sea_demo(usuario, "expulsar suscriptor")

    suscripcion = repo.por_id(db, suscripcion_id)
    if not suscripcion:
        raise NoEncontrado("Suscripción no encontrada.")

    arbol = repo_arboles.por_id(db, suscripcion.arbol_id)
    if not arbol or arbol.productor_id != usuario.id:
        registrar_evento("acceso_denegado", "advertencia", usuario=usuario, detalle=f"expulsar en la suscripción {suscripcion_id}")
        raise NoEncontrado("Suscripción no encontrada.")

    destinatario, nombre_arbol = suscripcion.usuario.email if suscripcion.usuario else None, arbol.nombre
    _quitar(db, suscripcion, arbol)
    transaccion.confirmar(db)
    # Quien pagó debe enterarse de que perdió el cupo
    if destinatario and not MODO_DESARROLLO:
        enviar_en_segundo_plano(enviar_aviso_adopcion_cancelada, destinatario, nombre_arbol)
    return {"status": "success", "mensaje": "Suscriptor expulsado y cupo liberado."}


def cancelar(db: Session, usuario: Usuario, arbol_id: int) -> dict:
    arbol = repo_arboles.por_id(db, arbol_id)
    if not arbol:
        raise NoEncontrado("Árbol no encontrado.")

    # Se busca la suscripción real del usuario: sin esto, cancelar solo
    # bajaba el contador y el usuario seguía suscrito.
    suscripcion = repo.de_usuario_y_arbol(db, usuario.id, arbol.id)
    if not suscripcion:
        raise NoEncontrado("No estás suscrito a este árbol.")

    _quitar(db, suscripcion, arbol)
    transaccion.confirmar(db)
    return {
        "status": "success",
        "mensaje": f"Suscripción cancelada para {usuario.nombre} en {arbol.nombre}.",
        "arbol": serializar_arbol(db, arbol),
    }
