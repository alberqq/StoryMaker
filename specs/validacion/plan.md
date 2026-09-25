# Plan — Validación de la novela antes de publicar

La forma técnica de la [spec](spec.md): qué ficheros se tocan, con qué funciones, en qué orden y con qué prueba. Amplía los ítems del [plan del backend](../backend/plan.md) para `publication`, `writing`, `gates`, `commons/formal` y `formal/tla` sin sustituirlos.

## 1. Ítems

### 1.1 El render y el rechazo

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **VA-01** | `_lectura(db, filas)` común; `construir_lectura` y `construir_lectura_candidata` sobre ella; `estructura`; `en_navegador` con Playwright, ventana 1000 × 1200 y `None` si no hay navegador; `render_visual` asíncrono que junta las dos mitades | `backend/src/storymaker/publication/render.py` | `tests/unit/test_validacion_de_la_novela.py::TestRenderEnNavegador`, `tests/unit/test_publicacion.py::TestRenderVisual` | REQ-VA-01, REQ-VA-02, REQ-VA-03, REQ-VA-04 |
| **VA-02** | `PublicacionRechazada` con `incidencias`; `publicar` corre las dos comprobaciones, puntúa con `registrar_veredicto` y escribe solo si pasan; `capitulos_citados`; `registrar_rechazo`; `publish` según spec §3.2 | `backend/src/storymaker/publication/nodos.py` | `tests/integracion/test_publicacion_rechazada.py`, `test_validacion_de_la_novela.py::TestRechazoDeLaPublicacion` | REQ-VA-05, REQ-VA-10 |
| **VA-03** | Las dos aristas en `ARISTAS`; `tras_publish`; `add_conditional_edges("PublishVersion", ...)` en lugar de la arista fija | `backend/src/storymaker/commons/graph/aristas.py`, `commons/graph/construccion.py` | `test_validacion_de_la_novela.py::TestRechazoDeLaPublicacion::test_la_arista_sigue_el_tope_del_juez`, `tests/contratos/test_identidad_nodos.py` | REQ-VA-06, REQ-VA-22 |

### 1.2 El gate de Writing y el escritor

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **VA-04** | `QUE_DEVUELVEN_CAPITULOS` e `incidencias_que_devuelven_capitulos` | `backend/src/storymaker/commons/db/repos/arnes.py` | Las de VA-05 y VA-07 | REQ-VA-07, REQ-VA-08 |
| **VA-05** | `InformeDeWriting.rechazos` y su texto; `revisar`; `capitulos_a_rehacer`; `motivos_para` | `backend/src/storymaker/writing/gate.py` | `test_validacion_de_la_novela.py::TestRechazoDeLaPublicacion`, `::TestCoberturaEnElGate` | REQ-VA-07, REQ-VA-09 |
| **VA-06** | `await_approval` llama a `revisar` en `AwaitApproval4`, en batch y en la primera pasada; `_rehace_writing` y `_rehacer_writing`; `_resumen` de `AwaitApproval4` con el informe del manuscrito | `backend/src/storymaker/gates/nodos.py` | `tests/integracion/test_publicacion_rechazada.py`, `tests/integracion/test_extremo_a_extremo.py` | REQ-VA-07, REQ-VA-09 |
| **VA-07** | `motivos_para_rehacer` en el bloque 1, entre los fijos | `backend/src/storymaker/commons/context/bloques.py` | `test_validacion_de_la_novela.py::TestRechazoDeLaPublicacion::test_el_motivo_viaja_al_encargo_del_capitulo_que_cita` | REQ-VA-08 |

### 1.3 El juez y la revisión humana

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **VA-08** | `Criterio.TONO`; la pregunta de `tono`; «ocho» en el prompt del juez; `prompt_version` en su Span | `backend/src/storymaker/publication/esquemas.py`, `publication/rubrica.yaml`, `publication/nodos.py::juzgar` | `test_publicacion.py::TestJuez` | REQ-VA-11 |
| **VA-09** | `criterios`, `hoja`, `leer_hoja`, `notas_del_juez`, `registrar_revision`, `Acta`, `Fila`, `HojaInvalida` | `backend/src/storymaker/publication/revision_humana.py` | `test_validacion_de_la_novela.py::TestRevisionHumana` | REQ-VA-12, REQ-VA-13, REQ-VA-14 |
| **VA-10** | El sub-Typer `revision` con `hoja` y `registrar` | `backend/src/storymaker/cli/comandos.py` | Sin prueba en la suite: son envoltorios de VA-09 | REQ-VA-12, REQ-VA-14 |
| **VA-11** | La primera revisión de una novela completa y su acta | `docs/revision-humana.md` §5 | Inspección, pendiente | REQ-VA-15 |

### 1.4 Lean y la Trama

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **VA-12** | `lean_activo`; `verificar_cronologia` según spec §6.1 | `backend/src/storymaker/commons/formal/cronologia.py` | `test_validacion_de_la_novela.py::TestLeanEnCopia::test_lean_decide_y_python_explica` | REQ-VA-16, REQ-VA-18 |
| **VA-13** | `verificar(novela, *, proyecto=None)` con copia temporal; `_ejecutar` | `backend/src/storymaker/commons/formal/runner.py` | `TestLeanEnCopia::test_no_pisa_el_generado_del_repositorio` | REQ-VA-17 |
| **VA-14** | `STORYMAKER_LEAN=0` por defecto | `backend/tests/conftest.py` | La suite | REQ-VA-18 |
| **VA-15** | `comprobar_cronologia` con `validador`; `PUNTUADOS_EN_LA_TRAMA`; `puntuar` al final de `revisar` | `backend/src/storymaker/plotting/gate.py` | `tests/unit/test_revision_de_la_trama.py` | REQ-VA-10 |
| **VA-16** | El *score* de `cronologia_capitulo` en `extraer`, y la `propuesta` en el filtro del intento | `backend/src/storymaker/writing/nodos.py::extraer` | `tests/unit/test_escritura.py::TestCronologiaEnElExtractor` | REQ-VA-10 |
| **VA-17** | `resolver_escenario` y su uso en `volcar_escaleta` | `backend/src/storymaker/plotting/escaleta.py` | `test_validacion_de_la_novela.py::TestEscenarioDeLaEscena` | REQ-VA-19 |

### 1.5 El modelo

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **VA-18** | Constantes, variables y `entorno`; `Mueve` con `vivo`; `Caida`, `ResumeFromCheckpoint`, `Reintentar`; las dos aristas y las tres ramas de `PublishVersion`; `RehacerWriting` e `IdleRequest` según spec §8 | `formal/tla/harness.tla` | TLC | REQ-VA-20, REQ-VA-22 |
| **VA-19** | `harness.cfg` con todo y `harness_batch.cfg` | `formal/tla/harness.cfg`, `formal/tla/harness_batch.cfg` | TLC sobre las dos | REQ-VA-20 |
| **VA-20** | La mutación de `SF` a `WF`, en una copia fuera del repositorio | — | TLC, con la violación de `Termina` como resultado esperado | REQ-VA-21 |

## 2. Orden de trabajo

1. **VA-18 y VA-19**, el modelo. Va primero porque es la que decide si la arista de rechazo termina: si TLC encontrara un ciclo, la forma del resto cambiaría. Después, **VA-20**, para saber que la comprobación de `Termina` no es vacía.
2. **VA-03**, las aristas. Rompe `test_identidad_nodos` hasta que el modelo tenga las mismas, y por eso va detrás de VA-18.
3. **VA-01**, el render. `render_visual` pasa a ser asíncrono, así que las pruebas de `TestRenderVisual` cambian a la vez.
4. **VA-02**, el rechazo. Depende de VA-01 (`construir_lectura_candidata`) y de VA-03 (`tras_publish`).
5. **VA-04, VA-05, VA-06 y VA-07**, el camino de vuelta, en ese orden: la consulta, el informe, el gate y el paquete.
6. **VA-08**, el octavo criterio.
7. **VA-09 y VA-10**, la revisión humana.
8. **VA-12, VA-13 y VA-14** juntas: sin VA-14, en una máquina con `lake` la suite arrancaría Lean en cada prueba.
9. **VA-15, VA-16 y VA-17**, la Trama y el extractor.
10. **VA-11**, cuando una persona haya leído la novela.

## 3. Qué se rompe mientras tanto

- **Entre VA-03 y VA-18, `test_identidad_nodos` falla**, por construcción: es la prueba que vigila que el grafo y el modelo sean la misma máquina.
- **Con VA-01, la suite abre Chromium** en las pruebas que publican, y pasa de un minuto a casi dos. Sin Chromium instalado, esas pruebas siguen pasando, porque la novela no se para.
- **Con VA-08, una novela en curso cuyo juez ya puntuó siete criterios** tiene una nota que `completa` da por incompleta. Solo afecta a juicios anteriores al cambio, y la media se sigue calculando igual.
- `test_matrices.py` sigue fallando por la ausencia del `trace-matrix.md` de la raíz, igual que antes del cambio.

## 4. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-25 | Primera versión, con VA-01 a VA-20 | Baja de la spec |
