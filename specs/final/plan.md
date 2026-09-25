# Plan — Cierre del arnés: hooks, herramientas y coste por novela

La forma técnica de la [spec](spec.md): qué ficheros se tocan, con qué funciones, en qué orden y con qué prueba. Amplía los ítems del [plan del backend](../backend/plan.md) para `commons/agents`, `commons/validation` y `commons/obs` sin sustituirlos.

## 1. Ítems

### 1.1 Los hooks de `.claude/`

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **FI-01** | `leer_evento(entrada)`, `ruta_del_evento(evento)`, `es_capitulo(ruta)` y `salida_en_utf8()`. `main(argumentos, entrada)` lee la ruta del argumento o del evento; fuera de un capítulo devuelve 0; si bloquea, escribe el informe en `stderr` y devuelve `BLOQUEA` | `backend/src/storymaker/commons/validation/cli_hook.py` | `tests/contratos/test_hooks_de_claude.py::TestHookDeValidacion` | REQ-FI-01, REQ-FI-02, REQ-FI-03 |
| **FI-02** | `texto_introducido(evento)` junta `content`, `new_string` y los `new_string` de `edits`; `revisar_edicion(texto, ruta_contexto)` construye un `CapituloEnRevision` con las prohibidas del contexto y llama a `guardrail_prohibidas`; `main(entrada)` deniega con 2 y el motivo en `stderr` | `backend/src/storymaker/commons/validation/cli_policy.py` | `test_hooks_de_claude.py::TestHookDePolicy` | REQ-FI-04, REQ-FI-05 |
| **FI-03** | `PreToolUse` y `PostToolUse` sobre `Write\|Edit\|MultiEdit`, con `cd "$CLAUDE_PROJECT_DIR/backend" && uv run --quiet python -m …` y sin argumentos | `.claude/settings.json` | `test_hooks_de_claude.py::test_la_configuracion_declara_los_dos_hooks` | REQ-FI-06 |

### 1.2 Las herramientas del arquitecto

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **FI-04** | `EntradaSumarDias` y `EntradaEdad` con `extra="forbid"`; `sumar_dias`, `edad_en_fecha`; `Herramienta` con `calificado` y `json_schema()`; `HERRAMIENTAS_PROPIAS`; `ejecutar`, que valida y nunca lanza; `es_propia`; `servidor_mcp`, con `tool` y `create_sdk_mcp_server` importados en perezoso | `backend/src/storymaker/commons/agents/herramientas.py` | `tests/unit/test_herramientas.py::TestEsquema`, `::TestCalculo`, `::test_el_servidor_mcp_se_construye_con_el_sdk` | REQ-FI-07, REQ-FI-09 |
| **FI-05** | `PROPIAS` y `propias_de`; la cuota del arquitecto en `TECHOS` y sus 6 turnos en `TURNOS`; `invocar_rol` pasa `herramientas_de + propias_de`; el respaldo del prompt del arquitecto las menciona | `backend/src/storymaker/commons/agents/techos.py`, `commons/agents/invocacion.py::invocar_rol`, `commons/obs/prompts.py::RESPALDO` | `test_herramientas.py::TestConcesion`, `tests/unit/test_agentes.py::TestTechos` | REQ-FI-08 |
| **FI-06** | `pedir` separa las propias de las integradas: `tools` con las integradas, `allowed_tools` con todas y `mcp_servers` con el servidor `storymaker` cuando hay propias | `backend/src/storymaker/commons/agents/transporte_sdk.py::TransporteAgentSDK.pedir` | Sin prueba en la suite: el transporte real no se ejercita (ver su docstring). Se comprueba en la primera Ejecución real | REQ-FI-08 |

### 1.3 Langfuse

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **FI-07** | `Span.como_payload()` con `usage_details` y `cost_details`; `ObservadorLangfuse.registrar_span` con `propagate_attributes` y `start_observation(as_type="generation")`, `registrar_score` con `create_score(session_id=…)`, los dos protegidos con `_log.warning`; `construir(settings, *, novela=None)` | `backend/src/storymaker/commons/obs/trazas.py` | `tests/unit/test_observabilidad.py::TestLangfuse`, `::TestSpan` | REQ-FI-10, REQ-FI-12 |
| **FI-08** | `invocar` llama a `abrir_sesion(novela.stem)` y envuelve el cerrojo en `_vaciando(observador)`; `decidir` construye con `novela=ruta.stem` y cierra | `backend/src/storymaker/commons/graph/run.py::invocar`, `::_vaciando`, `cli/comandos.py::decidir` | `tests/integracion/test_contabilidad.py::TestUnaFilaPorFase::test_la_sesion_de_la_traza_es_la_novela`, `test_observabilidad.py::TestLangfuse::test_construir_con_novela_abre_la_sesion` | REQ-FI-11 |
| **FI-09** | `langfuse>=4.0`, y `uv.lock` con el nuevo especificador | `backend/pyproject.toml`, `backend/uv.lock` | — | REQ-FI-10 |
| **FI-10** | Una novela real con claves de Langfuse, y la sesión consultada en su interfaz | — | Demostración, pendiente | REQ-FI-13 |

## 2. Orden de trabajo

1. **FI-04**, las herramientas en sí. No dependen de nada y se prueban sin el SDK.
2. **FI-05** y **FI-06**, la concesión y el transporte. FI-05 no rompe nada de la suite, porque `TransporteFalso` ignora las herramientas y `herramientas_de` sigue devolviendo lo mismo.
3. **FI-07**, el observador. Cambia `como_payload`, así que las pruebas de `TestSpan` que miraban `usage` se revisan a la vez. Solo miraban `metadata`, y siguen valiendo.
4. **FI-08**, la sesión y el vaciado. Depende de FI-07 solo en que `construir` acepte `novela`.
5. **FI-09**, la dependencia.
6. **FI-01** y **FI-02**, los dos ejecutables de los hooks. FI-02 importa de FI-01.
7. **FI-03**, la configuración, al final. Mientras los ejecutables no existen, un hook que los llamara fallaría en cada edición de la sesión.

## 3. Qué se rompe mientras tanto

- Entre FI-05 y FI-06, el perfil `arquitecto` pediría al SDK real unas herramientas `mcp__storymaker__*` sin servidor que las sirva. Los dos ítems van juntos.
- Con FI-03 activo, **cada `Write` y cada `Edit` de una sesión de Claude Code en este repositorio lanza dos `uv run`**. Fuera de los capítulos salen enseguida con 0, pero pagan el arranque del intérprete.
- `test_matrices.py` sigue fallando por la ausencia del `trace-matrix.md` de la raíz, igual que antes del cambio.

## 4. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-25 | Primera versión, con FI-01 a FI-10 | Baja de la spec |
