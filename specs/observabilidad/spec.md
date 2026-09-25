# Spec — La traza de una generación en Langfuse

Qué cambia para que Langfuse cuente una generación de novela como pide el enunciado: una traza por generación dentro de la sesión de la novela, un span por capítulo, una `generation` por invocación de rol con su latencia y su prompt, y una observación por cada llamada a herramienta. Deriva de [`docs/architecture.md`](../../docs/architecture.md) §14 y §17, y amplía la [spec de cierre del arnés](../final/spec.md) §5 y el contrato §3.8 (`commons/obs`) de la [spec del backend](../backend/spec.md). La forma técnica exacta está en [`plan.md`](plan.md).

## 1. Qué problema resuelve

Tras It-36, Langfuse recibía una traza suelta por invocación de rol, con tokens y coste, dentro de la sesión de su novela. Cuatro cosas del enunciado no salían:

- **«Cada generación de novela es una traza.»** Una generación son seis o siete procesos de la CLI —uno por tramo entre gates—, y cada invocación de rol era su propia traza. No había forma de abrir «la generación de la versión 1» y verla entera.
- **«Cada rol y cada llamada a tool aparece como span.»** Los roles sí; las herramientas no, y el investigador hace decenas de llamadas a WebSearch y WebFetch por fase.
- **«Latencia visible por llamada, por capítulo y por novela.»** La observación se abría y se cerraba en el mismo instante: latencia cero. Y no había nada que agrupase un capítulo.
- **«Los prompts versionados, de forma que se vea qué versión produjo cada resultado.»** Ningún nodo rellenaba `prompt_version`, ninguna observación se enlazaba a su prompt y no había forma de sembrar los prompts en Langfuse.

Por el criterio de producto, nada de lo que se añade puede parar una novela: un fallo de Langfuse, o de la vía interna del SDK, se anota en el log y sigue.

## 2. La traza de una generación

### 2.1 El identificador

La **versión objetivo** de una invocación es `COALESCE(MAX(numero), 0) + 1` sobre `version_novela`: la versión que esta generación va a publicar. `invocar` la lee al abrir la novela y llama a `abrir_sesion(novela, generacion=objetivo)`.

El id de la traza es `Langfuse.create_trace_id(seed=f"{novela}·v{objetivo}")`, que es determinista y no abre conexión. Con él:

- El arranque y cada reanudación de la misma generación caen en **la misma traza**, porque la versión objetivo no cambia hasta publicar.
- Una regeneración apunta a la versión siguiente y abre **otra traza** dentro de la misma sesión.
- Una reanudación tras un `Fail` sigue en la traza de su generación.

El nombre de la traza es `«novela» · v«objetivo»`, y se propaga con `propagate_attributes(trace_name=…)` junto al `session_id`.

Sin `generacion` —un `decidir` que solo registra la decisión, o las pruebas— no hay traza fija: cada observación abre la suya en la sesión, como antes.

### 2.2 Qué cuelga de la traza

- **El span de capítulo.** Un `Span` cuyo nombre empieza por `capitulo_NN` cuelga de un span `capitulo_NN` de tipo `span`, que se crea con el primero de sus hijos en el proceso y empieza cuando empieza ese hijo. Se cierra en `cerrar()`, con fin igual al del último hijo. Si un capítulo se trabaja en dos procesos —se rehace tras un gate—, la traza tiene dos spans `capitulo_NN`: Langfuse los agrupa por nombre.
- **Las invocaciones sin capítulo** —entrevista, investigación, trama, juez— cuelgan directamente de la traza.

### 2.3 La `generation`

Cada `registrar_span` crea una observación de tipo `generation` con el payload de siempre (`usage_details`, `cost_details`, metadatos con `coste_usd_estimado_en_cliente`, U-7) y además:

- **Inicio y fin reales.** El fin es el instante de `registrar_span`, que los nodos llaman justo después de `invocar_rol`; el inicio es el fin menos `Consumo.duracion_ms`. Se fijan creando el span con el tracer interno del cliente (`_otel_tracer.start_span(start_time=…)`) en el contexto actual, para que conserve los atributos propagados. Si esa vía falla, la observación se crea por la API pública y la latencia queda a cero (U-20). `duracion_ms` viaja además en el metadato.
- **El prompt enlazado.** Si `prompt_version` es un número, la observación se crea con `prompt=get_prompt(nombre, version=…)`, donde `nombre` es `prompt_nombre` o, sin él, el `rol`. Con `local` o sin versión no se enlaza nada.

### 2.4 Las herramientas

Cada llamada a herramienta dentro de la invocación es una observación de tipo `tool`, hija de su `generation`, con:

- el nombre de la herramienta (`WebSearch`, `WebFetch`, `mcp__storymaker__sumar_dias`, …);
- la entrada serializada en JSON y recortada a 500 caracteres;
- inicio y fin: la llegada del `ToolUseBlock` y la de su `ToolResultBlock`;
- nivel `ERROR` si el resultado vino marcado como error —una llamada denegada por la cuota lo está— o si nunca llegó.

La salida no se envía (arq. §14). Las llamadas se leen del flujo de mensajes del SDK en `TransporteAgentSDK.pedir`, no de los hooks de cuota, y viajan en `Consumo.herramientas`.

## 3. `Consumo`

`Consumo` gana dos campos con valor por defecto, de modo que ninguna construcción existente cambia:

| Campo | Qué | Suma |
|---|---|---|
| `duracion_ms: int = 0` | `duration_ms` del `ResultMessage` | Se suma: con reintentos de esquema, la invocación duró lo que duraron sus intentos |
| `herramientas: tuple[LlamadaAHerramienta, ...] = ()` | Las llamadas a herramientas de la invocación | Se concatena |

Van en `Consumo` y no en `Resultado` porque es lo que los nodos ya pasan al `Span`: ponerlas ahí no obliga a tocar ningún nodo para que lleguen.

## 4. Scores

`registrar_score` envía `create_score(trace_id=…)` cuando hay traza fija, y `create_score(session_id=…)` cuando no. La firma de `Observador.registrar_score`, de `scores.registrar` y de `scores.registrar_veredicto` no cambia.

Las coincidencias del guardrail ya viajan en el detalle del *score* de `guardrail_prohibidas` que la pasada determinista emite siempre (`writing/nodos.py::validar_determinista`), junto a su fila `guardrail:prohibida` en `audit_log`. Con la traza fija, esas coincidencias quedan en la traza de la generación que las produjo.

## 5. Prompts

- `PromptDeRol` gana `nombre`, el nombre del prompt en Langfuse, que es el valor del `Perfil`.
- `RepositorioDePrompts.para` pide `get_prompt(perfil, label="production", fallback=RESPALDO[perfil])`. Si el SDK devuelve el respaldo (`is_fallback`), la versión es `local`; sin credenciales, también.
- `subir(settings)` crea en Langfuse, con la etiqueta `production`, **solo los prompts que no existen todavía**, con el texto de `RESPALDO`. Un prompt que ya existe no se toca: Langfuse es la fuente de verdad y la versión que el Autor haya editado allí manda. Devuelve qué creó y qué dejó.
- Se lanza con `uv run python -m storymaker.commons.obs.prompts subir` desde `backend/`.
- Los nodos pasan al `Span` `prompt_version` y `prompt_nombre` del prompt con el que invocaron.

## 6. Contratos

| Fichero | Qué cambia |
|---|---|
| `commons/agents/invocacion.py` | `LlamadaAHerramienta`; `Consumo.duracion_ms` y `Consumo.herramientas`, con `__add__` que suma y concatena |
| `commons/agents/transporte_sdk.py` | `pedir` recoge las llamadas a herramientas del flujo; `_consumo_de` lee `duration_ms` |
| `commons/obs/trazas.py` | `Span.prompt_nombre`, `duracion_ms` en el metadato; `capitulo_de(nombre)`; `abrir_sesion(novela, *, generacion=None)` en el protocolo y en las dos implementaciones; `ObservadorLangfuse` con traza fija, spans de capítulo, latencia, `tool` y prompt enlazado; `cerrar` cierra los spans de capítulo |
| `commons/obs/prompts.py` | `PromptDeRol.nombre`; `para` con `fallback`; `subir`; `main` |
| `commons/graph/run.py` | `invocar` abre la sesión con la versión objetivo, ya con la novela abierta |
| `intake/nodos.py`, `investigation/nodos.py`, `plotting/nodos.py`, `writing/nodos.py` | Cada `Span` lleva `prompt_version` y `prompt_nombre` |
| `publication/nodos.py` | El `Span` del juez lleva `prompt_version`. Lo cambia la sesión que lleva la validación, porque el fichero es suyo en este momento |

## 7. Requisitos

| Id | Enunciado | Clase | Gate |
|---|---|---|---|
| REQ-OB-01 | Con `generacion`, el id de traza es el determinista de `«novela»·v«generacion»`: dos observadores con la misma novela y la misma versión objetivo envían a la misma traza, y con otra versión a otra | T | G1 |
| REQ-OB-02 | `invocar` abre la sesión con la versión objetivo: 1 en una novela sin versiones, N+1 con N publicadas | T | G1 |
| REQ-OB-03 | Un span con capítulo cuelga de un span `capitulo_NN`, uno solo por capítulo y proceso, que `cerrar` termina con el fin del último hijo; un span sin capítulo cuelga de la traza | T | G1 |
| REQ-OB-04 | La `generation` empieza `duracion_ms` antes de terminar, y `duracion_ms` viaja en el metadato | T | G1 |
| REQ-OB-05 | Si la vía interna del SDK falla, la observación se crea por la API pública y el nodo sigue | T | G1 |
| REQ-OB-06 | Cada `LlamadaAHerramienta` del consumo es una observación `tool` hija de su `generation`, con entrada recortada a 500 caracteres y nivel `ERROR` si falló | T | G1 |
| REQ-OB-07 | El transporte del SDK convierte los `ToolUseBlock` y `ToolResultBlock` del flujo en `LlamadaAHerramienta`, y lee `duration_ms` | T | G1 |
| REQ-OB-08 | `Consumo.__add__` suma la duración y concatena las herramientas | T | G1 |
| REQ-OB-09 | Con versión numérica, la `generation` se enlaza al prompt `prompt_nombre` (o `rol`) en esa versión; con `local`, a ninguno | T | G1 |
| REQ-OB-10 | Con traza fija, los *scores* van a la traza; sin ella, a la sesión | T | G1 |
| REQ-OB-11 | `para` devuelve `local` cuando Langfuse entrega el respaldo, y la versión remota cuando existe | T | G1 |
| REQ-OB-12 | `subir` crea con la etiqueta `production` solo los prompts que faltan y no toca los que existen | T | G1 |
| REQ-OB-13 | Cada `Span` que emiten los nodos de Intake, Investigation, Plotting y Writing lleva la versión y el nombre del prompt con el que se invocó | T | G1 |
| REQ-OB-14 | En una novela real con claves, la sesión muestra una traza por generación con sus capítulos, sus invocaciones con latencia distinta de cero, sus herramientas y los *scores* | D | G6 |

Todos son **T**, con un cliente de Langfuse falso que graba lo que recibe, salvo REQ-OB-14, que es **D** y está pendiente de claves. La vía interna del SDK es un riesgo aceptado, U-20 en [`verification.md`](../../docs/verification.md).

## 8. Lo que queda fuera

- Los *datasets* de Langfuse para los briefs de evaluación (verification §4.2): los briefs de `evals/` están borrados en el árbol.
- La exportación OTLP nativa sigue igual: opcional y desactivada por defecto.
- Las aserciones de G6 contra la API de Langfuse siguen ensayándose contra `ObservadorNulo`.

## 9. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-25 | Primera versión: traza por generación (§2.1), span por capítulo (§2.2), latencia y prompt enlazado (§2.3), herramientas (§2.4), `Consumo` (§3), *scores* a la traza (§4) y siembra de prompts (§5). Entran REQ-OB-01 a REQ-OB-14 | Baja de arq. §14 reescrita; ver It-37 en [`iteraciones.md`](../../docs/iteraciones.md) |
