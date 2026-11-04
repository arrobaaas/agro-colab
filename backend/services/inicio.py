"""Datos iniciales: cuentas de demostración, árboles de ejemplo y administrador."""

import os
from datetime import datetime

from sqlalchemy.orm import Session

from catalogo import foto_de
from core import ROL_ADMIN, es_cuenta_demo
from database import SessionLocal, hash_password
from repositories import arboles as repo_arboles, transaccion, usuarios as repo_usuarios


def crear_administrador(db: Session):
    """Crea la cuenta de administrador desde ADMIN_EMAIL y ADMIN_PASSWORD.

    Nadie puede registrarse como administrador: la cuenta solo existe si se
    configuran esas variables en el servidor, y su contraseña no queda en el
    repositorio. Si el correo ya tiene cuenta, se la asciende a
    administrador. La contraseña solo se usa al crearla: después se cambia
    desde el perfil o con la recuperación de contraseña.
    """
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    if not email:
        return
    usuario = repo_usuarios.por_correo_exacto(db, email)
    if usuario:
        if usuario.rol != ROL_ADMIN and not es_cuenta_demo(usuario):
            usuario.rol = ROL_ADMIN
            usuario.verificado = 1
            transaccion.confirmar(db)
            print(f"[admin] {email} ahora es administrador")
        return
    if len(password) < 12:
        print("[admin] ADMIN_PASSWORD falta o tiene menos de 12 caracteres: no se creó el administrador")
        return
    repo_usuarios.crear(
        db,
        nombre=os.getenv("ADMIN_NOMBRE", "").strip() or "Administrador",
        email=email, password=hash_password(password), rol=ROL_ADMIN, verificado=1,
        consentimiento_datos=1, fecha_consentimiento=datetime.now(), acepta_terminos=1,
    )
    transaccion.confirmar(db)
    print(f"[admin] cuenta de administrador creada: {email}")


def cargar_datos_iniciales():
    """Se ejecuta al arrancar, después de crear las tablas (main.py)."""
    db = SessionLocal()
    try:
        if repo_usuarios.contar(db) == 0:
            # Cuentas de demostración, con contraseña hasheada con bcrypt
            for nombre, email, rol in (
                ("Camila Soto", "comprador@agrocolab.cl", "comprador"),
                ("Hernán Silva", "agricultor@agrocolab.cl", "agricultor"),
            ):
                repo_usuarios.crear(
                    db, nombre=nombre, email=email, password=hash_password("123"), rol=rol, verificado=1,
                    consentimiento_datos=1, fecha_consentimiento=datetime.now(), acepta_terminos=1,
                )
            transaccion.confirmar(db)

        if repo_arboles.contar(db) == 0:
            productor = repo_usuarios.por_correo_exacto(db, "agricultor@agrocolab.cl")
            for especie, identificador, nombre, plan, tipo, precio, cupos, cosecha, ubicacion in (
                ("palto_hass", "#104", "Palto Hass #104", "Básico", "Compartido", 12000, 5, "45 kg anuales", "Valle del Aconcagua, Región de Valparaíso"),
                ("naranjo_valencia", "#22", "Naranjo Valencia #22", "Premium", "Exclusivo", 35000, 1, "80 kg anuales", "Curicó, Región del Maule"),
                ("limonero_eureka", "#12", "Limonero Eureka #12", "Intermedio", "Compartido", 8000, 3, "35 kg anuales", "Mallarauco, Región Metropolitana"),
            ):
                repo_arboles.crear(
                    db, nombre=nombre, especie=especie, identificador=identificador, plan=plan,
                    tipo_suscripcion=tipo, precio_mensual_clp=precio, cupos_totales=cupos, cupos_ocupados=0,
                    estimacion_cosecha=cosecha, ubicacion=ubicacion, imagen=foto_de(especie, 0),
                    imagen_origen="galeria", productor_id=productor.id if productor else None,
                )
            transaccion.confirmar(db)

        crear_administrador(db)
    finally:
        db.close()
