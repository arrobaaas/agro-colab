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
│       ├── agricultor.js   # Vista de agricultor: dashboard y subida de árboles
│       ├── perfil.js       # Modal de perfil de usuario
│       └── app.js          # Arranque: decide la vista inicial
├── backend/                # Lógica del servidor, API y controladores
│   ├── main.py             # API FastAPI con endpoints REST
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
| POST | `/api/arboles` | Crea un nuevo árbol en el catálogo (solo agricultores). |
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

## Ejecución del Proyecto

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

---

## Equipo de Desarrollo

- Joaquin Alveal Santos
- Matias Gonzalez Paredes
- Nicolas Reyes Orellana
