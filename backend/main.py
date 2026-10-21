from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database import (
    engine, SessionLocal, Base, Usuario, Arbol, Suscripcion, Pedido,
    hash_password, verify_password, asegurar_columnas, es_hash_bcrypt,
    migrar_cuentas_antiguas,
)
from catalogo import (
    CATALOGO_ESPECIES, listar_especies, buscar_especie,
    fotos_permitidas, componer_nombre, normalizar_identificador, foto_de,
)

app = FastAPI(
    title="Agro-Colab API",
    description="Adopción de árboles frutales y abastecimiento directo con trazabilidad"
)

# Permitir peticiones desde el frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear tablas y datos iniciales
Base.metadata.create_all(bind=engine)
asegurar_columnas()
migrar_cuentas_antiguas()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def datos_iniciales():
    db = SessionLocal()
    try:
        # Verificar si ya hay datos
        if db.query(Usuario).count() == 0:
            # Crear usuarios de prueba (contraseña hasheada con bcrypt).
            # Van verificados y con los consentimientos aceptados para que
            # sirvan de inmediato en las cuentas de demostración.
            usuarios = [
                Usuario(
                    nombre="Camila Soto", email="comprador@agrocolab.cl",
                    password=hash_password("123"), rol="comprador", verificado=1,
                    consentimiento_datos=1, fecha_consentimiento=datetime.now(),
                    acepta_terminos=1,
                ),
                Usuario(
                    nombre="Hernán Silva", email="agricultor@agrocolab.cl",
                    password=hash_password("123"), rol="agricultor", verificado=1,
                    consentimiento_datos=1, fecha_consentimiento=datetime.now(),
                    acepta_terminos=1,
                )
            ]
            db.add_all(usuarios)
            db.commit()

        if db.query(Arbol).count() == 0:
            # Crear árboles de prueba (con fotos del catálogo de especies)
            arboles = [
                Arbol(
                    nombre="Palto Hass #104",
                    especie="palto_hass",
                    identificador="#104",
                    plan="Básico",
                    tipo_suscripcion="Compartido",
                    precio_mensual_clp=12000,
                    cupos_totales=5,
                    cupos_ocupados=3,
                    estimacion_cosecha="45 kg anuales",
                    ubicacion="Valle del Aconcagua, Región de Valparaíso",
                    imagen=foto_de("palto_hass", 0),
                    imagen_origen="galeria",
                    productor_id=2
                ),
                Arbol(
                    nombre="Naranjo Valencia #22",
                    especie="naranjo_valencia",
                    identificador="#22",
                    plan="Premium",
                    tipo_suscripcion="Exclusivo",
                    precio_mensual_clp=35000,
                    cupos_totales=1,
                    cupos_ocupados=0,
                    estimacion_cosecha="80 kg anuales",
                    ubicacion="Curicó, Región del Maule",
                    imagen=foto_de("naranjo_valencia", 0),
                    imagen_origen="galeria",
                    productor_id=2
                ),
                Arbol(
                    nombre="Limonero Eureka #12",
                    especie="limonero_eureka",
                    identificador="#12",
                    plan="Intermedio",
                    tipo_suscripcion="Compartido",
                    precio_mensual_clp=8000,
                    cupos_totales=3,
                    cupos_ocupados=1,
                    estimacion_cosecha="35 kg anuales",
                    ubicacion="Mallarauco, Región Metropolitana",
                    imagen=foto_de("limonero_eureka", 0),
                    imagen_origen="galeria",
                    productor_id=2
                )
            ]
            db.add_all(arboles)
            db.commit()
    finally:
        db.close()

datos_iniciales()

# ----------------- MODELOS DE DATOS (ESQUEMAS) -----------------

class SuscripcionRequest(BaseModel):
    user_name: str
    tree_id: int

class LoginRequest(BaseModel):
    email: str
    password: str
    rol: str

class PedidoRequest(BaseModel):
    plan_nombre: str
    monto_clp: int
    cliente_nombre: str
    telefono: str
    email: str
    tipo_destino: str  # "particular" o "comercial"
    razon_social: Optional[str] = None
    rut: Optional[str] = None
    direccion: str
    comuna: str
    frecuencia_entrega: str

class ArbolRequest(BaseModel):
    nombre: Optional[str] = None  # se compone desde especie + identificador
    especie: str
    identificador: Optional[str] = None
    ubicacion: str
    plan: str
    tipo_suscripcion: str
    cupos_totales: int
    precio_mensual_clp: int
    estimacion_cosecha: str
    imagen: str
    productor: str


# ----------------- VALIDACION DE ESPECIE E IMAGEN -----------------

def validar_imagen(imagen: str, especie_id: str):
    """Revisa la imagen enviada por el agricultor.

    El catálogo curado es la única fuente de imágenes: así el comprador nunca ve
    una foto que no corresponda al árbol que está adoptando. La validación se
    hace en el servidor, no solo en el formulario.

    Devuelve (imagen, origen, error).
    """
    if not imagen or not imagen.strip():
        return None, None, "Debes elegir una imagen del árbol."

    valor = imagen.strip()

    if valor.startswith("data:"):
        return None, None, "Por ahora las fotos deben elegirse del catálogo de la especie."

    if valor in fotos_permitidas(especie_id):
        return valor, "galeria", None

    return None, None, "La imagen elegida no corresponde a la especie seleccionada."


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


def serializar_arbol(arbol) -> dict:
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
        "cupos_ocupados": arbol.cupos_ocupados,
        "estimacion_cosecha": arbol.estimacion_cosecha,
        "ubicacion": arbol.ubicacion,
        "imagen": arbol.imagen,
        "imagen_origen": arbol.imagen_origen or "galeria",
        "productor": arbol.productor.nombre if arbol.productor else None,
    }

class PerfilRequest(BaseModel):
    nombre: str
    email: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    password: Optional[str] = None

# ----------------- ENDPOINTS (RUTAS) -----------------

# 1. Rutas de Árboles
@app.get("/api/especies")
def listar_catalogo_especies():
    """Catálogo cerrado de especies con las fotos que el agricultor puede usar."""
    return listar_especies()


@app.get("/api/arboles")
def listar_arboles(db: SessionLocal = Depends(get_db)):
    arboles = db.query(Arbol).all()
    return [serializar_arbol(a) for a in arboles]


@app.post("/api/arboles")
def crear_arbol(data: ArbolRequest, db: SessionLocal = Depends(get_db)):
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
        "arbol": serializar_arbol(nuevo_arbol)
    }

@app.post("/api/suscribir")
def suscribir(data: SuscripcionRequest, db: SessionLocal = Depends(get_db)):
    arbol = db.query(Arbol).filter(Arbol.id == data.tree_id).first()
    if not arbol:
        return {"status": "error", "mensaje": "Árbol no encontrado."}

    if arbol.cupos_ocupados < arbol.cupos_totales:
        # Buscar el usuario real por su nombre
        usuario = db.query(Usuario).filter(Usuario.nombre == data.user_name).first()
        if not usuario:
            return {"status": "error", "mensaje": "Usuario no encontrado."}

        arbol.cupos_ocupados += 1

        # Crear registro de suscripción con el usuario real
        suscripcion = Suscripcion(usuario_id=usuario.id, arbol_id=data.tree_id)
        db.add(suscripcion)
        db.commit()

        return {
            "status": "success",
            "mensaje": f"¡Suscripción confirmada para {data.user_name} en {arbol.nombre}!",
            "arbol": serializar_arbol(arbol)
        }
    return {"status": "error", "mensaje": "Cupos agotados para este árbol."}

# 6. Gestión de suscriptores (para el agricultor)
@app.get("/api/mis-arboles/{productor_id}/suscriptores")
def listar_suscriptores(productor_id: int, db: SessionLocal = Depends(get_db)):
    """Lista los usuarios suscritos a los árboles de un productor."""
    arboles = db.query(Arbol).filter(Arbol.productor_id == productor_id).all()

    resultado = []
    for arbol in arboles:
        suscripciones = db.query(Suscripcion).filter(Suscripcion.arbol_id == arbol.id).all()
        suscriptores = []
        for s in suscripciones:
            u = db.query(Usuario).filter(Usuario.id == s.usuario_id).first()
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
            "cupos_ocupados": arbol.cupos_ocupados,
            "suscriptores": suscriptores
        })

    return resultado

@app.delete("/api/suscripciones/{suscripcion_id}")
def expulsar_suscriptor(suscripcion_id: int, db: SessionLocal = Depends(get_db)):
    """Expulsa a un suscriptor de un árbol y libera su cupo."""
    suscripcion = db.query(Suscripcion).filter(Suscripcion.id == suscripcion_id).first()
    if not suscripcion:
        return {"status": "error", "mensaje": "Suscripción no encontrada."}

    arbol = db.query(Arbol).filter(Arbol.id == suscripcion.arbol_id).first()

    db.delete(suscripcion)
    if arbol and arbol.cupos_ocupados > 0:
        arbol.cupos_ocupados -= 1
    db.commit()

    return {"status": "success", "mensaje": "Suscriptor expulsado y cupo liberado."}

@app.get("/api/usuario/{usuario_id}")
def obtener_usuario(usuario_id: int, db: SessionLocal = Depends(get_db)):
    """Obtiene el perfil público de un usuario (para que el agricultor lo vea)."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}

    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "telefono": usuario.telefono,
        "direccion": usuario.direccion,
        "rol": usuario.rol,
        "verificado": usuario.verificado
    }

@app.put("/api/arboles/{arbol_id}")
def actualizar_arbol(arbol_id: int, data: ArbolRequest, db: SessionLocal = Depends(get_db)):
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
        "arbol": serializar_arbol(arbol)
    }

@app.delete("/api/arboles/{arbol_id}")
def eliminar_arbol(arbol_id: int, db: SessionLocal = Depends(get_db)):
    arbol = db.query(Arbol).filter(Arbol.id == arbol_id).first()
    if not arbol:
        return {"status": "error", "mensaje": "Árbol no encontrado."}

    db.delete(arbol)
    db.commit()
    return {"status": "success", "mensaje": f"Árbol '{arbol.nombre}' eliminado correctamente."}

@app.post("/api/cancelar-suscripcion")
def cancelar_suscripcion(data: SuscripcionRequest, db: SessionLocal = Depends(get_db)):
    arbol = db.query(Arbol).filter(Arbol.id == data.tree_id).first()
    if not arbol:
        return {"status": "error", "mensaje": "Árbol no encontrado."}

    if arbol.cupos_ocupados > 0:
        arbol.cupos_ocupados -= 1
        db.commit()

        return {
            "status": "success",
            "mensaje": f"Suscripción cancelada para {data.user_name} en {arbol.nombre}.",
            "arbol": serializar_arbol(arbol)
        }
    return {"status": "error", "mensaje": "No hay suscriptores que cancelar."}

# 2. Rutas de Autenticación (Login y Registro)
class RegistroRequest(BaseModel):
    nombre: str
    email: str
    password: str
    rol: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None

import random
import string

@app.post("/api/register")
def registrar_usuario(data: RegistroRequest, db: SessionLocal = Depends(get_db)):
    # Verificar si el email ya existe
    existente = db.query(Usuario).filter(Usuario.email == data.email).first()
    if existente:
        return {"status": "error", "mensaje": "El correo electrónico ya está registrado."}

    # Generar código de verificación de 6 dígitos
    codigo = ''.join(random.choices(string.digits, k=6))

    nuevo_usuario = Usuario(
        nombre=data.nombre,
        email=data.email,
        password=hash_password(data.password),
        rol=data.rol,
        telefono=data.telefono,
        direccion=data.direccion,
        verificado=0,
        codigo_verificacion=codigo,
        consentimiento_datos=1,
        fecha_consentimiento=datetime.now(),
        acepta_terminos=1
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    # Simular envío de correo (en producción, usar un servicio como SendGrid, Mailgun, etc.)
    print(f"\n{'='*50}")
    print(f"CORREO DE VERIFICACIÓN ENVIADO A: {data.email}")
    print(f"Código de verificación: {codigo}")
    print(f"{'='*50}\n")

    return {
        "status": "success",
        "mensaje": f"Usuario {nuevo_usuario.nombre} registrado correctamente. Revisa tu correo para verificar tu cuenta.",
        "user": {
            "id": nuevo_usuario.id,
            "nombre": nuevo_usuario.nombre,
            "email": nuevo_usuario.email,
            "rol": nuevo_usuario.rol
        },
        "codigo_verificacion": codigo  # En producción, esto NO se retornaría
    }

class VerificacionRequest(BaseModel):
    email: str
    codigo: str

@app.get("/api/admin/reiniciar-bd")
def reiniciar_bd():
    """Reinicia la base de datos con los datos iniciales (para desarrollo)"""
    db = SessionLocal()
    try:
        # Eliminar datos existentes
        db.query(Suscripcion).delete()
        db.query(Pedido).delete()
        db.query(Arbol).delete()
        db.query(Usuario).delete()
        db.commit()

        # Crear usuarios de prueba con contraseñas hasheadas
        usuarios = [
            Usuario(nombre="Camila Soto", email="comprador@agrocolab.cl", password=hash_password("123"), rol="comprador", verificado=1, consentimiento_datos=1, fecha_consentimiento=datetime.now(), acepta_terminos=1),
            Usuario(nombre="Hernán Silva", email="agricultor@agrocolab.cl", password=hash_password("123"), rol="agricultor", verificado=1, consentimiento_datos=1, fecha_consentimiento=datetime.now(), acepta_terminos=1)
        ]
        db.add_all(usuarios)
        db.commit()

        # Crear árboles de prueba
        arboles = [
            Arbol(nombre="Palto Hass #104", especie="palto_hass", identificador="#104", plan="Básico", tipo_suscripcion="Compartido", precio_mensual_clp=12000, cupos_totales=5, cupos_ocupados=3, estimacion_cosecha="45 kg anuales", ubicacion="Valle del Aconcagua, Región de Valparaíso", imagen=foto_de("palto_hass", 0), imagen_origen="galeria", productor_id=2),
            Arbol(nombre="Naranjo Valencia #22", especie="naranjo_valencia", identificador="#22", plan="Premium", tipo_suscripcion="Exclusivo", precio_mensual_clp=35000, cupos_totales=1, cupos_ocupados=0, estimacion_cosecha="80 kg anuales", ubicacion="Curicó, Región del Maule", imagen=foto_de("naranjo_valencia", 0), imagen_origen="galeria", productor_id=2),
            Arbol(nombre="Limonero Eureka #12", especie="limonero_eureka", identificador="#12", plan="Intermedio", tipo_suscripcion="Compartido", precio_mensual_clp=8000, cupos_totales=3, cupos_ocupados=1, estimacion_cosecha="35 kg anuales", ubicacion="Mallarauco, Región Metropolitana", imagen=foto_de("limonero_eureka", 0), imagen_origen="galeria", productor_id=2)
        ]
        db.add_all(arboles)
        db.commit()

        # Crear suscripciones de prueba (comprador -> árboles)
        comprador = db.query(Usuario).filter(Usuario.email == "comprador@agrocolab.cl").first()
        if comprador:
            suscripciones = [
                Suscripcion(usuario_id=comprador.id, arbol_id=1),  # Palto Hass
                Suscripcion(usuario_id=comprador.id, arbol_id=3)   # Limonero
            ]
            db.add_all(suscripciones)
            db.commit()

        return {"status": "success", "mensaje": "Base de datos reiniciada correctamente."}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}
    finally:
        db.close()

@app.post("/api/verificar-cuenta")
def verificar_cuenta(data: VerificacionRequest, db: SessionLocal = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}

    if usuario.verificado:
        return {"status": "error", "mensaje": "La cuenta ya está verificada."}

    if usuario.codigo_verificacion != data.codigo:
        return {"status": "error", "mensaje": "Código de verificación incorrecto."}

    usuario.verificado = 1
    usuario.codigo_verificacion = None
    db.commit()

    return {
        "status": "success",
        "mensaje": "Cuenta verificada correctamente. Ya puedes iniciar sesión."
    }

@app.post("/api/login")
def login(data: LoginRequest, db: SessionLocal = Depends(get_db)):
    usuario = db.query(Usuario).filter(
        Usuario.email == data.email,
        Usuario.rol == data.rol
    ).first()

    if not usuario or not verify_password(data.password, usuario.password):
        return {
            "status": "error",
            "mensaje": "Credenciales inválidas o el rol seleccionado no coincide."
        }

    # La cuenta todavía guardaba la contraseña en texto plano: se re-hashea
    # en el primer inicio de sesión correcto.
    if not es_hash_bcrypt(usuario.password):
        usuario.password = hash_password(usuario.password)
        db.commit()
        db.refresh(usuario)
        print(f"[migracion] contrasena re-hasheada para {usuario.email}")

    return {
        "status": "success",
        "mensaje": f"Bienvenido/a {usuario.nombre}",
        "user": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol,
            "verificado": usuario.verificado,
            "codigo_verificacion": usuario.codigo_verificacion
        }
    }

# 5. Rutas de Derechos de Usuarios (Ley 21.719)
@app.delete("/api/usuario/{email}")
def eliminar_usuario(email: str, db: SessionLocal = Depends(get_db)):
    """Derecho a la eliminación de datos (Art. 20 Ley 21.719)"""
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}

    # Eliminar suscripciones del usuario
    db.query(Suscripcion).filter(Suscripcion.usuario_id == usuario.id).delete()

    # Eliminar pedidos del usuario
    db.query(Pedido).filter(Pedido.cliente_id == usuario.id).delete()

    # Eliminar árbolos publicados por el usuario (si es agricultor)
    db.query(Arbol).filter(Arbol.productor_id == usuario.id).delete()

    # Finalmente eliminar el usuario
    db.delete(usuario)
    db.commit()

    return {
        "status": "success",
        "mensaje": "Todos tus datos han sido eliminados correctamente."
    }

# 3. Rutas de Logística y Pedidos
@app.post("/api/pedidos")
def registrar_pedido(pedido: PedidoRequest, db: SessionLocal = Depends(get_db)):
    nuevo_pedido = Pedido(
        cliente_id=1,  # temporal
        plan_nombre=pedido.plan_nombre,
        monto_clp=pedido.monto_clp,
        tipo_destino=pedido.tipo_destino,
        razon_social=pedido.razon_social,
        rut=pedido.rut,
        direccion=pedido.direccion,
        comuna=pedido.comuna,
        frecuencia_entrega=pedido.frecuencia_entrega,
        codigo_seguimiento=f"AGRO-{db.query(Pedido).count() + 1:04d}",
        estado_logistica="En coordinación con huerto de origen"
    )
    db.add(nuevo_pedido)
    db.commit()
    db.refresh(nuevo_pedido)

    return {
        "status": "success",
        "mensaje": f"Plan contratado con éxito. Código de despacho: {nuevo_pedido.codigo_seguimiento}",
        "pedido": {
            "id": nuevo_pedido.id,
            "plan_nombre": nuevo_pedido.plan_nombre,
            "monto_clp": nuevo_pedido.monto_clp,
            "tipo_destino": nuevo_pedido.tipo_destino,
            "direccion": nuevo_pedido.direccion,
            "comuna": nuevo_pedido.comuna,
            "frecuencia_entrega": nuevo_pedido.frecuencia_entrega,
            "codigo_seguimiento": nuevo_pedido.codigo_seguimiento,
            "fecha_registro": nuevo_pedido.fecha_registro.strftime("%d/%m/%Y %H:%M"),
            "estado_logistica": nuevo_pedido.estado_logistica
        }
    }

@app.get("/api/pedidos")
def listar_pedidos(db: SessionLocal = Depends(get_db)):
    pedidos = db.query(Pedido).all()
    return [
        {
            "id": p.id,
            "plan_nombre": p.plan_nombre,
            "monto_clp": p.monto_clp,
            "tipo_destino": p.tipo_destino,
            "direccion": p.direccion,
            "comuna": p.comuna,
            "frecuencia_entrega": p.frecuencia_entrega,
            "codigo_seguimiento": p.codigo_seguimiento,
            "fecha_registro": p.fecha_registro.strftime("%d/%m/%Y %H:%M"),
            "estado_logistica": p.estado_logistica
        }
        for p in pedidos
    ]

# 4. Rutas de Perfil de Usuario
@app.put("/api/perfil")
def actualizar_perfil(data: PerfilRequest, db: SessionLocal = Depends(get_db)):
    cambios = data.dict(exclude_unset=True)

    # Buscar usuario por email
    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
    if not usuario:
        return {"status": "error", "mensaje": "Usuario no encontrado."}

    # Actualizar campos
    if "nombre" in cambios:
        usuario.nombre = cambios["nombre"]
    if "telefono" in cambios:
        usuario.telefono = cambios["telefono"]
    if "direccion" in cambios:
        usuario.direccion = cambios["direccion"]
    if "password" in cambios and cambios["password"]:
        usuario.password = cambios["password"]

    db.commit()
    db.refresh(usuario)

    return {
        "status": "success",
        "mensaje": "Perfil actualizado correctamente.",
        "user": {
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol,
            "telefono": usuario.telefono,
            "direccion": usuario.direccion
        }
    }
