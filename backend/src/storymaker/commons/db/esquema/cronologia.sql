-- spec: §3.7 · arq: §7 "cronologia_* — la materia prima de Lean"
-- `origen` distingue lo histórico de lo narrativo, y mezclar ambos en la misma tabla es
-- deliberado: es en esa mezcla donde aparecen las incoherencias que ningún validador
-- semántico detecta, como un personaje histórico en escena tres años después de morir.

CREATE TABLE IF NOT EXISTS cronologia_evento (
  id               INTEGER PRIMARY KEY,
  clave            TEXT    NOT NULL UNIQUE,
  descripcion      TEXT    NOT NULL,
  momento          TEXT    NOT NULL,
  lugar_entidad_id INTEGER REFERENCES mundo_entidad(id),
  origen           TEXT    NOT NULL CHECK (origen IN ('historico','narrativo')),
  -- Las filas narrativas las escribe el extractor al leer el capítulo; por eso Lean
  -- corre en su pasada y no en la determinista.
  capitulo_version_id INTEGER REFERENCES capitulo_version(id),
  CHECK (origen = 'historico' OR capitulo_version_id IS NOT NULL)
) STRICT;

CREATE TABLE IF NOT EXISTS cronologia_participante (
  evento_id    INTEGER NOT NULL REFERENCES cronologia_evento(id),
  personaje_id INTEGER NOT NULL REFERENCES canon_personaje(id),
  PRIMARY KEY (evento_id, personaje_id)
) STRICT;

CREATE INDEX IF NOT EXISTS ix_cronologia_momento ON cronologia_evento(momento);
CREATE INDEX IF NOT EXISTS ix_cronologia_origen ON cronologia_evento(origen);
