from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Float, Boolean, Text, inspect, text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import bcrypt
import hmac

# Conexión a SQLite (para desarrollo local)
SQLALCHEMY_DATABASE_URL = "sqlite:///./agrocolab.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
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

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    arbol_id = Column(Integer, ForeignKey("arboles.id"))
    fecha_suscripcion = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="suscripciones")
    arbol = relationship("Arbol", back_populates="suscriptores")

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

    cliente = relationship("Usuario", back_populates="pedidos")


# ----------------- MIGRACIONES LIGERAS -----------------
# create_all() no modifica las tablas que ya existen en el archivo SQLite, por eso
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