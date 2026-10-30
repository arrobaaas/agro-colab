<div align="center">

# 🌱 Agro-Colab

**Financia la cosecha, asegura tu abastecimiento.**

Plataforma web que conecta a consumidores con pequeños agricultores chilenos mediante la
adopción de árboles frutales y la suscripción a canastas de cosecha, con trazabilidad
directa del huerto a la mesa y sin intermediarios.

[![Demo en vivo](https://img.shields.io/badge/demo-en%20vivo-059669?style=for-the-badge&logo=github)](https://arrobaaas.github.io/agro-colab/)
[![Licencia MIT](https://img.shields.io/badge/licencia-MIT-blue?style=for-the-badge)](LICENSE)
[![Pruebas](https://img.shields.io/github/actions/workflow/status/arrobaaas/agro-colab/pruebas.yml?branch=main&label=pruebas&style=for-the-badge)](https://github.com/arrobaaas/agro-colab/actions/workflows/pruebas.yml)

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?logo=sqlalchemy&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?logo=tailwindcss&logoColor=white)

[Demo](https://arrobaaas.github.io/agro-colab/) ·
[Funcionalidades](#-funcionalidades) ·
[Arquitectura](#-arquitectura) ·
[Instalación](#-instalación-local) ·
[API](#-api-rest) ·
[Seguridad](#-seguridad-y-protección-de-datos) ·
[Equipo](#-equipo)

</div>

---

## 📋 Sobre el proyecto

Agro-Colab nació como proyecto semestral del curso **INGT1003 Arquitectura de Desarrollo
(Móvil y Web)** de la Universidad Mayor (2026). Responde a un problema concreto: el pequeño
agricultor necesita financiamiento antes de la temporada y vende su cosecha a intermediarios
que se quedan con buena parte del margen. Agro-Colab le permite cobrar por adelantado,
directamente al consumidor final.

La plataforma ofrece dos líneas de producto:

| Línea | Qué compra el cliente | Unidad | Planes |
|---|---|---|---|
| **Adopción de árboles** | Un cupo sobre un árbol concreto: es copropietario de su producción de temporada | Cupo (copartícipe) | Básico (5 personas) · Intermedio (3) · Premium (exclusivo) |
| **Abastecimiento** | Una canasta de cosecha con entrega programada a domicilio o local comercial | Kilos por entrega | Dúo · Familiar · B2B (facturable) |

Cada pedido genera un código de seguimiento que lo vincula al huerto de origen.

> **Prueba la demo** con las cuentas de demostración:
> comprador `comprador@agrocolab.cl` / `123` · agricultor `agricultor@agrocolab.cl` / `123`

---

## ✨ Funcionalidades

**Para el comprador**
- Catálogo de árboles con filtro por plan y cupos disponibles en tiempo real.
- Adopción de árboles con control de cupos en el servidor: no hay sobreventa aunque varias personas compren a la vez.
- Contratación de canastas de abastecimiento con destino particular o comercial (razón social y RUT).
- Panel de adopción: árboles adoptados, coparticipantes, cosecha estimada, cancelación de la suscripción.
- Autocompletado de direcciones reales con OpenStreetMap, sin geolocalizar el dispositivo.
- Perfil editable y eliminación completa de la cuenta.

**Para el agricultor**
- Panel con estadísticas: árboles publicados, suscriptores e ingresos estimados.
- Publicación de árboles desde un **catálogo cerrado de 12 especies**: el nombre se compone automáticamente (por ejemplo, "Palto Hass" + "#104").
- **Galería de 36 fotos verificadas** de Wikimedia Commons. El servidor rechaza cualquier imagen que no pertenezca a la especie, incluso en peticiones hechas a mano.
- Gestión de suscriptores: ver su perfil de contacto y expulsarlos para liberar el cupo.

---

## 🏗 Arquitectura

Modelo cliente-servidor en tres capas. El frontend es una SPA en JavaScript vanilla
organizada en servicios; el backend es una API REST en FastAPI dividida en routers por
dominio.

```mermaid
flowchart LR
    subgraph Cliente["Capa de presentación · GitHub Pages"]
        SPA["SPA HTML + JS<br/>Tailwind CSS"]
    end
    subgraph Servidor["Capa de negocio · Render"]
        API["FastAPI<br/>routers por dominio"]
        Core["core.py<br/>validaciones, tokens, catálogo"]
    end
    subgraph Datos["Capa de datos"]
        DB[("SQLite<br/>SQLAlchemy ORM")]
    end
    Photon["Photon / OpenStreetMap"]

    SPA -- "fetch + Bearer token" --> API
    API --> Core --> DB
    SPA -- "autocompletado" --> Photon
```

| Capa | Tecnología | Responsabilidad |
|---|---|---|
| Presentación | HTML5, CSS3, JavaScript (ES2020), Tailwind CSS, Font Awesome | Vistas por rol en un único documento, sin recargas |
| Negocio | Python 3.12, FastAPI, Pydantic | Reglas de cupos, validación de especies e imágenes, autenticación |
| Datos | SQLAlchemy 2, SQLite | Persistencia, restricciones de integridad y migraciones ligeras al arrancar |

---

## 📁 Estructura del proyecto

```
agro-colab/
├── index.html                 # Redirección a frontend/ para GitHub Pages
├── frontend/
│   ├── index.html             # SPA: login y vistas de comprador y agricultor
│   ├── privacidad.html        # Política de privacidad (Ley 21.719)
│   ├── terminos.html          # Términos y condiciones
│   ├── monitoreo.html         # Panel de monitoreo de seguridad (con token)
│   ├── css/
│   │   ├── styles.css         # Estilos propios
│   │   └── tailwind.css       # Tailwind compilado (scripts/compilar-css.sh)
│   └── js/
│       ├── config.js          # URL de la API y vistas por rol
│       ├── api.js             # Cliente HTTP: adjunta el token de sesión
│       ├── auth.js            # Sesión en localStorage
│       ├── views.js           # Router de vistas
│       ├── login.js           # Login, registro y verificación de cuenta
│       ├── parcelas.js        # Catálogo, carrito y logística del comprador
│       ├── dashboard.js       # Panel de adopción del comprador
│       ├── agricultor.js      # Panel del agricultor
│       ├── catalogo.js        # Selector de especies y galería de fotos
│       ├── autocomplete.js    # Autocompletado de direcciones (Photon)
│       ├── perfil.js          # Perfil de usuario
│       ├── ui.js              # Alertas, formato de montos y escape de HTML
│       ├── acciones.js        # Delegación de eventos (sin onclick en el HTML)
│       ├── efectos.js         # Animaciones de scroll e inclinación 3D
│       ├── monitoreo.js       # Panel de monitoreo de seguridad
│       └── app.js             # Arranque de la aplicación
├── backend/
│   ├── main.py                # Aplicación FastAPI, CORS y registro de routers
│   ├── core.py                # Esquemas, tokens de sesión y lógica compartida
│   ├── database.py            # Modelos SQLAlchemy y migraciones
│   ├── catalogo.py            # Catálogo cerrado de especies con fotos atribuidas
│   ├── seguridad.py           # Registro de eventos, reglas de alerta y alertas
│   ├── notificaciones.py      # Envío de correos (Brevo)
│   ├── routers/               # arboles, especies, suscripciones, pedidos, pagos, usuarios, monitoreo
│   ├── tests/                 # Pruebas automatizadas (pytest)
│   ├── requirements.txt
│   └── requirements-dev.txt   # requirements.txt + pytest y httpx
├── Informe.pdf                # Informe del proyecto
├── Presentacion.pptx          # Presentación del proyecto
├── scripts/compilar-css.sh    # Compila Tailwind localmente (verifica el checksum)
├── LICENSE
└── THIRD_PARTY_NOTICES.md
```

---

## 🚀 Instalación local

**Requisitos:** Python 3.12 o superior y un navegador moderno.

```bash
git clone https://github.com/arrobaaas/agro-colab.git
cd agro-colab

# Backend (http://127.0.0.1:8000)
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

En otra terminal:

```bash
# Frontend (http://localhost:3000)
cd frontend
python3 -m http.server 3000
```

Los estilos de Tailwind ya vienen compilados en `frontend/css/tailwind.css`. Si agregas
clases nuevas al HTML o al JavaScript, vuelve a compilarlos (no requiere Node; descarga
el ejecutable oficial y verifica su checksum antes de usarlo):

```bash
bash scripts/compilar-css.sh
```

La base de datos SQLite (`backend/agrocolab.db`) se crea sola al primer arranque, con las
cuentas de demostración y tres árboles de ejemplo. La documentación interactiva de la API
queda en `http://127.0.0.1:8000/docs`.

### Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `AGROCOLAB_SECRET` | En producción | Clave para firmar los tokens de sesión. Si falta, se genera una al arrancar y las sesiones se cierran en cada reinicio. |
| `AGROCOLAB_MOD_MODE` | No | `desarrollo` devuelve el código de verificación de cuenta en la respuesta, para probar el registro sin correo. Por defecto: `produccion`. |
| `BREVO_API_KEY` | Para registrar cuentas y recuperar contraseñas en producción | Clave de la API de [Brevo](https://www.brevo.com) para enviar los códigos por correo (plan gratuito: 300 correos al día). |
| `CORREO_REMITENTE` | Junto con `BREVO_API_KEY` | Correo verificado en Brevo desde el que se envía el código. |
| `ALERTA_CORREO` | No | Correo que recibe las alertas de seguridad (usa Brevo). |
| `ALERTA_WEBHOOK_URL` | No | Webhook de Discord o Slack para las alertas de seguridad (`https://`). |
| `MONITOREO_TOKEN` | Para usar el panel | Token secreto (24 caracteres o más) que da acceso al panel de monitoreo. Sin él, el panel está desactivado. |

Sin `BREVO_API_KEY` y `CORREO_REMITENTE`, en producción el registro de cuentas nuevas
avisa que no está disponible, en lugar de crear cuentas que nadie podría verificar.
Las cuentas de demostración funcionan siempre.

---

## 🧪 Pruebas

El backend tiene **35 pruebas automatizadas** (pytest) que corren en GitHub Actions
en cada push y en cada pull request, junto con una revisión de sintaxis de todo el
JavaScript del frontend.

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest
```

Las pruebas usan una base SQLite temporal (nunca `agrocolab.db`) y no envían correos.

| Archivo | Qué cubre |
|---|---|
| `tests/test_cuentas.py` | Registro y verificación, login, tokens alterados, recuperación de contraseña (sin enumeración de usuarios, código guardado como hash y anulado tras 5 errores, cierre de sesiones) |
| `tests/test_pagos.py` | Pasarela simulada: aprobación y rechazo, monto fijado por el servidor, tarjetas inválidas, sin cobro si no hay cupo, número y CVV nunca guardados, planes que exigen un pago propio y no reutilizable |
| `tests/test_seguridad.py` | Autorización por recurso, cabeceras de seguridad, rechazo de HTML (XSS), imágenes fuera del catálogo, cuentas demo protegidas, límite de intentos de login, borrado de datos al eliminar la cuenta |

---

## 🔌 API REST

Los endpoints marcados con 🔒 exigen el header `Authorization: Bearer <token>`, que se
obtiene al iniciar sesión. El usuario se toma siempre del token, nunca del cuerpo de la
petición.

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/register` | Registra una cuenta y envía el código de verificación |
| `POST` | `/api/verificar-cuenta` | Verifica la cuenta con el código de 6 dígitos |
| `POST` | `/api/recuperar-contrasena` | Envía un código para restablecer la contraseña (misma respuesta exista o no la cuenta) |
| `POST` | `/api/restablecer-contrasena` | Cambia la contraseña con el código y cierra las sesiones abiertas |
| `GET` | `/api/estado` | Indica si el envío real de correos está activo |
| `POST` | `/api/login` | Inicia sesión y devuelve el token |
| `GET` | `/api/especies` | Catálogo cerrado de especies con sus fotos verificadas |
| `GET` | `/api/arboles` | Catálogo público de árboles |
| `POST` | `/api/arboles` 🔒 | Publica un árbol (solo agricultores) |
| `PUT` | `/api/arboles/{id}` 🔒 | Edita un árbol (solo su productor) |
| `DELETE` | `/api/arboles/{id}` 🔒 | Elimina un árbol y sus suscripciones (solo su productor) |
| `POST` | `/api/pagos` 🔒 | Pasarela simulada: valida la tarjeta de prueba y, si se aprueba, adopta el árbol reservando el cupo de forma atómica |
| `GET` | `/api/pagos` 🔒 | Historial de pagos del comprador (marca y últimos 4 dígitos) |
| `POST` | `/api/cancelar-suscripcion` 🔒 | Cancela la suscripción propia y libera el cupo |
| `GET` | `/api/suscripciones/usuario/{id}` 🔒 | Árboles adoptados por el usuario |
| `GET` | `/api/mis-arboles/{id}/suscriptores` 🔒 | Suscriptores de los árboles del productor |
| `DELETE` | `/api/suscripciones/{id}` 🔒 | Expulsa a un suscriptor (solo el productor) |
| `POST` | `/api/pedidos` 🔒 | Registra un plan de abastecimiento o el despacho de la cosecha de un árbol adoptado |
| `GET` | `/api/pedidos` 🔒 | Pedidos del usuario |
| `PUT` | `/api/pedidos/{id}` 🔒 | Modifica el destino y la frecuencia de un pedido propio |
| `DELETE` | `/api/pedidos/{id}` 🔒 | Cancela un plan de abastecimiento propio |
| `GET` | `/api/usuario/{id}` 🔒 | Perfil propio, o el de un suscriptor para su productor |
| `PUT` | `/api/perfil` 🔒 | Actualiza el perfil propio |
| `DELETE` | `/api/usuario/{email}` 🔒 | Elimina la cuenta propia y todos sus datos |

---

## 🔐 Seguridad y protección de datos

**Medidas implementadas**
- Contraseñas hasheadas con **bcrypt**; mínimo 8 caracteres para cuentas nuevas. Las bases antiguas con texto plano se migran solas al arrancar.
- **Tokens de sesión firmados con HMAC-SHA256**, con expiración de 7 días y ligados a la contraseña: al cambiarla, los tokens anteriores dejan de servir. Cambiar la contraseña exige la actual.
- **Autorización por recurso:** cada usuario solo ve y modifica lo suyo, y solo el productor ve los datos de contacto de sus suscriptores. Solo los compradores adoptan y contratan planes.
- **Precios fijados por el servidor:** el monto de un plan o de un árbol nunca se toma del navegador.
- **Protección contra XSS en tres capas:** todo dato se escapa antes de insertarse como HTML, el backend rechaza `<` y `>` en los textos y una **Content-Security-Policy estricta** prohíbe el JavaScript en línea (`script-src` sin `'unsafe-inline'`) y las conexiones a dominios ajenos. El HTML no tiene manejadores `onclick`: los eventos se conectan por delegación (`acciones.js`).
- **Sesión limitada a la pestaña:** la sesión y la canasta se guardan en `sessionStorage`, no en `localStorage`. Sobreviven a recargar o a ir a Privacidad y volver, y se borran al cerrar la pestaña: cada visita nueva parte en el login. Cerrar sesión vacía también la canasta.
- **Validación estricta de entrada** con Pydantic: largos máximos, valores permitidos (roles, planes, frecuencias) y rangos numéricos.
- **Rate limiting** por IP real (detrás del proxy de Render) y por cuenta en login, registro y verificación, guardado en la base de datos para que sobreviva a reinicios.
- **Verificación de cuenta por correo:** código de 6 dígitos generado con `secrets`, vigente por 30 minutos, con reenvío y sin revelar qué correos están registrados.
- **Cuentas demo protegidas:** sus credenciales son públicas, así que no se pueden borrar, cambiarles la contraseña ni eliminar sus árboles.
- **Integridad de cupos:** la reserva se hace con un `UPDATE` condicional atómico, y un índice único impide que un usuario ocupe dos cupos del mismo árbol.
- **Cabeceras de seguridad** (`nosniff`, `X-Frame-Options`, `Referrer-Policy`, `no-store`) y **CORS** restringido a los orígenes, métodos y cabeceras que usa el frontend.

**Registro, monitoreo y alertas**

El backend registra cada evento de seguridad en la tabla `eventos_seguridad` (30 días) y
como una línea JSON en los logs del servidor: logins fallidos y exitosos, tokens
falsificados, accesos a datos ajenos, bloqueos por rate limit, intentos de XSS, ataques a
las cuentas demo, cambios de contraseña y cuentas eliminadas. El navegador también reporta
cuando la CSP bloquea código (`POST /api/seguridad/csp`).

Cuando se cumple una regla se envía una **alerta** por correo y/o webhook, como máximo una
vez por hora por regla y origen:

| Regla | Se dispara con |
|---|---|
| Posible fuerza bruta | 5 logins fallidos contra una cuenta en 15 min |
| Tokens falsificados | 5 tokens inválidos desde una IP en 10 min |
| Acceso a datos ajenos | 5 accesos denegados desde una IP en 10 min |
| Ataque a cuentas demo | 3 intentos de modificarlas desde una IP en 30 min |
| Rate limit superado | 1 bloqueo |
| Intento de XSS | 1 texto con `<` o `>` |
| Bloqueo de CSP | 1 reporte del navegador |

El **panel de monitoreo** (`frontend/monitoreo.html`) muestra los eventos de las últimas
24 horas, por tipo y por severidad, y se actualiza cada 30 segundos. Pide el
`MONITOREO_TOKEN`, que se guarda solo en memoria.

**Ley N° 21.719 de Protección de Datos Personales (Chile)**

El proyecto incorpora desde el diseño los requisitos de la ley, vigente desde el 1 de
diciembre de 2026: consentimiento explícito al registrarse, [política de
privacidad](https://arrobaaas.github.io/agro-colab/privacidad.html) y los derechos de
acceso, rectificación y eliminación desde el perfil del usuario.

<details>
<summary><b>Registro de actividades de tratamiento, DPO y protocolo de brechas</b></summary>

**Delegado de Protección de Datos (DPO):** Nicolas Reyes Orellana · [@arrobaaas](https://github.com/arrobaaas)

| Dato | Finalidad | Base legal | Plazo |
|---|---|---|---|
| Nombre | Identificar al usuario | Consentimiento | Hasta eliminación |
| Email | Autenticación y comunicaciones | Consentimiento | Hasta eliminación |
| Contraseña (hash bcrypt) | Autenticación | Consentimiento | Hasta eliminación |
| Teléfono | Contacto de entrega | Consentimiento | Hasta eliminación |
| Dirección | Despacho de productos | Consentimiento | Hasta eliminación |
| Suscripciones | Gestión de adopciones | Contrato | Hasta eliminación |
| Pedidos | Gestión logística | Contrato | Hasta eliminación |
| IP, correo y acción en eventos de seguridad | Detectar y responder a ataques | Interés legítimo (seguridad del servicio) | 30 días |

| Derecho (Art. 20) | Cómo ejercerlo |
|---|---|
| Acceso | Perfil de usuario |
| Rectificación | Perfil de usuario |
| Eliminación | Botón "Eliminar mi cuenta" en el perfil |
| Oposición | Contactar al DPO |

**Protocolo de notificación de brechas (Art. 22):** notificación a la Agencia de Protección
de Datos dentro de 72 horas, aviso directo a los usuarios afectados, documentación del
incidente y de las medidas correctivas.

**Evaluación de impacto (DPIA):** riesgo bajo. No se tratan datos sensibles, el volumen es
pequeño (prototipo académico) y las medidas mitigantes son el hash de contraseñas, el
consentimiento y el derecho a eliminación.

**Encargados del tratamiento:** GitHub Pages ([términos](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)) y Render ([términos](https://render.com/legal/terms)).

</details>

---

## 🗺 Hoja de ruta

- [x] Catálogo de árboles y adopción con control de cupos
- [x] Planes de abastecimiento con logística particular y comercial
- [x] Catálogo cerrado de especies con imágenes verificadas
- [x] Panel del comprador y panel del agricultor
- [x] Persistencia con SQLAlchemy y SQLite
- [x] Autenticación con tokens y autorización por recurso
- [x] Pasarela de pago (simulada)
- [ ] Migración a PostgreSQL
- [x] Envío real del correo de verificación (Brevo) y recuperación de contraseña
- [ ] Fotos propias del productor con flujo de moderación
- [x] Pruebas automatizadas e integración continua

---

## 🤖 Declaración de uso de Inteligencia Artificial

En este proyecto se usaron herramientas de IA como **apoyo**. Las decisiones de diseño,
la revisión del código y la responsabilidad sobre el resultado son del equipo.

| Herramienta | Período | Uso |
|---|---|---|
| **Gemini** (Google) | Septiembre 2026 | Estructura y redacción de los argumentos comerciales del informe |
| **ChatGPT** (OpenAI) | Septiembre 2026 | Comparación técnica de lenguajes (Node.js vs Python) y apoyo en el código del prototipo inicial |
| **Claude Code** (Anthropic, modelo Claude Opus 5.5) | Octubre 2026 | Asistente de programación en la terminal: revisión de código en busca de fallas, rediseño de las tarjetas de suscripción, implementación de la autenticación con tokens y la autorización por recurso, corrección de la condición de carrera en la reserva de cupos, y redacción de esta documentación y de los avisos de licencias |

**Cómo se verificó**
- Las cifras sobre el abandono del campo y las tendencias de consumo en Chile se contrastaron a mano con las fuentes primarias del Ministerio de Agricultura y con las revistas sectoriales citadas en el informe.
- Los cambios de código propuestos por la IA se revisaron antes de incorporarlos. Los de seguridad se probaron contra la API en ejecución: peticiones sin token o con token falso, acceso a recursos de otros usuarios y compras simultáneas del último cupo.

---

## 👥 Equipo

- Joaquin Alveal Santos - [@Joaquin-alveal](https://github.com/Joaquin-Alveal)
- Matias Gonzalez Paredes - [@Skt1-Ctrl](https://github.com/SKT1-Ctrl)
- Nicolas Reyes Orellana - [@arrobaaas](https://github.com/arrobaaas)

Proyecto semestral · INGT1003 Arquitectura de Desarrollo (Móvil y Web) · Universidad Mayor · 2026

---

## 📄 Licencia

El código se distribuye bajo la [licencia MIT](LICENSE). Las fotografías del catálogo
conservan sus licencias originales de Wikimedia Commons (CC BY, CC BY-SA o dominio
público), con autor y licencia registrados por imagen. Las dependencias, servicios y
créditos de cada foto están en [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
