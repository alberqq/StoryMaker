# Spec — La ejecución contra el modelo y la verificación de las novelas

**Qué fija este documento.** Los contratos que el backend tiene que cumplir para que una novela recorra el grafo entero **contra el modelo de verdad** —no contra el transporte falso de la suite— y el aparato con el que se comprueba que lo que sale es una novela y no solo un fichero. Deriva de [`architecture.md`](../../docs/architecture.md), que es la fuente de verdad, y completa la [spec del backend](../backend/spec.md) en lo que esta daba por supuesto: que el Agent SDK, el CLI de Claude Code, FastEmbed y Playwright se comportan como los describe su documentación.

**Por qué es una spec aparte.** La spec del backend contrata el sistema contra sí mismo, y la suite lo demuestra con dobles: 667 pruebas recorren una novela de `Configure` a `PublishVersion` sin gastar un token. Lo que este documento contrata es **la costura con lo que no controlamos**: el subproceso del CLI, sus herramientas diferidas, la forma de sus mensajes, el catálogo de modelos de FastEmbed y el navegador. Ahí ningún doble ve nada, porque el doble lo escribimos nosotros con nuestra idea de cómo se comporta lo real.

**Cómo se lee.** Cada apartado fija un contrato, sus errores y su clase de confianza. §10 enumera los requisitos con identificador propio, `REQ-ER-nn`, con el apartado del que nacen y el ítem del [plan del backend](../backend/plan.md) que los realiza. Donde el ítem todavía no existe, la columna lo dice.

---

## 1. Alcance

**Entra:**

- El transporte de producción (`commons/agents/transporte_sdk.py`) y la cuota de herramientas (`commons/agents/hooks.py`).
- El contrato de salida de los roles (`commons/agents/invocacion.py`).
- El vectorizador real (`commons/embeddings/modelo.py`).
- Los tres puntos de Lean, la escaleta anclada y el reparto de identificadores a los roles que los devuelven.
- La Fase 5 tal como corre sin gates: juez, publicación y PDF.
- La contabilidad de la invocación: consumo, `fase_run` y manifiesto.
- El aparato de verificación fuera de la ejecución: evaluaciones, varianza del juez, revisión humana y aserciones sobre la traza.
- Las condiciones de entorno de la máquina del Autor.

**No entra:**

- El frontend y sus pantallas, que tienen su propia spec.
- El contenido de los prompts de rol, que vive en Langfuse (arq. §14).
- La calidad literaria como propiedad garantizable: lo que aquí se contrata es **cómo se mide**, no que salga buena.

---

## 2. Entorno de ejecución

**Contrato.** Una novela real exige cuatro cosas de la máquina, y el arnés distingue su ausencia de un defecto de la novela:

| Pieza | Para qué | Si falta |
|---|---|---|
| CLI de Claude Code con sesión iniciada | Es la única puerta al modelo; el SDK lo lanza como subproceso y hereda su sesión | Error de entorno al primer nodo agente |
| Extra `agentes` (`claude-agent-sdk`) | El transporte de producción | Error de entorno |
| Extra `embeddings` (FastEmbed, onnxruntime) | Resúmenes, hechos y consultas del ensamblador | Error de entorno en el primer nodo que indexa |
| Extra `render` (Playwright + Chromium) | El PDF | **Aviso**: la versión se publica igual (§8) |
| `elan` y `lake` en el `PATH` | Los tres puntos de Lean | **Aviso** mientras el Autor no decida lo contrario (§6) |

**Windows con Smart App Control.** Esa política bloquea las extensiones nativas sin reputación. Las ruedas más recientes de dos dependencias lo están: `uuid-utils` 0.17, de la que depende LangGraph al importar, y el núcleo nativo de `hypothesis` 6.168. `backend/pyproject.toml` fija `uuid-utils<0.17` e `hypothesis<6.166` **solo en `win32`**, con `[tool.uv] constraint-dependencies`, de modo que Linux y la CI siguen en lo último. `mypy` no carga en esa máquina en ninguna versión, porque depende de `librt`; G1 lo ejecuta en la CI.

*Clase: **D** (se demuestra arrancando una novela en la máquina real). Gate: G2.*

---

## 3. El transporte de producción

**Contrato.** `TransporteAgentSDK.pedir` recibe el perfil, el modelo, el prompt, el prompt de sistema, las herramientas concedidas, los turnos y la cuota, y devuelve el texto de la respuesta final con su consumo. Tiene cinco obligaciones que no dependen del rol:

**3.1 Cada rol ve solo sus herramientas.** Se pasan `tools` **y** `allowed_tools` con la misma lista. `allowed_tools` solo aprueba sin preguntar y no restringe nada: sin `tools`, un rol sin herramientas recibe el juego completo de Claude Code, intenta usar alguna, el hook se la deniega y el único turno se gasta sin respuesta. Con `tools=[]` el rol no tiene nada que pedir, y el «sin permiso de escritura» del juez queda garantizado por construcción y no por el hook.

**3.2 Las herramientas llegan cargadas.** El CLI difiere `WebSearch` y `WebFetch` detrás de `ToolSearch`, y cargarlas cuesta un turno que la micro-sesión de dos (arq. §4) no tiene. El transporte lanza el subproceso con `ENABLE_TOOL_SEARCH=false`.

**3.3 Los hooks tienen la forma que el SDK exige.** Por evento, una lista de `HookMatcher`:

- **`PreToolUse`**, sin *matcher*: decide la cuota de cualquier herramienta.
- **`PostToolUse`**, con `matcher="WebFetch"`: recorta la única salida que tiene techo. Sin acotar, reescribiría la salida de otras herramientas con una forma que no es la suya.

**3.4 La salida es la respuesta final.** El texto que se devuelve es `ResultMessage.result`. Solo si viene vacío se usa la concatenación de los bloques de texto. El texto intermedio de un rol con herramientas («voy a buscar…») no es salida y no se valida.

**3.5 El consumo se lee de donde está.** El SDK entrega `usage` como diccionario. La entrada suma `input_tokens`, `cache_creation_input_tokens` y `cache_read_input_tokens`; la salida es `output_tokens`; y el coste es `total_cost_usd`, que sigue siendo una estimación en cliente y no facturación (U-7).

**Errores.**

| Situación | Respuesta |
|---|---|
| El rol agota `max_turns` | No es una avería del sistema: lo que llegó a decir pasa a `schema_guard`, que decide y reintenta con el error inyectado |
| El CLI devuelve un resultado de error por otra causa (límite de uso, sesión caducada) | Error del nodo, con el `subtype` y el texto del CLI, **no** «la salida no es JSON válido» |
| El subproceso no arranca | Error de entorno |

*Clase: **T** (forma de los hooks, cuota y lectura del consumo, con pruebas que se saltan sin el extra `agentes`) **+ D** (una llamada real por perfil). Gate: G1 y G2.*

---

## 4. La cuota de herramientas

**Contrato.** `CuotaDeHerramientas.decidir` sigue denegando tanto la herramienta agotada como la nunca concedida. Añade una sola excepción: las **herramientas de carga**, que no salen a la red ni devuelven material y solo cargan la definición de otra. Hoy solo es `ToolSearch`. Pasan sin contar, y **solo si el rol tiene alguna cuota**: a quien no puede salir a la red no le sirve cargar nada.

**Por qué importa.** Sin esta excepción, en la versión del CLI que difiere las herramientas, el investigador no puede buscar nunca: su primer paso es `ToolSearch`, el hook lo deniega por no tener cuota y el rol entrega un corpus vacío que `VerifyCorpus` pasa en un instante porque no hay nada que verificar. El sello se pone sobre nada y la novela se escribe sin detalle de época.

*Clase: **T**. Gate: G1.*

---

## 5. El contrato de salida

**Contrato.** Lo fija la arquitectura en §5 y la spec del backend en §3.3 (REQ-BE-132): `invocar_rol` adjunta al prompt el **JSON Schema del esquema del rol**, generado con `model_json_schema()` del mismo modelo contra el que valida `schema_guard`, serializado compacto y dentro de la estimación del techo. Este apartado añade lo que la primera ejecución real enseñó sobre ese contrato.

**5.1 El esquema no lleva prosa de desarrollador.** Pydantic convierte el docstring de cada clase en `description`, y así viajaban al modelo explicaciones de diseño, ejemplos de un encargo concreto y notas sobre reintentos. El contrato conserva solo las `description` declaradas con `Field(description=...)`, que son las escritas para el rol. Las de clase se eliminan al generar el esquema. Además, el esquema del entrevistador baja de unos 1.600 tokens a unos 850.

**5.2 El esquema se registra por su hash.** Junto a la versión del prompt de rol, el span y `manifiesto.prompts_json` llevan el hash del esquema serializado. Cambiar un campo cambia lo que vio el modelo, y la reproducibilidad de §13 exige que eso quede escrito.

**5.3 La forma no se describe dos veces.** Ni el prompt que construye un nodo ni el prompt de rol describen los campos de la salida. Ejemplo del conflicto que esto evita: el micro-investigador tenía la orden de «responder `no_encontrado`», mientras su esquema exige `{"encontrado": false, ...}`. El prompt dice *qué* hacer y el esquema dice *cómo* entregarlo.

**5.4 El esquema cabe en su columna.** El esquema cuenta dentro de «Prompt + skills» de la tabla de §12. Compacto y sin descripciones de clase, el mayor, el del arquitecto, ronda los 1.100 tokens frente a los 2.000 de esa columna.

*Clase: **A** (el esquema sale del modelo que valida, luego no puede divergir) **/T** (que viaja, que no lleva descripciones de clase y que su hash llega al manifiesto). Gate: G1.*

---

## 6. Lean en sus tres puntos

**Contrato.** La arquitectura (§11c) pone Lean en tres sitios:

- el gate de Plotting, sobre la cronología planificada;
- la pasada del extractor, sobre la cronología hasta el capítulo recién escrito;
- `PublishVersion`, sobre la cronología completa.

En los tres, el generador escribe `Cronologia/Generado.lean` con **solo datos** y el *runner* invoca `lake exe verificar` y lee su **código de salida**. Este apartado fija que **los tres llaman al runner**, cosa que hoy no hace ninguno.

**Veredictos.**

| Resultado | Gate de Plotting | Pasada del extractor | Publicación |
|---|---|---|---|
| Invariantes cumplidos | Pasa | Pasa | Pasa |
| Invariante violado | Incidencia bloqueante en el informe del gate | Incidencia bloqueante: vuelve al editor | **La versión no se publica**, sin anulación |
| `lake` ausente o proyecto roto | **Aviso** en el informe | **Aviso** | **Aviso** y se publica |

**Por qué el entorno ausente es aviso.** Lo manda el criterio de producto: un ejercicio académico que no corre porque falta `elan` en el portátil no demuestra nada. El aviso no se esconde: aparece en el informe del gate y en el manifiesto, en un campo `lean` con el valor `no_verificado`. Una versión publicada sin Lean se distingue siempre de una verificada.

*Clase: **A** (los invariantes, por construcción en Lean) **+ T** (que los tres puntos llaman al runner y que el entorno ausente degrada a aviso). Gate: G3 y G5.*

---

## 7. La escaleta anclada y los identificadores

**El problema.** Tres validadores de capítulo —`anclaje_valido`, `cobertura_capitulo` y `cobertura_personalizacion`— miran `plan_anclaje`. En la primera novela real esa tabla quedó vacía y los tres **aprobaron sin comprobar nada**. Hubo dos causas:

- `plotting.volcar` llamaba a `volcar_escaleta` sin los mapas de hechos y de datos, así que se descartaba cada anclaje propuesto.
- Ningún rol que devuelve identificadores los recibía: el extractor de capítulo tenía que devolver `hecho_id`, `personaje_id` o `escenario_id` a partir de un prompt que solo contenía la prosa.

**Contrato.**

**7.1 Todo identificador del esquema tiene su dominio en la entrada.** Si el esquema de salida de un rol lleva un campo que es clave foránea, el prompt de ese rol contiene la lista de valores válidos, con la clave y una etiqueta legible.

**7.2 El arquitecto ancla por clave.** El contexto de Plotting imprime cada hecho del corpus como `(#id)` y, en una sección propia, cada elemento del encargo con su clave, su marca de obligatorio y su texto: el `Brief` que va delante los trae sin identificador, y las filas de `intake_dato` —que son la verdad (arq. §7)— no redactan igual que el brief. El arquitecto ancla escenas a esas claves y `volcar_escaleta` recibe los dos mapas. Se acepta la clave (`#12`, `hecho #12`, `12`) y también el texto normalizado, porque copiar el enunciado en vez de la clave apunta a lo mismo.

Un anclaje que no resuelve es **aviso del gate de Plotting** —validador `anclaje_resuelto`—, no un descarte silencioso. No bloquea: la escena existe igual, y si lo que se pierde es un obligatorio, `cobertura_anclada` ya bloquea por su cuenta.

**7.4 El homenajeado se llama como dice el encargo.** La ficha del canon marcada como homenajeado se escribe con `nombre_homenajeado` del `Brief`, no con el nombre que proponga el arquitecto; su clave dentro de la escaleta sigue siendo la del arquitecto. En la segunda novela real el arquitecto la abrevió («Mercè Vidal» por el nombre con los dos apellidos) y, como `nombres_exactos` compara contra el canon, el nombre completo no se exigió nunca.

*Lo que queda para el Autor.* `nombres_exactos` comprueba **cómo** se escribe el nombre cuando aparece, no **que** aparezca entero. En esa misma novela el nombre de pila salió 141 veces y el completo ninguna. Exigir que aparezca al menos una vez es una decisión de producto que este documento no toma.

**7.3 El extractor recibe su escaleta.** Recibe las escenas del capítulo con sus beats y, detrás, un **catálogo de identificadores**, cada uno con su etiqueta legible:

- los **personajes y escenarios del canon entero**, y no solo los de estas escenas, porque la continuidad de un personaje que se nombra sin intervenir también es continuidad;
- los **hechos que el escritor tuvo delante**: los anclados a estas escenas más los vecinos semánticos del bloque 5, con la misma consulta. El extractor mide lo que se usó de lo que se ofreció, y un hecho que el escritor no vio no puede declararse usado;
- los **elementos de personalización del encargo entero**, porque `cobertura_personalizacion` pregunta si un obligatorio apareció en *algún* capítulo, no solo en el que lo tenía anclado;
- los **hitos de arco anclados a escenas de este capítulo**.

Todo cabe en los 6.000 tokens de contexto que §12 ya le reserva.

**El catálogo es el dominio.** `schema_guard` valida la salida con ese catálogo como contexto: un `hecho_id`, `dato_id`, `personaje_id`, `escenario_id`, participante de evento o hito que no esté en él hace la salida inválida, y el reintento de esquema inyecta el error con la lista de valores admitidos. **Ninguna escritura del volcado ve nunca un identificador fuera de dominio.**

*Por qué no basta la clave foránea.* En la segunda novela real, el extractor del capítulo 5 —sin catálogo, adivinando— devolvió un identificador que no existía. La clave foránea hizo su trabajo y abortó la transacción, pero en el peor sitio: con el capítulo ya escrito y validado, la invocación entera se detuvo y hubo que retomarla con `continuar`. Los cuatro capítulos anteriores habían dejado **una** fila en `uso_hecho` y **una** en `intake_uso_dato`, que es lo que da un modelo que acierta por casualidad los identificadores bajos. La clave foránea detecta el defecto; el catálogo lo evita, y el reintento lo corrige donde todavía es barato.

*Clase: **T** (un capítulo con anclaje no puede aprobarse sin que el extractor lo declare usado). Gate: G1 y G3.*

---

## 8. La Fase 5 sin gates

**Contrato.**

**8.1 El juez recibe la rúbrica.** Antes de la novela van las siete preguntas de `publication/rubrica.yaml`, el mismo fichero de la revisión humana. Son la continuidad, el arco, la coherencia de personajes, el ritmo, la prosa, la naturalidad de la personalización y la autenticidad de época. Recibe además la política del encargo (`canon_obra.estilo_json`) y la lista de elementos de personalización, porque tres de los siete criterios no se pueden puntuar sin ellas. Su esquema exige **exactamente siete puntuaciones, una por criterio y sin repetir**.

**8.2 En batch el umbral informa.** Con gates, una media por debajo de 6,0 vuelve al gate de Writing y el Autor decide qué rehacer. En batch nadie decide: volver a juzgar el mismo texto solo llevaría a `Fail` al segundo rechazo. La nota se registra y la versión se publica.

**8.3 El PDF va después de publicar.** Se imprime desde la misma lectura que ve el navegador, con `page.pdf()`, junto al fichero de la novela como `<novela>.v<n>.pdf`. Si Playwright o Chromium faltan, es un aviso: la versión ya está publicada y validada y el PDF se puede derivar después.

**8.4 `render_visual` es estructural.** Comprueba que la lectura trae índice, ficha y portada, que la ficha no está vacía y que la portada lleva título. La interceptación con navegador de la versión candidata que describe la arquitectura queda como riesgo aceptado en `verification.md` §5, con su mitigación: la lectura se construye desde las mismas tablas que la versión.

**Errores.**

| Situación | Respuesta |
|---|---|
| Media del juez < 6,0 con gates | Vuelta al gate de Writing |
| Media del juez < 6,0 en batch | Score registrado, se publica |
| El juez no devuelve siete criterios distintos | Salida inválida, reintento con el error inyectado |
| Render sin índice, ficha o portada | La versión no se publica |
| PDF que no se imprime | Aviso; la versión queda publicada |

*Clase: **T** (umbral en batch, rúbrica en el prompt, siete criterios) **+ D** (el PDF de una novela real). Gate: G5.*

---

## 9. Contabilidad de la invocación

**Contrato.** Lo que una invocación hizo queda escrito, aunque se interrumpa.

**9.1 Cada fase abre su `fase_run`.** Hoy solo la abre Intake, y `storymaker estado` enseña «Fase: intake» a una novela publicada. Cada fase la abre al entrar y la cierra al salir con su estado —`completada`, `fallida` o `esperando_gate`— y su consumo.

*Dos costuras que hay que cerrar antes de implementarlo.* Las encontró la segunda novela real, al ir a escribirlo:

- **El corpus se identifica por su `fase_run`.** Seis consultas de `commons/db/repos/mundo.py` filtran `mundo_hecho` por `fase_run_id`, y hoy funcionan porque todas las fases comparten la de Intake. En cuanto Plotting abra la suya, `sellar_corpus` y la lectura de hechos buscarían el corpus bajo un identificador que no lo tiene. El estado tiene que llevar **aparte el `fase_run` de Investigation** —`corpus_run_id`— y esas consultas leer de él.
- **`interrumpida` no está en el `CHECK` de `fase_run.estado`.** Los valores del esquema son `en_curso`, `esperando_gate`, `completada`, `fallida`, `aparcada` y `abortada`. Este apartado usa los del esquema en lugar de añadir uno: una fase que se detiene en un gate está `esperando_gate`, y una que revienta está `fallida`.

Hoy, además, una invocación retomada con `continuar` no marca nada si falla, porque `invocar` solo conoce la `fase_run` de un `Arranque`. Con cada fase abriendo la suya, la fila abierta es la de la fase en curso, y es esa la que se cierra como `fallida`.

**9.2 El consumo se acumula en el estado.** Todo nodo agente suma el consumo de su `Resultado` al estado del grafo, incluido el juez. `storymaker estado` y el `ResultadoInvocacion` enseñan la suma. Una novela entera no puede costar cero.

**9.3 El manifiesto está completo.** Lleva cuatro cosas, y ningún campo sale vacío por omisión:

- `prompts_json`, con la versión y el hash del esquema de cada rol (§5.2);
- `sdk_version`, leída con `importlib.metadata`;
- `gates_enabled`, tomado del **estado** de la ejecución y no de `Settings`, porque una novela en batch no se publicó con gates;
- el resultado de Lean (§6).

La versión guarda además la nota del juez en `judge_score_json`.

**9.4 La observabilidad no tumba un nodo.** Si Langfuse está configurado, el observador usa la API de la versión instalada, la 4: `start_span` y `create_score`. Un fallo al enviar una traza o un score degrada a aviso. Perder una traza no puede costar una novela.

*Clase: **T**. Gate: G1 y G6.*

---

## 10. El aparato de verificación

**Contrato.** Una novela se da por verificada cuando pasa por las cinco comprobaciones siguientes. Las cinco corren **a mano, desde una máquina con sesión de Claude Code**, porque un *runner* de CI no la tiene.

| Comprobación | Qué mide | Cómo | Criterio de hecho | Ítem |
|---|---|---|---|---|
| **Evaluaciones** | Que el sistema completa y respeta sus puertas en cinco encargos diseñados para romperlo: caso base, inyección, incoherencia temporal, prohibidas difíciles y cobertura imposible | `uv run storymaker evaluar --briefs ../evals/briefs` | Cero incidencias críticas; 5/5 completan; ≥ 70 % de capítulos al primer intento; en «cobertura imposible» el gate de Writing lo señala | P-120 |
| **Varianza del juez** | Si un juez Haiku es estable | `evals/varianza_juez.py` sobre la misma novela, N ≥ 5 | Desviación por criterio publicada; si supera la tolerancia declarada, tabla antes/después al subir el rol | P-121 |
| **Revisión humana** | Si la nota del juez significa algo | Una persona aplica `rubrica.yaml` sobre la novela entera, con el protocolo de `docs/revision-humana.md` | Acta en su §5 con las siete notas y la diferencia con el juez por criterio | P-122 |
| **Traza** | Que lo que el sistema dice que hizo es lo que hizo | `tests/traza/test_g6.py` contra la traza real de Langfuse | Span de escritor y de validación antes de cada aprobación; intentos dentro del límite; ningún rol salvo el investigador con red; toda decisión de gate con actor y momento | P-123 |
| **Evidencia** | Lo que el sistema promete en lugar de reproducibilidad textual | Copiar a `ejemplos/` el PDF de una novela real con su manifiesto | `ejemplos/novela-ejemplo.pdf` y su manifiesto commiteados, de una novela con corpus poblado y Lean verificado | P-124 |

**Orden.** La revisión humana y la varianza del juez van primero, porque son baratas y sin ellas la nota del juez no se puede leer. Las evaluaciones van cuando §4, §6 y §7 estén en pie, porque son cinco novelas enteras y medirían un sistema al que todavía le faltan puertas.

*Clase: **D** (evaluaciones y evidencia) **+ I** (revisión humana) **+ T** (traza). Gate: G2 y G6.*

---

## 11. Requisitos

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-ER-01 | La ausencia de una pieza de entorno se distingue de un defecto de la novela: la de Playwright o de `lake` es aviso; la del CLI, del SDK o de FastEmbed es error de entorno | §2 | P-48, P-94, P-128 |
| REQ-ER-02 | En Windows, las dependencias nativas que Smart App Control bloquea se fijan a versiones que cargan, solo en `win32` | §2 | P-01 |
| REQ-ER-03 | Cada rol ve solo sus herramientas: el transporte pasa `tools` y `allowed_tools` con la misma lista | §3.1 | P-27 |
| REQ-ER-04 | `WebSearch` y `WebFetch` llegan cargadas desde el primer turno | §3.2 | P-27, P-77 |
| REQ-ER-05 | Los hooks se entregan como listas de `HookMatcher`, con `PostToolUse` acotado a `WebFetch` | §3.3 | P-29, P-30 |
| REQ-ER-06 | La salida de un rol es `ResultMessage.result`; el texto intermedio no se valida | §3.4 | P-27, P-31 |
| REQ-ER-07 | El consumo se lee del diccionario `usage`, incluidos los tokens de caché | §3.5 | P-27, P-50 |
| REQ-ER-08 | Agotar `max_turns` entrega a `schema_guard` lo que el rol llegó a decir; cualquier otro resultado de error del CLI es error del nodo con su causa | §3 | P-27, P-31 |
| REQ-ER-09 | `ToolSearch` pasa sin gastar cuota solo para los roles con alguna cuota de red | §4 | P-29 |
| REQ-ER-10 | El esquema adjunto al prompt no lleva las descripciones de clase de Pydantic | §5.1 | P-27 |
| REQ-ER-11 | El hash del esquema de cada rol viaja al span y a `manifiesto.prompts_json` | §5.2 | P-27, P-52, P-93 |
| REQ-ER-12 | Ningún prompt de nodo ni de rol describe los campos de la salida | §5.3 | P-27, P-52 |
| REQ-ER-13 | El esquema cuenta dentro de la columna «Prompt + skills» de su techo | §5.4 | P-28, P-32 |
| REQ-ER-14 | Los tres puntos de Lean —gate de Plotting, pasada del extractor y publicación— llaman al runner | §6 | P-48, P-80, P-84, P-91 |
| REQ-ER-15 | Un invariante violado bloquea en los tres puntos; en la publicación, sin anulación | §6 | P-80, P-84, P-91 |
| REQ-ER-16 | `lake` ausente es aviso en los tres puntos y queda como `no_verificado` en el manifiesto | §6 | P-48, P-93 |
| REQ-ER-17 | Todo identificador del esquema de un rol tiene su dominio en el prompt de ese rol | §7.1 | P-75, P-83 |
| REQ-ER-18 | `volcar_escaleta` recibe los mapas de hechos y de datos, y el arquitecto ve los elementos del encargo con su clave; un anclaje que no resuelve es aviso `anclaje_resuelto` del gate de Plotting | §7.2 | P-75, P-80 |
| REQ-ER-31 | La ficha del homenajeado en el canon lleva `nombre_homenajeado` del `Brief`, no el nombre del arquitecto | §7.4 | P-75 |
| REQ-ER-19 | El extractor de capítulo recibe las escenas de su capítulo con sus beats y el catálogo de §7.3 —personajes y escenarios del canon, hechos que vio el escritor, elementos del encargo e hitos del capítulo—, dentro de su techo | §7.3 | P-83, P-85 |
| REQ-ER-30 | `schema_guard` valida la salida del extractor contra ese catálogo; un identificador fuera de dominio es salida inválida y se reintenta con el error, y nunca llega al volcado | §7.3 | P-31, P-83 |
| REQ-ER-20 | El juez recibe la rúbrica, la política del encargo y los elementos de personalización antes de la novela | §8.1 | P-90 |
| REQ-ER-21 | El esquema del juez exige exactamente siete puntuaciones, una por criterio | §8.1 | P-90 |
| REQ-ER-22 | En batch, una media del juez por debajo del umbral se registra y no impide publicar | §8.2 | P-90 |
| REQ-ER-23 | El PDF se imprime tras publicar, junto al fichero de la novela, y su fallo es aviso | §8.3 | P-94 |
| REQ-ER-24 | `render_visual` comprueba índice, ficha no vacía y portada con título; la interceptación con navegador es riesgo aceptado con fila en `verification.md` §5 | §8.4 | P-92 |
| REQ-ER-25 | Cada fase abre y cierra su `fase_run` con estado y consumo | §9.1 | P-60 |
| REQ-ER-26 | Todo nodo agente, juez incluido, suma su consumo al estado | §9.2 | P-57 |
| REQ-ER-27 | El manifiesto lleva `prompts_json`, `sdk_version`, `gates_enabled` del estado y el resultado de Lean; la versión guarda la nota del juez | §9.3 | P-93 |
| REQ-ER-28 | El observador de Langfuse usa la API de la versión instalada, y un fallo de envío degrada a aviso | §9.4 | P-50, P-51 |
| REQ-ER-29 | Las cinco comprobaciones de §10 se ejecutan en el orden declarado y dejan su resultado escrito | §10 | P-120, P-121, P-122, P-123, P-124 |

---

## 12. Clases de confianza, en una tabla

| Pieza | Clase | Gate |
|---|---|---|
| Entorno de ejecución | D | G2 |
| Transporte: herramientas, carga, hooks, salida y consumo | T + D | G1, G2 |
| Cuota con herramientas de carga | T | G1 |
| Contrato de salida | A / T | G1 |
| Lean en sus tres puntos | A + T | G3, G5 |
| Escaleta anclada e identificadores | T | G1, G3 |
| Fase 5 sin gates | T + D | G5 |
| Contabilidad | T | G1, G6 |
| Aparato de verificación | D + I + T | G2, G6 |

Ninguna pieza introduce un camino que publique una versión sin validar. Las dos que ablandan una puerta —el umbral del juez en batch y Lean sin entorno— lo hacen **dejándolo escrito en el manifiesto**, de modo que la versión publicada dice cómo se publicó.

---

## 13. Lo que este documento deja fuera a propósito

- **Subir de modelo algún rol.** La arquitectura lo prevé como una línea del frontmatter y exige medirlo antes. Aquí solo se contrata la medición (§10).
- **La longitud de capítulo y el techo de salida del escritor.** Son valores por defecto de §19 de la arquitectura, y cambiarlos es una decisión de producto, no de costura.
- **Los prompts de rol.** Viven en Langfuse; este documento solo exige que no describan la forma de la salida (§5.3).

---

## 14. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | §7.2 añade los elementos del encargo con clave al contexto del arquitecto, acepta clave o texto y hace del anclaje sin resolver un **aviso** del gate; entra §7.4 con REQ-ER-31 y queda anotada para el Autor la presencia del nombre completo | La segunda novela real salió con `plan_anclaje` vacía, como la primera, y con la homenajeada abreviada en el canon: el nombre completo no apareció en ninguno de los diez capítulos |
| 2026-09-24 | §9.1 cambia `interrumpida` por los estados que el esquema admite y declara dos costuras previas: el corpus identificado por su `fase_run` y el fallo de una invocación retomada | Al ir a implementarlo apareció que seis consultas de `mundo` dependen de que todas las fases compartan una `fase_run`: abrir una por fase sin separar el corpus rompería el sello |
| 2026-09-24 | §7.3 fija el **catálogo** del extractor —canon entero, hechos que vio el escritor, encargo entero e hitos del capítulo— y lo convierte en dominio de `schema_guard`; entra REQ-ER-30 | La segunda novela real se detuvo en el capítulo 5 por una clave foránea: el extractor adivinaba identificadores. Restringir el catálogo a lo anclado habría dejado sin dominio la continuidad de quien no interviene y la cobertura de un obligatorio fuera de su capítulo |
| 2026-09-24 | Versión inicial | Contratar la costura con el CLI, el SDK, FastEmbed, Playwright y Lean, que la spec del backend daba por supuesta y ningún doble de la suite puede comprobar, y fijar con qué se verifica una novela terminada |
