# Bitácora de decisiones · Agro-Colab

Registro de las decisiones técnicas del proyecto, desde el prototipo del Hito 1 hasta el
producto del Hito 3. Cada entrada indica la fecha, qué se decidió, qué alternativas se
evaluaron, por qué se eligió una y **qué salió mal**. Las fechas salen del historial de Git
(`git log --date=short`), y las cifras, de las mediciones del documento técnico del Hito 2.

| Estado | Significado |
|---|---|
| ✅ Vigente | La decisión sigue en el código entregado |
| 🔁 Reemplazada | Una entrada posterior la cambió (se indica cuál) |

---

## Resumen

| # | Fecha | Decisión | Estado |
|---|---|---|---|
| D01 | 2026-09-09 | Python con FastAPI para el backend | ✅ Vigente, con otro motivo |
| D02 | 2026-09-09 | Aplicación de página única en JavaScript, sin framework | ✅ Vigente |
| D03 | 2026-09-09 | Datos en listas dentro del proceso | 🔁 Reemplazada por D04 |
| D04 | 2026-10-06 | SQLAlchemy con SQLite | 🔁 Reemplazada en producción por D12 |
| D05 | 2026-10-06 | El agricultor sube su propia foto PNG | 🔁 Reemplazada por D08 |
| D06 | 2026-10-19 | GitHub Pages para el frontend y Render para la API | ✅ Vigente |
| D07 | 2026-10-19 | Ley 21.719 desde el diseño: bcrypt, consentimiento y eliminación | ✅ Vigente |
| D08 | 2026-10-21 | Catálogo cerrado de 12 especies con fotos verificadas | ✅ Vigente |
| D09 | 2026-10-26 | Adoptar exige pagar, a través de la canasta | ✅ Vigente |
| D10 | 2026-10-29 | Tokens firmados con HMAC-SHA256 y autorización por recurso | ✅ Vigente |
| D11 | 2026-10-29 | Reserva atómica de cupos | ✅ Vigente |
| D12 | 2026-10-30 | PostgreSQL en producción, SQLite en local | ✅ Vigente |
| D13 | 2026-10-30 | Pasarela de pago simulada | ✅ Vigente |
| D14 | 2026-10-30 | Pruebas automatizadas e integración continua en dos motores | ✅ Vigente |
| D15 | 2026-10-31 | Administrador creado solo desde variables del servidor | ✅ Vigente |
| D16 | 2026-11-04 | Monolito modular | ✅ Vigente |
| D17 | 2026-11-04 | Contrato HTTP con un código por resultado | ✅ Vigente |
| D18 | 2026-11-04 | Capas reales: routers, services y repositories | ✅ Vigente |
| D19 | 2026-11-09 | Endurecimiento de seguridad tras la revisión | ✅ Vigente |
| D20 | 2026-11-10 | Auditoría de seguridad: hallazgos AC-01 a AC-44 | ✅ Vigente |
| D21 | 2026-11-10 | Un solo pago para toda la canasta | ✅ Vigente |
| D22 | 2026-11-17 | Instalación en un equipo limpio y errores en lenguaje de usuario | ✅ Vigente |
| D23 | 2026-11-17 | Eliminar una cuenta devuelve sus cupos | ✅ Vigente |
| D24 | 2026-11-17 | Tratamiento de errores no previstos, de punta a punta | ✅ Vigente |

---

## Detalle

### D01 · Python con FastAPI para el backend · 2026-09-09

- **Alternativas:** Node.js con Express (Hito 1), y Django.
- **Por qué:** el Hito 1 eligió FastAPI por su rendimiento asíncrono y por la sintaxis
  accesible de Python para el equipo.
- **Qué salió mal:** el argumento asíncrono no se cumplió. Ninguna ruta usa `async def`,
  porque el acceso a datos con SQLAlchemy es síncrono y FastAPI ejecuta esas rutas en un
  grupo de hilos.
- **Cómo se resolvió:** la decisión se mantuvo, pero se justificó con lo que de verdad
  aportó: la validación tipada de Pydantic, la documentación automática en `/docs` y la
  división de la API por dominios. Se declaró en el Hito 2.

### D02 · Aplicación de página única en JavaScript, sin framework · 2026-09-09

- **Alternativas:** una aplicación multipágina, o un framework como React.
- **Por qué:** el comprador recorre catálogo, canasta, pago y panel sin recargar, y la
  sesión debe mantenerse entre vistas. Sin framework no hay paso de compilación, y el sitio se
  publica tal cual en GitHub Pages.
- **Qué salió mal:** sin un framework, el orden de carga de los scripts y los `onclick` en
  el HTML causaron errores: la aplicación nunca llamaba a `app.init()` (29 oct) y los botones
  del login dejaban de responder (28 oct).
- **Cómo se resolvió:** servicios por módulo en `frontend/js/`, un router de vistas
  (`views.js`) y delegación de eventos con `data-accion` (`acciones.js`), sin JavaScript en
  línea. Esto además permitió una CSP sin `'unsafe-inline'`.

### D03 · Datos en listas dentro del proceso · 2026-09-09

- **Alternativa:** una base de datos desde el primer día.
- **Por qué:** el prototipo del Hito 1 solo necesitaba mostrar el recorrido.
- **Qué salió mal:** los datos se perdían en cada reinicio, y la pauta del Hito 2 exige
  persistencia real.
- **Reemplazada por:** D04.

### D04 · SQLAlchemy con SQLite · 2026-10-06

- **Alternativas:** escribir SQL a mano, o partir directamente con PostgreSQL.
- **Por qué:** SQLite se levanta sin instalar nada, y el ORM permite usar el mismo código con
  otro motor más adelante.
- **Qué salió mal:** en Render el disco no es persistente, así que la base SQLite se borraba
  en cada despliegue. Además, `create_all` no modifica tablas existentes: el 19 de octubre
  hubo que forzar la recreación de la base para agregar campos.
- **Reemplazada en producción por:** D12. SQLite sigue en local y en las pruebas.

### D05 · El agricultor sube su propia foto PNG · 2026-10-06

- **Alternativa:** un catálogo de imágenes controlado por el sistema.
- **Por qué:** era lo más rápido de construir.
- **Qué salió mal:** cualquier imagen podía representar a cualquier árbol, y eso contradice la
  trazabilidad que promete el producto.
- **Reemplazada por:** D08.

### D06 · GitHub Pages para el frontend y Render para la API · 2026-10-19

- **Alternativas:** un servidor propio, o servir el frontend desde la misma API.
- **Por qué:** los dos tienen plan gratuito y se despliegan con un `push`, sin administrar
  servidores.
- **Qué salió mal:** ese mismo día hubo cinco correcciones seguidas: bcrypt no se instalaba en
  Render, la base no tenía los campos nuevos y la raíz del sitio no apuntaba al frontend. Para
  recrear la base se publicó el endpoint `/api/admin/reiniciar-bd`, **sin autenticación**. El
  29 de octubre también hubo que permitir el origen de GitHub Pages en CORS.
- **Cómo se resolvió:** el endpoint de reinicio se eliminó el 27 de octubre, en la
  reorganización del backend. La base se recrea con el script `db/esquema.sql` y nunca con una
  ruta pública. **Costo que se asume:** en el plan gratuito, la primera petición después de
  15 minutos sin uso demora hasta un minuto. El frontend lo explica en el mensaje de error.

### D07 · Ley 21.719 desde el diseño · 2026-10-19

- **Alternativa:** agregar la privacidad al final del semestre.
- **Por qué:** la ley entra en plena vigencia el 1 de diciembre de 2026, dentro del semestre, y
  el sistema trata nombre, correo, teléfono y dirección.
- **Qué salió mal:** el 21 de octubre el login respondía `500`. Las contraseñas de las cuentas
  ya creadas seguían en texto plano, y bcrypt no podía compararlas.
- **Cómo se resolvió:** se recrearon las cuentas con su hash. Hoy hay consentimiento explícito
  con la versión de la política guardada, eliminación de la cuenta (que pide la contraseña),
  descarga de los datos propios y registro de accesos con 30 días de retención.

### D08 · Catálogo cerrado de 12 especies con fotos verificadas · 2026-10-21

- **Alternativa:** mantener la subida libre de fotos (D05).
- **Por qué:** el comprador debe ver siempre el árbol correcto. Hay 36 fotos de Wikimedia
  Commons con su atribución en `backend/catalogo.py`.
- **Qué salió mal:** el selector del frontend dependía de un `api.js` en caché, y no cargaba
  después de publicar los cambios.
- **Cómo se resolvió:** el catálogo se carga por su cuenta, y los archivos llevan `?v=` para
  forzar la descarga. El servidor rechaza cualquier especie o foto fuera del catálogo, incluso
  en peticiones hechas a mano.

### D09 · Adoptar exige pagar, a través de la canasta · 2026-10-26

- **Alternativa:** la ruta original `POST /api/suscribir`, que adoptaba sin cobrar.
- **Por qué:** la promesa es financiar la cosecha por adelantado. Adoptar sin pagar la
  contradecía.
- **Qué salió mal:** el flujo nuevo trajo errores de interfaz: adopciones dobles, una canasta
  que no se vaciaba después de pagar y modales que seguían abiertos al cambiar de vista.
- **Cómo se resolvió:** se corrigieron entre el 26 y el 30 de octubre. La doble adopción quedó
  frenada en la base de datos (D11), no solo en la pantalla.

### D10 · Tokens firmados con HMAC-SHA256 y autorización por recurso · 2026-10-29

- **Alternativas:** JWT con una biblioteca, o sesiones en el servidor.
- **Por qué:** HMAC viene en la biblioteca estándar de Python, y un token propio permite ligarlo
  a la contraseña: al cambiarla, se cierran las otras sesiones.
- **Qué salió mal:** hasta esa fecha, la API confiaba en el `id` de usuario que enviaba el
  navegador. Cualquiera podía actuar por otra persona.
- **Cómo se resolvió:** hoy el usuario sale siempre del token, y cada recurso comprueba quién
  es su dueño (`403` si no lo es). **Costo que se asume:** el código de tokens es propio y
  sensible, así que tiene pruebas dedicadas.

### D11 · Reserva atómica de cupos · 2026-10-29

- **Alternativa:** contar los cupos libres y después insertar la suscripción, que era el
  código original.
- **Por qué:** dos compras simultáneas veían el mismo cupo libre (una condición de carrera).
- **Qué salió mal:** el error no se veía al usar la aplicación a mano. Solo apareció al probar
  compras en paralelo.
- **Cómo se resolvió:** un `UPDATE` condicional (`cupos_ocupados < cupos_totales`) junto con el
  índice único `uq_suscripcion_usuario_arbol`. Se comprobó con 500 compras simultáneas del
  último cupo, y hay pruebas que lo protegen.

### D12 · PostgreSQL en producción, SQLite en local · 2026-10-30

- **Alternativas:** seguir con SQLite en un disco persistente pagado, o usar solo PostgreSQL
  también en local.
- **Por qué:** los datos tienen que sobrevivir a los despliegues (D04), y en local se quiere
  levantar el proyecto sin instalar nada.
- **Qué salió mal:** el 4 de noviembre, borrar un agricultor con despachos de otros clientes
  respondía `500` en PostgreSQL. Las pruebas, que entonces corrían solo con SQLite, no lo
  detectaban.
- **Cómo se resolvió:** se corrigió el orden del borrado y se agregó una prueba de regresión.
  La integración continua ejecuta todas las pruebas en los dos motores (D14).

### D13 · Pasarela de pago simulada · 2026-10-30

- **Alternativa:** integrar una pasarela real.
- **Por qué:** es un prototipo académico. Una pasarela real exige contrato comercial y
  requisitos de auditoría propios.
- **Medidas:** el monto lo fija el servidor, solo se guardan la marca y los 4 últimos dígitos,
  y solo se aceptan tarjetas de prueba, para que nadie escriba una tarjeta real creyendo que se
  cobrará.
- **Qué queda pendiente:** con una pasarela real, la decisión de arquitectura se revisa (D16).

### D14 · Pruebas automatizadas e integración continua en dos motores · 2026-10-30

- **Alternativa:** probar solo a mano antes de cada entrega.
- **Por qué:** la reorganización de capas (D18) y el contrato HTTP (D17) solo eran seguros con
  pruebas que miran la API desde afuera.
- **Resultado:** 139 pruebas al cierre del Hito 2 y 290 en el producto final. GitHub Actions
  las ejecuta en cada *push* contra SQLite y contra PostgreSQL 16, y revisa la sintaxis del
  JavaScript. `test_arquitectura.py` hace fallar la integración si una consulta sale de la capa
  de datos, y `test_entregables.py`, si `docs/API.md` o `db/esquema.sql` dejan de coincidir
  con el código.

### D15 · Administrador creado solo desde variables del servidor · 2026-10-31

- **Alternativa:** un rol de administrador que se elige al registrarse.
- **Por qué:** nadie debe poder registrarse como administrador, y la contraseña no puede quedar
  en el repositorio.
- **Qué salió mal:** la auditoría del 10 de noviembre (hallazgo AC-03) mostró que, si alguien
  registraba primero el correo del administrador sin verificarlo, al arrancar el servidor se
  ascendía esa cuenta con la contraseña del atacante.
- **Cómo se resolvió:** una cuenta sin verificar solo se asciende si se reemplaza su contraseña
  por `ADMIN_PASSWORD`. Hay pruebas para los tres casos.

### D16 · Monolito modular · 2026-11-04

- **Alternativa:** separar el sistema en servicios (cuentas, pagos, catálogo).
- **Por qué:** pagar y reservar un cupo deben ocurrir juntos o no ocurrir, y una transacción
  local lo garantiza sin coordinar servicios. Somos 3 integrantes con un semestre, se esperan
  decenas de usuarios (en local se midieron entre 104 y 214 lecturas por segundo con 10
  clientes), y el plan gratuito detiene cada servicio por separado.
- **Costo que se asume:** un error grave detiene todo el servicio, y nada en la infraestructura
  impide que un módulo lea cualquier tabla. Esa disciplina la imponen las pruebas.
- **Cuándo se revisaría:** con una pasarela real, si el envío de correo retrasa el registro de
  forma visible, si varios equipos tuvieran que publicar por separado o si una medición muestra
  una parte saturada.

### D17 · Contrato HTTP con un código por resultado · 2026-11-04

- **Alternativa:** mantener `200` con un campo `status` en el cuerpo, que era como funcionaba.
- **Por qué:** quien consume la API debe poder confiar en el código de estado.
- **Qué salió mal:** no se había cerrado un contrato de códigos antes de programar. Una medición
  mostró que **10 de 17 errores llegaban como éxito**.
- **Cómo se resolvió:** cada resultado usa su código (201, 400, 401, 402, 403, 404, 409, 413,
  422, 429), y todos los errores tienen la forma `{"status": "error", "mensaje": "..."}`. El
  contrato está en `docs/API.md`, y `test_contrato_http.py` lo protege. Hubo que ajustar el
  cliente y cambiar dos rutas.

### D18 · Capas reales: routers, services y repositories · 2026-11-04

- **Alternativa:** dejar la lógica en los controladores, como estaba.
- **Por qué:** había 89 líneas con consultas dentro de los routers y reglas de negocio en el
  controlador. Eran "capas que son solo carpetas".
- **Resultado:** `routers/` solo traduce HTTP, `services/` tiene las reglas y no conoce HTTP, y
  `repositories/` tiene las consultas y transacciones. Una prueba lee el código y falla si se
  rompe la regla.
- **Limitación declarada:** los servicios todavía modifican objetos del ORM directamente. No
  hay objetos de dominio separados.

### D19 · Endurecimiento de seguridad tras la revisión · 2026-11-09

- **Qué se encontró:** con la clave de ejemplo de `.env.example` en `AGROCOLAB_SECRET` se podían
  falsificar tokens. Además, el login tardaba distinto según si el correo existía, lo que
  permitía saber qué cuentas estaban registradas.
- **Qué se hizo:** el servidor rechaza la clave de ejemplo y las claves de menos de 32
  caracteres. El login tarda lo mismo exista o no la cuenta. Se agregaron las cabeceras HSTS,
  Permissions-Policy, COOP y CSP en la API, SRI en la hoja de estilos externa, y eliminar la
  cuenta pide la contraseña actual.

### D20 · Auditoría de seguridad: hallazgos AC-01 a AC-44 · 2026-11-10

- **Qué se hizo:** una revisión completa, con hallazgos numerados de AC-01 a AC-44. Las pruebas
  de `backend/tests/test_auditoria.py` cubren 41 de ellos, con el código del hallazgo en cada
  bloque.
- **Hallazgos principales:** las cuentas de demostración podían mezclarse con datos reales
  (AC-01, AC-02 y AC-06), la cuenta del administrador se podía secuestrar (AC-03, ver D15), los
  correos podían robarse antes de verificarse (AC-04), los logs y las alertas llevaban el correo
  y la IP completos (AC-14 a AC-17) y había condiciones de carrera al reclamar un pago (AC-22,
  AC-23 y AC-42).
- **Procedimiento nuevo:** `docs/INCIDENTES.md` dice qué rotar y a quién avisar si se filtra un
  secreto.

### D21 · Un solo pago para toda la canasta · 2026-11-10

- **Alternativa:** un cobro por cada producto de la canasta, que era como funcionaba.
- **Por qué:** con varios productos en la canasta, el comprador tenía que ingresar la tarjeta y
  pagar una vez por cada uno.
- **Resultado:** `POST /api/pagos/canasta` cobra una sola vez, con una tarjeta, y deja todos los
  pagos en la misma transacción. Si un árbol de la canasta falla (por ejemplo, porque ya no
  tiene cupo), no se cobra nada (`test_canasta.py`). El despacho
  ahora guarda el celular con su código de país y el código postal.

### D22 · Instalación en un equipo limpio y errores en lenguaje de usuario · 2026-11-17

- **Qué se hizo:** se clonó el repositorio en una carpeta vacía y se siguió el README al pie de
  la letra. El proyecto se levantó al primer intento, y el flujo principal (login, pago,
  suscripción, reinicio del servidor y lectura) conservó el dato.
- **Qué salió mal:** al seguir los pasos aparecieron tres trabas reales: `python` no existe en
  Linux (hay que usar `python3`), el puerto 8000 puede estar ocupado por un servidor anterior y
  el login falla si se elige el rol equivocado. Además, el catálogo mostraba un error técnico
  (`Error al conectar con la API (url)`) cuando el servidor no respondía.
- **Cómo se resolvió:** las tres trabas quedaron en `docs/MANUAL.md` con su solución. El catálogo
  ahora muestra un estado de carga, un mensaje para el usuario que explica la espera de Render y
  un botón **Intentar de nuevo**.

### D23 · Eliminar una cuenta devuelve sus cupos · 2026-11-17

- **Cómo se encontró:** al escribir el análisis de datos personales del Hito 3 se revisó qué
  borra exactamente la eliminación de una cuenta.
- **Qué salió mal:** la API muestra los cupos ocupados contando las suscripciones, pero la reserva
  atómica (D11) usa la columna `arboles.cupos_ocupados`. El borrado de cuentas eliminaba las
  suscripciones sin descontar esa columna. El árbol aparecía con cupo libre y el pago respondía
  "Cupos agotados" para siempre. En un árbol Premium (exclusivo), bastaba con que su único
  comprador eliminara la cuenta para que nadie más pudiera adoptarlo. La limpieza de la cuenta de
  demostración sí descontaba el cupo. Era la misma operación, escrita dos veces y de forma
  distinta.
- **Cómo se resolvió:** `repositories/usuarios.borrar_con_sus_datos` descuenta un cupo por cada
  árbol adoptado antes de borrar las suscripciones. `test_cupos_al_eliminar.py` agrega 3 pruebas
  (borrado propio, borrado por el administrador y nueva adopción del cupo liberado) que fallaban
  antes de la corrección y comprueban que la API y la columna coincidan.
- **Qué queda pendiente:** que dos fuentes digan cuántos cupos hay ocupados es la causa de fondo.
  Lo correcto sería que la API leyera la misma columna, o que un `CHECK` o un disparador las
  mantuviera iguales.

### D24 · Tratamiento de errores no previstos, de punta a punta · 2026-11-17

- **Alternativa:** dejar que todo error no previsto terminara en el `500` genérico.
- **Qué faltaba:** si la base de datos se caía, la API respondía "error inesperado" (`500`).
  Si dos peticiones chocaban en un índice único, también `500`. En el navegador, `fetch` no
  tenía tiempo límite (una API colgada dejaba "Cargando..." para siempre). Un token vencido
  mostraba "Tu sesión expiró", pero la interfaz seguía como si la sesión estuviera abierta. Un
  botón que fallaba sin control no avisaba nada al usuario.
- **Qué se hizo:**
  - Backend (`main.py`): la base caída responde `503` ("No pudimos conectarnos con la base de
    datos..."), y un choque de restricción, `409`. Ninguno expone tablas ni SQL, y los dos
    llevan las cabeceras CORS para que el navegador pueda leer el mensaje.
    `test_errores_inesperados.py` agrega 7 pruebas; 5 fallaban antes del cambio.
  - Cliente HTTP (`api.js`): tiempo límite de 75 segundos (Render tarda hasta un minuto en
    despertar) y un `ErrorDeConexion` con un mensaje para el usuario. Un `401` con token
    borra la sesión local y vuelve al inicio de sesión.
  - Red de seguridad (`acciones.js` y `app.js`): todo botón que falla sin control muestra un
    aviso; una promesa rechazada sin `catch` también, como máximo una vez cada 10 segundos. Si
    un módulo falla al arrancar, el resto de la aplicación sigue funcionando.
- **Cómo se verificó:** en Chrome, con el producto corriendo: `fetch` colgado (el aviso llegó a
  los 1,5 s con el límite reducido para la prueba), API inalcanzable, token alterado (la vista
  volvió al inicio de sesión y la sesión quedó vacía), login con contraseña incorrecta (no se
  confundió con una sesión vencida), botón que falla de forma síncrona y asíncrona, y promesa
  sin `catch`.
