-- Esquema de la base de datos de Agro-Colab para PostgreSQL.
-- Archivo generado por db/generar_esquema.py: no editar a mano.
-- Uso:  createdb agrocolab && psql -d agrocolab -f db/esquema.sql
-- La aplicación también crea este esquema sola al arrancar (backend/main.py).

CREATE TABLE eventos_seguridad (
  id SERIAL NOT NULL,
  momento TIMESTAMP WITHOUT TIME ZONE,
  tipo VARCHAR,
  severidad VARCHAR,
  ip VARCHAR,
  usuario_id INTEGER,
  email VARCHAR,
  ruta VARCHAR,
  detalle VARCHAR,
  PRIMARY KEY (id)
);
CREATE INDEX ix_eventos_seguridad_ip ON eventos_seguridad (ip);
CREATE INDEX ix_eventos_seguridad_momento ON eventos_seguridad (momento);
CREATE INDEX ix_eventos_seguridad_tipo ON eventos_seguridad (tipo);

CREATE TABLE intentos_acceso (
  id SERIAL NOT NULL,
  clave VARCHAR,
  momento FLOAT,
  PRIMARY KEY (id)
);
CREATE INDEX ix_intentos_acceso_clave ON intentos_acceso (clave);
CREATE INDEX ix_intentos_acceso_momento ON intentos_acceso (momento);

CREATE TABLE usuarios (
  id SERIAL NOT NULL,
  nombre VARCHAR,
  email VARCHAR,
  password VARCHAR,
  rol VARCHAR,
  telefono VARCHAR,
  direccion VARCHAR,
  verificado INTEGER,
  codigo_verificacion VARCHAR,
  codigo_expira TIMESTAMP WITHOUT TIME ZONE,
  recuperacion_hash VARCHAR,
  recuperacion_expira TIMESTAMP WITHOUT TIME ZONE,
  recuperacion_intentos INTEGER,
  consentimiento_datos INTEGER,
  fecha_consentimiento TIMESTAMP WITHOUT TIME ZONE,
  acepta_terminos INTEGER,
  politica_privacidad TEXT,
  sesion_version INTEGER,
  PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_usuarios_email ON usuarios (email);
CREATE INDEX ix_usuarios_id ON usuarios (id);
CREATE INDEX ix_usuarios_nombre ON usuarios (nombre);

CREATE TABLE arboles (
  id SERIAL NOT NULL,
  nombre VARCHAR,
  ubicacion VARCHAR,
  plan VARCHAR,
  tipo_suscripcion VARCHAR,
  cupos_totales INTEGER,
  cupos_ocupados INTEGER,
  precio_mensual_clp INTEGER,
  estimacion_cosecha VARCHAR,
  imagen VARCHAR,
  especie VARCHAR,
  identificador VARCHAR,
  imagen_origen VARCHAR,
  productor_id INTEGER,
  PRIMARY KEY (id),
  CONSTRAINT ck_arboles_cupos CHECK (cupos_ocupados >= 0 AND cupos_ocupados <= cupos_totales),
  FOREIGN KEY(productor_id) REFERENCES usuarios (id)
);
CREATE INDEX ix_arboles_id ON arboles (id);
CREATE INDEX ix_arboles_nombre ON arboles (nombre);

CREATE TABLE pagos (
  id SERIAL NOT NULL,
  usuario_id INTEGER,
  tipo VARCHAR,
  arbol_id INTEGER,
  plan_nombre VARCHAR,
  concepto VARCHAR,
  monto_clp INTEGER,
  estado VARCHAR,
  motivo_rechazo VARCHAR,
  marca VARCHAR,
  ultimos4 VARCHAR,
  codigo_autorizacion VARCHAR,
  transaccion VARCHAR,
  pedido_id INTEGER,
  fecha TIMESTAMP WITHOUT TIME ZONE,
  PRIMARY KEY (id),
  FOREIGN KEY(usuario_id) REFERENCES usuarios (id),
  UNIQUE (transaccion)
);
CREATE INDEX ix_pagos_id ON pagos (id);
CREATE INDEX ix_pagos_usuario_id ON pagos (usuario_id);

CREATE TABLE pedidos (
  id SERIAL NOT NULL,
  cliente_id INTEGER,
  plan_nombre VARCHAR,
  monto_clp INTEGER,
  tipo_destino VARCHAR,
  razon_social VARCHAR,
  rut VARCHAR,
  direccion VARCHAR,
  comuna VARCHAR,
  codigo_postal VARCHAR,
  telefono_codigo VARCHAR,
  telefono VARCHAR,
  frecuencia_entrega VARCHAR,
  codigo_seguimiento VARCHAR,
  fecha_registro TIMESTAMP WITHOUT TIME ZONE,
  estado_logistica VARCHAR,
  tipo VARCHAR,
  arbol_id INTEGER,
  PRIMARY KEY (id),
  FOREIGN KEY(cliente_id) REFERENCES usuarios (id),
  UNIQUE (codigo_seguimiento),
  FOREIGN KEY(arbol_id) REFERENCES arboles (id)
);
CREATE INDEX ix_pedidos_id ON pedidos (id);

CREATE TABLE suscripciones (
  id SERIAL NOT NULL,
  usuario_id INTEGER,
  arbol_id INTEGER,
  fecha_suscripcion TIMESTAMP WITHOUT TIME ZONE,
  PRIMARY KEY (id),
  CONSTRAINT uq_suscripcion_usuario_arbol UNIQUE (usuario_id, arbol_id),
  FOREIGN KEY(usuario_id) REFERENCES usuarios (id),
  FOREIGN KEY(arbol_id) REFERENCES arboles (id)
);
CREATE INDEX ix_suscripciones_id ON suscripciones (id);
