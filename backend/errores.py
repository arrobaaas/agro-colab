"""Errores del dominio. La capa de negocio los lanza sin saber nada de HTTP;
main.py los traduce al código de estado que corresponde."""


class ErrorDeNegocio(Exception):
    """Base de los errores previstos. `estado` es el campo status del cuerpo."""

    estado = "error"

    def __init__(self, mensaje: str, **extra):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.extra = extra


class NoAutenticado(ErrorDeNegocio):
    """Faltan credenciales o no son válidas (401)."""


class PagoRechazado(ErrorDeNegocio):
    """El emisor de la tarjeta rechazó el pago (402)."""

    estado = "rechazado"


class Prohibido(ErrorDeNegocio):
    """El usuario está identificado, pero no puede hacer esto (403)."""


class NoEncontrado(ErrorDeNegocio):
    """El recurso no existe o no es visible para este usuario (404)."""


class Conflicto(ErrorDeNegocio):
    """La petición es válida, pero choca con el estado actual (409)."""


class DatoInvalido(ErrorDeNegocio):
    """El dato tiene buen formato, pero no cumple una regla de negocio (422)."""


class CodigoIncorrecto(ErrorDeNegocio):
    """Código de verificación o recuperación incorrecto o vencido (400)."""


class DemasiadosIntentos(ErrorDeNegocio):
    """Se superó el límite de intentos (429)."""


class ServicioNoDisponible(ErrorDeNegocio):
    """Falta una dependencia externa, como el envío de correo (503)."""
