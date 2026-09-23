-- spec: §4.3 · arq: §7 "plan_* — escaleta"
-- La escaleta es jerárquica —capítulos, escenas, beats— y es donde vive la fecha
-- narrativa: por eso una cronología imposible se detecta en el gate de Plotting, sobre
-- estas tablas, sin haber redactado una línea.

CREATE TABLE IF NOT EXISTS plan_capitulo (
  id      INTEGER PRIMARY KEY,
  numero  INTEGER NOT NULL UNIQUE,
  titulo  TEXT,
  funcion TEXT,
  gancho  TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS plan_escena (
  id               INTEGER PRIMARY KEY,
  capitulo_id      INTEGER NOT NULL REFERENCES plan_capitulo(id),
  orden            INTEGER NOT NULL,
  escenario_id     INTEGER REFERENCES canon_escenario(id),
  fecha_narrativa  TEXT,
  pdv_personaje_id INTEGER REFERENCES canon_personaje(id),
  objetivo         TEXT,
  conflicto        TEXT,
  resultado        TEXT,
  UNIQUE (capitulo_id, orden)
) STRICT;

CREATE TABLE IF NOT EXISTS plan_beat (
  id              INTEGER PRIMARY KEY,
  escena_id       INTEGER NOT NULL REFERENCES plan_escena(id),
  orden           INTEGER NOT NULL,
  accion          TEXT    NOT NULL,
  -- El giro de valor de cada beat es la materia prima de `ejecucion_escaleta`.
  cambio_de_valor TEXT,
  UNIQUE (escena_id, orden)
) STRICT;

CREATE TABLE IF NOT EXISTS plan_escena_personaje (
  escena_id    INTEGER NOT NULL REFERENCES plan_escena(id),
  personaje_id INTEGER NOT NULL REFERENCES canon_personaje(id),
  PRIMARY KEY (escena_id, personaje_id)
) STRICT;

CREATE TABLE IF NOT EXISTS plan_anclaje (
  id           INTEGER PRIMARY KEY,
  escena_id    INTEGER NOT NULL REFERENCES plan_escena(id),
  -- Los tres caminos posibles: un hecho del corpus, una entidad, o un elemento de
  -- personalización del comprador. Exactamente uno de los tres.
  hecho_id     INTEGER REFERENCES mundo_hecho(id),
  entidad_id   INTEGER REFERENCES mundo_entidad(id),
  dato_id      INTEGER REFERENCES intake_dato(id),
  tipo_vinculo TEXT    NOT NULL,
  CHECK (
    (hecho_id IS NOT NULL) + (entidad_id IS NOT NULL) + (dato_id IS NOT NULL) = 1
  )
) STRICT;

CREATE INDEX IF NOT EXISTS ix_plan_escena_capitulo ON plan_escena(capitulo_id);
CREATE INDEX IF NOT EXISTS ix_plan_anclaje_escena ON plan_anclaje(escena_id);
CREATE INDEX IF NOT EXISTS ix_plan_anclaje_dato ON plan_anclaje(dato_id);
