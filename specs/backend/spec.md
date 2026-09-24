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
| Rutas | `directorio_proyectos` (por defecto `proyectos/`) | El directorio es el registro de novelas (§16.4 arq.): **una carpeta por novela**, `<nombre>/<nombre>.db`, con el cerrojo, los PDF y los capítulos exportados al lado |
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
2. **Se aplican las migraciones pendientes** y se comprueba que la versión de esquema del fichero es la que el código espera. Una columna **aditiva y que admite nulos**, añadida después de crear la tabla —hoy, `mundo_hecho.sin_respaldo`—, entra con `ALTER TABLE` en cada apertura si el fichero no la tiene, sin tocar sus filas y **sin subir la versión**, de modo que el código anterior siga abriendo el fichero.
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

Monta los siete bloques de §6 de la arquitectura en orden, con sus techos: encargo (800), canon relevante (2.500), continuidad (2.500), memoria (3.000), anclajes (1.500), reglas (1.200) y personalización (500). Total 12.000.

**El bloque 3 lleva lo que ya ha pasado.** Tras el estado de continuidad al cierre de N−1, que es fijo, van los eventos de `cronologia_evento` con `origen = 'narrativo'` de las versiones **aprobadas** de los capítulos 1 a N−2, como `Capitulo k: descripcion`, con la descripción recortada a 160 caracteres y del capítulo más reciente al más antiguo. Así el recorte, que va por la cola, suelta primero lo más lejano.

**El bloque 6 lleva reglas de escritura, qué hacer con cada firmeza y lo que la novela ya ha gastado.** Van fijas cuatro reglas: narrar en pretérito; entregar solo prosa, sin títulos ni encabezados; que ningún personaje, histórico incluido, sepa ni cuente lo que aún no ha ocurrido en la fecha narrativa de su escena, y no contradecir lo que el bloque 3 dice que ya pasó. Tras ellas va, también fijo, **el uso de cada firmeza**: `documentado` se cuenta como hecho, con sus fechas y cifras; `debatido`, sin tomar partido, mejor por boca de un personaje; `inferido`, como ambiente, sin cifras exactas y sin que la trama gire sobre ello; `desconocido` es espacio libre para la ficción mientras no contradiga lo documentado; `inventado`, dentro del grado de licencia, y lo que la cita no dice no se cuenta como hecho. Después, calculadas en Python sobre el texto de los capítulos aprobados 1 a N−1, dos listas: **las ocho palabras y las cuatro expresiones de dos palabras más frecuentes**, fuera de las palabras vacías y de los nombres del canon, con su recuento, y **la última frase de cada capítulo anterior**. Las dos se recortan antes que las reglas.

**Tres propiedades que el ensamblador debe cumplir siempre**, y que son las que se verifican con Hypothesis y con CrossHair:

1. El paquete **nunca excede** el techo total.
2. El recorte va **por la cola de la lista ya ordenada por relevancia**, y el bloque 3 —continuidad— es el último que se toca.
3. Los **anclajes explícitos de la escaleta entran siempre**, antes que cualquier vecino semántico.

**La recuperación la hace él, no el agente.** La consulta se deriva mecánicamente del texto de las escenas del capítulo N, se vectoriza con FastEmbed y se resuelve con KNN de `sqlite-vec` sobre los tres índices. Con las mismas entradas salen los mismos vecinos, siempre.

**El bloque 5 lleva la firmeza de cada hecho, no su estado declarado.** Cada anclaje y cada vecino va precedido de `[firmeza]`, calculada con `firmeza()` de §3.6 sobre el `estado`, el `respaldo` y el `origen` de la fila. Es lo que le dice al escritor cuánto puede apoyarse en el dato: `documentado`, `debatido`, `inferido`, `desconocido` o `inventado`. Si el veredicto fue parcial, detrás va `(no lo dice la cita: «…»)` con lo que el enunciado añade, **mientras ese añadido siga en el enunciado**: `anadido_vigente(enunciado, sin_respaldo)`, pura y de §3.6, lo comprueba normalizando los dos textos.

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

**La firmeza de un hecho también vive aquí**, como función pura de `puras.py`: `firmeza(estado, respaldo, origen) -> str`. Devuelve `inventado` si `origen = 'invencion_autorizada'`; si no, el mínimo, en el orden `documentado > debatido > inferido > desconocido`, entre lo que `estado` declara (`verificado` cuenta como `documentado`) y el techo que permite el respaldo: sin techo si es `respaldado`, `inferido` en cualquier otro caso. Es **total**: un estado que no reconoce cuenta como `desconocido`, de modo que ningún valor inesperado sube a nadie de categoría. Quien lee un hecho para enseñarlo a un modelo o al Autor la llama; nadie la guarda. Su dominio es finito —cuatro estados, cuatro respaldos, tres orígenes—, así que se comprueba **por enumeración exhaustiva de las cuarenta y ocho combinaciones**, que es una demostración y no una muestra. A su lado vive `anadido_vigente(enunciado, sin_respaldo) -> str | None`: devuelve el añadido del veredicto parcial si sigue en el enunciado —literal, o con todas sus **palabras significativas** presentes, porque el verificador a veces lo copia con otras palabras—, y `None` si no hay añadido o el Autor lo quitó al corregir. Son significativas las palabras normalizadas de más de tres letras y los números; si el añadido no tiene ninguna, cuentan todas.

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

**El evento ancla es un elemento más.** Si el `Brief` trae `evento_ancla`, se guarda en `intake_dato` como elemento obligatorio, junto a los del comprador, y desde ahí lo recorren la escaleta y las tres comprobaciones de cobertura.

**Los capítulos del brief cerrado mandan.** Cuando el entrevistador cierra el `Brief`, `Configure` escribe su `n_capitulos` en el estado del grafo, que hasta entonces llevaba el del lanzamiento. Es el número con el que el arquitecto planifica, y así la escaleta y el bucle de Writing cuentan los mismos capítulos.

**Contradicciones.** Las detecta un `@model_validator` de Pydantic, no un modelo: edad del homenajeado contra el período, fecha de nacimiento contra el `evento_ancla` si viene relleno, tono festivo contra un período de duelo, dato aportado que coincide con una palabra prohibida. El agente captura el `ValueError`, lo traduce a pregunta y obliga a resolverlo.

**Contrato de seguridad.** Una cadena del texto en bruto **no puede aparecer jamás en el prompt del escritor**, y hay una aserción que lo comprueba sobre cargas de inyección. La defensa es estructural: una inyección tiene que sobrevivir a convertirse en una fila tipada para hacer daño.

**La entrevista, a través del gate.** Las preguntas del entrevistador se guardan como incidencias de aviso del validador `pregunta_del_entrevistador`, sin capítulo, y el aviso del gate de Intake las enumera. El Autor contesta con `storymaker decidir <novela> rehacer --comentario "<respuestas>"`. La arista «rehacer» devuelve a `Configure`, que vuelve a entrevistar con la premisa y **los comentarios de todos los gates de Intake decididos como «rehacer»**, en orden. Sobre esa segunda pasada:
- las preguntas anteriores se retiran y solo quedan las nuevas;
- el texto pegado **no se vuelve a extraer**, porque la cuarentena ya lo tiene;
- un dato dictado que ya existe con el mismo tipo, valor y origen **no se vuelve a escribir**;
- `intake_brief` guarda una fila por pasada, y todo lector toma la última.

**La descripción del encargo es premisa, no cuarentena.** El encargo admite un campo `descripcion`: la novela contada con las palabras de quien la encarga, que es como la interfaz propone empezar. El lector del encargo la **antepone a la premisa en prosa**, de modo que el entrevistador la lee entera y pregunta solo por lo que no dice. No pasa por la cuarentena porque no es texto pegado de un tercero, sino lo que escribe el Autor en su propia pantalla, igual que los campos del encargo; lo que sí es texto de terceros sigue entrando por `texto_libre`.

**Errores.** Brief incompleto tras agotar las preguntas → el gate se abre igualmente con el informe de lo que falta; decide el Autor. Aprobar con preguntas pendientes sigue con el brief que haya.

### 4.2 `investigation/` — Fase 2

**Entrada.** Período y lugar del `Brief` y, en el modo exhaustivo, sus personajes históricos, su evento ancla y su rol de época. **Nunca sus campos personales** —nombre del homenajeado, fecha de nacimiento, elementos de personalización—: el investigador es el único rol con red. La regla Semgrep `pii-fuera-del-investigador` impide construir el prompt con ellos, y `pii_en_prompt_de_investigacion` mira cada prompt ya ensamblado —sesión única, dirigidas y micro-sesiones— antes de emitirlo; si encuentra uno, esa sesión no sale y queda un aviso.

**Paso 1 · una sesión, tres búsquedas.** El investigador reparte **3 `WebSearch` y 3 `WebFetch`** entre las seis dimensiones del período y las deja todas pobladas. El tope lo impone el arnés con los hooks de §3.3, no una instrucción del prompt: la cuarta llamada no se emite. Cada hecho se guarda con su enunciado, el estado epistémico que declara el investigador **sobre lo que dice su fuente** —`verificado` si la fuente lo afirma, `debatido` si recoge versiones o dudas, `inferido` si lo deduce él de lo que la fuente dice, `desconocido` si la fuente dice que no se sabe o no encontró nada—, sus fuentes, el `fase_run_id` que lo escribió y su **cita de 300 caracteres como mucho**. El prompt —de la sesión única, de las dirigidas y de la micro-sesión— da la **definición de los cuatro estados** del glosario, no solo sus nombres.

**Paso 1 en modo exhaustivo · ocho sesiones dirigidas.** Si el estado de la novela dice `investigacion = "exhaustiva"`, en lugar de la sesión única corren en serie, con el perfil `investigador_dirigido` —**1 `WebSearch` y 1 `WebFetch`** cada una, techo de 15.000 tokens—:

| # | Encargo | Qué recibe | Se omite si |
|---|---|---|---|
| 1–6 | Una dimensión del período | Período, lugar y la dimensión | — |
| 7 | Personajes históricos y evento ancla | Período, lugar, los personajes que deben aparecer y el evento ancla | El brief no trae ni personajes ni evento |
| 8 | El oficio del homenajeado | Período, lugar y `rol_epoca` | No hay `rol_epoca` |

Los hechos de las dos últimas llevan una de las seis dimensiones de siempre. Cada sesión deja una incidencia de severidad `aviso` y validador `investigacion_dirigida`, sin capítulo, con su encargo y sus hechos o el motivo por el que se saltó: es la línea que el informe del gate enseña. Una salida inválida tras los reintentos de esquema **salta esa sesión** y las demás siguen; `PresupuestoExcedido` y los errores de entorno suben. Los comentarios de «rehacer» del gate de Investigation se añaden a todas las sesiones, y también a la única en el modo estándar. El modo se fija al crear la novela —`storymaker nueva --investigacion estandar|exhaustiva`, la API o `Settings.investigacion`— y no cambia después.

**Paso 2 · el verificador.** Un agente distinto, **sin herramientas y sin red**, lee los pares enunciado–cita **por lotes de veinte** y responde una sola pregunta por hecho: ¿el fragmento dice lo que el hecho afirma? Cada veredicto lleva `respaldado` —si la cita sostiene el **dato central**, que es lo que el hecho dice que existió u ocurrió; una fecha, un lugar o un detalle que la cita no trae no lo tumba, es un añadido— y `sin_respaldo`, con lo que el enunciado añade y la cita no dice, vacío si no añade nada. Un veredicto respaldado con añadido es el **parcial**: se guarda `respaldo = 'respaldado'` y el añadido en `mundo_hecho.sin_respaldo`, y la firmeza no cambia. El verificador **escribe solo `respaldo` y `sin_respaldo`**: `estado` se queda como lo declaró el investigador, y ningún camino del arnés lo reescribe después. Un `no_respaldado` **limita la firmeza del hecho a `inferido` y lo marca; no lo borra y no detiene la fase.** **Las lagunas no pasan por él**: un hecho `desconocido` nace con `respaldo = 'no_aplica'`, y ni los lotes ni `verificar_hecho` miran lo que no esté `pendiente`.

**Salida.** `mundo_hecho`, `mundo_fuente`, `mundo_hecho_fuente`, `mundo_entidad`, con `respaldo` escrito y `estado` intacto.

**Rehacer no contamina.** Los hechos de la ejecución anterior no se borran ni se mezclan: solo cuentan los del `fase_run` vigente, y los antiguos quedan como historia consultable.

**Una llamada denegada dice qué hacer.** El motivo de la denegación del hook de cuota le pide al rol que no lo intente de nuevo y entregue ya su respuesta en JSON. La sesión única tiene veinte turnos.

**Errores.** Una sesión única que termina sin una respuesta válida tras sus reintentos de esquema **no detiene la fase**: deja una incidencia `aviso` de validador `investigacion_dirigida` —«sesion unica: sin resultado»— y la fase sigue con el corpus vacío hacia el verificador y el gate. Cero hechos en una dimensión no es un error bloqueante: es una fila del informe del gate, con el recuento por dimensión delante del Autor, que puede rehacer con comentario dirigido a lo que falte.

### 4.3 `plotting/` — Fase 3

**Entrada.** Brief validado y corpus.

**Qué hace.** El arquitecto **inventa la Premisa y el Tema**, construye el canon —personajes, relaciones, arcos con sus hitos, escenarios, voz, glosario— y la escaleta jerárquica de capítulos → escenas → beats con sus anclajes. Copia además `grado_licencia`, `arcaismo` y `contenido_admisible` a `canon_obra.estilo_json`, que es como esos diales llegan al bloque 6 del paquete.

**El arquitecto no recibe el corpus entero.** Los hechos le llegan por la misma búsqueda semántica de §3.5, con la consulta derivada de lo que está planificando. Es el tercero de los cuatro usos que §16.2 de la arquitectura da a los embeddings, y es lo que evita volcarle en la ventana un corpus de varios cientos de hechos.

**El hueco.** El arquitecto declara cada hueco con **su escena, su dimensión y la afirmación que usaría si no se encuentra**, y el hueco queda en `plan_hueco`; el estado del grafo lleva solo su identificador. Para cada uno, `FillGap` dispara **una única micro-llamada** al investigador, con una sola `WebSearch`. La micro-sesión recibe el mismo bloque de instrucciones por hecho que las demás sesiones del investigador, **con la cita incluida**, porque sin ella el verificador no tendría nada que leer. Si lo encuentra, entra como `origen = 'micro_arquitecto'` y **pasa en el acto por el verificador**: una llamada con ese único par enunciado–cita, sin herramientas ni red. Si la salida del verificador no valida tras sus reintentos, el hecho se queda con `respaldo = 'pendiente'`, su firmeza no pasa de `inferido` y la escaleta sigue; `PresupuestoExcedido` y los errores de entorno suben, como en Investigation. Si no lo encuentra, el veredicto `no_encontrado` **autoriza la invención**: la afirmación propuesta entra como fila con `estado = 'inferido'`, `origen = 'invencion_autorizada'`, sin fuente y con `respaldo = 'no_aplica'`: su firmeza es `inventado`. **En los dos casos el hecho se ancla a la escena del hueco.** **Los huecos se topan en cinco por ejecución; la invención no se topa, se cuenta** y aparece por dimensión en el informe del gate, que dice también cuántos hechos de la micro-sesión quedaron sin respaldo.

**El sello.** Al aprobarse la escaleta se calcula el hash sobre el contenido ordenado de las tablas `mundo_*` vigentes —con el `respaldo` de cada hecho, del que depende su firmeza— y se escribe `mundo_sello`. **A partir de ahí el corpus es de solo lectura**: durante Writing solo se puede anclar a lo existente o declarar una Licencia.

**La firmeza en la escaleta.** El prompt del arquitecto dice qué hacer con cada firmeza: el evento ancla y los giros, sobre `documentado`; `debatido`, si la duda forma parte de la escena; `inferido`, como ambiente; `desconocido`, hueco libre para inventar; `inventado`, ya es licencia. El informe del gate de Plotting **avisa de cada escena cuyos anclajes a hechos son todos `inferido` o `desconocido`**, con su capítulo y su orden; una escena sin anclajes a hechos no cuenta. Es aviso, no bloqueo.

**La forma de la escaleta.** El prompt del arquitecto enuncia el número de capítulos del brief, **de 2 a 4 escenas por capítulo** y la extensión por capítulo (arq. §19), junto a los elementos del encargo que tiene que anclar. El gate de Plotting abre una **incidencia de aviso** por cada capítulo fuera del rango de escenas. No bloquea, por el criterio de producto, pero el Autor lo ve en el informe antes de aprobar, y puede rehacer.

**La revisión y el rehacer.** Al terminar `Plan` corre la revisión de la escaleta —cobertura, arcos, rango de escenas, anclajes sin resolver y cronología, esta en Python cuando no hay `lake`—, se guarda como incidencias sin capítulo y **no cierra el gate**; un elemento obligatorio sin anclar se ancla solo a la escena más parecida. Tras «rehacer» o «editar» en el gate, `Plan` sustituye la trama y el arquitecto recibe la anterior, los comentarios y los avisos. El detalle está en [`specs/trama-rehacible/spec.md`](../trama-rehacible/spec.md).

**Errores.** Tope de huecos alcanzado no bloquea: queda la invención autorizada, que no cuesta nada y produce exactamente la misma fila. Un capítulo fuera del rango de escenas es aviso en el gate. Borrar la trama con un capítulo escrito aborta por clave foránea.

### 4.4 `writing/` — Fase 4

El bucle por capítulo, que es la unidad de generación, validación, checkpoint y regeneración.

1. El ensamblador monta el paquete del capítulo N.
2. El escritor **redacta el capítulo entero de una vez**. La escena es unidad de planificación y de traza, no de redacción: coser escenas generadas por separado es la forma más fiable de producir prosa mecánica. Los encabezados markdown que traiga el texto —el título del capítulo, los de escena—, de cualquier nivel, se quitan al guardarlo: título y escenas viven en la escaleta, y dejarlos los duplicaba en la lectura y los contaba como palabras.
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

**El juez recibe la rúbrica** —las siete preguntas de `rubrica.yaml`, el mismo fichero de la revisión humana— antepuesta a la novela. **Antes de puntuar enumera las contradicciones**: lo que un capítulo afirma y otro desmiente, y lo que un personaje sabe o cuenta antes de que ocurra en la fecha narrativa. `SalidaJuez.contradicciones` las recoge, y la nota de continuidad **se topa en Python** a `10 − 2·n`, con mínimo 1; el juez las cuenta, pero no decide cuánto pesan. Las contradicciones se guardan en el detalle del *score*. **El PDF** se imprime **desde la ruta de impresión del frontend** (arq. §16.1), junto al fichero de la novela como `<novela>.v<n>.pdf`, y si falla queda como aviso: la versión ya está publicada y validada. Se imprime **cuando la invocación que publicó ya ha confirmado**, al salir del grafo y antes de avisar de que ha terminado, porque dentro del paso de `publish` la versión todavía no es visible para otra conexión. No hace falta un servidor levantado: Playwright abre `/novelas/<n>/v/<k>/imprimir` y el propio proceso le responde, con los estáticos de `frontend_dist` y la API con la aplicación de FastAPI en memoria. Se imprime toda versión que aún no tenga su PDF, de modo que una impresión fallida se repite en la siguiente invocación que termine. Sin `dist/` se cae al HTML mínimo de `render.py`, con un aviso.

**Errores.** Lean falla → **la versión no se publica, sin anulación posible**. Umbral del juez no superado → vuelta al gate de Writing **con gates**; **en modo batch se registra la nota y se publica**, porque no hay nadie que decida qué rehacer.

### 4.6 `regeneration/` — Fase 6

**Entrada.** La petición del lector en lenguaje natural, o una edición humana directa del corpus, del canon o de la escaleta. **Las dos entran por la misma puerta y disparan la misma maquinaria.**

1. La petición se resuelve por búsqueda semántica contra canon y corpus; los candidatos se muestran y **el Autor confirma en el gate**. Sin esto, la fase exigiría que el lector conociera los identificadores internos. Confirmar es elegir: la aprobación lleva en su comentario la fila elegida y su valor nuevo, `<objeto>:<fila_id> <campo>=<valor>` —por ejemplo `personaje:1 nombre=Manuel`—, y `RequestChange` aplica exactamente eso **sin volver a buscar**. Una aprobación sin fila ni valor no cambia nada y la fase pasa de largo: ningún modelo interpreta la petición, así que escribir la frase del lector como valor sería escribir una instrucción en el canon. Se mantiene la forma `campo=valor` sin fila, que resuelve la fila por búsqueda sobre el valor.
2. **Se modifica la fila del hecho, no el texto.** El canon manda sobre el texto: un buscar-y-reemplazar sobre la prosa deja mintiendo a la biblia.
3. `uso_hecho` dice qué capítulos usan un hecho; **esos se regeneran**. Para un personaje, los que lo usan son los que lo nombran según `continuidad` de sus versiones aprobadas, los que la escaleta le asigna en `plan_escena_personaje` y los de sus hitos en `uso_hito`.
4. Los posteriores pasan a `Invalidado` y se les corren **solo los validadores de coste cero** —Python y Lean—. Si ninguno falla, se quedan como están y no cuestan un token.
5. Se publica un manifiesto nuevo que **reutiliza los capítulos no tocados**; la versión anterior sobrevive entera.
6. El diff sale de comparar dos manifiestos con un `JOIN`.

**Errores.** Una regeneración que toque un hecho usado en nueve capítulos es correcta pero cara: **el gate de Regeneration enseña el recuento de afectados antes de pagarlo** y permite abortar.

### 4.7 `gates/` — los cinco gates y la notificación

**Contrato.** El nodo **abre el gate** —fila `pendiente` en `gate`— y avisa; después llama a `interrupt()`, el checkpointer persiste y la invocación termina. **La decisión se toma en el PC del Autor** con `storymaker decidir`, que la escribe sobre el gate pendiente y reanuda con `Command(resume=...)` en el mismo proceso. Como LangGraph vuelve a ejecutar el nodo al reanudar, la invocación lleva una **marca de reanudación de un solo uso** que impide abrir el gate otra vez y volver a avisar. `continuar` **se niega** a reanudar una novela con un gate pendiente: sin decisión, lo aprobaría en silencio.

Cuatro decisiones: **aprobar**, **rehacer con comentario** —el texto libre se inyecta como bloque extra en el prompt y cuenta contra el límite de reintentos—, **editar** y **abortar**.

**Notificación tras la interfaz `Notifier`, y solo para avisar**, con Telegram como única implementación hoy. El aviso de un gate lleva el título, un resumen de lo que hay que revisar y termina con **«Decide en el PC»**, en texto plano, **sin comandos y sin botones**. Si Telegram rechaza el envío o no hay red, se avisa en la salida del proceso y el gate bloquea igual. WhatsApp exige Meta Business, número verificado y plantillas aprobadas, y queda como adaptador futuro.

**Sin respuesta**: el *timeout* **aparca** la ejecución con estado propio. **No hay auto-aprobación**, porque eso convertiría un gate de calidad en un temporizador.

**`gates_enabled = false`** los desactiva enteros, y queda registrado en el manifiesto. Es imprescindible: los cinco briefs de evaluación tienen que correr desatendidos.

---

## 5. La API de FastAPI

Tres superficies: **lectura**, **seguimiento** y **operación**. Las dos primeras solo leen el fichero de la novela. La tercera opera la novela entera desde la interfaz (arq. §16.5), y **lo que ejecuta el grafo no lo ejecuta la API: lanza la CLI como proceso aparte** y responde en el acto. Todas las rutas van bajo el prefijo `/api` —`GET /api/novelas`, y así las demás—, salvo la aplicación.

### 5.1 Lectura

| Método y ruta | Contrato | Errores |
|---|---|---|
| `GET /novelas/{id}` | Ficha de la novela: fase, gate abierto si lo hay, y el **historial** de versiones con fecha y media de la rúbrica del juez | `404` |
| `GET /novelas/{id}/versiones/{n}` | Manifiesto de la versión; sus capítulos en orden, cada uno con **número y título**; la versión **anterior** si la hay; y el **bloque de paratexto** —título, homenajeado tal como lo fija el canon, ocasión y Licencias declaradas— | `404` |
| `GET /novelas/{id}/versiones/{n}/capitulos/{k}` | Texto del capítulo tal como esa versión lo fija, con su título y el total de capítulos del manifiesto | `404` |
| `GET /novelas/{id}/versiones/{n}/personajes` | **Personajes y escenarios** por separado, con los capítulos **de esa versión** en que aparecen; cada personaje con sus rasgos, si es el homenajeado y su relación con él; cada escenario con su lugar, su nombre de época y **un nombre corto** | `404` |
| `GET /novelas/{id}/versiones/{a}/diff/{b}` | Qué capítulos cambian entre dos manifiestos: un `JOIN`, no un diff de texto | `404` |
| `GET /novelas/{id}/versiones/{n}/pdf` | **El PDF de la versión**, el que `publish` imprimió junto al fichero de la novela como `<nombre>.v<n>.pdf`, servido para descargar | `404` si la versión no existe o su PDF no se generó |
| `POST /novelas/{id}/cambios` | Petición de cambio del lector con su texto, su **fragmento**, el capítulo y la versión. El fragmento entra en la búsqueda semántica. **No toca nada**: abre la Fase 6, que se detiene en su gate, y **deja en `audit_log` la petición con sus candidatos**, para que la pantalla del gate los enseñe sin repetir la búsqueda | `409` si está ocupada; `422` si viene sin texto |

**La ficha de personajes cuelga de una versión y no de la novela**: «los capítulos en los que aparece» solo tiene respuesta dentro de un manifiesto.

**Cada escenario lleva un nombre corto.** Es el del lugar del corpus si el escenario está enlazado a uno y, si no, el arranque de su descripción: hasta la primera coma, punto o cláusula de detalle —«con…», «donde…»—, y como mucho seis palabras. El arquitecto solo escribe una descripción, y sin esto la pantalla titulaba cada lugar con un párrafo. La regla vive en un solo sitio de la API, de modo que la ficha, la escaleta y el documento de impresión nombran igual cada escenario.

### 5.2 Seguimiento

| Método y ruta | Contrato | Errores |
|---|---|---|
| `GET /novelas` | Una fila por carpeta de `proyectos/` con su `<nombre>.db`: título, homenajeado, fase actual, **estado de la novela**, gate pendiente con su fase, capítulos aprobados y total, coste acumulado y versiones publicadas | — |
| `GET /novelas/{id}/panel` | Todo lo que el panel enseña: el estado; **las seis fases** con su estado, sus ejecuciones, tokens, coste, inicio y fin, y si dejaron salida; el gate pendiente; los capítulos con su estado e intentos; la **actividad** reciente; el consumo total; si el proceso vive; y los registros de proceso disponibles | `404` |
| `GET /novelas/{id}/gate` | El gate pendiente: su fase, desde cuándo, **los recuentos del aviso**, las preguntas del entrevistador en Intake, la petición y los candidatos en Regeneración —cada candidato con su objeto, su fila, el campo que tocaría por defecto y el valor que ese campo tiene hoy, que es lo que la pantalla necesita para componer la elección de §4.6—, y **las filas editables** de hechos, personajes, escenarios y glosario, con los hechos marcados como no editables si el corpus está sellado. En Intake, además, **la conversación**: la descripción del encargo, las respuestas de cada ronda anterior —los comentarios de los gates de Intake decididos como «rehacer»— y el brief si el entrevistador ya lo cerró | `404` si no hay gate pendiente |
| `GET /novelas/{id}/fases/{fase}` | La salida de una fase y sus ejecuciones con las decisiones de sus gates. Encargo: brief, datos y cuarentena. Investigación: hechos con dimensión, estado, respaldo, cita y fuentes, entidades y sello. Trama: obra, personajes con arcos e hitos, relaciones, escenarios, Licencias, glosario y escaleta con anclajes. Escritura: capítulos con sus intentos y las incidencias de cada uno. Publicación: versiones con la rúbrica por criterio y el manifiesto. Regeneración: peticiones y ediciones humanas | `404` |
| `GET /novelas/{id}/intentos/{capitulo_version}` | El texto de un intento de capítulo, con sus incidencias | `404` |
| `GET /novelas/{id}/registros/{nombre}` | El final del registro de un proceso lanzado desde la interfaz | `404` |
| `GET /ejemplos` | Los briefs de `ejemplos/`, ya leídos, para partir de uno en el encargo | — |

**El estado de una novela lo calcula el backend, con esta precedencia:**

| Estado | Condición |
|---|---|
| `en_marcha` | El cerrojo existe y el proceso cuyo PID guarda sigue vivo |
| `detenida` | El cerrojo existe y su proceso ya no vive |
| `arrancando` | No hay cerrojo, pero hay un registro de proceso de hace menos de veinte segundos |
| `esperando_autor` | Hay un gate `pendiente` |
| `aparcada` | El último gate está `aparcado` |
| `fallida` | La última ejecución de fase terminó `fallida` |
| `terminada` | Hay versión publicada y ninguna ejecución de fase abierta |
| `en_pausa` | Ninguna de las anteriores |

**Una novela recién encargada existe antes que su fichero.** `POST /novelas` crea la carpeta con el encargo y el registro, y `storymaker nueva` crea el `.db` un momento después. Una carpeta con `encargo.json` y sin `.db` aparece en el listado y en el panel: `arrancando` mientras su registro tenga menos de veinte segundos, y `fallida` después, con el registro a la vista para ver por qué no arrancó. Volver a encargar con ese nombre se admite, porque no hay novela que pisar.

**Cada fase tiene estado aunque no tenga filas.** Sale de su última fila de `fase_run` y, si no tiene ninguna, de si dejó salida: hay brief, hay hechos, hay escaleta, hay capítulos o hay versión. Una fase sin filas y con salida es `completada`, marcada como deducida. Es lo que hace legibles las novelas empezadas antes de que cada fase abriera su fila.

**La actividad está interpretada**: las ejecuciones de fase que se abren y se cierran, los intentos de capítulo con su resultado, las decisiones de gate con su comentario, las ediciones humanas y las acciones lanzadas desde la interfaz, cada una con su momento y una frase. No es el registro del proceso.

### 5.3 Operación

| Método y ruta | Contrato | Errores |
|---|---|---|
| `POST /encargos/validar` | Valida un brief con el mismo modelo que `storymaker nueva` y devuelve los errores por campo | — |
| `POST /novelas` | Con el nombre, el brief, si va en batch y el **modo de investigación** —`estandar` o `exhaustiva`—: escribe el brief como `encargo.json` en la carpeta de la novela y **lanza `storymaker nueva`**, con `--investigacion exhaustiva` cuando se pide | `409` si ya existe su `.db`; `422` si el brief no valida |
| `POST /novelas/{id}/continuar` | **Lanza `storymaker continuar`** | `409` si está ocupada; `422` si hay un gate pendiente |
| `POST /novelas/{id}/decisiones` | Con la decisión —`aprobar`, `rehacer` o `abortar`— y el comentario: **lanza `storymaker decidir`** | `409` si está ocupada; `422` si no hay gate pendiente, si la decisión es `editar` o si es `abortar` fuera de Intake |
| `POST /novelas/{id}/reintentar` | **Lanza `storymaker reintentar`**, que decide él mismo si procede | `409` si está ocupada |
| `POST /novelas/{id}/desbloquear` | Rompe el cerrojo **solo si su proceso ha muerto** | `409` si el proceso vive; `422` si no hay cerrojo |
| `POST /novelas/{id}/ediciones` | Edición humana directa de una fila —hecho, personaje, escenario o glosario— con su campo, su valor nuevo y su motivo, **tomando el cerrojo durante la escritura**, con la maquinaria de `regeneration/`: la fila cambia, se reindexa y queda en `edicion_humana` y en `audit_log` | `409` si está ocupada; `422` si el campo no es editable o el corpus está sellado |

**Lanzar es desacoplar.** El proceso se crea en su propio grupo, fuera del servidor y **con una consola oculta que heredan los procesos que él abra** —el Agent SDK, Lean, Playwright—, de modo que operar desde la interfaz no abre ninguna ventana, con el mismo intérprete y el mismo directorio de proyectos, y su salida va a `proyectos/<nombre>/registro/<momento>-<comando>.log`. La respuesta es un `202` con el nombre del registro, y la acción queda en `audit_log` con el actor `autor`. **El servidor no guarda ningún proceso en memoria**: reiniciarlo no mata nada, y el estado de §5.2 se recalcula del fichero en cada consulta.

**Las comprobaciones previas no sustituyen al comando.** La API rechaza lo que el comando rechazaría para que el Autor lo vea en la pantalla, pero si dos acciones se cruzan, la que llega segunda choca con el cerrojo en su proceso y lo dice en su registro. No se pierde nada, porque la decisión ya está escrita.

**Las acciones solo se aceptan desde la propia máquina y como JSON.** Cada ruta de operación rechaza con `403` a un cliente que no sea `127.0.0.1` o `::1`, y con `415` un cuerpo que no sea `application/json`. La API no concede CORS, y el servidor se arranca escuchando en `127.0.0.1`. Es la mitigación de U-17.

### 5.4 La aplicación

`GET /` y el resto de rutas de la aplicación **sirven el frontend construido** desde `frontend/dist`, de modo que lectura, PDF y `render_visual` compartan origen (arq. §16.4). El *fallback* va en el manejador de `404` y solo para `GET`: un `POST` a una dirección inexistente sigue siendo un `404`, y nada bajo `/api` cae en la aplicación.

**Cada respuesta declara su modelo Pydantic**, porque el frontend deriva sus tipos de transporte del OpenAPI. Las pruebas de API cubren las rutas de escritura: una petición malformada no abre la Fase 6 ni lanza ningún proceso.

*Clase: **A/T** (contrato OpenAPI y pruebas de API). Gate: G1.*

---

## 6. La CLI de Typer

| Comando | Qué hace |
|---|---|
| `storymaker nueva <brief.json>` | Crea la carpeta y el fichero de la novela, `proyectos/<nombre>/<nombre>.db`, y arranca la invocación |
| `storymaker continuar <novela>` | Reanuda desde el último checkpoint tras un fallo. **Se niega** si hay un gate pendiente |
| `storymaker decidir <novela> <aprobar\|rehacer\|editar\|abortar> [--comentario]` | **La única entrada de una decisión de gate**, también cuando decide la interfaz, que lanza este mismo comando. La escribe sobre el gate pendiente y reanuda en el mismo proceso; sin gate pendiente, con una decisión desconocida o con `abortar` fuera del gate de Intake, se rechaza sin tocar nada |
| `storymaker estado <novela>` | Fase, gate abierto, capítulos aprobados, consumo acumulado |
| `storymaker ramificar <novela> <destino>` | **Copia el fichero** y escribe la fila de `procedencia` |
| `storymaker cambiar <novela> "<peticion>"` | Entra en la Fase 6 por la puerta del Autor |
| `storymaker desbloquear <novela>` | Rompe un cerrojo huérfano dejado por un proceso muerto |
| `storymaker reintentar <novela>` | Reabre el capítulo que agotó sus reintentos: escribe en el checkpoint un capítulo recién empezado, como salida de `SealCorpus`, y reanuda. **Se niega** si la novela no terminó en `Fail`, si el corpus no está sellado o si hay un gate pendiente |
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
| `nombres_exactos` | Homenajeado y personajes escritos exactamente como en el canon; la mayúscula inicial de principio de frase no cuenta como otra grafía | Post `WriteChapter` | A | G3 | Sí |
| `longitud_capitulo` | Palabras dentro del rango del brief | Post `WriteChapter` | A | G3 | Sí |
| `guardrail_prohibidas` | Términos prohibidos en tres niveles, **normalizando antes de comparar**; un término de una palabra salta también en sus derivadas, por su raíz de al menos cuatro letras | Post `WriteChapter` | A/T | G3 | Sí |
| `anacronismo_fechado` | Ningún objeto, término o concepto con `fecha_inicio` posterior a la fecha narrativa | Post `WriteChapter` | A | G3 | Sí |
| `anclaje_valido` | Todo anclaje apunta a un hecho del corpus sellado o a una Licencia declarada | Post `WriteChapter` | A | G3 | Sí |
| `cobertura_anclada` | Cada elemento obligatorio del brief está anclado a ≥1 escena de la escaleta | Gate de Plotting | A | G4 | Sí |
| `arco_anclado` | Todo personaje presente en **≥3 escenas** de `plan_escena_personaje` tiene fila en `canon_arco`; si su arco es positivo o negativo, **≥2 hitos** anclados a escenas de capítulos estrictamente crecientes. **El arco plano cuenta**: declarar que un personaje no se transforma es la decisión que el validador reclama. El homenajeado es la única excepción — no puede tener arco plano y su último hito cae en el tercio final | Gate de Plotting | A | G4 | Sí |
| `cobertura_capitulo` | Lo que la escaleta encomendó a este capítulo aparece en él. Abre incidencia de severidad `aviso` que **nombra cada elemento por su texto** | Post `Extract` | A | G3 | No |
| `cobertura_personalizacion` | Cada elemento obligatorio aparece en ≥1 capítulo | Gate de Writing | A | G5 | Sí |
| `render_visual` | Índice, ficha de personajes y portada renderizan bien (Playwright MCP) | Dentro de `PublishVersion`, sobre la versión candidata, **antes del `commit`** | D | G5 | Sí |

**El linter de auto-similitud no es uno de los once.** El cuarto uso que §16.2 de la arquitectura da a los embeddings —detectar repeticiones y auto-similitud entre capítulos, como linter de prosa y de originalidad— se recoge aquí por lo que es: el vector del capítulo recién escrito se compara con los de los anteriores y se abre incidencia de severidad `aviso` cuando la repetición pasa del umbral declarado. No bloquea, no gobierna ninguna arista y no entra en la tabla de arriba, porque la lista de §11a es cerrada y esto no es una puerta: es una señal para el informe del gate de Writing.

**La cobertura se comprueba tres veces y cada una cuesta menos que la siguiente.** `cobertura_anclada` convierte un fallo de diez capítulos escritos y pagados en un fallo de escaleta; `cobertura_capitulo` avisa al escribir cada capítulo, y el aviso viaja al encargo del siguiente, que puede recoger el elemento; `cobertura_personalizacion` es la que bloquea, antes de publicar, porque anclar no es escribir y escribir el capítulo N no garantiza que ningún otro se quedara sin su parte.

#### b) Semánticos — los juzga un modelo

| Validador | Comprueba | Punto | Clase | Gate | Bloquea |
|---|---|---|---|---|---|
| `respaldo_fuente` | Que la cita guardada sostenga el enunciado del hecho | Cierre de Investigation; en `FillGap`, cada hecho de la micro-sesión | I | G4 | **No**: limita la firmeza a `inferido` |
| `ejecucion_escaleta` | Que los beats planificados para este capítulo hayan ocurrido | Post `Extract` | I | G4 | **No**: aviso |
| `arco_ejecutado` | Que los hitos de arco anclados a este capítulo hayan ocurrido | Post `Extract` | I | G4 | **No**: aviso |
| `juez_rubrica` | Siete criterios 1-10 con justificación, y la lista de contradicciones con la que se topa la continuidad | `Judge` | T/I | G5 | Sí, por umbral |
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
| Hecho sin respaldo en su cita | Marca | Su firmeza no pasa de `inferido`; destacado en el informe del gate |
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
| REQ-BE-14 | En `mundo_hecho` la inmutabilidad se condiciona a la existencia del sello: el verificador puede anotar el respaldo antes, nadie puede escribir después | §3.1 | P-17, P-79 |
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
| REQ-BE-204 | `firmeza(estado, respaldo, origen)` es pura y total: `inventado` si es invención; si no, el mínimo entre lo declarado y `inferido` cuando el respaldo no es `respaldado` | §3.6 | P-72 |
| REQ-BE-205 | El bloque 5 del paquete y el contexto del arquitecto llevan cada hecho con su firmeza, no con su estado declarado | §3.4 | P-35, P-125 |
| REQ-BE-209 | El bloque 5 y el contexto del arquitecto añaden «no lo dice la cita» con el añadido del parcial solo mientras siga en el enunciado | §3.4 | P-35, P-125 |
| REQ-BE-210 | El bloque 6 lleva, entre sus reglas fijas, qué hacer con cada firmeza | §3.4 | P-151 |
| REQ-BE-211 | Abrir una novela sin `mundo_hecho.sin_respaldo` la añade sin tocar sus filas y sin subir la versión del esquema | §2.3 | P-18 |

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
| REQ-BE-180 | El encargo admite `descripcion`, que el lector antepone a la premisa en prosa y no pasa por la cuarentena | §4.1 | P-180 |
| REQ-BE-61 | El prompt del investigador se construye solo con período y lugar; los campos personales del `Brief` no salen a la red, y lo imponen una regla Semgrep y una aserción | §4.2 | P-74, P-06 |
| REQ-BE-62 | El investigador dispone de **3 `WebSearch` y 3 `WebFetch` en una sesión**, y el tope lo impone el arnés con sus hooks, no una instrucción del prompt | §4.2 | P-69, P-29 |
| REQ-BE-63 | Cada hecho se guarda con su enunciado, su estado epistémico, sus fuentes, el `fase_run_id` que lo escribió y una cita de 300 caracteres como mucho | §4.2 | P-70 |
| REQ-BE-64 | El verificador es un agente distinto, **sin herramientas y sin red**, que lee los pares enunciado–cita por lotes de veinte | §4.2 | P-72 |
| REQ-BE-65 | Un veredicto `no_respaldado` **limita la firmeza del hecho a `inferido` y lo marca**: no lo borra, no reescribe su estado y no detiene la fase | §4.2 | P-72 |
| REQ-BE-199 | El verificador escribe solo `respaldo`; ningún camino del arnés reescribe `estado` después de crear la fila | §4.2 | P-72 |
| REQ-BE-200 | El prompt del investigador define los cuatro estados epistémicos **respecto a lo que dice su fuente**, en la sesión única, en las dirigidas y en la micro-sesión | §4.2 | P-69, P-153 |
| REQ-BE-207 | Un hecho `desconocido` nace con `respaldo = 'no_aplica'` y no pasa por el verificador, tampoco en la micro-sesión | §4.2 | P-70, P-72 |
| REQ-BE-208 | El verificador devuelve por hecho si la cita sostiene el dato central y qué añade el enunciado; el parcial se guarda como `respaldado` con el añadido en `sin_respaldo` | §4.2 | P-72 |
| REQ-BE-214 | El prompt del verificador define el dato central como lo que el hecho dice que existió u ocurrió, y trata la fecha o el lugar que la cita no trae como añadido | §4.2 | P-72 |
| REQ-BE-215 | `anadido_vigente` reconoce el añadido por sus palabras significativas, no solo por la copia literal | §3.6 | P-35, P-125 |
| REQ-BE-206 | El prompt de la micro-sesión pide la cita textual del hecho que encuentre | §4.3 | P-77 |
| REQ-BE-66 | Rehacer no contamina: solo cuentan los hechos del `fase_run` vigente, y los anteriores quedan como historia consultable | §4.2 | P-71 |
| REQ-BE-67 | Cero hechos en una dimensión no bloquea: es una fila del informe del gate, con el recuento por dimensión delante del Autor | §4.2 | P-73 |
| REQ-BE-68 | El arquitecto inventa la Premisa y el Tema, y construye el canon completo y la escaleta jerárquica con sus anclajes | §4.3 | P-75 |
| REQ-BE-69 | `grado_licencia`, `arcaismo` y `contenido_admisible` se copian a `canon_obra.estilo_json`, que es como llegan al bloque de reglas del paquete | §4.3 | P-76 |
| REQ-BE-70 | El arquitecto **no recibe el corpus entero**: los hechos le llegan por búsqueda semántica con la consulta derivada de lo que planifica | §4.3 | P-125 |
| REQ-BE-71 | Cada hueco dispara **una única micro-llamada** al investigador con una sola `WebSearch`, con un tope de cinco huecos por ejecución | §4.3 | P-77 |
| REQ-BE-201 | Cada hecho que encuentra la micro-sesión pasa por el verificador en `FillGap`; si su salida no valida, se queda `pendiente` y la escaleta sigue | §4.3 | P-77 |
| REQ-BE-202 | El informe del gate de Plotting cuenta los hechos de la micro-sesión que quedaron sin respaldo | §4.3 | P-78 |
| REQ-BE-203 | El hash del sello incluye el `respaldo` y el `sin_respaldo` de cada hecho | §4.3 | P-79 |
| REQ-BE-212 | El prompt del arquitecto dice qué hacer con cada firmeza | §4.3 | P-75 |
| REQ-BE-213 | El informe de Plotting avisa de cada escena cuyos anclajes a hechos son todos `inferido` o `desconocido` | §4.3 | P-78 |
| REQ-BE-72 | Un veredicto `no_encontrado` **autoriza la invención**, que entra como fila `inferido` con `origen = 'invencion_autorizada'`, sin fuente y con `respaldo = 'no_aplica'` | §4.3 | P-77 |
| REQ-BE-73 | La invención **no se topa, se cuenta**, y aparece por dimensión en el informe del gate | §4.3 | P-78 |
| REQ-BE-74 | Al aprobarse la escaleta se calcula el hash sobre el contenido ordenado de las tablas `mundo_*` vigentes y el corpus pasa a ser de solo lectura | §4.3 | P-79 |
| REQ-BE-217 | Cada hueco lleva escena, dimensión y afirmación propuesta, y el hecho que lo cubre se ancla a su escena | §4.3 | P-77 |
| REQ-BE-218 | Tras «rehacer» o «editar» en el gate de Plotting, `Plan` sustituye la trama con la anterior, los comentarios y los avisos delante del arquitecto; volver de un hueco no replanifica | §4.3 | P-75 |
| REQ-BE-219 | La revisión de la escaleta se guarda, no cierra el gate y ancla sola el elemento obligatorio suelto | §4.3 | P-80 |
| REQ-BE-135 | El prompt del arquitecto enuncia los capítulos, de 2 a 4 escenas por capítulo y la extensión, y el gate de Plotting avisa de cada capítulo fuera del rango de escenas | §4.3 | P-75, P-80 |
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
| REQ-BE-103 | La notificación va detrás de la interfaz `Notifier`, con Telegram como única implementación, **solo avisa** y termina con «Decide en el PC», sin comandos | §4.7 | P-105 |
| REQ-BE-104 | Sin respuesta, el *timeout* **aparca** la ejecución con estado propio; **no hay auto-aprobación** | §4.7 | P-107 |
| REQ-BE-105 | `gates_enabled = false` desactiva los cinco gates y el hecho queda registrado en el manifiesto | §4.7 | P-108, P-93 |

### 10.4 API, CLI, validadores y errores

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-BE-106 | `storymaker decidir` escribe la decisión sobre el gate pendiente y reanuda en el mismo proceso | §6 | P-109 |
| REQ-BE-107 | Al reanudar, el gate decidido no se reabre ni se vuelve a avisar; `continuar` no reanuda un gate pendiente | §4.7 | P-109 |
| REQ-BE-108 | Una decisión sin gate pendiente, o fuera de las cuatro, se rechaza sin tocar nada | §6 | P-109 |
| REQ-BE-109 | `GET /novelas` lista las carpetas de `proyectos/` y abre el fichero de cada una: no hay registro global de novelas | §5 | P-111 |
| REQ-BE-145 | El bloque 3 lleva, tras el estado al cierre de N−1, los eventos narrativos de las versiones aprobadas de los capítulos 1 a N−2, del más reciente al más antiguo, con techo de 2.500; la memoria baja a 3.000 | §3.4 | P-150 |
| REQ-BE-146 | El bloque 6 lleva fijas las cuatro reglas de escritura, y después las palabras y expresiones más repetidas en los capítulos aprobados y la última frase de cada uno | §3.4 | P-151 |
| REQ-BE-147 | El juez enumera las contradicciones antes de puntuar, y la nota de continuidad se topa en Python a `10 − 2·n`, con mínimo 1 | §4.5 | P-152 |
| REQ-BE-137 | `cobertura_capitulo` abre una incidencia de severidad `aviso`, no bloqueante, que nombra cada elemento que falta por su texto | §7.2 | P-143 |
| REQ-BE-140 | `guardrail_prohibidas` detecta un término de una palabra también dentro de otra que contenga su raíz —la palabra sin su vocal final, de al menos cuatro letras—; por debajo compara por palabra completa | §7.2 | P-41 |
| REQ-BE-141 | Un capítulo se guarda sin ninguna línea de encabezado markdown, de cualquier nivel, y sus palabras se cuentan sin ellas | §4.4 | P-81 |
| REQ-BE-142 | El `evento_ancla` del `Brief`, si viene, se guarda como elemento obligatorio del encargo | §4.1 | P-68 |
| REQ-BE-148 | En modo exhaustivo, `Research` corre en serie seis sesiones por dimensión y dos dirigidas por el brief —personajes históricos con evento ancla, y oficio—, cada una con una `WebSearch` y un `WebFetch`; las dirigidas se omiten si el brief no trae de qué | §4.2 | P-153 |
| REQ-BE-149 | Una sesión dirigida con salida inválida se salta con un aviso y las demás siguen; `PresupuestoExcedido` y los errores de entorno detienen la fase | §4.2 | P-153 |
| REQ-BE-190 | El modo de investigación se elige al crear la novela, viaja en el estado del grafo y no cambia después; por defecto es el estándar | §4.2 | P-154 |
| REQ-BE-191 | Todo prompt del investigador —sesión única, dirigidas y micro-sesiones— pasa por `pii_en_prompt_de_investigacion` antes de emitirse, y una sesión con un dato personal no se emite | §4.2 | P-74, P-153 |
| REQ-BE-192 | Los comentarios de «rehacer» del gate de Investigation llegan a todas las sesiones del investigador | §4.2 | P-153 |
| REQ-BE-193 | El informe del gate de Investigation enseña una línea por sesión dirigida, con sus hechos o el motivo por el que se saltó | §4.2 | P-73 |
| REQ-BE-194 | La denegación de una llamada por cuota le pide al rol que entregue ya su respuesta, y la sesión única del investigador tiene veinte turnos | §4.2 | P-29, P-69 |
| REQ-BE-195 | Una sesión única del investigador sin respuesta válida deja un aviso en el gate y no detiene la fase | §4.2 | P-69 |
| REQ-BE-196 | La aprobación del gate de Regeneration con `<objeto>:<fila_id> <campo>=<valor>` aplica ese cambio a esa fila sin volver a buscar; una fila o un campo que no existen no se aplican | §4.6 | P-95 |
| REQ-BE-197 | Una aprobación sin fila ni `campo=valor` no modifica ninguna fila | §4.6 | P-95 |
| REQ-BE-198 | Los capítulos afectados por un cambio de personaje salen de `continuidad`, `plan_escena_personaje` y `uso_hito` | §4.6 | P-97 |
| REQ-BE-216 | Al cerrar el `Brief`, el `n_capitulos` del estado pasa a ser el del brief | §4.1 | P-68 |
| REQ-BE-139 | `nombres_exactos` acepta el nombre canónico con la primera letra en mayúscula y sigue bloqueando cualquier otra diferencia de grafía | §7.2 | P-41 |
| REQ-BE-138 | `storymaker reintentar` reabre el capítulo de una novela terminada en `Fail` sin tocar lo aprobado, y se niega sin tocar nada fuera de ese caso | §6 | P-144 |
| REQ-BE-136 | Cada novela vive en `proyectos/<nombre>/<nombre>.db`, con sus derivados —cerrojo, PDF, capítulos exportados— en la misma carpeta; ramificar crea la carpeta del destino | §2.2 | P-111, P-102 |
| REQ-BE-110 | El endpoint de versión devuelve el manifiesto, sus capítulos en orden y el **bloque de paratexto** con el que se arma la portada | §5 | P-110 |
| REQ-BE-111 | La ficha de personajes cuelga de una **versión**, no de la novela | §5 | P-110 |
| REQ-BE-112 | `POST /novelas/{id}/cambios` no toca nada: abre la Fase 6, que se detiene en su gate | §5 | P-110, P-95 |
| REQ-BE-113 | FastAPI sirve el frontend construido desde `frontend_dist` y declara su URL base en `frontend_base_url`, de modo que lectura, PDF y `render_visual` compartan origen | §5 | P-136 |
| REQ-BE-114 | *Retirado el 2026-09-24.* Decía que ningún endpoint reanudaba una ejecución; desde arq. §16.5 la API lanza la CLI para decidir y continuar (REQ-BE-157), y lo que protege es que solo se opere desde la propia máquina (REQ-BE-164) | §5 | — |
| REQ-BE-115 | El contrato OpenAPI y Schemathesis garantizan que **una petición de cambio malformada no abre la Fase 6** | §5 | P-112 |
| REQ-BE-150 | `GET /novelas` devuelve para cada novela su estado, fase actual, homenajeado, gate pendiente, capítulos aprobados y total, coste y versiones | §5.2 | P-160 |
| REQ-BE-151 | El estado de una novela sigue la precedencia de §5.2: en marcha, detenida, arrancando, esperando al Autor, aparcada, fallida, terminada y en pausa | §5.2 | P-160, P-163 |
| REQ-BE-152 | Cada fase tiene estado aunque no tenga filas en `fase_run`: una fase sin filas y con salida es `completada` y va marcada como deducida | §5.2 | P-160 |
| REQ-BE-153 | El panel devuelve las seis fases con sus ejecuciones, el gate pendiente, los capítulos con sus intentos, la actividad interpretada, el consumo y si el proceso vive | §5.2 | P-160 |
| REQ-BE-154 | El endpoint del gate devuelve su fase, los recuentos del aviso, las preguntas del entrevistador, la petición y candidatos de Regeneración y las filas editables, sin ofrecer como editable un hecho de un corpus sellado | §5.2 | P-160 |
| REQ-BE-155 | Cada fase expone su salida y sus ejecuciones con las decisiones de sus gates; el texto de un intento se pide aparte | §5.2 | P-161 |
| REQ-BE-156 | `GET /ejemplos` devuelve los briefs de `ejemplos/` ya leídos | §5.2 | P-162 |
| REQ-BE-157 | Encargar, continuar, decidir y reintentar **lanzan la CLI como proceso aparte** y responden `202` sin esperar a que termine | §5.3 | P-162, P-164 |
| REQ-BE-158 | El proceso lanzado sobrevive a un reinicio del servidor, y su salida va a `proyectos/<nombre>/registro/` | §5.3 | P-162 |
| REQ-BE-159 | El servidor no guarda ningún proceso en memoria: el estado se recalcula del fichero en cada consulta | §5.3 | P-160, P-162 |
| REQ-BE-160 | La API rechaza antes de lanzar lo que el comando rechazaría: novela ocupada, gate ausente o presente, decisión `editar`, abortar fuera de Intake, brief inválido | §5.3 | P-162, P-165 |
| REQ-BE-161 | Desbloquear rompe el cerrojo solo si su proceso ha muerto | §5.3 | P-162, P-163 |
| REQ-BE-162 | Una edición de gate toma el cerrojo, cambia la fila, la reindexa y queda en `edicion_humana` y `audit_log`, y rechaza un campo no editable o un hecho de un corpus sellado | §5.3 | P-162 |
| REQ-BE-163 | Toda acción de la interfaz queda en `audit_log` con el actor `autor` | §5.3 | P-162 |
| REQ-BE-164 | Las rutas de operación rechazan con `403` a un cliente no local y con `415` un cuerpo que no sea JSON, y la API no concede CORS | §5.3 | P-162 |
| REQ-BE-165 | La petición de cambio del lector queda en `audit_log` con su texto, fragmento, capítulo, versión y candidatos, y el gate los lee de ahí sin repetir la búsqueda | §5.1 | P-166 |
| REQ-BE-167 | Una carpeta con encargo y sin `.db` es una novela `arrancando` durante veinte segundos y `fallida` después, y se puede volver a encargar | §5.2 | P-160, P-162 |
| REQ-BE-181 | En Intake, el endpoint del gate devuelve la descripción del encargo, las respuestas de las rondas anteriores en orden y el brief si ya está cerrado | §5.2 | P-181 |
| REQ-BE-182 | `POST /novelas` acepta el modo de investigación y, si es `exhaustiva`, lanza `storymaker nueva` con `--investigacion exhaustiva`; otro valor se rechaza con `422` | §5.3 | P-182 |
| REQ-BE-183 | Cada escenario se sirve con un nombre corto: el del lugar del corpus o el arranque de su descripción, de seis palabras como mucho, el mismo en la ficha, la escaleta y la impresión | §5.1 | P-183 |
| REQ-BE-184 | El PDF de una versión se descarga por la API; si no se generó, la respuesta es `404` y no un error del servidor | §5.1 | P-184 |
| REQ-BE-185 | Un proceso lanzado desde la interfaz no abre ninguna ventana, ni él ni los que él lance | §5.3 | P-162 |
| REQ-BE-186 | El PDF de una versión se imprime desde la ruta de impresión del frontend, tras confirmar la invocación y antes del aviso de terminada, sin servidor levantado; sin `dist/` cae al HTML mínimo con un aviso, y un fallo no cambia el resultado de la invocación | §4.5 | P-185 |
| REQ-BE-187 | Cada candidato de Regeneración del endpoint del gate lleva su objeto, su fila, su campo por defecto y el valor actual de ese campo; un candidato registrado sin fila los lleva vacíos | §5.2 | P-186 |
| REQ-BE-166 | `decidir` rechaza `abortar` fuera del gate de Intake sin tocar nada | §5.3 | P-165 |
| REQ-BE-116 | La CLI expone los nueve comandos declarados | §6 | P-113, P-144 |
| REQ-BE-117 | `ramificar` **copia el fichero** y escribe la fila de `procedencia`; no hay columna de rama en las consultas | §6 | P-102 |
| REQ-BE-118 | `evaluar` corre los cinco briefs en modo batch con `gates_enabled = false` | §6 | P-120, P-108 |
| REQ-BE-119 | Todos los validadores de ejecución son nodos o aristas condicionales; **ninguno es una herramienta que un agente decida llamar** | §7.2 | P-06, P-56 |
| REQ-BE-120 | Las aristas condicionales leen booleanos calculados en Python, nunca la salida de un modelo | §7.2 | P-56 |
| REQ-BE-121 | Tres validadores semánticos no bloquean: `respaldo_fuente` limita la firmeza, y `ejecucion_escaleta` y `arco_ejecutado` abren aviso | §7.2b | P-72, P-84 |
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
| 2026-09-24 | §4.3: los huecos con escena, dimensión y afirmación propuesta; la revisión que se guarda y repara; rehacer la Trama. Entran REQ-BE-217 a REQ-BE-219 | Se propaga §4 (Fase 3) de la arquitectura; el detalle baja a `specs/trama-rehacible/` |
| 2026-09-24 | §4.1: el `n_capitulos` del brief cerrado pasa al estado del grafo; entra REQ-BE-216 | Se propaga §4 de la arquitectura: en el encargo por conversación el estado arrancaba con diez capítulos y la escaleta tenía los que el comprador hubiera pedido |
| 2026-09-24 | §4.2: el dato central es lo que existió u ocurrió, y la fecha o el lugar ausentes de la cita son añadido. §3.6: `anadido_vigente` tolera que el añadido se copie con otras palabras. Entran REQ-BE-214 y REQ-BE-215 | Se propaga §4 de la arquitectura: el verificador era demasiado estricto con fragmentos que no repiten el contexto de su página |
| 2026-09-24 | **La firmeza se usa, y el respaldo admite el parcial.** §2.3: `sin_respaldo` se añade al abrir, sin subir la versión del esquema. §3.4: el bloque 5 enseña lo que no dice la cita mientras siga en el enunciado y el bloque 6 dice qué hacer con cada firmeza. §3.6: `anadido_vigente`. §4.2: los estados se definen respecto a la fuente, las lagunas no se verifican y el verificador da el parcial. §4.3: el arquitecto recibe el uso de cada firmeza y el informe de Plotting avisa de las escenas apoyadas solo en lo inferido o desconocido. REQ-BE-200 y REQ-BE-203 se reescriben; entran REQ-BE-207 a REQ-BE-213 | Se propagan §4, §6, §7 y §17 de la arquitectura |
| 2026-09-24 | **La firmeza de un hecho se calcula al leer.** §3.6 gana `firmeza(estado, respaldo, origen)`; §3.4 lleva la firmeza al bloque 5; §4.2 fija que el verificador escribe solo `respaldo` y que el prompt define los cuatro estados; §4.3 pasa los hechos de la micro-sesión por el verificador, da firmeza `inventado` a las invenciones, cuenta en el gate de Plotting los hechos micro sin respaldo y mete el `respaldo` en el hash del sello. REQ-BE-65 se reescribe y entran REQ-BE-199 a REQ-BE-206; REQ-BE-206 y la cita de la micro-sesión en §4.3 salieron al implementar (It-31) | Se propagan §4, §6 y §7 de la arquitectura. `inferido` mezclaba deducción, cita fallida e invención, la degradación subía de categoría a los `desconocido` y los hechos de la micro-sesión no los miraba nadie |
| 2026-09-24 | §4.7: el aviso de un gate termina con «Decide en el PC» y deja de traer los comandos de `storymaker decidir`; REQ-BE-103 se reescribe | Se propaga §10 de la arquitectura, por petición del Autor |
| 2026-09-24 | §4.6: confirmar en el gate es elegir la fila y su valor, con el formato `<objeto>:<fila_id> <campo>=<valor>`; una aprobación sin ellos no cambia nada; el alcance de un personaje sale de `continuidad`, la escaleta y `uso_hito`. Entran REQ-BE-196 a REQ-BE-198 | Se propaga §4 de la arquitectura. La spec pedía a la vez «lenguaje natural» y «ningún modelo», y el código lo resolvía escribiendo la frase del lector como valor en la fila que devolviera una segunda búsqueda |
| 2026-09-24 | §5.2: los candidatos de Regeneración del gate llevan **objeto, fila, campo por defecto y valor actual**. Entra REQ-BE-187 | La pantalla del gate compone con ellos la elección que §4.6 define |
| 2026-09-24 | §4.5: **el PDF se imprime desde la ruta de impresión del frontend**, tras confirmar la invocación, con la aplicación en memoria y sin servidor. Entra REQ-BE-186 | El PDF salía del HTML mínimo de `render.py`, sin maqueta, y el Autor lo encontró horrible. Era la deuda anotada en It-21: la arquitectura pedía imprimir la ruta de lectura desde el principio |
| 2026-09-24 | §5.1: `GET /novelas/{id}/versiones/{n}/pdf` sirve **el PDF de la versión**. §5.3: el proceso lanzado lleva **una consola oculta** que heredan los suyos. Entran REQ-BE-184 y REQ-BE-185 | El Autor no tenía forma de llegar al PDF desde la interfaz, y cada lanzamiento abría ventanas de consola: el proceso se creaba sin consola y Windows se la daba, visible, a cada proceso que abría |
| 2026-09-24 | §4.2: la denegación por cuota pide entregar ya, la sesión única tiene veinte turnos y su falta de resultado es un aviso y no un error. Entran REQ-BE-194 y REQ-BE-195 | Se propaga §4 de la arquitectura: una novela se detuvo en Research porque el investigador agotó los turnos intentando búsquedas denegadas |
| 2026-09-24 | §5.1: cada escenario lleva **un nombre corto**, derivado del lugar o del arranque de la descripción. Entra REQ-BE-183 | Petición del Autor: los lugares salían titulados con su descripción entera |
| 2026-09-24 | §4.2 gana el modo exhaustivo de la investigación —ocho sesiones dirigidas, su perfil, su tabla de encargos y su política de fallos—, amplía la entrada del investigador a personajes, evento y rol de época y conecta la guarda de PII a todo prompt del investigador. Entran REQ-BE-148, REQ-BE-149 y REQ-BE-190 a REQ-BE-193 | Se propagan §4 y §15 de la arquitectura, con las decisiones de su grilling |
| 2026-09-24 | §5.3: `POST /novelas` acepta **el modo de investigación** y lo pasa a `storymaker nueva`. Entra REQ-BE-182 | El modo exhaustivo de arq. §4, Fase 2, se elige al crear la novela, y la interfaz crea novelas |
| 2026-09-24 | §4.1: el encargo admite **`descripcion`**, que entra en la premisa y no en la cuarentena; §5.2: el gate de Intake devuelve **la conversación** —descripción, respuestas de cada ronda y brief cerrado—. Entran REQ-BE-180 y REQ-BE-181 | Petición del Autor: que el encargo lo haga el entrevistador, como describe la Fase 1. Con el formulario completo no le quedaba nada que preguntar, y lo que se escribía con palabras propias acababa en la cuarentena, que el entrevistador no lee |
| 2026-09-24 | §7.2: `guardrail_prohibidas` detecta derivadas; §4.4: los encabezados markdown del escritor no se guardan; §4.1: el evento ancla entra como elemento obligatorio. Entran REQ-BE-140 a REQ-BE-142 | Se propagan §4 y §11a de la arquitectura. La tercera novela real dejó pasar dos prohibidas en forma derivada, repitió el título de cinco capítulos dentro del texto y no narró su evento ancla |
| 2026-09-24 | La fila de `nombres_exactos` en §7.2 admite la mayúscula inicial de principio de frase; entra REQ-BE-139 | Se propaga §11a de la arquitectura: un nombre canónico en minúscula inicial tumbaba los capítulos que lo escribían correctamente al abrir frase |
| 2026-09-24 | **§5 se reescribe en tres superficies —lectura, seguimiento y operación—**: la API calcula el estado de cada novela y de cada fase, sirve la salida de cada fase y **lanza la CLI como proceso aparte** para encargar, continuar, decidir y reintentar; escribe ella misma las ediciones de un gate; solo acepta acciones locales y en JSON. Se retira REQ-BE-114 y entran REQ-BE-150 a REQ-BE-166. Los números saltan a 150, y los ítems a `P-160`, para no pisar los que otra línea de trabajo está numerando en paralelo | Baja de arq. §16.5: el Autor opera la novela desde la interfaz. Lo que la API ya no puede prometer —que ningún endpoint reanuda— se cambia por lo que sí protege: un solo camino de código y nada operable desde fuera de la máquina |
| 2026-09-24 | §3.4: el bloque 3 lleva los eventos narrativos de los capítulos aprobados anteriores a N−1 y sube a 2.500; la memoria baja a 3.000; el bloque 6 lleva reglas de escritura, repeticiones y cierres. §4.5 y §7.2: el juez enumera contradicciones y la continuidad se topa. Entran REQ-BE-145 a REQ-BE-147 | Se propagan §6 y §11b de la arquitectura, a partir de la lectura de la cuarta novela real |
| 2026-09-24 | `cobertura_capitulo` pasa a severidad `aviso` y su incidencia nombra el elemento por su texto; la CLI gana `storymaker reintentar`. Entran REQ-BE-137 y REQ-BE-138 | Se propagan §11a y §16.5 de la arquitectura. La cuarta novela real agotó los reintentos del capítulo 8 con el mismo texto tres veces: el editor recibía «no aparecen: [1]» y no tenía nada que corregir |
| 2026-09-24 | §5 declara el prefijo `/api`, los modelos de respuesta y los campos que el frontend lee —historial con fecha y puntuación, título de capítulo, versión anterior, escenarios, fragmento de la petición—, y la ficha de personajes pasa a responder en `/versiones/{n}/personajes` | Al implementar el frontend: la API servía la ficha sin versión, sin paratexto y sin títulos, cosas que este apartado ya contrataba o que la spec del frontend pedía y ningún campo daba. Ninguna decisión nueva: es la superficie que las dos specs ya describían, escrita con la forma que tiene |
| 2026-09-24 | **Una carpeta por novela**: §2.2, §5 y §6 dicen `proyectos/<nombre>/<nombre>.db`; entra REQ-BE-136 | Se propaga la decisión del Autor en §16.4 de la arquitectura |
| 2026-09-24 | §4.3 fija **la forma de la escaleta**: el arquitecto recibe capítulos, escenas por capítulo y extensión, y el gate de Plotting avisa de los capítulos fuera del rango. Entra REQ-BE-135 | La primera escaleta con gates salió con una escena por capítulo. §19 de la arquitectura fija de 2 a 4, pero ni el prompt lo decía ni nada lo comprobaba |
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
