from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Float, Boolean, Text, inspect, text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import bcrypt

# Conexión a SQLite (para desarrollo local)
SQLALCHEMY_DATABASE_URL = "sqlite:///./agrocolab.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def hash_password(password: str) -> str:
    """Hash de contraseña usando bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verificar contraseña contra hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

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
    """Agrega a las tablas existentes las columnas que los modelosecesitan."""
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