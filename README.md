# Agro-Colab

Proyecto Semestral - INGT1003 Arquitectura de Desarrollo (Móvil y Web)

**Promesa de Valor:** Financia la cosecha, asegura tu abastecimiento. Agro-Colab ofrece trazabilidad directa del huerto a la mesa, con dos líneas de producto: la adopción de árboles frutales, donde el consumidor financia y es copropietario de la producción de un árbol concreto, y el abastecimiento, donde contrata canastas de cosecha con entrega programada. En ambas, el financiamiento llega directo al pequeño agricultor, sin intermediarios.

---

## Resumen del Proyecto

Agro-Colab es una plataforma web que conecta a las personas con la agricultura a través de dos líneas de producto complementarias, ambas orientadas a eliminar al intermediario y a acercar el campo a la ciudad:

1. **Adopción de árboles frutales:** el cliente compra un cupo sobre un árbol concreto y se convierte en copropietario de su producción de temporada. El plan define cuántos copartícipes comparten el árbol.

2. **Abastecimiento de canastas:** el cliente contrata una canasta de cosecha ya definida (fruta en kilos, con frecuencia de entrega) y la recibe en su domicilio o su local comercial.

El denominador común de ambas líneas es la trazabilidad: cada pedido se registra con un código de seguimiento que lo vincula al huerto de origen.

---

## Línea 1: Planes de Adopción

Se aplican sobre un árbol del catálogo. La unidad es el cupo y el stock es el número de copartícipes disponibles:

- **Plan Básico:** el usuario comparte el árbol y su producción de temporada con 5 personas.
- **Plan Intermedio:** el usuario comparte el árbol y su producción con 3 personas.
- **Plan Premium:** el usuario es dueño exclusivo del 100% de lo que produzca el árbol en la temporada.

En el prototipo, cada árbol del catálogo declara su plan, y seleccionar un plan filtra el catálogo para mostrar solo los árboles disponibles de ese plan.

### Catálogo de Especies e Imágenes

El nombre y la foto de un árbol publicado no son texto libre. El backend mantiene un **catálogo cerrado de 12 especies frutales** (`backend/catalogo.py`), cada una con tres fotografías verificadas de la fruta y del árbol:

| Especie | Identificador | Fotos |
|---|---|---|
| 🥑 Palto Hass | `palto_hass` | 3 |
| 🍊 Naranjo Valencia | `naranjo_valencia` | 3 |
| 🍋 Limonero Eureka | `limonero_eureka` | 3 |
| 🟠 Mandarino | `mandarino` | 3 |
| 🌳 Ciruelo | `ciruelo` | 3 |
| 🍒 Cerezo | `cerezo` | 3 |
| 🍏 Manzano | `manzano` | 3 |
| 🍑 Duraznero | `duraznero` | 3 |
| 🍐 Membrillo | `membrillo` | 3 |
| 🥝 Kiwi | `kiwi` | 3 |
| 🍓 Frutilla | `frutilla` | 3 |
| 🫒 Olivo | `olivo` | 3 |

El flujo de publicación funciona así:

1. El agricultor elige la **especie** en un selector. El formulario muestra su descripción y arma el nombre en vivo: "Palto Hass" + "#104" = **"Palto Hass #104"**.
2. Se despliega la **galería** con las tres fotos de esa especie. El Agricultor marca una y se muestra el crédito (autor, licencia y enlace a Wikimedia Commons).
3. Al enviar, el **servidor vuelve a validar**: la especie debe existir en el catálogo y la URL de la imagen debe pertenecer a esa especie. Un `POST` hecho a mano con la foto de otra fruta también es rechazado.

La columna `especie` del modelo `Arbol` guarda el identificador del catálogo, `identificador` el número del árbol en el huerto y `imagen_origen` el origen de la foto (`galeria` / `propia`, reservado para el flujo de revisión). Los árboles publicados antes de este cambio siguen funcionando: su especie se deduce del nombre y al editarlos se les vuelve a ofrecer la galería.

---

## Línea 2: Planes de Abastecimiento

Se aplican sobre canastas de cosecha. La unidad son los kilos por entrega y cada plan define frecuencia y destino:

- **Plan Dúo:** canasta quincenal de 2.5 kg de Palta Hass y 3.0 kg de cítrico, para 1 a 2 personas.
- **Plan Familiar:** canasta quincenal de 5.0 kg de Palta Hass y 6.0 kg de fruta de temporada, para 3 a 5 personas, con participación en 2 árboles.
- **Plan B2B:** lote semanal de 25 kg, facturable, con calibre adaptado y certificado de origen.

Al seleccionar un plan de esta línea, el usuario pasa al selector logístico, que define si el despacho es particular o comercial.

---

## Arquitectura del Sistema

Siguiendo los lineamientos del curso (Unidad 1), el proyecto se estructura bajo un Modelo Cliente-Servidor y una Arquitectura de 3 Capas:

- **Capa de Presentación (Frontend):** Interfaz responsive (Mobile-first) enfocada en la experiencia del usuario (UI/UX), construida con HTML5, CSS3, JavaScript, Tailwind CSS y Font Awesome.
- **Capa de Negocio (Backend):** API REST que maneja la lógica de las suscripciones, el control de stock (cuántos cupos le quedan a un árbol) y la validación de usuarios, utilizando el patrón MVC.
- **Capa de Datos:** En esta primera etapa, la persistencia se maneja mediante estructuras de datos en memoria (listas de Python). Para futuras versiones, se planea migrar a una base de datos relacional (PostgreSQL).

---

## Funcionalidades Principales

- **Catálogo Interactivo:** Exploración de árboles frutales disponibles, con filtro por plan de adopción (Básico, Intermedio, Premium) y estado de cupos ocupados en tiempo real.
- **Catálogo Cerrado de Especies:** El productor no escribe libremente el nombre del árbol ni sube cualquier foto. Escoge la especie de una lista curada (Palto Hass, Naranjo Valencia, Limonero Eureka, Mandarino, Ciruelo, Cerezo, Manzano, Duraznero, Membrillo, Kiwi, Frutilla y Olivo) y el sistema arma el nombre combinando la especie con el número del árbol en el huerto (por ejemplo, "Palto Hass #104").
- **Galería de Imágenes Verificadas:** Junto a cada especie hay un set curado de fotos de la fruta y del árbol. El productor elige una de ellas y no se puede publicar con una imagen ajena a la especie, lo que garantiza que el catálogo nunca muestre, por ejemplo, un limonero con foto de palto. La validación ocurre en el servidor, no solo en el formulario.
- **Flujo de Suscripción:** Selección de plan de adopción sobre un árbol, con validación de cupos disponibles en el servidor.
- **Flujo de Abastecimiento:** Selección de plan de canasta (Dúo, Familiar, B2B) y configuración del destino logístico, particular o comercial, con generación de código de seguimiento.
- **Carrito de Compras:** Los productos adquiridos se agreguen al carrito con estado "Comprado" y opción de cancelar.
- **Perfil de Usuario:** Edición de nombre, correo, teléfono, dirección y contraseña.
- **Dashboard del Agricultor:** Estadísticas de árboles publicados, suscriptores e ingresos estimados.
- **Gestión de Agricultores:** Interfaz para que los productores publiquen sus árboles y actualicen el estado de crecimiento.

---

## Estructura del Proyecto

```
agro-colab/
├── frontend/               # Interfaz cliente (SPA - Single Page Application)
│   ├── index.html          # Punto de entrada único: login + vistas por rol
│   ├── css/
│   │   └── styles.css      # Estilos personalizados (Tailwind por CDN + clases propias)
│   └── js/
│       ├── config.js       # URL de la API, claves de sesión, vistas por rol
│       ├── ui.js           # Alertas, formato de montos, estados visuales
│       ├── api.js          # Consumo de la API (fetch)
│       ├── auth.js         # Sesión en localStorage
│       ├── views.js        # Router de vistas y navbar
│       ├── login.js        # Formulario de acceso
│       ├── parcelas.js     # Vista de comprador: adopción, abastecimiento y logística
│       ├── catalogo.js     # Catálogo de especies y galería de imágenes
│       ├── agricultor.js   # Vista de agricultor: dashboard y subida de árboles
│       ├── perfil.js       # Modal de perfil de usuario
│       └── app.js          # Arranque: decide la vista inicial
├── backend/                # Lógica del servidor, API y controladores
│   ├── main.py             # API FastAPI con endpoints REST
│   ├── catalogo.py         # Catálogo cerrado de especies con sus fotos verificadas
│   ├── database.py         # Modelos SQLAlchemy y migraciones de esquema
│   └── requirements.txt    # Dependencias Python (FastAPI, Uvicorn, Pydantic)
├── docs/                   # Documentación del proyecto
├── db/                     # Modelo de datos y scripts (Próximamente Hito 2)
├── .env.example            # Archivo de configuración base sin datos reales
└── README.md               # Documentación principal del proyecto
```

---

## API REST - Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/arboles` | Obtiene el catálogo completo de árboles disponibles para adopción. |
| GET | `/api/especies` | Devuelve el catálogo cerrado de especies con las fotos verificadas que el agricultor puede usar. |
| POST | `/api/arboles` | Crea un nuevo árbol en el catálogo (solo agricultores). Valida que la especie exista y que la imagen pertenezca a esa especie. |
| PUT | `/api/arboles/{id}` | Actualiza un árbol publicado, con las mismas validaciones de especie e imagen. |
| POST | `/api/suscribir` | Registra una suscripción de un usuario a un árbol. |
| POST | `/api/cancelar-suscripcion` | Cancela una suscripción y descuenta el cupo del árbol. |
| POST | `/api/login` | Autentica a un usuario (comprador o agricultor). |
| POST | `/api/pedidos` | Registra un pedido de abastecimiento con datos de logística. |
| GET | `/api/pedidos` | Obtiene la lista de pedidos registrados. |
| PUT | `/api/perfil` | Actualiza el perfil del usuario autenticado. |

---

## Flujo de Acceso

La aplicación muestra primero el login. Al entrar, cada rol ve la vista que le corresponde según `VISTAS_POR_ROL` en `js/config.js`; hoy comprador y agricultor tienen vistas separadas. El cambio de vista ocurre en el mismo documento, sin recargas ni navegación entre páginas.

**Cuentas de demostración:**
- Comprador: `comprador@agrocolab.cl` / `123`
- Agricultor: `agricultor@agrocolab.cl` / `123`

---

## Ver en vivo

La página está disponible en línea:

**URL:** [https://arrobaaas.github.io/agro-colab/](https://arrobaaas.github.io/agro-colab/)

- **Frontend:** GitHub Pages (hosting estático, siempre activo)
- **Backend:** Render (API REST, siempre activo)

---

## Ejecución local del Proyecto

**Backend (puerto 8000):**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Frontend (puerto 3000):**
```bash
cd frontend
python3 -m http.server 3000
```

Abre en el navegador: `http://localhost:3000`

---

## Pendientes para el Hito 2

Estos puntos están fuera del alcance del prototipo actual y aún no existen en el código:

- Pasarela de pago simulada en el flujo de suscripción.
- Dashboard de Usuario con el estado del árbol adoptado, el avance de la cosecha y la gestión de suscripciones.
- Capa de datos persistente: hoy el backend usa bases simuladas en memoria.
- Autenticación en los endpoints protegidos: hoy solo el login valida credenciales.
- **Fotos propias del productor:** hoy la imagen sale siempre de la galería curada. Permitir que el agricultor suba la foto de su árbol requiere un flujo de moderación (estado `pendiente` en la tabla, revisión antes de publicarla y reemplazo por la foto del catálogo mientras tanto), para no perder la garantía de que la imagen corresponde a la especie.

---

## Protección de Datos (Ley 21.719)

Agro-Colab cumple con la Ley N° 21.719 de Protección de Datos Personales de Chile (vigente desde el 1 de diciembre de 2026).

**Página de privacidad:** [https://arrobaaas.github.io/agro-colab/privacidad.html](https://arrobaaas.github.io/agro-colab/privacidad.html)

### Delegado de Protección de Datos (DPO)

- **Nombre:** Nicolas Reyes Orellana
- **Contacto:** [@arrobaaas](https://github.com/arrobaaas)

### Registro de Actividades de Tratamiento

| Dato | Finalidad | Base legal | Plazo |
|---|---|---|---|
| Nombre | Identificar al usuario | Consentimiento | Hasta eliminación |
| Email | Autenticación y comunicaciones | Consentimiento | Hasta eliminación |
| Contraseña (hash bcrypt) | Autenticación | Consentimiento | Hasta eliminación |
| Teléfono | Contacto de entrega | Consentimiento | Hasta eliminación |
| Dirección | Despacho de productos | Consentimiento | Hasta eliminación |
| Suscripciones | Gestión de adopciones | Contrato | Hasta eliminación |
| Pedidos | Gestión logística | Contrato | Hasta eliminación |

### Medidas de seguridad implementadas

- **Contraseñas hasheadas** con bcrypt (nunca se guardan en texto plano)
- **Consentimiento explícito** obligatorio antes de registrar datos
- **Derecho a la eliminación:** puedes borrar tu cuenta y todos tus datos desde el perfil
- **Acceso restringido:** solo el usuario puede ver y modificar sus datos
- **HTTPS:** Todas las comunicaciones van cifradas en producción

### Protocolo de Notificación de Brechas (Art. 22)

- Notificación a la **Agencia de Protección de Datos** dentro de **72 horas**
- Información directa al usuario afectado
- Documentación del incidente y medidas correctivas
- Contacto del DPO para reportar incidentes

### Evaluación de Impacto (DPIA)

Realizada para tratamientos de alto riesgo:
- **Riesgo:** Bajo
- **Datos sensibles:** No se tratan datos de salud, origen étnico, etc.
- **Volumen:** Pequeño (prototipo académico)
- **Medidas mitigantes:** Hash de contraseñas, consentimiento, derecho a eliminación

### Acuerdos de Tratamiento de Datos (DPA)

| Proveedor | Tipo | DPA |
|---|---|---|
| GitHub Pages | Hosting estático | [GitHub Terms](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) |
| Render | Hosting backend | [Render Terms](https://render.com/legal/terms) |

### Tus derechos (Art. 20 Ley 21.719)

| Derecho | Cómo ejercerlo |
|---|---|
| **Acceso** | Perfil de usuario |
| **Rectificación** | Perfil de usuario |
| **Eliminación** | Botón "Eliminar mi cuenta" en el perfil |
| **Oponerte** | Contactar al DPO |

---

## Licencias y Fuentes

### Licencia del Proyecto

Este proyecto se distribuye bajo la **MIT License**. Puedes usar, modificar y distribuir el código libremente, siempre que incluyas la licencia original.

### Dependencias y sus Licencias

| Dependencia | Licencia | Fuente |
|---|---|---|
| FastAPI | MIT | https://github.com/tiangolo/fastapi |
| Pydantic | MIT | https://github.com/pydantic/pydantic |
| Uvicorn | BSD-3-Clause | https://github.com/encode/uvicorn |
| SQLAlchemy | MIT | https://github.com/sqlalchemy/sqlalchemy |
| Tailwind CSS | MIT | https://github.com/tailwindlabs/tailwindcss |
| Font Awesome | CC BY 4.0 / MIT | https://github.com/FortAwesome/Font-Awesome |

### Recursos Externos

| Recurso | Fuente | Licencia |
|---|---|---|
| Imágenes de árboles y frutas | Wikimedia Commons | CC BY / CC BY-SA / dominio público (atribución por foto en la galería) |
| Íconos | Font Awesome | CC BY 4.0 / MIT |
| Framework CSS | Tailwind CSS | MIT |
| Hosting frontend | GitHub Pages | https://docs.github.com/en/site-policy/github-terms/github-terms-of-service |
| Hosting backend | Render | https://render.com/legal/terms |
| Autocompletado de direcciones | Photon (Komoot) | [OpenStreetMap ODbL](https://www.openstreetmap.org/copyright) |
| Datos de direcciones | OpenStreetMap | [ODbL](https://opendatacommons.org/licenses/odbl/) |

### Créditos de las fotos del catálogo

Las 36 imágenes del catálogo de especies provienen de Wikimedia Commons y se eligieron revisando una por una que correspondieran a la fruta o al árbol de la especie. Cada foto guarda su atribución (autor, licencia y enlace al archivo original), que se muestra bajo la galería en el formulario del agricultor. Se evitaron las licencias GFDL y "sin restricciones" por exigir o no permitir el uso previsto.

| Especie | Autores |
|---|---|
| Palto Hass | Treysam, B.navez, USDAgov |
| Naranjo Valencia | Auli Raha, Ivar Leidus, Zeynel Cebeci |
| Limonero Eureka | Vyacheslav Argenberg, André Karwath, *fiedler* |
| Mandarino | Joe Ravi, Ivar Leidus, David J. Stang |
| Ciruelo | Jonathan Billinger, Franca, Xosema |
| Cerezo | Netol, Schueler-Design, Chris Light |
| Manzano | Dinnye, Ashish Gupta, Noah Wulf |
| Duraznero | Takkk, Jack Dykinga (USDA), Allagash Brewing |
| Membrillo | Lazaregagnidze, SAplants |
| Kiwi | Luc Viatour, Pseudopanax, André Karwath |
| Frutilla | Incnis Mrsi, Thomas Wolf, Ivar Leidus |
| Olivo | David Perez, Dietmar Rabich |

### Autocompletado de Direcciones

El formulario de logística usa **Photon** (https://photon.komoot.io/) para sugerir direcciones reales mientras el usuario escribe. Photon es un geocodificador open source basado en **OpenStreetMap**.

El mismo autocompletado se usa en el **panel del agricultor**, en el campo "Ubicación" tanto del formulario de publicación como del modal de edición: el productor escribe el lugar del huerto y elige entre las sugerencias, en vez de describirlo a mano. Así la ubicación queda en un formato uniforme ("Curicó, Región del Maule") y comparable entre los árboles del catálogo.

- **Sin API key** requerida
- **Sin geolocalización** del dispositivo
- **Gratuito** y open source
- Los datos de direcciones están bajo licencia **ODbL** de OpenStreetMap

El repositorio `react-google-maps-api` fue evaluado pero descartado porque:
- Es para React (el proyecto usa JavaScript vanilla)
- Requiere API key de Google Maps con costo
- La versión 3.x es software comercial

### Declaración de Uso de Inteligencia Artificial

Durante el desarrollo de este proyecto, el equipo utilizó herramientas de Inteligencia Artificial como apoyo en la fase de investigación, redacción y generación de código.

**Herramientas utilizadas:**
- Gemini (Google)
- ChatGPT (OpenAI)

**Fases en las que se aplicó:**
- Estructuración de la redacción de los argumentos comerciales
- Ordenamiento de la estructura del documento
- Contraste de las desventajas técnicas de los lenguajes evaluados (Node.js vs Python)
- Apoyo en la generación de código del prototipo inicial

**Método de verificación:**
Las cifras y problemáticas sugeridas por la IA respecto al abandono del campo y las tendencias de consumo en Chile fueron validadas y contrastadas manualmente leyendo las fuentes primarias del Ministerio de Agricultura y revistas sectoriales citadas en la bibliografía.

**Fecha de uso:** Septiembre de 2026

---

## Equipo de Desarrollo

- Joaquin Alveal Santos - [@Joaquin-alveal](https://github.com/Joaquin-Alveal)
- Matias Gonzalez Paredes - [@Skt1-Ctrl](https://github.com/SKT1-Ctrl)
- Nicolas Reyes Orellana - [@arrobaaas](https://github.com/arrobaaas)
