"""Contratos de datos de la API: lo que cada ruta acepta como entrada.

Pydantic rechaza con 422 lo que no cumple, antes de llegar a la capa de negocio.
"""

from typing import Annotated, Literal, Optional

from pydantic import AfterValidator, BaseModel, Field, StringConstraints


def _sin_html(valor):
    """Defensa en profundidad contra XSS: ningún texto de usuario necesita < o >."""
    if valor is not None and ("<" in valor or ">" in valor):
        raise ValueError("no puede contener los caracteres < o >")
    return valor


def Texto(maximo: int, minimo: int = 1):
    """Texto libre: sin espacios sobrantes, con largo acotado y sin HTML."""
    return Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=minimo, max_length=maximo),
        AfterValidator(_sin_html),
    ]


def normalizar_rut(valor):
    """Valida un RUT chileno con su dígito verificador (módulo 11) y lo
    devuelve con formato 76.123.456-0. Acepta puntos, guion y espacios."""
    if valor is None or valor == "":
        return None
    limpio = valor.replace(".", "").replace("-", "").replace(" ", "").upper()
    cuerpo, dv = limpio[:-1], limpio[-1:]
    if not cuerpo.isdigit() or not 7 <= len(cuerpo) <= 8 or dv not in "0123456789K":
        raise ValueError("el formato debe ser como 76.123.456-0")

    suma, factor = 0, 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    esperado = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    if dv != esperado:
        raise ValueError("el dígito verificador no corresponde")

    con_puntos = f"{int(cuerpo):,}".replace(",", ".")
    return f"{con_puntos}-{dv}"


Rut = Annotated[str, StringConstraints(strip_whitespace=True, max_length=15), AfterValidator(normalizar_rut)]

Correo = Annotated[str, StringConstraints(
    strip_whitespace=True, max_length=120, pattern=r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$"
)]


def _hasta_72_bytes(valor):
    """bcrypt no admite más de 72 bytes: el límite se valida aquí para responder
    422 y no un error 500 al calcular el hash."""
    if len(valor.encode("utf-8")) > 72:
        raise ValueError("debe tener como máximo 72 bytes")
    return valor


Contrasena = Annotated[str, StringConstraints(min_length=8, max_length=128), AfterValidator(_hasta_72_bytes)]
# [0-9] y no \d: \d también acepta dígitos de otros alfabetos
Codigo = Annotated[str, StringConstraints(pattern=r"^[0-9]{6}$")]
Rol = Literal["comprador", "agricultor"]


def _solo_digitos_celular(valor):
    """Acepta espacios y guiones al escribir, y guarda solo los dígitos."""
    limpio = valor.replace(" ", "").replace("-", "")
    if not limpio.isascii() or not limpio.isdigit() or not 7 <= len(limpio) <= 15:
        raise ValueError("debe tener entre 7 y 15 dígitos")
    return limpio


def _codigo_postal(valor):
    """Los despachos son dentro de Chile, donde el código postal tiene 7 dígitos."""
    if not valor.isascii() or not valor.isdigit() or len(valor) != 7:
        raise ValueError("debe tener 7 dígitos")
    return valor


# Mismas opciones que el selector del formulario de despacho
CodigoPais = Literal["+56", "+54", "+591", "+55", "+57", "+593", "+34", "+1", "+52", "+595", "+51", "+598", "+58"]
Celular = Annotated[str, StringConstraints(strip_whitespace=True, max_length=25), AfterValidator(_solo_digitos_celular)]
CodigoPostal = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10), AfterValidator(_codigo_postal)]
TipoDestino = Literal["particular", "comercial"]
Frecuencia = Literal["semanal", "quincenal", "mensual"]


class LoginRequest(BaseModel):
    # Sin largo mínimo: las cuentas demo usan una contraseña corta
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]
    password: Annotated[str, StringConstraints(max_length=128)]
    rol: Rol

class PedidoRequest(BaseModel):
    # El monto lo fija el servidor (catálogo de planes o precio del árbol) y el
    # cliente sale de la sesión: no se piden en el cuerpo
    plan_nombre: Texto(120)
    tipo_destino: TipoDestino
    razon_social: Optional[Texto(120, 0)] = None
    rut: Optional[Rut] = None
    direccion: Texto(200)
    comuna: Texto(80)
    codigo_postal: CodigoPostal
    telefono_codigo: CodigoPais
    telefono: Celular
    frecuencia_entrega: Frecuencia
    tipo: Literal["abastecimiento", "arbol"] = "abastecimiento"
    arbol_id: Optional[int] = None
    # Plan de abastecimiento: pago aprobado de la pasarela (routers/pagos.py)
    pago_id: Optional[int] = None

class LogisticaRequest(BaseModel):
    """Datos de despacho que se pueden modificar en un pedido existente."""
    tipo_destino: TipoDestino
    razon_social: Optional[Texto(120, 0)] = None
    rut: Optional[Rut] = None
    direccion: Texto(200)
    comuna: Texto(80)
    codigo_postal: CodigoPostal
    telefono_codigo: CodigoPais
    telefono: Celular
    frecuencia_entrega: Frecuencia

class ArbolRequest(BaseModel):
    # El nombre se compone desde especie + identificador, y el productor sale de la sesión
    especie: Texto(40)
    identificador: Optional[Texto(12, 0)] = None
    ubicacion: Texto(150)
    plan: Literal["Básico", "Intermedio", "Premium"]
    tipo_suscripcion: Literal["Compartido", "Exclusivo"]
    cupos_totales: int = Field(ge=1, le=50)
    precio_mensual_clp: int = Field(ge=1, le=10_000_000)
    # Solo el número de kilos: el servidor arma el texto ("45 kg anuales")
    # para que no haya ambigüedad de unidades (kg, gramos, cajas...)
    estimacion_cosecha_kg: int = Field(ge=1, le=100_000)
    imagen: Texto(500)

class PerfilRequest(BaseModel):
    nombre: Texto(80, 2)
    email: Correo
    telefono: Optional[Texto(30, 0)] = None
    direccion: Optional[Texto(200, 0)] = None
    password: Optional[Contrasena] = None
    # Obligatoria para cambiar la contraseña: con solo el token (por ejemplo,
    # robado) no se puede secuestrar la cuenta
    password_actual: Optional[Annotated[str, StringConstraints(max_length=128)]] = None

class RegistroRequest(BaseModel):
    nombre: Texto(80, 2)
    email: Correo
    password: Contrasena
    rol: Rol
    telefono: Optional[Texto(30, 0)] = None
    direccion: Optional[Texto(200, 0)] = None
    # Consentimiento explícito: sin estas casillas marcadas no hay registro
    acepta_datos: Literal[True]
    acepta_terminos: Literal[True]

class EliminarCuentaRequest(BaseModel):
    """Con solo un token robado no se debe poder borrar la cuenta."""
    password: Annotated[str, StringConstraints(max_length=128)]

class AdminUsuarioRequest(BaseModel):
    """Cambios que el administrador hace en la cuenta de otra persona."""
    nombre: Texto(80, 2)
    email: Correo
    telefono: Optional[Texto(30, 0)] = None
    direccion: Optional[Texto(200, 0)] = None
    verificado: bool
    # Opcional: una contraseña nueva, por ejemplo si la persona perdió acceso a su correo
    password: Optional[Contrasena] = None

class ReenvioRequest(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]

class VerificacionRequest(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]
    codigo: Codigo
    # La contraseña con la que se registró: el código solo prueba que el correo es suyo
    password: Annotated[str, StringConstraints(max_length=128)]

class RecuperacionRequest(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]

class RestablecerRequest(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]
    codigo: Codigo
    password: Contrasena


NumeroTarjeta = Annotated[str, StringConstraints(strip_whitespace=True, min_length=12, max_length=23, pattern=r"^[\d ]+$")]
Vencimiento = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^(0[1-9]|1[0-2])/\d{2}$")]
Cvv = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{3,4}$")]


class PagoRequest(BaseModel):
    tipo: Literal["arbol", "plan"]
    arbol_id: Optional[int] = None
    plan_nombre: Optional[Texto(120)] = None
    numero: NumeroTarjeta
    titular: Texto(80)
    vencimiento: Vencimiento
    cvv: Cvv


class ItemCanasta(BaseModel):
    tipo: Literal["arbol", "plan"]
    arbol_id: Optional[int] = None
    plan_nombre: Optional[Texto(120)] = None


class PagoCanastaRequest(BaseModel):
    """Un solo cobro para toda la canasta, con una sola tarjeta."""
    items: Annotated[list[ItemCanasta], Field(min_length=1, max_length=10)]
    numero: NumeroTarjeta
    titular: Texto(80)
    vencimiento: Vencimiento
    cvv: Cvv


class ReporteCSP(BaseModel):
    directiva: Annotated[str, StringConstraints(max_length=100)] = ""
    bloqueado: Annotated[str, StringConstraints(max_length=300)] = ""
    pagina: Annotated[str, StringConstraints(max_length=300)] = ""
    muestra: Optional[Annotated[str, StringConstraints(max_length=120)]] = None
