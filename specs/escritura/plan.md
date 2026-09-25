# Plan — La Escritura que no se atasca

La forma técnica de la [spec](spec.md): qué ficheros se tocan, con qué funciones, en qué orden y con qué prueba. Amplía los ítems del bucle de Writing, de la publicación y del juez del [plan del backend](../backend/plan.md) sin sustituirlos. Si algo de aquí contradice a la arquitectura o a las specs, se para y se pregunta.

## 1. Ítems

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **ES-01** | `nombres_exactos` acepta el nombre tal cual, con la inicial en mayúscula y, si tiene varias palabras, con la inicial en minúscula | `backend/src/storymaker/commons/validation/chapter_validator.py::nombres_exactos` | `tests/unit/test_escritura.py::TestNombresDescriptivos`, `tests/unit/test_core_domain.py`, `tests/contratos/test_nodo_vs_hook.py` | REQ-ES-01 |
| **ES-02** | `reparar` compara el texto devuelto con el de la versión y, si es el mismo, registra `SIN_CAMBIOS` y devuelve `None`; `repair` agota los reintentos con `None` | `backend/src/storymaker/writing/nodos.py::reparar`, `::repair` | `tests/integracion/test_contabilidad.py::TestReintentar` | REQ-ES-02 |
| **ES-03** | `cronologia_de_la_novela(db, con_version)` y `verificar_cronologia(novela, bloquea, validador)` | `backend/src/storymaker/commons/formal/cronologia.py` | `test_escritura.py::TestCronologiaDeLaNovela` | REQ-ES-03, REQ-ES-05 |
| **ES-04** | La clave de los eventos narrativos lleva la versión | `backend/src/storymaker/writing/extraccion.py::volcar_cronologia` | `test_escritura.py::test_cada_intento_escribe_sus_eventos`, `tests/unit/test_writing.py` | REQ-ES-04 |
| **ES-05** | `extraer` compone la cronología con la versión, la comprueba bloqueando y se queda con lo que lleva `cap{N}-v{versión}-`, como `CRONOLOGIA_DEL_CAPITULO` | `backend/src/storymaker/writing/nodos.py::extraer` | `test_escritura.py::TestCronologiaEnElExtractor` | REQ-ES-03 |
| **ES-06** | `comprobar_cronologia` del gate de Plotting pasa a `verificar_cronologia` sin bloquear; `evaluacion` cambia su docstring | `backend/src/storymaker/plotting/gate.py::comprobar_cronologia`, `commons/formal/evaluacion.py` | `tests/unit/test_revision_de_la_trama.py`, `tests/integracion/test_trama_rehacible.py::TestRevisionGuardada` | REQ-ES-05 |
| **ES-07** | `cronologia_completa` pasa a `cronologia_de_la_novela`; `publicar` la comprueba antes de `publicar_version` y lanza `PublicacionRechazada` | `backend/src/storymaker/publication/nodos.py::cronologia_completa`, `::publicar` | `test_escritura.py::test_antes_de_nacer_bloquea_y_se_calcula_sin_lean`, `tests/integracion/test_extremo_a_extremo.py` | REQ-ES-06 |
| **ES-08** | `registrar_contradicciones` con `CONTRADICCION_DEL_JUEZ` y `_CAPITULO_CITADO`, llamada desde `judge`; `InformeDeWriting.contradicciones`; `resumen_movil` del gate de Writing; `aviso_de_terminada(..., contradicciones)` y `_avisar` que las cuenta | `backend/src/storymaker/publication/nodos.py::registrar_contradicciones`, `::judge`, `writing/gate.py`, `gates/nodos.py::resumen_movil`, `gates/notifier.py::aviso_de_terminada`, `commons/graph/run.py::_avisar` | `test_escritura.py::TestContradiccionesDelJuez` | REQ-ES-07 |
| **ES-09** | `regenerar` con sus cuatro salidas sin grafo y la escritura del checkpoint como salida de `Idle`; `ResultadoInvocacion.nota`; `NadaQueRegenerar` | `backend/src/storymaker/commons/graph/run.py::regenerar`, `commons/errores.py` | `tests/integracion/test_regeneracion.py::TestSinNadaQueRegenerar` | REQ-ES-08, REQ-ES-12 |
| **ES-10** | `tras_idle` y la arista condicional de `Idle` | `backend/src/storymaker/commons/graph/aristas.py::tras_idle`, `commons/graph/construccion.py::construir` | `test_regeneracion.py::TestCambioDeUnPersonaje`, `tests/contratos/test_identidad_nodos.py` | REQ-ES-08 |
| **ES-11** | `checkpoint` en regeneración y `revisar_invalidados` | `backend/src/storymaker/writing/nodos.py::checkpoint`, `regeneration/revision.py` | `test_regeneracion.py::TestCambioDeUnPersonaje` | REQ-ES-09, REQ-ES-10, REQ-ES-11 |
| **ES-12** | `DecisionTomada.fase`; `decidir` llama a `regenerar` sobre un gate de Regeneración; `salida.resultado` enseña la nota | `backend/src/storymaker/gates/decisiones.py`, `cli/comandos.py::decidir`, `cli/salida.py::resultado` | `test_regeneracion.py::TestSinNadaQueRegenerar::test_rehacer_descarta_la_peticion` | REQ-ES-08, REQ-ES-12 |
| **ES-13** | `retirados.py`: `pares`, `aparece`, `sustituir`, `incidencias`, `propagar`, `capitulos_que_lo_nombran`; `request` propaga y guarda `retirados`; `calcular_alcance(..., pares)` en `request`, `regenerar` y `POST /cambios` | `backend/src/storymaker/regeneration/retirados.py`, `regeneration/nodos.py::request`, `::calcular_alcance`, `commons/graph/run.py::regenerar`, `api/cambios.py` | `tests/unit/test_valor_retirado.py`, `test_regeneracion.py::TestElNombreLlegaAlTexto` | REQ-ES-13, REQ-ES-14 |
| **ES-14** | `EstadoNovela.retirados`; `validar_determinista(..., retirados)` desde `validate` y `pasa_coste_cero`; `checkpoint` los pasa a `revisar_invalidados` y los vacía al terminar | `backend/src/storymaker/commons/graph/estado.py`, `writing/nodos.py`, `regeneration/revision.py` | `test_regeneracion.py::TestElNombreLlegaAlTexto` | REQ-ES-15 |

## 2. Orden de trabajo

1. **ES-01**, sin dependencias: es el falso positivo que hoy para una novela.
2. **ES-02**, que no depende de nada más.
3. **ES-04** antes que **ES-03**: sin la versión en la clave, la cronología del intento heredaría las filas del anterior.
4. **ES-03**, luego **ES-05**, **ES-06** y **ES-07**, que lo usan.
5. **ES-08**.

Al terminar: `uv run pytest`, `uv run ruff check` y `uv run mypy src` en el backend.

## 3. Qué se rompe mientras tanto

- **`test_nodo_vs_hook.py`** espera que «manuel ferrer» siga siendo otra grafía: por eso ES-01 no ignora las mayúsculas, solo libera la inicial.
- **`TestReintentar`** contaba cuatro versiones del capítulo 1 porque el editor de su caída devolvía el mismo texto. Con ES-02 esas copias no se guardan: la prueba pasa a comprobar que el intento fallido sigue y que queda `reparacion_sin_cambios`.
- **Las novelas ya escritas** tienen eventos con la clave sin versión. Siguen contando, porque `cronologia_de_la_novela` elige por versión aprobada y no por clave; solo los intentos nuevos escriben la clave nueva.
- **Una instalación sin `lake`** pasa a comprobar la cronología de la prosa con Python y a bloquear por ella: una novela que antes se escribía entera puede ahora volver al editor, que es lo que G3 pide.

## 4. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-25 | Entran ES-13 y ES-14, el valor retirado. ES-13 antes que ES-14, que lee sus pares | Baja de §9 de la spec (It-36) |
| 2026-09-25 | Entran ES-09 a ES-12. Orden: ES-10 y ES-11 antes que ES-09, que entra por ellos; ES-12 al final. Mientras tanto no se rompe nada: sin ES-09 el grafo nunca llega a `RequestChange` | Baja de §9 de la spec |
| 2026-09-24 | Primera versión, con ES-01 a ES-08 | Baja de la spec |
