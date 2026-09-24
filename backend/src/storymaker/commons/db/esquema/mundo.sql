-- spec: §4.2 · arq: §7 "mundo_* — corpus histórico (append-only hasta el sello)"
-- `estado` y `respaldo` no dicen lo mismo: estado es una propiedad del hecho en la
-- historiografía; respaldo, una propiedad de la cita. Un hecho puede estar bien
-- respaldado y ser debatido, y otro afirmarse como verificado y resultar no respaldado.

CREATE TABLE IF NOT EXISTS mundo_fuente (
  id         INTEGER PRIMARY KEY,
  tipo       TEXT    NOT NULL,
  autor      TEXT,
  fecha      TEXT,
  url        TEXT,
  titulo     TEXT,
  fiabilidad TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS mundo_hecho (
  id             INTEGER PRIMARY KEY,
  fase_run_id    INTEGER NOT NULL REFERENCES fase_run(id),
  enunciado      TEXT    NOT NULL,
  estado         TEXT    NOT NULL CHECK (estado IN ('verificado','debatido','inferido','desconocido')),
  entidades_json TEXT,
  dimension      TEXT    NOT NULL CHECK (dimension IN ('cronologia','lugar','cultura_material','lenguaje','mentalidad','estructura_social')),
  origen         TEXT    NOT NULL CHECK (origen IN ('investigacion_inicial','micro_arquitecto','invencion_autorizada')),
  -- 300 caracteres: obliga a señalar el fragmento que sostiene este enunciado en vez de
  -- volcar media página, y mantiene acotado el contexto del verificador.
  cita           TEXT    CHECK (cita IS NULL OR length(cita) <= 300),
  respaldo       TEXT    NOT NULL DEFAULT 'pendiente'
                         CHECK (respaldo IN ('pendiente','respaldado','no_respaldado','no_aplica')),
  -- El veredicto parcial: la cita sostiene el dato central y el enunciado añade esto, que
  -- no dice. Se guarda con `respaldo = 'respaldado'`. En las novelas creadas antes entra al
  -- abrir, como columna aditiva (`apertura.COLUMNAS_ADITIVAS`).
  sin_respaldo   TEXT    CHECK (sin_respaldo IS NULL OR length(sin_respaldo) <= 300),
  creado_en      TEXT    NOT NULL DEFAULT (datetime('now')),
  -- Un dato que el arquitecto inventó con permiso no tiene nada que comprobar.
  CHECK (origen <> 'invencion_autorizada' OR respaldo = 'no_aplica')
) STRICT;

CREATE TABLE IF NOT EXISTS mundo_hecho_fuente (
  hecho_id  INTEGER NOT NULL REFERENCES mundo_hecho(id),
  fuente_id INTEGER NOT NULL REFERENCES mundo_fuente(id),
  PRIMARY KEY (hecho_id, fuente_id)
) STRICT;

CREATE TABLE IF NOT EXISTS mundo_entidad (
  id             INTEGER PRIMARY KEY,
  tipo           TEXT    NOT NULL CHECK (tipo IN ('periodo','lugar','personaje_historico','cultura_material','lexico')),
  nombre         TEXT    NOT NULL,
  nombre_epoca   TEXT,
  -- Las dos columnas que alimentan el detector de anacronismos y el cuarto invariante.
  fecha_inicio   TEXT,
  fecha_fin      TEXT,
  atributos_json TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS mundo_sello (
  id           INTEGER PRIMARY KEY,
  hash         TEXT    NOT NULL,
  fase_run_id  INTEGER NOT NULL REFERENCES fase_run(id),
  calculado_en TEXT    NOT NULL DEFAULT (datetime('now'))
) STRICT;

CREATE INDEX IF NOT EXISTS ix_mundo_hecho_run ON mundo_hecho(fase_run_id);
CREATE INDEX IF NOT EXISTS ix_mundo_hecho_dimension ON mundo_hecho(dimension);
