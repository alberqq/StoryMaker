-- spec: §3.5 · arq: §7 "vec_* — índices semánticos", §16.2
-- Tres índices y no uno, porque son los tres que el ensamblador consulta por separado y
-- sus identificadores viven en espacios distintos. Las columnas de metadato se filtran
-- dentro de la propia consulta KNN; las auxiliares, con prefijo +, solo se leen al
-- resolver el resultado.

CREATE VIRTUAL TABLE IF NOT EXISTS vec_hecho USING vec0(
  hecho_id  integer primary key,
  embedding float[384] distance_metric=cosine,
  estado    text,
  dimension text
);

-- La biblia son tres tablas y la clave primaria de una vec0 es un único entero, así que
-- este índice lleva identificador propio y guarda en auxiliares a qué fila apunta.
CREATE VIRTUAL TABLE IF NOT EXISTS vec_canon USING vec0(
  id        integer primary key,
  embedding float[384] distance_metric=cosine,
  familia   text,
  +tabla    text,
  +fila_id  integer
);

-- `vigente` existe porque de un mismo capítulo hay varias capitulo_version: los
-- reintentos del bucle y las que deja cada regeneración. Sin ese filtro, el escritor del
-- capítulo 7 podría recibir el resumen de un intento rechazado del 3.
CREATE VIRTUAL TABLE IF NOT EXISTS vec_resumen USING vec0(
  capitulo_version_id integer primary key,
  embedding           float[384] distance_metric=cosine,
  capitulo_numero     integer,
  vigente             integer
);
