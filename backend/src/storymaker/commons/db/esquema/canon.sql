-- spec: §4.3 · arq: §7 "canon_* — biblia de la obra (viva)"
-- El Arco tiene tabla porque si no, no puede tener validador: todos los validadores
-- deterministas de este sistema comparan el texto contra una fila, y sin fila el arco
-- solo podía juzgarlo el juez, sobre la novela entera y una sola vez.

CREATE TABLE IF NOT EXISTS canon_obra (
  id                    INTEGER PRIMARY KEY,
  titulo                TEXT,
  premisa               TEXT,
  tema                  TEXT,
  genero                TEXT,
  n_capitulos           INTEGER NOT NULL DEFAULT 10,
  palabras_por_capitulo INTEGER NOT NULL DEFAULT 1200,
  voz                   TEXT,
  -- Aquí bajan los diales de la frontera historia-ficción: licencia, arcaísmo y
  -- contenido admisible. De aquí los toma el bloque 6 del paquete de contexto.
  estilo_json           TEXT,
  homenajeado_id        INTEGER REFERENCES canon_personaje(id)
) STRICT;

CREATE TABLE IF NOT EXISTS canon_personaje (
  id                    INTEGER PRIMARY KEY,
  nombre                TEXT    NOT NULL,
  tipo                  TEXT    NOT NULL CHECK (tipo IN ('inventado','historico_ficcionalizado','historico_de_fondo')),
  rasgos_json           TEXT,
  objetivo              TEXT,
  miedo                 TEXT,
  voz                   TEXT,
  estatus               TEXT,
  personaje_historico_id INTEGER REFERENCES mundo_entidad(id),
  fecha_nacimiento      TEXT,
  fecha_muerte          TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS canon_relacion (
  a_id       INTEGER NOT NULL REFERENCES canon_personaje(id),
  b_id       INTEGER NOT NULL REFERENCES canon_personaje(id),
  tipo       TEXT    NOT NULL,
  intensidad INTEGER,
  PRIMARY KEY (a_id, b_id, tipo)
) STRICT;

CREATE TABLE IF NOT EXISTS canon_arco (
  id             INTEGER PRIMARY KEY,
  personaje_id   INTEGER NOT NULL REFERENCES canon_personaje(id),
  -- El arco plano es un tipo legítimo: declarar que un personaje no se transforma es
  -- una decisión sobre él, y es justo la decisión que `arco_anclado` reclama.
  tipo           TEXT    NOT NULL CHECK (tipo IN ('positivo','negativo','plano')),
  estado_inicial TEXT,
  estado_final   TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS canon_arco_hito (
  id          INTEGER PRIMARY KEY,
  arco_id     INTEGER NOT NULL REFERENCES canon_arco(id),
  orden       INTEGER NOT NULL,
  descripcion TEXT    NOT NULL,
  escena_id   INTEGER REFERENCES plan_escena(id)
) STRICT;

CREATE TABLE IF NOT EXISTS canon_escenario (
  id               INTEGER PRIMARY KEY,
  lugar_entidad_id INTEGER REFERENCES mundo_entidad(id),
  descripcion      TEXT,
  detalles_json    TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS canon_licencia (
  id             INTEGER PRIMARY KEY,
  hecho_id       INTEGER REFERENCES mundo_hecho(id),
  alteracion     TEXT    NOT NULL,
  justificacion  TEXT    NOT NULL,
  declarada      INTEGER NOT NULL DEFAULT 1 CHECK (declarada IN (0, 1))
) STRICT;

CREATE TABLE IF NOT EXISTS canon_glosario (
  id          INTEGER PRIMARY KEY,
  termino     TEXT    NOT NULL,
  significado TEXT    NOT NULL,
  registro    TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS canon_prohibida (
  id          INTEGER PRIMARY KEY,
  nivel       TEXT    NOT NULL CHECK (nivel IN ('global','novela','destinatario')),
  termino     TEXT    NOT NULL,
  -- La detección normaliza antes de comparar: mayúsculas, acentos, plurales y variantes.
  normalizado TEXT    NOT NULL
) STRICT;

CREATE INDEX IF NOT EXISTS ix_canon_arco_personaje ON canon_arco(personaje_id);
CREATE INDEX IF NOT EXISTS ix_canon_hito_escena ON canon_arco_hito(escena_id);
CREATE INDEX IF NOT EXISTS ix_canon_prohibida_norm ON canon_prohibida(normalizado);
