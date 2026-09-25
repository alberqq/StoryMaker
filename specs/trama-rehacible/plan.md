# Plan — La Trama que se puede rehacer

La forma técnica de la [spec](spec.md): qué ficheros se tocan, con qué funciones, en qué orden y con qué prueba. Amplía los ítems `P-75`, `P-77`, `P-80` y `P-105` del [plan del backend](../backend/plan.md) sin sustituirlos. Si algo de aquí contradice a la arquitectura o a las specs, se para y se pregunta.

## 1. Ítems

### 1.1 El esquema

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **TR-01** | `canon_obra.fase_run_id` en `canon.sql` y en `COLUMNAS_ADITIVAS`; `plan_hueco` en `plan.sql` y en `TABLAS_ADITIVAS`, que `_anadir_columnas` crea al abrir si falta. Una columna aditiva de una tabla que no existe no se añade: la creará el esquema | `backend/src/storymaker/commons/db/esquema/canon.sql`, `commons/db/esquema/plan.sql`, `commons/db/apertura.py::_anadir_columnas` | `tests/unit/test_persistencia.py::TestColumnasAditivas` | REQ-TR-02, REQ-TR-08 |

### 1.2 Los huecos

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **TR-02** | `HuecoPropuesto` —`pregunta`, `escena`, `dimension`, `si_no_se_encuentra`— con un `model_validator(mode="before")` que convierte el texto suelto y cae a `cultura_material` ante una dimensión desconocida; `SalidaArquitecto.huecos: list[HuecoPropuesto]` | `backend/src/storymaker/plotting/esquemas.py` | `tests/integracion/test_trama_rehacible.py::TestHuecosAnclados` | REQ-TR-08 |
| **TR-03** | Repositorio de huecos: `registrar_hueco`, `hueco`, `cerrar_hueco` —que guarda hecho y resultado y ancla el hecho a la escena del hueco—, `huecos_de_la_trama`, y los auxiliares de la reparación `anclar_dato` y `escenas_con_texto`, que devuelve también `fecha_narrativa` | `backend/src/storymaker/commons/db/repos/plan.py` | `test_trama_rehacible.py::TestHuecosAnclados` | REQ-TR-08, REQ-TR-09 |
| **TR-04** | `FORMA_DE_LOS_HUECOS` en el prompt del arquitecto, con la regla de no atribuir nada a personajes históricos; `volcar` devuelve clave de escena → identificador y pasa el dueño a `volcar_canon`, y deja de repetir `volcar_prohibidas`; `plan` registra los huecos hasta `settings.huecos_por_plotting` y deja sus identificadores en `huecos_pendientes`; `fill_gap` lee el hueco, llama a `cubrir_hueco` con su dimensión y su propuesta, y lo cierra | `backend/src/storymaker/plotting/nodos.py::plan`, `::fill_gap`, `::registrar_hueco`, `::volcar`, `plotting/canon.py::volcar_canon` | `test_trama_rehacible.py::TestHuecosAnclados` | REQ-TR-08, REQ-TR-09 |
| **TR-05** | `cubrir_hueco(..., propuesta="")`: lo inventado se escribe con la propuesta y, sin ella, con la pregunta | `backend/src/storymaker/plotting/nodos.py::cubrir_hueco` | `test_trama_rehacible.py::test_lo_no_encontrado_entra_con_la_propuesta_y_no_con_la_pregunta`, `tests/unit/test_firmeza_en_el_flujo.py` | REQ-TR-09 |

### 1.3 La revisión

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **TR-06** | `evaluar(novela) -> Veredicto`: I1 a I4 en Python sobre `NovelaLean`, con avisos `cronologia_escaleta` que dicen quién, dónde y cuándo; el lugar 0 no cuenta para I3 | `backend/src/storymaker/commons/formal/evaluacion.py::evaluar` | `tests/unit/test_revision_de_la_trama.py::TestCronologiaSinLean` | REQ-TR-07 |
| **TR-07** | `NACIMIENTO_DESCONOCIDO` y `nacimiento_de` en `generador`; `cronologia_de_la_escaleta` y `cronologia_completa` los usan para quien no tiene fecha; `comprobar_cronologia` corre Lean si hay `lake` —con sus incidencias rebajadas a aviso— y `evaluar` si no o si Lean falla | `backend/src/storymaker/commons/formal/generador.py`, `plotting/gate.py::cronologia_de_la_escaleta`, `::comprobar_cronologia`, `publication/nodos.py::cronologia_completa` | `test_revision_de_la_trama.py::test_sin_fecha_de_nacimiento_no_nace_en_1800`, `tests/unit/test_trama_anclada.py::TestNacimientoDeEpoca`, `tests/integracion/test_trama_rehacible.py::TestRevisionGuardada` | REQ-TR-07, REQ-TR-15 |
| **TR-08** | `reparar_cobertura(db, vectorizador)`: cada obligatorio sin anclar, a la escena de mayor coseno entre las que devuelve `escenas_de_su_fecha`, con el evento ancla buscado por `evento_ancla` y `fecha_evento_ancla` del encargo; su aviso `cobertura_reparada` | `backend/src/storymaker/plotting/gate.py::reparar_cobertura`, `::escenas_de_su_fecha`, `::_anios_y_meses`, `::_evento_ancla_con_fecha` | `test_revision_de_la_trama.py::TestCoberturaReparada`, `test_trama_anclada.py::TestReparacionConFecha` | REQ-TR-06 |
| **TR-09** | `revisar(db, vectorizador)`: retira lo anterior salvo `ESCRITOS_POR_EL_VOLCADO`, repara, comprueba, evalúa la cronología y lo inventado, y guarda; `incidencias_guardadas` y `retirar_incidencias` sobre `VALIDADORES_DE_LA_TRAMA`, que gana `anclaje_por_parecido` e `invencion_sobre_historico`. `plan` llama a `revisar` tras volcar | `backend/src/storymaker/plotting/gate.py::revisar`, `::incidencias_guardadas`, `plotting/nodos.py::plan` | `test_revision_de_la_trama.py::TestRevisionEnElGate` | REQ-TR-05 |
| **TR-10** | `InformeDePlotting` gana `huecos` y cuenta los inventados sobre ellos cuando los hay; «grave» y «aviso» en lugar de «BLOQUEA»; `_resumen` del gate de Plotting añade el informe entero | `backend/src/storymaker/plotting/informe.py::construir`, `gates/nodos.py::_resumen` | `tests/unit/test_plotting.py::TestInforme` | REQ-TR-10 |

### 1.4 Rehacer

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **TR-11** | `hay_que_planificar`, `hay_trama`, `borrar` —en orden de claves foráneas, con `vec_canon`— y `como_texto` | `backend/src/storymaker/plotting/trama.py` | `test_revision_de_la_trama.py::TestCuandoSePlanifica` | REQ-TR-02, REQ-TR-04 |
| **TR-12** | `plan` decide con `hay_que_planificar`; si hay trama, compone `rehacer_como_texto` con `como_texto`, `comentarios_de_rehacer("plotting")` y las incidencias guardadas, borra y retira; `planificar(..., rehacer=...)` lo añade al prompt | `backend/src/storymaker/plotting/nodos.py::plan`, `::rehacer_como_texto`, `::planificar` | `test_trama_rehacible.py::TestRehacer` | REQ-TR-01, REQ-TR-03 |

### 1.5 La pantalla

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **TR-13** | `AvisoDeLaTrama`, `HuecoDeLaTrama`, `RevisionDeLaTrama`; `GateDeNovela.trama`, que `gate_de` rellena con `revision_de_la_trama` en el gate de Plotting | `backend/src/storymaker/api/seguimiento.py::revision_de_la_trama`, `::gate_de` | `test_revision_de_la_trama.py::TestRevisionEnElGate` | REQ-TR-10 |
| **TR-14** | Tipos regenerados; `RevisionDeLaTrama` exportado desde `shared/api`; el componente `RevisionDeLaTrama` y su sección en `Gate`, con los estilos `lista-avisos` y `lista-huecos`, y las etiquetas «Anclado por parecido» e «Invención sobre un histórico» | `frontend/src/shared/api/transporte.ts`, `shared/api/seguimiento.ts`, `pages/gate/ui/RevisionDeLaTrama.tsx`, `pages/gate/ui/Gate.tsx`, `pages/gate/ui/gate.css` | `frontend/tests/pantallas/gate-trama.test.tsx` | REQ-TR-10 |

### 1.6 Los anclajes

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **TR-15** | `con_claves(hechos, datos)`: subclase de `SalidaArquitecto` que sobrescribe `model_json_schema` para enumerar `#id` en `AnclajePropuesto.hecho` y `.dato` sin tocar la validación; `planificar` la construye con los hechos del contexto y los datos del encargo y se la pasa a `invocar_rol`, y el prompt dice qué clave va en qué campo | `backend/src/storymaker/plotting/esquemas.py::con_claves`, `plotting/nodos.py::planificar` | `test_trama_anclada.py::TestClavesEnElContrato` | REQ-TR-11 |
| **TR-16** | `por_parecido` —palabras de cuatro letras o más y años, `PALABRAS_COMUNES_MINIMAS = 2`, `PROPORCION_MINIMA = 0.6`—, `AnclajeResuelto` y `resolver_anclaje` en tres pasos; `volcar_escaleta` gana `textos_de_hecho`, `textos_de_dato` y `resueltos_por_parecido`; `volcar` escribe los avisos `anclaje_por_parecido` junto a los `anclaje_resuelto` | `backend/src/storymaker/plotting/escaleta.py::por_parecido`, `::resolver_anclaje`, `::volcar_escaleta`, `plotting/nodos.py::volcar` | `test_trama_anclada.py::TestAnclajesComoFrase` | REQ-TR-12 |

### 1.7 Arcos, invenciones y fechas

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **TR-17** | `_revisar_arco` compara la lista de capítulos con su orden, sin quitar repetidos, y el mensaje dice «retroceden de capítulo» | `backend/src/storymaker/commons/validation/escaleta.py::_revisar_arco` | `test_trama_anclada.py::TestOrdenDeLosHitos`, `tests/unit/test_core_domain.py` | REQ-TR-13 |
| **TR-18** | `invenciones_sobre_historicos(db, hecho_ids=None)` con `_nombres_historicos` y `_marcas`; la llaman `revisar` sobre todo el corpus y `fill_gap` sobre el hecho que acaba de inventar. `recalcular_invenciones(db)` retira y vuelve a escribir los avisos, y la llama `editar` tras cambiar un hecho o un personaje | `backend/src/storymaker/plotting/gate.py::invenciones_sobre_historicos`, `::recalcular_invenciones`, `plotting/nodos.py::fill_gap`, `api/operacion.py::editar` | `test_trama_anclada.py::TestInventadoSobreHistoricos`, `test_trama_rehacible.py::test_lo_inventado_sobre_un_historico_deja_aviso_en_el_gate` | REQ-TR-14 |
| **TR-19** | `nacimiento_de_epoca(propuesta, brief)` en el volcado del canon, para el homenajeado; `NACIMIENTO_DEL_HOMENAJEADO` en el prompt; en el Intake, `_edad_contra_periodo` avisa sin preguntar ante una fecha posterior al período y `_nacimiento_contra_evento_ancla` no la contrasta | `backend/src/storymaker/plotting/canon.py::nacimiento_de_epoca`, `::volcar_canon`, `plotting/nodos.py::planificar`, `intake/contradicciones.py` | `test_trama_anclada.py::TestNacimientoDeEpoca`, `tests/unit/test_intake.py::TestContradicciones` | REQ-TR-15 |

### 1.8 El aviso

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **TR-20** | `NOMBRE_DE_FASE` pasa a `commons/graph/nodos.py` y lo usan la API y el título del aviso; `InformeDePlotting.como_resumen` con `ETIQUETAS`; `resumen_movil(gate, estado)` con `_CIFRAS`; `abrir(..., informe, movil)` imprime el informe y envía el resumen | `backend/src/storymaker/commons/graph/nodos.py`, `plotting/informe.py::como_resumen`, `gates/nodos.py::resumen_movil`, `::abrir`, `::await_approval`, `api/seguimiento.py` | `test_trama_anclada.py::TestResumenParaElMovil`, `test_trama_anclada.py::TestAvisoDelGateDePlotting`, `tests/unit/test_gates.py::TestAviso` | REQ-TR-16 |

### 1.9 Fechas, nombres y la regla de los arcos

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **TR-21** | `leer_fecha(texto) -> FechaLeida` con `_ISO`, `_PREFIJO`, `_ANIO`, `_MESES`, `_ESTACIONES` y las precisiones `DIA`, `MES`, `ANIO`; `a_momento` pasa a devolver su `momento`. `cronologia_de_la_escaleta` lee cada `fecha_narrativa` con `leer_fecha` y deja el escenario a 0 si la precisión no es `DIA` | `backend/src/storymaker/commons/formal/generador.py::leer_fecha`, `::a_momento`, `plotting/gate.py::cronologia_de_la_escaleta` | `test_trama_anclada.py::TestFechasEnProsa`, `tests/unit/test_formal.py` | REQ-TR-17 |
| **TR-22** | `nombra_a(texto, nombre)` con `DELANTE_DE_UN_LUGAR` y `_detras_de_un_lugar`, en lugar de `_marcas`; `invenciones_sobre_historicos` la usa | `backend/src/storymaker/plotting/gate.py::nombra_a`, `::invenciones_sobre_historicos` | `test_trama_anclada.py::TestNombresDeLugar`, `::TestInventadoSobreHistoricos` | REQ-TR-18 |
| **TR-23** | `regla_de_los_arcos()` con `Defaults.ESCENAS_PARA_EXIGIR_ARCO` y `HITOS_MINIMOS_ARCO_CON_TRANSFORMACION`, en el bloque «Arcos» del prompt; `forma_de_la_escaleta` pide la fecha en ISO; `EscenaPropuesta.fecha_narrativa` gana su `description` | `backend/src/storymaker/plotting/nodos.py::regla_de_los_arcos`, `::forma_de_la_escaleta`, `::planificar`, `plotting/esquemas.py::EscenaPropuesta` | `test_trama_anclada.py::TestReglaDeLosArcosEnElPrompt` | REQ-TR-19 |

## 2. Orden de trabajo

1. **TR-01**. Sin la columna y la tabla nada de lo demás tiene dónde escribir, y al ser aditivas las novelas existentes se siguen abriendo con el código anterior.
2. **TR-02** y **TR-03**, independientes entre sí; después **TR-05** y **TR-04**, que los usan.
3. **TR-06**, luego **TR-07** a **TR-09**: la revisión necesita la cronología en Python para tener algo que decir en una instalación sin `lake`.
4. **TR-15** y **TR-16**, antes de que la revisión se apoye en los anclajes: la reparación de TR-08 solo debe actuar sobre lo que ni la clave ni el parecido resolvieron.
5. **TR-17**, **TR-18** y **TR-19**, independientes entre sí; después **TR-21**, **TR-22** y **TR-23**, que los afinan y tampoco dependen unos de otros. TR-21 va antes de cualquier prueba de cronología con fechas en prosa.
6. **TR-10** y **TR-20**, que leen lo que la revisión guardó.
7. **TR-11** y **TR-12**. Van después de la revisión porque rehacer lee lo que la revisión guardó.
8. **TR-13**, se regeneran los tipos y **TR-14**.

Al terminar: `uv run pytest`, `uv run ruff check` y `uv run mypy src` en el backend, `npm run comprobar` y `npm test` en el frontend, y `npm run build` para que FastAPI sirva la pantalla nueva.

## 3. Qué se rompe mientras tanto

- **La prueba de columnas aditivas** abre una base con solo `mundo_hecho`: sin la regla de TR-01 para tablas inexistentes, el `ALTER TABLE` sobre `canon_obra` revienta. Va en el mismo ítem.
- **`test_ningun_rol_se_invoca_de_mas`** afirma una sola llamada al arquitecto y sigue valiendo: en modo batch no hay gate y nadie rehace.
- **El doble de transporte** no guardaba los prompts, y las pruebas de TR-12 necesitan leerlos: gana `prompts` por perfil. `guion.arquitectura` acepta huecos como texto o como `HuecoPropuesto`.
- **Las novelas a medias** con `huecos_pendientes` en claro siguen avanzando por el camino del texto de TR-04; las que esperan en el gate de Plotting con una trama sin dueño replanifican al primer «rehacer», que es lo que el Autor pedía.
- **Hasta TR-12**, rehacer en el gate de Plotting sigue reabriendo el mismo gate sin llamar al arquitecto.
- **Una novela que espera en el gate de Plotting con la trama ya volcada** no gana los anclajes resueltos por parecido, la fecha de nacimiento de época ni los avisos nuevos hasta que el Autor rehace: la revisión corre al terminar `Plan`, no al abrir el gate.
- **Las cronologías de escaletas ya guardadas** cambian al releerse con TR-21: escenas que antes no entraban pasan a entrar, y las que caían en los años 1 o 24 se mueven a su fecha. Como todo lo de Plotting es aviso, lo único que cambia es qué se avisa.
- **`test_intake.py::test_el_homenajeado_nace_despues_del_periodo`** comprueba el mensaje del aviso, que cambia con TR-19: se actualiza en el mismo ítem.

## 4. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | Entran TR-21 a TR-23: las fechas en prosa con su precisión, los nombres detrás de una palabra de lugar y la regla de los arcos en el prompt | Baja de la spec, §3.3, §3.6 y §4.4 |
| 2026-09-24 | Segunda versión, reescrita: entran TR-15 a TR-20 y se amplían TR-03, TR-04, TR-07, TR-08, TR-09 y TR-14 | Baja de la segunda versión de la spec |
| 2026-09-24 | Primera versión, con TR-01 a TR-14 | Baja de la spec |
