# Spec — Backend de StoryMaker

Qué construye el backend, qué contrato expone cada pieza, qué devuelve cuando algo va mal y con qué se comprueba que hace lo que dice.

Deriva de [`architecture.md`](../../docs/architecture.md), que es la fuente de verdad, y de [`verification.md`](../../docs/verification.md), de donde toma el marco T·A·I·D·U y los Quality Gates. **Si algo de este documento contradice a la arquitectura, manda la arquitectura.** La forma técnica exacta —ficheros, funciones, orden de trabajo— no vive aquí, sino en [`plan.md`](plan.md).

**Alcance.** Todo `backend/src/storymaker/`: las seis fases, los módulos transversales de `commons/`, la API de FastAPI y la CLI de Typer. Queda fuera el frontend de React, que tiene su propia metodología en §16.3 de la arquitectura, y quedan fuera el proyecto de Lean y la especificación de TLA+, que son artefactos de verificación y no código del arnés — el backend solo los invoca.

---

## 1. La forma del backend en una página

El backend es **un paquete Python organizado *package by feature***, donde cada feature es una fase y `commons/` guarda lo que todas usan y ninguna posee. Sobre él hay dos puntos de entrada —la CLI y la API— que llaman a la misma función de invocación del grafo.

Tres afirmaciones gobiernan todo lo demás, y conviene tenerlas delante al leer el resto:

1. **El estado vive en un fichero SQLite por novela, y en ningún otro sitio.** Ni en memoria del servidor, ni en una cola, ni en un registro global. Matar cualquier proceso en cualquier punto y reanudar no pierde nada.
2. **Los validadores son nodos del grafo.** Ningún agente puede elegir no llamarlos. Las aristas condicionales leen booleanos calculados en Python.
3. **El agente recibe su contexto, no lo busca.** Ningún rol salvo el investigador tiene herramientas, y ninguno tiene `Bash`, `Write` ni acceso al disco.

```text
backend/src/storymaker/
├─ intake/ investigation/ plotting/ writing/ publication/ regeneration/   las seis fases
├─ gates/                                                                 interrupt, Notifier, bot
├─ api/                                                                   FastAPI: lectura, cambio
├─ cli/                                                                   Typer
└─ commons/  graph · db · agents · context · validation · embeddings · formal · obs
```

Cada feature contiene sus nodos de LangGraph, su agente, sus esquemas Pydantic y sus validadores propios. **Ninguna fase importa de otra**: lo que comparten baja a `commons/`, y el grafo que las cablea vive en `commons/graph/` porque es de todas y de ninguna.

---

## 2. Puesta en marcha y configuración

### 2.1 Los dos puntos de entrada

| Entrada | Proceso | Responsabilidad |
|---|---|---|
| **CLI (Typer)** | Efímero, uno por comando | Crear la novela, lanzar y reanudar la invocación, ramificar, romper un cerrojo huérfano, correr los cinco briefs en modo batch |
| **API (FastAPI)** | Servidor de larga vida | Servir la lectura y recibir la petición de cambio del lector. **No reanuda ninguna ejecución** |

Los dos llaman a `commons/graph/run.py::invocar(novela, entrada)`. La API no tiene un camino propio hacia el grafo, y esto es deliberado: si lo tuviera, habría dos implementaciones de la reanudación y solo una de ellas estaría cubierta por las pruebas de integración.

### 2.2 Configuración

Un único objeto `Settings` de `pydantic-settings`, leído del entorno y de un `.env`, cargado una vez al arrancar. No hay lectura de variables de entorno dispersa por el código: **quien necesita un valor lo recibe inyectado**, para que las pruebas puedan construir un `Settings` distinto sin tocar el entorno del proceso.

| Grupo | Claves | Nota |
|---|---|---|
| Rutas | `directorio_proyectos` (por defecto `proyectos/`) | El directorio es el registro de novelas (§16.4 arq.) |
| Frontend | `frontend_dist` (por defecto `frontend/dist`), `frontend_base_url` | Lo que FastAPI sirve y la URL con la que Playwright abre la lectura para imprimir y para `render_visual` |
| Modelos | `modelo_por_rol` (mapa rol→id de modelo), `sdk_version` | Por defecto los nueve roles en Haiku 4.5 |
| Gates | `gates_enabled`, `timeout_gate_horas` | `false` en modo batch |
| Telegram | `telegram_bot_token`, `telegram_chat_id` | Solo aviso saliente; sin ellos el sistema corre igual y el gate bloquea igual |
| Modelo | — | **No hay credencial de Anthropic.** El Agent SDK lanza Claude Code como subproceso y hereda su sesión: el arnés fija modelo, herramientas y turnos, pero no autentica |
| Langfuse | `langfuse_public_key`, `langfuse_secret_key`, `langfuse_host`, `otlp_enabled` | OTLP desactivado por defecto |
| Límites | `reintentos_por_capitulo` (2), `huecos_por_plotting` (5), `k_vecinos` (8), `techo_webfetch_tokens` (10.000) | Los valores de §19 de la arquitectura |
| Embeddings | `modelo_embeddings`, `dimension_embeddings` (384) | Viajan al `manifiesto` |

**Ningún secreto se escribe en el repositorio.** `gitleaks` lo comprueba en G0 y G1, y es el único fallo de este proyecto con consecuencias fuera de él.

### 2.3 Arranque: lo que se comprueba antes de aceptar trabajo

Al abrir una novela, y antes de nada más:

1. **Se carga `sqlite-vec`** con `enable_load_extension`. Si falla, el arranque se detiene con un mensaje explícito. **Nunca se degrada en silencio** a un sistema sin búsqueda semántica: un ensamblador que no puede buscar produciría paquetes de contexto empobrecidos sin que nadie se enterase (U-15).
2. **Se aplican las migraciones pendientes** y se comprueba que la versión de esquema del fichero es la que el código espera.
3. **Se activan los `PRAGMA`**: `journal_mode=WAL`, `foreign_keys=ON`, `synchronous=NORMAL`.
4. **Se toma el cerrojo** si la operación va a invocar el grafo (§3.2).

---

## 3. Contratos de `commons/`

### 3.1 `commons/db` — esquema, transacciones e inmutabilidad

**Contrato.** Expone una conexión abierta sobre el fichero de una novela y las consultas de dominio. Nadie fuera de este módulo construye SQL a mano contra las tablas del arnés.

**Esquema.** El de §7 de la arquitectura, con tablas `STRICT` y `CHECK` sobre todos los enumerados: `mundo_hecho.estado`, `mundo_hecho.origen`, `mundo_hecho.respaldo`, `canon_prohibida.nivel`, `incidencia.severidad`, `fase_run.estado`, `gate.decision`. Un valor fuera del enumerado **aborta la transacción**; no se normaliza ni se corrige.

**Inmutabilidad, con dos cerrojos.** El principio «nada se sobrescribe» se protege arriba con la regla Semgrep `no-update-inmutables`, que impide escribir el código, y abajo con ***triggers* `BEFORE UPDATE` y `BEFORE DELETE`** sobre `capitulo_version`, `fase_run`, `version_novela`, `version_capitulo` y `mundo_hecho` tras el sello, que impiden que se ejecute. El *trigger* lanza `RAISE(ABORT, ...)` con el nombre de la tabla. **Lo que protege es el contenido**: `capitulo_version` admite el cambio de `estado` que hace `ApproveChapter` y `fase_run` admite su cierre con el consumo, pero el texto, el intento y la identidad de la ejecución no se tocan, y `version_novela` y `version_capitulo` no admiten escritura alguna. En `mundo_hecho` la condición es la existencia del sello, de modo que el verificador puede degradar antes y nadie puede escribir después. Un principio con un solo cerrojo es una convención; con los dos, es una propiedad.

**Transacciones.** La regla que sostiene el §7 entero: **el checkpoint de LangGraph y la escritura de dominio ocurren en la misma transacción.** El nodo no hace `commit` por su cuenta; lo hace el envoltorio de invocación al cerrar el paso. De ahí que no pueda existir un instante en que el grafo crea que el capítulo 6 está hecho y la biblia no lo tenga.

**Errores.**

| Situación | Respuesta |
|---|---|
| Fichero de novela inexistente | `NovelaNoEncontrada`, la CLI y la API lo traducen a mensaje y a `404` |
| Versión de esquema posterior a la que el código conoce | Se detiene el arranque: nunca se abre una novela con un esquema del futuro |
| Violación de `CHECK` o de *trigger* | La transacción entera se deshace y la incidencia sube como error del nodo |

*Clase de confianza: **A** (esquema y *triggers*), confirmada por **T** en `tests/db/`. Gate: G1.*

### 3.2 `commons/graph` — el estado, el cableado y la invocación

**Contrato.** Define el `TypedDict` del estado compartido, construye el `StateGraph` cableando los nodos que cada feature exporta, y expone la única función que lo invoca.

**El estado es un `TypedDict` total y explícito.** Nada de `dict[str, Any]` en este módulo: mypy `--strict` lo comprueba, y es lo que permite que el contador de huecos de Plotting o el de reintentos de Writing tengan un dueño declarado en lugar de acabar definidos dentro de la fase que primero los necesitó.

**Los nodos se llaman igual que las acciones de la especificación TLA+.** No es una convención estética: es lo que hace que un contraejemplo de TLC se lea como una secuencia de nodos reales. La tabla de correspondencia de §9 de la arquitectura es una lista de identidades, y una prueba la comprueba: **el conjunto de nombres de nodo del grafo y el conjunto de nombres de acción de `formal/tla/harness.tla` deben ser iguales.** Si alguien añade un nodo sin añadir su acción, la prueba cae.

**La invocación.**

```
invocar(novela: Novela, entrada: Arranque | Reanudacion) -> ResultadoInvocacion
```

Avanza de nodo en nodo hasta encontrar un `interrupt()` o hasta terminar, y devuelve qué ocurrió: el nodo en que se detuvo, el gate que quedó abierto si lo hay, y el consumo acumulado. Entre una invocación y la siguiente no queda nada vivo.

**El cerrojo.** Antes de invocar se toma en exclusiva `<novela>.db.lock`; se suelta al acabar, pase lo que pase. **Quien llega segundo recibe `NovelaOcupada` y es rechazado, no encolado.** Cubre al CLI y a la API a la vez porque son procesos distintos y un cerrojo en memoria no los vería. Un cerrojo huérfano se rompe con `storymaker desbloquear`.

**Errores.**

| Situación | Respuesta |
|---|---|
| Otra invocación en curso | `NovelaOcupada` → `409` en la API, mensaje en la CLI |
| Excepción dentro de un nodo | Se registra en `fase_run` con estado de error, se suelta el cerrojo, el último checkpoint queda intacto |
| Reintentos agotados | Transición a `Fail`, que es un estado declarado del grafo y no una excepción |

*Clase: **A** (identidad nodo↔acción, comprobada estáticamente) **/T** (integración con agente falso). Gate: G1.*

### 3.3 `commons/agents` — invocación del Agent SDK y techos

**Contrato.** Una función por la que pasan **todas** las llamadas a un modelo. Recibe el rol, el prompt ensamblado y el esquema Pydantic de salida; devuelve la instancia validada del esquema y el consumo. Ningún módulo llama al Agent SDK por su cuenta.

**Lo que fija por invocación**, tomado de la tabla de §12 de la arquitectura: el modelo, `allowed_tools`, `max_turns` y el techo de tokens del rol.

**El contrato de salida.** La función adjunta al prompt el **JSON Schema del esquema de salida**, generado con `model_json_schema()` del mismo modelo Pydantic contra el que después valida `schema_guard`, y la instrucción de responder solo con un objeto JSON que lo cumpla. El esquema forma parte del prompt a todos los efectos: **entra en la estimación de la guarda de presupuesto** y viaja igual en el reintento. Ningún nodo describe la forma de su salida por su cuenta, y el prompt de rol —Langfuse o su respaldo local— tampoco: si lo hiciera habría dos descripciones de un mismo contrato y una acabaría mintiendo.

**Las tres guardas, todas por construcción:**

| Guarda | Mecanismo | Qué impide |
|---|---|---|
| **Presupuesto** | Se **estima** el prompt ensamblado antes de emitir y, si excede el techo del rol, **la llamada no se emite**. El SDK no expone su tokenizador, así que se cuenta por lo alto con un margen declarado: sobreestimar rechaza una llamada que habría cabido y se nota en el acto; subestimar revienta la ventana, que es lo que esta guarda existe para impedir | Que una sesión reviente el límite de 100.000 tokens concurrentes |
| **Cuota de herramientas** | Hook `PreToolUse` que devuelve `permissionDecision: "deny"` al agotarse la cuota | Que el investigador emita una cuarta `WebSearch` |
| **Truncado de la respuesta** | Hook `PostToolUse` que reescribe el resultado con `updatedToolOutput` antes de que entre en contexto | Que una página de 40.000 tokens entre entera |

Ninguna de las tres es declarativa: no hay opción en `settings.json` ni en `ClaudeAgentOptions` que las haga. Se programan una vez aquí y se aplican a todos.

**`schema_guard`.** La salida del modelo se valida contra el esquema del rol **antes de escribir en SQLite**. Si falla, se reintenta con el error de validación inyectado en el prompt; agotado el límite, se abre incidencia. Un modelo no escribe nunca en la base sin pasar por aquí.

**Errores.**

| Situación | Respuesta |
|---|---|
| Prompt por encima del techo del rol | `PresupuestoExcedido`, la llamada no se emite y el nodo abre incidencia |
| Salida que no valida tras los reintentos | Incidencia de severidad bloqueante |
| Error de red o del SDK | Reintento con espera exponencial, tope declarado, y después error del nodo |

*Clase: **A** (las tres guardas son estructurales) **/T** (su eficacia, con pruebas por guarda). Gate: G1, y G6 sobre la traza.*

### 3.4 `commons/context` — el ensamblador de paquetes

**Contrato.** `ensamblar(novela, capitulo_n) -> Paquete`. Python puro sobre SQLite y los índices vectoriales. **Es el corazón del arnés y conviene que no tenga nada de inteligente.**

Monta los siete bloques de §6 de la arquitectura en orden, con sus techos: encargo (800), canon relevante (2.500), continuidad (1.500), memoria (4.000), anclajes (1.500), reglas (1.200) y personalización (500). Total 12.000.

**Tres propiedades que el ensamblador debe cumplir siempre**, y que son las que se verifican con Hypothesis y con CrossHair:

1. El paquete **nunca excede** el techo total.
2. El recorte va **por la cola de la lista ya ordenada por relevancia**, y el bloque 3 —continuidad— es el último que se toca.
3. Los **anclajes explícitos de la escaleta entran siempre**, antes que cualquier vecino semántico.

**La recuperación la hace él, no el agente.** La consulta se deriva mecánicamente del texto de las escenas del capítulo N, se vectoriza con FastEmbed y se resuelve con KNN de `sqlite-vec` sobre los tres índices. Con las mismas entradas salen los mismos vecinos, siempre.

**El paquete se persiste entero y se enlaza desde su span de Langfuse.** Poder abrir literalmente lo que el modelo vio al escribir el capítulo 7 es la definición operativa de interpretabilidad en este sistema, y cuesta casi nada.

**Errores.** Un bloque vacío no es un error: el capítulo 1 no tiene memoria de N−1 y el paquete lo refleja. Lo que sí es error es que falte la escaleta del capítulo pedido, que aborta la invocación en lugar de generar a ciegas.

*Clase: **A** (techos y orden de recorte, por CrossHair) **/T** (Hypothesis sobre estados de base arbitrarios). Gate: G1, G2.*

### 3.5 `commons/embeddings` — FastEmbed y los índices `vec0`

**Contrato.** Es **el único módulo autorizado a escribir en las tablas `vec_*`**, y la regla Semgrep `indice-solo-por-embeddings` lo impone. Expone dos operaciones: indexar una fila y buscar los `k` vecinos.

**El índice se escribe en la misma transacción que la fila.** Quien inserta un hecho, una ficha de canon o un resumen, lo indexa en el mismo `commit`. Importa sobre todo en el canon, que es biblia viva: cuando el Autor edita una ficha en un gate, la fila de `edicion_humana` **dispara el reembedding** de lo que tocó. Sin eso la búsqueda seguiría devolviendo el texto anterior a la corrección.

**`vec_resumen.vigente`.** Se pone a 1 al aprobar una versión y a 0 en la que sustituye. El bloque 4 del paquete pide `capitulo_numero < N AND vigente = 1`. Sin ese filtro el escritor del capítulo 7 podría recibir el resumen de un intento rechazado del 3 — un fallo silencioso, porque el capítulo saldría bien escrito recordando algo que ya no está en la novela.

**No se usan claves de partición**, porque una novela tiene unos cientos de hechos y la extensión pide cien o más por valor de partición. Lo que en otro sistema serían particiones, aquí son columnas de metadato.

*Clase: **A** (la regla Semgrep y la búsqueda exhaustiva, que no es aproximada) **/T**. Gate: G1.*

### 3.6 `commons/validation` — el Core Domain

**Contrato.** **Python puro, agnóstico a quién lo llama.** No importa `claude_agent_sdk`, ni `langgraph`, ni `httpx`, ni `langfuse`; la regla Semgrep `core-domain-puro` lo impone. Cada validador recibe datos y devuelve una lista de incidencias tipadas: nunca escribe en la base, nunca llama a un modelo, nunca sale a la red.

**Tiene dos consumidores y una sola implementación:**

- **En producción**, el grafo lo ejecuta como nodos y aristas condicionales.
- **En edición manual**, `.claude/` lo expone como *skill* y como *hook*, de modo que cuando una persona edita un capítulo a mano, la misma validación comprueba que no ha roto los guardrails ni la continuidad.

Si divergieran, el producto y el editor humano dejarían de estar de acuerdo sobre qué es válido. Por eso **la prueba de contrato más valiosa del proyecto** ejecuta el mismo capítulo por ambos caminos y exige el mismo veredicto, incidencia por incidencia.

**El registro es el cableado.** `registro.py` expone `REGISTRO: dict[str, EntradaValidador]`, y cada entrada declara cuatro cosas: el nombre, el punto de ejecución, si bloquea y **la ruta de su implementación como cadena**, no como `import`. Lo último no es un detalle de estilo: es lo que permite que el registro cubra los once validadores deterministas de §11a de la arquitectura —incluidos `schema_guard`, que vive en `commons/agents/`, y `render_visual`, que vive en `publication/` y conduce un navegador— sin que `commons/validation/` importe nada de fuera y sin romper `core-domain-puro`. Quien resuelve la ruta es quien compone la pasada, no el registro.

**Los dos consumidores se sirven de él**: el grafo compone cada pasada filtrando el registro por `punto`, y el hook de `.claude/` enumera desde ahí los que puede ejecutar sobre un capítulo editado a mano. Un validador que no esté en el registro no corre por ningún camino, de modo que no puede existir un validador vivo fuera de él — que es lo que convierte la comprobación de §7.1 nº 20 en clase **A** y no en un cotejo de dos listas mantenidas a mano.

La lista de validadores está en §7.2, y esa tabla, la de §11a de la arquitectura y el registro se comparan por pares en CI.

*Clase: **A** (pureza, por Semgrep; registro como cableado) **/T** (mutación ≥ 80 %, que es lo que demuestra que la red tiene malla). Gate: G1, G2.*

### 3.7 `commons/formal` — el generador de Lean y su *runner*

**Contrato.** Genera un fichero Lean 4 desde `cronologia_evento`, `cronologia_participante` y las fechas de `canon_personaje` y `mundo_entidad`; invoca `lake build` por subproceso; devuelve un booleano y, si falla, el invariante violado con los eventos implicados.

Los cuatro invariantes de §11c se verifican **por decisión (`decide`)**, de modo que la demostración es automática y no puede atascarse.

**Corre en tres sitios**, y cada uno mira algo distinto: en el **gate de Plotting**, sobre la cronología que se deduce de `plan_escena.fecha_narrativa`, `plan_escena_personaje` y las fechas vitales del canon y del corpus, donde la escaleta vuelve al arquitecto sin que haya una línea escrita; en la **pasada del extractor** de cada capítulo, sobre la cronología acumulada, donde el fallo vuelve al editor dentro del bucle; y **antes de publicar**, sobre la cronología completa, donde **la versión no se publica**. G5 no admite excepción.

**Lo que queda fuera.** Que el generador traduzca fielmente el contenido de SQLite es código Python corriente y se verifica como tal, con una prueba de contrato que regenera un fichero de referencia y lo compara. Está anotado como brecha de refinamiento en U-1.

**Errores.** Si `lake` no está instalado o el subproceso falla por una razón que no es un invariante violado, **eso no es un capítulo inválido**: es un error de entorno, y se distingue del veredicto negativo. Confundirlos aprobaría capítulos por avería.

*Clase: **A**. Gate: G3, G5.*

### 3.8 `commons/obs` — Langfuse

**Contrato.** Spans manuales emitidos por los nodos: **una sesión por novela**, que incluye la entrevista y todas las regeneraciones, y **un span por invocación**, nombrado `capitulo_07 · escritor · intento_2`. Tokens, coste y latencia salen del `ResultMessage` del SDK.

Todos los *scores* de validadores —programáticos, semánticos y de Lean— se envían asociados a su traza, y las decisiones de gate también: **la intervención del Autor queda trazada igual que la de un agente.**

**Los prompts de rol viven en Langfuse como fuente de verdad** y se inyectan como `system_prompt`; el id de versión viaja en el span. Las *skills* y `CLAUDE.md` se quedan en el repositorio y se registran por su hash.

`total_cost_usd` se etiqueta **siempre** como estimación en cliente, nunca como facturación (U-7).

*Clase: **D** (observación) **/T** (las aserciones de G6 sobre la traza). Gate: G6.*

---

## 4. Las seis fases

Cada feature expone sus nodos al grafo, su agente y sus esquemas. Lo que sigue es el contrato de cada una: qué recibe, qué deja escrito y con qué falla.

### 4.1 `intake/` — Fase 1

**Entrada.** La premisa inicial libre del comprador y, opcionalmente, texto pegado.

**Qué hace.** Una extracción rellena del esquema `Brief` lo que pueda; el entrevistador **solo pregunta por lo que sigue vacío o ambiguo**. El texto pegado entra en `intake_texto_crudo` —la cuarentena— y solo avanza convertido en filas tipadas de `intake_dato` con `origen = 'texto_libre_no_confiable'`.

**Salida.** `intake_brief` con el `Brief` serializado y su `hash`, y las filas de `intake_dato`. **La verdad son las filas, no el JSON**: el JSON es la fotografía auditable que no decide nada.

**Contradicciones.** Las detecta un `@model_validator` de Pydantic, no un modelo: edad del homenajeado contra el período, fecha de nacimiento contra el `evento_ancla` si viene relleno, tono festivo contra un período de duelo, dato aportado que coincide con una palabra prohibida. El agente captura el `ValueError`, lo traduce a pregunta y obliga a resolverlo.

**Contrato de seguridad.** Una cadena del texto en bruto **no puede aparecer jamás en el prompt del escritor**, y hay una aserción que lo comprueba sobre cargas de inyección. La defensa es estructural: una inyección tiene que sobrevivir a convertirse en una fila tipada para hacer daño.

**La entrevista, a través del gate.** Las preguntas del entrevistador se guardan como incidencias de aviso del validador `pregunta_del_entrevistador`, sin capítulo, y el aviso del gate de Intake las enumera. El Autor contesta con `storymaker decidir <novela> rehacer --comentario "<respuestas>"`. La arista «rehacer» devuelve a `Configure`, que vuelve a entrevistar con la premisa y **los comentarios de todos los gates de Intake decididos como «rehacer»**, en orden. Sobre esa segunda pasada:
- las preguntas anteriores se retiran y solo quedan las nuevas;
- el texto pegado **no se vuelve a extraer**, porque la cuarentena ya lo tiene;
- un dato dictado que ya existe con el mismo tipo, valor y origen **no se vuelve a escribir**;
- `intake_brief` guarda una fila por pasada, y todo lector toma la última.

**Errores.** Brief incompleto tras agotar las preguntas → el gate se abre igualmente con el informe de lo que falta; decide el Autor. Aprobar con preguntas pendientes sigue con el brief que haya.

### 4.2 `investigation/` — Fase 2

**Entrada.** Período y lugar del `Brief`. **Nunca sus campos personales**: el investigador es el único rol con red, y la regla Semgrep `pii-fuera-del-investigador` más una aserción sobre el prompt ensamblado impiden que los datos del homenajeado salgan por ahí.

**Paso 1 · una sesión, tres búsquedas.** El investigador reparte **3 `WebSearch` y 3 `WebFetch`** entre las seis dimensiones del período y las deja todas pobladas. El tope lo impone el arnés con los hooks de §3.3, no una instrucción del prompt: la cuarta llamada no se emite. Cada hecho se guarda con su enunciado, su estado epistémico, sus fuentes, el `fase_run_id` que lo escribió y su **cita de 300 caracteres como mucho**.

**Paso 2 · el verificador.** Un agente distinto, **sin herramientas y sin red**, lee los pares enunciado–cita **por lotes de veinte** y responde una sola pregunta por hecho: ¿el fragmento dice lo que el hecho afirma? Un `no_respaldado` **degrada el hecho a `inferido` y lo marca; no lo borra y no detiene la fase.**

**Salida.** `mundo_hecho`, `mundo_fuente`, `mundo_hecho_fuente`, `mundo_entidad`, con `respaldo` escrito.

**Rehacer no contamina.** Los hechos de la ejecución anterior no se borran ni se mezclan: solo cuentan los del `fase_run` vigente, y los antiguos quedan como historia consultable.

**Errores.** Cero hechos en una dimensión no es un error bloqueante: es una fila del informe del gate, con el recuento por dimensión delante del Autor, que puede rehacer con comentario dirigido a lo que falte.

### 4.3 `plotting/` — Fase 3

**Entrada.** Brief validado y corpus.

**Qué hace.** El arquitecto **inventa la Premisa y el Tema**, construye el canon —personajes, relaciones, arcos con sus hitos, escenarios, voz, glosario— y la escaleta jerárquica de capítulos → escenas → beats con sus anclajes. Copia además `grado_licencia`, `arcaismo` y `contenido_admisible` a `canon_obra.estilo_json`, que es como esos diales llegan al bloque 6 del paquete.

**El arquitecto no recibe el corpus entero.** Los hechos le llegan por la misma búsqueda semántica de §3.5, con la consulta derivada de lo que está planificando. Es el tercero de los cuatro usos que §16.2 de la arquitectura da a los embeddings, y es lo que evita volcarle en la ventana un corpus de varios cientos de hechos.

**El hueco.** Para cada hueco que la escaleta destapa dispara **una única micro-llamada** al investigador, con una sola `WebSearch`. Si lo encuentra, entra como `origen = 'micro_arquitecto'`; si no, el veredicto `no_encontrado` **autoriza la invención**, que entra igualmente como fila con `estado = 'inferido'`, `origen = 'invencion_autorizada'`, sin fuente y con `respaldo = 'no_aplica'`. **Los huecos se topan en cinco por ejecución; la invención no se topa, se cuenta** y aparece por dimensión en el informe del gate.

**El sello.** Al aprobarse la escaleta se calcula el hash sobre el contenido ordenado de las tablas `mundo_*` vigentes y se escribe `mundo_sello`. **A partir de ahí el corpus es de solo lectura**: durante Writing solo se puede anclar a lo existente o declarar una Licencia.

**Errores.** Tope de huecos alcanzado no bloquea: queda la invención autorizada, que no cuesta nada y produce exactamente la misma fila.

### 4.4 `writing/` — Fase 4

El bucle por capítulo, que es la unidad de generación, validación, checkpoint y regeneración.

1. El ensamblador monta el paquete del capítulo N.
2. El escritor **redacta el capítulo entero de una vez**. La escena es unidad de planificación y de traza, no de redacción: coser escenas generadas por separado es la forma más fiable de producir prosa mecánica.
3. **`Validate`, en dos pasadas, ambas dentro del bucle de reparación:**
   - **Determinista**, de coste cero: los validadores programáticos que actúan sobre el capítulo, solo texto contra filas ya escritas.
   - **Del extractor**, una sola llamada y **solo si la anterior no dejó incidencias**. Un extractor independiente devuelve resumen, delta de continuidad, hechos usados, elementos de personalización usados, **eventos de cronología narrativa** y veredicto de ejecución. Sobre su salida corren `cobertura_capitulo`, `ejecucion_escaleta`, `arco_ejecutado` y **los cuatro invariantes de Lean sobre la cronología acumulada**. Lean vive aquí y no en la pasada anterior porque las filas de `cronologia_evento` con `origen = 'narrativo'` **las escribe el extractor al leer el capítulo**: antes de su llamada, la cronología del capítulo N sencillamente no existe.
4. Si hay incidencias **bloqueantes**, el editor recibe el informe ya producido y emite un parche; vuelta a (3), con **2 reintentos**.
5. `ApproveChapter` marca el estado.
6. Checkpoint **en la misma transacción**.

**Por qué el extractor es independiente.** Si el escritor declarase qué hechos ha usado, el índice hecho→capítulo se construiría sobre el testimonio de quien tiene interés en decir que los usó todos; y si declarase qué beats ejecutó, la comprobación de que el capítulo cumple la escaleta sería el escritor dándose el visto bueno.

**Por qué corre antes de aprobar.** Un veredicto emitido después de `ApproveChapter` no tendría adónde ir: no hay arista de vuelta desde `Checkpoint` a `Repair`.

**Las filas del extractor cuelgan del intento, no del capítulo.** `uso_hecho`, `intake_uso_dato` y `continuidad` llevan el `capitulo_version_id` del intento que las produjo, así que las de un intento descartado quedan colgando de una versión que ningún manifiesto recoge. No hace falta borrarlas.

**El extractor de capítulo es un rol, con su techo.** Consume contexto y se invoca hasta tres veces por capítulo, así que necesita fila en §12: el presupuesto se garantiza sumando techos declarados, y un agente sin techo sería un hueco en ese método. Su techo es **12.000** —capítulo más la escaleta de sus escenas—, y el del extractor de `intake/` **6.000**. Ninguno mueve el peor caso del sistema, que sigue siendo la sesión inicial del investigador con 45.000.

**Errores.** Reintentos agotados → `Fail`, que es un estado del grafo, no una excepción.

### 4.5 `publication/` — Fase 5

**Entrada.** La novela terminada.

**Qué hace.** El juez aplica la rúbrica de siete criterios y devuelve **un esquema de puntuaciones; no tiene permiso de escritura sobre el texto.** Superados el umbral del juez y el gate de Lean, se publica `version_novela` con su `version_capitulo`, se escribe el `manifiesto` con los hashes, los prompts, los modelos, los embeddings y la versión del SDK, se maqueta el PDF y se genera la lectura web.

**El PDF se imprime desde la misma ruta que lee el navegador**, con `page.pdf()` de Playwright. Si se maquetara aparte, web y PDF divergirían, y la divergencia aparecería el día de la demo.

**El navegador ve la versión candidata porque se le sirve.** Con la transacción abierta, ningún otro proceso puede leer ese manifiesto, así que `publication.publish` conduce el navegador **interceptando sus peticiones de datos** y respondiéndolas desde el manifiesto candidato que tiene en memoria. La ruta que abre es la de impresión del frontend, servida por el propio FastAPI desde `frontend_dist`. De esto depende una exigencia sobre el frontend, y está escrita en su spec: **ningún módulo fuera de `shared/api` emite red**, porque lo que no se puede interceptar no se puede juzgar.

**El render se comprueba antes de publicar.** Se arma el manifiesto de la versión candidata, se renderiza la lectura contra él y `render_visual` lo juzga **con la transacción todavía abierta**: si algo no renderiza, se deshace y no hay versión publicada. G5 no admite excepción, y un índice roto detectado después sería una versión ya publicada sin arista de vuelta. No hace falta nodo nuevo: la comprobación cabe dentro de `publication.publish`.

**Sin gate humano**, porque el manuscrito ya se aprobó al cerrar Writing y lo que queda es automático.

**El juez recibe la rúbrica** —las siete preguntas de `rubrica.yaml`, el mismo fichero de la revisión humana— antepuesta a la novela. **El PDF** se imprime tras `publish`, junto al fichero de la novela como `<novela>.v<n>.pdf`, y si falla queda como aviso: la versión ya está publicada y validada.

**Errores.** Lean falla → **la versión no se publica, sin anulación posible**. Umbral del juez no superado → vuelta al gate de Writing **con gates**; **en modo batch se registra la nota y se publica**, porque no hay nadie que decida qué rehacer.

### 4.6 `regeneration/` — Fase 6

**Entrada.** La petición del lector en lenguaje natural, o una edición humana directa del corpus, del canon o de la escaleta. **Las dos entran por la misma puerta y disparan la misma maquinaria.**

1. La petición se resuelve por búsqueda semántica contra canon y corpus; los candidatos se muestran y **el Autor confirma en el gate**. Sin esto, la fase exigiría que el lector conociera los identificadores internos.
2. **Se modifica la fila del hecho, no el texto.** El canon manda sobre el texto: un buscar-y-reemplazar sobre la prosa deja mintiendo a la biblia.
3. `uso_hecho` dice qué capítulos lo usan; **esos se regeneran**.
4. Los posteriores pasan a `Invalidado` y se les corren **solo los validadores de coste cero** —Python y Lean—. Si ninguno falla, se quedan como están y no cuestan un token.
5. Se publica un manifiesto nuevo que **reutiliza los capítulos no tocados**; la versión anterior sobrevive entera.
6. El diff sale de comparar dos manifiestos con un `JOIN`.

**Errores.** Una regeneración que toque un hecho usado en nueve capítulos es correcta pero cara: **el gate de Regeneration enseña el recuento de afectados antes de pagarlo** y permite abortar.

### 4.7 `gates/` — los cinco gates y la notificación

**Contrato.** El nodo **abre el gate** —fila `pendiente` en `gate`— y avisa; después llama a `interrupt()`, el checkpointer persiste y la invocación termina. **La decisión se toma en el PC del Autor** con `storymaker decidir`, que la escribe sobre el gate pendiente y reanuda con `Command(resume=...)` en el mismo proceso. Como LangGraph vuelve a ejecutar el nodo al reanudar, la invocación lleva una **marca de reanudación de un solo uso** que impide abrir el gate otra vez y volver a avisar. `continuar` **se niega** a reanudar una novela con un gate pendiente: sin decisión, lo aprobaría en silencio.

Cuatro decisiones: **aprobar**, **rehacer con comentario** —el texto libre se inyecta como bloque extra en el prompt y cuenta contra el límite de reintentos—, **editar** y **abortar**.

**Notificación tras la interfaz `Notifier`, y solo para avisar**, con Telegram como única implementación hoy. El aviso de un gate lleva el título, un resumen de lo que hay que revisar y **los comandos exactos** para decidir, en texto plano y **sin botones**. Si Telegram rechaza el envío o no hay red, se avisa en la salida del proceso y el gate bloquea igual. WhatsApp exige Meta Business, número verificado y plantillas aprobadas, y queda como adaptador futuro.

**Sin respuesta**: el *timeout* **aparca** la ejecución con estado propio. **No hay auto-aprobación**, porque eso convertiría un gate de calidad en un temporizador.

**`gates_enabled = false`** los desactiva enteros, y queda registrado en el manifiesto. Es imprescindible: los cinco briefs de evaluación tienen que correr desatendidos.

---

## 5. La API de FastAPI

Lectura, más una petición de cambio que no toca nada hasta su gate. **Ningún endpoint reanuda una ejecución**: los gates se deciden con la CLI.

| Método y ruta | Quién llama | Contrato | Errores |
|---|---|---|---|
| `GET /novelas` | Frontend | Lista el directorio `proyectos/` y abre cada fichero para leer título, fase en curso y número de versiones | — |
| `GET /novelas/{id}` | Frontend | Ficha de la novela: fase, gate abierto si lo hay, versiones publicadas | `404` |
| `GET /novelas/{id}/versiones/{n}` | Frontend | Manifiesto de la versión y sus capítulos en orden, más el **bloque de paratexto** con el que se arma la portada: título, homenajeado tal como debe escribirse, dedicatoria con su ocasión y las Licencias declaradas de la nota del autor | `404` |
| `GET /novelas/{id}/versiones/{n}/capitulos/{k}` | Frontend | Texto del capítulo tal como esa versión lo fija | `404` |
| `GET /novelas/{id}/versiones/{n}/personajes` | Frontend | Fichas de personajes y lugares con los capítulos **de esa versión** en los que aparecen | `404` |
| `GET /novelas/{id}/versiones/{a}/diff/{b}` | Frontend | Diff de dos manifiestos: qué capítulos cambian | `404` |
| `POST /novelas/{id}/cambios` | Frontend | Petición de cambio del lector. **No toca nada**: abre la Fase 6, que se detiene en su gate | `409` si la novela está ocupada |
| `GET /` y el resto de rutas de la aplicación | Navegador | **Sirve el frontend construido** desde `frontend/dist`, de modo que lectura, PDF y `render_visual` compartan origen (§16.4 arq.) | `404` solo fuera de las rutas declaradas |

**La ficha de personajes cuelga de una versión y no de la novela.** El canon es vivo, pero «los capítulos en los que aparece este personaje» solo tiene respuesta dentro de un manifiesto: sin versión en la ruta, la ficha enlazaría a capítulos de una versión que el lector no está leyendo. Es la misma razón por la que ninguna ruta de lectura del frontend carece de número de versión.

**Ningún endpoint reanuda una ejecución**, y por eso ninguno va protegido. Todo es lectura, más una petición de cambio que no altera nada hasta que el Autor la aprueba en su gate. Que la API quede abierta es una decisión declarada, no un olvido: está en U-17.

**OpenAPI y Schemathesis** cubren la petición de cambio: **una petición malformada no abre la Fase 6.** Una prueba fija además que no existe ninguna ruta que reanude.

*Clase: **A/T** (contrato OpenAPI y Schemathesis). Gate: G1.*

---

## 6. La CLI de Typer

| Comando | Qué hace |
|---|---|
| `storymaker nueva <brief.json>` | Crea el fichero de la novela en `proyectos/` y arranca la invocación |
| `storymaker continuar <novela>` | Reanuda desde el último checkpoint tras un fallo. **Se niega** si hay un gate pendiente |
| `storymaker decidir <novela> <aprobar\|rehacer\|editar\|abortar> [--comentario]` | **La única entrada de una decisión de gate.** La escribe sobre el gate pendiente y reanuda en el mismo proceso; sin gate pendiente o con una decisión desconocida, se rechaza sin tocar nada |
| `storymaker estado <novela>` | Fase, gate abierto, capítulos aprobados, consumo acumulado |
| `storymaker ramificar <novela> <destino>` | **Copia el fichero** y escribe la fila de `procedencia` |
| `storymaker cambiar <novela> "<peticion>"` | Entra en la Fase 6 por la puerta del Autor |
| `storymaker desbloquear <novela>` | Rompe un cerrojo huérfano dejado por un proceso muerto |
| `storymaker evaluar` | Corre los cinco briefs en modo batch con `gates_enabled = false` |

`ramificar` es literalmente copiar el fichero. La alternativa —ramas conviviendo con una columna de rama— obligaría a meter un filtro en **todas** las consultas del sistema, y bastaría con que una lo olvidara para que la rama B leyese capítulos de la rama A.

---

## 7. Los validadores

Son dos familias con dos propósitos distintos, y mezclarlas es la fuente habitual de confusión: **unos comprueban que el código está bien escrito; otros comprueban que una novela concreta está bien hecha.** Los primeros corren mientras programamos y no saben nada de novelas; los segundos corren durante una generación y no saben nada de Python.

### 7.1 Validadores de programación — mientras se escribe el código

Corren en el portátil y en CI, sobre el repositorio. **Ninguno de ellos ve una novela**: ven código, tipos, esquemas y modelos. Su gate es G0, G1 o G2. Los números 18, 20, 21, 22, 22-b y 22-c son la familia de correspondencia de §11e de la arquitectura: los únicos que comparan el código contra estos documentos, o estos documentos entre sí, en vez de contra sí mismo.

| # | Validador | Qué comprueba | Clase | Gate | Bloquea |
|---|---|---|---|---|---|
| 1 | **mypy `--strict`** | Que ningún valor se use de forma incompatible; que el estado del grafo no tenga `dict[str, Any]` | A | G0, G1 | Sí |
| 2 | **ruff + bandit (conjunto `S`)** | Inyección SQL por interpolación, `subprocess` con `shell=True`, `pickle`, aserciones en producción | A | G0, G1 | Sí |
| 3 | **gitleaks** | Que no se commitee el token de Telegram ni las claves de Langfuse. No hay clave de Anthropic: los modelos corren por Claude Code, que el SDK lanza como subproceso con la sesión ya autenticada del Autor | A | G0, G1 | Sí |
| 4 | **pip-audit** | Vulnerabilidades conocidas en el *lockfile* | A | G1 | Sí |
| 5 | **Semgrep `no-update-inmutables`** | Ningún `UPDATE` ni `DELETE` sobre `capitulo_version`, `fase_run`, `version_*` o `mundo_hecho` tras el sello | A | G1 | Sí |
| 6 | **Semgrep `core-domain-puro`** | Que `commons/validation/` no importe el SDK, LangGraph, httpx ni Langfuse | A | G1 | Sí |
| 7 | **Semgrep `validador-no-es-tool`** | Que ningún símbolo del Core Domain acabe en un `allowed_tools` ni decorado como herramienta | A | G1 | Sí |
| 8 | **Semgrep `sin-red-fuera-del-investigador`** | `WebSearch` o `WebFetch` en la definición de cualquier otro rol | A | G1 | Sí |
| 9 | **Semgrep `pii-fuera-del-investigador`** | Que el prompt del investigador no se construya con campos personales del `Brief` | A | G1 | Sí |
| 10 | **Semgrep `indice-solo-por-embeddings`** | Escrituras en tablas `vec_*` desde fuera de `commons/embeddings/` | A | G1 | Sí |
| 11 | **pytest unitarias** | Un caso positivo y uno negativo por validador de ejecución; los siete bloques del ensamblador; la consulta de invalidación; el diff de manifiestos | T | G1 | Sí |
| 12 | **Hypothesis** | Las propiedades generales que reflejan los invariantes de TLA+ sobre el código real | T/A | G1 | Sí |
| 13 | **Pruebas de contrato** | Seis contratos, entre ellos **el mismo capítulo por el nodo y por el hook de `.claude/`, exigiendo el mismo veredicto incidencia por incidencia** | A/T | G1 | Sí |
| 14 | **TLC sobre `formal/tla/harness.cfg`** | Los **cinco invariantes de estado** —`TypeOK`, `NoPublishUnvalidated`, `ResumeIsExactlyOnce`, `RetriesBounded` y `CorpusSelladoNoSeToca`— y las dos propiedades temporales, `PreviousVersionPreserved` y `Termina`, sobre todos los estados alcanzables del modelo (5 capítulos, 2 reintentos) | A | G1 | Sí |
| 15 | **`lake build` de *fixture*** | Que el proyecto Lean compila y que el generador produce el fichero de referencia | A | G1 | Sí |
| 16 | **Integración con agente falso** | El grafo completo sobre SQLite temporal: recorrido en batch, atomicidad del checkpoint, reanudación, Fase 6, ramificación, reintentos agotados | T | G1 | Sí |
| 17 | **Suite adversaria determinista** | Inyección por texto pegado, página hostil, herramienta prohibida, exfiltración de PII, evasión del guardrail | T | G1 | Sí |
| 18 | **Identidad nodo↔acción** | Que los nombres de nodo del grafo sean iguales a las acciones de `harness.tla` **y que su conjunto de aristas sea igual a la definición `Aristas`** que gobierna el `Next` | A | G1 | Sí |
| 19 | **Steiger** | Las dos reglas de FSD sobre `frontend/src` | A | G1 | **No, informa** |
| 20 | **`registro_de_validadores`** | Que el registro de validadores deterministas, la tabla de §11a de la arquitectura y la de §7.2 de este documento coinciden por pares: mismo conjunto, mismo punto de ejecución, misma condición de bloqueo | A/T | G1 | Sí |
| 21 | **`inventario_del_plan`** | Sobre todo `specs/*/plan.md`, con sus filas `P-nn` y sus filas `IMP-nn`: que cada ruta y cada símbolo de la columna «Ficheros y símbolos» existe en el árbol, y que todo módulo de `backend/src/storymaker/**` —salvo los `__init__.py`— y todo módulo `.ts` o `.tsx` de `frontend/src/**` está declarado en algún ítem | T | G1 | **No, informa en dos cubos** |
| 22 | **`anclas_de_procedencia`** | Que toda ancla de un docstring de módulo —primera línea, formato `spec: §3.6 · arq: §11a`— apunta a un apartado que existe, y que **todo apartado de §3 y §4 de este documento tiene al menos un módulo que lo cite** | T | G1 | **No, informa** |
| 22-b | **`matrices_de_trazabilidad`** | Que las tres matrices —la de la raíz y las dos de `specs/`— están bien formadas, no repiten identificador, no citan ítems que ningún plan declara, declaran resolución para cada huérfano y **no encogen**. El recuento de filas en `GAP` se informa | A | G1 | **Sí, salvo el recuento de huecos, que informa** |
| 22-c | **`requisitos_declarados`** | Sobre la tabla de §10 de este documento y la de §12 de la spec del frontend: que todo ítem citado en la columna «Ítems» exista en el plan correspondiente, que ningún apartado de §3 y §4 se quede sin ningún requisito que lo cite y que ningún identificador se repita ni se reutilice | T | G1 | **No, informa** |
| 23 | **CrossHair** | Las cinco funciones puras críticas: `normalizar`, `hay_solape_temporal`, `es_anacronico`, `truncar_por_prioridad`, `capitulos_afectados` | A | G2 | No |
| 24 | **mutmut ≥ 80 %** | Que la suite detecte de verdad un validador silenciosamente roto | T | G2 | No |
| 25 | **Evals sobre cinco briefs** | Conducta del sistema con modelo real: cero incidencias críticas, 5/5 completan, ≥ 70 % de capítulos al primer intento | T/I | G2 | No |
| 26 | **Varianza del juez** | N ejecuciones sobre la misma novela; se publica la desviación por criterio | T | G2 | No |
| 27 | **Red-teaming manual por hito** | Una persona intentando romperlo a mano, con modelo real | I | G2 | No |

**La regla número 7 merece un comentario**, porque es análisis estático haciendo lo que ninguna prueba puede hacer bien: una prueba comprobaría que *hoy* los validadores corren; la regla impide que *mañana* alguien los convierta en algo que un modelo pueda olvidarse de llamar.

**Y la número 24 es la que protege a todas las demás.** Un validador que siempre devuelve «correcto» es indistinguible de un validador correcto mirando la suite en verde: los capítulos se aprueban, los *scores* salen perfectos y nadie se entera hasta leer la novela.

### 7.2 Validadores de ejecución — mientras se genera una novela

Corren dentro del grafo, sobre el contenido. Su gate es G3, G4, G5 o G6. **Todos son nodos o aristas condicionales; ninguno es una herramienta que un agente decida llamar.**

#### a) Programáticos — deterministas, coste cero

| Validador | Comprueba | Punto | Clase | Gate | Bloquea |
|---|---|---|---|---|---|
| `schema_guard` | La salida de cada rol cumple su modelo Pydantic | Salida de cada nodo agente | A | G3 | Sí |
| `nombres_exactos` | Homenajeado y personajes escritos exactamente como en el canon | Post `WriteChapter` | A | G3 | Sí |
| `longitud_capitulo` | Palabras dentro del rango del brief | Post `WriteChapter` | A | G3 | Sí |
| `guardrail_prohibidas` | Términos prohibidos en tres niveles, **normalizando antes de comparar** | Post `WriteChapter` | A/T | G3 | Sí |
| `anacronismo_fechado` | Ningún objeto, término o concepto con `fecha_inicio` posterior a la fecha narrativa | Post `WriteChapter` | A | G3 | Sí |
| `anclaje_valido` | Todo anclaje apunta a un hecho del corpus sellado o a una Licencia declarada | Post `WriteChapter` | A | G3 | Sí |
| `cobertura_anclada` | Cada elemento obligatorio del brief está anclado a ≥1 escena de la escaleta | Gate de Plotting | A | G4 | Sí |
| `arco_anclado` | Todo personaje presente en **≥3 escenas** de `plan_escena_personaje` tiene fila en `canon_arco`; si su arco es positivo o negativo, **≥2 hitos** anclados a escenas de capítulos estrictamente crecientes. **El arco plano cuenta**: declarar que un personaje no se transforma es la decisión que el validador reclama. El homenajeado es la única excepción — no puede tener arco plano y su último hito cae en el tercio final | Gate de Plotting | A | G4 | Sí |
| `cobertura_capitulo` | Lo que la escaleta encomendó a este capítulo aparece en él | Post `Extract` | A | G3 | Sí |
| `cobertura_personalizacion` | Cada elemento obligatorio aparece en ≥1 capítulo | Gate de Writing | A | G5 | Sí |
| `render_visual` | Índice, ficha de personajes y portada renderizan bien (Playwright MCP) | Dentro de `PublishVersion`, sobre la versión candidata, **antes del `commit`** | D | G5 | Sí |

**El linter de auto-similitud no es uno de los once.** El cuarto uso que §16.2 de la arquitectura da a los embeddings —detectar repeticiones y auto-similitud entre capítulos, como linter de prosa y de originalidad— se recoge aquí por lo que es: el vector del capítulo recién escrito se compara con los de los anteriores y se abre incidencia de severidad `aviso` cuando la repetición pasa del umbral declarado. No bloquea, no gobierna ninguna arista y no entra en la tabla de arriba, porque la lista de §11a es cerrada y esto no es una puerta: es una señal para el informe del gate de Writing.

**La cobertura se comprueba tres veces y cada una cuesta menos que la siguiente.** `cobertura_anclada` convierte un fallo de diez capítulos escritos y pagados en un fallo de escaleta; `cobertura_capitulo` convierte un fallo de novela en un reintento de capítulo; `cobertura_personalizacion` se queda como red de seguridad, porque anclar no es escribir y escribir el capítulo N no garantiza que ningún otro se quedara sin su parte.

#### b) Semánticos — los juzga un modelo

| Validador | Comprueba | Punto | Clase | Gate | Bloquea |
|---|---|---|---|---|---|
| `respaldo_fuente` | Que la cita guardada sostenga el enunciado del hecho | Cierre de Investigation | I | G4 | **No**: degrada a `inferido` |
| `ejecucion_escaleta` | Que los beats planificados para este capítulo hayan ocurrido | Post `Extract` | I | G4 | **No**: aviso |
| `arco_ejecutado` | Que los hitos de arco anclados a este capítulo hayan ocurrido | Post `Extract` | I | G4 | **No**: aviso |
| `juez_rubrica` | Siete criterios 1-10 con justificación | `Judge` | T/I | G5 | Sí, por umbral |
| `revision_humana` | La misma rúbrica, aplicada por una persona a ≥1 novela completa | Fuera de línea | I | G4 | — |

**Tres de ellos no bloquean, y es deliberado.** Una novela de regalo no se detiene porque una fecha del contexto venga mal citada. Y `ejecucion_escaleta` y `arco_ejecutado` son **el juicio de un modelo sobre si algo narrativo ocurrió, y eso no es una puerta**: un beat resuelto de otra manera no es un error, y un validador bloqueante gastaría los dos reintentos discutiendo con el editor sobre una lectura. Abren incidencia de severidad `aviso`, entran en el informe del gate de Writing y **viajan al bloque 1 del paquete del capítulo siguiente**, donde el escritor lee qué quedó pendiente. Ese viaje es lo que los distingue de un simple apunte.

**Lo que ninguno de los dos hace es juzgar si el arco está bien.** Cuentan si los hitos ocurrieron, que es contable; si la transformación está ganada o solamente anunciada lo dice el juez sobre la obra entera.

**Que `juez_rubrica` y `revision_humana` usen el mismo fichero de rúbrica** es lo que hace comparable el juicio humano con el del modelo.

#### c) Formal — Lean 4 sobre la cronología

| Punto | Sobre qué | Gate | Efecto del fallo |
|---|---|---|---|
| Gate de Plotting | La cronología deducida de la escaleta y de las fechas vitales | G4 | La escaleta vuelve al arquitecto. Aún no hay una línea escrita |
| Dentro de `Validate`, **pasada del extractor** de cada capítulo | La cronología acumulada, ya con los eventos narrativos que el extractor leyó | G3 | El capítulo vuelve al editor con el invariante violado como incidencia |
| Antes de `PublishVersion` | La cronología completa de la novela | G5 | **La versión no se publica. No hay anulación** |
| Tras invalidar capítulos en Fase 6 | La cronología de un capítulo ya aprobado, cuyas filas están escritas desde que se aprobó | G3 | Solo se reescriben los capítulos que Lean tumba; verificarlos no invoca a nadie |

Los cuatro invariantes: orden temporal de los eventos; edad del personaje coherente con su fecha de nacimiento; un personaje no está en dos lugares a la vez; **un personaje no aparece fuera de sus fechas vitales documentadas**. El cuarto es el caso demostrativo: un personaje histórico en escena tres años después de su muerte le parece perfectamente natural a un modelo, que no tiene aritmética temporal. A Lean no. *Clase: **A**.*

#### d) Guardas estructurales — no producen incidencias, impiden el acto

No son validadores en el sentido de emitir un veredicto: son cerrojos que hacen imposible el estado malo. **Su clase es A porque no hay nada que comprobar en ejecución: el camino no existe.**

| Guarda | Impide | Gate |
|---|---|---|
| Guarda de presupuesto de contexto | Que se emita una llamada por encima del techo del rol | G3 |
| Cuota de herramientas (`PreToolUse`) | La cuarta `WebSearch` del investigador | G3 |
| Truncado de respuesta (`PostToolUse`) | Que una página entera entre en contexto | G3 |
| `allowed_tools` y `max_turns` por invocación | Que un rol use una herramienta que no le corresponde | G4 |
| Cuarentena de texto libre | Que el texto pegado llegue en bruto a un prompt | G3 |
| *Triggers* de inmutabilidad | Que se sobrescriba un capítulo, una ejecución o una versión | G1 |
| Comprobación de `sqlite-vec` al abrir | Que el sistema corra sin búsqueda semántica sin que nadie lo note | G1 |
| Cerrojo de fichero por novela | Dos invocaciones simultáneas sobre la misma novela | G1 |

#### e) Post-ejecución — aserciones sobre la traza

Tras publicar, un script consulta la API de Langfuse y **afirma propiedades sobre la trayectoria real**. Esto es T, no D: una traza que nadie consulta no verifica nada.

- Todo capítulo aprobado tiene un span de escritor y al menos uno de validación **anterior** a su aprobación.
- Ningún capítulo tiene más spans de `intento_` que el límite de reintentos.
- El coste acumulado está por debajo del presupuesto declarado.
- **Ningún span de un rol distinto del investigador contiene `WebSearch` ni `WebFetch`.**
- Toda decisión de gate tiene actor y momento.

La primera y la última son `NoPublishUnvalidated` y la trazabilidad de la intervención humana, comprobadas sobre una ejecución real en lugar de sobre un modelo. *Clase: **T**. Gate: G6.*

---

## 8. Casos de error, en una tabla

Qué distingue un error de una incidencia: **una incidencia es un defecto del contenido y tiene camino de vuelta; un error es una avería y detiene la invocación.** Confundirlos aprobaría capítulos por avería.

| Caso | Tipo | Respuesta |
|---|---|---|
| Palabra prohibida en el capítulo | Incidencia bloqueante | Vuelve al editor; agotados los reintentos, `Fail` |
| Personaje fuera de sus fechas vitales | Incidencia bloqueante | Vuelve al editor con el invariante de Lean violado |
| Beat planificado que no ocurre | Incidencia `aviso` | Informe del gate y bloque 1 del capítulo siguiente |
| Hecho sin respaldo en su cita | Marca | Degrada a `inferido`, destacado en el informe del gate |
| Salida del modelo que no valida | Incidencia | Reintento con el error en el prompt; después, bloqueante |
| Prompt por encima del techo del rol | Error | La llamada no se emite |
| `lake` ausente o subproceso roto | Error de entorno | **Se distingue del veredicto negativo**; detiene, no aprueba |
| `sqlite-vec` que no carga | Error de arranque | Se detiene con mensaje explícito |
| Segunda invocación sobre la misma novela | Rechazo | `NovelaOcupada` / `409` |
| Decisión de gate malformada | Rechazo | El grafo no se reanuda |
| `decidir` sin gate pendiente, o `continuar` con uno | Rechazo | La novela no se reanuda |
| Autor que no contesta un gate | Aparcamiento | Estado propio; **nunca auto-aprobación** |

---

## 9. Clases de confianza declaradas

Resumen de lo que este documento compromete, como exige `AGENTS.md`. Cada pieza con su clase primaria y el gate que la cubre.

| Pieza | Clase | Gate |
|---|---|---|
| Esquema, `CHECK` e inmutabilidad por *trigger* | A/T | G1 |
| Estado del grafo e identidad nodo↔acción | A/T | G1 |
| Invocación del SDK y sus tres guardas | A/T | G1, G6 |
| Ensamblador de paquetes | A/T | G1, G2 |
| Índices `vec0` y su escritura transaccional | A/T | G1 |
| Core Domain (`commons/validation`) | A/T | G1, G2 |
| Generador y *runner* de Lean | A | G3, G5 |
| Observabilidad y *scores* | D/T | G6 |
| Las seis fases, de extremo a extremo | T/D | G1, G2 |
| API de FastAPI | A/T | G1 |
| Serialidad de las micro-sesiones del arquitecto (P-134) | A/T | G1 |
| Acta de grilling y de revisión por documento (P-135) | **I** | G4 |
| CLI | T | G1 |
| Correspondencia documento↔código (§7.1 nº 18, 20, 21, 22) | A/T | G1 |
| Fiabilidad de los validadores semánticos | **I** | G4 |
| Lectura de la API sin autenticación | **U-17** | — |

**Riesgos aceptados que este backend hereda**, todos con fila en §5 de `verification.md`: U-1 brecha de refinamiento, U-18 veracidad de los documentos sobre el dominio, U-2 verdad histórica del corpus, U-3 reproducibilidad textual, U-4 evasión por paráfrasis, U-7 coste estimado, U-8 dominios de `WebFetch`, U-9 varianza del juez, U-13 fiabilidad del verificador, U-15 disponibilidad de `sqlite-vec`, U-14 cita fabricada, U-16 fiabilidad de `ejecucion_escaleta` y `arco_ejecutado`, U-17 API de lectura sin autenticación.

---

## 10. Requisitos

Los apartados anteriores son el contrato, y están escritos en prosa porque un contrato necesita decir también **por qué**. Esta tabla es ese mismo contrato en su forma comprobable: **cada fila enuncia una sola cosa y se puede responder con un sí o un no**. No añade ninguna decisión; si una fila y su apartado discrepan, manda el apartado y la fila está mal escrita.

**Cómo se lee cada columna.** El identificador `REQ-BE-nn` es estable y **no se reutiliza jamás**: un requisito retirado deja su fila con la nota, nunca cede su número. El apartado es de dónde se extrae el enunciado, y es también **de dónde hereda su clase de confianza y su gate**, que allí están declarados; un requisito que se compruebe de otra manera lo dice en su propia fila. Los ítems son los de [`plan.md`](plan.md) que lo materializan, con el prefijo `FE:` cuando quien lo realiza es el plan del frontend. Un guion en esa columna significa que **ningún ítem lo realiza todavía**, que es justamente lo que `requisitos_declarados` informa.

**Lo que esta tabla no cubre a propósito** son los validadores de §7.1 y §7.2. Sus tablas ya son listas con identificador propio —el nombre del validador—, comparadas por pares contra §11a de la arquitectura y contra el registro, de modo que duplicarlas aquí añadiría cincuenta y siete filas sin añadir ninguna comprobación. Lo que sí se enuncia es lo que §7 afirma **alrededor** de ellas: que ninguno sea una herramienta, en qué orden corren las dos pasadas y cuáles no bloquean.

### 10.1 Puesta en marcha y configuración

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-BE-01 | La CLI y la API invocan ambas la misma función de invocación del grafo; la API no tiene un camino propio hacia él | §2.1 | P-113, P-138, P-57 |
| REQ-BE-02 | Existe un único objeto `Settings`, cargado una vez al arrancar e inyectado a quien lo necesita; ningún módulo consulta el entorno en caliente | §2.2 | P-02 |
| REQ-BE-03 | Los valores por defecto de §19 de la arquitectura son constantes con nombre, no números sueltos repartidos por el código | §2.2 | P-03 |
| REQ-BE-04 | Ningún secreto se escribe en el repositorio, y `gitleaks` lo comprueba en G0 y en G1 | §2.2 | P-04, P-05 |
| REQ-BE-05 | El sistema no guarda credencial de Anthropic: el Agent SDK lanza Claude Code como subproceso y hereda su sesión | §2.2 | P-27 |
| REQ-BE-06 | Al abrir una novela se carga `sqlite-vec`, y si falla el arranque se detiene; **nunca se degrada en silencio** a un sistema sin búsqueda semántica | §2.3 | P-19 |
| REQ-BE-07 | Al abrir se aplican las migraciones pendientes y se rechaza un fichero con versión de esquema posterior a la que el código conoce | §2.3 | P-18 |
| REQ-BE-08 | Al abrir se activan `journal_mode=WAL`, `foreign_keys=ON` y `synchronous=NORMAL` | §2.3 | P-19 |
| REQ-BE-09 | Toda operación que vaya a invocar el grafo toma antes el cerrojo de la novela | §2.3 | P-59 |

### 10.2 Contratos de `commons/`

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-BE-10 | Nadie fuera de `commons/db` construye SQL a mano contra las tablas del arnés | §3.1 | P-20 |
| REQ-BE-11 | Todas las tablas son `STRICT` y llevan `CHECK` sobre sus enumerados; un valor fuera de rango **aborta la transacción** y no se normaliza | §3.1 | P-16 |
| REQ-BE-12 | La regla Semgrep `no-update-inmutables` impide **escribir** un `UPDATE` o un `DELETE` sobre las tablas inmutables | §3.1 | P-06 |
| REQ-BE-13 | Los *triggers* `BEFORE UPDATE` y `BEFORE DELETE` impiden **ejecutarlo**, protegiendo el contenido pero admitiendo el cambio de estado de `capitulo_version` y el cierre de `fase_run` con su consumo | §3.1 | P-17 |
| REQ-BE-14 | En `mundo_hecho` la inmutabilidad se condiciona a la existencia del sello: el verificador puede degradar antes, nadie puede escribir después | §3.1 | P-17, P-79 |
| REQ-BE-15 | El checkpoint de LangGraph y la escritura de dominio ocurren en la misma transacción, cerrada por el envoltorio de invocación y nunca por el nodo | §3.1 | P-21 |
| REQ-BE-16 | Una novela inexistente produce `NovelaNoEncontrada`, que la CLI traduce a mensaje y la API a `404` | §3.1 | P-128 |
| REQ-BE-17 | El estado del grafo es un `TypedDict` total y explícito, sin `dict[str, Any]`, comprobado por mypy `--strict` | §3.2 | P-54 |
| REQ-BE-18 | Los nodos se llaman igual que las acciones de `harness.tla`, y una prueba exige que sean iguales tanto el conjunto de nombres como el de aristas | §3.2 | P-55, P-62 |
| REQ-BE-19 | `invocar` avanza hasta un `interrupt()` o hasta el final y devuelve nodo de parada, gate abierto y consumo; entre una invocación y la siguiente no queda nada vivo | §3.2 | P-57 |
| REQ-BE-20 | El cerrojo es un fichero por novela, cubre a la CLI y a la API por igual, y **quien llega segundo es rechazado con `NovelaOcupada`, no encolado** | §3.2 | P-59 |
| REQ-BE-21 | Una excepción dentro de un nodo se registra en `fase_run`, suelta el cerrojo y deja intacto el último checkpoint | §3.2 | P-60, P-128 |
| REQ-BE-22 | Agotar los reintentos lleva a `Fail`, que es un estado declarado del grafo y no una excepción | §3.2 | P-60 |
| REQ-BE-23 | Todas las llamadas a un modelo pasan por una única función de invocación; ningún módulo llama al Agent SDK por su cuenta | §3.3 | P-27 |
| REQ-BE-24 | Cada invocación fija el modelo, `allowed_tools`, `max_turns` y el techo de tokens del rol | §3.3 | P-27, P-32 |
| REQ-BE-132 | Cada invocación adjunta al prompt el JSON Schema del esquema de salida del rol, generado del mismo modelo contra el que valida `schema_guard`, y ese esquema cuenta en la estimación de presupuesto | §3.3 | P-27 |
| REQ-BE-25 | El prompt ensamblado se **estima** antes de emitir, por lo alto y con margen declarado, y la llamada **no se emite** si excede el techo del rol | §3.3 | P-28 |
| REQ-BE-26 | Un hook `PreToolUse` deniega la llamada en cuanto se agota la cuota de herramientas del rol | §3.3 | P-29 |
| REQ-BE-27 | Un hook `PostToolUse` reescribe el resultado de la herramienta antes de que entre en el contexto del agente | §3.3 | P-30 |
| REQ-BE-28 | `schema_guard` valida la salida contra el esquema del rol **antes de escribir en SQLite**, reintenta con el error de validación inyectado y abre incidencia al agotarse | §3.3 | P-31 |
| REQ-BE-29 | El ensamblador monta los siete bloques en orden con sus techos declarados y 12.000 tokens en total | §3.4 | P-33, P-34, P-35, P-36, P-37 |
| REQ-BE-30 | El paquete **nunca excede** el techo total | §3.4 | P-38 |
| REQ-BE-31 | El recorte va por la cola de la lista ya ordenada por relevancia, y el bloque de continuidad es el último que se toca | §3.4 | P-38 |
| REQ-BE-32 | Los anclajes explícitos de la escaleta entran siempre, antes que cualquier vecino semántico | §3.4 | P-38 |
| REQ-BE-33 | La recuperación la hace el ensamblador con una consulta derivada de las escenas del capítulo, y con las mismas entradas devuelve los mismos vecinos | §3.4 | P-35 |
| REQ-BE-34 | El paquete se persiste entero y se enlaza desde su span de Langfuse | §3.4 | P-39 |
| REQ-BE-35 | Un bloque vacío no es un error; la escaleta ausente del capítulo pedido **aborta la invocación** en lugar de generar a ciegas | §3.4 | P-33 |
| REQ-BE-36 | `commons/embeddings` es el único módulo autorizado a escribir en las tablas `vec_*`, y una regla Semgrep lo impone | §3.5 | P-24, P-06 |
| REQ-BE-37 | El índice se escribe en la misma transacción que la fila que indexa | §3.5 | P-24 |
| REQ-BE-38 | Una fila de `edicion_humana` dispara el reembedding de lo que el Autor tocó | §3.5 | P-26 |
| REQ-BE-39 | `vec_resumen.vigente` pasa a 1 al aprobar una versión y a 0 en la que sustituye, y el bloque de memoria filtra por él | §3.5 | P-25 |
| REQ-BE-40 | No se usan claves de partición; lo que en otro sistema serían particiones aquí son columnas de metadato | §3.5 | P-15, P-23 |
| REQ-BE-41 | El Core Domain es Python puro: no importa el Agent SDK, LangGraph, `httpx` ni Langfuse, y una regla Semgrep lo impone | §3.6 | P-40, P-06 |
| REQ-BE-42 | Un validador recibe datos y devuelve incidencias tipadas: nunca escribe en la base, nunca llama a un modelo, nunca sale a la red | §3.6 | P-40 |
| REQ-BE-43 | El grafo y el hook de `.claude/` se sirven de **una sola implementación**, y una prueba de contrato ejecuta el mismo capítulo por ambos caminos exigiendo el mismo veredicto incidencia por incidencia | §3.6 | P-46, P-116 |
| REQ-BE-44 | `REGISTRO` declara por validador el nombre, el punto de ejecución, si bloquea y **la ruta de su implementación como cadena**, nunca como `import` | §3.6 | P-131 |
| REQ-BE-45 | Un validador que no está en el registro no corre por ningún camino | §3.6 | P-131 |
| REQ-BE-46 | El registro, la tabla de §11a de la arquitectura y la de §7.2 de este documento se comparan **por pares** en CI | §3.6 | P-132 |
| REQ-BE-47 | El generador produce el fichero Lean desde `cronologia_*` y las fechas vitales del canon y del corpus, invoca `lake build` por subproceso y devuelve veredicto e invariante violado con sus eventos | §3.7 | P-47, P-48 |
| REQ-BE-48 | Los cuatro invariantes se verifican **por decisión**, de modo que la demostración es automática y no puede atascarse | §3.7 | P-49 |
| REQ-BE-49 | Lean corre en tres puntos: el gate de Plotting, la pasada del extractor de cada capítulo y antes de publicar | §3.7 | P-80, P-84, P-91 |
| REQ-BE-50 | `lake` ausente o un subproceso roto es **error de entorno** y se distingue del veredicto negativo: detiene, no aprueba | §3.7 | P-48 |
| REQ-BE-51 | Langfuse recibe **una sesión por novela**, que incluye la entrevista y todas las regeneraciones, y **un span por invocación** nombrado por capítulo, rol e intento | §3.8 | P-50 |
| REQ-BE-52 | Todos los *scores* de validadores y todas las decisiones de gate viajan a la traza: la intervención del Autor queda trazada igual que la de un agente | §3.8 | P-51 |
| REQ-BE-53 | Los prompts de rol viven en Langfuse como fuente de verdad, se inyectan como `system_prompt` y su id de versión viaja en el span | §3.8 | P-52 |
| REQ-BE-54 | `total_cost_usd` se etiqueta **siempre** como estimación en cliente, nunca como facturación | §3.8 | P-51 |

### 10.3 Las seis fases

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-BE-55 | El texto pegado entra en `intake_texto_crudo` y solo avanza convertido en filas tipadas con `origen = 'texto_libre_no_confiable'` | §4.1 | P-66 |
| REQ-BE-56 | Una extracción previa rellena lo que puede y el entrevistador **solo pregunta por lo que sigue vacío o ambiguo** | §4.1 | P-68 |
| REQ-BE-57 | La verdad son las filas de `intake_dato`; el `Brief` serializado es la fotografía auditable y no decide nada | §4.1 | P-64 |
| REQ-BE-58 | Las contradicciones del brief las detecta un `@model_validator` de Pydantic, no un modelo | §4.1 | P-65 |
| REQ-BE-59 | Ninguna cadena del texto en bruto aparece jamás en el prompt del escritor, y una aserción lo comprueba sobre cargas de inyección | §4.1 | P-67 |
| REQ-BE-60 | Un brief incompleto tras agotar las preguntas no bloquea: el gate se abre con el informe de lo que falta | §4.1 | P-127 |
| REQ-BE-133 | Las preguntas del entrevistador se guardan y el aviso del gate de Intake las enseña; el Autor las contesta con «rehacer» y su comentario, y `Configure` vuelve a entrevistar con todas las respuestas dadas | §4.1 | P-68 |
| REQ-BE-134 | Repetir `Configure` no duplica nada: el texto pegado se extrae una vez y un dato dictado que ya existe no se reescribe | §4.1 | P-68, P-66 |
| REQ-BE-61 | El prompt del investigador se construye solo con período y lugar; los campos personales del `Brief` no salen a la red, y lo imponen una regla Semgrep y una aserción | §4.2 | P-74, P-06 |
| REQ-BE-62 | El investigador dispone de **3 `WebSearch` y 3 `WebFetch` en una sesión**, y el tope lo impone el arnés con sus hooks, no una instrucción del prompt | §4.2 | P-69, P-29 |
| REQ-BE-63 | Cada hecho se guarda con su enunciado, su estado epistémico, sus fuentes, el `fase_run_id` que lo escribió y una cita de 300 caracteres como mucho | §4.2 | P-70 |
| REQ-BE-64 | El verificador es un agente distinto, **sin herramientas y sin red**, que lee los pares enunciado–cita por lotes de veinte | §4.2 | P-72 |
| REQ-BE-65 | Un veredicto `no_respaldado` **degrada el hecho a `inferido` y lo marca**: no lo borra y no detiene la fase | §4.2 | P-72 |
| REQ-BE-66 | Rehacer no contamina: solo cuentan los hechos del `fase_run` vigente, y los anteriores quedan como historia consultable | §4.2 | P-71 |
| REQ-BE-67 | Cero hechos en una dimensión no bloquea: es una fila del informe del gate, con el recuento por dimensión delante del Autor | §4.2 | P-73 |
| REQ-BE-68 | El arquitecto inventa la Premisa y el Tema, y construye el canon completo y la escaleta jerárquica con sus anclajes | §4.3 | P-75 |
| REQ-BE-69 | `grado_licencia`, `arcaismo` y `contenido_admisible` se copian a `canon_obra.estilo_json`, que es como llegan al bloque de reglas del paquete | §4.3 | P-76 |
| REQ-BE-70 | El arquitecto **no recibe el corpus entero**: los hechos le llegan por búsqueda semántica con la consulta derivada de lo que planifica | §4.3 | P-125 |
| REQ-BE-71 | Cada hueco dispara **una única micro-llamada** al investigador con una sola `WebSearch`, con un tope de cinco huecos por ejecución | §4.3 | P-77 |
| REQ-BE-72 | Un veredicto `no_encontrado` **autoriza la invención**, que entra como fila `inferido` con `origen = 'invencion_autorizada'`, sin fuente y con `respaldo = 'no_aplica'` | §4.3 | P-77 |
| REQ-BE-73 | La invención **no se topa, se cuenta**, y aparece por dimensión en el informe del gate | §4.3 | P-78 |
| REQ-BE-74 | Al aprobarse la escaleta se calcula el hash sobre el contenido ordenado de las tablas `mundo_*` vigentes y el corpus pasa a ser de solo lectura | §4.3 | P-79 |
| REQ-BE-75 | El escritor **redacta el capítulo entero de una vez**: la escena es unidad de planificación y de traza, no de redacción | §4.4 | P-81 |
| REQ-BE-76 | `Validate` corre en dos pasadas, ambas dentro del bucle de reparación: primero la determinista, después la del extractor | §4.4 | P-82, P-83 |
| REQ-BE-77 | La pasada del extractor es **una sola llamada y solo si la determinista no dejó incidencias** | §4.4 | P-83 |
| REQ-BE-78 | Sobre la salida del extractor corren `cobertura_capitulo`, `ejecucion_escaleta`, `arco_ejecutado` y los cuatro invariantes de Lean sobre la cronología acumulada | §4.4 | P-84 |
| REQ-BE-79 | El extractor es un rol independiente del escritor: quien produjo el capítulo no declara qué hechos usó ni qué beats ejecutó | §4.4 | P-83 |
| REQ-BE-80 | Las filas del extractor cuelgan del `capitulo_version_id` del intento que las produjo, de modo que las de un intento descartado no hace falta borrarlas | §4.4 | P-85 |
| REQ-BE-81 | Un capítulo admite **2 reintentos**; agotados, el grafo transita a `Fail` | §4.4 | P-86, P-60 |
| REQ-BE-82 | `ApproveChapter` y el checkpoint ocurren en la misma transacción | §4.4 | P-87 |
| REQ-BE-83 | Los dos extractores son roles con techo declarado: 12.000 el de capítulo y 6.000 el de intake | §4.4 | P-32 |
| REQ-BE-84 | Los avisos de ejecución viajan al bloque de encargo del paquete del capítulo siguiente, donde el escritor lee qué quedó pendiente | §4.4 | P-88 |
| REQ-BE-85 | El juez devuelve un esquema de puntuaciones y **no tiene permiso de escritura sobre el texto** | §4.5 | P-90 |
| REQ-BE-86 | El manifiesto registra los hashes, los prompts, los modelos, los embeddings y la versión del SDK | §4.5 | P-93 |
| REQ-BE-87 | El PDF se imprime con `page.pdf()` **desde la misma ruta que lee el navegador**, sin una segunda maquetación | §4.5 | P-94, FE:IMP-30 |
| REQ-BE-88 | `render_visual` juzga la **versión candidata** con la transacción todavía abierta, y `publication.publish` conduce el navegador **interceptando sus peticiones de datos** | §4.5 | P-92 |
| REQ-BE-89 | Si el render falla, la transacción se deshace y no hay versión publicada | §4.5 | P-92 |
| REQ-BE-90 | Publication no tiene gate humano: el manuscrito ya se aprobó al cerrar Writing | §4.5 | — |
| REQ-BE-91 | Un fallo de Lean antes de publicar impide la publicación **sin anulación posible** | §4.5 | P-91 |
| REQ-BE-92 | La petición del lector y la edición humana directa entran por la misma puerta y disparan la misma maquinaria | §4.6 | P-95, P-101 |
| REQ-BE-93 | La petición se resuelve por búsqueda semántica contra canon y corpus, y **el Autor confirma los candidatos en el gate** | §4.6 | P-95 |
| REQ-BE-94 | Se modifica la fila del hecho, **nunca el texto**, y el cambio queda en `audit_log` | §4.6 | P-96 |
| REQ-BE-95 | `uso_hecho` determina qué capítulos se regeneran | §4.6 | P-97 |
| REQ-BE-96 | Los capítulos posteriores pasan a `Invalidado` y se les corren **solo los validadores de coste cero**; si ninguno falla, se quedan como están | §4.6 | P-97 |
| REQ-BE-97 | El manifiesto nuevo reutiliza los capítulos no tocados, y la versión anterior sobrevive entera | §4.6 | P-98 |
| REQ-BE-98 | El diff sale de comparar dos manifiestos con un `JOIN` | §4.6 | P-99 |
| REQ-BE-99 | El gate de Regeneration enseña el recuento de capítulos afectados **antes de pagarlo** y permite abortar | §4.6 | P-100 |
| REQ-BE-100 | El nodo de gate llama a `interrupt()`, el checkpointer persiste y la invocación termina | §4.7 | P-103 |
| REQ-BE-101 | El gate ofrece cuatro decisiones: aprobar, rehacer con comentario, editar y abortar | §4.7 | P-104 |
| REQ-BE-102 | El comentario de «rehacer» se inyecta como bloque extra del prompt y **cuenta contra el límite de reintentos** | §4.7 | P-104 |
| REQ-BE-103 | La notificación va detrás de la interfaz `Notifier`, con Telegram como única implementación, **solo avisa** y trae los comandos para decidir | §4.7 | P-105 |
| REQ-BE-104 | Sin respuesta, el *timeout* **aparca** la ejecución con estado propio; **no hay auto-aprobación** | §4.7 | P-107 |
| REQ-BE-105 | `gates_enabled = false` desactiva los cinco gates y el hecho queda registrado en el manifiesto | §4.7 | P-108, P-93 |

### 10.4 API, CLI, validadores y errores

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-BE-106 | `storymaker decidir` escribe la decisión sobre el gate pendiente y reanuda en el mismo proceso | §6 | P-109 |
| REQ-BE-107 | Al reanudar, el gate decidido no se reabre ni se vuelve a avisar; `continuar` no reanuda un gate pendiente | §4.7 | P-109 |
| REQ-BE-108 | Una decisión sin gate pendiente, o fuera de las cuatro, se rechaza sin tocar nada | §6 | P-109 |
| REQ-BE-109 | `GET /novelas` lista el directorio `proyectos/` y abre cada fichero: no hay registro global de novelas | §5 | P-111 |
| REQ-BE-110 | El endpoint de versión devuelve el manifiesto, sus capítulos en orden y el **bloque de paratexto** con el que se arma la portada | §5 | P-110 |
| REQ-BE-111 | La ficha de personajes cuelga de una **versión**, no de la novela | §5 | P-110 |
| REQ-BE-112 | `POST /novelas/{id}/cambios` no toca nada: abre la Fase 6, que se detiene en su gate | §5 | P-110, P-95 |
| REQ-BE-113 | FastAPI sirve el frontend construido desde `frontend_dist` y declara su URL base en `frontend_base_url`, de modo que lectura, PDF y `render_visual` compartan origen | §5 | P-136 |
| REQ-BE-114 | Ningún endpoint de la API reanuda una ejecución | §5 | P-109, P-138 |
| REQ-BE-115 | El contrato OpenAPI y Schemathesis garantizan que **una petición de cambio malformada no abre la Fase 6** | §5 | P-112 |
| REQ-BE-116 | La CLI expone los ocho comandos declarados | §6 | P-113 |
| REQ-BE-117 | `ramificar` **copia el fichero** y escribe la fila de `procedencia`; no hay columna de rama en las consultas | §6 | P-102 |
| REQ-BE-118 | `evaluar` corre los cinco briefs en modo batch con `gates_enabled = false` | §6 | P-120, P-108 |
| REQ-BE-119 | Todos los validadores de ejecución son nodos o aristas condicionales; **ninguno es una herramienta que un agente decida llamar** | §7.2 | P-06, P-56 |
| REQ-BE-120 | Las aristas condicionales leen booleanos calculados en Python, nunca la salida de un modelo | §7.2 | P-56 |
| REQ-BE-121 | Tres validadores semánticos no bloquean: `respaldo_fuente` degrada, y `ejecucion_escaleta` y `arco_ejecutado` abren aviso | §7.2b | P-72, P-84 |
| REQ-BE-122 | El linter de auto-similitud abre incidencia de aviso y **no es uno de los once validadores de §11a** | §7.2a | P-126 |
| REQ-BE-123 | La cobertura se comprueba en tres puntos de coste creciente: escaleta, capítulo y cierre de Writing | §7.2a | P-42, P-43, P-44 |
| REQ-BE-124 | `juez_rubrica` y `revision_humana` usan el mismo fichero de rúbrica, que es lo que hace comparables los dos juicios | §7.2b | P-122 |
| REQ-BE-125 | Las guardas estructurales no emiten veredicto: hacen imposible el estado malo | §7.2d | P-28, P-29, P-30 |
| REQ-BE-126 | Las propiedades de G6 se afirman **consultando la traza real** por la API de Langfuse, no sobre un modelo | §7.2e | P-123 |
| REQ-BE-127 | Una incidencia es un defecto del contenido y tiene camino de vuelta; un error es una avería y detiene la invocación | §8 | P-128 |
| REQ-BE-128 | Un error de entorno nunca se traduce en un capítulo aprobado | §8 | P-48 |
| REQ-BE-129 | Las micro-sesiones del arquitecto corren **en serie**, afirmado por construcción | §9 | P-134 |
| REQ-BE-130 | Cada documento de `docs/` y de `specs/` deja acta de su grilling y de su revisión. *Clase **I**, gate G4* | §9 | P-135 |
| REQ-BE-131 | Los identificadores de este apartado no se repiten ni se reutilizan, y todo ítem citado existe en el plan | §10 | P-139 |

---

## 11. Lo que este documento deja fuera a propósito

- **La forma técnica exacta** —qué fichero, qué función, en qué orden se construye— va en [`plan.md`](plan.md).
- **El frontend**, que tiene su metodología propia en §16.3 de la arquitectura.
- **El contenido del proyecto Lean y de la especificación TLA+**: son artefactos de verificación con vida propia; aquí solo se fija cómo los invoca el backend y qué hace con su veredicto.
- **Los prompts de rol**, que viven en Langfuse como fuente de verdad y no en el repositorio.

---

## 12. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | §4.1: **la entrevista pasa por el gate de Intake**. Entran REQ-BE-133 y REQ-BE-134 | Se propaga la decisión de la arquitectura en la Fase 1. El entrevistador se llamaba una vez y sus preguntas no las veía nadie |
| 2026-09-24 | **Telegram solo avisa y los gates se deciden con `storymaker decidir`**: se retira `POST /webhook/telegram` con su secreto, §4.7 fija que el nodo abre el gate antes de `interrupt()` y no lo reabre al reanudar, `continuar` se niega ante un gate pendiente, y la CLI pasa a ocho comandos. REQ-BE-106, 107, 108, 114, 115 y 116 se reescriben | Decisión del Autor, propagada desde la arquitectura. Al probarla con gates apareció además que el nodo nunca abría el gate: no quedaba fila, no se avisaba y nada podía decidirse |
| 2026-09-24 | §4.5: el juez recibe la rúbrica, el PDF se imprime tras publicar con su fallo como aviso, y en batch el umbral del juez no detiene | Se propaga la decisión de la arquitectura en Fase 5, a raíz de la auditoría previa a la primera ejecución real |
| 2026-09-24 | §7.1 nº 21: `inventario_del_plan` lee también las filas `IMP-nn` del plan del frontend y, en la dirección inversa, recorre `frontend/src/**`; REQ-BE-113 nombra la **URL base** en `frontend_base_url`, que la tabla de configuración de §2 ya declaraba | La arquitectura pide cotejar «el plan contra el árbol y a la inversa» sin limitarlo a una mitad, y el validador solo miraba el backend: las rutas del plan del frontend no las comprobaba nadie. La URL base la exige §16.4 y el requisito solo nombraba el directorio |
| 2026-09-24 | §3.3 fija **el contrato de salida**: la función de invocación adjunta al prompt el JSON Schema del esquema del rol, que cuenta contra su techo. Entra **REQ-BE-132** | Se propaga la decisión nueva de §5 de la arquitectura. La primera ejecución real cayó en `Configure` porque el entrevistador validaba contra un `Brief` que nunca le habían enseñado |
| 2026-09-23 | Al cablear los nodos y recorrer el sistema entero por primera vez: el estado del grafo gana seis punteros —`premisa`, `texto_pegado`, `capitulo_version_id`, `huecos_pendientes`, `a_regenerar` y `a_invalidar`—; **los cuatro gates dejan de ser terminales** y resuelven por «aprobar» en modo batch; `Plan` **planifica una sola vez** y no rehace la escaleta al volver de `FillGap`; y la Fase 6 resuelve la petición del lector con búsqueda semántica más la forma opcional `campo=valor`, sin que ningún modelo intervenga | Los nodos estaban cableados pero no llamaban a las funciones que hacen el trabajo, y al conectarlos apareció lo que faltaba. Los punteros son eso, punteros: el estado sigue sin llevar contenido. Los gates sin arista de salida hacían que el modo batch —el único en el que los cinco briefs de evaluación pueden correr— terminara en el primer gate. Y replanificar en cada hueco costaba cinco llamadas de arquitecto para duplicar personajes y capítulos |
| 2026-09-23 | §7.1 gana el validador **`matrices_de_trazabilidad`** (22-b), que bloquea sobre la forma de las tres matrices y **el suelo de su inventario**, e informa del recuento de huecos | Las matrices afirmaban en verde y no las miraba nadie: se comprobaban a mano con `grep`, y un parche que se comió un separador dejó tres filas contándose sin poder leerse. Lo que sostiene una afirmación tiene que ser comprobable por la suite, no por quien la escribió |
| 2026-09-23 | Se propaga la reescritura de §11d —**TLA+ directo**, cinco invariantes de estado y las rutas de `formal/tla/`— y entran las cuatro cosas que el frontend necesitaba: el **bloque de paratexto** en el endpoint de versión, la **ficha de personajes versionada**, **FastAPI sirviendo `frontend_dist`** con su URL base en `Settings`, y la **interceptación** con la que `render_visual` ve la versión candidata. §9 recoge además las clases de P-134 y P-135 | Escribir la spec del frontend destapó que la superficie que el backend le ofrecía no daba para dibujar la portada ni para enlazar una ficha a su capítulo, y que el validador que sostiene G5 no tenía forma de ver lo que juzga. Y la contradicción de §11d hacía que este documento midiera contra cuatro invariantes donde hay cinco |
| 2026-09-23 | Versión inicial | Fijar el contrato del backend completo —módulos transversales, seis fases, API y CLI— y, sobre todo, separar las dos familias de validadores: los que comprueban que el código está bien escrito y los que comprueban que una novela está bien hecha |
| 2026-09-23 | Al implementar H1 y H2: §3.1 precisa qué protege cada *trigger* —contenido sí, estado no— y §3.3 declara que la guarda de presupuesto **estima** por lo alto en lugar de medir | Dos hechos del terreno. La inmutabilidad literal de la fila entera hacía imposible `ApproveChapter` y el cierre de `fase_run`. Y el Agent SDK no expone el tokenizador de Anthropic, así que prometer un recuento exacto habría sido falso: lo que sí es exacto es el tope de herramientas y el truncado, que son estructurales |
| 2026-09-23 | Tras la pasada de congruencia con el plan: §4.3 declara que el corpus llega al arquitecto **por búsqueda semántica** y no entero, y §7.2 recoge el **linter de auto-similitud** entre capítulos, diciendo expresamente que no es uno de los once validadores de §11a | Son los usos 3 y 4 de los embeddings de §16.2 de la arquitectura. Estaban en el plan y no en la spec, que es la manera de que el código acabe haciendo algo que su contrato no dice |
| 2026-09-23 | Tras el recorrido de trazabilidad contra la arquitectura: **Lean baja de la pasada determinista a la pasada del extractor** y gana su tercer punto de ejecución, el gate de Plotting (§3.7, §4.4, §7.2c); `arco_anclado` pasa a exigirse **por apariciones en ≥3 escenas** con el arco plano admitido y el homenajeado como única excepción (§7.2a) | Tres desviaciones de la arquitectura, que manda. Lean en la pasada determinista habría verificado una cronología que llega hasta N−1, porque las filas narrativas del capítulo N las escribe el extractor; el punto de Plotting, el más barato de los tres, faltaba entero; y «personaje principal» es justamente el concepto que la arquitectura descarta porque el modelo de datos no sabe responderlo |
| 2026-09-23 | Tras el grilling: los dos extractores quedan declarados como roles con techo (12.000 y 6.000) y §1 de la arquitectura sube a nueve; `render_visual` pasa a correr dentro de `PublishVersion` sobre la versión candidata antes del `commit`; `cobertura_anclada` y `arco_anclado` quedan bajo G4 y `cobertura_personalizacion` bajo G5 | Tres hilos que el grilling destapó y que el Autor resolvió: un presupuesto que sumaba siete techos de nueve agentes, un validador de render que se declaraba posterior a la publicación que debía impedir, y dos validadores del gate de Plotting sin puerta asignada |
| 2026-09-23 | §7.1 gana tres validadores de programación —`registro_de_validadores` (bloquea), `inventario_del_plan` y `anclas_de_procedencia` (informan)— y el nº 18 pasa a comparar también **aristas**; §3.6 declara que `REGISTRO` es el cableado del que se sirven el grafo y el hook | Nada comprobaba que el código implementara lo que estos documentos especifican: ni que un apartado declarado llegara a escribirse, ni que un validador siguiera bloqueando después de un refactor. Con el registro como cableado la comprobación es clase A, porque un validador ausente de él sencillamente no corre |
| 2026-09-23 | Entra **§10, los 131 requisitos** `REQ-BE-nn` derivados de los propios apartados de este documento, cada uno con el apartado del que nace —de donde hereda clase y gate— y los ítems de plan que lo realizan; §7.1 gana el validador **`requisitos_declarados`** (22-c) y los apartados finales se renumeran | Este documento se podía leer, pero no comprobar: un apartado afirma muchas cosas a la vez y se puede implementar a medias sin que se note. Las tablas de validadores quedan fuera a propósito, porque el nombre del validador ya es su identificador y duplicarlas añadiría cincuenta y siete filas sin añadir ninguna comprobación |
