from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Float, Boolean, Text, UniqueConstraint, inspect, text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import bcrypt
import os
import hmac

def url_base_datos() -> str:
    """Base de datos a usar, en este orden:

    1. AGROCOLAB_DB_URL: la fijan las pruebas (backend/tests) para usar una
       base temporal.
    2. DATABASE_URL: PostgreSQL en producción (Render, Neon, Supabase...).
       Los datos sobreviven a los despliegues y reinicios del servidor;
       con SQLite en Render se perdían en cada despliegue.
    3. SQLite local (agrocolab.db) para desarrollar sin instalar nada.
    """
    url = os.getenv("AGROCOLAB_DB_URL") or os.getenv("DATABASE_URL") or "sqlite:///./agrocolab.db"
    # Los proveedores entregan "postgres://" o "postgresql://"; SQLAlchemy
    # necesita que se indique el controlador (psycopg 3)
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


SQLALCHEMY_DATABASE_URL = url_base_datos()
ES_SQLITE = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # check_same_thread solo existe en SQLite
    connect_args={"check_same_thread": False} if ES_SQLITE else {},
    # Descarta conexiones cortadas por el proveedor (las bases gratuitas
    # cierran las conexiones inactivas)
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Cuentas de demostración que el README documenta como cuentas de prueba
CUENTAS_DEMO = ("comprador@agrocolab.cl", "agricultor@agrocolab.cl")

def hash_password(password: str) -> str:
    """Hash de contraseña usando bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verificar contraseña contra hash bcrypt.

    Las bases de datos creadas antes del cambio a bcrypt guardaban la contraseña
    en texto plano. Para esos casos se compara directamente (y el login se
    encarga de re-hashear el dato), en vez de terminar en un error 500.
    """
    if not hashed:
        return False

    if not es_hash_bcrypt(hashed):
        return hmac.compare_digest(password, hashed)

    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except (ValueError, TypeError):
        return False

def es_hash_bcrypt(valor: str) -> bool:
    """True si el valor es un hash bcrypt válido."""
    return bool(valor) and valor.startswith(("$2a$", "$2b$", "$2y$"))

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String) # En un entorno real, esto debe ser un hash
    rol = Column(String) # "comprador" o "agricultor"
    telefono = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    verificado = Column(Integer, default=0) # 0 = no verificado, 1 = verificado
    codigo_verificacion = Column(String, nullable=True)
    codigo_expira = Column(DateTime, nullable=True)  # el código vale 30 minutos
    # Recuperación de contraseña: se guarda el hash del código (no el código),
    # su vencimiento y los intentos fallidos
    recuperacion_hash = Column(String, nullable=True)
    recuperacion_expira = Column(DateTime, nullable=True)
    recuperacion_intentos = Column(Integer, default=0)
    consentimiento_datos = Column(Integer, default=0) # 0 = no aceptado, 1 = aceptado
    fecha_consentimiento = Column(DateTime, nullable=True)
    acepta_terminos = Column(Integer, default=0) # 0 = no aceptado, 1 = aceptado
    politica_privacidad = Column(Text, nullable=True) # Versión de política aceptada

    # Relaciones
    arboles_publicados = relationship("Arbol", back_populates="productor")
    suscripciones = relationship("Suscripcion", back_populates="usuario")
    pedidos = relationship("Pedido", back_populates="cliente")

class Arbol(Base):
    __tablename__ = "arboles"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    ubicacion = Column(String)
    plan = Column(String)
    tipo_suscripcion = Column(String)
    cupos_totales = Column(Integer)
    cupos_ocupados = Column(Integer, default=0)
    precio_mensual_clp = Column(Integer)
    estimacion_cosecha = Column(String)
    imagen = Column(String)

    # Especie del catalogo (id) e identificador opcional del árbol en el huerto.
    # Together con "nombre" permiten saber de qué fruta es el árbol publicado.
    especie = Column(String, nullable=True)
    identificador = Column(String, nullable=True)
    # "galeria" = foto curada del catalogo | "propia" = foto subida por el agricultor
    imagen_origen = Column(String, nullable=True, default="galeria")

    productor_id = Column(Integer, ForeignKey("usuarios.id"))
    productor = relationship("Usuario", back_populates="arboles_publicados")
    suscriptores = relationship("Suscripcion", back_populates="arbol")

class Suscripcion(Base):
    __tablename__ = "suscripciones"
    # Un usuario no puede ocupar dos cupos del mismo árbol (lo garantiza la base,
    # no solo la validación previa, que no protege ante peticiones simultáneas)
    __table_args__ = (UniqueConstraint("usuario_id", "arbol_id", name="uq_suscripcion_usuario_arbol"),)

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    arbol_id = Column(Integer, ForeignKey("arboles.id"))
    fecha_suscripcion = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="suscripciones")
    arbol = relationship("Arbol", back_populates="suscriptores")

class EventoSeguridad(Base):
    """Registro de eventos de seguridad (auditoría y monitoreo).

    Se conservan 30 días (Ley 21.719: los datos se guardan solo el tiempo
    necesario para su finalidad, que aquí es detectar ataques).
    """
    __tablename__ = "eventos_seguridad"

    id = Column(Integer, primary_key=True)
    momento = Column(DateTime, default=datetime.utcnow, index=True)
    tipo = Column(String, index=True)
    severidad = Column(String)  # "info", "advertencia" o "critica"
    ip = Column(String, index=True, nullable=True)
    usuario_id = Column(Integer, nullable=True)
    email = Column(String, nullable=True)
    ruta = Column(String, nullable=True)
    detalle = Column(String, nullable=True)


class IntentoAcceso(Base):
    """Intentos registrados por el rate limiting (login, registro, verificación).

    Se guardan en la base y no en memoria: así sobreviven a un reinicio del
    proceso y valen para todos los procesos del servidor.
    """
    __tablename__ = "intentos_acceso"

    id = Column(Integer, primary_key=True)
    clave = Column(String, index=True)
    momento = Column(Float, index=True)  # time.time()


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"))
    plan_nombre = Column(String)
    monto_clp = Column(Integer)
    tipo_destino = Column(String) # "particular" o "comercial"
    razon_social = Column(String, nullable=True)
    rut = Column(String, nullable=True)
    direccion = Column(String)
    comuna = Column(String)
    frecuencia_entrega = Column(String)
    codigo_seguimiento = Column(String, unique=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    estado_logistica = Column(String)
    # "abastecimiento" = plan de canastas | "arbol" = despacho de la cosecha
    # de un árbol adoptado (arbol_id). Sin esto el panel no podía distinguirlos.
    tipo = Column(String, default="abastecimiento")
    arbol_id = Column(Integer, ForeignKey("arboles.id"), nullable=True)

    cliente = relationship("Usuario", back_populates="pedidos")


class Pago(Base):
    """Pago de la pasarela simulada.

    De la tarjeta solo se guardan la marca y los últimos 4 dígitos: el número
    completo y el CVV nunca se almacenan ni se registran. arbol_id y pedido_id
    no son claves foráneas para que el comprobante sobreviva si el agricultor
    elimina el árbol; concepto guarda el nombre tal como se pagó.
    """
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), index=True)
    tipo = Column(String)  # "arbol" (adopción) o "plan" (abastecimiento)
    arbol_id = Column(Integer, nullable=True)
    plan_nombre = Column(String, nullable=True)
    concepto = Column(String)
    monto_clp = Column(Integer)
    estado = Column(String)  # "aprobado" o "rechazado"
    motivo_rechazo = Column(String, nullable=True)
    marca = Column(String)
    ultimos4 = Column(String)
    codigo_autorizacion = Column(String, nullable=True)
    transaccion = Column(String, unique=True)
    pedido_id = Column(Integer, nullable=True)  # plan: pedido que usó el pago
    fecha = Column(DateTime, default=datetime.utcnow)


# ----------------- MIGRACIONES LIGERAS -----------------
# create_all() no modifica las tablas que ya existen en la base, por eso
# se comparan los modelos con el esquema real y se completan las columnas faltantes.

def asegurar_columnas():
    """Agrega a las tablas existentes las columnas que los modelos necesitan."""
    inspector = inspect(engine)
    tablas_existentes = inspector.get_table_names()

    for nombre_tabla, tabla in Base.metadata.tables.items():
        if nombre_tabla not in tablas_existentes:
            continue

        existentes = {col["name"] for col in inspector.get_columns(nombre_tabla)}

        for columna in tabla.columns:
            if columna.name in existentes:
                continue

            tipo = columna.type.compile(dialect=engine.dialect)
            default = ""
            valor_default = getattr(columna.default, "arg", None)
            if valor_default is not None and not callable(valor_default):
                default = f" DEFAULT {valor_default!r}"

            with engine.begin() as conexion:
                conexion.execute(
                    text(f"ALTER TABLE {nombre_tabla} ADD COLUMN {columna.name} {tipo}{default}")
                )
            print(f"[migracion] columna '{columna.name}' agregada a '{nombre_tabla}'")


def migrar_cuentas_antiguas():
    """Repara las cuentas y los árboles que quedaron con datos de versiones anteriores.

    - Contraseñas en texto plano -> se re-hashean con bcrypt.
      Sin esto, bcrypt.checkpw() lanza 'Invalid salt' y el login responde 500.
    - Cuentas de demostración sin verificar -> se verifican, para que las
      cuentas de ejemplo funcionen apenas se crea la base.
    - Contadores de cupos que no cuadran con las suscripciones reales -> se
      recalculan. Con un contador inflado, el panel del agricultor anuncia
      suscriptores que no existen.
    """
    db = SessionLocal()
    try:
        for usuario in db.query(Usuario).all():
            if usuario.password and not es_hash_bcrypt(usuario.password):
                usuario.password = hash_password(usuario.password)
                print(f"[migracion] contrasena re-hasheada para {usuario.email}")

            if usuario.email in CUENTAS_DEMO and not usuario.verificado:
                usuario.verificado = 1
                usuario.codigo_verificacion = None
                print(f"[migracion] cuenta de demostracion verificada: {usuario.email}")

        # Un usuario no puede tener dos suscripciones al mismo árbol: se
        # conserva la más antigua y se borran las repetidas. Va antes del
        # recálculo de cupos para que el contador refleje la realidad.
        vistas = set()
        for suscripcion in db.query(Suscripcion).order_by(Suscripcion.id).all():
            clave = (suscripcion.arbol_id, suscripcion.usuario_id)
            if clave in vistas:
                db.delete(suscripcion)
                print(
                    f"[migracion] suscripcion duplicada eliminada "
                    f"(arbol {clave[0]}, usuario {clave[1]})"
                )
            else:
                vistas.add(clave)
        db.flush()

        # create_all() no agrega restricciones a tablas que ya existían: el
        # índice único se crea aparte, ya sin duplicados que lo impidan.
        db.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_suscripcion_usuario_arbol "
            "ON suscripciones (usuario_id, arbol_id)"
        ))

        for arbol in db.query(Arbol).all():
            reales = db.query(Suscripcion).filter(Suscripcion.arbol_id == arbol.id).count()
            if (arbol.cupos_ocupados or 0) != reales:
                print(
                    f"[migracion] cupos de '{arbol.nombre}': "
                    f"{arbol.cupos_ocupados} -> {reales} (suscripciones reales)"
                )
                arbol.cupos_ocupados = reales

        db.commit()
    finally:
        db.close()
