<div align="center">

# 🌱 Agro-Colab

**Financia la cosecha, asegura tu abastecimiento.**

Plataforma web full stack que conecta a consumidores con pequeños agricultores chilenos:
el cliente adopta un árbol frutal o contrata una canasta de cosecha, y el pago llega
directo al productor, sin intermediarios.

[![Demo en vivo](https://img.shields.io/badge/demo-en%20vivo-059669?style=for-the-badge&logo=github)](https://arrobaaas.github.io/agro-colab/)
[![Pruebas](https://img.shields.io/github/actions/workflow/status/arrobaaas/agro-colab/pruebas.yml?branch=main&label=pruebas&style=for-the-badge)](https://github.com/arrobaaas/agro-colab/actions/workflows/pruebas.yml)
[![Licencia MIT](https://img.shields.io/badge/licencia-MIT-blue?style=for-the-badge)](LICENSE)

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?logo=sqlalchemy&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?logo=tailwindcss&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white)

<br>

<a href="https://arrobaaas.github.io/agro-colab/">
  <img src="docs/capturas/portada.png" alt="Pantalla de inicio de Agro-Colab: titular 'Del huerto chileno. Directo a tu mesa.', un árbol animado de partículas y el formulario de inicio de sesión" width="900">
</a>

[Demo](https://arrobaaas.github.io/agro-colab/) ·
[Destacados](#-destacados-técnicos) ·
[Arquitectura](#-arquitectura) ·
[Seguridad](#-seguridad) ·
[Instalación](#-instalación-local) ·
[API](#-api-rest) ·
[Base de datos](db/README.md) ·
[Documentos](#-documentos) ·
[Equipo](#-equipo)

</div>

---

## 🔎 Prueba la demo

**👉 [arrobaaas.github.io/agro-colab](https://arrobaaas.github.io/agro-colab/)**

| Rol | Correo | Contraseña |
|---|---|---|
| Comprador | `comprador@agrocolab.cl` | `123` |
| Agricultor | `agricultor@agrocolab.cl` | `123` |

> El backend corre en el plan gratuito de Render: si estuvo inactivo, la primera petición
> puede tardar alrededor de un minuto mientras el servidor despierta.
>
> **Estas cuentas son públicas: no escribas datos reales en ellas.** Lo demo y lo real están
> separados: el comprador demo solo adopta árboles demo, la cuenta demo no ve a personas reales
> ni modifica el catálogo, y lo que quede guardado en la cuenta demo se borra cada hora.

---

## 📋 El problema

El pequeño agricultor necesita capital **antes** de la temporada, y termina vendiendo su
cosecha a intermediarios que se quedan con buena parte del margen. Agro-Colab le permite
cobrar por adelantado, directamente al consumidor final, con dos líneas de producto:

| Línea | Qué compra el cliente | Planes |
|---|---|---|
| **Adopción de árboles** | Un cupo sobre un árbol concreto: es copropietario de su producción de temporada | Básico (5 personas) · Intermedio (3) · Premium (exclusivo) |
| **Abastecimiento** | Una canasta de cosecha con entrega programada a domicilio o a un local comercial | Dúo · Familiar · B2B (facturable) |

Cada pedido genera un código de seguimiento que lo vincula a su huerto de origen.

---

## ⭐ Destacados técnicos

- **Sin sobreventa bajo concurrencia.** La reserva de cupos es un `UPDATE` condicional atómico, respaldado por un índice único y una restricción `CHECK`: dos compras simultáneas del último cupo nunca se aprueban ambas.
- **Seguridad aplicada de punta a punta.** Tokens firmados con HMAC-SHA256, autorización por recurso, *rate limiting* persistente, CSP estricta sin JavaScript en línea y defensa contra XSS en tres capas. [Ver detalle](#-seguridad).
- **Monitoreo y alertas propios.** Los eventos de seguridad se registran en base de datos y en logs JSON, y disparan alertas por correo o webhook según reglas (fuerza bruta, tokens falsificados, accesos a datos ajenos).
- **Calidad verificada en CI.** 279 pruebas automatizadas que GitHub Actions ejecuta en cada *push* contra **SQLite y PostgreSQL**, junto con una revisión de sintaxis del frontend. Las reglas de la arquitectura también se comprueban leyendo el código.
- **Frontend sin frameworks.** SPA en JavaScript vanilla organizada en servicios, con router de vistas, delegación de eventos, gráficos accesibles hechos con HTML y CSS, y un árbol 3D de partículas en `<canvas>`.
- **Privacidad desde el diseño.** Cumplimiento de la Ley N° 21.719 de Protección de Datos Personales de Chile: consentimiento explícito, derechos de acceso, rectificación y eliminación, y registro de tratamiento.

---

## ✨ Funcionalidades

**Comprador**
- Catálogo de árboles con filtro por plan y cupos disponibles en tiempo real.
- Canasta de compra y pasarela de pago simulada: el monto lo fija el servidor y los datos de la tarjeta nunca se guardan.
- Planes de abastecimiento con destino particular o comercial (razón social y RUT).
- Panel de adopción: árboles adoptados, coparticipantes, cosecha estimada y cancelación de la suscripción.
- Autocompletado de direcciones reales con OpenStreetMap, sin geolocalizar el dispositivo.
- Registro con verificación por correo, recuperación de contraseña y eliminación completa de la cuenta.

**Agricultor**
- Panel con estadísticas y gráficos: ingresos por árbol, ocupación de cupos y adopciones por mes.
- Publicación de árboles desde un **catálogo cerrado de 12 especies**, con nombre compuesto automáticamente (por ejemplo, "Palto Hass #104").
- **Galería de 36 fotos verificadas** de Wikimedia Commons: el servidor rechaza cualquier imagen que no corresponda a la especie, incluso en peticiones hechas a mano. Así el comprador ve siempre el árbol correcto.
- Gestión de suscriptores: perfil de contacto y expulsión para liberar el cupo.

**Administrador**
- Panel con todas las cuentas: búsqueda por nombre o correo, filtro por tipo y resumen de compradores, agricultores y árboles publicados.
- Detalle de cada cuenta: datos de contacto, árboles publicados (agricultor) o adoptados (comprador).
- Corrección de datos, verificación manual, cambio de contraseña (cierra las sesiones de la persona y le avisa por correo) y eliminación de la cuenta con todos sus datos.
- Nadie puede registrarse como administrador: la cuenta se crea solo desde las variables del servidor. Las cuentas demo y de otros administradores no se pueden editar ni eliminar. Cada edición, eliminación y lectura de datos queda en el registro de seguridad.

---

## 🏗 Arquitectura

Arquitectura cliente-servidor en capas, en un **monolito modular**. El frontend estático se
publica en GitHub Pages y consume una API REST en FastAPI desplegada en Render.

```mermaid
flowchart LR
    subgraph Cliente["Presentación · GitHub Pages"]
        SPA["SPA en JavaScript<br/>Tailwind CSS"]
    end
    subgraph Servidor["Servidor · Render · un proceso"]
        R["routers/<br/>HTTP"]
        S["services/<br/>reglas de negocio"]
        Rep["repositories/<br/>consultas y transacciones"]
        Seg["seguridad.py<br/>eventos y alertas"]
    end
    subgraph Datos["Datos"]
        DB[("PostgreSQL<br/>SQLAlchemy ORM")]
    end
    Brevo["Brevo<br/>correo transaccional"]
    Photon["Photon<br/>OpenStreetMap"]

    SPA -- "fetch + Bearer token" --> R
    R --> S --> Rep --> DB
    S --> Seg --> Rep
    S -- "códigos de verificación" --> Brevo
    SPA -- "autocompletado" --> Photon
```

| Capa | Dónde | Responsabilidad | No puede |
|---|---|---|---|
| Presentación | `frontend/` | Vistas por rol en un único documento, sin recargas | Decidir reglas: el servidor valida todo de nuevo |
| HTTP | `backend/routers/`, `main.py` | Rutas, validación de entrada y traducción de errores a códigos HTTP | Contener condicionales de negocio ni consultas |
| Negocio | `backend/services/` | Cupos, pagos, validación de especies e imágenes, cuentas | Conocer HTTP ni escribir consultas |
| Datos | `backend/repositories/`, `database.py` | Consultas, transacciones, modelos y migraciones ligeras | Depender de las capas superiores |

`backend/tests/test_arquitectura.py` comprueba estas reglas leyendo el código.

**Tecnologías:** Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, PostgreSQL (SQLite en local), bcrypt,
JavaScript ES2020, Tailwind CSS, GitHub Pages, Render, GitHub Actions y Brevo.

---

## 🔐 Seguridad

| Área | Implementación |
|---|---|
| Contraseñas | Hash con **bcrypt**, de 8 caracteres a 72 bytes. Cambiarla exige la actual y cierra las demás sesiones |
| Sesión | **Tokens firmados con HMAC-SHA256**, con expiración de 7 días, ligados a la contraseña y con cierre de sesión en el servidor. Se guardan en `sessionStorage`, limitados a la pestaña |
| Autorización | Por recurso: cada usuario solo ve y modifica lo suyo. El usuario se toma siempre del token, nunca del cuerpo de la petición. El panel de administración exige el rol de administrador en el servidor. Lo demo y lo real no se mezclan |
| Integridad | Precios fijados por el servidor, reserva de cupos atómica con índice único y `CHECK`, y lo vendido no cambia mientras el árbol tenga suscriptores |
| XSS | Escape de todo dato insertado como HTML, rechazo de `<` y `>` en el backend y **Content-Security-Policy** sin `'unsafe-inline'` en scripts (los estilos en línea sí se permiten) |
| Abuso | *Rate limiting* por IP y por cuenta en login (solo cuentan los fallos), registro, verificación, pagos, pedidos y publicaciones, persistido en la base de datos. Peticiones de 64 KB como máximo |
| Cuentas | Verificación por correo con códigos generados con `secrets` y guardados como HMAC con clave. La verificación también exige la contraseña. Ni las respuestas ni su tiempo revelan qué correos están registrados |
| Transporte | Cabeceras `nosniff`, `X-Frame-Options`, `Referrer-Policy`, HSTS y `no-store`, también en los errores 500, y CORS limitado al origen de GitHub Pages (compartido por los sitios de la cuenta) |

<details>
<summary><b>Registro de eventos, reglas de alerta y panel de monitoreo</b></summary>

<br>

Cada evento de seguridad se guarda en la tabla `eventos_seguridad` (30 días) y como una
línea JSON en los logs del servidor, con el correo y la IP enmascarados: logins fallidos y exitosos, tokens falsificados,
accesos a datos ajenos, bloqueos por *rate limit*, intentos de XSS, ataques a las cuentas
demo, cambios de contraseña y cuentas eliminadas. El navegador también reporta cuando la
CSP bloquea código (`POST /api/seguridad/csp`).

Cuando se cumple una regla se envía una alerta por correo o webhook, como máximo una vez
por hora por regla y origen:

| Regla | Se dispara con |
|---|---|
| Posible fuerza bruta | 5 logins fallidos contra una cuenta en 15 min |
| Tokens falsificados | 5 tokens inválidos desde una IP en 10 min |
| Acceso a datos ajenos | 5 accesos denegados desde una IP en 10 min |
| Ataque a cuentas demo | 3 intentos de modificarlas desde una IP en 30 min |
| Rate limit superado | 1 bloqueo |
| Intento de XSS | 1 texto con `<` o `>` |
| Bloqueo de CSP | 3 reportes desde una IP en 10 min |
| Prueba de contraseñas | 6 logins fallidos desde una IP en 15 min |
| Códigos de recuperación | 8 incorrectos desde una IP en 15 min |
| Códigos de verificación | 4 incorrectos contra una cuenta en 1 hora |
| Prueba de tarjetas | 5 pagos rechazados desde una IP en 15 min |

Se envían como máximo 20 alertas por hora en total, y las alertas por webhook no pueden
mencionar a todo el canal.

El panel de monitoreo (`frontend/monitoreo.html`) muestra los eventos de las últimas 24
horas por tipo y severidad, y se actualiza cada 30 segundos. Pide el `MONITOREO_TOKEN`,
que se guarda solo en memoria.

</details>

<details>
<summary><b>Ley N° 21.719 de Protección de Datos Personales (Chile)</b></summary>

<br>

El proyecto incorpora desde el diseño los requisitos de la ley, vigente desde el 1 de
diciembre de 2026: consentimiento explícito al registrarse, registrado en el servidor con la
versión aceptada, [política de
privacidad](https://arrobaaas.github.io/agro-colab/frontend/privacidad.html) y derechos
de acceso, rectificación, portabilidad y eliminación desde el perfil del usuario.

**Delegado de Protección de Datos (DPO):** Nicolas Reyes Orellana · [@arrobaaas](https://github.com/arrobaaas)

| Dato | Finalidad | Base legal | Plazo |
|---|---|---|---|
| Nombre | Identificar al usuario | Contrato | Hasta eliminación |
| Email | Autenticación y comunicaciones | Contrato | Hasta eliminación |
| Contraseña (hash bcrypt) | Autenticación | Contrato | Hasta eliminación |
| Teléfono | Contacto de entrega | Contrato | Hasta eliminación |
| Dirección | Despacho de productos | Contrato | Hasta eliminación |
| Suscripciones | Gestión de adopciones | Contrato | Hasta eliminación |
| Pedidos: dirección, código postal y celular, con razón social y RUT si son comerciales | Gestión logística | Contrato | Hasta eliminación |
| Pagos: marca y últimos 4 dígitos | Comprobantes | Contrato | Hasta eliminación |
| IP, correo y acción en eventos de seguridad | Detectar y responder a ataques | Interés legítimo | 30 días |

| Derecho | Cómo ejercerlo |
|---|---|
| Acceso y portabilidad | Botón "Descargar mis datos" en el perfil |
| Rectificación | Perfil de usuario; el correo, por medio del administrador |
| Eliminación | Botón "Eliminar cuenta" en el perfil. El registro de seguridad conserva la IP y las acciones, sin el correo, hasta 30 días |
| Oposición | Contactar al DPO |

**Notificación de brechas:** el equipo se compromete a avisar a la Agencia de Protección de
Datos y a los usuarios afectados dentro de 72 horas, con documentación del incidente y de las
medidas correctivas. El procedimiento está en [`docs/INCIDENTES.md`](docs/INCIDENTES.md).

**Evaluación de impacto:** no se tratan datos sensibles y el volumen es pequeño (prototipo
académico). El mayor riesgo era la cuenta demo con credenciales públicas, y por eso lo demo y lo
real están separados; el origen de GitHub Pages sigue siendo compartido.

**Encargados del tratamiento:** GitHub Pages, Render y Brevo; Photon, Google Fonts, cdnjs y
Wikimedia desde el navegador; y Discord o Slack si están activadas las alertas por webhook.

</details>

---

## 🧪 Pruebas e integración continua

**279 pruebas automatizadas** con pytest. GitHub Actions las ejecuta en cada *push* y
*pull request* dos veces, **con SQLite y con PostgreSQL**, y además revisa la sintaxis de
todo el JavaScript del frontend. Las pruebas usan una base temporal y nunca envían correos.

| Archivo | Qué cubre |
|---|---|
| `test_cuentas.py` | Registro y verificación, login, tokens alterados y recuperación de contraseña (sin enumeración de usuarios, código guardado como hash, bloqueo tras 5 errores y cierre de sesiones) |
| `test_pagos.py` | Aprobación y rechazo, monto fijado por el servidor, tarjetas inválidas, sin cobro si no hay cupo, número y CVV nunca guardados |
| `test_seguridad.py` | Autorización por recurso, cabeceras, rechazo de XSS, imágenes fuera del catálogo, cuentas demo protegidas, límite de intentos y borrado de datos |
| `test_admin.py` | Acceso exclusivo del administrador, registro como administrador bloqueado, edición y cambio de contraseña, correos repetidos, eliminación con sus árboles y cuentas protegidas |
| `test_base_datos.py` | Selección de la base de datos según las variables de entorno (SQLite local o PostgreSQL de Render) |
| `test_contrato_http.py` | Código de estado de cada resultado (201, 400, 401, 402, 403, 404, 409, 422, 429) y forma única de los errores |
| `test_arquitectura.py` | Separación de capas: consultas solo en la capa de datos, routers sin reglas, negocio sin HTTP |
| `test_despacho.py` | Celular con código de país y código postal del despacho |
| `test_canasta.py` | Pago único de la canasta: un cobro, todo o nada, rechazo sin adopciones y límites |
| `test_auditoria.py` | Lo corregido en la auditoría de seguridad: separación de lo demo y lo real, cuentas, límites, carreras, alertas, privacidad y cabeceras |
| `test_entregables.py` | La tabla de la API, `.env.example` y `db/esquema.sql` coinciden con el código; ejecuta completa la colección de Postman |

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest
```

---

## 🚀 Instalación local

**Requisitos:** Python 3.12 o superior y un navegador moderno.

```bash
git clone https://github.com/arrobaaas/agro-colab.git
cd agro-colab

# Backend → http://127.0.0.1:8000  (documentación interactiva en /docs)
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env        # Windows: copy ..\.env.example ..\.env
uvicorn main:app --reload --port 8000 --env-file ../.env
```

```bash
# Frontend → http://localhost:3000  (en otra terminal)
cd frontend
python3 -m http.server 3000
```

Con los valores de [`.env.example`](.env.example) se usa una base SQLite local que se crea
sola con las cuentas de demostración y tres árboles de ejemplo, y en modo `desarrollo` el
código de verificación aparece en la consola, así que se puede probar el registro sin
configurar el correo. El archivo `.env` está excluido del repositorio. Para crear la base en
PostgreSQL con un script, ver [`db/`](db/README.md).

Los estilos de Tailwind vienen compilados. Si agregas clases nuevas, vuelve a compilarlos
con `bash scripts/compilar-css.sh` (no requiere Node: descarga el ejecutable oficial y
verifica su checksum contra el valor fijado en el script).

<details>
<summary><b>Variables de entorno</b></summary>

<br>

| Variable | Obligatoria | Descripción |
|---|---|---|
| `AGROCOLAB_DB_URL` | No | Conexión con prioridad sobre `DATABASE_URL`. La usan las pruebas para una base temporal |
| `DATABASE_URL` | En producción | Conexión a PostgreSQL (`postgres://` o `postgresql://`). Sin ella se usa SQLite local |
| `AGROCOLAB_SECRET` | En producción | Clave para firmar los tokens. De 32 caracteres o más. Si falta, se genera una al arrancar, se avisa en el log y las sesiones se cierran en cada reinicio |
| `AGROCOLAB_MOD_MODE` | No | `desarrollo` muestra los códigos de verificación y de recuperación sin enviar correo. El servidor se niega a arrancar así si existe `DATABASE_URL` o `RENDER`. Por defecto: `produccion` |
| `CABECERA_IP_CLIENTE` | Recomendada en producción | Cabecera confiable con la IP real del cliente. Elígela tras comprobar qué llega al servidor (ver `docs/INCIDENTES.md`). Sin ella se usa el último valor de `X-Forwarded-For` |
| `AGROCOLAB_DOCS` | No | `1` publica `/docs` y `/openapi.json` en producción. En desarrollo siempre están abiertos |
| `BREVO_API_KEY` | Para el registro en producción | Clave de la API de [Brevo](https://www.brevo.com) para enviar los códigos por correo |
| `CORREO_REMITENTE` | Junto con `BREVO_API_KEY` | Correo verificado en Brevo desde el que se envían los códigos |
| `ALERTA_CORREO` | No | Correo que recibe las alertas de seguridad |
| `ALERTA_WEBHOOK_URL` | No | Webhook de Discord o Slack para las alertas (`https://`) |
| `ADMIN_EMAIL` | Para el panel de administración | Correo de la cuenta de administrador. Si ya existe una cuenta verificada con ese correo, se la asciende al arrancar. Si está sin verificar, se reemplaza su contraseña por `ADMIN_PASSWORD` |
| `ADMIN_PASSWORD` | Junto con `ADMIN_EMAIL` | Contraseña inicial (12 caracteres o más). Después se cambia desde el perfil |
| `ADMIN_NOMBRE` | No | Nombre que se muestra de la cuenta de administrador. Por defecto: "Administrador" |
| `MONITOREO_TOKEN` | Para usar el panel | Token secreto (24 caracteres o más) del panel de monitoreo. Sin él, el panel está desactivado |

Sin `BREVO_API_KEY` y `CORREO_REMITENTE`, en producción el registro avisa que no está
disponible en lugar de crear cuentas que nadie podría verificar. Las cuentas de
demostración funcionan siempre.

</details>

---

## 🔌 API REST

Documentación interactiva (Swagger) en `/docs` en desarrollo, o en producción con `AGROCOLAB_DOCS=1`. El contrato completo,
con parámetros, cuerpos de ejemplo y códigos de éxito y de error, está en
[`docs/API.md`](docs/API.md). Para probarla, importa
[`docs/AgroColab.postman_collection.json`](docs/AgroColab.postman_collection.json) en Postman.

Cada resultado usa su código HTTP: 201 al crear, 401 sin credenciales, 403 sin permiso, 404 si
no existe, 409 si choca con el estado actual y 422 con datos inválidos. Todos los errores
responden `{"status": "error", "mensaje": "..."}`. Los endpoints marcados con 🔒 exigen
`Authorization: Bearer <token>`.

<details>
<summary><b>Ver todos los endpoints</b></summary>

<br>

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/register` | Registra una cuenta y envía el código de verificación |
| `POST` | `/api/verificar-cuenta` | Verifica la cuenta con el código de 6 dígitos e inicia la sesión |
| `POST` | `/api/reenviar-codigo` | Envía un código de verificación nuevo |
| `POST` | `/api/recuperar-contrasena` | Envía un código para restablecer la contraseña |
| `POST` | `/api/restablecer-contrasena` | Cambia la contraseña con el código y cierra las sesiones abiertas |
| `GET` | `/api/estado` | Indica si el envío real de correos está activo |
| `POST` | `/api/login` | Inicia sesión y devuelve el token |
| `POST` | `/api/logout` 🔒 | Cierra en el servidor todas las sesiones de la cuenta |
| `GET` | `/api/especies` | Catálogo cerrado de especies con sus fotos verificadas |
| `GET` | `/api/arboles` | Catálogo público de árboles |
| `GET` | `/api/arboles/{id}` | Un árbol del catálogo |
| `POST` | `/api/arboles` 🔒 | Publica un árbol (solo agricultores) |
| `PUT` | `/api/arboles/{id}` 🔒 | Edita un árbol (solo su productor) |
| `DELETE` | `/api/arboles/{id}` 🔒 | Elimina un árbol sin suscriptores activos (solo su productor) |
| `POST` | `/api/pagos` 🔒 | Pasarela simulada: valida la tarjeta y adopta el árbol reservando el cupo de forma atómica |
| `POST` | `/api/pagos/canasta` 🔒 | Paga toda la canasta en un solo cobro: todo o nada |
| `GET` | `/api/pagos` 🔒 | Historial de pagos (marca y últimos 4 dígitos) |
| `GET` | `/api/pagos/{id}` 🔒 | Un comprobante propio |
| `DELETE` | `/api/arboles/{id}/suscripcion` 🔒 | Cancela la suscripción propia y libera el cupo |
| `GET` | `/api/suscripciones/usuario/{id}` 🔒 | Árboles adoptados por el usuario |
| `GET` | `/api/mis-arboles/{id}/suscriptores` 🔒 | Suscriptores de los árboles del productor |
| `DELETE` | `/api/suscripciones/{id}` 🔒 | Expulsa a un suscriptor (solo el productor) |
| `POST` | `/api/pedidos` 🔒 | Registra un plan de abastecimiento o el despacho de una cosecha |
| `GET` | `/api/pedidos` 🔒 | Pedidos del usuario |
| `GET` | `/api/pedidos/{id}` 🔒 | Un pedido propio |
| `PUT` | `/api/pedidos/{id}` 🔒 | Modifica el destino y la frecuencia de un pedido propio |
| `DELETE` | `/api/pedidos/{id}` 🔒 | Cancela un plan de abastecimiento propio |
| `GET` | `/api/usuario/{id}` 🔒 | Perfil propio, o el de un suscriptor para su productor |
| `PUT` | `/api/perfil` 🔒 | Actualiza el perfil propio |
| `GET` | `/api/perfil/exportar` 🔒 | Descarga una copia de los datos de la cuenta |
| `DELETE` | `/api/perfil` 🔒 | Elimina la cuenta de la sesión y sus datos. Exige la contraseña |
| `GET` | `/api/admin/usuarios` 🔒 | Todas las cuentas con su actividad (solo administrador) |
| `GET` | `/api/admin/usuarios/{id}` 🔒 | Detalle de una cuenta con sus árboles publicados y adoptados (solo administrador) |
| `PUT` | `/api/admin/usuarios/{id}` 🔒 | Corrige los datos de una cuenta, su verificación o su contraseña (solo administrador) |
| `DELETE` | `/api/admin/usuarios/{id}` 🔒 | Elimina una cuenta y todos sus datos (solo administrador) |
| `POST` | `/api/seguridad/csp` | Reporte del navegador cuando la CSP bloquea código |
| `GET` | `/api/seguridad/resumen` | Datos del panel de monitoreo (exige `X-Monitoreo-Token`) |

</details>

---

## 📁 Estructura del proyecto

<details>
<summary><b>Ver árbol de archivos</b></summary>

```
agro-colab/
├── frontend/
│   ├── index.html             # SPA: login y vistas de comprador y agricultor
│   ├── privacidad.html        # Política de privacidad (Ley 21.719)
│   ├── terminos.html          # Términos y condiciones
│   ├── cookies.html           # Política de cookies
│   ├── monitoreo.html         # Panel de monitoreo de seguridad
│   ├── css/                   # Estilos propios y Tailwind compilado
│   └── js/
│       ├── app.js             # Arranque de la aplicación
│       ├── config.js          # URL de la API y vistas por rol
│       ├── api.js             # Cliente HTTP con token de sesión
│       ├── auth.js            # Sesión del usuario
│       ├── views.js           # Router de vistas
│       ├── acciones.js        # Delegación de eventos (sin onclick en el HTML)
│       ├── login.js           # Login, registro y verificación
│       ├── recuperacion.js    # Recuperación de contraseña
│       ├── parcelas.js        # Catálogo, canasta y logística del comprador
│       ├── pago.js            # Checkout de la pasarela simulada
│       ├── dashboard.js       # Panel del comprador
│       ├── agricultor.js      # Panel del agricultor
│       ├── graficos.js        # Gráficos accesibles con HTML y CSS
│       ├── catalogo.js        # Selector de especies y galería de fotos
│       ├── autocomplete.js    # Autocompletado de direcciones
│       ├── perfil.js          # Perfil de usuario
│       ├── dialogo.js         # Diálogos propios (reemplazan alert y confirm)
│       ├── efectos.js         # Animaciones de scroll e inclinación 3D
│       ├── constelacion.js    # Árbol 3D de partículas en canvas
│       ├── admin.js           # Panel de administración
│       ├── sitio.js           # Aviso de cookies y clic derecho, en todas las páginas
│       ├── monitoreo.js       # Panel de monitoreo
│       ├── legal.js           # Efectos de las páginas legales
│       └── ui.js              # Alertas, formato de montos y escape de HTML
├── backend/
│   ├── main.py                # Aplicación, CORS y traducción de errores a códigos HTTP
│   ├── routers/               # Capa HTTP: rutas, sin reglas ni consultas
│   ├── services/              # Capa de negocio: cuentas, arboles, suscripciones, pedidos, pagos, admin
│   ├── repositories/          # Capa de datos: consultas y transacciones
│   ├── database.py            # Conexión, modelos SQLAlchemy y migraciones ligeras
│   ├── schemas.py             # Contratos de entrada (Pydantic)
│   ├── errores.py             # Errores del dominio
│   ├── core.py                # Tokens, autenticación y límite de intentos
│   ├── catalogo.py            # Catálogo de especies con fotos atribuidas
│   ├── seguridad.py           # Eventos, reglas de alerta y alertas
│   ├── notificaciones.py      # Correo transaccional (Brevo) y sus plantillas
│   └── tests/                 # Pruebas automatizadas (pytest)
├── db/                        # Diagrama del modelo y script de creación de la base
├── .github/workflows/         # Integración continua
├── scripts/compilar-css.sh    # Compilación de Tailwind con verificación de checksum
├── .env.example               # Variables de entorno, con valores de ejemplo
└── docs/
    ├── Informe_Hito2_AgroColab.pdf  # Documento técnico del Hito 2
    ├── API.md                 # Contrato completo de la API
    ├── AgroColab.postman_collection.json  # Peticiones de la demostración
    ├── capturas/              # Capturas de pantalla
    ├── Informe.pdf            # Propuesta del Hito 1
    └── Presentacion.pptx      # Presentación del proyecto
```

</details>

---

## 📚 Documentos

| Documento | Contenido |
|---|---|
| [Documento técnico del Hito 2](docs/Informe_Hito2_AgroColab.pdf) | Arquitectura, decisiones, contrato de la API, capas, persistencia, mediciones y limitaciones |
| [Contrato de la API](docs/API.md) | Rutas, verbos, parámetros, cuerpos de ejemplo y códigos de estado |
| [Colección de Postman](docs/AgroColab.postman_collection.json) | Las peticiones de la demostración, listas para importar |
| [Modelo de datos y script SQL](db/README.md) | Diagrama y creación de la base desde cero |
| [Propuesta del Hito 1](docs/Informe.pdf) · [Presentación](docs/Presentacion.pptx) | Propuesta comercial y arquitectura inicial |

---

## 🤖 Uso de Inteligencia Artificial

En este proyecto se usaron herramientas de IA como **apoyo**. Las decisiones de diseño,
la revisión del código y la responsabilidad sobre el resultado son del equipo.

| Herramienta | Período | Uso |
|---|---|---|
| **Gemini** (Google) | Septiembre 2026 | Estructura y redacción de los argumentos comerciales del informe |
| **ChatGPT** (OpenAI) | Septiembre 2026 | Comparación técnica de lenguajes (Node.js vs Python) y apoyo en el código del prototipo inicial |
| **Claude Code** (Anthropic) | Octubre 2026 | Asistente de programación: revisión de código, autenticación con tokens y autorización por recurso, corrección de la condición de carrera en la reserva de cupos, y documentación |
| **Claude Code** (Anthropic) | Noviembre 2026 | Análisis contra la rúbrica, corrección de los códigos HTTP, separación en capas, pruebas nuevas, carpeta `db/`, colección de Postman, mediciones y documento técnico del Hito 2 |

Los cambios propuestos por la IA se revisaron antes de incorporarlos, y los de seguridad
se probaron contra la API en ejecución: peticiones sin token o con token falso, acceso a
recursos de otros usuarios y compras simultáneas del último cupo. Las cifras del informe
se contrastaron con fuentes primarias del Ministerio de Agricultura.

---

## 👥 Equipo

| Integrante | GitHub |
|---|---|
| Nicolas Reyes Orellana | [@arrobaaas](https://github.com/arrobaaas) |
| Joaquin Alveal Santos | [@Joaquin-Alveal](https://github.com/Joaquin-Alveal) |
| Matias Gonzalez Paredes | [@SKT1-Ctrl](https://github.com/SKT1-Ctrl) |

Proyecto semestral del curso **INGT1003 Arquitectura de Desarrollo (Móvil y Web)** ·
Universidad Mayor · 2026

---

## 📄 Licencia

Código bajo [licencia MIT](LICENSE). Las fotografías del catálogo conservan sus licencias
originales de Wikimedia Commons (CC BY, CC BY-SA o dominio público), con autor y licencia
registrados por imagen. Dependencias, servicios y créditos en
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
