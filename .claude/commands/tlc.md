---
description: Corre TLC sobre formal/tla/harness.tla con harness.cfg y harness_batch.cfg y resume invariantes, propiedades y estados
argument-hint: "[interactivo | batch]  (vacío: los dos modelos)"
---

# /tlc — model checking del arnés

Comprueba con TLC la especificación del arnés, `formal/tla/harness.tla`, sobre los dos modelos que declara `formal/tla/README.md`. Es una comprobación de desarrollo: TLC no corre en cada generación.

**Este comando no reinicia el servidor de la interfaz, no lanza ninguna novela y no edita `harness.tla` ni sus `.cfg`.** Se rige por `AGENTS.md`: si TLC encuentra un contraejemplo, se cuenta al Autor; el cambio que provoque baja por arquitectura → spec → plan, no se improvisa aquí.

Argumento recibido: `$ARGUMENTS`. Con `interactivo` se corre solo `harness.cfg`; con `batch`, solo `harness_batch.cfg`; vacío, los dos.

## Pasos

1. **Comprueba la JVM** con `java -version`. TLC necesita Java y `tla2tools.jar`, y ninguno está en el repositorio. Si no hay `java` en el PATH, **para aquí** y dilo: no instales una JVM sin que el Autor lo pida.
2. **Corre TLC desde `formal/tla/`**, que es donde deja su directorio `states/` (ignorado por git). Usa el envoltorio de la skill `tlaplus`, que descarga un `tla2tools.jar` fijado en `~/.tla2tools/` la primera vez; avisa de esa descarga antes de hacerla si el jar no existe:

   ```bash
   cd formal/tla
   bash ../../.claude/skills/tlaplus/scripts/tlc.sh harness.tla harness.cfg -workers auto
   bash ../../.claude/skills/tlaplus/scripts/tlc.sh harness.tla harness_batch.cfg -workers auto
   ```

   Si el Autor tiene su propio `tla2tools.jar`, vale igual el comando directo del README: `java -XX:+UseParallelGC -cp <ruta>/tla2tools.jar tlc2.TLC -workers auto -config harness.cfg harness.tla`.
3. **Resume cada modelo** en una tabla con: configuración, modo (interactivo o batch), veredicto, estados generados, estados distintos, profundidad y tiempo. Saca los números de la salida de TLC («states generated», «distinct states found», «depth of the complete state graph search»).
4. **Enumera lo comprobado**, leyéndolo del `.cfg` y no de memoria: los cinco invariantes (`TypeOK`, `NoPublishUnvalidated`, `ResumeIsExactlyOnce`, `RetriesBounded`, `CorpusSelladoNoSeToca`) y las dos propiedades temporales (`PreviousVersionPreserved`, `Termina`).
5. **Compara con la tabla de resultados de `formal/tla/README.md`.** Si los estados distintos cambian, dilo: significa que el modelo ha cambiado desde la última ejecución registrada.

## Si TLC encuentra una violación

Resume la traza en lenguaje llano —qué acciones, en qué orden, qué variable rompe la propiedad— y propón al Autor la fila para el «Registro de contraejemplos» del README de `formal/tla/` y la entrada de `docs/iteraciones.md`. No las escribas sin que el Autor lo confirme, y no toques el modelo para que pase.
