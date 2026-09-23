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
├─ api/                                                                   FastAPI: webhook, lectura, cambio
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
| **API (FastAPI)** | Servidor de larga vida | Recibir la decisión del gate por webhook, servir la lectura, recibir la petición de cambio del lector |

Los dos llaman a `commons/graph/run.py::invocar(novela, entrada)`. La API no tiene un camino propio hacia el grafo, y esto es deliberado: si lo tuviera, habría dos implementaciones de la reanudación y solo una de ellas estaría cubierta por las pruebas de integración.

### 2.2 Configuración

Un único objeto `Settings` de `pydantic-settings`, leído del entorno y de un `.env`, cargado una vez al arrancar. No hay lectura de variables de entorno dispersa por el código: **quien necesita un valor lo recibe inyectado**, para que las pruebas puedan construir un `Settings` distinto sin tocar el entorno del proceso.

| Grupo | Claves | Nota |
|---|---|---|
| Rutas | `directorio_proyectos` (por defecto `proyectos/`) | El directorio es el registro de novelas (§16.4 arq.) |
| Modelos | `modelo_por_rol` (mapa rol→id de modelo), `sdk_version` | Por defecto los nueve roles en Haiku 4.5 |
| Gates | `gates_enabled`, `timeout_gate_horas` | `false` en modo batch |
| Telegram | `telegram_bot_token`, `telegram_chat_id`, `telegram_secret_token` | El último protege el webhook |
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

**Inmutabilidad, con dos cerrojos.** El principio «nada se sobrescribe» se protege arriba con la regla Semgrep `no-update-inmutables`, que impide escribir el código, y abajo con ***triggers* `BEFORE UPDATE` y `BEFORE DELETE`** sobre `capitulo_version`, `fase_run`, `version_novela`, `version_capitulo` y `mundo_hecho` tras el sello, que impiden que se ejecute. El *trigger* lanza `RAISE(ABORT, ...)` con el nombre de la tabla. Un principio con un solo cerrojo es una convención; con los dos, es una propiedad.

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

**Los nodos se llaman igual que las acciones de PlusCal.** No es una convención estética: es lo que hace que un contraejemplo de TLC se lea como una secuencia de nodos reales. La tabla de correspondencia de §9 de la arquitectura es una lista de identidades, y una prueba la comprueba: **el conjunto de nombres de nodo del grafo y el conjunto de nombres de acción de `spec/harness.tla` deben ser iguales.** Si alguien añade un nodo sin añadir su acción, la prueba cae.

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

**Las tres guardas, todas por construcción:**

| Guarda | Mecanismo | Qué impide |
|---|---|---|
| **Presupuesto** | Se cuenta el prompt ensamblado antes de emitir; si excede el techo del rol, **la llamada no se emite** | Que una sesión reviente el límite de 100.000 tokens concurrentes |
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

**Errores.** Brief incompleto tras agotar las preguntas → el gate se abre igualmente con el informe de lo que falta; decide el Autor.

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

**El render se comprueba antes de publicar.** Se arma el manifiesto de la versión candidata, se renderiza la lectura contra él y `render_visual` lo juzga **con la transacción todavía abierta**: si algo no renderiza, se deshace y no hay versión publicada. G5 no admite excepción, y un índice roto detectado después sería una versión ya publicada sin arista de vuelta. No hace falta nodo nuevo: la comprobación cabe dentro de `publication.publish`.

**Sin gate humano**, porque el manuscrito ya se aprobó al cerrar Writing y lo que queda es automático.

**Errores.** Lean falla → **la versión no se publica, sin anulación posible**. Umbral del juez no superado → vuelta al gate de Writing.

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

**Contrato.** El nodo llama a `interrupt()`; el checkpointer persiste; la invocación termina. La decisión llega y reanuda con `Command(resume=...)`.

Cuatro decisiones: **aprobar**, **rehacer con comentario** —el texto libre se inyecta como bloque extra en el prompt y cuenta contra el límite de reintentos—, **editar** y **abortar**.

**Notificación tras la interfaz `Notifier`**, con Telegram como única implementación hoy. Es un token en el `.env` y soporta botones inline; WhatsApp exige Meta Business, número verificado y plantillas aprobadas, y queda como adaptador futuro.

**Sin respuesta**: el *timeout* **aparca** la ejecución con estado propio. **No hay auto-aprobación**, porque eso convertiría un gate de calidad en un temporizador.

**`gates_enabled = false`** los desactiva enteros, y queda registrado en el manifiesto. Es imprescindible: los cinco briefs de evaluación tienen que correr desatendidos.

---

## 5. La API de FastAPI

Tres superficies con perfiles de riesgo distintos, y conviene no mezclarlas.

| Método y ruta | Quién llama | Contrato | Errores |
|---|---|---|---|
| `POST /webhook/telegram` | Telegram | Callback del botón inline. **Comprueba el `secret_token` de la cabecera `X-Telegram-Bot-Api-Secret-Token`**; escribe la decisión en `gate`, responde en seguida y lanza la invocación **como tarea de fondo** | `401` sin secreto válido; `409` si la novela está ocupada; `200` y decisión ignorada si el gate ya estaba decidido |
| `GET /novelas` | Frontend | Lista el directorio `proyectos/` y abre cada fichero para leer título, fase en curso y número de versiones | — |
| `GET /novelas/{id}` | Frontend | Ficha de la novela: fase, gate abierto si lo hay, versiones publicadas | `404` |
| `GET /novelas/{id}/versiones/{n}` | Frontend | Manifiesto de la versión y sus capítulos en orden | `404` |
| `GET /novelas/{id}/versiones/{n}/capitulos/{k}` | Frontend | Texto del capítulo tal como esa versión lo fija | `404` |
| `GET /novelas/{id}/personajes` | Frontend | Fichas de personajes y lugares con sus capítulos | `404` |
| `GET /novelas/{id}/versiones/{a}/diff/{b}` | Frontend | Diff de dos manifiestos: qué capítulos cambian | `404` |
| `POST /novelas/{id}/cambios` | Frontend | Petición de cambio del lector. **No toca nada**: abre la Fase 6, que se detiene en su gate | `409` si la novela está ocupada |

**El endpoint de decisión es el único que reanuda una ejecución**, y por eso es el único protegido. El resto es lectura, más una petición de cambio que no altera nada hasta que el Autor la aprueba. Que la lectura quede abierta es una decisión declarada, no un olvido: está en U-17.

**OpenAPI y Schemathesis** cubren el endpoint de decisión: **una decisión malformada no reanuda el grafo.**

*Clase: **A/T** (contrato OpenAPI y Schemathesis). Gate: G1.*

---

## 6. La CLI de Typer

| Comando | Qué hace |
|---|---|
| `storymaker nueva <brief.json>` | Crea el fichero de la novela en `proyectos/` y arranca la invocación |
| `storymaker continuar <novela>` | Reanuda desde el último checkpoint, sea tras un fallo o tras un gate |
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

Corren en el portátil y en CI, sobre el repositorio. **Ninguno de ellos ve una novela**: ven código, tipos, esquemas y modelos. Su gate es G0, G1 o G2. Los números 18, 20, 21 y 22 son la familia de correspondencia de §11e de la arquitectura: los únicos que comparan el código contra estos documentos en vez de contra sí mismo.

| # | Validador | Qué comprueba | Clase | Gate | Bloquea |
|---|---|---|---|---|---|
| 1 | **mypy `--strict`** | Que ningún valor se use de forma incompatible; que el estado del grafo no tenga `dict[str, Any]` | A | G0, G1 | Sí |
| 2 | **ruff + bandit (conjunto `S`)** | Inyección SQL por interpolación, `subprocess` con `shell=True`, `pickle`, aserciones en producción | A | G0, G1 | Sí |
| 3 | **gitleaks** | Que no se commitee el token de Telegram, las claves de Langfuse ni la de Anthropic | A | G0, G1 | Sí |
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
| 14 | **TLC sobre `spec/harness.cfg`** | Los cuatro invariantes de seguridad sobre todos los estados alcanzables del modelo (5 capítulos, 2 reintentos) | A | G1 | Sí |
| 15 | **`lake build` de *fixture*** | Que el proyecto Lean compila y que el generador produce el fichero de referencia | A | G1 | Sí |
| 16 | **Integración con agente falso** | El grafo completo sobre SQLite temporal: recorrido en batch, atomicidad del checkpoint, reanudación, Fase 6, ramificación, reintentos agotados | T | G1 | Sí |
| 17 | **Suite adversaria determinista** | Inyección por texto pegado, página hostil, herramienta prohibida, exfiltración de PII, evasión del guardrail | T | G1 | Sí |
| 18 | **Identidad nodo↔acción** | Que los nombres de nodo del grafo sean iguales a las acciones de `harness.tla` **y que su conjunto de aristas sea igual a la definición `Aristas`** que gobierna el `Next` | A | G1 | Sí |
| 19 | **Steiger** | Las dos reglas de FSD sobre `frontend/src` | A | G1 | **No, informa** |
| 20 | **`registro_de_validadores`** | Que el registro de validadores deterministas, la tabla de §11a de la arquitectura y la de §7.2 de este documento coinciden por pares: mismo conjunto, mismo punto de ejecución, misma condición de bloqueo | A/T | G1 | Sí |
| 21 | **`inventario_del_plan`** | Sobre todo `specs/*/plan.md`: que cada ruta y cada símbolo de la columna «Ficheros y símbolos» existe en el árbol, y que todo módulo de `backend/src/storymaker/**` —salvo los `__init__.py`— está declarado en algún ítem | T | G1 | **No, informa en dos cubos** |
| 22 | **`anclas_de_procedencia`** | Que toda ancla de un docstring de módulo —primera línea, formato `spec: §3.6 · arq: §11a`— apunta a un apartado que existe, y que **todo apartado de §3 y §4 de este documento tiene al menos un módulo que lo cite** | T | G1 | **No, informa** |
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
| Secreto del webhook ausente o incorrecto | Rechazo | `401` |
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
| CLI | T | G1 |
| Correspondencia documento↔código (§7.1 nº 18, 20, 21, 22) | A/T | G1 |
| Fiabilidad de los validadores semánticos | **I** | G4 |
| Lectura de la API sin autenticación | **U-17** | — |

**Riesgos aceptados que este backend hereda**, todos con fila en §5 de `verification.md`: U-1 brecha de refinamiento, U-18 veracidad de los documentos sobre el dominio, U-2 verdad histórica del corpus, U-3 reproducibilidad textual, U-4 evasión por paráfrasis, U-7 coste estimado, U-8 dominios de `WebFetch`, U-9 varianza del juez, U-13 fiabilidad del verificador, U-15 disponibilidad de `sqlite-vec`, U-14 cita fabricada, U-16 fiabilidad de `ejecucion_escaleta` y `arco_ejecutado`, U-17 API de lectura sin autenticación.

---

## 10. Lo que este documento deja fuera a propósito

- **La forma técnica exacta** —qué fichero, qué función, en qué orden se construye— va en [`plan.md`](plan.md).
- **El frontend**, que tiene su metodología propia en §16.3 de la arquitectura.
- **El contenido del proyecto Lean y de la especificación TLA+**: son artefactos de verificación con vida propia; aquí solo se fija cómo los invoca el backend y qué hace con su veredicto.
- **Los prompts de rol**, que viven en Langfuse como fuente de verdad y no en el repositorio.

---

## 11. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-23 | Versión inicial | Fijar el contrato del backend completo —módulos transversales, seis fases, API y CLI— y, sobre todo, separar las dos familias de validadores: los que comprueban que el código está bien escrito y los que comprueban que una novela está bien hecha |
| 2026-09-23 | Tras la pasada de congruencia con el plan: §4.3 declara que el corpus llega al arquitecto **por búsqueda semántica** y no entero, y §7.2 recoge el **linter de auto-similitud** entre capítulos, diciendo expresamente que no es uno de los once validadores de §11a | Son los usos 3 y 4 de los embeddings de §16.2 de la arquitectura. Estaban en el plan y no en la spec, que es la manera de que el código acabe haciendo algo que su contrato no dice |
| 2026-09-23 | Tras el recorrido de trazabilidad contra la arquitectura: **Lean baja de la pasada determinista a la pasada del extractor** y gana su tercer punto de ejecución, el gate de Plotting (§3.7, §4.4, §7.2c); `arco_anclado` pasa a exigirse **por apariciones en ≥3 escenas** con el arco plano admitido y el homenajeado como única excepción (§7.2a) | Tres desviaciones de la arquitectura, que manda. Lean en la pasada determinista habría verificado una cronología que llega hasta N−1, porque las filas narrativas del capítulo N las escribe el extractor; el punto de Plotting, el más barato de los tres, faltaba entero; y «personaje principal» es justamente el concepto que la arquitectura descarta porque el modelo de datos no sabe responderlo |
| 2026-09-23 | Tras el grilling: los dos extractores quedan declarados como roles con techo (12.000 y 6.000) y §1 de la arquitectura sube a nueve; `render_visual` pasa a correr dentro de `PublishVersion` sobre la versión candidata antes del `commit`; `cobertura_anclada` y `arco_anclado` quedan bajo G4 y `cobertura_personalizacion` bajo G5 | Tres hilos que el grilling destapó y que el Autor resolvió: un presupuesto que sumaba siete techos de nueve agentes, un validador de render que se declaraba posterior a la publicación que debía impedir, y dos validadores del gate de Plotting sin puerta asignada |
| 2026-09-23 | §7.1 gana tres validadores de programación —`registro_de_validadores` (bloquea), `inventario_del_plan` y `anclas_de_procedencia` (informan)— y el nº 18 pasa a comparar también **aristas**; §3.6 declara que `REGISTRO` es el cableado del que se sirven el grafo y el hook | Nada comprobaba que el código implementara lo que estos documentos especifican: ni que un apartado declarado llegara a escribirse, ni que un validador siguiera bloqueando después de un refactor. Con el registro como cableado la comprobación es clase A, porque un validador ausente de él sencillamente no corre |
