# Plan — La traza de una generación en Langfuse

La forma técnica de la [spec](spec.md): qué ficheros se tocan, con qué funciones, en qué orden y con qué prueba. Amplía los ítems FI-07 y FI-08 del [plan de cierre del arnés](../final/plan.md) sin sustituirlos.

## 1. Ítems

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **OB-01** | `LlamadaAHerramienta(nombre, entrada, inicio, fin, error)` con tiempos en segundos de época; `Consumo.duracion_ms` y `Consumo.herramientas`; `__add__` que suma y concatena | `backend/src/storymaker/commons/agents/invocacion.py` | `tests/unit/test_observabilidad.py::TestConsumo` | REQ-OB-08 |
| **OB-02** | `RegistroDeHerramientas` en `pedir`: un `ToolUseBlock` abre la llamada por su `id`, su `ToolResultBlock` la cierra con `is_error`; lo que queda abierto al terminar se cierra como error. `_consumo_de` lee `duration_ms`. `recortar(entrada)` a 500 caracteres | `backend/src/storymaker/commons/agents/transporte_sdk.py::TransporteAgentSDK.pedir`, `::_consumo_de`, `::RegistroDeHerramientas` | `test_observabilidad.py::TestRegistroDeHerramientas` | REQ-OB-07 |
| **OB-03** | `Span.prompt_nombre`; `duracion_ms` en `como_payload`; `capitulo_de(nombre)` | `backend/src/storymaker/commons/obs/trazas.py` | `test_observabilidad.py::TestSpan` | REQ-OB-04 |
| **OB-04** | `abrir_sesion(novela, *, generacion=None)` en `Observador`, `ObservadorNulo` y `ObservadorLangfuse`; `ObservadorLangfuse._traza_id` con `Langfuse.create_trace_id(seed=…)` y `_nombre_traza` | `commons/obs/trazas.py` | `test_observabilidad.py::TestTrazaDeGeneracion` | REQ-OB-01 |
| **OB-05** | `ObservadorLangfuse._iniciar(padre, *, nombre, as_type, inicio_ns, **campos)`: crea el span con `_otel_tracer.start_span(context=set_span_in_context(padre), start_time=…)` y `_create_observation_from_otel_span`; sin padre y con traza fija, el padre es `_create_remote_parent_span` y se marca `AS_ROOT`. Si algo falla, `start_observation` pública con `trace_context` | `commons/obs/trazas.py` | `TestTrazaDeGeneracion::test_sin_via_interna_se_usa_la_publica` | REQ-OB-04, REQ-OB-05 |
| **OB-06** | `registrar_span` con el padre de capítulo (`_capitulo(n, inicio_ns)`), la `generation`, sus `tool` y el fin; `cerrar` termina los capítulos con `end(end_time=…)` antes del `flush` | `commons/obs/trazas.py::ObservadorLangfuse.registrar_span`, `::cerrar` | `TestTrazaDeGeneracion` | REQ-OB-03, REQ-OB-06 |
| **OB-07** | `_prompt(span)`: `get_prompt(nombre, version=int(v))` protegido; nada con `local` o `None` | `commons/obs/trazas.py::ObservadorLangfuse._prompt` | `TestTrazaDeGeneracion::test_la_generation_se_enlaza_a_su_prompt` | REQ-OB-09 |
| **OB-08** | `registrar_score` con `trace_id` si hay traza fija y `session_id` si no | `commons/obs/trazas.py::ObservadorLangfuse.registrar_score` | `TestTrazaDeGeneracion::test_los_scores_van_a_la_traza` | REQ-OB-10 |
| **OB-09** | `PromptDeRol.nombre`; `para` con `label="production"` y `fallback`; `subir(settings)`; `main(argv)` con el subcomando `subir` | `backend/src/storymaker/commons/obs/prompts.py` | `test_observabilidad.py::TestPrompts` | REQ-OB-11, REQ-OB-12 |
| **OB-10** | `invocar` llama a `abrir_sesion(novela.stem, generacion=…)` dentro de `abrir_novela`, con `version_objetivo(db)` | `backend/src/storymaker/commons/graph/run.py::invocar`, `::version_objetivo` | `tests/integracion/test_contabilidad.py::TestUnaFilaPorFase::test_la_sesion_de_la_traza_es_la_novela` | REQ-OB-02 |
| **OB-11** | Cada nodo guarda el `PromptDeRol` y pasa `prompt_version` y `prompt_nombre` al `Span` | `backend/src/storymaker/intake/nodos.py`, `investigation/nodos.py`, `plotting/nodos.py`, `writing/nodos.py` | `tests/integracion/test_contabilidad.py::test_los_spans_llevan_su_prompt` | REQ-OB-13 |
| **OB-12** | Una novela real con claves y su sesión consultada en Langfuse | — | Demostración, pendiente | REQ-OB-14 |

## 2. Orden de trabajo

1. **OB-01**, `Consumo`. Los campos nuevos tienen valor por defecto y no rompen ninguna construcción.
2. **OB-02**, el transporte. Solo añade al `Consumo` que ya devolvía.
3. **OB-03** a **OB-08**, el observador, de una vez: la traza, el padre, la `generation`, las herramientas y los *scores* comparten `_iniciar`.
4. **OB-09**, los prompts.
5. **OB-10**, la versión objetivo en `invocar`.
6. **OB-11**, los nodos. Van al final porque solo pasan datos a campos que ya existen.

## 3. Qué se rompe mientras tanto

- `test_observabilidad.py::TestLangfuse` usa un `ClienteFalso` que solo tiene `start_observation`, `create_score` y `flush`. Sin `_otel_tracer`, `_iniciar` cae a la API pública, que es justo REQ-OB-05, así que esas pruebas siguen valiendo; las nuevas usan un cliente falso con las dos vías.
- La prueba de la sesión de `test_contabilidad.py` graba `abrir_sesion(novela)`: pasa a grabar también la generación.
- `test_matrices.py` sigue fallando por la ausencia del `trace-matrix.md` de la raíz, igual que antes.

## 4. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-25 | Primera versión, con OB-01 a OB-12 | Baja de la spec |
