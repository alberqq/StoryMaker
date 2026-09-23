-- spec: §4.1 · arq: §7 "intake_* — encargo y material del comprador"
-- La verdad son las filas de intake_dato; intake_brief.json es la fotografía auditable
-- que no decide nada. Guardar el mismo dato en los dos sitios y dejar que ambos manden
-- sería el error que el resto del sistema evita en todas partes.

CREATE TABLE IF NOT EXISTS intake_brief (
  id          INTEGER PRIMARY KEY,
  fase_run_id INTEGER NOT NULL REFERENCES fase_run(id),
  version     INTEGER NOT NULL DEFAULT 1,
  json        TEXT    NOT NULL,
  hash        TEXT    NOT NULL,
  creado_en   TEXT    NOT NULL DEFAULT (datetime('now'))
) STRICT;

-- La cuarentena. El texto pegado vive aquí y no sale de aquí.
CREATE TABLE IF NOT EXISTS intake_texto_crudo (
  id           INTEGER PRIMARY KEY,
  texto        TEXT NOT NULL,
  recibido_en  TEXT NOT NULL DEFAULT (datetime('now')),
  procesado_en TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS intake_dato (
  id             INTEGER PRIMARY KEY,
  texto_crudo_id INTEGER REFERENCES intake_texto_crudo(id),
  tipo           TEXT    NOT NULL CHECK (tipo IN ('persona','lugar','fecha','objeto','anecdota')),
  valor_json     TEXT    NOT NULL,
  origen         TEXT    NOT NULL CHECK (origen IN ('entrevista','texto_libre_no_confiable')),
  obligatorio    INTEGER NOT NULL DEFAULT 0 CHECK (obligatorio IN (0, 1)),
  -- Solo lo extraído de la cuarentena tiene texto de procedencia; por eso el nulo.
  CHECK (origen = 'entrevista' OR texto_crudo_id IS NOT NULL)
) STRICT;

CREATE TABLE IF NOT EXISTS intake_uso_dato (
  capitulo_version_id INTEGER NOT NULL REFERENCES capitulo_version(id),
  escena_id           INTEGER NOT NULL REFERENCES plan_escena(id),
  dato_id             INTEGER NOT NULL REFERENCES intake_dato(id),
  tipo_uso            TEXT    NOT NULL,
  PRIMARY KEY (capitulo_version_id, escena_id, dato_id)
) STRICT;

CREATE INDEX IF NOT EXISTS ix_intake_dato_obligatorio ON intake_dato(obligatorio);
