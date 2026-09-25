# Registro de iteraciones

Qué se cambió, **por qué** y qué efecto tuvo. Una fila por iteración, en orden cronológico inverso: lo más reciente arriba.

No es un registro de commits —para eso está `git log`— ni el registro de cambios de un documento, que anota qué párrafo se tocó. Aquí se anota la **cadena causa → efecto**: qué observación provocó el cambio, qué se hizo y qué se midió después. Una iteración sin efecto medido es una iteración sin terminar, y se marca como tal.

Cada documento mantiene además su propio registro de cambios al final. Cuando una iteración de aquí toca un documento, se anota en ambos sitios: aquí el porqué, allí el qué.

---

## 2026-09-25 · El arnés contra sus requisitos

### It-40 · Tres defectos que solo salieron corriendo los ejemplos: Lean averiado y ramas sin hilo

**Causa.** Al correr los briefs de [`ejemplos/evals/`](../ejemplos/evals) con `lake` en el `PATH`, dos novelas coherentes acabaron en `Fail` desde `PublishVersion` con la misma incidencia: «la cronología no supera la verificación formal y la salida no nombra ningún invariante conocido». En `eval-01-jubilacion`, `lake exe verificar` había salido con `unspecified system_category error (error code: 4551)`: Smart App Control de Windows bloquea a veces el ejecutable recién recompilado, y al repetir la misma cronología daba «✓ coherente, 57 eventos, 6 personas». En `eval-02-hijo`, `Generado.lean` no compilaba: el generador escribía `muerte := some -4035` para Carlos III, que muere antes del origen de la cronología, y Lean lo lee como una resta. Aparte, las ramas de `storymaker ramificar` nacían con el checkpoint vacío (`pc = None`), así que ni se continuaban ni se regeneraban: el hilo de LangGraph se llama como el fichero (`run._hilo`), y la copia traía el checkpoint bajo el nombre del origen.

**Qué se hizo.** Las tres cosas alinean el código con decisiones ya fijadas; ninguna cambia la arquitectura.
- [`generador.py`](../backend/src/storymaker/commons/formal/generador.py) escribe `some (-n)` para los negativos.
- [`runner.interpretar`](../backend/src/storymaker/commons/formal/runner.py) lanza `AveriaDeLean`, un `ErrorDeEntorno`, cuando `verificar` sale con fallo sin nombrar ningún invariante, en lugar de abrir una incidencia bloqueante genérica. `verificar_cronologia` ya capturaba las excepciones de Lean y caía a la evaluación en Python, que es lo que piden §11c de la arquitectura y las specs `escritura` y `validacion` («si Lean falla por cualquier avería»). Nada se da por bueno sin juzgar: la avería la juzga Python con la misma severidad.
- [`branch.ramificar`](../backend/src/storymaker/commons/graph/branch.py) muda `checkpoints` y `writes` al hilo de la rama, que es lo que §8 promete al decir que la rama «se continúa desde ahí».

**Efecto medido.** Pruebas nuevas en `tests/unit/test_formal.py` (paréntesis, avería y caída a Python con la misma severidad) y en `tests/integracion/test_invocacion.py` (la rama hereda su hilo). La suite del backend da 1106 pasadas; los 7 fallos de `tests/correspondencia/test_matrices.py` son anteriores y se deben a que falta `trace-matrix.md` en la raíz. Las novelas que ya habían caído por esto se reabrieron fuera del grafo: la publicación de `eval-01`, repitiendo con Lean y como salida de `AwaitApproval4`, y las ramas `fase-6-*`, reasignando su hilo a mano. Ninguna se publicó sin pasar G5.

**Pendiente.** Que el sistema no deje ejecutar un binario sin firma sigue siendo un riesgo de entorno en Windows. Ahora degrada a Python (U-1) en lugar de tumbar la publicación, pero la score no dice qué motor juzgó.

### It-39 · Un muerto recordado no participa

**Causa.** La novela de prueba `prueba-langfuse` agotó dos veces los reintentos del capítulo 2, en seis versiones, todas por `cronologia_capitulo`. Según esa regla, el abuelo del homenajeado, muerto en 1790 según el canon, participaba en eventos de 1805. El texto era correcto: lo recordaba como «su difunto abuelo», porque el brief exige el elemento obligatorio «aprendió a navegar con su abuelo en una txalupa». El fallo estaba en el extractor. Contaba como participante a quien solo se nombra, porque ni el esquema de `EventoNarrativo.participantes` ni su prompt decían lo contrario. Ningún parche del editor podía arreglarlo sin quitar el elemento obligatorio.

**Qué se hizo.** A petición del Autor, se aplicó directamente, sin pasar antes por la spec de escritura. El campo `participantes` de [`writing/esquemas.py`](../backend/src/storymaker/writing/esquemas.py) lleva ahora una `description`, que viaja en el contrato de salida. El catálogo del extractor, en [`writing/extraccion.py`](../backend/src/storymaker/writing/extraccion.py), dice que solo participan los presentes, y que quien se recuerda, se nombra, se sueña o ya ha muerto no participa.

**Efecto medido.** Hay una prueba nueva en `test_writing.py::TestCatalogoDelExtractor`, y pasan las 80 de escritura e integración. Sobre la novela real, `storymaker reintentar prueba-langfuse` reescribió el capítulo 2 y lo aprobó al primer intento, sin incidencias. El juez dio 5,625, y la versión 1 se publicó con su PDF. La novela entera costó 263 058 + 190 192 tokens y 1,7172 $, y Langfuse da lo mismo en su sesión. El score del juez y los de publicación llegan a Langfuse colgados de la traza de la generación (It-37), no de la sesión.

**Deuda.** La [spec de escritura](../specs/escritura/spec.md) no recoge la regla.

### It-38 · Los validadores que cierran la novela, Lean de verdad y un modelo que termina

**Causa.** El Autor pidió cerrar todo el apartado de validación del enunciado. Una lectura del árbol contra §11 de la [arquitectura](architecture.md) dio siete huecos:

- `render_visual` buscaba tres identificadores en el HTML y no abría ningún navegador.
- Un rechazo de la publicación lanzaba una excepción y terminaba la novela en `Fail`, sin devolver nada a nadie.
- `cobertura_personalizacion` estaba escrita y registrada, pero no la llamaba ningún nodo.
- El juez no puntuaba el tono.
- La revisión humana no tenía herramienta.
- `lake` no estaba instalado, así que Lean no había corrido nunca en el flujo.
- TLC no terminaba.

**Qué se hizo.** Primero se escribió arriba: §9, §11a-§11d y §17 de la arquitectura, y la [spec](../specs/validacion/spec.md), el [plan](../specs/validacion/plan.md) y la matriz de `specs/validacion/`. Después, el código:

- **El render.** `render_visual` abre la lectura candidata en Chromium, comprueba que portada, índice y fichas se pintan y pulsa cada enlace del índice. Lo que no se ve cita su pieza o su capítulo. Sin navegador, avisa y sigue.
- **El rechazo.** `PublishVersion` gana dos aristas, al gate de Writing y a `Fail`, con el tope del juez. El rechazo queda como incidencia que cita capítulos. Rehacer en el gate reescribe esos capítulos, y su escritor lee el motivo en el bloque 1.
- **La cobertura.** `cobertura_personalizacion` corre en cada llegada al gate de Writing, también en batch.
- **El juez y la revisión humana.** El juez gana `tono` como octavo criterio. `storymaker revision hoja` y `registrar` hacen la hoja, el *score* y el acta.
- **Lean.** Se instaló elan con el toolchain v4.15.0 y `lake build` compila el proyecto. Con Lean, **Lean decide y Python explica**, porque las incidencias de Lean no decían a quién ni cuándo. Lean trabaja en una copia de `formal/lean` para no pisar el `Generado.lean` versionado. La suite lo apaga con `STORYMAKER_LEAN=0`, porque con él tardaba nueve minutos.
- **El modelo.** El modelo TLA+ gana las acciones `Caida`, `ResumeFromCheckpoint` y `Reintentar`, las dos aristas de `PublishVersion` y un entorno acotado.

**Efecto medido.**

- **Lean sobre las tres novelas publicadas** en `proyectos/`:
  - `metro` falla I1 en la prosa (26 eventos) y en la escaleta (9 escenas). La homenajeada tiene en el canon su nacimiento real, de 1967, y la novela la sitúa en 1917. Cuando se generó, solo lo avisó la cronología de la escaleta en el gate de Plotting; ni los deterministas ni el juez lo vieron, y se publicó. Es el caso real que pide el enunciado, contado en [`formal/lean/README.md`](../formal/lean/README.md).
  - `lozoya` falla I3 en la escaleta y pasa en la prosa.
  - `pepa` pasa las dos.
  - Python y Lean coinciden en los seis veredictos.
- **TLC**, con un JRE portátil:
  - `harness.cfg` agota 12.650 estados distintos y `harness_batch.cfg`, 4.425, cada una en un segundo, sin ninguna violación de los cinco invariantes ni de las dos propiedades temporales.
  - Cambiando `SF` por `WF` en una copia, TLC viola `Termina` con la traza del Autor que rehace sin fin, así que la comprobación no es vacía.
  - El modelo ampliado no dio ningún contraejemplo nuevo. Lo que impedía terminar era que el modelo no era finito: sin cota al lector, `versiones` crecía con cada regeneración.
- **La inspección en el navegador** de la interfaz de lectura de las tres novelas encontró que en `metro` los cinco lugares «no aparecían en ningún capítulo». Ninguna escena tenía escenario, porque el volcado exigía la clave exacta. Provocó `resolver_escenario` y está en [`inspeccion-visual.md`](inspeccion-visual.md). El nuevo `render_visual` no dio incidencias sobre ninguna de las tres.
- **La suite.** Pasan 1086 pruebas, con 1 omitida, y 26 son nuevas. Fallan las siete de `test_matrices.py` por la ausencia del `trace-matrix.md` de la raíz, igual que en It-37. Con Chromium abierto en las pruebas que publican, la suite pasa de un minuto a casi dos.

**Deuda.**

- La revisión humana tiene herramienta y ninguna acta: la escribe una persona que haya leído una novela entera (REQ-VA-15).
- Las tres novelas publicadas no se han vuelto a volcar, así que `metro` sigue sin escenarios en sus escenas.
- El MCP de Playwright no conectó en la sesión de la inspección, que se hizo con la librería.

### It-37 · La traza de una generación, con capítulos, latencia, herramientas y prompts

**Causa.** El Autor señaló que faltaba todo lo de Langfuse del enunciado. Tras It-36 llegaban a Langfuse los tokens y el coste de cada invocación, en la sesión de su novela, pero cuatro cosas no salían. Primera: cada invocación era su propia traza, mientras que el enunciado pide una traza por generación, y una generación cruza seis o siete procesos de la CLI por los gates. Segunda: las llamadas a herramientas no aparecían. Tercera: la latencia era cero, porque la observación se abría y se cerraba en el mismo instante. Cuarta: ningún nodo rellenaba la versión de prompt ni había forma de sembrar los prompts. It-36 anotaba además que los deterministas no puntuaban; ya lo hacen desde `validar_determinista`, que escribió la sesión que lleva la validación.

**Qué se hizo.** Se siguió el flujo completo. Primero se reescribió §14 de la [arquitectura](architecture.md) con la forma de la traza y se añadieron tres filas a §17. Después, un grilling con cinco decisiones: el Autor pidió que las resolviera el agente, y se tomaron las recomendaciones. Por último, la [spec](../specs/observabilidad/spec.md), el [plan](../specs/observabilidad/plan.md) y su matriz. El resultado:
- El id de la traza se deriva de la novela y de la versión objetivo.
- Hay un span `capitulo_NN` que agrupa a sus invocaciones.
- Cada `generation` lleva inicio y fin reales, calculados con `duration_ms` y fijados con el tracer interno del SDK, con la vía pública como respaldo (U-20).
- Cada llamada a herramienta es una observación `tool`, leída del flujo de mensajes.
- Los *scores* van a la traza de su generación.
- Los nodos pasan la versión y el nombre del prompt, y `python -m storymaker.commons.obs.prompts subir` crea en Langfuse los prompts que faltan.
- El Span del juez vive en `publication/nodos.py`, que en ese momento editaba la sesión de validación; lo cambia ella.

**Efecto medido.**
- Hay 15 pruebas nuevas, 14 en `test_observabilidad.py` y una en `test_contabilidad.py`. Una de ellas corre el observador sobre el SDK real con un exportador en memoria: los cuatro spans comparten el id de traza esperado y la sesión, la jerarquía es capítulo → `generation` → `tool` y las latencias son las del SDK (2500 y 1000 ms).
- De la suite pasan 1085, con dos omitidas. Fallan las siete de `test_matrices.py` por la ausencia del `trace-matrix.md` de la raíz, igual que en It-35 e It-36.
- **No se ha medido** nada contra un Langfuse de verdad, porque en esta máquina no hay claves (REQ-OB-14).

**Deuda.** Las aserciones de G6 siguen ensayándose contra `ObservadorNulo` y no contra la API. Los *datasets* de evaluación no existen, porque los briefs de `evals/` están borrados.

### It-36 · Dos hooks, herramientas con esquema y el coste de la novela en Langfuse

**Causa.** Una revisión del repositorio contra la lista de requisitos del arnés encontró cuatro huecos. El hook de validación leía `$CLAUDE_FILE_PATH`, que Claude Code no define, y saltaba con cualquier fichero. No había hook de policy propio. Ninguna herramienta tenía un esquema del arnés. Y `ObservadorLangfuse` llamaba a `trace()` y `score()`, que no existen en langfuse 4.15.4, sin abrir nunca la sesión.

**Qué se hizo.** A petición del Autor, se implementó directamente, sin pasar antes por la arquitectura, la spec y el plan, y sin grilling. La [spec](../specs/final/spec.md) y el [plan](../specs/final/plan.md) de `specs/final/` se escribieron después, describiendo lo que ya estaba hecho. El hook de validación lee el evento por `stdin`, solo mira capítulos y bloquea por `stderr`. Hay un hook de policy en `PreToolUse` que deniega la edición que introduce un término prohibido. El arquitecto tiene dos herramientas de fechas con entrada Pydantic, servidas por un servidor MCP en proceso. Y el observador usa la API v4, con una `generation` por invocación y la novela como sesión.

**Efecto medido.** Hay 40 pruebas nuevas en `test_herramientas.py`, `test_hooks_de_claude.py`, `test_observabilidad.py` y `test_contabilidad.py`. De la suite pasan 1047, con una omitida. Fallan las siete de `test_matrices.py` porque el `trace-matrix.md` de la raíz no está en el árbol, igual que en It-35. Los dos hooks se ejecutaron por su comando real con un evento de prueba, y la policy denegó con 2. Con las claves ya puestas, una novela real de dos capítulos en batch (`prueba-langfuse`) dejó 14 `generation` en su sesión de Langfuse, con 153 126 + 99 786 tokens y 1,0058 $. Son exactamente los de `storymaker estado`. La novela terminó en `Fail` en el capítulo 2, por reintentos agotados desde `Extract`, así que no llegó al juez. **No se ha medido** si el arquitecto llegó a usar sus herramientas: el span no lo registra.

**Deuda.** §5 y §12 de [`architecture.md`](architecture.md) no recogen que el arquitecto tiene herramientas. La matriz consolidada no existe. Y `registrar_veredicto` sigue sin llamarse desde los validadores deterministas.

## 2026-09-25 · La Fase 6 de verdad

### It-37 · La novela que se reescribe, en la columna de Publicación

**Causa.** Durante la reescritura de `lozoya`, el tablero la ponía en la columna de Publicación, «en marcha», mientras el panel decía Escritura. `fase_actual` elige la fase más avanzada que haya trabajado, y una novela publicada ya tiene Publication trabajada aunque lo que corre sea Writing.

**Qué se hizo.** En [`seguimiento.py`](../backend/src/storymaker/api/seguimiento.py), `fase_actual` devuelve, **tras publicar**, la fase de la última `fase_run` si sigue abierta. Antes de publicar se mantiene la regla de siempre, porque la novela solo avanza y hay novelas antiguas con su única fila de fase abierta.

**Efecto medido.** Una prueba nueva en `test_seguimiento.py`: la semilla publicada con todas sus filas cerradas sale en `publication`, y con una ejecución de Writing abierta sale en `writing`. Pasan las 85 de la API. El servidor en marcha no se ha reiniciado, porque tenía evals en curso, así que el cambio entra en el próximo arranque.

### It-36 · El nombre nuevo no llegaba al texto

**Causa.** La primera regeneración real, un cambio de nombre de personaje en `lozoya`, recorrió la Fase 6 entera y publicó la versión 2, pero el nombre nuevo no aparecía en ningún capítulo y el viejo seguía en todos. El paquete del escritor llevaba el nombre nuevo una vez, en la ficha del canon, y el viejo de tres a seis veces: siete beats de `plan_beat` y la prosa del capítulo anterior en la memoria. Ningún validador miraba el nombre retirado. Además, el capítulo 3 lo nombraba y quedó fuera del alcance, porque ni `continuidad` ni la escaleta ni `uso_hito` lo registraban. Las pruebas de It-35 pasaban porque el agente falso no escribe nombres: comprobaban la maquinaria, no que el cambio llegara.

**Qué se hizo.** `regeneration/retirados.py` y §9 de la [spec de escritura](../specs/escritura/spec.md), con REQ-ES-13 a REQ-ES-15 y los ítems ES-13 y ES-14. Un cambio de nombre de personaje o de término de glosario hace ahora tres cosas más:
- reescribe el valor viejo, como palabra entera, en las columnas de texto de `plan_*` y `canon_*`;
- suma al alcance los capítulos cuyo texto aprobado lo dice;
- mientras dura la regeneración, lleva los pares en `EstadoNovela.retirados`, y la pasada determinista, también en la revisión de los invalidados, marca como bloqueante cada valor viejo que conserve el capítulo.

**Efecto medido.** En `lozoya`, con el canon devuelto al nombre viejo y la petición repetida, la propagación reescribió siete celdas y el alcance pasó de cuatro capítulos a cinco. Los cinco regenerados dicen el nombre nuevo 5, 3, 1, 2 y 2 veces y el viejo ninguna, y la escaleta ya no lo contiene. El validador nuevo no llegó a saltar: con la escaleta coherente y la memoria ya regenerada, el escritor no escribió el nombre viejo. Los dos segundos intentos, del 3 y del 5, fueron por longitud. Diez pruebas nuevas: nueve en `test_valor_retirado.py` y una de integración en la que el escritor conserva el nombre y el editor lo repara. La ejecución se cortó una vez a mitad al caerse el servidor que la había lanzado, y se retomó con `desbloquear` y `continuar` desde el checkpoint, sin repetir capítulos.

### It-35 · Un cambio aprobado que no llegaba a ninguna parte

**Causa.** Al preguntar el Autor cómo se propaga un cambio sobre la novela terminada, la lectura del código dio tres huecos, y una prueba con un grafo mínimo confirmó el primero. **Uno:** a `RequestChange` no llegaba ninguna arista ni ninguna invocación. El gate de Regeneración lo abre la API como fila, no un `interrupt()`, y `decidir` reanudaba con `Command(resume=...)` un hilo que ya había terminado en `Idle`: LangGraph devolvía el estado sin ejecutar nada e `invocar` cerraba la fase como **completada**. Es muy probablemente el síntoma de It-30, «terminó en `Idle` sin gastar un token», que allí se atribuyó a la resolución de la fila. **Dos:** si hubiera entrado, `Checkpoint` sumaba uno y `WriteChapter` reescribía todo lo posterior, la cascada que §4 descarta; `a_regenerar` y `regenerando` no los leía nadie. **Tres:** ningún código pasaba los validadores de coste cero a los `invalidado` ni los devolvía a `aprobado`, así que `publicar` los habría rechazado.

**Qué se hizo.** §9 de la [spec de escritura](../specs/escritura/spec.md), con REQ-ES-08 a REQ-ES-12 y los ítems ES-09 a ES-12. `decidir` sobre un gate de Regeneración llama a `regenerar`, que escribe `pc = RequestChange` en el checkpoint como salida de `Idle` —el mismo truco que `reintentar`— y `Idle` gana un router, `tras_idle`. `Checkpoint`, en regeneración, saca el siguiente de `a_regenerar` y, con la cola vacía, pasa `revisar_invalidados`: determinista y cronología sobre las filas ya escritas; los que pasan vuelven a `aprobado` y los que fallan entran en la cola. Sin nada que regenerar no se entra en el grafo: sin fila ni valor no se toca nada, con una fila que nadie usa se aplica sin versión nueva, y rehacer o editar descartan la petición.

**Lo que destapó la prueba.** Un hecho del corpus no se puede cambiar en una novela publicada: el sello hace `mundo_hecho` de solo lectura por *trigger*, y `RequestChange` reventaba. `/ediciones` ya lo rechazaba; `regenerar` ahora también, con una nota. Contradice a §8 de la arquitectura, que dice «el corpus se re-sella», y queda abierto.

**Lo que no se hizo.** El modelo TLA+ sigue con la guarda `~regenerando` en `Checkpoint → WriteChapter` y con un solo capítulo invalidado por petición. El conjunto de aristas no cambia y la prueba de identidad pasa, pero la guarda del código ya no es la del modelo, y **TLC no se ha vuelto a pasar**: esta máquina no tiene JVM. Siguen abiertos también el «rehacer» del gate de Writing, que vuelve a `WriteChapter` con `capitulo = N + 1`, y `/ediciones`, que cambia la fila sin propagar.

**Efecto medido.** Seis pruebas nuevas en [`test_regeneracion.py`](../backend/tests/integracion/test_regeneracion.py): cambiar el nombre de un personaje que sale en el capítulo 1 publica una versión 2 con el 1 regenerado y el 2 reutilizado —el escritor se llama una vez— y la versión 1 intacta; con un evento imposible sembrado en el 2, Lean lo tumba y se reescribe también, y su versión vieja se queda `invalidado`; los tres caminos sin grafo no escriben versión. Pasan 1041 de la suite; fallan las siete de `test_matrices.py` porque `trace-matrix.md` de la raíz ya no está en el árbol.

## 2026-09-24 · La firmeza de los hechos

### It-33 · Un verificador menos estricto con lo que el fragmento calla

**Causa.** La primera novela en modo exhaustivo sacó 57 hechos, 44 documentados, pero 11 cayeron a `inferido` sin merecerlo. El prompt del verificador llamaba dato central a las fechas, cifras, nombres y lugares, y la cita es un fragmento que no repite lo que la página da por sabido: «tranvías e iluminación eléctricos» no dice «Barcelona 1887-1888» porque eso lo dice el título. Además, cuatro parciales no enseñaban su nota, porque el verificador copió el añadido con otras palabras. El Autor vio todo en `inferido` mirando la salida a mitad de la investigación, antes de que el verificador pasara.

**Qué se hizo.** En [`architecture.md`](architecture.md) §4, el dato central pasa a ser lo que el hecho dice que existió u ocurrió; la fecha o el lugar que la cita no trae son un añadido y dan parcial. El Autor descartó darle al verificador el título de la fuente: sigue viendo solo el par enunciado–cita. `anadido_vigente` reconoce el añadido por sus palabras significativas, y la pantalla etiqueta «En proceso de verificación» lo que aún no se ha verificado. GI-31 a GI-33 del [plan](../specs/gate-investigacion/plan.md).

**Efecto medido.** 923 pruebas del backend y 111 del frontend en verde. Los cuatro parciales que no enseñaban su nota la enseñan ya, con la regla nueva. El prompt nuevo no se ha medido sobre una investigación real: el corpus de la novela de prueba se verificó con el anterior.


### It-32 · El respaldo parcial y una firmeza que se usa

**Causa.** La primera novela verificada con firmeza sacó seis hechos no respaldados, y en los seis el dato central estaba literalmente en la cita: el verificador rechazaba una glosa del investigador. Los catorce hechos venían declarados `verificado`, porque se le pedía juzgar un consenso historiográfico que con una página no puede conocer. Y la firmeza llegaba al escritor y al arquitecto sin ninguna instrucción, así que no cambiaba nada de lo que se escribía. El Autor pidió además una sola etiqueta por hecho, y al leer «sin fuente» entendió que se quitaba la fuente.

**Qué se hizo.** Se fijó en [`architecture.md`](architecture.md) §4, §6, §7 y §17: el veredicto parcial, guardado como `respaldado` con el añadido en la columna nueva `sin_respaldo`; los estados redefinidos respecto a lo que dice la fuente, con los nombres de siempre; las lagunas sin verificar; qué hacer con cada firmeza, para el escritor y para el arquitecto; el aviso de escenas poco firmes en Plotting, y la firmeza como única etiqueta en pantalla. El añadido se enseña como «No lo dice la cita», y la cita y las fuentes siguen donde estaban. Bajó a las specs y al [plan](../specs/gate-investigacion/plan.md), GI-18 a GI-29.

**Lo que apareció en el grilling del plan.** Subir `VERSION_ESQUEMA` para la columna nueva habría hecho que el servidor de la interfaz, arrancado con el código anterior, se negara a abrir cualquier novela que el nuevo tocara, con una Ejecución viva de por medio. La columna es aditiva y admite nulos, así que se añade al abrir, sin subir la versión.

**Efecto medido.** 919 pruebas del backend y 107 del frontend en verde, `tsc` limpio. No se ha medido todavía sobre una investigación real: el corpus de la novela de prueba se verificó con el veredicto binario.


### It-31 · Un dueño por columna, y la firmeza calculada

**Causa.** Al repasar con el Autor los niveles de las afirmaciones de la investigación salieron tres incoherencias. `inferido` significaba a la vez «lo deduje», «la cita no lo sostiene» e «inventado con permiso». Degradar un hecho `desconocido` sin respaldo lo pasaba a `inferido`, que es un escalón más firme. Y los hechos de la micro-sesión de Plotting se quedaban en `respaldo = 'pendiente'` para siempre, porque el verificador corre antes.

**Qué se hizo.** Se fijó en [`architecture.md`](architecture.md) §7 que `estado` lo escribe quien crea la fila, `respaldo` solo el verificador, y que lo que ven el arquitecto y el escritor es la **firmeza**, calculada al leer por [`puras.firmeza`](../backend/src/storymaker/commons/validation/puras.py) como el mínimo entre lo declarado y lo que el respaldo permite. `FillGap` pasa ahora por el verificador cada hecho que encuentra la micro-sesión, y el sello incluye el respaldo. Bajó a la spec del backend, a la del gate de Investigación y a su [plan](../specs/gate-investigacion/plan.md), GI-08 a GI-17.

**Lo que apareció al implementar.** El prompt de la micro-sesión **no pedía la cita**: solo el dato. Con el verificador ya conectado en `FillGap`, todo lo que la micro-sesión encontrara habría salido `no_respaldado` por falta de fragmento. Se le añadió el mismo bloque «De cada hecho guarda» que usan la sesión única y las dirigidas, que lleva la cita y ahora también las definiciones de los cuatro estados. Se propagó a §4.3 de la spec del backend y a GI-13.

**Efecto medido.** Las 48 combinaciones de la regla, contra la tabla de §7 escrita a mano; 898 pruebas del backend y 102 del frontend en verde, `tsc` limpio. Los tipos del frontend se regeneraron con `scripts/generar-tipos.ts`.

**Deuda.** El verificador por lotes sigue escribiendo el veredicto en el `hecho_id` que el modelo devuelva, aunque no esté en el lote. `verificar_hecho` ya lo protege para un solo hecho; el lote no se tocó porque no era parte de este cambio.

## 2026-09-24 · La interfaz opera el arnés

### It-24 · Del lector al taller

**Causa.** El Autor vio la interfaz de lectura de It-21 y la describió como «súper pobre»: no salían todas las novelas, y no había forma de lanzar una ejecución, seguirla ni consultar lo que dejaba cada fase. Lo primero era un servidor de demo apuntado a otra carpeta. Lo segundo contradecía una decisión fijada: solo la CLI reanudaba una ejecución.

**Qué se hizo.** Se preguntó al Autor antes de escribir nada, y decidió que **la interfaz lo opere todo**, con un panel moderno y el lector en maqueta de libro. Pidió además que el taller fuera **un tablero tipo Jira** donde arrastrar una tarjeta aprueba su gate. La decisión se escribió en §16.5 de la arquitectura, conservando la razón de ser de la anterior en lugar de su letra: cada acción que ejecuta el grafo **lanza la CLI como proceso aparte**, el servidor no guarda nada en memoria y la API solo acepta acciones locales y en JSON. El grilling restringió «abortar» al gate de Intake, la única arista del modelo TLA+, y convirtió «editar» en corregir filas antes de aprobar o rehacer. Bajó a §5 de la spec del backend (P-160 a P-166), a la spec del frontend reescrita (REQ-FE-52 a REQ-FE-92) y a su plan (IMP-34 a IMP-46), con las tres matrices al día, y se implementó: seguimiento, salidas por fase, operación con su lanzador, `entities/novela`, tablero, encargo, panel, gate, salidas y tokens de diseño en claro y oscuro.

**Efecto medido.** 64 pruebas de API, 38 de ellas nuevas; 81 del frontend con MSW, entre ellas el arrastre con su confirmación, las acciones por estado, las preguntas de Intake y el editor que nunca envía `editar`. El inventario de P-129 queda en cero en las dos direcciones. Sobre las dos novelas reales publicadas, nueve pantallas sin errores de consola, y una acción real que la API lanzó desacoplada y la CLI rechazó en su propio registro.

**Deuda o pendiente.** El aviso de Telegram todavía no lleva la dirección de la pantalla del gate que promete §10. Falta encargar una novela desde la interfaz y seguirla hasta publicarla, que cuesta una ejecución completa. `render_visual` e `imprimir_pdf` siguen sin usar la ruta de impresión de React (It-21).

## 2026-09-24 · La cuarta novela real

### It-26 · Leer la novela entera

**Causa.** La cuarta novela real, *La cartógrafa del corazón*, se publicó con un 7,4 del juez y un 8 en continuidad, y al leerla aparecieron defectos que ningún validador mira:

- **Contradicciones de trama.** La firma del mapa se contradice en cinco capítulos: Magallanes promete llevar el nombre de Inés en los márgenes, luego «su nombre no estaría en él», luego lo firma ella y al final «Magallanes desconoce el nombre». La navaja del padre se entrega dos veces.
- **Conocimiento imposible.** Magallanes, antes de zarpar, dice «esto no es lo que encontré… llegué más al sur».
- **Repetición.** «Precisión» aparece 63 veces y «treinta años» 34, y los capítulos 8 y 9 cierran con el mismo párrafo.
- **Forma.** El tiempo verbal pasa de pretérito a presente en el capítulo 8, y en el capítulo 4 aparecen encabezados de escena.

La causa común es que el escritor solo ve N−1: el estado de continuidad dice qué posee cada personaje, pero no qué se prometió o se entregó tres capítulos atrás, y la repetición de la novela entera no la ve nadie. El juez sí podía ver las contradicciones, pero su nota no dependía de ellas.

**Qué se hizo.** En §6 de la [arquitectura](architecture.md), el bloque 3 lleva **lo que ya ha pasado**: los eventos narrativos que el extractor ya escribía para Lean, de los capítulos aprobados anteriores a N−1. Su techo sube a 2.500 a costa de la memoria, que baja a 3.000. El bloque 6 lleva cuatro **reglas de escritura** fijas y **lo que la novela ya ha gastado**: las palabras y expresiones más repetidas y la frase con la que cerró cada capítulo. En §11b, el juez **enumera las contradicciones** antes de puntuar, y Python topa la continuidad a `10 − 2·n`. Hay dos filas nuevas en §17, REQ-BE-145 a REQ-BE-147 en la spec del backend, y `P-150` a `P-152` en el plan. Los encabezados markdown los quita ya `texto.sin_encabezados` al guardar el capítulo (It-25).

**Efecto medido.** Hay trece pruebas nuevas en `test_contexto_de_trama.py`:

- el recuento de repeticiones, sin los nombres del canon;
- los eventos del capítulo 1 en el bloque 3 del capítulo 3, sin los de un intento descartado y sin los de N−1;
- los techos, que siguen sumando 12.000;
- las reglas fijas y la frase de cierre del anterior;
- el tope de continuidad.

Sobre la base de la novela de Sevilla, el paquete del capítulo 10 habría llevado 46 eventos en el bloque 3 dentro de su techo. En el bloque 6 habría ido la lista «precisión» (48), «treinta años» (32) y «sus manos» (21), y entre los cierres ya usados el «Y por fin descansa» que el capítulo 9 repitió. La suite completa pasa: 787 pruebas. **El efecto sobre la prosa está sin medir** hasta la próxima novela real.

**Deuda o pendiente.** Los errores de dato histórico que contradicen el corpus —la corte de Carlos I en Sevilla en 1517, «Río de la Plata» en 1518— siguen sin comprobación: `anacronismo_fechado` solo mira entidades con fecha, y el escritor recibe del corpus lo que la búsqueda semántica le acerca, no lo que su escena contradice.

### It-23 · El capítulo 8 y el mismo texto tres veces

**Causa.** La cuarta novela real se detuvo en el capítulo 8 de 10, con siete aprobados. `cobertura_capitulo` bloqueó los tres intentos porque el extractor no declaró usado el elemento «aprendió a dibujar copiando los mapas que guardaba su padre». El elemento estaba escrito de forma indirecta: «la letra que había practicado treinta años copiando los antiguos», «Es de mi padre». La incidencia lo nombraba solo por su identificador —«no aparecen: [1]»—, así que el editor no sabía qué faltaba, y **los tres intentos tienen el mismo texto, carácter por carácter**. Con el capítulo en `Fail`, el grafo había terminado y `continuar` no tenía nada que retomar: la única salida era empezar de nuevo.

**Qué se hizo.** §11a de la [arquitectura](architecture.md) hace que `cobertura_capitulo` avise en lugar de bloquear, y la cobertura que bloquea queda en `cobertura_personalizacion`, antes de publicar. §16.5 añade `storymaker reintentar`, con dos filas nuevas en §17. En la spec del backend, §6 y §7.2 con REQ-BE-137 y REQ-BE-138, y en el plan, `P-143` y `P-144`. La incidencia nombra ahora cada elemento por su texto, y el registro de validadores la declara no bloqueante. `reintentar` escribe en el checkpoint un capítulo recién empezado como salida de `SealCorpus` y reanuda por `invocar`, sin tocar lo aprobado.

**Efecto medido.** Dos pruebas nuevas de `reintentar`. En la primera, una novela cae en el capítulo 1 por longitud, se reabre y llega a publicarse, con los intentos fallidos conservados como filas y su `fase_run` de Writing cerrada como `fallida`. En la segunda, una novela que espera en un gate rechaza el comando sin tocar nada. `test_writing.py` comprueba que el aviso lleva el texto del elemento, y `test_core_domain.py` que bloquean diez de los once validadores programáticos. La suite completa pasa: 717 pruebas.

**Deuda o pendiente.** El extractor sigue sin reconocer un elemento escrito de forma indirecta. Ya no detiene el capítulo, pero la cobertura de la novela depende de que algún capítulo lo nombre de manera que el extractor lo vea; si ninguno lo hace, lo detiene `cobertura_personalizacion` en G5.

### It-22 · Una sola `fase_run` y un coste de cero dólares

**Causa.** La cuarta novela real, en Sevilla entre 1517 y 1519, llegó al gate de Plotting con el corpus investigado y la escaleta escrita, y `storymaker estado` seguía diciendo «Fase: intake» y «0 + 0 tokens, 0.0000 $». En la base había una sola fila de `fase_run`, la que `invocar` abre para un `Arranque`, todavía `en_curso`. Ninguna otra fase abría la suya, nada cerraba esa fila si todo iba bien, y el consumo de cada llamada al modelo solo llegaba a los *spans* del observador. Como todos los hechos del corpus colgaban de esa misma fila, rehacer Investigation desde su gate habría mezclado el corpus nuevo con el anterior.

**Qué se hizo.** §9.1 y §9.2 de la [spec de ejecución real](../specs/ejecucion-real/spec.md) pasan de describir el defecto a fijar el contrato, con REQ-ER-25, REQ-ER-26 y REQ-ER-36. El detalle está en su [plan](../specs/ejecucion-real/plan.md), y en el plan del backend como `P-141` y `P-142`. Un envoltorio común a los veinticuatro nodos, puesto en `nodos_resueltos`, abre la fila de cada fase según `FASE_DE_NODO`: la abre cuando la fase cambia o cuando la abierta ya no está en curso, que es rehacer desde un gate. `invocar` cierra la última fila al salir del grafo, también tras reanudar. El estado lleva `corpus_run_id`, con el que `Research`, `VerifyCorpus`, `FillGap` y `SealCorpus` escriben, verifican y sellan el corpus. El consumo lo cuenta un `TransporteContado` alrededor del transporte, y el envoltorio reparte la diferencia de cada nodo entre el estado y la fila.

Contarlo en el transporte y no en cada nodo agente, como decía la versión anterior de §9.2, cubre por construcción a todos los nodos, juez incluido, y cuenta también los reintentos de esquema que `invocar_rol` descarta. La fila abierta es la última de la base y no la que apunta el estado, porque la Fase 6 abre la suya desde la API antes de que corra ningún nodo.

**Efecto medido.** Nueve pruebas nuevas en `tests/integracion/test_contabilidad.py`. En batch, una novela deja cinco filas, de `intake` a `publication`, todas `completada`, encadenadas por `input_run_id` y con tokens, y el consumo de la invocación es su suma. El corpus, huecos de `FillGap` incluidos, se escribe y se sella bajo la fila de Investigation. Con gates, la fila del gate queda `esperando_gate` y la anterior `completada`. Rehacer Investigation abre una segunda fila, y los hechos nuevos llevan su identificador sin mezclarse con los de la primera. La suite completa pasa: 713 pruebas.

**Deuda o pendiente.** Las lecturas del corpus que no filtran por ejecución —el contexto del arquitecto, `anclaje_valido` y el resumen del gate de Investigation— siguen viendo los hechos de todas las ejecuciones. Tras un rehacer, verían también los de la ejecución descartada. Las novelas que ya estaban a medias no traen `corpus_run_id` en su checkpoint y siguen con su única fila: el envoltorio la toma como su corpus, y la primera fase nueva la cierra como `completada`.

---

## 2026-09-24 · El frontend

### It-21 · La API que el frontend consume no era la que las specs describían

**Causa.** Al implementar [`specs/frontend/plan.md`](../specs/frontend/plan.md) contra la API real aparecieron tres huecos. La API servía la ficha de personajes sin versión, el manifiesto sin bloque de paratexto y los capítulos sin título, aunque §5 de la spec del backend ya contrataba las dos primeras cosas (P-110); `estaticos.py` servía un HTML propio en `/lectura` en lugar del `dist/` de React (P-136); y todas las respuestas eran `dict[str, Any]`, con lo que los tipos que IMP-05 deriva del OpenAPI no decían nada. Además, con un solo origen, la aplicación y la API chocaban: las dos tienen rutas `/novelas/…`.

**Qué se hizo.** La API pasa a `/api` y FastAPI sirve el `dist/` con *fallback* a `index.html` en el manejador de `404`, solo para `GET`. Los endpoints de lectura declaran modelos Pydantic y devuelven lo que las dos specs pedían: paratexto, ficha versionada con personajes y escenarios, historial con fecha y puntuación, título de capítulo y versión anterior. La petición de cambio recibe el fragmento y lo usa en la búsqueda. El frontend entero —seis pantallas, cliente único, modo impresión— se construye sobre esa superficie, con los tipos generados. Se propagó a §5 de la spec del backend, §2.1 de la del frontend y el plan del frontend, cada uno con su fila de registro.

**Efecto medido.** 26 pruebas de API en verde, 8 de ellas nuevas sobre una novela sembrada de dos versiones, y 5 sobre el `dist/` servido. 46 pruebas del frontend con MSW, incluidas las de estructura: cliente único, sin copia local, capas y alias. El inventario de P-129 pasa de diez módulos del frontend «presente y no declarado» a cero. Un recorrido con Playwright contra FastAPI sirviendo el `dist/` encontró las cuatro regiones `data-render` e imprimió el documento a PDF.

**Deuda o pendiente.** `render_visual` y `imprimir_pdf` (P-92, P-94) siguen juzgando e imprimiendo el HTML que arma `publication/render.py`, no la ruta de impresión de React interceptando sus peticiones: el frontend es interceptable, pero el lado del backend no está escrito. IMP-29 e IMP-30 quedan sin cerrar porque ninguna novela tiene todavía una versión publicada; el acta de [`frontend/tests/recorrido.md`](../frontend/tests/recorrido.md) registra el ensayo.

## 2026-09-24 · La tercera novela real

### It-34 · Seis capítulos en la escaleta y un séptimo en el bucle

**Causa.** Revisando cómo se fija la longitud desde la interfaz apareció un desajuste latente. El encargo por conversación solo envía el nombre del homenajeado y una descripción, así que el lanzamiento no trae capítulos y el estado del grafo arrancaba con los diez por defecto. El arquitecto, en cambio, planifica con el `n_capitulos` del `Brief` que cierra el entrevistador. Si el comprador pedía seis en la conversación, la escaleta tenía seis y el bucle de Writing iba a por el séptimo, que se detenía con `EscaletaAusente`; si pedía quince, se escribían diez y cinco capítulos de la escaleta se quedaban sin escribir.

**Qué se hizo.** §4 de la [arquitectura](architecture.md), §4.1 de la [spec del backend](../specs/backend/spec.md) con REQ-BE-216 y `P-68` del plan. Al cerrar el `Brief`, `Configure` escribe su `n_capitulos` en el estado.

**Efecto medido.** Una prueba nueva en `test_intake.py`: lanzada con diez y cerrada con tres, el estado acaba con tres. Pasan las 921 de la suite.

### It-30 · Quitar un apellido

**Causa.** El Autor seleccionó el apellido del protagonista en la novela de Cáceres ya publicada y pidió que no apareciera. La petición llegó con su fragmento y sus candidatos, el gate de Regeneration se aprobó con esa frase como comentario, y la fase terminó en `Idle` sin gastar un token ni publicar versión nueva. Había tres desviaciones de la spec: al aprobar, `RequestChange` volvía a buscar con el texto del comentario y se quedaba con el primer candidato —un personaje que no era el protagonista—, en vez de aplicar lo que el Autor había confirmado; sin `campo=valor`, la frase entera se tomaba como valor nuevo; y el alcance de un personaje solo miraba los hitos de su arco, no los capítulos donde se le nombra.

**Qué se hizo.** §4 de la [arquitectura](architecture.md), §4.6 de la [spec del backend](../specs/backend/spec.md) con REQ-BE-196 a REQ-BE-198, y `P-95` y `P-97` del plan. La aprobación lleva la fila elegida y su valor —`personaje:1 nombre=Manuel`— y `resolver_eleccion` los aplica sin buscar; una aprobación sin ellos no toca nada; el alcance de un personaje sale de `continuidad`, `plan_escena_personaje` y `uso_hito`. La pantalla del gate, que es de otra sesión, pasa a ofrecer los candidatos como opciones y un campo con el valor nuevo.

**Efecto medido.** Cuatro pruebas nuevas en `test_regeneracion_eleccion.py`. Pasan las 813 de la suite. Ninguna fila de la novela de Cáceres quedó estropeada por el intento anterior: la frase no se escribió en ninguna tabla.

### It-28 · El investigador que no entregaba

**Causa.** Una novela nueva —Imperio romano bajo Marco Aurelio, Cáceres, años 161-180, en modo estándar y con gates— pasó el gate de Intake y se detuvo en Research con «La salida no es JSON valido». El investigador consumió 58.341 tokens de entrada y dejó cero hechos y cero fuentes, y el reintento de esquema acabó igual. Lo que encaja: en un período con poca información en la red siguió buscando tras gastar su cuota, cada intento denegado le costó un turno, el mensaje de denegación solo decía «cuota agotada», y agotó los doce turnos sin llegar a entregar el JSON. Lo único que recogió el transporte fue su texto intermedio.

**Qué se hizo.** §4 de la [arquitectura](architecture.md), §4.2 de la [spec del backend](../specs/backend/spec.md) con REQ-BE-194 y REQ-BE-195, y `P-69` del plan. El motivo de la denegación le dice al rol que no insista y entregue ya lo que tenga; la sesión única pasa de doce a veinte turnos; y una sesión única sin respuesta válida deja un aviso en el gate y la fase sigue con el corpus que haya, como una sesión dirigida del modo exhaustivo.

**Efecto medido.** Dos pruebas nuevas: el motivo de la denegación y la sesión sin JSON que no detiene la fase. Pasan las 805 de la suite. La novela se relanzó desde la interfaz.

### It-27 · La investigación exhaustiva

**Causa.** La tercera novela real salió con doce hechos, siete de cultura material, y sus errores históricos venían de lo concreto del encargo: la fecha de detención de la figura real, el evento ancla sin narrar y la ley de imprenta que era el conflicto de la trama. Tres páginas repartidas por el modelo entre seis dimensiones no llegaban a eso.

**Qué se hizo.** §4, §12, §15, §17, §18 y §19 de la [arquitectura](architecture.md), sometidos a grilling; §4.2 de la [spec del backend](../specs/backend/spec.md) con REQ-BE-148, REQ-BE-149 y REQ-BE-190 a REQ-BE-193; `P-153`, `P-154`, `P-73` y `P-74` del plan. El modo exhaustivo corre ocho sesiones dirigidas en serie —seis por dimensión, personajes con evento ancla, oficio— con un perfil nuevo de una búsqueda y una página. El grilling destapó que `pii_en_prompt_de_investigacion` existía y tenía pruebas pero no la llamaba nadie: ahora mira todo prompt del investigador antes de emitirlo, y la regla de Semgrep deja de tratar el rol de época como dato personal. La API y la casilla del encargo las añadió otra sesión (REQ-BE-182, REQ-FE-99).

**Efecto medido.** Diez pruebas nuevas en `test_investigacion_exhaustiva.py`: las ocho sesiones y su informe, las seis cuando el brief no trae personajes ni oficio, el comentario en todas, una sesión inválida que se salta, un nombre del homenajeado escrito en el oficio que no sale a internet y la elección de sesión según el modo. Pasan las 797 de la suite. Falta verlo en una novela real.

### It-25 · Lo que la novela terminada enseñó

**Causa.** Leída entera, la novela de Salamanca —diez capítulos, versión 1, 7,86 del juez— tenía tres defectos que ninguna puerta había visto. «Herejía» y «arruinada» estaban en el texto con «hereje» y «ruina» prohibidas: la comparación por palabra completa solo cazaba la forma exacta, el plural y los acentos. Cinco capítulos repetían su título dentro del texto («# Capítulo 1: El Oficio»), y otra novela traía además encabezados de escena («## Escena 1: …»): el escritor los mete a veces y se guardaban tal cual. Y el evento ancla, el regreso de fray Luis a su cátedra en diciembre de 1576, no se narró: el capítulo 9 se quedó en su liberación. Anclarlo era una instrucción al arquitecto, no una comprobación.

**Qué se hizo.** §4 y §11a de la [arquitectura](architecture.md), §4.1, §4.4 y §7.2 de la [spec del backend](../specs/backend/spec.md) con REQ-BE-140 a REQ-BE-142, y `P-41`, `P-68` y `P-81` del plan. `guardrail_prohibidas` busca además la raíz del término —la palabra sin su vocal final, de al menos cuatro letras— dentro de cada palabra, así que «asa» sigue sin saltar en «casa». `insertar_capitulo_version` quita toda línea de encabezado markdown, de cualquier nivel, antes de guardar y de contar palabras. `Brief.elementos_a_cubrir` añade el evento ancla como elemento obligatorio, e Intake lo vuelca con los demás: desde ahí lo ven el arquitecto, `cobertura_anclada` y `cobertura_personalizacion`.

**Efecto medido.** Cinco pruebas nuevas: tres derivadas que saltan, los encabezados que no se guardan y el evento que entra como obligatorio. Pasan las 651 unitarias, de correspondencia, de contratos y adversarias, y las 30 de integración.

**Deuda o pendiente.** Siguen sin puerta las erratas de la prosa —una palabra inglesa, «se sintió» por «se sentó»—, las contradicciones entre capítulos y la fidelidad histórica fina, como la fecha de la detención de fray Luis. Las tres dependen hoy del juez, que puntuó la novela más alto que una lectura atenta.

### It-29 · «Fray» a principio de frase

**Causa.** La novela de Salamanca agotó los reintentos del capítulo 9. El primer intento lo tumbó `nombres_exactos`: el canon registra «fray Luis de León», con minúscula, y el capítulo lo escribía «Fray Luis de León» al abrir frase. El validador comparaba carácter a carácter, y lo que es ortografía del castellano contaba como un nombre mal escrito.

**Qué se hizo.** §11a de la [arquitectura](architecture.md), la fila de §7.2 de la [spec del backend](../specs/backend/spec.md) con REQ-BE-139 y `P-41` del plan: `nombres_exactos` acepta el nombre con la primera letra en mayúscula. Cualquier otra diferencia sigue bloqueando. Dos pruebas nuevas en `test_core_domain.py`: «Fray Luis de León» pasa y «Fray luis de León» sigue saltando.

**Efecto medido.** Las dos pruebas pasan. La novela se retomó desde el capítulo 9 con este cambio y con `cobertura_capitulo` ya en aviso (It-23).

### It-19 · Un `INSERT` ignorado y un `lastrowid` ajeno

**Causa.** Un encargo nuevo, [`ejemplos/brief-salamanca.yaml`](../ejemplos/brief-salamanca.yaml) —Salamanca, 1572-1576, diez capítulos, en batch—, se detuvo dos veces con `FOREIGN KEY constraint failed`, ya con el catálogo de It-17 en su sitio: en el capítulo 3 y en el 4, las dos veces en un intento posterior al primero. La traza señaló `volcar_cronologia`, al escribir `cronologia_participante`. Los participantes estaban en dominio; el evento no. Los eventos se escriben con `INSERT OR IGNORE` sobre `cap<N>-<clave>`, el segundo intento repetía las claves del primero y su `INSERT` se ignoraba, y el código tomaba `lastrowid` como id del evento. Tras un `INSERT` ignorado, `lastrowid` conserva el último id insertado en la conexión, de cualquier tabla.

**Qué se hizo.** §7.3 de la [spec de ejecución real](../specs/ejecucion-real/spec.md) fija que un evento con clave ya escrita no se duplica ni cuelga sus participantes de otro, con REQ-ER-35. `volcar_cronologia` mira `rowcount` y salta el evento si no hubo fila. Una prueba de `test_writing.py` vuelca dos intentos con las mismas claves y exige `PRAGMA foreign_key_check` vacío; contra el código anterior falla.

**Efecto medido.** La prueba pasa con el cambio y falla sin él.

**Deuda o pendiente.** Los eventos de un intento posterior cuya clave ya existe no se registran: la cronología de ese capítulo sigue siendo la del primer intento que la escribió. Es lo que ya hacía el `OR IGNORE`, ahora sin romper la transacción.

### It-20 · Telegram callaba en batch

**Causa.** Con `--batch` los gates se desactivan, y los gates eran lo único que avisaba. Las dos caídas de It-19 solo se supieron mirando la terminal, y tampoco habría llegado nada al terminar la novela.

**Qué se hizo.** §10 de la [arquitectura](architecture.md), §9.5 de la spec de ejecución real con REQ-ER-32 a REQ-ER-34, y `P-140` del plan del backend: tres avisos fuera de gate —parada, final y aparcamiento— que salen siempre. `invocar` emite los dos primeros al salir del grafo y `aparcar` el tercero, todos a través de `avisar_sin_fallar`, de modo que un aviso perdido no cambia el resultado. `invocar` y `reanudar` aceptan un `notifier` inyectable.

**Efecto medido.** Siete pruebas nuevas en `test_gates.py`, `test_invocacion.py` y `test_extremo_a_extremo.py`: el texto de los tres avisos, la parada en un fallo, el silencio en un gate, el final con su versión y un notifier que revienta sin tumbar nada. Las 31 pruebas de esos tres ficheros pasan.

**Deuda o pendiente.** `aparcar` avisa, pero ningún nodo lo llama todavía: el *timeout* de `P-107` no está cableado, así que el aviso de aparcamiento no puede salir en una ejecución real hasta que lo esté.

---

## 2026-09-24 · La segunda novela real

### It-17 · El extractor adivinaba los identificadores

**Causa.** Un encargo nuevo, [`ejemplos/brief-exposicion.yaml`](../ejemplos/brief-exposicion.yaml) —Barcelona, 1888, diez capítulos, en batch—, se detuvo dos veces con `FOREIGN KEY constraint failed`: en el capítulo 5 y en el 10, las dos con el capítulo ya escrito y validado. El extractor de capítulo tiene que devolver `hecho_id`, `dato_id`, `personaje_id`, `escenario_id`, participantes e hitos, y su prompt era solo la prosa. La arquitectura (§4) le prometía la escaleta y el código no se la daba. Adivinaba, y cuando adivinaba un número que no existía, el volcado reventaba en la clave foránea. Cuando acertaba era por casualidad: en los cuatro primeros capítulos quedaron **una** fila en `uso_hecho` y **una** en `intake_uso_dato`, y `arco_ejecutado` avisaba en cada capítulo de que sus hitos no habían ocurrido, porque el extractor no sabía cuáles eran.

**Qué se hizo.** Bajó de arriba abajo: §7.3 de la [spec de ejecución real](../specs/ejecucion-real/spec.md) fija el catálogo y entra REQ-ER-30; `P-31` y `P-83` del plan lo declaran. En el código, `extraccion.catalogo` monta la escaleta del capítulo y el catálogo de identificadores. `schema_guard.validar` acepta un contexto de validación, `invocar_rol` se lo pasa, y `SalidaExtractorDeCapitulo` rechaza cualquier identificador que no esté en el `Dominio`, con la lista de admitidos en el mensaje, que es lo que el reintento le inyecta al modelo.

**Efecto medido.** La novela se retomó con `continuar` tras cada caída sin perder capítulos aprobados, y terminó completa: diez capítulos aprobados, entre 1.036 y 1.259 palabras, versión 1 publicada y PDF impreso. El capítulo 10, el único escrito con el catálogo, dejó cuatro filas en `uso_hecho`, cuatro en `uso_hito` y tres en `intake_uso_dato`, y ningún aviso falso de `arco_ejecutado`.

### It-18 · La escaleta sin anclajes y la homenajeada abreviada

**Causa.** La misma novela salió con `plan_anclaje` vacía, igual que la primera: `volcar` no pasaba los mapas a `volcar_escaleta`, y al arquitecto los elementos del encargo le llegaban dentro del `Brief`, sin identificador. Los tres validadores de cobertura aprobaron sin mirar nada. Además, el arquitecto registró a la homenajeada sin su segundo apellido, y como `nombres_exactos` compara contra el canon, el nombre completo no se exigió: salió cero veces en diez capítulos, frente a 141 del nombre de pila.

**Qué se hizo.** §7.2 y §7.4 de la [spec de ejecución real](../specs/ejecucion-real/spec.md), `P-75` y `P-80`, y después el código: el prompt del arquitecto lista los elementos con su `#id`, `volcar_escaleta` resuelve la clave o el texto, lo que no resuelve queda como aviso `anclaje_resuelto` en el gate, y la ficha del homenajeado se escribe con `nombre_homenajeado`.

**Efecto medido.** 676 pruebas pasan. Falta verlo en una novela real, porque esta ya había pasado Plotting.

**Deuda o pendiente.** Si el nombre completo tiene que aparecer al menos una vez es una decisión del Autor. §9.1 —una `fase_run` por fase— no se puede implementar todavía: seis consultas de `mundo` identifican el corpus por la `fase_run` compartida. §9.2 y §9.3 siguen abiertos: la novela entera consta como 0 tokens y 0 $, y `judge_score_json` quedó vacío aunque el juez puntuó 7,43.

---

## 2026-09-24 · Tercera pasada de trazabilidad del frontend

### It-16 · El inventario prometía leer todos los planes y solo leía uno

**Causa.** Al cruzar el plan del frontend con la arquitectura apareció que `inventario_del_plan` (`P-129`) solo recogía las filas que empiezan por `| **P-` y solo recorría `backend/src/storymaker/`. El plan del frontend numera sus ítems `IMP-nn`, así que sus rutas no las comprobaba nadie. El ítem prometía leer «todo `specs/*/plan.md`» y el código leía la mitad: una desviación respecto del plan que el propio validador de desviaciones no podía ver.

**Qué se hizo.** La corrección bajó de arriba abajo. §7.1 nº 21 de la [spec del backend](../specs/backend/spec.md) y `P-129` declaran las dos clases de fila y el recorrido inverso de `frontend/src/**`, y [`test_inventario.py`](../backend/tests/correspondencia/test_inventario.py) lee `P-nn` e `IMP-nn`, resuelve las rutas del frontend relativas a `frontend/src/` y cuenta `.ts`, `.tsx` y `.css` como código. `frontend/src/**`, que `IMP-31` escribe para decir «en toda la interfaz», no se toma como comodín. En la misma pasada, §16.3 de la arquitectura pasa a declarar `.mcp.json` en la raíz en lugar de un `.claude/mcp.json` que Claude Code nunca leería, y `P-136` nombra la URL base que §16.4 exige.

**Efecto medido.** El cubo «declarado y ausente» pasa de 0 a 47 rutas, todas del frontend, que todavía no existe: es el estado normal durante el desarrollo. La parte del backend no cambia, con 0 ausentes y 0 no declarados. La dirección inversa se probó con un árbol falso fuera del repositorio: un módulo sin declarar y un `main.tsx` suelto en `src/` aparecen en «presente y no declarado», y uno declarado deja de figurar como ausente.

**Deuda o pendiente.** `P-136` sigue sin implementar: ni `Settings.frontend_dist` ni `Settings.frontend_base_url` existen en `commons/config.py`, y no hace falta que existan hasta que haya un `dist/` que servir.

---

## 2026-09-24 · La primera ejecución contra el modelo

### It-15 · El nombre del modelo de embeddings llegaba sin su organización

**Causa.** Con Intake ya completo, la ejecución cayó en `Plan`: FastEmbed rechazó `paraphrase-multilingual-MiniLM-L12-v2`. El módulo de embeddings declaraba bien el nombre con prefijo, `NOMBRE_EN_FASTEMBED`, pero `invocar` construía el vectorizador con `settings.modelo_embeddings`, que guarda el nombre de §19 sin él. La suite no lo veía porque recorre el grafo con `VectorizadorFalso`.

**Qué se hizo.** `FastEmbedVectorizador` antepone `sentence-transformers/` cuando el nombre no trae organización. Una prueba fija que el nombre de `Settings` llega completo.

**Efecto.** El modelo real se descarga, carga y devuelve vectores de 384 dimensiones en el portátil del Autor. 665 pruebas pasan.

### It-14 · Ningún rol recibía la forma de su salida

**Causa.** Con los hooks ya arreglados, el entrevistador respondió, pero con un `Brief` de claves inventadas (`titulo`, `genero`) y `personajes_historicos` copiado de la forma del YAML. `invocar_rol` validaba contra el modelo Pydantic sin habérselo enseñado nunca al rol, y el prompt de respaldo, sin Langfuse, son dos líneas.

**Qué se hizo.** Se decidió arriba primero —arquitectura §5 y §17, spec §3.3 con `REQ-BE-132`, plan `P-27`, `A-118` y `ARQ-138`— y después `invocar_rol` adjunta al prompt el JSON Schema del esquema, compactado y dentro de la estimación del techo. El mayor, el del arquitecto, ronda los 1.800 tokens frente a un techo de 25.000.

**Efecto.** El tercer intento completó Intake: `Brief` validado y tres filas de `intake_dato`.

### It-13 · Los hooks del transporte tenían una forma que el SDK no acepta

**Causa.** La primera novela real, `nueva ../ejemplos/brief-ejemplo.yaml --batch`, cayó en `Configure` **antes de la primera llamada al modelo**: `TypeError: 'function' object is not iterable` dentro del SDK. `TransporteAgentSDK._hooks` entregaba por evento la función suelta, y `ClaudeAgentOptions.hooks` exige una lista de `HookMatcher`. La suite no podía verlo porque recorre el grafo con `TransporteFalso` y el transporte real no se ejercita en ella; es exactamente la clase de fallo que su docstring deja para la ejecución de verdad.

**Qué se hizo.** Cada evento lleva ahora `[HookMatcher(...)]`, y `PostToolUse` va acotado a `WebFetch`, que es la única salida con techo: sin acotar habría reescrito la salida de cualquier herramienta con una forma que no es la suya. Dos pruebas en `tests/unit/test_agentes.py` fijan la forma, y se saltan si el extra `agentes` no está instalado.

**Efecto.** 663 pruebas pasan. La ejecución fallida no consumió nada: el checkpoint quedó intacto en `Configure`.

### It-12 · Smart App Control bloqueaba dos ruedas nativas

**Causa.** En el portátil del Autor, con Windows 11 y Smart App Control activo, la suite daba ocho fallos de integración y dos módulos de propiedades sin cargar: `uuid-utils` 0.17.1, de la que depende LangGraph, y el núcleo nativo de `hypothesis` 6.168 estaban bloqueados por falta de reputación.

**Qué se hizo.** `[tool.uv] constraint-dependencies` fija `uuid-utils<0.17` e `hypothesis<6.166`, solo en `win32`.

**Efecto.** La suite vuelve a 661, sin cambiar una línea de código. `mypy` sigue sin cargar en esa máquina, porque depende de `librt`, que es nativa en todas sus versiones; G1 lo ejecuta en la CI.

## 2026-09-23 · Auditoría contra `REQUIREMENTS.md` y cierre de los huecos baratos

### It-11 · TLC corrigió la arquitectura: la liveness necesita equidad **fuerte**

**Causa.** Con el tope del juez puesto, TLC volvió a violar `Termina`. La traza: `AwaitApproval4 → RehacerWriting → WriteChapter → … → Checkpoint → AwaitApproval4`, indefinidamente. El Autor pide rehacer Writing para siempre.

**El diagnóstico.** §11d de la arquitectura afirmaba que la liveness vale «bajo hipótesis de **equidad débil** sobre su respuesta». Es falso, y TLC lo demostró. La equidad débil solo obliga a una acción que esté *continuamente* habilitada, y `Aprobar` en el gate de Writing no lo está: en cuanto el Autor pide rehacer, arranca el bucle de escritura y la aprobación queda deshabilitada durante decenas de estados.

**Qué se hizo.** `Spec` pasa de `WF_vars(AutorAprueba)` a `SF_vars(AutorAprueba)`. En castellano llano: *el Autor puede pedir que se rehaga tantas veces como quiera, pero no infinitas*, que es lo que se quería decir y no lo que se había escrito.

**Por qué es el hallazgo que más enseña.** Los otros tres gates no tienen el problema, porque rehacen fases que aún no han producido capítulos y la aprobación se rehabilita enseguida. Solo el de Writing intercala una computación larga entre dos oportunidades de aprobar. Esa asimetría es **invisible leyendo el documento** — y el documento llevaba meses escrito y había pasado varios grillings.

**Efecto medido.** Parcial: la reverificación con equidad fuerte es mucho más cara que con débil y quedó corriendo al cerrar la sesión. Lo verificado con certeza es que las tres violaciones anteriores desaparecieron y que el espacio explorado creció de 235 a 59.236 estados distintos.

### It-10 · Un tope que faltaba: los rechazos del juez

**Causa.** Corregido It-09, TLC violó `Termina` con el ciclo `Judge → AwaitApproval4 → Judge`: el Autor aprueba, el juez rechaza por no superar el umbral, y vuelta a empezar. Sin fin.

**Qué se hizo.** Se añade `rechazosJuez` con su constante `MaxRechazosJuez`, y una arista nueva `Judge → Fail` para cuando se agotan. Se propagó a §5 y §9 de la arquitectura.

**Por qué importa más de lo que parece.** Todo lo demás en este sistema está acotado: `intentos` por capítulo, `huecos` del arquitecto, `max_turns` por sesión. El bucle del juez era **el único sin tope**, y no porque alguien decidiera dejarlo abierto: porque nadie lo miró. Es justo la clase de omisión que sobrevive a una revisión humana —no hay nada escrito que esté mal, falta algo que nadie echa en falta— y que un explorador exhaustivo encuentra en tres segundos.

### It-09 · El primer contraejemplo: rehacer no era la pasada inicial

**Causa.** Primera ejecución de TLC. Violación de `ResumeIsExactlyOnce` en 35 estados: escritos y aprobados los cinco capítulos, el Autor pide rehacer en el gate de Writing y la ejecución vuelve a `WriteChapter` con `aprobados = {1..5}` y `capitulo = 5`. La pasada inicial exige `aprobados = 1..capitulo-1`.

**Qué se hizo.** El *rehacer* del gate de Writing se separa en la acción `RehacerWriting`, que entra en modo regeneración.

**La decisión que hubo que tomar.** Había dos formas de hacer desaparecer el error: estrechar el invariante para que no cubriera este caso, o arreglar el modelo. Se arregló el modelo, porque §8 ya decía que «rehacer, reanudar, ramificar y regenerar son la misma operación con distinto punto de entrada» — la máquina de estados era la que no lo reflejaba. Estrechar el invariante habría sido cambiar la pregunta para que la respuesta saliera bien.

**Efecto medido.** `ResumeIsExactlyOnce` deja de violarse sobre 42.145 estados distintos.

### It-08 · La auditoría volvió a quedarse obsoleta, y esta vez se vio venir

**Causa.** Mientras se cerraban los huecos documentales, el otro proceso completó el tramo **H1**: nueve ficheros de esquema SQL, `apertura.py`, `transaccion.py`, los repositorios y los triggers de `inmutabilidad.sql`. La suite pasó de 22 tests a **78**. Seis filas de la auditoría y tres párrafos de prosa quedaron mintiendo.

**Qué se hizo.** Se actualizaron treinta filas y los bloques de estado, y se añadió al aviso de cabecera la cuarta pasada. Los cambios de estado por H1 fueron `MEM-01`, `MEM-02`, `MEM-03` y `GR-02` a `CUMPLE`, y `LEC-10` a `PARCIAL`.

**El detalle que merece la pena retener.** `LEC-10` —conservar la versión anterior— pasa a `PARCIAL` por una razón agradable: `inmutabilidad.sql` instala triggers que abortan cualquier `UPDATE` sobre el texto de un capítulo **antes de que exista una sola regeneración que pudiera romperlo**. El cerrojo está puesto antes que aquello que encierra, que es el único orden en que un invariante de este tipo llega a existir. Puesto después, siempre hay una excepción que ya se coló.

**Efecto medido.** `python check_requirements.py` → `CUMPLE: 27 | MANUAL: 12 | NO_APLICA: 8 | NO_CUMPLE: 50 | PARCIAL: 9`, código 0. De 7 `CUMPLE` a 27.

### It-07 · Dos clases de `PARCIAL`, y por qué no se juntan

**Causa.** Al recontar los `PARCIAL` apareció que no todos significan lo mismo, y tratarlos igual daba una lista de trabajo engañosa.

**Qué se aprendió.** Hay dos patrones distintos:

- **«La constante existe y quien la aplica no»**: `HAR-07`, `HAR-08`, `VAL-04`, `HAR-01`, `LEC-10`. Se cierran solos al avanzar el plan. No hay que hacer nada con ellos.
- **«Está escrito y el entorno no deja ejecutarlo»**: `TLA-05` sin JVM, `LEAN-03` sin `lake`, `CC-02` sin Node. No se cierran trabajando más, **se cierran instalando tres herramientas**.

**Efecto.** El apartado final de la auditoría pasa a separarlos, y la lista de pendientes se ordena en tres montones por tipo de esfuerzo en vez de por familia de requisito. Es la información más accionable del documento y estaba enterrada.

### It-06 · Lo que se decidió NO marcar en verde

**Causa.** Tres requisitos podían haberse marcado `CUMPLE` con una interpretación generosa: `TLA-05` (el modelo está escrito, TLC no ha corrido), `LEAN-03` (el proyecto está, `lake` no existe) y `CC-02` (el MCP está configurado, nunca se ha levantado). Y `TLA-07` pedía contraejemplos de TLC que podrían haberse redactado de forma plausible.

**Qué se hizo.** Los tres quedan en `PARCIAL` y `TLA-07` en `NO_CUMPLE` con la tabla vacía. Se añadió a la auditoría un apartado que **nombra explícitamente dónde estuvo la tentación**.

**Por qué.** Un fichero `.tla` en el árbol no es una verificación. La distancia entre «especificado» y «verificado» es justamente lo que estos requisitos miden, y borrarla habría convertido la auditoría en su contrario: un documento que tranquiliza en vez de informar. Una auditoría cuyo autor tiene incentivo en que salga verde solo vale si se sabe dónde pudo hacer trampa.

**Efecto.** No medible, por definición. Es la clase de decisión cuyo efecto solo se ve cuando alguien confía en el documento seis meses después.

### It-05 · Especificación TLA+ escrita directamente en TLA+, no en PlusCal

**Causa.** `TLA-01` a `TLA-07` estaban todos en `NO_CUMPLE`: no existía ningún fichero `.tla` en el árbol. La arquitectura (§11d) los daba por diseñados desde hacía tiempo, con los cuatro invariantes ya nombrados, pero nadie los había escrito.

**Qué se hizo.** [`formal/tla/harness.tla`](../formal/tla/harness.tla), con las seis fases, la reanudación y la regeneración; los cuatro invariantes de §11d más `CorpusSelladoNoSeToca`; la liveness bajo equidad débil sobre la respuesta del Autor; y `harness.cfg` con el modelo pequeño de 5 capítulos y 2 reintentos.

**Desviación respecto a la arquitectura, y por qué.** §11d pide «PlusCal traducido a TLA+, con los `process` nombrados igual que los nodos». La especificación está escrita **directamente en TLA+**, con los nombres de los nodos como valores del contador de programa. El traductor de PlusCal no está disponible en el entorno, y una traducción mantenida a mano sería una segunda copia que puede divergir de su fuente — exactamente el problema que la definición `Aristas` existe para evitar. La forma directa conserva lo que la arquitectura quería de verdad, que es la correspondencia literal de nombres y una relación de transición explícita y única.

**Efecto medido.** Parcial, y conviene ser exacto: la especificación existe y es legible, pero **TLC no se ha ejecutado**. No hay JVM en la máquina (`java -version` → `command not found`), así que la garantía de este directorio es de clase **A por inspección**, no por *model checking*. `TLA-05` sigue sin cerrarse y `TLA-07` no tiene contraejemplos que registrar porque no ha habido ejecución que los produzca. Inventarlos habría sido peor que no tenerlos.

**Propagado.** La desviación subió a la arquitectura y dejó de serlo: §11d se reescribió entero —TLA+ directo, `Mueve(de, a)` sobre `Aristas`, los cinco invariantes de estado y `PreviousVersionPreserved` como propiedad temporal— y el cambio bajó a `verification.md`, a la spec y al plan del backend.

**Pendiente.** Ejecutar TLC en un entorno con JVM y anotar aquí lo que encuentre.

### It-04 · Una decisión de diseño en el propio modelo: `PublishVersion` sin guarda

**Causa.** Al escribir `NoPublishUnvalidated` apareció la tentación de poner la comprobación como guarda de la acción `PublishVersion`, que es lo que haría el código.

**Qué se hizo.** Se dejó `PublishVersion` **sin guarda** y se introdujo una variable de historia, `publicoSinValidar`, sobre la que se enuncia el invariante.

**Por qué.** Con la guarda, el invariante sería una tautología: comprobaría la guarda recién escrita en lugar de comprobar el grafo, y pasaría siempre aunque el cableado fuera un desastre. Sin ella, TLC explora si existe **algún** camino —por reintentos, por un gate que rehace, por una regeneración a medias— que llegue a publicar con un capítulo sin validar. Es la diferencia entre una prueba que interroga al sistema y una que se interroga a sí misma.

**Efecto.** El invariante pasa a tener contenido. Queda por comprobar cuando haya JVM.

### It-03 · Entregables de raíz: el repositorio no se podía usar

**Causa.** `ENT-01` estaba en `NO_CUMPLE` por tres ausencias que no dependían de escribir ni una línea de backend: no había `README.md`, no había `.env.example` en la raíz y no había brief de ejemplo. Sin brief, `ENT-06` —la novela de muestra reproducible— no tenía entrada con la que reproducirse, así que un requisito barato estaba bloqueando uno caro.

**Qué se hizo.** [`README.md`](../README.md) con la puesta en marcha, el brief de ejemplo y la tabla de correspondencia acción ↔ nodo ↔ efecto en SQLite; [`.env.example`](../.env.example) en la raíz; [`ejemplos/brief-ejemplo.yaml`](../ejemplos/brief-ejemplo.yaml) con los tres bloques del brief comentados uno a uno; y [`.mcp.json`](../.mcp.json) con el servidor de Playwright.

**Efecto medido.** `ENT-01` pasa de `NO_CUMPLE` a `PARCIAL` —queda la novela de muestra— y `CC-02` de `NO_CUMPLE` a `PARCIAL`: el servidor MCP está configurado, pero no se ha podido levantar porque no hay Node en el entorno (`npx` → `command not found`), así que no cuenta como verificado.

**Deuda que deja.** Hay ahora dos `.env.example`, uno en la raíz y otro en `backend/`, escritos por dos manos distintas. El de la raíz es el canónico y el `README` apunta a él. Unificarlos es trabajo del siguiente que toque `backend/`.

### It-02 · La auditoría se reescribió entera a mitad de camino

**Causa.** La primera pasada de la auditoría encontró `backend/` con diecinueve `__init__.py` vacíos; la segunda, cero ficheros; la tercera, el tramo H0 completo y en el *index* de git. Otro proceso estaba construyendo el backend en paralelo, y el documento recién escrito describía un repositorio que ya no existía.

**Qué se hizo.** Se reescribió [`docs/requirements-audit.md`](requirements-audit.md) entero contra el estado final, en lugar de parchear las filas afectadas, y se añadió al principio un aviso explícito de que el árbol se movió durante la auditoría y de que las evidencias corresponden a la última pasada.

**Por qué reescribir y no parchear.** Una auditoría es un documento cuyo valor entero está en que sus evidencias sean ciertas a la vez. Parchear doce filas y dejar las demás con la evidencia vieja produce un documento internamente inconsistente, que es peor que uno desactualizado: el lector no sabe qué parte creer.

**Efecto medido.** `python check_requirements.py` → `Requisitos: 106 | CUMPLE: 7 | MANUAL: 12 | NO_APLICA: 8 | NO_CUMPLE: 69 | PARCIAL: 10`, código de salida 0. Diez `PARCIAL` frente a los cinco de la primera pasada, todos por la misma razón: H0 aporta las constantes y los tipos, pero no todavía quien los aplica.

### It-01 · El hallazgo que ordenó todo lo demás

**Causa.** Al auditar los 106 requisitos apareció un patrón que no era casualidad: **lo que el enunciado verifica leyendo documentos estaba cubierto, y lo que verifica leyendo o ejecutando código no lo estaba en absoluto**. Los siete `CUMPLE` salían todos de `docs/` y de `.claude/skills/`; los sesenta y nueve `NO_CUMPLE`, de la misma causa única.

**Qué se aprendió.** Los `PARCIAL` no son medias tintas repartidas al azar, sino un patrón repetido con nombre propio: **la constante existe y quien la aplica no**. `HAR-07` tiene `REINTENTOS_POR_CAPITULO` y no el bucle; `HAR-08` tiene `TOKENS_CONCURRENTES_MAXIMOS` y no la guarda que rechaza la llamada; `VAL-04` tiene `RANGO_PALABRAS` y no el validador; `HAR-01` tiene los nueve roles como `StrEnum` y ningún agente detrás.

**Efecto.** Ese patrón fija el orden de trabajo: los cuatro se cierran casi solos cuando lleguen los tramos H1 a H7 del plan, así que no se tocan ahora. El esfuerzo se dirigió a lo que **no** depende del backend —entregables de raíz, `/docs`, TLA+, Lean y evals—, que además es lo que otro proceso no estaba escribiendo al mismo tiempo.

---

## Cómo se anota una iteración

Cuatro campos, y ninguno es opcional:

- **Causa.** Qué se observó. Un número, un fallo, una traza, una fila de la auditoría. No «parecía mejorable».
- **Qué se hizo.** El cambio, con enlace al fichero.
- **Efecto medido.** Qué dice la misma medida después. Si no se midió, se escribe que no se midió — que es un resultado, no una omisión.
- **Deuda o pendiente**, cuando el cambio deja algo abierto.

Las iteraciones que nacen de un contraejemplo de TLC se anotan además en [`formal/tla/README.md`](../formal/tla/README.md), con la traza. Las que nacen de un hallazgo de red-team, en [`red-team.md`](red-team.md).
