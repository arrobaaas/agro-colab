from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

# Conexión a SQLite (para desarrollo local)
SQLALCHEMY_DATABASE_URL = "sqlite:///./agrocolab.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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