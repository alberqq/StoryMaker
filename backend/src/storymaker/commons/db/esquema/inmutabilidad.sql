-- spec: §3.1 · arq: §2 principio 5, §7
-- El segundo cerrojo de «nada se sobrescribe». Arriba, la regla Semgrep
-- `no-update-inmutables` impide escribir el código; aquí, el trigger impide que se
-- ejecute. Un principio con un solo cerrojo es una convención; con los dos, es una
-- propiedad.
--
-- Lo que se protege es **el contenido**, no la fila entera, y conviene decir por qué. Un
-- capítulo tiene que poder pasar de borrador a aprobado, y una ejecución de fase tiene
-- que poder cerrarse con su consumo y su hora de fin: si el trigger prohibiera toda
-- escritura, `ApproveChapter` y el cierre de `fase_run` serían imposibles y el sistema
-- necesitaría una fila nueva para registrar que algo terminó. Lo que la arquitectura
-- prohíbe es reescribir lo generado —el texto, el intento, a qué capítulo pertenece—,
-- porque eso es lo que haría perder la versión anterior.

-- capitulo_version: el texto es intocable; el estado es lo único que se mueve.
CREATE TRIGGER IF NOT EXISTS inmutable_capitulo_version_update
BEFORE UPDATE ON capitulo_version
WHEN OLD.texto       IS NOT NEW.texto
  OR OLD.capitulo_id IS NOT NEW.capitulo_id
  OR OLD.fase_run_id IS NOT NEW.fase_run_id
  OR OLD.intento     IS NOT NEW.intento
  OR OLD.palabras    IS NOT NEW.palabras
  OR OLD.creado_en   IS NOT NEW.creado_en
BEGIN
  SELECT RAISE(ABORT, 'capitulo_version es inmutable: solo puede cambiar su estado');
END;

CREATE TRIGGER IF NOT EXISTS inmutable_capitulo_version_delete
BEFORE DELETE ON capitulo_version
BEGIN
  SELECT RAISE(ABORT, 'capitulo_version es inmutable: no se borra');
END;

-- fase_run: su identidad no cambia; su cierre sí.
CREATE TRIGGER IF NOT EXISTS inmutable_fase_run_update
BEFORE UPDATE ON fase_run
WHEN OLD.fase           IS NOT NEW.fase
  OR OLD.input_run_id   IS NOT NEW.input_run_id
  OR OLD.prompt_nombre  IS NOT NEW.prompt_nombre
  OR OLD.prompt_version IS NOT NEW.prompt_version
  OR OLD.modelo         IS NOT NEW.modelo
  OR OLD.inicio         IS NOT NEW.inicio
BEGIN
  SELECT RAISE(ABORT, 'fase_run es inmutable: solo puede cerrarse');
END;

CREATE TRIGGER IF NOT EXISTS inmutable_fase_run_delete
BEFORE DELETE ON fase_run
BEGIN
  SELECT RAISE(ABORT, 'fase_run es inmutable: no se borra');
END;

-- Una versión publicada y su manifiesto no se tocan jamás. Ahí no hay matiz: es la
-- promesa de `PreviousVersionPreserved`.
CREATE TRIGGER IF NOT EXISTS inmutable_version_novela_update
BEFORE UPDATE ON version_novela
BEGIN
  SELECT RAISE(ABORT, 'version_novela es inmutable');
END;

CREATE TRIGGER IF NOT EXISTS inmutable_version_novela_delete
BEFORE DELETE ON version_novela
BEGIN
  SELECT RAISE(ABORT, 'version_novela es inmutable');
END;

CREATE TRIGGER IF NOT EXISTS inmutable_version_capitulo_update
BEFORE UPDATE ON version_capitulo
BEGIN
  SELECT RAISE(ABORT, 'version_capitulo es inmutable: el manifiesto no se reescribe');
END;

CREATE TRIGGER IF NOT EXISTS inmutable_version_capitulo_delete
BEFORE DELETE ON version_capitulo
BEGIN
  SELECT RAISE(ABORT, 'version_capitulo es inmutable: el manifiesto no se reescribe');
END;

-- El corpus es append-only hasta el sello y de solo lectura después. Antes del sello, el
-- verificador escribe `respaldo` —nunca `estado`— y el Autor edita en el gate; después,
-- durante Writing, nadie puede añadir ni tocar un hecho: solo anclar a los existentes o
-- declarar una Licencia. La condición es la existencia del sello, de modo que un
-- re-sellado tras una edición humana vuelve a cerrar la puerta.
CREATE TRIGGER IF NOT EXISTS corpus_sellado_update
BEFORE UPDATE ON mundo_hecho
WHEN EXISTS (SELECT 1 FROM mundo_sello)
BEGIN
  SELECT RAISE(ABORT, 'el corpus esta sellado: mundo_hecho es de solo lectura');
END;

CREATE TRIGGER IF NOT EXISTS corpus_sellado_delete
BEFORE DELETE ON mundo_hecho
WHEN EXISTS (SELECT 1 FROM mundo_sello)
BEGIN
  SELECT RAISE(ABORT, 'el corpus esta sellado: mundo_hecho es de solo lectura');
END;

CREATE TRIGGER IF NOT EXISTS corpus_sellado_insert
BEFORE INSERT ON mundo_hecho
WHEN EXISTS (SELECT 1 FROM mundo_sello)
BEGIN
  SELECT RAISE(ABORT, 'el corpus esta sellado: no se anaden hechos durante Writing');
END;
