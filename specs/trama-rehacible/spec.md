# Spec — La Trama que se puede rehacer

Qué pasa en la Fase 3 cuando el Autor pide otra trama, qué comprueba el arnés sobre la escaleta antes de enseñársela y cómo se cubre un hueco para que sirva a una escena. Deriva de [`docs/architecture.md`](../../docs/architecture.md) §4 (Fase 3), §9, §10, §11a y §11c, y de la spec del backend, [`specs/backend/spec.md`](../backend/spec.md) §4.3. **Si algo de este documento contradice a la arquitectura, manda la arquitectura.** La forma técnica exacta vive en [`plan.md`](plan.md).

## 1. Qué problema resuelve

El gate de Plotting es el momento más barato de toda la novela para corregir: no hay una línea escrita, y cambiar la escaleta cuesta un párrafo. Para que ese momento sirva, el Autor necesita tres cosas que el gate tiene que darle a la vez:

- **Poder pedir otra trama** y que el arquitecto la haga de verdad, dirigida por lo que el Autor dijo y sin perder lo que corrigió.
- **Saber qué está mal** en la escaleta antes de decidir: elementos del encargo sin anclar, personajes recurrentes sin arco, cronologías imposibles, capítulos fuera de forma.
- **Ver cómo se cubrió cada hueco** que el arquitecto declaró, y que lo que se encontró o se inventó llegue a la escena que lo necesitaba.

Ninguna de las tres puede convertirse en una puerta que atasque la novela: por el criterio de producto, **nada de lo que aquí se comprueba cierra el gate**. El Autor aprueba cuando quiera; lo que el arnés hace es que aprobar, rehacer y corregir sean decisiones informadas.

## 2. Rehacer la Trama

### 2.1 Cuándo se planifica

`Plan` tiene dos aristas de entrada, y no significan lo mismo. Desde `FillGap` es una vuelta dentro de la misma ejecución: la trama ya está escrita y no se toca. Desde el gate de Plotting, tras «rehacer» o «editar», el Autor ha pedido otra, y el arquitecto tiene que hacerla.

Lo que las distingue es un dato de la base. **`canon_obra.fase_run_id` guarda la ejecución de Plotting que escribió la trama**, y `Plan` planifica en dos casos:

- **No hay trama.** Es la primera pasada.
- **Hay un gate de Plotting decidido como «rehacer» o «editar» en la ejecución que escribió la trama o en una posterior.** Tras planificar, la trama nueva nace con la ejecución en curso como dueña, que es posterior a ese gate, así que la pregunta no se repite en la vuelta siguiente.

Reanudar tras un fallo no pasa por el gate y **no replanifica**. Una trama escrita antes de que `canon_obra` llevara dueño se replanifica si existe cualquier «rehacer» de Plotting.

### 2.2 Qué recibe el arquitecto

Al rehacer, el prompt del arquitecto gana un bloque «Rehacer» con, por este orden:

1. **Todos los comentarios** de los gates de Plotting decididos como «rehacer», en orden, con la indicación de que el último manda.
2. **Los avisos de la revisión** de la trama anterior (§3), con la instrucción de corregirlos.
3. **La trama anterior resumida**: título, premisa y tema; cada personaje con su tipo, estatus, objetivo, miedo y voz **tal como el Autor los dejó en el gate**; y de la escaleta, el título y la función de cada capítulo y el objetivo de cada escena. La instrucción es conservar lo que el comentario no pida cambiar.

El bloque aparece aunque el comentario esté vacío: rehacer sin comentario ya es un reintento dirigido por la revisión.

### 2.3 Qué se sustituye

Tras leer lo anterior, `Plan` **borra la trama entera** —canon, escaleta, arcos, huecos, prohibidas— con su índice semántico en `vec_canon`, retira las incidencias de la revisión anterior, llama al arquitecto y vuelca la nueva. El contador de huecos vuelve a su tope.

El borrado solo es posible antes del sello: si un capítulo escrito apunta a una escena o a un personaje, las claves foráneas lo abortan. Los hechos que cubrieron huecos de la trama anterior **se quedan en el corpus**, porque son hechos, y el arquitecto nuevo puede anclarlos otra vez.

## 3. La revisión de la escaleta

### 3.1 Qué corre y cuándo

Al terminar `Plan`, sobre la trama recién volcada, corre la revisión: `cobertura_anclada`, `arco_anclado`, el rango de escenas por capítulo, los anclajes que el volcado no resolvió y la cronología de §3.3. Lo que encuentra **se guarda como `incidencia` sin capítulo**, con su validador, su severidad, su mensaje y, si la tiene, su ubicación. Cada revisión retira antes lo de la anterior.

Guardarla es lo que permite que la lean tres sitios sin recalcularla: el aviso del gate, la pantalla del gate y el prompt del arquitecto al rehacer.

### 3.2 La cobertura se repara

Un elemento obligatorio del encargo que ninguna escena ancla **se ancla solo** a la escena cuyo objetivo, conflicto y resultado más se le parecen por similitud de coseno entre embeddings. El anclaje lleva `tipo_vinculo = 'elemento del encargo, anclado por el arnes'`, y la revisión deja un aviso `cobertura_reparada` que nombra el elemento por su texto y dice en qué capítulo y escena quedó. Con la reparación hecha, `cobertura_anclada` ya no tiene nada que decir.

### 3.3 La cronología, con o sin Lean

La cronología se deduce de la escaleta: cada escena fechada es un evento con su escenario y sus personajes, y cada personaje una persona con sus fechas vitales. **Quien no tiene fecha de nacimiento recibe un nacimiento tan temprano que ninguna escena cae antes**: «no se sabe» no puede convertirse en «nació el día de la época».

Si `lake` está en el `PATH`, corre Lean. Si no está, o si Lean falla por cualquier avería, **los cuatro invariantes se evalúan en Python** sobre los mismos datos, con las mismas definiciones —igualdad exacta de día en I3, ausencia de fecha como ausencia de restricción— y una regla más: un escenario desconocido no es estar en otro sitio. Cada aviso dice quién, en qué escena y en qué fecha. En los dos caminos las incidencias son **avisos**.

### 3.4 Qué enseña el gate

**El informe del gate**, en el aviso de Telegram y de la CLI, añade al recuento de capítulos, escenas y personajes el informe de la Trama: cada hueco con su escena y cómo se cubrió, los inventados por dimensión, los hechos de la micro-sesión sin respaldo, las escenas poco firmes y los avisos de la revisión marcados como «grave» o «aviso», con la advertencia de que rehacer los lleva al arquitecto.

**La pantalla del gate** enseña una sección «La revisión de la escaleta», antes de la decisión:

- **Los avisos**, lo grave primero, cada uno con una etiqueta legible de su validador —«Arco», «Cronología», «Anclado por el arnés»…— en rojo si es grave y en ámbar si no, y debajo la frase «Ninguno impide aprobar. Si rehaces, el arquitecto recibe estos avisos además de tu comentario».
- **Sin avisos**, «Cobertura, arcos y cronología en verde: la escaleta puede sellarse».
- **Los huecos**, cada uno con su pregunta, su escena —o «sin escena»—, una etiqueta con su resultado —«encontrado» en verde, «inventado» en azul, «sin cubrir» en gris— y el enunciado con que quedó cubierto.
- **Las escenas poco firmes**, si las hay, en una línea.

## 4. Los huecos

### 4.1 Qué declara el arquitecto

Cada hueco lleva **la pregunta**, **la clave de la escena que lo necesita**, **su dimensión** y **`si_no_se_encuentra`**, la afirmación que el arquitecto usaría si la investigación no lo encuentra, escrita como un hecho. El prompt se lo pide así. Una dimensión fuera de las seis cae a `cultura_material`, y un hueco escrito como texto suelto es una pregunta sin escena ni propuesta: ninguno de los dos invalida la salida entera.

### 4.2 Dónde viven

Los huecos se registran en `plan_hueco` al volcar la trama, hasta el tope de cinco. **El estado del grafo lleva sus identificadores**, no su contenido: `huecos_pendientes` es una lista de identificadores en texto. Un pendiente que no es un número —un checkpoint anterior, con la pregunta en claro— se cubre igual, sin escena.

### 4.3 Cómo se cubren

`FillGap` toma el siguiente, llama una vez al investigador y escribe el hecho con la dimensión del hueco:

- **Encontrado**: `origen = 'micro_arquitecto'`, y pasa por el verificador como ya fijaba la spec del backend.
- **No encontrado**: `origen = 'invencion_autorizada'` y **el enunciado es la afirmación propuesta**; solo si el arquitecto no la dio se escribe la pregunta.

En los dos casos el hueco guarda el hecho y su resultado, y **el hecho se ancla a la escena del hueco** con `tipo_vinculo = 'cubre un hueco de la escaleta'`. Los inventados del informe se cuentan sobre los huecos de la trama vigente cuando los hay, de modo que lo inventado para una trama anterior no se atribuye a la nueva.

## 5. Contratos

| Pieza | Cambio |
|---|---|
| `canon_obra` | Gana `fase_run_id INTEGER REFERENCES fase_run(id)`, **columna aditiva**: se añade al abrir si falta, sin subir `VERSION_ESQUEMA` |
| `plan_hueco` | Tabla nueva —`id`, `escena_id`, `pregunta`, `dimension`, `propuesta`, `hecho_id`, `resultado` ∈ {`encontrado`, `inventado`}—, **tabla aditiva**: se crea al abrir si falta |
| `SalidaArquitecto.huecos` | Pasa de `list[str]` a `list[HuecoPropuesto]`, que admite también el texto suelto |
| `GET /api/novelas/{id}/gate` | `GateDeNovela` gana `trama: RevisionDeLaTrama \| null`, presente solo en el gate de Plotting: `avisos` (`validador`, `grave`, `mensaje`, `ubicacion`), `huecos` (`pregunta`, `dimension`, `resultado`, `enunciado`, `capitulo`, `escena`), `inventados` y `escenas_poco_firmes` |

## 6. Requisitos

| ID | Requisito | Clase | Gate |
|---|---|---|---|
| REQ-TR-01 | Tras «rehacer» o «editar» en el gate de Plotting, `Plan` vuelve a llamar al arquitecto y sustituye la trama sin duplicar capítulos, personajes ni obra | T | G4 |
| REQ-TR-02 | Volver de `FillGap` y reanudar tras un fallo no replanifican; la decisión sale de `canon_obra.fase_run_id` frente a los gates de Plotting | T | G4 |
| REQ-TR-03 | Al rehacer, el arquitecto recibe los comentarios, los avisos de la revisión y la trama anterior con las correcciones del Autor | T | G4 |
| REQ-TR-04 | Con un capítulo escrito, la trama no se puede borrar | A | G3 |
| REQ-TR-05 | La revisión corre al terminar `Plan` y se guarda como incidencias sin capítulo, retirando las de la revisión anterior; ninguna cierra el gate | T | G4 |
| REQ-TR-06 | Un elemento obligatorio sin anclar se ancla a la escena más parecida y queda un aviso que dice cuál | T | G4 |
| REQ-TR-07 | Sin `lake`, o si Lean falla, la cronología de la escaleta se evalúa en Python con los mismos invariantes, y quien no tiene fecha de nacimiento no nace el día de la época | T | G4 |
| REQ-TR-08 | Cada hueco se registra con su escena, su dimensión y su afirmación propuesta, y el estado del grafo solo lleva su identificador | T | G1 |
| REQ-TR-09 | El hecho que cubre un hueco se ancla a su escena; el inventado entra con la afirmación propuesta y no con la pregunta | T | G1 |
| REQ-TR-10 | El gate de Plotting sirve la revisión y el informe del aviso la resume; la pantalla enseña los avisos, lo grave primero, y los huecos con su resultado | T | G4 |

REQ-TR-04 es **A** porque lo garantizan las claves foráneas del esquema, con `PRAGMA foreign_keys=ON`, y no una comprobación del código: la prueba solo confirma que el cerrojo está puesto. Los demás son **T**. La evaluación en Python de REQ-TR-07 queda bajo U-1 de [`verification.md`](../../docs/verification.md): su fidelidad a `Cronologia.Basico` se afirma con pruebas, no con una demostración, y se admite porque ahí es un aviso y no una puerta.

## 7. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | Primera versión: rehacer la Trama, la revisión de la escaleta que se guarda y repara, y los huecos con escena | Se propaga §4 (Fase 3) de la arquitectura: el gate de Plotting tiene que permitir pedir otra trama, explicar qué está mal y enseñar cómo se cubrió cada hueco |
