# Spec — Cierre del arnés: hooks, herramientas y coste por novela

Qué cambia para que el arnés cumpla cuatro cosas que no cumplía entero: el hook de validación del capítulo, un hook de policy propio, herramientas con esquema validado y el registro de tokens y coste por novela en Langfuse. Toca contratos de la [spec del backend](../backend/spec.md): §3.3 (`commons/agents`), §3.6 (`commons/validation`) y §3.8 (`commons/obs`). Deriva de [`docs/architecture.md`](../../docs/architecture.md) §3, §5, §12, §14 y §15, y **amplía §5 y §12** en un punto que la arquitectura no recoge todavía: un rol distinto del investigador con herramientas (§4). La forma técnica exacta está en [`plan.md`](plan.md).

## 1. Qué problema resuelve

Una lectura del repositorio contra la lista de requisitos del arnés dio cuatro huecos:

- **El hook de validación no recibía el fichero.** `.claude/settings.json` le pasaba `"$CLAUDE_FILE_PATH"`, una variable que Claude Code no define: la ruta llega en el JSON del evento, por la entrada estándar. Además saltaba con cualquier `Write` o `Edit`, fuera o no un capítulo, y escribía el informe en `stdout`, que Claude Code no le enseña al agente cuando el hook bloquea.
- **No había hook de policy.** La policy de términos prohibidos (`guardrail_prohibidas`) corría como nodo del grafo y dentro del hook de validación, pero no como hook propio.
- **Ninguna herramienta tenía un esquema propio.** Las salidas de los roles se validan con Pydantic en `schema_guard`, pero los roles solo usaban `WebSearch` y `WebFetch`, que son de Claude Code y cuyo esquema no es del arnés.
- **Langfuse no recibía nada.** `ObservadorLangfuse` llamaba a `cliente.trace()` y `cliente.score()`, que no existen en la versión fijada del SDK (4.15.4). `abrir_sesion` no se llamaba desde ningún sitio, así que tampoco habría habido una sesión por novela sobre la que sumar el coste, y `cerrar` tampoco se llamaba, así que lo pendiente podía no salir antes de que terminara el proceso.

Por el criterio de producto, nada de lo que se añade aquí puede atascar una novela. Los dos hooks solo actúan sobre la edición manual de un capítulo, las herramientas son una ayuda opcional para el arquitecto, y un fallo de Langfuse se anota en el log sin tumbar el nodo.

## 2. El hook de validación

### 2.1 Cómo llega el evento

Claude Code ejecuta el hook con el evento como JSON en la entrada estándar. La ruta del fichero editado está en `tool_input.file_path`. El hook se configura como `PostToolUse` sobre `Write|Edit|MultiEdit`, desde `$CLAUDE_PROJECT_DIR/backend` y no desde el directorio de trabajo de la sesión, que puede haber cambiado.

La skill `continuity-check` sigue invocando el mismo ejecutable con la ruta como argumento. Con argumento, el hook no lee la entrada estándar.

### 2.2 Qué es un capítulo

Un fichero es un capítulo si es Markdown y tiene su `<nombre>.contexto.json` al lado, o si su nombre empieza por `capitulo`. Cualquier otro fichero —los documentos de `docs/`, las specs, el código— pasa sin mirarse. Tampoco bloquean un evento ilegible, un evento sin ruta ni una ruta que no existe: el hook devuelve 0.

### 2.3 Qué devuelve

Sobre un capítulo, el hook corre `revisar_fichero`, el mismo Core Domain que ejecuta el grafo. Si alguna incidencia bloquea, escribe el informe en `stderr` y devuelve **2**. En `PostToolUse` la edición ya está en disco: el 2 hace que Claude Code le pase el informe al agente para que la corrija. Si nada bloquea, escribe el informe en `stdout` y devuelve 0.

La salida se fuerza a UTF-8, porque en Windows la consola no lo es por defecto y las comillas del informe llegaban rotas.

## 3. El hook de policy

Es un hook distinto, y corre en otro momento: **`PreToolUse`** sobre `Write|Edit|MultiEdit`. Mira solo el texto que la edición **introduce** —`content` de un `Write`, `new_string` de un `Edit` y cada `new_string` de un `MultiEdit`—, no el fichero entero. Si ese texto trae un término prohibido, deniega la herramienta antes de que la edición llegue al disco: escribe el motivo en `stderr` y devuelve 2.

La regla es la del grafo, `guardrail_prohibidas`, con su normalización. Los términos salen del mismo `<capitulo>.contexto.json` que usa el hook de validación. Sin contexto no hay lista y la edición pasa. Lo que ya estaba en el capítulo antes de la edición no lo juzga este hook sino el de validación.

El reparto de papeles es deliberado. La validación comprueba el capítulo entero y todas las reglas, pero después de escribir. La policy comprueba una sola regla, antes. Importa por el nivel `destinatario` de §15 de la arquitectura: el nombre que no puede aparecer en una novela que se regala no debería llegar a escribirse, ni siquiera un instante.

## 4. Las herramientas del arquitecto

### 4.1 Qué hacen

Son dos, de cálculo puro, sin red y sin base:

- **`sumar_dias`**: recibe `fecha` (AAAA-MM-DD) y `dias` (entero entre −36 500 y 36 500) y devuelve la fecha resultante con su día de la semana.
- **`edad_en_fecha`**: recibe `nacimiento` y `fecha`, cada una en AAAA, AAAA-MM o AAAA-MM-DD, y devuelve los años cumplidos. Si la precisión no alcanza para saber si el cumpleaños ya pasó, devuelve el intervalo («entre 33 y 34 años»). Si la fecha es anterior al nacimiento, lo dice.

El calendario es el gregoriano proléptico de `datetime`. Cuando alguna de las fechas es anterior al 15 de octubre de 1582, la respuesta de `sumar_dias` avisa de que el día de la semana no coincide con el calendario juliano de la época.

La razón para dárselas al arquitecto es que fecha cada escena y conoce el nacimiento y la muerte de cada personaje, y la aritmética de calendario es justo lo que un modelo hace mal de cabeza. Ninguna de las dos es un validador: los validadores siguen siendo nodos del grafo (arq. §1) y nada de lo que devuelven se toma como veredicto.

### 4.2 El esquema

Cada herramienta declara su entrada como un modelo Pydantic con `extra="forbid"`. De ese modelo sale el JSON Schema que se registra en el servidor MCP y que ve el modelo, y contra ese mismo modelo se valida la entrada dentro del manejador. No hay una segunda descripción que pueda divergir.

Una entrada que no cumple el esquema no se ejecuta: vuelve al rol como resultado de error (`is_error`), con el campo y el mensaje de Pydantic. Una fecha que cumple el patrón pero no existe, como 1574-02-30, vuelve igual. El manejador no lanza nunca.

### 4.3 Cómo se conceden

Llegan por un servidor MCP en proceso, `storymaker`, que el transporte del SDK crea solo cuando el perfil las tiene. Claude Code las nombra `mcp__storymaker__<herramienta>`.

- Viven en una tabla propia, `PROPIAS`, aparte de `HERRAMIENTAS`. Esa tabla sigue siendo la de las herramientas de red, y las pruebas y la regla Semgrep que vigilan que solo el investigador salga a la red la siguen leyendo igual.
- Solo el perfil `arquitecto` las tiene, con una **cuota de 4 llamadas por herramienta** que impone el mismo hook `PreToolUse` del SDK que ya limita las búsquedas del investigador.
- El arquitecto pasa de 1 a **6 turnos**, porque usar una herramienta cuesta al menos uno más. Si agota los turnos, `schema_guard` recibe lo que haya dicho, como ya ocurre con el investigador.
- Su techo de §12 no cambia: cada respuesta es una línea.
- El prompt de respaldo del arquitecto le dice que las use para edades y fechas relativas.

## 5. Tokens y coste por novela en Langfuse

### 5.1 Qué se envía

`ObservadorLangfuse` usa la API v4 del SDK, construida sobre OpenTelemetry:

- **Cada invocación de rol es una observación de tipo `generation`**, con el nombre de span de siempre (`capitulo_07 · escritor · intento_2`). Lleva `usage_details` con los tokens de entrada y salida y `cost_details` con `total` igual al coste que da el SDK. Con eso Langfuse cuenta los tokens y el coste de la observación.
- **La sesión es la novela.** Se propaga con `propagate_attributes(session_id=…)`, y Langfuse suma por sesión: el coste de la novela es esa suma, sin cálculo propio.
- **Los scores van a la sesión**, con `create_score(session_id=…)`.
- El coste sigue etiquetado en el metadato como `coste_usd_estimado_en_cliente` (U-7). `cost_details` no lo convierte en facturación: es la misma estimación, puesta donde Langfuse la suma.

### 5.2 Dónde se abre la sesión

- `invocar` abre la sesión con el nombre de la novela (`novela.stem`, el mismo que el hilo de LangGraph) antes de construir las dependencias. Arranque, reanudación, reintento y regeneración pasan todos por ahí, así que caen en la misma sesión.
- `storymaker decidir` construye su observador con `construir(settings, novela=…)`, de modo que el score de la decisión del Autor también cae en ella.
- Al salir de `invocar`, también si un nodo revienta, se llama a `cerrar()`, que vacía lo pendiente. `decidir` también cierra.

### 5.3 Qué pasa si Langfuse falla

El envío de un span o de un score está protegido. Un fallo se anota como `warning` en el log y el nodo sigue. Sin claves, `construir` sigue devolviendo el `ObservadorNulo`, que ahora también recuerda la sesión.

## 6. Contratos

| Pieza | Contrato |
|---|---|
| `commons/validation/cli_hook.py` | `main(argumentos=None, entrada=None) -> int`: 0 o `BLOQUEA` (2). `leer_evento`, `ruta_del_evento`, `es_capitulo`, `salida_en_utf8` |
| `commons/validation/cli_policy.py` | `main(entrada=None) -> int`: 0 o 2. `texto_introducido(evento) -> str`, `revisar_edicion(texto, ruta_contexto) -> list[Incidencia]` |
| `.claude/settings.json` | `PreToolUse` → `cli_policy`, `PostToolUse` → `cli_hook`, ambos sobre `Write\|Edit\|MultiEdit` y sin argumentos |
| `commons/agents/herramientas.py` | `HERRAMIENTAS_PROPIAS: dict[str, Herramienta]` por nombre calificado; `ejecutar(calificado, argumentos) -> dict` con `content` y, si falla, `is_error`; `servidor_mcp(calificados)`; `es_propia(nombre)` |
| `commons/agents/techos.py` | `PROPIAS`, `propias_de(perfil)`; cuota y `TURNOS` del arquitecto |
| `commons/agents/invocacion.py` | El transporte recibe `herramientas_de(perfil) + propias_de(perfil)` |
| `commons/agents/transporte_sdk.py` | `tools` solo con las integradas; `allowed_tools` con todas; `mcp_servers={"storymaker": …}` si hay propias |
| `commons/obs/trazas.py` | `Span.como_payload()` con `usage_details` y `cost_details`; `ObservadorLangfuse` sobre la API v4; `construir(settings, *, novela=None)` |
| `commons/graph/run.py` | `invocar` abre la sesión y cierra el observador al salir |
| `backend/pyproject.toml` | `langfuse>=4.0` |

## 7. Requisitos

| ID | Requisito | Clase | Gate |
|---|---|---|---|
| REQ-FI-01 | El hook de validación lee la ruta de `tool_input.file_path` en el JSON de la entrada estándar; con argumento, la toma del argumento | T | G1 |
| REQ-FI-02 | El hook de validación solo mira capítulos; cualquier otro fichero, un evento ilegible o una ruta inexistente pasan con 0 | T | G1 |
| REQ-FI-03 | Un capítulo que bloquea devuelve 2 con el informe en `stderr`, en UTF-8 | T | G1 |
| REQ-FI-04 | El hook de policy deniega en `PreToolUse` un `Write`, `Edit` o `MultiEdit` que introduce en un capítulo un término prohibido de su contexto | T | G1 |
| REQ-FI-05 | La policy juzga solo el texto que la edición introduce, y sin contexto deja pasar | T | G1 |
| REQ-FI-06 | `.claude/settings.json` declara los dos hooks, cada uno en su momento, y ninguno lee `$CLAUDE_FILE_PATH` | T | G1 |
| REQ-FI-07 | La entrada de cada herramienta propia se valida contra su modelo Pydantic, del que sale también el JSON Schema publicado; lo que no cumple vuelve como error con el campo y no se ejecuta | T | G1 |
| REQ-FI-08 | Solo el arquitecto tiene herramientas propias, con cuota por herramienta y turnos para usarlas, y no cuentan como herramientas de red | T | G1 |
| REQ-FI-09 | `sumar_dias` y `edad_en_fecha` calculan a la precisión que traen las fechas y avisan del calendario antes de 1582 | T | G1 |
| REQ-FI-10 | Cada invocación llega a Langfuse como `generation` con tokens y coste, en la sesión de su novela, y los scores van a la misma sesión | T | G1 |
| REQ-FI-11 | `invocar` y `decidir` abren la sesión de la novela y vacían el observador al terminar | T | G1 |
| REQ-FI-12 | Un fallo de Langfuse no tumba el nodo | T | G1 |
| REQ-FI-13 | En una novela real con claves, la sesión de Langfuse enseña el coste y los tokens totales de la novela | D | G6 |

Todos son **T** salvo REQ-FI-13. Las pruebas de REQ-FI-10 usan un cliente falso que graba lo que recibe, y la propagación de la sesión se ha comprobado a mano contra el SDK real leyendo el atributo `session.id` del span. REQ-FI-13 es **D** porque solo se demuestra enviando a un Langfuse de verdad. Se demostró el 2026-09-25 con una novela de dos capítulos: la sesión recogió 14 invocaciones, y sus tokens y su coste coincidieron con los de `storymaker estado`.

## 8. Lo que queda fuera

- **La arquitectura no recoge §4.** §5 y §12 de [`architecture.md`](../../docs/architecture.md) siguen diciendo que solo el investigador tiene herramientas.
- **La matriz consolidada.** El `trace-matrix.md` de la raíz no está en el árbol, así que los requisitos de esta spec no se han consolidado. Las pruebas de `test_matrices.py` fallan por esa ausencia, que es anterior a este cambio.
- **Los errores de mypy de `transporte_sdk.py`.** Los tipos de los hooks y de `ResultMessage.result` no cuadran con los del SDK 0.2.158. Son anteriores a este cambio, y este cambio no añade ninguno.
- **La forma de la traza.** Una traza por generación, el span por capítulo, la latencia, las herramientas y los prompts enlazados son la [spec de observabilidad](../observabilidad/spec.md). Los validadores deterministas de la pasada de Writing puntúan con `registrar_veredicto` desde `validar_determinista`.

## 9. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-25 | §7: REQ-FI-13 queda demostrado | Novela `prueba-langfuse` contra Langfuse Cloud; ver It-36 |
| 2026-09-25 | §8: lo pendiente de Langfuse pasa a la spec de observabilidad, y deja de afirmarse que los deterministas no puntúan | Ya puntúan desde `validar_determinista`; ver It-37 |
| 2026-09-25 | Primera versión: hook de validación por `stdin` (§2), hook de policy (§3), herramientas del arquitecto (§4), Langfuse v4 con sesión por novela (§5). Entran REQ-FI-01 a REQ-FI-13 | Revisión del arnés contra sus requisitos; ver It-36 en [`iteraciones.md`](../../docs/iteraciones.md) |
