-- spec: §4.4 · arq: §7 "texto_* — capítulos inmutables y versiones"
-- Nunca se hace UPDATE sobre el contenido de un capítulo. Una versión de la novela es el
-- manifiesto `version_capitulo`: la lista ordenada de qué `capitulo_version_id` la
-- componen. De ahí salen gratis tres cosas: la versión anterior se conserva por
-- construcción, el «qué cambió» es comparar dos manifiestos, y un capítulo no
-- regenerado se comparte entre versiones sin duplicarse.

CREATE TABLE IF NOT EXISTS capitulo_version (
  id          INTEGER PRIMARY KEY,
  capitulo_id INTEGER NOT NULL REFERENCES plan_capitulo(id),
  fase_run_id INTEGER NOT NULL REFERENCES fase_run(id),
  intento     INTEGER NOT NULL DEFAULT 1,
  texto       TEXT    NOT NULL,
  palabras    INTEGER NOT NULL,
  resumen     TEXT,
  -- Lo único que cambia de una fila ya escrita. El texto, no.
  estado      TEXT    NOT NULL DEFAULT 'borrador'
                      CHECK (estado IN ('borrador','aprobado','invalidado','descartado')),
  creado_en   TEXT    NOT NULL DEFAULT (datetime('now')),
  UNIQUE (capitulo_id, fase_run_id, intento)
) STRICT;

CREATE TABLE IF NOT EXISTS version_novela (
  id               INTEGER PRIMARY KEY,
  numero           INTEGER NOT NULL UNIQUE,
  gate_id          INTEGER REFERENCES gate(id),
  judge_score_json TEXT,
  creada_en        TEXT    NOT NULL DEFAULT (datetime('now'))
) STRICT;

CREATE TABLE IF NOT EXISTS version_capitulo (
  version_id          INTEGER NOT NULL REFERENCES version_novela(id),
  capitulo_version_id INTEGER NOT NULL REFERENCES capitulo_version(id),
  PRIMARY KEY (version_id, capitulo_version_id)
) STRICT;

-- El índice hecho -> capítulo, a granularidad de escena. La consulta de regeneración lo
-- agrega a capítulo, que es la unidad de reescritura.
CREATE TABLE IF NOT EXISTS uso_hecho (
  capitulo_version_id INTEGER NOT NULL REFERENCES capitulo_version(id),
  escena_id           INTEGER NOT NULL REFERENCES plan_escena(id),
  hecho_id            INTEGER NOT NULL REFERENCES mundo_hecho(id),
  tipo_uso            TEXT    NOT NULL,
  PRIMARY KEY (capitulo_version_id, escena_id, hecho_id)
) STRICT;

-- Su gemelo para el arco: sin él, mover un hito del capítulo 8 al 5 no invalidaría nada.
CREATE TABLE IF NOT EXISTS uso_hito (
  capitulo_version_id INTEGER NOT NULL REFERENCES capitulo_version(id),
  escena_id           INTEGER NOT NULL REFERENCES plan_escena(id),
  hito_id             INTEGER NOT NULL REFERENCES canon_arco_hito(id),
  ejecutado           INTEGER NOT NULL CHECK (ejecutado IN (0, 1)),
  PRIMARY KEY (capitulo_version_id, escena_id, hito_id)
) STRICT;

CREATE TABLE IF NOT EXISTS continuidad (
  id                  INTEGER PRIMARY KEY,
  capitulo_version_id INTEGER NOT NULL REFERENCES capitulo_version(id),
  personaje_id        INTEGER NOT NULL REFERENCES canon_personaje(id),
  escenario_id        INTEGER REFERENCES canon_escenario(id),
  fecha_narrativa     TEXT,
  conocimiento_json   TEXT,
  posesiones_json     TEXT,
  estado_json         TEXT
) STRICT;

CREATE INDEX IF NOT EXISTS ix_capitulo_version_capitulo ON capitulo_version(capitulo_id);
CREATE INDEX IF NOT EXISTS ix_uso_hecho_hecho ON uso_hecho(hecho_id);
CREATE INDEX IF NOT EXISTS ix_uso_hito_hito ON uso_hito(hito_id);
CREATE INDEX IF NOT EXISTS ix_continuidad_capitulo ON continuidad(capitulo_version_id);
