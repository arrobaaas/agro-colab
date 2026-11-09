# Contrato de la API REST

Tabla de recursos de Agro-Colab: 34 operaciones. La documentación interactiva se genera en
`/docs` al levantar el servicio, y las pruebas comprueban que esta tabla coincida con las rutas reales.

## Convenciones

- **Formato:** JSON. Las escrituras y los errores incluyen `status` y `mensaje`, en lenguaje de usuario.
- **Autenticación:** cabecera `Authorization: Bearer <token>`. El usuario sale siempre del token, nunca del cuerpo.
- **Parámetros:** los de ruta van entre llaves. Ninguna ruta usa parámetros de consulta.
- **Versionado:** la ruta no lleva versión porque hay un solo consumidor. Los cambios compatibles se agregan a
  `/api/`; un cambio incompatible se publicaría en `/api/v2/`, conviviendo con el anterior hasta migrar al cliente.

## Códigos de estado

| Código | Cuándo se usa | Ejemplo |
|---|---|---|
| 200 | La operación se completó | Leer, actualizar o borrar |
| 201 | Se creó un recurso | Publicar un árbol, pagar, crear un pedido |
| 202 | Se aceptó y falta un paso | Registrar una cuenta, pendiente de verificar |
| 204 | Se completó y no hay cuerpo | Reporte de CSP |
| 400 | La petición no se puede cumplir | Código de verificación incorrecto o vencido |
| 401 | Faltan credenciales o no son válidas | Sin token, token falso, contraseña incorrecta |
| 402 | El emisor rechazó el pago | Tarjeta sin fondos. RFC 9110 lo reserva, pero es la convención de las pasarelas, y el cuerpo trae `status: rechazado` y el comprobante |
| 403 | Identificado, pero sin permiso | Un comprador publica un árbol |
| 404 | No existe, o no es visible para este usuario | Árbol inexistente, pedido ajeno |
| 405 | Verbo no admitido | `PATCH /api/arboles` |
| 409 | Choca con el estado actual | Adoptar dos veces, sin cupos, plan sin pagar |
| 422 | El dato no es válido | 0 cupos, especie fuera del catálogo, tarjeta vencida |
| 429 | Se superó el límite de intentos | Demasiados inicios de sesión |
| 503 | Falta una dependencia externa | Registro sin servicio de correo configurado |

Todos los errores tienen la misma forma:

```json
{"status": "error", "mensaje": "Solo los agricultores pueden publicar árboles."}
```

## Recursos

### Especies

| Verbo | Ruta | Acceso | Cuerpo | Éxito | Errores | Qué hace |
|---|---|---|---|---|---|---|
| `GET` | `/api/especies` | Público | — | 200 | — | Catálogo cerrado de 12 especies con sus fotos verificadas |

### Árboles

| Verbo | Ruta | Acceso | Cuerpo | Éxito | Errores | Qué hace |
|---|---|---|---|---|---|---|
| `GET` | `/api/arboles` | Público | — | 200 | — | Catálogo con los cupos reales |
| `GET` | `/api/arboles/{arbol_id}` | Público | — | 200 | 404, 422 | Un árbol |
| `POST` | `/api/arboles` | Agricultor | `ArbolRequest` | 201 | 401, 403, 422 | Publica un árbol; el productor sale del token |
| `PUT` | `/api/arboles/{arbol_id}` | Su productor | `ArbolRequest` | 200 | 401, 403, 404, 409, 422 | Edita; no acepta menos cupos que suscriptores (409) |
| `DELETE` | `/api/arboles/{arbol_id}` | Su productor | — | 200 | 401, 403, 404, 422 | Borra el árbol, sus suscripciones y despachos |

### Suscripciones

| Verbo | Ruta | Acceso | Cuerpo | Éxito | Errores | Qué hace |
|---|---|---|---|---|---|---|
| `GET` | `/api/suscripciones/usuario/{usuario_id}` | El mismo usuario | — | 200 | 401, 403, 422 | Árboles adoptados |
| `GET` | `/api/mis-arboles/{productor_id}/suscriptores` | El mismo productor | — | 200 | 401, 403, 422 | Suscriptores con datos de contacto |
| `DELETE` | `/api/arboles/{arbol_id}/suscripcion` | Comprador suscrito | — | 200 | 401, 404, 422 | Cancela la suscripción propia y libera el cupo |
| `DELETE` | `/api/suscripciones/{suscripcion_id}` | Productor del árbol | — | 200 | 401, 403, 404, 422 | Expulsa a un suscriptor y libera el cupo |

### Pedidos

| Verbo | Ruta | Acceso | Cuerpo | Éxito | Errores | Qué hace |
|---|---|---|---|---|---|---|
| `GET` | `/api/pedidos` | Sesión | — | 200 | 401 | Solo los pedidos propios |
| `GET` | `/api/pedidos/{pedido_id}` | Su cliente | — | 200 | 401, 404, 422 | Un pedido propio. Uno ajeno responde 404 |
| `POST` | `/api/pedidos` | Comprador | `PedidoRequest` | 201 | 401, 403, 409, 422 | Exige un pago aprobado y sin usar; el monto lo fija el servidor |
| `PUT` | `/api/pedidos/{pedido_id}` | Su cliente | `LogisticaRequest` | 200 | 401, 404, 422 | Cambia destino y frecuencia |
| `DELETE` | `/api/pedidos/{pedido_id}` | Su cliente | — | 200 | 401, 404, 409, 422 | Cancela un plan. Un despacho de árbol responde 409 |

### Pagos (pasarela simulada)

| Verbo | Ruta | Acceso | Cuerpo | Éxito | Errores | Qué hace |
|---|---|---|---|---|---|---|
| `GET` | `/api/pagos` | Sesión | — | 200 | 401 | Últimos 50 pagos propios |
| `GET` | `/api/pagos/{pago_id}` | Su titular | — | 200 | 401, 404, 422 | Un comprobante propio |
| `POST` | `/api/pagos` | Comprador | `PagoRequest` | 201 | 401, 402, 403, 404, 409, 422, 429 | Autoriza y, si es un árbol, reserva el cupo en la misma transacción |

### Cuentas y sesión

| Verbo | Ruta | Acceso | Cuerpo | Éxito | Errores | Qué hace |
|---|---|---|---|---|---|---|
| `POST` | `/api/register` | Público | `RegistroRequest` | 202 | 422, 429, 503 | Crea la cuenta y envía el código. Igual respuesta si el correo ya existe |
| `POST` | `/api/verificar-cuenta` | Público | `{email, codigo}` | 200 | 400, 422, 429 | Verifica y entrega el token |
| `POST` | `/api/reenviar-codigo` | Público | `{email}` | 200 | 422, 429 | Igual respuesta exista o no la cuenta |
| `POST` | `/api/login` | Público | `LoginRequest` | 200 | 401, 422, 429 | Devuelve el token en user.token |
| `POST` | `/api/recuperar-contrasena` | Público | `{email}` | 200 | 422, 429, 503 | Envía un código de 15 minutos |
| `POST` | `/api/restablecer-contrasena` | Público | `{email, codigo, password}` | 200 | 400, 422, 429 | Cambia la contraseña y cierra las sesiones |
| `GET` | `/api/estado` | Público | — | 200 | — | Indica si el correo real está activo |
| `GET` | `/api/usuario/{usuario_id}` | Él mismo o su productor | — | 200 | 401, 403, 404, 422 | Perfil con datos de contacto |
| `PUT` | `/api/perfil` | Sesión | `PerfilRequest` | 200 | 401, 403, 422 | Cambiar la contraseña exige la actual |
| `DELETE` | `/api/perfil` | Sesión | `EliminarCuentaRequest` (`{"password"}`) | 200 | 401, 403, 422, 429 | Borra la cuenta de la sesión y todos sus datos. Exige la contraseña actual |

### Administración

| Verbo | Ruta | Acceso | Cuerpo | Éxito | Errores | Qué hace |
|---|---|---|---|---|---|---|
| `GET` | `/api/admin/usuarios` | Administrador | — | 200 | 401, 403 | Todas las cuentas con su actividad |
| `GET` | `/api/admin/usuarios/{usuario_id}` | Administrador | — | 200 | 401, 403, 404, 422 | Detalle con árboles publicados y adoptados |
| `PUT` | `/api/admin/usuarios/{usuario_id}` | Administrador | `AdminUsuarioRequest` | 200 | 401, 403, 404, 409, 422 | Corrige datos, verificación o contraseña |
| `DELETE` | `/api/admin/usuarios/{usuario_id}` | Administrador | — | 200 | 401, 403, 404, 422 | Elimina la cuenta; las protegidas responden 403 |

### Monitoreo de seguridad

| Verbo | Ruta | Acceso | Cuerpo | Éxito | Errores | Qué hace |
|---|---|---|---|---|---|---|
| `POST` | `/api/seguridad/csp` | Público (navegador) | `ReporteCSP` | 204 | 422, 429 | Reporte de bloqueos de la CSP |
| `GET` | `/api/seguridad/resumen` | Cabecera X-Monitoreo-Token | — | 200 | 401, 404, 429 | Eventos de las últimas 24 horas. 404 si el panel está desactivado |

## Reglas de los cuerpos

| Esquema | Campos y reglas |
|---|---|
| `ArbolRequest` | `especie` del catálogo; `plan`: Básico, Intermedio o Premium; `tipo_suscripcion`: Compartido o Exclusivo; `cupos_totales` de 1 a 50; `precio_mensual_clp` de 0 a 10.000.000; `estimacion_cosecha_kg` de 1 a 100.000; `imagen` de la especie |
| `PedidoRequest` | `tipo_destino`: particular o comercial; `frecuencia_entrega`: semanal, quincenal o mensual; `rut` con dígito verificador; `pago_id` de un pago aprobado. El monto enviado se ignora |
| `LogisticaRequest` | `tipo_destino`, `direccion`, `comuna` y `frecuencia_entrega`; `razon_social` y `rut` si el destino es comercial |
| `PagoRequest` | `tipo`: arbol o plan; `numero` con dígito de Luhn; `vencimiento` MM/AA; `cvv` de 3 o 4 dígitos |
| `RegistroRequest` | `nombre` de 2 a 80; `email` con formato; `password` de 8 a 128; `rol`: comprador o agricultor |
| `LoginRequest` | `email`, `password` y `rol` |
| `PerfilRequest` | `nombre`, `email` propio, `telefono`, `direccion`; `password` y `password_actual` para cambiarla |
| `AdminUsuarioRequest` | `nombre`, `email`, `telefono`, `direccion`, `verificado`; `password` opcional |

## Cuerpos de ejemplo

**`POST /api/arboles`, respuesta 201**

```json
{
  "especie": "palto_hass", "identificador": "#7", "ubicacion": "Quillota",
  "plan": "Básico", "tipo_suscripcion": "Compartido", "cupos_totales": 2,
  "precio_mensual_clp": 9000, "estimacion_cosecha_kg": 30,
  "imagen": "<url de una foto de la especie, según GET /api/especies>"
}
```

**`POST /api/pagos`, respuesta 201**

```json
{
  "tipo": "plan", "plan_nombre": "Canasta Huerto Esencial",
  "numero": "4242 4242 4242 4242", "titular": "Camila Soto", "vencimiento": "12/30", "cvv": "123"
}
```

Tarjetas de prueba: `4242 4242 4242 4242` y `5555 5555 5555 4444` se aprueban; `4000 0000 0000 0002`
(sin fondos) y `4000 0000 0000 9995` (bloqueada) responden 402.

**`POST /api/pedidos`, respuesta 201**

```json
{
  "plan_nombre": "Canasta Huerto Esencial", "cliente_nombre": "Camila Soto",
  "telefono": "+56911111111", "email": "comprador@agrocolab.cl", "tipo_destino": "particular",
  "direccion": "Av. Falsa 123", "comuna": "Ñuñoa", "frecuencia_entrega": "mensual", "pago_id": 1
}
```

## Probarla

Importa [`AgroColab.postman_collection.json`](AgroColab.postman_collection.json) en Postman o Bruno, con el
servicio corriendo, y ejecuta las peticiones en orden. Cada una verifica su código de estado, y una prueba
automatizada ejecuta la colección completa en cada cambio.
