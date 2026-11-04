# Base de datos

| Archivo | Contenido |
|---|---|
| [`modelo_datos.png`](modelo_datos.png) | Diagrama con las 7 tablas, sus claves, relaciones y tipos |
| [`esquema.sql`](esquema.sql) | Script que crea la base desde cero en PostgreSQL |
| [`generar_esquema.py`](generar_esquema.py) | Regenera el script desde los modelos de `backend/database.py` |

## Crear la base desde cero

```bash
createdb agrocolab
psql -d agrocolab -f db/esquema.sql
```

La aplicación también crea las tablas sola al arrancar y carga dos cuentas de demostración
con tres árboles de ejemplo. Sin `DATABASE_URL` usa una base SQLite local, sin instalar nada.
Para usar PostgreSQL, define `DATABASE_URL` (ver [`.env.example`](../.env.example)).

## Decisiones del modelo

- `suscripciones` es la relación N a N entre `usuarios` y `arboles`. Su índice único
  `uq_suscripcion_usuario_arbol` impide que una persona ocupe dos cupos del mismo árbol.
- `arboles.cupos_ocupados` se actualiza con un `UPDATE` condicional, para que dos compras
  simultáneas no se queden con el último cupo.
- `pagos.arbol_id` y `pagos.pedido_id` no son claves foráneas a propósito: el comprobante
  debe sobrevivir si el agricultor elimina el árbol.
- `eventos_seguridad` e `intentos_acceso` no tienen claves foráneas: son registros de
  auditoría y de límites de intentos, y no dependen de que la cuenta siga existiendo.

Una prueba automatizada comprueba que `esquema.sql` coincida con los modelos.
