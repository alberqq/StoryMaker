# Plan de implementación — Backend de StoryMaker

**Solo la forma técnica exacta**: qué fichero, qué símbolo, en qué orden y contra qué puerta se comprueba. El *qué hace* está en [`spec.md`](spec.md) y el *por qué* en [`architecture.md`](../../docs/architecture.md), que es la fuente de verdad. **Si algo de este plan contradice la arquitectura, hay que parar y preguntar al Autor.**

La correspondencia ítem a ítem entre este plan y la arquitectura vive en [`trace-matrix.md`](trace-matrix.md), y es la que garantiza que no queda ni una decisión fijada sin código que la realice ni un ítem de trabajo que nadie pidió.

---

## 1. Cómo se lee este plan

Cada ítem lleva un identificador `P-nn` que no se reutiliza jamás, el entregable, los ficheros y símbolos concretos que lo materializan, el apartado de la arquitectura del que nace y el Quality Gate que lo cubre. Los ítems se agrupan en **ocho hitos** ordenados por dependencia: un hito no empieza hasta que el anterior pasa su gate.

El criterio de corte de cada hito es el mismo: **el hito termina cuando su parte de la suite está en verde y no cuando el código existe.**

| Hito | Qué deja en pie | Gate |
|---|---|---|
| **H0** | Andamiaje, configuración y las puertas estáticas | G0, G1 |
| **H1** | La persistencia: esquema, inmutabilidad, migraciones | G1 |
| **H2** | El núcleo transversal de `commons/` | G1, G2 |
| **H3** | El grafo, su estado y la invocación | G1 |
| **H4** | Fases 1 a 3: del brief al corpus sellado | G1, G4 |
| **H5** | Fase 4: el bucle de capítulo completo | G1, G3 |
| **H6** | Fases 5 y 6: publicar y regenerar | G1, G5 |
| **H7** | Puntos de entrada, gates humanos y cierre de verificación | G1, G2, G6 |

---

## 2. H0 · Andamiaje y puertas estáticas

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-01** | Paquete Python y árbol de carpetas *package by feature*, con las seis fases, `gates/`, `api/`, `cli/` y los ocho módulos de `commons/`, gestionado con **uv** | `backend/pyproject.toml`, `backend/uv.lock`, `backend/src/storymaker/**/__init__.py` | §16.1, §16.3 | G0 |
| **P-02** | `Settings` de `pydantic-settings` con los siete grupos de claves, leído una vez y **inyectado**, nunca consultado del entorno en caliente | `commons/config.py::Settings`, `.env.example` | §19, spec §2.2 | G1 |
| **P-03** | Valores por defecto de §19 como constantes con nombre, no números sueltos en el código | `commons/config.py::Defaults` | §19 | G1 |
| **P-04** | Puerta G0 local: `ruff`, `mypy` rápido y `gitleaks` en `pre-commit` | `.pre-commit-config.yaml` | §11, verif. §6 | G0 |
| **P-05** | Puerta G1 en CI: `uv sync --frozen`, `mypy --strict`, `ruff`+`bandit`, `gitleaks` y `pip-audit` sobre `uv.lock` | `.github/workflows/ci.yml`, `mypy.ini` | §16.1, verif. §6 | G1 |
| **P-06** | Las seis reglas Semgrep: `no-update-inmutables`, `core-domain-puro`, `validador-no-es-tool`, `sin-red-fuera-del-investigador`, `pii-fuera-del-investigador`, `indice-solo-por-embeddings` | `semgrep/*.yaml` | §1, §2, §11, §15 | G1 |
| **P-07** | Andamiaje de pruebas: `pytest`, fábricas de novela temporal y **agente falso** que devuelve respuestas fijadas por rol | `tests/conftest.py`, `tests/dobles/agente_falso.py` | spec §7.1 | G1 |
| **P-129** | `inventario_del_plan`: parser de la columna «Ficheros y símbolos» de todo `specs/*/plan.md` y cotejo contra el árbol en las dos direcciones —todo módulo de `backend/src/storymaker/**` salvo los `__init__.py` tiene que estar declarado en algún ítem—, con la salida partida en **dos cubos**: «declarado y ausente», que se mira al cerrar hito, y «presente y no declarado», que se mira siempre | `tests/correspondencia/test_inventario.py` | §11e | G1 |
| **P-130** | Convención de ancla en la primera línea del docstring de cada módulo —`spec: §3.6 · arq: §11a`— y `anclas_de_procedencia`, que la comprueba **en las dos direcciones**: ancla sin apartado y apartado de §3 o §4 sin módulo que lo cite | `tests/correspondencia/test_anclas.py` | §11e | G1 |

**Lo que rompe:** nada. H0 no toca comportamiento.

---

## 3. H1 · Persistencia

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-08** | DDL de `intake_*`: `intake_brief`, `intake_texto_crudo`, `intake_dato` con `texto_crudo_id` anulable, `intake_uso_dato` | `commons/db/esquema/intake.sql` | §7 | G1 |
| **P-09** | DDL de `mundo_*`: `mundo_fuente`, `mundo_hecho` con `fase_run_id`, `cita`, `respaldo` y `dimension`, `mundo_hecho_fuente`, `mundo_entidad`, `mundo_sello` | `commons/db/esquema/mundo.sql` | §7 | G1 |
| **P-10** | DDL de `canon_*`, las nueve tablas, incluidas `canon_arco`, `canon_arco_hito` con su `escena_id` y `canon_obra.homenajeado_id` | `commons/db/esquema/canon.sql` | §7 | G1 |
| **P-11** | DDL de `plan_*`: `plan_capitulo`, `plan_escena`, `plan_beat`, `plan_escena_personaje`, `plan_anclaje` con `dato_id` anulable | `commons/db/esquema/plan.sql` | §7 | G1 |
| **P-12** | DDL de `texto_*`: `capitulo_version`, `version_novela`, `version_capitulo`, `uso_hecho`, `uso_hito`, `continuidad` | `commons/db/esquema/texto.sql` | §7 | G1 |
| **P-13** | DDL de `cronologia_evento` y `cronologia_participante`, con `origen` distinguiendo `historico` de `narrativo` | `commons/db/esquema/cronologia.sql` | §7, §11c | G1 |
| **P-14** | DDL de `arnes_*`: `fase_run`, `gate`, `incidencia`, `score`, `audit_log`, `edicion_humana`, `procedencia`, `manifiesto` | `commons/db/esquema/arnes.sql` | §7, §13 | G1 |
| **P-15** | Tablas virtuales `vec_hecho`, `vec_canon` —con sus columnas auxiliares `+tabla` y `+fila_id`— y `vec_resumen` con `capitulo_numero` y `vigente` | `commons/db/esquema/vec.sql` | §7, §16.2 | G1 |
| **P-16** | `STRICT` en toda tabla y `CHECK` sobre los siete enumerados; un valor fuera de rango **aborta la transacción** | los seis ficheros de esquema | spec §3.1 | G1 |
| **P-17** | *Triggers* `BEFORE UPDATE` y `BEFORE DELETE` con `RAISE(ABORT,…)` sobre `capitulo_version`, `fase_run`, `version_novela`, `version_capitulo` y `mundo_hecho` tras el sello | `commons/db/esquema/inmutabilidad.sql` | §2 p.5, §7 | G1 |
| **P-18** | Migraciones numeradas, versión de esquema en la novela y **negativa a abrir un esquema del futuro** | `commons/db/migraciones/`, `commons/db/apertura.py::migrar` | spec §2.3 | G1 |
| **P-19** | Apertura de novela: `PRAGMA journal_mode=WAL`, `foreign_keys=ON`, `synchronous=NORMAL`, y **carga comprobada de `sqlite-vec`** que detiene el arranque con mensaje explícito si falla | `commons/db/apertura.py::abrir_novela` | §16.2, §18 | G1 |
| **P-20** | Repositorios de dominio, uno por familia: nadie fuera de `commons/db` construye SQL contra las tablas del arnés | `commons/db/repos/*.py` | spec §3.1 | G1 |
| **P-21** | Envoltorio transaccional que **escribe el checkpoint de LangGraph y el dominio en la misma transacción**; el nodo no hace `commit` | `commons/db/transaccion.py::paso_atomico` | §1, §7 | G1 |

**Lo que rompe:** nada aún; no hay quien escriba.

---

## 4. H2 · El núcleo transversal

### 4.1 Embeddings e índices

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-22** | FastEmbed local con `paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensiones, cargado una vez por proceso | `commons/embeddings/modelo.py::vectorizar` | §16.1, §16.2 | G1 |
| **P-23** | `indexar(fila)` y `buscar(indice, consulta, k)` con KNN de `sqlite-vec` y filtrado **dentro** de la consulta por columnas de metadato; `k = 8` por defecto y **sin claves de partición** | `commons/embeddings/indice.py` | §16.2, §19 | G1 |
| **P-24** | El índice se escribe **en la misma transacción que la fila**, y es el único módulo autorizado a tocar `vec_*` | `commons/embeddings/indice.py`, regla `indice-solo-por-embeddings` | §16.2 | G1 |
| **P-25** | `vigente` de `vec_resumen` a 1 al aprobar y a 0 en la versión que sustituye; el bloque 4 pide `capitulo_numero < N AND vigente = 1` | `commons/embeddings/indice.py::marcar_vigente` | §7 | G1 |
| **P-26** | Reembedding disparado por `edicion_humana`: lo que el Autor toca se reindexa en el mismo `commit` | `commons/embeddings/reembedding.py::reindexar_edicion` | §16.2 | G1 |

### 4.2 Invocación de agentes

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-27** | `invocar_rol(rol, prompt, esquema)`: **única puerta al Agent SDK**. Fija modelo, `allowed_tools`, `max_turns` y techo por rol desde la tabla de §12, y reintenta el fallo de red o del SDK con **espera exponencial y tope declarado** antes de darlo por error del nodo | `commons/agents/invocacion.py` | §5, §12 | G1 |
| **P-28** | Guarda de presupuesto: se cuenta el prompt ensamblado y **la llamada no se emite** si excede el techo → `PresupuestoExcedido` | `commons/agents/presupuesto.py::guarda_techo` | §12 | G1 |
| **P-29** | Hook `PreToolUse` que devuelve `permissionDecision: "deny"` al agotarse la cuota de herramientas del rol | `commons/agents/hooks.py::cuota_herramientas` | §12 | G1 |
| **P-30** | Hook `PostToolUse` que reescribe el resultado con `updatedToolOutput` acotado a 10.000 tokens antes de que entre en contexto | `commons/agents/hooks.py::truncar_salida` | §12, §19 | G1 |
| **P-31** | `schema_guard`: la salida se valida contra el esquema Pydantic del rol **antes de escribir en SQLite**, con reintento que inyecta el error de validación | `commons/agents/schema_guard.py` | §11a | G3 |
| **P-32** | Tabla de techos por rol como dato, no como literal disperso: los diez techos de §12, incluidos los dos extractores, con los **45.000** de la sesión inicial del investigador como peor caso del sistema | `commons/agents/techos.py::TECHOS` | §12 | G1 |

### 4.3 El ensamblador de paquetes

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-33** | `ensamblar(novela, capitulo_n) -> Paquete`: los siete bloques en orden con sus techos, 12.000 en total | `commons/context/ensamblador.py` | §6 | G1 |
| **P-34** | Bloque 1 · Encargo: escenas, beats, objetivo, extensión, hitos de arco del capítulo y **lo que quedó pendiente en N−1**, con los **tres avisos más recientes** | `commons/context/bloques/encargo.py` | §6, §11b | G1 |
| **P-35** | Bloques 2, 4 y 5 llenados **por relevancia semántica**, con la consulta derivada mecánicamente del texto de las escenas de N | `commons/context/bloques/{canon,memoria,anclajes}.py` | §6 | G1 |
| **P-36** | Bloque 4 incluye el **texto íntegro de N−1**, no solo su resumen | `commons/context/bloques/memoria.py` | §6 | G1 |
| **P-37** | Bloque 6 · Reglas: voz, estilo, glosario, prohibidas y **la política de licencia, arcaísmo y contenido admisible** leída de `canon_obra.estilo_json` | `commons/context/bloques/reglas.py` | §4, §6 | G1 |
| **P-38** | `truncar_por_prioridad`: se corta **por la cola de la lista ya ordenada**, los anclajes explícitos entran siempre y el bloque 3 es el último que se toca | `commons/context/truncado.py` | §6 | G2 |
| **P-39** | El paquete se **persiste entero** y se enlaza desde su span de Langfuse | `commons/context/persistencia.py` | §6, §14 | G6 |

### 4.4 Core Domain de validación

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-40** | `chapter_validator.py` y `policy_checker.py` en **Python puro**: reciben datos y devuelven incidencias tipadas; nunca escriben, nunca llaman a un modelo, nunca salen a la red | `commons/validation/{chapter_validator,policy_checker}.py` | §15 | G1 |
| **P-41** | Los cinco validadores de capítulo: `nombres_exactos`, `longitud_capitulo`, `guardrail_prohibidas` con normalización de mayúsculas, acentos, plurales y variantes, `anacronismo_fechado` y `anclaje_valido` | `commons/validation/capitulo/*.py` | §11a, §15 | G3 |
| **P-42** | Los validadores de escaleta: `cobertura_anclada` contra `plan_anclaje.dato_id` y `arco_anclado` **derivado de apariciones** —≥3 escenas en `plan_escena_personaje`, arco plano admitido, homenajeado con ≥2 hitos crecientes y el último en el tercio final— | `commons/validation/escaleta/*.py` | §11a, §19 | G4 |
| **P-43** | Los validadores sobre la salida del extractor: `cobertura_capitulo` y las lecturas de `ejecucion_escaleta` y `arco_ejecutado`, ambas de severidad `aviso` | `commons/validation/extraccion/*.py` | §11a, §11b | G3 |
| **P-44** | `cobertura_personalizacion` contra `intake_uso_dato`, en el gate de Writing | `commons/validation/cobertura.py` | §11a | G5 |
| **P-45** | Las cinco funciones puras que CrossHair verifica: `normalizar`, `hay_solape_temporal`, `es_anacronico`, `truncar_por_prioridad`, `capitulos_afectados` | `commons/validation/puras.py` | spec §7.1 | G2 |
| **P-46** | Exposición del mismo Core Domain a Claude Code como *skill* y como *hook*, **sin segunda implementación** | `.claude/skills/continuity-check/`, `.claude/settings.json` | §3, §15 | G1 |
| **P-131** | `REGISTRO: dict[str, EntradaValidador]` con nombre, punto de ejecución, condición de bloqueo y **ruta de implementación como cadena**, cubriendo los once validadores de §11a. El grafo compone cada pasada filtrando por `punto` y el hook enumera desde ahí: **nadie construye una lista de validadores a mano** | `commons/validation/registro.py` | §11a, §11e | G1 |
| **P-132** | `registro_de_validadores`: cotejo por pares del `REGISTRO`, la tabla de §11a y la de §7.2 de la spec —mismo conjunto, mismo punto, misma condición de bloqueo—. **Es el único de los cuatro de §11e que bloquea junto a P-62** | `tests/correspondencia/test_registro.py` | §11e | G1 |

### 4.5 Lean y observabilidad

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-47** | Generador del fichero Lean desde `cronologia_*` y las fechas de `canon_personaje` y `mundo_entidad`, con los **cuatro invariantes verificados por `decide`** | `commons/formal/generador.py`, `lean/StoryMaker/Cronologia.lean` | §11c | G3, G5 |
| **P-48** | *Runner* de `lake build` por subproceso que devuelve veredicto e invariante violado, y **distingue el error de entorno del veredicto negativo** | `commons/formal/runner.py::verificar` | spec §3.7, §8 | G3 |
| **P-49** | Proyecto Lake con los cuatro invariantes y el *fixture* de referencia que G1 recompila | `lean/lakefile.lean`, `tests/formal/fixture_cronologia.lean` | §11c | G1 |
| **P-50** | Langfuse: **una sesión por novela** y **un span por invocación** nombrado `capitulo_07 · escritor · intento_2`, con tokens, coste y latencia del `ResultMessage` | `commons/obs/trazas.py` | §14 | G6 |
| **P-51** | Envío de *scores* de los tres tipos de validador y de **las decisiones de gate**, con `total_cost_usd` etiquetado siempre como estimación en cliente | `commons/obs/scores.py` | §13, §14 | G6 |
| **P-52** | Prompts de rol leídos de **Langfuse como fuente de verdad**, inyectados como `system_prompt`, con el id de versión en el span; las *skills* y `CLAUDE.md` se registran por hash | `commons/obs/prompts.py` | §14 | G6 |
| **P-53** | Exportación OTLP nativa **opcional**, activable por variable de entorno, de la que la observabilidad no depende | `commons/obs/otlp.py` | §14, §18 | G6 |

---

## 5. H3 · El grafo

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-54** | `EstadoNovela`, `TypedDict` total y explícito, sin `dict[str, Any]`: contador de huecos, contador de reintentos, capítulo en curso, gate abierto | `commons/graph/estado.py` | §16.3, spec §3.2 | G1 |
| **P-55** | Cableado del `StateGraph` con **los nodos nombrados igual que las acciones de PlusCal**, importando los nodos que exporta cada fase y sin que ninguna fase importe de otra | `commons/graph/construccion.py` | §9, §16.3 | G1 |
| **P-56** | Las aristas condicionales de §9, que **leen booleanos calculados en Python** y nunca la salida de un modelo | `commons/graph/aristas.py` | §1, §9 | G1 |
| **P-57** | `invocar(novela, entrada)`: avanza hasta `interrupt()` o final y devuelve nodo de parada, gate abierto y consumo. **Entre invocación e invocación no queda nada vivo** | `commons/graph/run.py::invocar` | §16.4 | G1 |
| **P-58** | `ResumeFromCheckpoint` como **arista de entrada** a cualquier nodo: un solo mecanismo para reanudar tras fallo, tras gate y tras ramificación | `commons/graph/run.py::reanudar` | §9, §10 | G1 |
| **P-59** | Cerrojo `<novela>.db.lock` tomado en exclusiva y soltado pase lo que pase; **quien llega segundo recibe `NovelaOcupada` y es rechazado, no encolado**. El huérfano que deja un proceso muerto se rompe a mano con `storymaker desbloquear` (P-113) | `commons/graph/cerrojo.py` | §16.4 | G1 |
| **P-60** | Estado `Fail` como estado declarado del grafo, no como excepción, alcanzado al agotarse los reintentos | `commons/graph/construccion.py` | §9 | G1 |
| **P-61** | Especificación PlusCal traducida a TLA+ con los `process` nombrados como los nodos, modelando **las seis fases**, con los cuatro invariantes de seguridad y la *liveness* bajo equidad débil | `spec/harness.tla`, `spec/harness.cfg` | §11d | G1 |
| **P-62** | Prueba de **identidad nodo↔acción**: iguales los nombres, e iguales el conjunto de aristas del `StateGraph` y la definición `Aristas` | `tests/contratos/test_identidad_nodos.py` | §9, spec §3.2 | G1 |
| **P-133** | Definición `Aristas` en la especificación, **de la que se deriva el `Next` que TLC explora**, para que P-62 lea cableado verificado en vez de parsear el modelo | `spec/harness.tla` | §9, §11d | G1 |
| **P-63** | TLC sobre el modelo pequeño —5 capítulos, 2 reintentos— en CI, con los contraejemplos documentados junto al cambio que provocaron | `.github/workflows/ci.yml`, `docs/contraejemplos.md` | §11d | G1 |

**Lo que rompe:** a partir de aquí el grafo existe pero sus nodos son *stubs*; la suite de integración con agente falso empieza a correr y va pasando de rojo a verde hito a hito.

---

## 6. H4 · Fases 1 a 3

### 6.1 `intake/`

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-64** | Esquema `Brief` de Pydantic con los tres bloques completos de §4 —homenajeado, mundo, obra y frontera— y `elementos_personalizacion` tipado y marcable como obligatorio | `intake/esquemas.py::Brief` | §4 | G1 |
| **P-65** | `@model_validator` de contradicciones: edad contra período, nacimiento contra `evento_ancla` **si viene relleno**, tono contra período de duelo, dato que coincide con palabra prohibida | `intake/contradicciones.py` | §4 | G1 |
| **P-66** | Cuarentena: el texto pegado entra en `intake_texto_crudo` y **no sale de ahí**; el extractor de intake produce filas tipadas con `origen = 'texto_libre_no_confiable'` | `intake/cuarentena.py`, `intake/extractor.py` | §4, §7 | G3 |
| **P-67** | Aserción de seguridad: **ninguna cadena del texto en bruto aparece jamás en el prompt del escritor**, comprobada sobre cargas de inyección | `tests/adversarias/test_inyeccion_intake.py` | §4, §15 | G1 |
| **P-68** | Nodo `intake.configure`: extracción previa, entrevistador que **solo pregunta por lo vacío o ambiguo**, `ValueError` traducido a pregunta, `intake_brief` con su `hash` | `intake/nodos.py::configure` | §4, §9 | G1 |
| **P-127** | Informe del gate de Intake: los campos que siguen vacíos tras agotar las preguntas y los elementos marcados como obligatorios. **El gate se abre igualmente**; decide el Autor | `intake/informe.py` | §10, spec §4.1 | G4 |

### 6.2 `investigation/`

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-69** | Nodo `investigation.research`: **una sesión**, las seis dimensiones del período, con **3 `WebSearch` y 3 `WebFetch`** impuestas por los hooks de P-29 y P-30 | `investigation/nodos.py::research` | §4, §19 | G1 |
| **P-70** | Escritura del hecho con enunciado, estado epistémico, fuentes mapeadas desde las referencias de `WebSearch`, `fase_run_id` y **cita de 300 caracteres como mucho** | `investigation/corpus.py` | §4, §7 | G1 |
| **P-71** | Vigencia por `fase_run_id`: rehacer escribe hechos nuevos y **no borra ni mezcla** los anteriores, que quedan como historia consultable | `commons/db/repos/mundo.py::hechos_vigentes` | §4, §8 | G1 |
| **P-72** | Nodo `investigation.verify`, que realiza el validador semántico `respaldo_fuente`: agente **sin herramientas y sin red**, por **lotes de veinte**, que escribe `respaldo` y **degrada a `inferido`** sin borrar ni bloquear | `investigation/nodos.py::verify` | §4, §11b | G4 |
| **P-73** | Informe del gate de Investigation con el **recuento de hechos por dimensión** y los `no_respaldado` destacados | `investigation/informe.py` | §4, §18 | G4 |
| **P-74** | Aislamiento de PII: el prompt del investigador se construye solo con período y lugar, con la regla `pii-fuera-del-investigador` y una aserción sobre el prompt ensamblado | `investigation/prompts.py`, `tests/adversarias/test_pii.py` | §15, spec §4.2 | G1 |

### 6.3 `plotting/`

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-75** | Nodo `plotting.plan`: el arquitecto **inventa Premisa y Tema**, puebla `canon_*` —personajes, relaciones, **arcos con sus hitos anclados a escenas**, escenarios, voz, glosario— y `plan_*` con la escaleta de capítulos → escenas → beats | `plotting/nodos.py::plan` | §4, §7 | G1 |
| **P-76** | Copia de `grado_licencia`, `arcaismo` y `contenido_admisible` a `canon_obra.estilo_json`, que es como los diales llegan al bloque 6 | `plotting/canon.py::volcar_diales` | §4 | G1 |
| **P-125** | Entrega de corpus al arquitecto **por búsqueda semántica y no volcando el corpus entero** en su ventana, con la misma consulta KNN de P-23 | `plotting/contexto.py::hechos_relevantes` | §16.2 | G1 |
| **P-77** | Nodo `plotting.fill_gap`: **una única micro-llamada** con una `WebSearch`, **tope de cinco huecos** en el estado del grafo, y `no_encontrado` que **autoriza la invención** como fila con `estado='inferido'`, `origen='invencion_autorizada'`, sin fuente y `respaldo='no_aplica'`. Estos hechos **no pasan por el verificador de respaldo**, que cerró su sesión al acabar Investigation: uno inventado no tiene fuente que comprobar y uno recién buscado no justifica una segunda ronda | `plotting/nodos.py::fill_gap` | §4 | G1 |
| **P-78** | La invención **no se topa, se cuenta**: el informe del gate de Plotting muestra el recuento de inventados **por dimensión** | `plotting/informe.py` | §4 | G4 |
| **P-79** | Nodo `plotting.seal`: hash sobre el contenido ordenado de las tablas `mundo_*` **vigentes**, fila en `mundo_sello`, y corpus de **solo lectura** a partir de ahí | `plotting/nodos.py::seal` | §4, §7 | G1 |
| **P-80** | Puerta del gate de Plotting: `cobertura_anclada`, `arco_anclado` y **Lean sobre la cronología deducida de la escaleta** —`plan_escena.fecha_narrativa`, `plan_escena_personaje` y las fechas vitales— en verde antes de abrir el gate | `plotting/gate.py` | §11a, §11c | G4 |

---

## 7. H5 · Fase 4, el bucle de capítulo

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-81** | Nodo `writing.write`: el escritor **redacta el capítulo entero de una vez**, con el paquete de P-33 como única entrada y **sin herramientas** | `writing/nodos.py::write` | §4, §5 | G1 |
| **P-82** | Nodo `writing.validate`, **pasada determinista**: los validadores de P-41 sobre el texto contra filas ya escritas, de coste cero | `writing/nodos.py::validate` | §4, §11a | G3 |
| **P-83** | Nodo `writing.extract`, **pasada del extractor**, una sola llamada y **solo si la anterior no dejó incidencias**: resumen, delta de continuidad, hechos usados, elementos usados, **eventos de cronología narrativa** y veredicto de ejecución | `writing/nodos.py::extract` | §4 | G3 |
| **P-84** | Sobre la salida del extractor corren `cobertura_capitulo`, `ejecucion_escaleta`, `arco_ejecutado` y **los cuatro invariantes de Lean sobre la cronología acumulada**, que es la que el extractor acaba de completar | `writing/validacion.py` | §4, §11c | G3 |
| **P-85** | Poblado de `uso_hecho` y `uso_hito` a granularidad de **escena**, `intake_uso_dato` y `continuidad`, todos con el `capitulo_version_id` **del intento** que los produjo | `writing/extraccion.py` | §7 | G1 |
| **P-86** | Nodo `writing.repair`: el editor recibe **el informe ya producido** y emite un parche, que entra como `capitulo_version` con `intento+1`; **dos reintentos** y después `Fail` | `writing/nodos.py::repair` | §4, §19 | G3 |
| **P-87** | Nodos `writing.approve` y `writing.checkpoint`, este último **en la misma transacción** que la aprobación, y con `vec_resumen.vigente` actualizado | `writing/nodos.py::{approve,checkpoint}` | §4, §7 | G1 |
| **P-88** | Los avisos de ejecución: **los tres más recientes** viajan al bloque 1 del capítulo siguiente, y **el del último capítulo se destaca en el informe del gate de Writing** con el hito concreto que falta | `writing/avisos.py` | §11b, §19 | G4 |
| **P-126** | Linter de prosa por **auto-similitud**: se compara el vector del capítulo recién escrito con los de los anteriores y se abre incidencia de severidad `aviso` cuando la repetición pasa del umbral declarado. **No es uno de los once validadores de §11a** y no gobierna ninguna arista: es el cuarto uso de los embeddings, y su sitio es el informe del gate | `writing/similitud.py` | §16.2 | G3 |
| **P-89** | Gate de Writing: informe con capítulos, incidencias, avisos y `cobertura_personalizacion` | `writing/gate.py` | §11a | G5 |

---

## 8. H6 · Fases 5 y 6

### 8.1 `publication/`

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-90** | Nodo `publication.judge`, que realiza `juez_rubrica`: **siete criterios 1-10 con justificación**, salida como esquema de puntuaciones y **sin permiso de escritura sobre el texto**; umbral no superado devuelve al gate de Writing | `publication/nodos.py::judge`, `publication/rubrica.yaml` | §4, §11b | G5 |
| **P-91** | Lean sobre la **cronología completa** antes de publicar: si falla, **la versión no se publica y no hay anulación** | `publication/verificacion.py` | §11c | G5 |
| **P-92** | Nodo `publication.publish`: arma el manifiesto de la **versión candidata**, renderiza la lectura contra él, corre `render_visual` **con la transacción todavía abierta** e inserta `version_novela` y `version_capitulo`; si el render falla, se deshace | `publication/nodos.py::publish` | §4, §11a | G5 |
| **P-93** | `manifiesto` con `brief_hash`, `sello_corpus_hash`, `prompts_json`, `modelos_json`, **`embeddings_json`** y `sdk_version` | `publication/manifiesto.py` | §13, §16.2 | G5 |
| **P-94** | Lectura web renderizada —índice navegable, ficha de personajes y lugares enlazada a sus capítulos, portada con dedicatoria— y **PDF impreso con `page.pdf()` desde esa misma ruta** | `publication/render.py` | §4, §16.1 | G5 |

### 8.2 `regeneration/`

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-95** | Nodo `regeneration.request`: la petición en lenguaje natural se resuelve **por búsqueda semántica** contra canon y corpus, y **el Autor confirma el candidato en el gate** | `regeneration/nodos.py::request` | §4, §16.2 | G4 |
| **P-96** | **Se modifica la fila del hecho, nunca el texto**, y queda en `audit_log` | `regeneration/cambio.py` | §2 p.4, §4 | G1 |
| **P-97** | Nodo `regeneration.invalidate`: `capitulos_afectados` sale de `uso_hecho` y de `uso_hito`; los posteriores pasan a `Invalidado` y se les corren **solo los validadores de coste cero**, Python y Lean, sin invocar al extractor | `regeneration/nodos.py::invalidate` | §4, §11c | G3 |
| **P-98** | Nodo `regeneration.regenerate` y manifiesto nuevo que **reutiliza los capítulos no tocados**; la versión anterior sobrevive entera | `regeneration/nodos.py::regenerate` | §4, §7 | G5 |
| **P-99** | Diff por **`JOIN` de dos manifiestos**: página de novedades en el PDF y distintivo en el índice web | `regeneration/diff.py` | §4 | G1 |
| **P-100** | Gate de Regeneration con el **recuento de capítulos afectados antes de pagarlos** y la opción de abortar | `regeneration/gate.py` | §18 | G4 |
| **P-101** | Edición humana directa como entrada de primera clase: fila en `edicion_humana` y en `audit_log`, **misma maquinaria que la petición del lector**, re-sello del corpus y reembedding de lo tocado | `regeneration/edicion_humana.py` | §8, §16.2 | G1 |
| **P-102** | Nodo `branch.fork`: **copiar el fichero** y escribir `procedencia` con el fichero y el `fase_run` de origen | `commons/graph/branch.py::fork` | §8 | G1 |

---

## 9. H7 · Puntos de entrada, gates y cierre

### 9.1 `gates/`

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-103** | Nodo `gates.await`: `interrupt()` de LangGraph, fila `gate` pendiente, el checkpointer persiste y **la invocación termina**. La decisión reanuda después con `Command(resume=...)`, por el mismo camino que P-58 | `gates/nodos.py::await_approval` | §10 | G4 |
| **P-104** | Las **cuatro decisiones**: aprobar, **rehacer con comentario** —el texto libre se inyecta como bloque extra en el prompt y cuenta contra el límite de reintentos—, editar y abortar | `gates/decisiones.py` | §10 | G4 |
| **P-105** | Interfaz `Notifier` con Telegram como única implementación: `httpx` contra la Bot API y **botones inline** *Aprobar · Rehacer · Abortar* | `gates/notifier.py`, `gates/telegram.py` | §10, §16.1 | G1 |
| **P-106** | Notificaciones informativas **desactivadas por defecto**, que no bloquean | `gates/notifier.py::informativa` | §10 | G1 |
| **P-107** | *Timeout* declarado que **aparca** la ejecución con estado propio; **nunca auto-aprobación** | `gates/timeout.py` | §10 | G4 |
| **P-108** | `gates_enabled = false` que los desactiva enteros para el modo batch, con el hecho registrado en el manifiesto | `gates/nodos.py`, `publication/manifiesto.py` | §10 | G2 |

### 9.2 `api/` y `cli/`

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-109** | `POST /webhook/telegram`: comprueba `X-Telegram-Bot-Api-Secret-Token`, escribe la decisión, responde en seguida y **lanza la invocación como tarea de fondo del propio proceso**. Es **idempotente**: un callback sobre un gate ya decidido responde `200` y se ignora, porque Telegram reintenta las entregas que no confirma | `api/webhook.py` | §16.4 | G1 |
| **P-110** | Los **cinco** endpoints de lectura restantes —ficha de la novela, manifiesto de una versión, texto de un capítulo, personajes y lugares, y diff de dos versiones— más `POST /novelas/{id}/cambios`, que **no toca nada** hasta el gate. Todos devuelven `404` sobre una novela, versión o capítulo inexistente | `api/lectura.py`, `api/cambios.py` | spec §5 | G1 |
| **P-111** | `GET /novelas` que **lista el directorio `proyectos/`** y abre cada fichero: no hay base de datos global de novelas | `api/novelas.py` | §16.4 | G1 |
| **P-112** | Contrato OpenAPI y Schemathesis sobre el endpoint de decisión: **una decisión malformada no reanuda el grafo** | `tests/api/test_schemathesis.py` | spec §5 | G1 |
| **P-128** | Taxonomía de errores como excepciones tipadas —`NovelaNoEncontrada`, `NovelaOcupada`, `PresupuestoExcedido`, esquema del futuro, entorno de `lake` roto, escaleta ausente del capítulo pedido— y su traducción única a mensaje de CLI y a código HTTP. **Separa incidencia de error**: la incidencia es un defecto del contenido y tiene camino de vuelta; el error es una avería y detiene la invocación | `commons/errores.py`, `api/manejadores.py`, `cli/salida.py` | §9, §16.4, spec §8 | G1 |
| **P-113** | Los siete comandos de Typer: `nueva`, `continuar`, `estado`, `ramificar`, `cambiar`, `desbloquear`, `evaluar` | `cli/comandos.py` | §16.4, spec §6 | G1 |

### 9.3 Cierre de verificación

| # | Entregable | Ficheros y símbolos | Arq. | Gate |
|---|---|---|---|---|
| **P-114** | Unitarias: un caso positivo y uno negativo **por validador de ejecución**, los siete bloques del ensamblador, la consulta de invalidación y el diff de manifiestos | `tests/unit/**` | spec §7.1 | G1 |
| **P-115** | Propiedades de Hypothesis que **reflejan los invariantes de TLA+** sobre el código real | `tests/propiedades/**` | §11d, verif. §3.6 | G1 |
| **P-116** | Las seis pruebas de contrato, entre ellas **el mismo capítulo por el nodo y por el hook de `.claude/`, exigiendo el mismo veredicto incidencia por incidencia** | `tests/contratos/**` | §15, verif. §3.8 | G1 |
| **P-117** | Integración con agente falso sobre SQLite temporal: recorrido en batch, atomicidad del checkpoint, reanudación, Fase 6, ramificación y reintentos agotados | `tests/integracion/**` | §11d, spec §7.1 | G1 |
| **P-118** | Suite adversaria determinista: inyección por texto pegado, página hostil, herramienta prohibida, exfiltración de PII y evasión del guardrail | `tests/adversarias/**` | §15, verif. §4.9 | G1 |
| **P-119** | CrossHair sobre las cinco funciones puras y **`mutmut` con mutación ≥ 80 %** en `commons/validation/` | CI nocturna | verif. §3.3, §3.7 | G2 |
| **P-120** | Evals sobre los **cinco briefs** en modo batch: cero incidencias críticas, 5/5 completan, ≥ 70 % de capítulos al primer intento | `evals/briefs/*.json`, `evals/correr.py` | verif. §4.2 | G2 |
| **P-121** | **Varianza del juez**: N ejecuciones sobre la misma novela y publicación de la desviación por criterio, con la tabla antes/después si hay que subir el rol | `evals/varianza_juez.py` | §5, §13 | G2 |
| **P-122** | `revision_humana`: una persona aplica **el mismo fichero de rúbrica** que usa el juez sobre al menos una novela completa, y una sesión de red-teaming manual por hito | `publication/rubrica.yaml`, `docs/revision-humana.md` | §11b, verif. §4.5 | G2 |
| **P-123** | Aserciones de G6 sobre la traza real consultando la API de Langfuse: span de escritor y de validación anterior a la aprobación, `intento_` dentro del límite, coste bajo presupuesto, **ningún span que no sea del investigador con `WebSearch` o `WebFetch`**, y toda decisión de gate con actor y momento | `tests/traza/test_g6.py` | §14, spec §7.2e | G6 |
| **P-124** | La evidencia final: `ejemplos/novela-ejemplo.pdf` commiteado **con su manifiesto**, que es lo que el sistema promete en lugar de reproducibilidad textual | `ejemplos/` | §13 | G6 |

---

## 10. Dependencias y qué se rompe mientras tanto

- **H1 antes que todo lo demás.** Ningún nodo se escribe contra un esquema que aún puede cambiar: el coste de rehacer una migración es menor que el de rehacer seis features.
- **P-27 antes que cualquier nodo con agente.** Si una fase llamara al SDK por su cuenta mientras `commons/agents` no existe, el techo de §12 dejaría de garantizarse por construcción y pasaría a ser una convención — que es exactamente lo que la arquitectura evita.
- **P-33 antes que P-81.** El escritor no tiene otra entrada que el paquete; sin ensamblador no hay nada que probar.
- **P-47 y P-48 antes que P-84.** Lean corre en la pasada del extractor, así que el generador tiene que existir antes que el bucle.
- **P-61, P-62 y P-133 en paralelo con H3.** La especificación TLA+ y el grafo se escriben a la vez, porque la prueba de identidad cae si uno de los dos se adelanta. `Aristas` (P-133) tiene que existir antes que P-62, o la prueba no tiene contra qué comparar el cableado.
- **P-131 y P-132 van juntos, en H2, y antes que cualquier nodo de `Validate`.** La comprobación bloqueante vive donde vive el registro y no al final: dejarla en el cierre de verificación habría permitido que la deriva corriera libre durante cinco hitos para caer en el último, que es justo cuando ya no compensa arreglarla.
- **Nadie compone una pasada con una lista propia.** Si una fase compusiera su pasada con una lista propia mientras el registro no existe, el registro pasaría a ser un inventario paralelo y la comprobación caería de clase **A** a **T** — justo lo que la decisión evita.
- **P-129 y P-130 informan desde el primer día y no bloquean nunca.** Durante H0–H6 el cubo «declarado y ausente» está lleno por definición, y es el estado normal; el que se mira mientras tanto es «presente y no declarado».
- **Entre H3 y H7 la suite de integración está en rojo**, y es el estado normal: los nodos pendientes son *stubs* que devuelven `NotImplementedError`, y cada hito los va sustituyendo. Lo que no puede estar en rojo en ningún momento es G0 ni la parte estática de G1.

---

## 11. Lo que este plan no cubre

- **El frontend de React**, sus cuatro páginas de Feature-Sliced Design y **Steiger**, el linter que verifica sus dos reglas de importación e **informa sin bloquear**. Tienen metodología propia en §16.3 de la arquitectura y les corresponde su propio `specs/frontend/`. Este plan solo garantiza que el backend le sirve lo que necesita: los siete endpoints de §9.2 y la ruta de lectura que P-94 imprime como PDF.
- **El semáforo que sumaría los techos de las micro-sesiones concurrentes del arquitecto.** La arquitectura lo describe en §12 como la salida *si algún día* se paralelizan; hoy corren en serie, `fill_gap` es un nodo secuencial del grafo y el peor caso sigue siendo un solo agente abierto. Construirlo ahora sería código sin caso de uso, y el día que lo haya bastará con el techo de 14.000 ya declarado.
- **El contenido matemático del proyecto Lean y la redacción de los invariantes TLA+**, más allá de crear los proyectos, generarlos e invocarlos (P-47 a P-49, P-61 a P-63).
- **Los prompts de rol**, que viven en Langfuse como fuente de verdad y no en el repositorio (§14).
- **Las decisiones de diseño.** Si al implementar aparece una que este plan no contempla, se sube a `architecture.md` antes de escribirla en código.

---

## 12. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-23 | Versión inicial: 124 ítems en ocho hitos, con la trazabilidad contra la arquitectura en `trace-matrix.md` | Cerrar la forma técnica exacta antes de escribir código, y dejar comprobable que ninguna decisión fijada se queda sin ítem que la realice |
| 2026-09-23 | Primera pasada de congruencia contra la spec: entra **P-128**, la taxonomía de errores y su traducción a CLI y a HTTP; P-110 deja de contar seis endpoints de lectura donde hay cinco más el de P-111; P-109 declara la idempotencia del webhook; P-27 recoge el reintento con espera exponencial ante un fallo del SDK; y P-126 aclara que no es uno de los once validadores | La spec contrataba cuatro cosas que ningún ítem recogía —§3.1, §3.3, §5 y §8—, y un recuento de endpoints que se pisaba con otro ítem. Lo que el plan no nombra, no se construye |
| 2026-09-23 | P-01 y P-05 fijan **uv** como gestor de entorno y dependencias, con `uv.lock` como el *lockfile* que audita G1 | Decisión del Autor en el recorrido del plan. Queda registrada arriba, en §16.1 de la arquitectura: el plan la cita, no la inventa |
| 2026-09-23 | Tras el primer recorrido de la matriz de trazabilidad: entran P-125 —corpus al arquitecto por búsqueda semántica—, P-126 —linter de auto-similitud entre capítulos— y P-127 —informe del gate de Intake—; P-77 declara que los hechos del arquitecto no pasan por el verificador; y §11 declara fuera de alcance Steiger y el semáforo de micro-sesiones concurrentes | Los usos 3 y 4 de los embeddings de §16.2 y el informe del primero de los cinco gates no tenían ítem, y dos piezas que la arquitectura menciona quedaban sin dueño declarado: una porque es del frontend y otra porque hoy no hace falta |
| 2026-09-23 | Entran cinco ítems para la familia §11e: **P-129** y **P-130** en H0 (inventario y anclas, informan), **P-131** y **P-132** en H2 (el `REGISTRO` como cableado y su cotejo a tres bandas, que bloquea) y **P-133** en H3 (la definición `Aristas`). P-62 pasa a comparar también aristas | La conformidad del código con la especificación no tenía ítem ni gate: se sostenía sobre que alguien leyera los documentos. Los identificadores continúan la numeración en vez de intercalarse porque un `P-nn` no se reutiliza jamás |
