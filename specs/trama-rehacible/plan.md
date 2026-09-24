# Plan — La Trama que se puede rehacer

La forma técnica de la [spec](spec.md): qué ficheros se tocan, con qué funciones, en qué orden y con qué prueba. Amplía los ítems `P-75`, `P-77` y `P-80` del [plan del backend](../backend/plan.md) sin sustituirlos. Si algo de aquí contradice a la arquitectura o a las specs, se para y se pregunta.

## 1. Ítems

### 1.1 El esquema

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **TR-01** | `canon_obra.fase_run_id` en `canon.sql` y en `COLUMNAS_ADITIVAS`; `plan_hueco` en `plan.sql` y en `TABLAS_ADITIVAS`, que `_anadir_columnas` crea al abrir si falta. Una columna aditiva de una tabla que no existe no se añade: la creará el esquema | `backend/src/storymaker/commons/db/esquema/canon.sql`, `commons/db/esquema/plan.sql`, `commons/db/apertura.py::_anadir_columnas` | `tests/unit/test_persistencia.py::TestColumnasAditivas` | REQ-TR-02, REQ-TR-08 |

### 1.2 Los huecos

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **TR-02** | `HuecoPropuesto` —`pregunta`, `escena`, `dimension`, `si_no_se_encuentra`— con un `model_validator(mode="before")` que convierte el texto suelto y cae a `cultura_material` ante una dimensión desconocida; `SalidaArquitecto.huecos: list[HuecoPropuesto]` | `backend/src/storymaker/plotting/esquemas.py` | `tests/integracion/test_trama_rehacible.py::TestHuecosAnclados` | REQ-TR-08 |
| **TR-03** | Repositorio de huecos: `registrar_hueco`, `hueco`, `cerrar_hueco` —que guarda hecho y resultado y ancla el hecho a la escena del hueco—, `huecos_de_la_trama`, y los auxiliares de la reparación `anclar_dato` y `escenas_con_texto` | `backend/src/storymaker/commons/db/repos/plan.py` | `test_trama_rehacible.py::TestHuecosAnclados` | REQ-TR-08, REQ-TR-09 |
| **TR-04** | `FORMA_DE_LOS_HUECOS` en el prompt del arquitecto; `volcar` devuelve clave de escena → identificador y pasa el dueño a `volcar_canon`, y deja de repetir `volcar_prohibidas`; `plan` registra los huecos hasta `settings.huecos_por_plotting` y deja sus identificadores en `huecos_pendientes`; `fill_gap` lee el hueco, llama a `cubrir_hueco` con su dimensión y su propuesta, y lo cierra | `backend/src/storymaker/plotting/nodos.py::plan`, `::fill_gap`, `::registrar_hueco`, `::volcar`, `plotting/canon.py::volcar_canon` | `test_trama_rehacible.py::TestHuecosAnclados` | REQ-TR-08, REQ-TR-09 |
| **TR-05** | `cubrir_hueco(..., propuesta="")`: lo inventado se escribe con la propuesta y, sin ella, con la pregunta | `backend/src/storymaker/plotting/nodos.py::cubrir_hueco` | `test_trama_rehacible.py::test_lo_no_encontrado_entra_con_la_propuesta_y_no_con_la_pregunta`, `tests/unit/test_firmeza_en_el_flujo.py` | REQ-TR-09 |

### 1.3 La revisión

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **TR-06** | `evaluar(novela) -> Veredicto`: I1 a I4 en Python sobre `NovelaLean`, con avisos `cronologia_escaleta` que dicen quién, dónde y cuándo; el lugar 0 no cuenta para I3 | `backend/src/storymaker/commons/formal/evaluacion.py::evaluar` | `tests/unit/test_revision_de_la_trama.py::TestCronologiaSinLean` | REQ-TR-07 |
| **TR-07** | `cronologia_de_la_escaleta` usa `NACIMIENTO_DESCONOCIDO` para quien no tiene fecha; `comprobar_cronologia` corre Lean si hay `lake` —con sus incidencias rebajadas a aviso— y `evaluar` si no o si Lean falla | `backend/src/storymaker/plotting/gate.py::cronologia_de_la_escaleta`, `::comprobar_cronologia` | `test_revision_de_la_trama.py::test_sin_fecha_de_nacimiento_no_nace_en_1800`, `tests/integracion/test_trama_rehacible.py::TestRevisionGuardada` | REQ-TR-07 |
| **TR-08** | `reparar_cobertura(db, vectorizador)`: cada obligatorio sin anclar, a la escena de mayor coseno, con su aviso `cobertura_reparada` | `backend/src/storymaker/plotting/gate.py::reparar_cobertura` | `test_revision_de_la_trama.py::TestCoberturaReparada` | REQ-TR-06 |
| **TR-09** | `revisar(db, vectorizador)`: retira lo anterior, repara, comprueba y guarda; `incidencias_guardadas` y `retirar_incidencias` sobre `VALIDADORES_DE_LA_TRAMA`. `plan` llama a `revisar` tras volcar | `backend/src/storymaker/plotting/gate.py::revisar`, `::incidencias_guardadas`, `plotting/nodos.py::plan` | `test_revision_de_la_trama.py::TestRevisionEnElGate` | REQ-TR-05 |
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
| **TR-14** | Tipos regenerados; `RevisionDeLaTrama` exportado desde `shared/api`; el componente `RevisionDeLaTrama` y su sección en `Gate`, con los estilos `lista-avisos` y `lista-huecos` | `frontend/src/shared/api/transporte.ts`, `shared/api/seguimiento.ts`, `pages/gate/ui/RevisionDeLaTrama.tsx`, `pages/gate/ui/Gate.tsx`, `pages/gate/ui/gate.css` | `frontend/tests/pantallas/gate-trama.test.tsx` | REQ-TR-10 |

## 2. Orden de trabajo

1. **TR-01**. Sin la columna y la tabla nada de lo demás tiene dónde escribir, y al ser aditivas las novelas existentes se siguen abriendo con el código anterior.
2. **TR-02** y **TR-03**, independientes entre sí; después **TR-05** y **TR-04**, que los usan.
3. **TR-06**, luego **TR-07** a **TR-09**: la revisión necesita la cronología en Python para tener algo que decir en una instalación sin `lake`.
4. **TR-10**.
5. **TR-11** y **TR-12**. Van después de la revisión porque rehacer lee lo que la revisión guardó.
6. **TR-13**, se regeneran los tipos y **TR-14**.

Al terminar: `uv run pytest` en el backend, `npm run comprobar` y `npm test` en el frontend.

## 3. Qué se rompe mientras tanto

- **La prueba de columnas aditivas** abre una base con solo `mundo_hecho`: sin la regla de TR-01 para tablas inexistentes, el `ALTER TABLE` sobre `canon_obra` revienta. Va en el mismo ítem.
- **`test_ningun_rol_se_invoca_de_mas`** afirma una sola llamada al arquitecto y sigue valiendo: en modo batch no hay gate y nadie rehace.
- **El doble de transporte** no guardaba los prompts, y las pruebas de TR-12 necesitan leerlos: gana `prompts` por perfil. `guion.arquitectura` acepta huecos como texto o como `HuecoPropuesto`.
- **Las novelas a medias** con `huecos_pendientes` en claro siguen avanzando por el camino del texto de TR-04; las que esperan en el gate de Plotting con una trama sin dueño replanifican al primer «rehacer», que es lo que el Autor pedía.
- **Hasta TR-12**, rehacer en el gate de Plotting sigue reabriendo el mismo gate sin llamar al arquitecto.

## 4. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | Primera versión, con TR-01 a TR-14 | Baja de la spec |
