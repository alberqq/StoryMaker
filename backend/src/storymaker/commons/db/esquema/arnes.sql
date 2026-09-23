-- spec: §3.1 · arq: §7 "arnes_* — estado del sistema"
-- Se aplica primero porque casi todo cuelga de fase_run: qué ejecución escribió cada fila
-- es lo que permite rehacer una fase sin mezclar su resultado con el de la anterior.

CREATE TABLE IF NOT EXISTS fase_run (
  id             INTEGER PRIMARY KEY,
  fase           TEXT    NOT NULL CHECK (fase IN ('intake','investigation','plotting','writing','publication','regeneration')),
  estado         TEXT    NOT NULL CHECK (estado IN ('en_curso','esperando_gate','completada','fallida','aparcada','abortada')),
  input_run_id   INTEGER REFERENCES fase_run(id),
  artefacto_hash TEXT,
  prompt_nombre  TEXT,
  prompt_version TEXT,
  modelo         TEXT,
  tokens_in      INTEGER NOT NULL DEFAULT 0,
  tokens_out     INTEGER NOT NULL DEFAULT 0,
  coste_usd      REAL    NOT NULL DEFAULT 0.0,
  trace_id       TEXT,
  inicio         TEXT    NOT NULL DEFAULT (datetime('now')),
  fin            TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS gate (
  id            INTEGER PRIMARY KEY,
  fase_run_id   INTEGER NOT NULL REFERENCES fase_run(id),
  estado        TEXT    NOT NULL CHECK (estado IN ('pendiente','decidido','aparcado')),
  decision      TEXT    CHECK (decision IS NULL OR decision IN ('aprobar','rehacer','editar','abortar')),
  comentario    TEXT,
  decidido_por  TEXT,
  notificado_en TEXT,
  decidido_en   TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS incidencia (
  id                  INTEGER PRIMARY KEY,
  capitulo_version_id INTEGER REFERENCES capitulo_version(id),
  validador           TEXT    NOT NULL,
  severidad           TEXT    NOT NULL CHECK (severidad IN ('bloqueante','aviso')),
  ubicacion           TEXT,
  mensaje             TEXT    NOT NULL,
  propuesta           TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS score (
  id           INTEGER PRIMARY KEY,
  objeto_tipo  TEXT    NOT NULL,
  objeto_id    INTEGER NOT NULL,
  validador    TEXT    NOT NULL,
  valor        REAL    NOT NULL,
  detalle_json TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS audit_log (
  id           INTEGER PRIMARY KEY,
  momento      TEXT    NOT NULL DEFAULT (datetime('now')),
  actor        TEXT    NOT NULL,
  accion       TEXT    NOT NULL,
  objeto       TEXT    NOT NULL,
  antes_json   TEXT,
  despues_json TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS edicion_humana (
  id          INTEGER PRIMARY KEY,
  fase_run_id INTEGER REFERENCES fase_run(id),
  tabla       TEXT    NOT NULL,
  fila_id     INTEGER NOT NULL,
  campo       TEXT    NOT NULL,
  antes       TEXT,
  despues     TEXT,
  motivo      TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS procedencia (
  origen_db          TEXT    NOT NULL,
  origen_fase_run_id INTEGER,
  creada_en          TEXT    NOT NULL DEFAULT (datetime('now'))
) STRICT;

CREATE TABLE IF NOT EXISTS manifiesto (
  id                INTEGER PRIMARY KEY,
  version_novela_id INTEGER NOT NULL REFERENCES version_novela(id),
  brief_hash        TEXT    NOT NULL,
  sello_corpus_hash TEXT    NOT NULL,
  prompts_json      TEXT    NOT NULL,
  modelos_json      TEXT    NOT NULL,
  embeddings_json   TEXT    NOT NULL,
  sdk_version       TEXT,
  gates_enabled     INTEGER NOT NULL DEFAULT 1 CHECK (gates_enabled IN (0, 1)),
  creado_en         TEXT    NOT NULL DEFAULT (datetime('now'))
) STRICT;

-- Lo que el modelo vio exactamente cuando escribio un capitulo. §6 exige persistirlo y
-- enlazarlo desde su span: poder abrir, delante del evaluador, literalmente el contexto del
-- capitulo 7 es la definicion operativa de «interpretable» en este sistema. Vive aqui y no
-- en un fichero aparte para que la propiedad «una novela es un fichero» quede intacta.
CREATE TABLE IF NOT EXISTS paquete_contexto (
  id                  INTEGER PRIMARY KEY,
  capitulo_version_id INTEGER REFERENCES capitulo_version(id),
  capitulo_numero     INTEGER NOT NULL,
  intento             INTEGER NOT NULL DEFAULT 1,
  texto               TEXT    NOT NULL,
  tokens              INTEGER NOT NULL,
  trace_span          TEXT,
  creado_en           TEXT    NOT NULL DEFAULT (datetime('now'))
) STRICT;

CREATE INDEX IF NOT EXISTS ix_gate_fase_run ON gate(fase_run_id);
CREATE INDEX IF NOT EXISTS ix_incidencia_capitulo ON incidencia(capitulo_version_id);
CREATE INDEX IF NOT EXISTS ix_paquete_capitulo ON paquete_contexto(capitulo_numero);
