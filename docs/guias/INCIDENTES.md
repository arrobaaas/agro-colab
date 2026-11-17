# Respuesta a incidentes

Qué hacer si se filtra un secreto o se sospecha de una brecha. Quien detecte el problema avisa
al Delegado de Protección de Datos (ver `frontend/privacidad.html`), que coordina los pasos.

## 1. Contener

| Qué se filtró | Qué hacer | Efecto |
|---|---|---|
| `AGROCOLAB_SECRET` | Generar una nueva con `python -c "import secrets; print(secrets.token_hex(32))"` y cambiarla en Render | Se cierran todas las sesiones y dejan de valer los códigos vigentes |
| `DATABASE_URL` | Rotar la contraseña en el proveedor de la base y actualizar la variable | Reinicio del servicio |
| `BREVO_API_KEY` | Revocarla en el panel de Brevo y crear otra | Sin correos hasta actualizarla |
| `ALERTA_WEBHOOK_URL` | Borrar el webhook en Discord o Slack y crear otro | Sin alertas por webhook hasta actualizarla |
| `MONITOREO_TOKEN` | Generar otro de 24 caracteres o más | El panel pide el token nuevo |
| Contraseña del administrador | Cambiarla desde el perfil, o con la recuperación de contraseña | Se cierran sus sesiones |
| Una cuenta de usuario | Cambiar su contraseña desde el panel de administración | Se cierran sus sesiones y recibe un aviso |

Si un secreto llegó a un commit, borrarlo del archivo no basta: siempre se rota.

## 2. Evaluar

1. Revisar el panel de monitoreo y la tabla `eventos_seguridad` (conserva 30 días). Exportar lo
   relevante de inmediato, antes de que venza. Los eventos `lectura_datos` indican quién leyó datos
   de terceros.
2. Revisar los logs de Render. Ahí el correo y la IP aparecen enmascarados.
3. Determinar qué datos, de quién, desde cuándo y por qué vía.

## 3. Notificar

El equipo se compromete a avisar a la Agencia de Protección de Datos Personales y a las personas
afectadas dentro de 72 horas desde la detección, en lenguaje claro: qué datos se vieron afectados,
las posibles consecuencias y las medidas adoptadas. Antes de usar un plazo o un artículo como
referencia legal, confirmarlo en el texto oficial de la Ley 21.719.

## 4. Documentar

Registrar fecha, alcance, decisiones, responsables y correcciones, aunque no se haya notificado.

## Comprobaciones al desplegar

- **Modo:** con `AGROCOLAB_MOD_MODE=desarrollo` el servidor se niega a arrancar si existe
  `DATABASE_URL` o `RENDER`.
- **IP real:** provocar un login fallido enviando `X-Forwarded-For: 203.0.113.7` y mirar qué IP
  queda en el panel de monitoreo. Debe ser la tuya. Si no lo es, o si varias personas aparecen con
  la misma IP, prueba otra cabecera en `CABECERA_IP_CLIENTE` (por ejemplo `True-Client-IP`) y repite
  la comprobación.
- **Secreto:** el log no debe mostrar el aviso de `AGROCOLAB_SECRET`.
