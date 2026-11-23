# Manual de uso e instalación · Agro-Colab

> 📄 **Versión para imprimir y entregar:** [`Manual_de_uso_e_instalacion.pdf`](Manual_de_uso_e_instalacion.pdf), con el
> diseño del informe final y capturas de cada paso. Se genera desde [`fuente/manual.html`](fuente/manual.html) con
> `node docs/guias/fuente/generar_manual.mjs`. Si cambias este archivo, cambia también el HTML.

Este manual permite que una persona que no conoce el proyecto lo instale, lo use y resuelva
los problemas más comunes sin ayuda del equipo. Los pasos se comprobaron el 17 de noviembre
de 2026 clonando el repositorio en una carpeta vacía y siguiéndolos al pie de la letra.

- [1. Usar la versión publicada](#1-usar-la-versión-publicada-sin-instalar-nada)
- [2. Requisitos para instalar](#2-requisitos-para-instalar)
- [3. Instalación paso a paso](#3-instalación-paso-a-paso)
- [4. Datos de prueba](#4-datos-de-prueba)
- [5. Flujo principal: adoptar un árbol](#5-flujo-principal-adoptar-un-árbol)
- [6. Otros recorridos](#6-otros-recorridos)
- [7. Fallas frecuentes y su solución](#7-fallas-frecuentes-y-su-solución)
- [8. Pruebas automatizadas](#8-pruebas-automatizadas)

---

## 1. Usar la versión publicada (sin instalar nada)

Abre **https://arrobaaas.github.io/agro-colab/** e ingresa con una de las cuentas de la
[sección 4](#4-datos-de-prueba).

El frontend está en GitHub Pages y la API en el plan gratuito de Render. Si nadie usó el
servicio en los últimos 15 minutos, **la primera petición puede tardar hasta un minuto**
mientras el servidor despierta. La página empieza a despertarlo apenas se abre, y si una
petición tarda más de 3,5 segundos aparece arriba el aviso **"Despertando el servidor…"**, que se
quita solo cuando responde. Después responde con normalidad.

---

## 2. Requisitos para instalar

| Requisito | Versión | Para qué |
|---|---|---|
| Python | 3.12 o superior | Backend (FastAPI) |
| Git | Cualquiera reciente | Clonar el repositorio |
| Navegador | Chrome, Firefox, Edge o Safari actuales | Frontend |
| PostgreSQL | 16 (opcional) | Solo si no quieres usar SQLite |

No hace falta Node.js: los estilos de Tailwind vienen compilados en el repositorio.
Tampoco hace falta una cuenta de correo: en modo `desarrollo`, el código de verificación
aparece en la consola del servidor.

---

## 3. Instalación paso a paso

Se necesitan **dos terminales**: una para el backend y otra para el frontend.

### Terminal 1 · Backend (http://127.0.0.1:8000)

**Linux y macOS**

```bash
git clone https://github.com/arrobaaas/agro-colab.git
cd agro-colab/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
uvicorn main:app --reload --port 8000 --env-file ../.env
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/arrobaaas/agro-colab.git
cd agro-colab\backend
py -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example ..\.env
uvicorn main:app --reload --port 8000 --env-file ..\.env
```

Está funcionando cuando la consola muestra `Application startup complete.` Con los valores
de `.env.example`:

- Se crea sola una base SQLite en `backend/agrocolab.db`, con las cuentas de demostración y
  tres árboles de ejemplo.
- La documentación interactiva de la API queda en http://127.0.0.1:8000/docs.
- Aparece el aviso `AGROCOLAB_SECRET es la clave de ejemplo...`. En local es normal: solo
  significa que las sesiones se cierran cada vez que se reinicia el servidor.

### Terminal 2 · Frontend (http://localhost:3000)

```bash
cd agro-colab/frontend
python3 -m http.server 3000      # Windows: py -m http.server 3000
```

Abre **http://localhost:3000** en el navegador. El frontend detecta que está en `localhost`
y llama solo a la API local.

Para apagar todo, presiona **Ctrl + C** en cada una de las dos terminales.

### Opcional · PostgreSQL en lugar de SQLite

```bash
createdb agrocolab
psql -d agrocolab -f db/esquema.sql
```

Después, en `.env`, cambia `AGROCOLAB_MOD_MODE=produccion` y define
`DATABASE_URL=postgresql://usuario:clave@localhost:5432/agrocolab`. El servidor no acepta el
modo `desarrollo` con una base de producción. Ver [`db/README.md`](../../db/README.md).

---

## 4. Datos de prueba

Todos los datos son ficticios. Nunca cargues datos reales de personas.

### Cuentas

| Rol | Correo | Contraseña | Botón de rol al ingresar |
|---|---|---|---|
| Comprador | `comprador@agrocolab.cl` | `123` | **Comprador** |
| Agricultor | `agricultor@agrocolab.cl` | `123` | **Agricultor** |
| Administrador | El de `ADMIN_EMAIL` en `.env` | El de `ADMIN_PASSWORD` (12 caracteres o más) | Cualquiera |

La cuenta de administrador no existe hasta que defines esas dos variables y reinicias el
servidor. Nadie puede registrarse como administrador.

Las cuentas de demostración son compartidas en la versión publicada, así que su perfil y su
contraseña no se pueden modificar.

### Tarjetas de la pasarela simulada

La pasarela no mueve dinero y solo acepta estas tarjetas. Con cualquier vencimiento futuro
(por ejemplo `12/29`) y cualquier CVV de 3 dígitos:

| Número | Resultado |
|---|---|
| `4242 4242 4242 4242` | Visa aprobada |
| `5555 5555 5555 4444` | Mastercard aprobada |
| `4000 0000 0000 0002` | Rechazada: fondos insuficientes |
| `4000 0000 0000 9995` | Rechazada: tarjeta bloqueada |

El formulario de pago tiene un botón para cada una, así que no hace falta escribirlas.

### Árboles de ejemplo

Al crear la base se cargan tres árboles del agricultor de demostración, uno por plan
(Básico, Intermedio y Premium). El primero es el **Palto Hass #104**: plan Básico,
5 cupos, $12.000 al mes.

---

## 5. Flujo principal: adoptar un árbol

Este es el recorrido que cierra el ciclo completo: la interfaz llama al servicio, el
servicio guarda en la base de datos y el dato vuelve a la pantalla.

1. En la pantalla de inicio, elige **Comprador**, escribe `comprador@agrocolab.cl` y `123`,
   y presiona **Ingresar**.
2. Presiona **Adoptar un árbol**. Aparece la lista **Árboles disponibles**, con los cupos
   libres de cada árbol.
3. Elige un árbol y confirma con **Agregar a mi canasta**. El contador de la canasta, en la
   cabecera, sube a 1.
4. Abre la canasta y presiona **Pagar $12.000** (el botón muestra el total). En **Pago con tarjeta**, usa el botón
   **Visa aprobada** y presiona **Pagar $…**. El monto lo fija el servidor, no el navegador.
5. Aparece **Pago aprobado**. Presiona **Continuar con el despacho**, completa la dirección,
   la comuna, el celular, el código postal y la frecuencia, y presiona
   **Confirmar destino y registrar pedido**.
6. Presiona **Mi panel**. El árbol adoptado aparece con sus coparticipantes, su cosecha
   estimada y la dirección de despacho.
7. **Recarga la página (F5).** El árbol sigue en el panel, porque quedó guardado en la base
   de datos.

Para comprobar los errores en el mismo recorrido:

- Paga con **Sin fondos**: aparece **Pago no realizado** con el motivo, y no se ocupa ningún
  cupo.
- Intenta adoptar otra vez el mismo árbol: la aplicación avisa que ya tienes un cupo en él.
  Si la petición llega a la API, responde `409 Conflict`.

---

## 6. Otros recorridos

### Comprador

- **Canastas de abastecimiento:** en **Ver canastas**, elige un plan (Huerto Esencial,
  Familiar o Lote Gastronómico B2B). El plan B2B pide razón social y un RUT de empresa válido.
- **Cancelar:** desde **Mi panel** se cancela la suscripción a un árbol (libera el cupo) o un
  plan de abastecimiento.
- **Perfil:** cambia nombre, teléfono, dirección o contraseña (la contraseña nueva exige la
  actual). **Descargar mis datos** entrega una copia de tus datos y **Eliminar cuenta** los
  borra todos después de pedir la contraseña.

### Agricultor

1. Ingresa con **Agricultor**, `agricultor@agrocolab.cl` y `123`.
2. **Tu huerto en cifras** muestra los ingresos por árbol, la ocupación de cupos y las
   adopciones por mes.
3. **Publicar un árbol**: elige la especie del catálogo cerrado, una de sus fotos
   verificadas, la ubicación, el plan, los cupos y el precio, y presiona **Publicar árbol**.
4. En **Mis árboles** se edita o elimina cada árbol, y se ven sus suscriptores con su
   contacto. El agricultor puede expulsar a un suscriptor para liberar su cupo.

### Administrador

Con la cuenta de `ADMIN_EMAIL`, el panel **Cuentas de Agro-Colab** lista todas las cuentas,
con búsqueda y filtro por tipo. Desde el detalle de una cuenta se corrigen sus datos, se la
verifica a mano, se cambia su contraseña o se elimina con todos sus datos.

### Registro de una cuenta nueva

En **¿No tienes cuenta? Regístrate**, completa el formulario y acepta los términos. En modo
`desarrollo`, el código de 6 dígitos aparece en la terminal del backend; en la versión
publicada llega por correo. Escríbelo en **Verifica tu cuenta** y entras directo.

---

## 7. Fallas frecuentes y su solución

Las tres primeras son las que más aparecieron al instalar el proyecto en un equipo limpio.

### 1. `python: orden no encontrada` o `command not found: python`

En Linux y macOS el ejecutable se llama `python3`. Usa `python3 -m venv venv`. En Windows
usa `py`. Dentro del entorno virtual ya activado, `python` sí funciona.

En Windows, si PowerShell no deja ejecutar `Activate.ps1`, corre una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y vuelve a activar el entorno.

### 2. La página carga, pero dice "No hay conexión con el servidor" o "No pudimos cargar los árboles"

El frontend no logra hablar con la API. Revisa, en este orden:

1. **¿El backend está corriendo?** La terminal 1 debe mostrar `Application startup complete.`
   y http://127.0.0.1:8000/api/arboles debe responder una lista.
2. **¿Abriste el frontend con `http://localhost:3000`?** Si abriste `index.html` con doble clic
   (`file://...`) o usaste otro puerto, el navegador bloquea la petición por CORS. En modo
   `desarrollo` la API solo acepta los puertos 3000 y 5173.
3. **¿El `.env` tiene `AGROCOLAB_MOD_MODE=desarrollo`?** En modo `produccion` la API solo
   acepta el frontend publicado en GitHub Pages.
4. **En la versión publicada**, espera un minuto: el servidor de Render puede estar
   despertando (lo indica el aviso de arriba). Después presiona **Intentar de nuevo**.

### 3. "Credenciales inválidas o el rol seleccionado no coincide"

El correo y la contraseña pueden estar bien, pero el botón de rol no corresponde a la cuenta.
`comprador@agrocolab.cl` entra solo con **Comprador** y `agricultor@agrocolab.cl` solo con
**Agricultor**. Después de 8 intentos fallidos desde el mismo equipo en 5 minutos, el login
responde "Demasiados intentos. Intenta más tarde." para frenar la fuerza bruta: espera 5 minutos y vuelve a
intentar.

### Otras fallas

| Síntoma | Causa | Solución |
|---|---|---|
| `[Errno 98] address already in use` (en Windows, `[Errno 10048]`) al levantar el backend | Otro proceso usa el puerto 8000, a menudo un uvicorn anterior | Ciérralo con Ctrl+C en su terminal, o usa otro puerto y ajusta `API_URL` en `frontend/js/config.js` |
| "Esta pasarela es de prueba y solo acepta las tarjetas de prueba" | Se escribió una tarjeta que no está en la tabla de la sección 4 | Usa uno de los botones de tarjeta de prueba del formulario |
| La sesión se cierra cada vez que se reinicia el backend | `AGROCOLAB_SECRET` es la clave de ejemplo y se usa una aleatoria | Genera una con `python3 -c "import secrets; print(secrets.token_hex(32))"` y ponla en `.env` |
| `AGROCOLAB_MOD_MODE=desarrollo no se permite con una base de producción` | Se definió `DATABASE_URL` en modo `desarrollo` | Deja `DATABASE_URL` vacía para usar SQLite, o cambia a `produccion` |
| Un cambio en el código no se ve en la página | El navegador usa archivos guardados en caché | Recarga con **Ctrl + F5** |
| Quiero partir con la base limpia | Los datos de pruebas anteriores siguen en SQLite | Detén el backend, borra `backend/agrocolab.db` y vuelve a levantarlo |
| No aparece el panel de administración | No se definieron `ADMIN_EMAIL` y `ADMIN_PASSWORD`, o la contraseña tiene menos de 12 caracteres | Defínelas en `.env` y reinicia el backend: la consola dice `[admin] cuenta de administrador creada` |

---

## 8. Pruebas automatizadas

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest
```

Las pruebas usan una base temporal y nunca envían correos. GitHub Actions las ejecuta en cada
*push* y en cada *pull request*, contra SQLite y contra PostgreSQL. Para correrlas en local
contra PostgreSQL, define `PRUEBAS_DB_URL` (ver `.env.example`).
