# Plan — El gate de Investigación con el corpus a la vista

La forma técnica de la [spec](spec.md) y de lo que la firmeza cambia en el backend ([spec del backend](../backend/spec.md) §3.4, §3.6, §4.2 y §4.3): qué ficheros se tocan, con qué funciones, en qué orden y con qué prueba. Si algo de aquí contradice a la arquitectura o a las specs, se para y se pregunta.

## 1. Ítems

### 1.1 El corpus en el gate

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **GI-01** | El verificador escribe cada veredicto con su motivo en `audit_log` | `backend/src/storymaker/investigation/nodos.py::verificar_respaldo` | `tests/api/test_operacion.py::TestDescartar::test_la_salida_trae_el_motivo_del_verificador` | REQ-GI-05 |
| **GI-02** | La salida de Investigación sirve `motivo_respaldo` por hecho, leído de `audit_log` | `backend/src/storymaker/api/fases.py::Hecho`, `api/fases.py::_investigacion` | La misma | REQ-GI-05 |
| **GI-03** | `descartar_hecho`: comprueba que nada lo usa y borra fuentes, vector y fila | `backend/src/storymaker/commons/db/repos/mundo.py::descartar_hecho` | `TestDescartar` | REQ-GI-03, REQ-GI-04 |
| **GI-04** | `POST /novelas/{id}/hechos/{hecho_id}/descartar`, con cerrojo, rechazo si está sellado y traza en `edicion_humana` y `audit_log` | `backend/src/storymaker/api/operacion.py::descartar` | `TestDescartar` | REQ-GI-03, REQ-GI-04 |
| **GI-05** | La entidad `hecho`: `FilaHecho` con su cita, su motivo y sus fuentes, y `Corpus` con las pestañas por dimensión y «Sin respaldo» | `frontend/src/entities/hecho/` | `tests/pantallas/gate-investigacion.test.tsx`, `tests/pantallas/fases.test.tsx` | REQ-GI-01, REQ-GI-05 |
| **GI-06** | La salida de Investigación usa `Corpus`; la de cualquier fase con gate pendiente enlaza al gate | `frontend/src/pages/phase/ui/SalidaInvestigacion.tsx`, `pages/phase/ui/Fase.tsx` | `gate-investigacion.test.tsx` | REQ-GI-06 |
| **GI-07** | El gate de Investigación enseña `CorpusDelGate` con Corregir y Descartar, aplicados en el sitio, y no enseña el editor genérico | `frontend/src/pages/gate/ui/CorpusDelGate.tsx`, `pages/gate/ui/Gate.tsx`, `pages/gate/api/gate.ts`, `shared/api/operacion.ts::descartarHecho` | `gate-investigacion.test.tsx` | REQ-GI-01, REQ-GI-02 |

### 1.2 La firmeza

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **GI-08** | `firmeza(estado, respaldo, origen) -> str`, pura y total, con el orden como tupla con nombre (`ORDEN_DE_FIRMEZA`) y el techo de lo no respaldado como constante | `backend/src/storymaker/commons/validation/puras.py::firmeza` | `tests/unit/test_firmeza.py`: las 48 combinaciones contra la tabla de arq. §7, más un estado desconocido | REQ-BE-204 |
| **GI-09** | `mundo.anotar_respaldo` escribe **solo** `respaldo`; `corpus.degradar_sin_respaldo` pasa a `corpus.anotar_veredicto`, y el comentario del disparador de inmutabilidad deja de decir que el verificador degrada | `commons/db/repos/mundo.py::anotar_respaldo`, `investigation/corpus.py::anotar_veredicto`, `commons/db/esquema/inmutabilidad.sql` | `tests/unit/test_investigation.py`, `tests/unit/test_persistencia.py`: tras un `no_respaldado`, `estado` sigue siendo el declarado | REQ-BE-65, REQ-BE-199 |
| **GI-10** | El verificador se parte en piezas: `_pedir_veredictos(filas)` hace una llamada y devuelve sus veredictos, `_anotar(veredicto)` escribe el respaldo y el motivo en `audit_log`; `verificar_respaldo(fase_run_id)` recorre los lotes de veinte como hasta ahora; `verificar_hecho(hecho_id)` verifica uno solo y, si la salida no valida, lo deja `pendiente` y devuelve `None`. Con un solo hecho en juego, toma el veredicto cuyo `hecho_id` coincide y, si ninguno coincide y hay uno solo, ese: un modelo que numera mal no puede escribir el respaldo de otro hecho | `investigation/nodos.py` | `tests/unit/test_firmeza_en_el_flujo.py::test_un_fallo_del_verificador_deja_el_hecho_pendiente` | REQ-BE-201 |
| **GI-11** | `cubrir_hueco` llama a `verificar_hecho` tras escribir un hecho `micro_arquitecto`; el informe de Plotting cuenta los micro con `respaldo = 'no_respaldado'` con `mundo.micro_sin_respaldo` | `plotting/nodos.py::cubrir_hueco`, `plotting/informe.py`, `commons/db/repos/mundo.py::micro_sin_respaldo` | `test_firmeza_en_el_flujo.py::test_el_hecho_de_la_micro_sesion_pasa_por_el_verificador`, `::test_el_informe_de_plotting_cuenta_los_micro_sin_respaldo` | REQ-BE-201, REQ-BE-202 |
| **GI-12** | `calcular_hash_corpus` incluye `respaldo` en lo que resume | `commons/db/repos/mundo.py::calcular_hash_corpus` | `test_firmeza_en_el_flujo.py::test_el_sello_cambia_con_el_respaldo` | REQ-BE-203 |
| **GI-13** | `ESTADOS_EXPLICADOS`: las cuatro definiciones del glosario, en el prompt de la sesión única, en el de las dirigidas y en el de la micro-sesión; la micro-sesión recibe además el bloque «De cada hecho guarda», que le pide la cita | `investigation/prompts.py` | `test_firmeza_en_el_flujo.py::test_los_prompts_definen_los_cuatro_estados`, `::test_la_micro_sesion_pide_la_cita` | REQ-BE-200 |
| **GI-14** | El bloque 5 y el contexto del arquitecto escriben `[firmeza]` delante de cada hecho; `plan.anclajes_de` trae además `hecho_respaldo` y `hecho_origen` | `commons/context/bloques.py::anclajes`, `commons/db/repos/plan.py::anclajes_de`, `plotting/contexto.py::como_texto` | `test_firmeza_en_el_flujo.py::test_el_arquitecto_ve_la_firmeza`, `tests/unit/test_ensamblador.py` | REQ-BE-205 |
| **GI-15** | `Hecho` gana `firmeza`; el informe de Investigación gana `por_firmeza` y rotula los no respaldados con «su firmeza no pasa de inferido» | `api/fases.py::Hecho`, `api/fases.py::_investigacion`, `investigation/informe.py` | `tests/api/test_operacion.py::TestDescartar::test_la_salida_trae_la_firmeza`, `tests/unit/test_investigation.py` | REQ-GI-07, REQ-GI-09 |
| **GI-16** | Se regeneran los tipos; `TONO_DE_LA_FIRMEZA` sustituye a `TONO_DEL_ESTADO` y entra `estadoQueDifiere(hecho)` en el modelo de la entidad; `FilaHecho` enseña la firmeza primero y el estado declarado solo cuando difiere y no es invención | `frontend/src/shared/api/transporte.ts`, `frontend/src/entities/hecho/model/hecho.ts`, `entities/hecho/ui/FilaHecho.tsx` | `tests/pantallas/gate-investigacion.test.tsx` | REQ-GI-08 |
| **GI-17** | Corregir un enunciado deja el respaldo como estaba | — (lo cumple ya la edición humana, que solo escribe el campo pedido) | `tests/api/test_operacion.py::TestDescartar::test_corregir_no_toca_el_respaldo` | REQ-GI-10 |

### 1.3 El respaldo parcial y el uso de la firmeza

| Ítem | Qué | Ficheros | Prueba | Requisitos |
|---|---|---|---|---|
| **GI-18** | `mundo_hecho.sin_respaldo TEXT` con `CHECK` de 300 caracteres en `mundo.sql`; `COLUMNAS_ADITIVAS` en `apertura.py`, que en cada apertura añade con `ALTER TABLE` la columna que falte, **sin tocar `VERSION_ESQUEMA`** | `commons/db/esquema/mundo.sql`, `commons/db/apertura.py::_anadir_columnas` | `tests/unit/test_persistencia.py::TestColumnasAditivas::test_una_novela_sin_la_columna_la_gana_sin_subir_de_version` | REQ-BE-211 |
| **GI-19** | `anadido_vigente(enunciado, sin_respaldo) -> str \| None`: el añadido si, normalizado, sigue dentro del enunciado normalizado | `commons/validation/puras.py::anadido_vigente` | `tests/unit/test_firmeza.py` | REQ-BE-209 |
| **GI-20** | `VeredictoDeRespaldo.sin_respaldo` (300 caracteres); `prompt_de_verificacion` pregunta por el dato central y pide copiar el añadido; `_anotar` escribe `respaldo` y `sin_respaldo` con `mundo.anotar_respaldo`, y los deja en `audit_log`; `verificar_hecho` no mira lo que no esté `pendiente` | `investigation/esquemas.py`, `investigation/prompts.py::prompt_de_verificacion`, `investigation/nodos.py`, `commons/db/repos/mundo.py::anotar_respaldo` | `tests/unit/test_firmeza_en_el_flujo.py::TestParcial` | REQ-BE-207, REQ-BE-208 |
| **GI-21** | Un hecho `desconocido` se escribe con `respaldo = 'no_aplica'` | `investigation/corpus.py::escribir_hecho` | `test_firmeza_en_el_flujo.py::test_una_laguna_no_pasa_por_el_verificador` | REQ-BE-207 |
| **GI-22** | `ESTADOS_EXPLICADOS` define los cuatro estados respecto a lo que dice la fuente | `investigation/prompts.py` | `test_firmeza_en_el_flujo.py::test_los_prompts_definen_los_cuatro_estados` | REQ-BE-200 |
| **GI-23** | `calcular_hash_corpus` incluye `sin_respaldo` | `commons/db/repos/mundo.py::calcular_hash_corpus` | `test_firmeza_en_el_flujo.py::test_el_sello_cambia_con_el_anadido` | REQ-BE-203 |
| **GI-24** | El bloque 5 y el contexto del arquitecto añaden `(no lo dice la cita: «…»)` con `anadido_vigente`; `plan.anclajes_de` trae además `hecho_sin_respaldo` | `commons/context/bloques.py::anclajes`, `commons/db/repos/plan.py::anclajes_de`, `plotting/contexto.py::como_texto` | `test_firmeza_en_el_flujo.py::test_el_arquitecto_ve_lo_que_no_dice_la_cita` | REQ-BE-209 |
| **GI-25** | `USO_DE_LA_FIRMEZA` en el bloque 6, dentro del fragmento fijo de reglas; el prompt del arquitecto lleva su propia versión, `USO_DE_LA_FIRMEZA_EN_LA_TRAMA` | `commons/context/bloques.py::reglas`, `plotting/nodos.py::planificar` | `tests/unit/test_ensamblador.py::test_las_reglas_dicen_que_hacer_con_cada_firmeza`, `test_firmeza_en_el_flujo.py::test_el_arquitecto_recibe_el_uso_de_la_firmeza` | REQ-BE-210, REQ-BE-212 |
| **GI-26** | `plan.escenas_poco_firmes(db)`: capítulo y orden de cada escena cuyos anclajes a hechos son todos `inferido` o `desconocido`; el informe de Plotting los enumera | `commons/db/repos/plan.py::escenas_poco_firmes`, `plotting/informe.py` | `test_firmeza_en_el_flujo.py::test_el_informe_de_plotting_avisa_de_las_escenas_poco_firmes` | REQ-BE-213 |
| **GI-27** | `Hecho` gana `no_lo_dice_la_cita`; se regeneran los tipos | `api/fases.py::Hecho`, `frontend/src/shared/api/transporte.ts` | `tests/api/test_operacion.py::TestDescartar::test_la_salida_trae_lo_que_no_dice_la_cita` | REQ-GI-07 |
| **GI-28** | `FilaHecho` enseña una sola insignia, la firmeza —la dimensión, cuando la lista mezcla varias, va como texto y no como insignia—, y debajo «No lo dice la cita: …»; el motivo del verificador sale en los no respaldados y en los parciales; `Corpus` enseña solo las pestañas de las seis dimensiones | `frontend/src/entities/hecho/` | `tests/pantallas/gate-investigacion.test.tsx` | REQ-GI-01, REQ-GI-05, REQ-GI-08, REQ-GI-11 |
| **GI-30** | `FilaHecho` mete lo que no dice la cita y el motivo del verificador en un `<details>` cerrado, rotulado «Nota del verificador», solo si `porRevisar(hecho)`; `.verificador` sin fondo rojo | `frontend/src/entities/hecho/ui/FilaHecho.tsx`, `entities/hecho/ui/hecho.css` | `tests/pantallas/gate-investigacion.test.tsx` | REQ-GI-05, REQ-GI-11 |
| **GI-31** | `prompt_de_verificacion`: el dato central es lo que existió u ocurrió; la fecha, el lugar o el detalle que la cita no trae van a `sin_respaldo` con `respaldado: true`; `no_respaldado` solo si la cita no sostiene lo que ocurrió o lo contradice | `backend/src/storymaker/investigation/prompts.py::prompt_de_verificacion` | `tests/unit/test_firmeza_en_el_flujo.py::TestParcial::test_el_prompt_del_verificador_pide_el_anadido` | REQ-BE-214 |
| **GI-32** | `anadido_vigente` tolerante: además de la copia literal, acepta el añadido si todas sus palabras significativas están en el enunciado | `backend/src/storymaker/commons/validation/puras.py::anadido_vigente` | `tests/unit/test_firmeza.py::TestAnadidoVigente` | REQ-BE-215 |
| **GI-33** | `FilaHecho` pone «En proceso de verificación» como etiqueta de un hecho `pendiente` | `frontend/src/entities/hecho/ui/FilaHecho.tsx` | `tests/pantallas/gate-investigacion.test.tsx` | REQ-GI-12 |
| **GI-29** | Corregir un enunciado deja también el añadido guardado | — | `tests/api/test_operacion.py::TestDescartar::test_corregir_no_toca_el_respaldo` | REQ-GI-10 |

## 2. Orden de trabajo

1. **GI-08**, sola y con su prueba: es la regla, y todo lo demás la llama.
2. **GI-09**. Desde aquí `estado` ya no cambia, y hasta GI-14 el escritor y el arquitecto ven el estado declarado sin techo: un `verificado` sin respaldo llegaría como `verificado`. Ningún test lo cubre en ese intervalo, así que GI-09 a GI-14 van en la misma tanda y no se deja el árbol en medio.
3. **GI-10**, luego **GI-11**: `cubrir_hueco` necesita `verificar_hecho`.
4. **GI-12** y **GI-13**, independientes entre sí.
5. **GI-14**, que cierra el hueco del paso 2.
6. **GI-15**, y con él se regeneran los tipos del frontend.
7. **GI-16** y **GI-17**.
8. **GI-18** primero de la tanda 1.3: sin la columna, nada de lo demás puede escribir el añadido. Luego **GI-19** a **GI-23**, que tocan el backend de Investigation; **GI-24** a **GI-26**, que tocan a los lectores y a Plotting, y por último **GI-27** a **GI-29**, con los tipos regenerados antes de tocar la pantalla.

Al terminar: `uv run pytest` en el backend, `npm run comprobar` y `npm test` en el frontend.

## 3. Qué se rompe mientras tanto

- **Las pruebas que afirman la degradación** —`test_investigation.py::test_un_hecho_sin_respaldo_se_degrada_y_no_se_borra`, `test_persistencia.py::test_antes_del_sello_el_verificador_puede_degradar` y la que busca «degradados a inferido» en el informe— fallan en cuanto entra GI-09. Se reescriben en el mismo ítem para afirmar lo contrario: el estado no cambia y la firmeza baja.
- **El doble de transporte** responde por perfil y no por fase, y ninguna prueba de integración abre huecos —el guion del arquitecto no declara ninguno—, así que la llamada nueva del verificador en `FillGap` no deja a ninguna sin respuesta preparada. Las pruebas de GI-11 preparan la suya.
- **Los sellos ya escritos** no se recalculan en ningún sitio, así que meter `respaldo` en el hash no invalida ninguna novela: solo cambia el hash de las que se sellen a partir de ahora.
- **Hasta GI-17 nada del esquema cambia**: las novelas existentes se leen igual, con la firmeza calculada sobre sus filas; las que se degradaron con la regla anterior salen `inferido`, que es lo que la regla nueva daría.
- **GI-18 sí cambia el esquema**, y es el único ítem que lo hace, pero **sin subir la versión**: la columna es aditiva y admite nulos, así que un proceso con el código viejo —el servidor de la interfaz arrancado antes, o la Ejecución que esté corriendo— sigue abriendo la novela y no la lee. Si un proceso viejo tiene la novela abierta mientras uno nuevo añade la columna, el `ALTER TABLE` espera al cerrojo de SQLite como cualquier escritura; las consultas viejas nombran sus columnas o las leen por nombre, y una columna más no les cambia nada.
- **Las pruebas de la pantalla** que buscan la pestaña «Sin respaldo» o la insignia del respaldo cambian en GI-28, que retira esa pestaña sin sustituirla.

## 4. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | Entran **GI-31 a GI-33**: el prompt del verificador con el dato central como lo que ocurrió, `anadido_vigente` tolerante y la etiqueta «En proceso de verificación» | Baja de la arquitectura y de las specs |
| 2026-09-24 | Entra **GI-30**: lo del verificador, en un desplegable cerrado y sin rojo | Baja de la spec, por petición del Autor |
| 2026-09-24 | GI-28: `Corpus` enseña solo las pestañas de las dimensiones; se retira `POR_REVISAR` | Baja de la spec: el Autor pidió solo pestañas de dimensión |
| 2026-09-24 | Entran **GI-18 a GI-29**: `sin_respaldo` como columna aditiva, sin subir la versión, `anadido_vigente`, el veredicto parcial, las lagunas sin verificar, los estados respecto a la fuente, el sello con el añadido, «No lo dice la cita» en los lectores, el uso de la firmeza para el escritor y el arquitecto, el aviso de escenas poco firmes y una sola etiqueta en pantalla. El orden y lo que se rompe mientras tanto ganan sus líneas | Baja de la spec y de la spec del backend |
| 2026-09-24 | GI-10 nombra las funciones como quedaron —`_pedir_veredictos` y `_anotar`—; GI-13 da a la micro-sesión el bloque que pide la cita; GI-16 dice que `TONO_DEL_ESTADO` se retira | Al implementar: el prompt de la micro-sesión no pedía la cita, y sin ella el verificador no tenía nada que leer (It-31) |
| 2026-09-24 | Se reescribe el documento entero. Entran **GI-08 a GI-17**, la firmeza de principio a fin: la función, el verificador que ya no reescribe el estado, la verificación de los hechos de la micro-sesión, el sello con el respaldo, las definiciones en el prompt, la firmeza en el contexto de los modelos, en la API, en el informe y en la pantalla. Se añaden el orden de trabajo y lo que se rompe mientras tanto | Baja de la spec y de la spec del backend |
| 2026-09-24 | Primera versión, con GI-01 a GI-07 | Baja de la spec |
