# Spec — La Trama que se puede rehacer

Qué pasa en la Fase 3 cuando el Autor pide otra trama, qué comprueba el arnés sobre la escaleta antes de enseñársela, cómo se resuelve a qué se agarra cada escena y cómo se cubre un hueco para que sirva a una escena. Deriva de [`docs/architecture.md`](../../docs/architecture.md) §4 (Fases 1 y 3), §9, §10, §11a, §11c y §19, y de la spec del backend, [`specs/backend/spec.md`](../backend/spec.md) §4.3 y §4.7. **Si algo de este documento contradice a la arquitectura, manda la arquitectura.** La forma técnica exacta vive en [`plan.md`](plan.md).

## 1. Qué problema resuelve

El gate de Plotting es el momento más barato de toda la novela para corregir: no hay una línea escrita, y cambiar la escaleta cuesta un párrafo. Para que ese momento sirva, el Autor necesita tres cosas que el gate tiene que darle a la vez:

- **Poder pedir otra trama** y que el arquitecto la haga de verdad, dirigida por lo que el Autor dijo y sin perder lo que corrigió.
- **Saber qué está mal** en la escaleta antes de decidir: elementos del encargo sin anclar, anclajes que no apuntan a nada, personajes recurrentes sin arco, cronologías imposibles, capítulos fuera de forma, invenciones que dicen algo de alguien real.
- **Ver cómo se cubrió cada hueco** que el arquitecto declaró, y que lo que se encontró o se inventó llegue a la escena que lo necesitaba.

Ninguna de las tres puede convertirse en una puerta que atasque la novela: por el criterio de producto, **nada de lo que aquí se comprueba cierra el gate**. El Autor aprueba cuando quiera; lo que el arnés hace es que aprobar, rehacer y corregir sean decisiones informadas. Y lo que el arnés puede arreglar sin preguntar —un anclaje escrito como frase, un elemento sin escena, una fecha de nacimiento que dejaría al protagonista sin nacer— lo arregla y lo dice.

## 2. Rehacer la Trama

### 2.1 Cuándo se planifica

`Plan` tiene dos aristas de entrada, y no significan lo mismo. Desde `FillGap` es una vuelta dentro de la misma ejecución: la trama ya está escrita y no se toca. Desde el gate de Plotting, tras «rehacer» o «editar», el Autor ha pedido otra, y el arquitecto tiene que hacerla.

Lo que las distingue es un dato de la base. **`canon_obra.fase_run_id` guarda la ejecución de Plotting que escribió la trama**, y `Plan` planifica en dos casos:

- **No hay trama.** Es la primera pasada.
- **Hay un gate de Plotting decidido como «rehacer» o «editar» en la ejecución que escribió la trama o en una posterior.** Tras planificar, la trama nueva nace con la ejecución en curso como dueña, que es posterior a ese gate, así que la pregunta no se repite en la vuelta siguiente.

Reanudar tras un fallo no pasa por el gate y **no replanifica**. Una trama escrita antes de que `canon_obra` llevara dueño se replanifica si existe cualquier «rehacer» de Plotting.

### 2.2 Qué recibe el arquitecto

El prompt del arquitecto lleva siempre el encargo, el contexto histórico con la firmeza de cada hecho, los elementos del encargo con su clave, la forma de la escaleta —con **la fecha de cada escena en ISO** (§3.3)—, la forma de los huecos (§4.1), **la regla de los arcos** (§3.6) y **la regla de la fecha de nacimiento del homenajeado** (§4.5). Su contrato de salida enumera las claves a las que puede anclar (§3.5).

Al rehacer, el prompt gana un bloque «Rehacer» con, por este orden:

1. **Todos los comentarios** de los gates de Plotting decididos como «rehacer», en orden, con la indicación de que el último manda.
2. **Los avisos de la revisión** de la trama anterior (§3), con la instrucción de corregirlos.
3. **La trama anterior resumida**: título, premisa y tema; cada personaje con su tipo, estatus, objetivo, miedo y voz **tal como el Autor los dejó en el gate**; y de la escaleta, el título y la función de cada capítulo y el objetivo de cada escena. La instrucción es conservar lo que el comentario no pida cambiar.

El bloque aparece aunque el comentario esté vacío: rehacer sin comentario ya es un reintento dirigido por la revisión.

### 2.3 Qué se sustituye

Tras leer lo anterior, `Plan` **borra la trama entera** —canon, escaleta, arcos, huecos, prohibidas— con su índice semántico en `vec_canon`, retira las incidencias de la revisión anterior, llama al arquitecto y vuelca la nueva. El contador de huecos vuelve a su tope.

El borrado solo es posible antes del sello: si un capítulo escrito apunta a una escena o a un personaje, las claves foráneas lo abortan. Los hechos que cubrieron huecos de la trama anterior **se quedan en el corpus**, porque son hechos, y el arquitecto nuevo puede anclarlos otra vez. Por eso el aviso de §4.4 mira todo lo inventado del corpus y no solo lo de la trama vigente: una invención de la trama anterior sigue al alcance del escritor.

## 3. La revisión de la escaleta

### 3.1 Qué corre y cuándo

Al terminar `Plan`, sobre la trama recién volcada, corre la revisión: la reparación de la cobertura (§3.2), `cobertura_anclada`, `arco_anclado` (§3.6), el rango de escenas por capítulo, la cronología (§3.3) y lo inventado sobre personajes históricos (§4.4). A esos se suman los dos avisos que deja el propio volcado (§3.5): los anclajes sin resolver y los resueltos por parecido. Lo que encuentra **se guarda como `incidencia` sin capítulo**, con su validador, su severidad, su mensaje y, si la tiene, su ubicación. Cada revisión retira antes lo de la anterior, salvo los dos avisos del volcado, que el volcado retira y escribe justo antes.

Los huecos se cubren **después** de la revisión, así que lo que `FillGap` inventa se mira en el momento: si nombra a un personaje histórico, `FillGap` deja su aviso (§4.4).

Guardarla es lo que permite que la lean tres sitios sin recalcularla: el aviso del gate, la pantalla del gate y el prompt del arquitecto al rehacer.

### 3.2 La cobertura se repara, y mira antes la fecha

Un elemento obligatorio del encargo que ninguna escena ancla **se ancla solo** a una escena, en dos pasos:

1. **La fecha estrecha las candidatas.** Si el elemento nombra un año —y el evento ancla trae el suyo, porque se busca con `evento_ancla` y `fecha_evento_ancla` del encargo—, compiten solo las escenas cuya `fecha_narrativa` nombra ese año, y de ellas las que nombran también su mes, si las hay. Años y meses se leen en cifra, en ISO o con el nombre del mes en castellano. Sin fecha en el elemento, o sin ninguna escena de su año, compiten todas: la fecha estrecha la búsqueda, nunca la deja sin candidatas.
2. **El parecido elige entre ellas**: la de objetivo, conflicto y resultado más parecidos por similitud de coseno entre embeddings.

El anclaje lleva `tipo_vinculo = 'elemento del encargo, anclado por el arnes'`, y la revisión deja un aviso `cobertura_reparada` que nombra el elemento por su texto y dice en qué capítulo y escena quedó. Con la reparación hecha, `cobertura_anclada` ya no tiene nada que decir.

### 3.3 La cronología, con o sin Lean

La cronología se deduce de la escaleta: cada escena fechada es un evento con su escenario y sus personajes, y cada personaje una persona con sus fechas vitales. **Quien no tiene fecha de nacimiento recibe un nacimiento tan temprano que ninguna escena cae antes** (`NACIMIENTO_DESCONOCIDO`): «no se sabe» no puede convertirse en «nació el día de la época». La cronología de la publicación usa la misma regla, de modo que un personaje sin fecha significa lo mismo en los dos sitios.

**Las fechas se leen con `leer_fecha`, que devuelve el momento y su precisión** —`dia`, `mes` o `anio`—:

- **ISO**, `AAAA`, `AAAA-MM` o `AAAA-MM-DD`, que es lo que pide el contrato del arquitecto: el campo `fecha_narrativa` lo describe así en el JSON Schema, y el prompt pide que la hora del día o «días después» vayan en la escena y no en la fecha. La precisión es la de las partes presentes.
- **Prosa**, si no es ISO: el año es **el primer número de cuatro cifras**, esté donde esté; el mes, su nombre en castellano —también «setiembre»—, y sin nombre de mes, una estación como mes aproximado: invierno enero, primavera abril, verano julio, otoño octubre; el día, el número de 1 a 31 que va justo delante del mes, con o sin «de». Un rango, «1846-1850», se lee por su principio. La precisión es `dia` con día y mes, `mes` con mes o estación, y `anio` con solo el año.
- **Sin año de cuatro cifras**, se lee el número del principio como año —«711 d.C.»—, salvo que el texto nombre un mes: «24 junio» sin año no es una fecha.

**Solo una escena fechada al día conserva su escenario** en la cronología; a las demás se les da el escenario desconocido. Así el invariante de los dos sitios —que compara días exactos— no convierte dos escenas «de 1856» en dos sitios el 1 de enero, y el nacimiento, la muerte y el orden siguen contando para todas. Con Lean el escenario desconocido no está exento de I3 como lo está en Python, así que una escena sin día puede coincidir con otra fechada justo el día 1 del mismo mes; se admite porque aquí es un aviso. El día es la unidad del modelo: moverse de un sitio a otro dentro del mismo día sigue avisando.

Si `lake` está en el `PATH`, corre Lean. Si no está, o si Lean falla por cualquier avería, **los cuatro invariantes se evalúan en Python** sobre los mismos datos, con las mismas definiciones —igualdad exacta de día en I3, ausencia de fecha como ausencia de restricción— y una regla más: un escenario desconocido no es estar en otro sitio. Cada aviso dice quién, en qué escena y en qué fecha. En los dos caminos las incidencias son **avisos**.

### 3.4 Qué enseña el gate

**El informe entero** sale por la salida del proceso, en la CLI: el recuento de capítulos, escenas y personajes y el informe de la Trama —cada hueco con su escena y cómo se cubrió, los inventados por dimensión, los hechos de la micro-sesión sin respaldo, las escenas poco firmes y los avisos de la revisión marcados como «grave» o «aviso», con la advertencia de que rehacer los lleva al arquitecto—.

**El aviso de Telegram** lo resume en cifras, porque se lee en un móvil y se decide en el PC:

- el título, «StoryMaker · ‹novela› · Trama: espera tu decisión»;
- una línea con los capítulos, las escenas y los personajes;
- los huecos, «N encontrados, M inventados»;
- la revisión, «N avisos, G graves», y debajo una línea por tipo de aviso con su etiqueta legible y su número, lo grave primero; sin avisos, «Revisión en verde»;
- y «Decide en el PC».

Las etiquetas son las mismas que las de la pantalla, para que el móvil y el PC hablen igual.

**La pantalla del gate** enseña una sección «La revisión de la escaleta», antes de la decisión:

- **Los avisos**, lo grave primero, cada uno con una etiqueta legible de su validador —«Arco», «Cronología», «Anclado por el arnés», «Anclado por parecido», «Invención sobre un histórico»…— en rojo si es grave y en ámbar si no, y debajo la frase «Ninguno impide aprobar. Si rehaces, el arquitecto recibe estos avisos además de tu comentario».
- **Sin avisos**, «Cobertura, arcos y cronología en verde: la escaleta puede sellarse».
- **Los huecos**, cada uno con su pregunta, su escena —o «sin escena»—, una etiqueta con su resultado —«encontrado» en verde, «inventado» en azul, «sin cubrir» en gris— y el enunciado con que quedó cubierto.
- **Las escenas poco firmes**, si las hay, en una línea.

### 3.5 A qué se agarra cada escena

**Las claves válidas viajan en el contrato del arquitecto.** Su JSON Schema enumera en el campo `hecho` del anclaje los `#id` de los hechos que ve en el contexto, y en el campo `dato` los de los elementos del encargo; el prompt le dice que ancle con esas claves. **La enumeración guía y no valida**: Pydantic acepta cualquier texto en esos campos, porque rechazar un anclaje mal escrito tumbaría la llamada más cara de la fase por un despiste.

Lo que no llega como clave se resuelve al volcar, en tres pasos, del más fiable al menos:

1. **La clave o el texto exacto, en su campo**: `hecho` contra el corpus, `dato` contra el encargo. El texto se compara normalizado.
2. **Lo mismo, en el campo cruzado**: un elemento del encargo escrito en `hecho` es el elemento, y un hecho escrito en `dato` es el hecho.
3. **Por parecido léxico**, primero contra los elementos del encargo —que es lo que la cobertura exige— y después contra el corpus. Se comparan las palabras con contenido, las de cuatro letras o más y los años, tras normalizar; un texto se elige si comparte con el anclaje **al menos dos de ellas y seis de cada diez de las del anclaje**. Entre varios gana el de mayor proporción y, a igualdad, el que menos palabras le sobran.

Un anclaje resuelto por parecido deja un aviso **`anclaje_por_parecido`** que dice la escena, lo que escribió el arquitecto y la clave y el texto a los que se resolvió. Solo lo que ni así apunta a nada queda como aviso **`anclaje_resuelto`** y no se escribe. Los dos avisos los escribe el volcado.

### 3.6 El orden de los hitos

`arco_anclado` exige que los hitos de un arco positivo o negativo **no retrocedan de capítulo**: dos hitos pueden compartir capítulo. El aviso dice «los hitos retroceden de capítulo» con la lista. El umbral de escenas a partir del cual se exige arco sigue siendo tres, también en las novelas cortas.

**El arquitecto conoce la regla desde su prompt**, con los números de la configuración: cuándo hace falta arco, que el plano sin hitos vale, cuántos hitos lleva uno positivo o negativo y en qué orden, y que el del homenajeado no puede ser plano y cierra en el tercio final.

## 4. Los huecos

### 4.1 Qué declara el arquitecto

Cada hueco lleva **la pregunta**, **la clave de la escena que lo necesita**, **su dimensión** y **`si_no_se_encuentra`**, la afirmación que el arquitecto usaría si la investigación no lo encuentra, escrita como un hecho. El prompt se lo pide así, y le pide además que **esa afirmación no atribuya cargos, oficios, lugares ni actos a personajes históricos reales**: lo que se inventa es el ambiente, no la biografía de nadie. Una dimensión fuera de las seis cae a `cultura_material`, y un hueco escrito como texto suelto es una pregunta sin escena ni propuesta: ninguno de los dos invalida la salida entera.

### 4.2 Dónde viven

Los huecos se registran en `plan_hueco` al volcar la trama, hasta el tope de cinco. **El estado del grafo lleva sus identificadores**, no su contenido: `huecos_pendientes` es una lista de identificadores en texto. Un pendiente que no es un número —un checkpoint anterior, con la pregunta en claro— se cubre igual, sin escena.

### 4.3 Cómo se cubren

`FillGap` toma el siguiente, llama una vez al investigador y escribe el hecho con la dimensión del hueco:

- **Encontrado**: `origen = 'micro_arquitecto'`, y pasa por el verificador como ya fijaba la spec del backend.
- **No encontrado**: `origen = 'invencion_autorizada'` y **el enunciado es la afirmación propuesta**; solo si el arquitecto no la dio se escribe la pregunta.

En los dos casos el hueco guarda el hecho y su resultado, y **el hecho se ancla a la escena del hueco** con `tipo_vinculo = 'cubre un hueco de la escaleta'`. Los inventados del informe se cuentan sobre los huecos de la trama vigente cuando los hay, de modo que lo inventado para una trama anterior no se atribuye a la nueva.

### 4.4 Lo inventado sobre personajes históricos

Todo hecho con `origen = 'invencion_autorizada'` que nombra a un personaje histórico deja un aviso **`invencion_sobre_historico`**, con ubicación `hecho #id`, que dice el nombre y el enunciado entero y pide corregirlo antes de sellar si no es cierto.

- **Quién es histórico**: los personajes del canon de tipo `historico_ficcionalizado` o `historico_de_fondo` y los `personajes_historicos` del encargo, deban aparecer o no, **sin el homenajeado**, que puede ser `historico_ficcionalizado` y es de quien la novela tiene que inventar.
- **Cuándo lo nombra** (`nombra_a`): el enunciado, partido en palabras y normalizado, contiene **el nombre entero** o, si el nombre tiene más de una palabra, **su último apellido** cuando tiene cinco letras o más **y va con mayúscula** en el texto. Ninguna de las dos formas cuenta **detrás de una palabra de lugar** —avenida, barrio, café, calle, canal, colegio, compañía, convento, estación, fuente, fundación, glorieta, hospital, hotel, iglesia, instituto, museo, palacio, parque, paseo, plaza, premio, puente, puerta, puerto, ronda, teatro o universidad—, saltando los «de», «del» y artículos de en medio: el Canal de Isabel II no es la reina, y «el valle del Lozoya» no es Lucio del Valle.
- **Dónde corre**: en la revisión, sobre todo lo inventado del corpus; en `FillGap`, sobre el hecho que acaba de inventar; y **tras una edición directa de un hecho o de un personaje**, otra vez sobre todo el corpus, retirando antes los avisos anteriores. La revisión no se repite al editar, y sin esto el aviso de un hecho ya corregido seguiría en la pantalla.

Es un aviso: el Autor lo corrige con la edición directa del hecho o rehace. No pasa por el verificador, porque una invención no tiene cita y el verificador diría siempre que el corpus no la sostiene.

### 4.5 La fecha de nacimiento del homenajeado

La fecha de nacimiento del homenajeado **en el canon es la de su personaje en la época**. El prompt se lo pide al arquitecto, y el volcado del canon lo asegura eligiendo, para el homenajeado:

1. la que propone el arquitecto, si le da al menos `EDAD_MINIMA_RAZONABLE` años —la del Intake, doce— al final del período;
2. si no, la del encargo, con la misma condición;
3. si ninguna, ninguna: sin fecha no hay restricción (§3.3), y una fecha falsa sí la hay.

En el Intake, una fecha de nacimiento posterior al período **no es una contradicción que preguntar**: es la fecha real, y el aviso de `contradiccion_del_brief` dice que se toma como tal y que el arquitecto le dará a su personaje una de la época. Tampoco se contrasta con el evento ancla.

## 5. Contratos

| Pieza | Cambio |
|---|---|
| `canon_obra` | Gana `fase_run_id INTEGER REFERENCES fase_run(id)`, **columna aditiva**: se añade al abrir si falta, sin subir `VERSION_ESQUEMA` |
| `plan_hueco` | Tabla nueva —`id`, `escena_id`, `pregunta`, `dimension`, `propuesta`, `hecho_id`, `resultado` ∈ {`encontrado`, `inventado`}—, **tabla aditiva**: se crea al abrir si falta |
| `SalidaArquitecto.huecos` | Pasa de `list[str]` a `list[HuecoPropuesto]`, que admite también el texto suelto |
| `con_claves(hechos, datos)` | Devuelve una subclase de `SalidaArquitecto` cuyo JSON Schema enumera `#id` en `AnclajePropuesto.hecho` y `.dato`; valida igual que `SalidaArquitecto` |
| `incidencia` sin capítulo | Dos validadores nuevos de severidad `aviso`: `anclaje_por_parecido`, que escribe el volcado, e `invencion_sobre_historico`, que escriben la revisión, `FillGap` y `POST /api/novelas/{id}/ediciones` al editar un hecho o un personaje |
| `escenas_con_texto` | Devuelve también `fecha_narrativa` |
| `NACIMIENTO_DESCONOCIDO`, `nacimiento_de` | Viven en `commons/formal/generador`; los usan la revisión de la escaleta y la cronología de la publicación |
| `leer_fecha(texto) -> FechaLeida` | `momento` y `precision` ∈ {`dia`, `mes`, `anio`, vacía}; `a_momento` devuelve su `momento`, y el ISO se lee igual que antes |
| `EscenaPropuesta.fecha_narrativa` | Su JSON Schema la describe como «AAAA, AAAA-MM o AAAA-MM-DD»; sigue aceptando cualquier texto |
| Aviso de un gate | `abrir` recibe el informe entero, que imprime, y el resumen para el móvil, que envía |
| `GET /api/novelas/{id}/gate` | `GateDeNovela` gana `trama: RevisionDeLaTrama \| null`, presente solo en el gate de Plotting: `avisos` (`validador`, `grave`, `mensaje`, `ubicacion`), `huecos` (`pregunta`, `dimension`, `resultado`, `enunciado`, `capitulo`, `escena`), `inventados` y `escenas_poco_firmes` |

## 6. Requisitos

| ID | Requisito | Clase | Gate |
|---|---|---|---|
| REQ-TR-01 | Tras «rehacer» o «editar» en el gate de Plotting, `Plan` vuelve a llamar al arquitecto y sustituye la trama sin duplicar capítulos, personajes ni obra | T | G4 |
| REQ-TR-02 | Volver de `FillGap` y reanudar tras un fallo no replanifican; la decisión sale de `canon_obra.fase_run_id` frente a los gates de Plotting | T | G4 |
| REQ-TR-03 | Al rehacer, el arquitecto recibe los comentarios, los avisos de la revisión y la trama anterior con las correcciones del Autor | T | G4 |
| REQ-TR-04 | Con un capítulo escrito, la trama no se puede borrar | A | G3 |
| REQ-TR-05 | La revisión corre al terminar `Plan` y se guarda como incidencias sin capítulo, retirando las de la revisión anterior; ninguna cierra el gate | T | G4 |
| REQ-TR-06 | Un elemento obligatorio sin anclar se ancla a la escena más parecida entre las de su fecha, y queda un aviso que dice cuál | T | G4 |
| REQ-TR-07 | Sin `lake`, o si Lean falla, la cronología de la escaleta se evalúa en Python con los mismos invariantes, y quien no tiene fecha de nacimiento no nace el día de la época | T | G4 |
| REQ-TR-08 | Cada hueco se registra con su escena, su dimensión y su afirmación propuesta, y el estado del grafo solo lleva su identificador | T | G1 |
| REQ-TR-09 | El hecho que cubre un hueco se ancla a su escena; el inventado entra con la afirmación propuesta y no con la pregunta | T | G1 |
| REQ-TR-10 | El gate de Plotting sirve la revisión y el informe del proceso la da entera; la pantalla enseña los avisos, lo grave primero, y los huecos con su resultado | T | G4 |
| REQ-TR-11 | El contrato del arquitecto enumera las claves de anclaje válidas sin rechazar las que no lo son | T | G1 |
| REQ-TR-12 | Un anclaje se resuelve en su campo, en el cruzado o por parecido léxico, y lo resuelto por parecido deja aviso | T | G4 |
| REQ-TR-13 | Los hitos de un arco pueden compartir capítulo y avisan solo si retroceden | T | G4 |
| REQ-TR-14 | Todo hecho inventado que nombra a un personaje histórico que no es el homenajeado deja aviso, en la revisión y en `FillGap`, y el aviso se recalcula tras editar un hecho o un personaje | T | G4 |
| REQ-TR-15 | La fecha de nacimiento del homenajeado en el canon da edad en el período o no existe, y la publicación trata la ausencia como la revisión | T | G5 |
| REQ-TR-16 | El aviso de Telegram de un gate resume en cifras, con los avisos de la Trama agrupados por tipo, y el informe entero sale por el proceso | T | G4 |
| REQ-TR-17 | Las fechas de la escaleta se leen en ISO o en prosa, con su precisión, y solo las fechadas al día conservan su escenario en la cronología | T | G4 |
| REQ-TR-18 | Un nombre histórico detrás de una palabra de lugar, o un apellido suelto en minúscula, no cuenta como nombrar a la persona | T | G4 |
| REQ-TR-19 | El prompt del arquitecto dice la regla de los arcos y pide las fechas de escena en ISO | T | G4 |

REQ-TR-04 es **A** porque lo garantizan las claves foráneas del esquema, con `PRAGMA foreign_keys=ON`, y no una comprobación del código: la prueba solo confirma que el cerrojo está puesto. Los demás son **T**. La evaluación en Python de REQ-TR-07 queda bajo U-1 de [`verification.md`](../../docs/verification.md): su fidelidad a `Cronologia.Basico` se afirma con pruebas, no con una demostración, y se admite porque ahí es un aviso y no una puerta. REQ-TR-15 va a **G5** porque lo que protege es la cronología de la publicación, la única de las tres que impide publicar.

## 7. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | §3.3 gana la lectura de fechas en prosa con su precisión, y el escenario desconocido para lo que no está fechado al día; §3.6, la regla de los arcos en el prompt; §4.4, los nombres detrás de una palabra de lugar y el apellido con mayúscula; §2.2 y §5 se ajustan. Entran REQ-TR-17 a REQ-TR-19 | Se propagan §4 (Fase 3), §11c y §17 de la arquitectura |
| 2026-09-24 | Segunda versión, reescrita: las claves de anclaje en el contrato y la resolución en tres pasos (§3.5), la reparación que mira la fecha (§3.2), el orden de los hitos (§3.6), lo inventado sobre personajes históricos (§4.4), la fecha de nacimiento de época del homenajeado (§4.5) y el aviso de Telegram en cifras (§3.4). Entran REQ-TR-11 a REQ-TR-16 y REQ-TR-06, REQ-TR-10 se precisan | Se propagan §4 (Fases 1 y 3), §10, §11a, §17 y §19 de la arquitectura |
| 2026-09-24 | Primera versión: rehacer la Trama, la revisión de la escaleta que se guarda y repara, y los huecos con escena | Se propaga §4 (Fase 3) de la arquitectura: el gate de Plotting tiene que permitir pedir otra trama, explicar qué está mal y enseñar cómo se cubrió cada hueco |
