# Matriz de trazabilidad — arquitectura ↔ planes de implementación

Trazabilidad de **todo el repositorio**: [`docs/architecture.md`](docs/architecture.md), que es la fuente de verdad y **no se modifica desde aquí**, contra los dos planes de implementación que la realizan, [`specs/backend/plan.md`](specs/backend/plan.md) y [`specs/frontend/plan.md`](specs/frontend/plan.md).

Este documento no decide nada: **comprueba**. Un requisito sin ítem es una decisión que nadie va a implementar; un ítem sin requisito es trabajo que nadie acordó. Los dos fallos son distintos y ninguno se ve desde el otro lado, así que el recorrido va en las dos direcciones: §1 de la arquitectura al plan, §2 del plan a la arquitectura.

## Convenio

**`ARQ-nn`** identifica un requisito de la arquitectura y lleva delante el apartado del que sale. Los identificadores son estables y **no se reutilizan jamás**: si un requisito desaparece, su fila se queda con nota en lugar de dejar el hueco a otro.

**`IMP-ID`** identifica un ítem de plan. El repositorio tiene dos planes con espacios de identificadores propios, así que aquí se escriben con su prefijo: **`BE:P-nn`** para el backend y **`FE:IMP-nn`** para el frontend. La correspondencia detallada de cada mitad vive en su propia matriz —[`specs/backend/trace-matrix.md`](specs/backend/trace-matrix.md) y [`specs/frontend/trace-matrix.md`](specs/frontend/trace-matrix.md)—, y esta es la vista consolidada: `ARQ-01` a `ARQ-116` son uno a uno los requisitos `A-01` a `A-116` de la matriz del backend, y `ARQ-117` a `ARQ-136` son los del frontend que ninguna matriz anterior enumeraba. Los que llegan después se numeran en orden de llegada: `ARQ-137` es `A-117`, `ARQ-138` es `A-118`, `ARQ-139` a `ARQ-141` vuelven a ser del frontend: son `ARQ-37` a `ARQ-39` de su matriz, y `ARQ-142` es `A-119`.

**Estado.** `CUBIERTO` solo si algún ítem lo materializa **con entregable concreto y criterio de hecho**; «implementar X» no cuenta, y donde la cobertura depende de algo que todavía no existe la nota lo dice. `GAP` en cualquier otro caso.

**Lo que esta matriz no hace.** No elimina ni fusiona filas para reducir huecos: el inventario nació con **132 filas** y hoy son **145**; crece cuando la arquitectura decide algo nuevo, nunca mengua. Un hueco se cierra **añadiendo o ampliando ítems en los planes**, nunca borrando la exigencia. Y donde la arquitectura es ambigua, queda anotado en la nota sin inventar requisito.

**El orden sigue los apartados de la arquitectura, no el número.** Los identificadores son estables desde la matriz del backend, que agrupaba por apartado, y respetar ese orden vale más que tener la columna ordenada.

---

## 1. Inventario: arquitectura → planes

| ARQ-ID | Descripción | IMP-IDs | Estado | Nota |
|---|---|---|---|---|
| ARQ-01 | §1 · Motor de orquestación LangGraph con estado explícito, un nodo por acción de la especificación TLA+ | BE:P-54, BE:P-55 | CUBIERTO | — |
| ARQ-02 | §1 · Agentes por Claude Agent SDK, todos en Haiku 4.5, con modelo, herramientas y turnos fijados por invocación | BE:P-27, BE:P-32 | CUBIERTO | — |
| ARQ-03 | §1 · Los nueve roles, cada uno con su punto de invocación | BE:P-27, BE:P-66, BE:P-68, BE:P-69, BE:P-72, BE:P-75, BE:P-81, BE:P-83, BE:P-86, BE:P-90 | CUBIERTO | — |
| ARQ-04 | §1 · Los validadores son nodos del grafo, nunca herramientas; las aristas condicionales leen booleanos de Python | BE:P-06, BE:P-56 | CUBIERTO | — |
| ARQ-05 | §1 · Paso de contexto por empuje determinista en siete bloques | BE:P-33 | CUBIERTO | — |
| ARQ-06 | §1 · Un único fichero SQLite por novela; checkpoint y dominio en la misma transacción | BE:P-18, BE:P-19, BE:P-20, BE:P-21, BE:P-87 | CUBIERTO | — |
| ARQ-07 | §1 · Capítulos inmutables más manifiesto | BE:P-12, BE:P-17, BE:P-98 | CUBIERTO | — |
| ARQ-08 | §1 · Grafo de `fase_run` inmutables: rehacer, reanudar, ramificar y regenerar son la misma operación | BE:P-58, BE:P-71, BE:P-102 | CUBIERTO | — |
| ARQ-09 | §1 · Cinco gates bloqueantes con notificación, desactivables en batch | BE:P-103, BE:P-127, BE:P-73, BE:P-78, BE:P-89, BE:P-100 | CUBIERTO | — |
| ARQ-10 | §1 · Validación formal en dos planos: Lean 4 para la historia, TLA+/PlusCal para el arnés | BE:P-47, BE:P-48, BE:P-61 | CUBIERTO | — |
| ARQ-11 | §1 · Observabilidad en Langfuse con spans manuales autorizados y OTLP opcional | BE:P-50, BE:P-53 | CUBIERTO | — |
| ARQ-12 | §1 · Presupuesto de 100.000 tokens concurrentes, garantizado por construcción | BE:P-28, BE:P-32 | CUBIERTO | — |
| ARQ-13 | §1 · Pila: FastAPI *package by feature* con `commons`; React en FSD v2.1 | BE:P-01, FE:IMP-01, FE:IMP-02, FE:IMP-04 | CUBIERTO | Las dos mitades: el backend en P-01, el frontend en IMP-01 a IMP-04 |
| ARQ-14 | §1 · Embeddings FastEmbed local, 384 dimensiones, indexados con `sqlite-vec` | BE:P-22, BE:P-23 | CUBIERTO | — |
| ARQ-111 | §1 · Correspondencia documento↔código comprobada por **tests de trazabilidad y no por lectura**: lo que la spec declara y el plan nombra tiene quien lo compruebe en CI | BE:P-62, BE:P-129, BE:P-130, BE:P-131, BE:P-132, BE:P-133, BE:P-137, FE:IMP-33 | CUBIERTO | `FE:IMP-33` es la parte del frontend: que el inventario y los requisitos lean también su plan y su spec |
| ARQ-137 | §1, §11e · Cada spec **enumera sus requisitos con identificador propio** —`REQ-BE-nn` y `REQ-FE-nn`—, derivados de su propio contenido y no importados del encargo | BE:P-139, FE:IMP-33 | CUBIERTO | El enunciado vive en la spec; los ítems solo lo comprueban. Los 132 del backend están en su §10 y los 51 del frontend en su §12 |
| ARQ-15 | §2 · El agente no busca su contexto, lo recibe | BE:P-33, BE:P-81 | CUBIERTO | — |
| ARQ-16 | §2 · Quien escribe no aprueba: escritor, editor, juez y extractor separados | BE:P-81, BE:P-83, BE:P-86, BE:P-90 | CUBIERTO | — |
| ARQ-17 | §2 · Determinista antes que modelo | BE:P-40, BE:P-82 | CUBIERTO | — |
| ARQ-18 | §2 · El canon manda sobre el texto | BE:P-96 | CUBIERTO | — |
| ARQ-19 | §2 · Nada se sobrescribe | BE:P-06, BE:P-17 | CUBIERTO | — |
| ARQ-20 | §2 · El orquestador no acumula: todo su conocimiento está en SQLite | BE:P-21, BE:P-57 | CUBIERTO | — |
| ARQ-21 | §3 · El ensamblador de paquetes como pieza propia, y conviene que no tenga nada de inteligente | BE:P-33 | CUBIERTO | — |
| ARQ-22 | §3 · Core Domain con una sola implementación y dos puntos de ejecución | BE:P-40, BE:P-46, BE:P-116 | CUBIERTO | — |
| ARQ-23 | §4 · Extracción previa y entrevistador que solo pregunta por lo vacío o ambiguo | BE:P-68, BE:P-180, FE:IMP-47, FE:IMP-48 | CUBIERTO | El encargo por conversación lleva al entrevistador la descripción libre y presenta sus rondas en el gate |
| ARQ-24 | §4 · Los tres bloques de campos del `Brief` | BE:P-64 | CUBIERTO | — |
| ARQ-25 | §4 · Los diales de la frontera viajan por `canon_obra.estilo_json` hasta el bloque 6 | BE:P-37, BE:P-76 | CUBIERTO | — |
| ARQ-26 | §4 · `evento_ancla` opcional y orientativo, contrastado en el `@model_validator` | BE:P-65 | CUBIERTO | — |
| ARQ-27 | §4 · Cuarentena del texto libre y extracción a filas tipadas; el bruto no llega a ningún prompt | BE:P-66, BE:P-67 | CUBIERTO | — |
| ARQ-28 | §4 · Contradicciones detectadas por Pydantic y traducidas a pregunta | BE:P-65, BE:P-68 | CUBIERTO | — |
| ARQ-29 | §4 · Una sesión, tres `WebSearch` y tres `WebFetch`, seis dimensiones, impuesto por el arnés | BE:P-29, BE:P-69 | CUBIERTO | — |
| ARQ-30 | §4 · Cada `WebFetch` acotado a 10.000 tokens | BE:P-30 | CUBIERTO | — |
| ARQ-31 | §4 · El hecho con enunciado, estado, fuentes, `fase_run_id` y cita de 300 caracteres | BE:P-70 | CUBIERTO | — |
| ARQ-32 | §4 · Rehacer no contamina el corpus | BE:P-71 | CUBIERTO | — |
| ARQ-145 | §4 · Modo exhaustivo de la investigación: ocho sesiones dirigidas en serie, elegido al crear la novela y guardado en el estado | BE:P-153, BE:P-154 | CUBIERTO | Es `A-122` de la matriz del backend |
| ARQ-33 | §4 · Verificador de respaldo sin red, por lotes de veinte, que escribe `respaldo` —con veredicto parcial y su añadido en `sin_respaldo`— y limita la firmeza sin borrar ni bloquear | BE:P-72 | CUBIERTO | — |
| ARQ-34 | §4 · El arquitecto inventa Premisa y Tema y construye canon y escaleta jerárquica | BE:P-75 | CUBIERTO | — |
| ARQ-35 | §4 · El hueco: una única llamada, tope de cinco, invención autorizada que no se topa sino que se cuenta | BE:P-77, BE:P-78 | CUBIERTO | — |
| ARQ-36 | §4 · Los hechos que encuentra la micro-sesión pasan por el verificador en `FillGap`; los inventados no | BE:P-77 | CUBIERTO | — |
| ARQ-37 | §4 · Sello del corpus al aprobar la escaleta; de solo lectura a partir de ahí | BE:P-79 | CUBIERTO | — |
| ARQ-157 | §4 · Cada hueco lleva escena, dimensión y afirmación propuesta, y el hecho que lo cubre se ancla a su escena | BE:P-77 | CUBIERTO | La forma exacta, en `specs/trama-rehacible/plan.md`, TR-02 a TR-05 |
| ARQ-158 | §4, §10 · Rehacer la Trama la sustituye, con la anterior, los comentarios y los avisos delante del arquitecto; `canon_obra.fase_run_id` distingue rehacer de volver de un hueco | BE:P-75 | CUBIERTO | TR-01, TR-11 y TR-12 |
| ARQ-159 | §4, §11c · La revisión de la escaleta se guarda, no cierra el gate, repara la cobertura y evalúa la cronología en Python cuando no hay `lake` | BE:P-80 | CUBIERTO | TR-06 a TR-10, TR-13 y TR-14 |
| ARQ-38 | §4 · El bucle por capítulo en seis pasos | BE:P-81, BE:P-82, BE:P-83, BE:P-86, BE:P-87 | CUBIERTO | — |
| ARQ-39 | §4 · El escritor redacta el capítulo entero de una vez | BE:P-81 | CUBIERTO | — |
| ARQ-40 | §4 · `Validate` en dos pasadas, con el extractor dentro y antes de `ApproveChapter` | BE:P-82, BE:P-83 | CUBIERTO | — |
| ARQ-41 | §4 · Las filas del extractor cuelgan del intento, no del capítulo | BE:P-85 | CUBIERTO | — |
| ARQ-42 | §4 · Fase 5: juez sin escritura, `render_visual` antes del `commit`, PDF desde la ruta de lectura, sin gate humano | BE:P-90, BE:P-92, BE:P-94, BE:P-185, FE:IMP-22, FE:IMP-23, FE:IMP-26, FE:IMP-30, FE:IMP-53 | CUBIERTO | El PDF se imprime desde la ruta del frontend; quien lo conduce es `publication/` |
| ARQ-43 | §4 · Fase 6: resolver, modificar el hecho, regenerar afectados, invalidar barato, manifiesto nuevo y diff | BE:P-95, BE:P-96, BE:P-97, BE:P-98, BE:P-99, BE:P-186, FE:IMP-18, FE:IMP-20, FE:IMP-21, FE:IMP-25, FE:IMP-54 | CUBIERTO | La petición entra por la página del lector (IMP-20) y el diff sale por dos superficies |
| ARQ-44 | §5 · La tabla de roles con su entrada, su salida y sus herramientas | BE:P-27, BE:P-32 | CUBIERTO | — |
| ARQ-45 | §5 · Solo el investigador tiene acceso a internet | BE:P-06, BE:P-74, BE:P-123 | CUBIERTO | — |
| ARQ-46 | §5 · La varianza del juez se mide, no se supone | BE:P-121 | CUBIERTO | — |
| ARQ-138 | §5 · El contrato de salida viaja con la llamada: la puerta de invocación adjunta al prompt el JSON Schema del modelo Pydantic del rol, dentro de su techo | BE:P-27 | CUBIERTO | Es el `A-118` de la matriz del backend |
| ARQ-47 | §6 · Siete bloques con sus techos, 12.000 en total | BE:P-33, BE:P-34, BE:P-150, BE:P-151 | CUBIERTO | — |
| ARQ-48 | §6 · El bloque 4 lleva el texto íntegro de N−1 | BE:P-36 | CUBIERTO | — |
| ARQ-49 | §6 · Bloques 2, 4 y 5 llenados por relevancia semántica, con `k = 8` | BE:P-23, BE:P-35 | CUBIERTO | — |
| ARQ-50 | §6 · Truncado por prioridad, con el bloque 3 como último en tocarse | BE:P-38 | CUBIERTO | — |
| ARQ-51 | §6 · El paquete se persiste entero y se enlaza desde su span | BE:P-39 | CUBIERTO | — |
| ARQ-52 | §7 · `intake_*`, con las filas como verdad y el JSON del brief como fotografía | BE:P-08, BE:P-66 | CUBIERTO | — |
| ARQ-53 | §7 · `mundo_*`, con `estado`, `respaldo` y `sin_respaldo` separados y la firmeza calculada al leer | BE:P-09, BE:P-16, BE:P-72 | CUBIERTO | — |
| ARQ-54 | §7 · `canon_*`, con `canon_arco`, `canon_arco_hito` y `canon_obra.homenajeado_id` | BE:P-10, BE:P-75 | CUBIERTO | — |
| ARQ-55 | §7 · `plan_*`, con `dato_id` anulable en `plan_anclaje` | BE:P-11 | CUBIERTO | — |
| ARQ-56 | §7 · `texto_*`, con `uso_hecho`, `uso_hito` y `continuidad` | BE:P-12 | CUBIERTO | — |
| ARQ-57 | §7 · `cronologia_*`, que mezcla deliberadamente lo histórico y lo narrativo | BE:P-13 | CUBIERTO | — |
| ARQ-58 | §7 · `arnes_*`, las ocho tablas de estado del sistema | BE:P-14, BE:P-16 | CUBIERTO | — |
| ARQ-59 | §7 · `vec_*`, los tres índices `vec0` con sus metadatos y auxiliares | BE:P-15, BE:P-25 | CUBIERTO | — |
| ARQ-60 | §7 · Nunca un `UPDATE` sobre un capítulo; la versión es el manifiesto | BE:P-12, BE:P-17, FE:IMP-07, FE:IMP-15 | CUBIERTO | De aquí sale que toda ruta de lectura lleve el número de versión |
| ARQ-61 | §7 · `uso_hecho` a granularidad de escena, agregada a capítulo | BE:P-85 | CUBIERTO | — |
| ARQ-62 | §8 · `fase_run` con `input_run_id` y las cuatro operaciones sobre un solo camino de código | BE:P-14, BE:P-58, BE:P-141, BE:P-142 | CUBIERTO | — |
| ARQ-63 | §8 · Ramificar es copiar el fichero y escribir `procedencia` | BE:P-102, BE:P-113 | CUBIERTO | — |
| ARQ-64 | §8 · La edición humana dispara la maquinaria de la Fase 6, con re-sello y reembedding | BE:P-26, BE:P-101 | CUBIERTO | — |
| ARQ-65 | §9 · Los nodos se llaman igual que las acciones de PlusCal, y la identidad se comprueba sobre nombres **y aristas** | BE:P-55, BE:P-62, BE:P-133 | CUBIERTO | La lectura de `Aristas` sigue en pie con la especificación escrita directamente en TLA+, pero el cuerpo de §11d y su registro de cambios discrepan sobre la forma de la especificación. Ver la nota de ARQ-78 |
| ARQ-66 | §9 · La máquina de estados con sus aristas, y `Fail` como estado declarado | BE:P-56, BE:P-60, BE:P-128 | CUBIERTO | — |
| ARQ-67 | §9 · `ResumeFromCheckpoint` como arista de entrada a cualquier nodo | BE:P-58 | CUBIERTO | — |
| ARQ-68 | §10 · `interrupt()`, el estado en disco y la invocación que termina | BE:P-103 | CUBIERTO | — |
| ARQ-69 | §10 · Las cuatro decisiones: aprobar, rehacer con comentario, editar, abortar | BE:P-104 | CUBIERTO | — |
| ARQ-70 | §10 · `Notifier` con Telegram, solo para avisar; la decisión se toma en el PC | BE:P-105, BE:P-109 | CUBIERTO | — |
| ARQ-71 | §10 · Notificaciones informativas, desactivadas por defecto | BE:P-106 | CUBIERTO | — |
| ARQ-72 | §10 · El *timeout* aparca; nunca se auto-aprueba | BE:P-107 | CUBIERTO | — |
| ARQ-142 | §10 · Tres avisos fuera de gate —parada, final y aparcamiento— que salen siempre, también en batch, y nunca cambian el resultado de la invocación | BE:P-140 | CUBIERTO | Es `A-119` de la matriz del backend |
| ARQ-73 | §10 · `gates.enabled = false` desactiva los cinco para el modo batch | BE:P-02, BE:P-108, BE:P-120 | CUBIERTO | — |
| ARQ-74 | §11 · Los once validadores programáticos, cada uno en su punto de ejecución | BE:P-31, BE:P-41, BE:P-42, BE:P-43, BE:P-44, BE:P-80, BE:P-89, BE:P-92, BE:P-143, FE:IMP-23, FE:IMP-27 | CUBIERTO | `render_visual` es uno de los once: el nodo es de `publication/` (P-92, que sirve el manifiesto candidato por interceptación), y las anclas y la interceptabilidad son del frontend |
| ARQ-75 | §11 · Los cinco validadores semánticos, tres de ellos no bloqueantes, con los avisos que viajan | BE:P-43, BE:P-72, BE:P-88, BE:P-90, BE:P-122, BE:P-152 | CUBIERTO | — |
| ARQ-76 | §11 · Los cuatro invariantes de Lean, verificados por `decide` | BE:P-47, BE:P-49 | CUBIERTO | El proyecto Lake está en `formal/lean/`, y `P-47` y `P-49` ya apuntan ahí |
| ARQ-77 | §11 · Lean en tres puntos: escaleta, pasada del extractor y publicación | BE:P-80, BE:P-84, BE:P-91, BE:P-97 | CUBIERTO | — |
| ARQ-78 | §11 · TLA+ directo sobre las seis fases, con `Extract` como acción propia, los **cinco invariantes de estado** —incluido `CorpusSelladoNoSeToca`— y `PreviousVersionPreserved` como propiedad temporal | BE:P-61, BE:P-115, BE:P-133 | CUBIERTO | **Resuelto.** El cuerpo de §11d se reescribió para decir lo que su registro de cambios y el código ya decían, y `P-61` recoge los cinco invariantes y las dos propiedades temporales |
| ARQ-79 | §11 · *Liveness* bajo equidad débil, y TLC en desarrollo y no en cada generación | BE:P-61, BE:P-63 | CUBIERTO | La especificación y su modelo están en `formal/tla/`, y el registro de contraejemplos es `docs/iteraciones.md`; `P-61`, `P-63` y `P-133` ya apuntan ahí |
| ARQ-110 | §11 · §11 delega en `verification.md` el plan de verificación completo: técnica, clase de confianza y gate por riesgo | BE:P-04, BE:P-05, BE:P-07, BE:P-45, BE:P-49, BE:P-112, BE:P-114, BE:P-115, BE:P-116, BE:P-117, BE:P-118, BE:P-119, BE:P-120, BE:P-121, BE:P-122, BE:P-123, BE:P-124 | CUBIERTO | — |
| ARQ-112 | §11 · §11e `inventario_del_plan`: rutas y símbolos del plan contra el árbol y a la inversa, informando **en dos cubos** | BE:P-129, FE:IMP-33 | CUBIERTO | `P-129` promete leer todo `specs/*/plan.md`, pero su parser **solo recoge filas `P-nn`** y su dirección inversa solo recorría `backend/src/`. Desde R-08 lee también las filas `IMP-nn` y recorre `frontend/src/**` |
| ARQ-113 | §11 · §11e `registro_de_validadores`: el registro **es el cableado**, con la ruta como cadena, y se comparan **tres tablas por pares** sobre los once de §11a. **Bloquea** | BE:P-131, BE:P-132 | CUBIERTO | — |
| ARQ-114 | §11 · §11e `anclas_de_procedencia`: ancla de docstring en las dos direcciones, con la inversa acotada a §3 y §4 de la spec del backend. Solo el backend: el frontend se traza por el inventario y los requisitos. Informa | BE:P-130 | CUBIERTO | — |
| ARQ-115 | §11 · §11e y §9: `identidad_nodo_accion` compara **nombres y aristas**, leyendo la definición `Aristas` que gobierna el `Next`. **Bloquea** | BE:P-62, BE:P-133 | CUBIERTO | — |
| ARQ-80 | §12 · La tabla de techos por rol, los diez | BE:P-32 | CUBIERTO | — |
| ARQ-81 | §12 · La guarda que rechaza la llamada antes de emitirla | BE:P-28 | CUBIERTO | — |
| ARQ-82 | §12 · Los hooks `PreToolUse` y `PostToolUse`, programados una vez en `commons/agents` | BE:P-29, BE:P-30 | CUBIERTO | — |
| ARQ-83 | §12 · El semáforo que sumaría los techos si las micro-sesiones se paralelizaran | BE:P-134 | CUBIERTO | El semáforo sigue siendo la salida *si algún día* se paralelizan; **no se construye**. P-134 afirma por construcción la condición que hoy lo hace innecesario: las micro-sesiones corren en serie |
| ARQ-84 | §13 · El manifiesto que sostiene la auditabilidad | BE:P-93 | CUBIERTO | — |
| ARQ-85 | §13 · La estabilidad métrica, declarada y publicada | BE:P-121 | CUBIERTO | — |
| ARQ-86 | §13 · No se promete el mismo texto: la evidencia es el PDF commiteado con su manifiesto | BE:P-124 | CUBIERTO | — |
| ARQ-87 | §14 · Una sesión por novela y un span por invocación, con su nombre | BE:P-50 | CUBIERTO | — |
| ARQ-88 | §14 · *Scores* de los tres tipos de validador y decisiones de gate en la traza | BE:P-51, BE:P-123 | CUBIERTO | — |
| ARQ-89 | §14 · Prompts en Langfuse como fuente de verdad; *skills* y `CLAUDE.md` por hash | BE:P-52 | CUBIERTO | — |
| ARQ-90 | §14 · Exportación OTLP nativa, opcional y de la que nada depende | BE:P-53 | CUBIERTO | — |
| ARQ-91 | §14 · `total_cost_usd` etiquetado siempre como estimación en cliente | BE:P-51 | CUBIERTO | — |
| ARQ-92 | §15 · Palabras prohibidas en tres niveles, normalizando antes de comparar | BE:P-41 | CUBIERTO | — |
| ARQ-93 | §15 · Datos personales que no salen del fichero, y texto libre que nunca llega en bruto | BE:P-67, BE:P-74, BE:P-118, FE:IMP-06, FE:IMP-32, FE:IMP-56, FE:IMP-57 | CUBIERTO | Del lado del frontend: ninguna copia en el navegador (`FE:IMP-32`) y ninguna petición a terceros (`FE:IMP-06`) |
| ARQ-94 | §15 · Audit log de las decisiones de policy, de gate y de las ediciones humanas | BE:P-101, BE:P-104 | CUBIERTO | — |
| ARQ-95 | §16 · La pila técnica de §16.1 | BE:P-01, BE:P-94, BE:P-105, FE:IMP-01, FE:IMP-29 | CUBIERTO | — |
| ARQ-96 | §16 · Los cuatro usos de los embeddings | BE:P-35, BE:P-95, BE:P-125, BE:P-126 | CUBIERTO | — |
| ARQ-97 | §16 · El índice se escribe en la misma transacción que la fila, y la edición humana dispara el reembedding | BE:P-24, BE:P-26 | CUBIERTO | — |
| ARQ-98 | §16 · El modelo de embeddings viaja en el manifiesto | BE:P-93 | CUBIERTO | — |
| ARQ-99 | §16 · No se usan claves de partición | BE:P-23 | CUBIERTO | — |
| ARQ-100 | §16 · La carga de `sqlite-vec` se comprueba al abrir y nunca degrada en silencio | BE:P-19, BE:P-128 | CUBIERTO | — |
| ARQ-101 | §16 · La organización del backend *package by feature*, con el grafo en `commons/graph/` | BE:P-01, BE:P-55 | CUBIERTO | — |
| ARQ-102 | §16 · El frontend en FSD v2.1 con Steiger informando sin bloquear | FE:IMP-02, FE:IMP-03, FE:IMP-04 | CUBIERTO | Dejó de estar fuera de alcance al escribirse `specs/frontend/plan.md`, y la matriz del backend ya no lo lista como excluido |
| ARQ-103 | §16 · Dos puntos de entrada sobre un solo camino de código | BE:P-57, BE:P-109, BE:P-113, BE:P-138 | CUBIERTO | — |
| ARQ-104 | §16 · La invocación que reanuda un gate corre en el proceso de la CLI que decide | BE:P-109 | CUBIERTO | — |
| ARQ-105 | §16 · Cerrojo de fichero por novela; quien llega segundo es rechazado, no encolado | BE:P-59, BE:P-113, BE:P-128, FE:IMP-21 | CUBIERTO | Del lado del frontend significa no encolar ni reintentar solo ante un `409` |
| ARQ-143 | §16 · Un capítulo que agotó sus reintentos se reabre con `storymaker reintentar`, sin tocar lo aprobado | BE:P-144 | CUBIERTO | — |
| ARQ-150 | §16.5 · **La interfaz opera la novela entera**: encargar, lanzar, seguir, consultar salidas, decidir y continuar | BE:P-160, BE:P-161, BE:P-181, FE:IMP-39, FE:IMP-40, FE:IMP-41, FE:IMP-42, FE:IMP-43, FE:IMP-44, FE:IMP-47, FE:IMP-48 | CUBIERTO | Es `ARQ-42` del frontend y `A-130` del backend |
| ARQ-151 | §16.5 · **Lo que ejecuta el grafo lo lanza la API como CLI aparte**, y el servidor no guarda procesos en memoria | BE:P-162, BE:P-164, FE:IMP-35 | CUBIERTO | `ARQ-43` y `A-131` |
| ARQ-152 | §16.5 · **Seguimiento sondeando el fichero**, con actividad interpretada | BE:P-160, FE:IMP-36, FE:IMP-41 | CUBIERTO | `ARQ-44` |
| ARQ-153 | §16.5 · **Tablero tipo Jira** donde arrastrar aprueba o rehace tras confirmar, con las publicadas en un listado debajo | FE:IMP-39, FE:IMP-55 | CUBIERTO | `ARQ-45` |
| ARQ-154 | §16.5, §10 · Editar es corregir filas antes de decidir; abortar solo en Intake | BE:P-162, BE:P-165, BE:P-166, FE:IMP-42 | CUBIERTO | `ARQ-46`, `A-132` y `A-135` |
| ARQ-155 | §16.5 · Desbloquear solo con el proceso muerto | BE:P-163, FE:IMP-41 | CUBIERTO | `ARQ-48` y `A-133` |
| ARQ-156 | §16.5, U-17 · Acciones solo locales y en JSON, servidor en `127.0.0.1` | BE:P-162 | CUBIERTO | `A-134` |
| ARQ-106 | §16 · El directorio `proyectos/` es el registro; no hay base de datos global de novelas | BE:P-111, FE:IMP-39 | CUBIERTO | — |
| ARQ-107 | §16 · Ningún endpoint reanuda una ejecución, y la API queda abierta por decisión declarada (U-17) | BE:P-109, BE:P-110, BE:P-136, FE:IMP-08, FE:IMP-09 | CUBIERTO | El frontend no envía ni guarda credenciales, y ninguna de sus dos variables es un secreto; U-17 con fila en `verification.md` §5 |
| ARQ-108 | §16 · Las mitigaciones de §18 que son código: recuento por dimensión, tope de fetch, recuento de afectados, carga comprobada, varianza medida | BE:P-19, BE:P-30, BE:P-73, BE:P-100, BE:P-121 | CUBIERTO | — |
| ARQ-109 | §16 · Los valores por defecto de §19, parametrizables y con nombre | BE:P-02, BE:P-03, FE:IMP-29, FE:IMP-31 | CUBIERTO | — |
| ARQ-116 | §18 · Los documentos pueden ser coherentes y estar equivocados: la familia de §11e comprueba que código y especificación dicen lo mismo, no que lo que dicen sea correcto | BE:P-135 | CUBIERTO | Su mitigación no es código sino **inspección**. P-135 la convierte en entregable: sin acta de grilling y de revisión no hay constancia de que ocurriera |
| ARQ-117 | §16.3 · Juego mínimo de capas `app/ pages/ shared/`; `widgets/` no se usa y `features/`/`entities/` no se crean de entrada | FE:IMP-02 | CUBIERTO | — |
| ARQ-118 | §16.3 · `pages/reading`: lector, índice, navegación, selección de fragmento y petición de cambio | FE:IMP-14, FE:IMP-15, FE:IMP-20 | CUBIERTO | — |
| ARQ-119 | §16.3 · `pages/characters`: fichas de personajes y lugares | FE:IMP-16 | CUBIERTO | El endpoint pasó a ser `GET /novelas/{id}/versiones/{n}/personajes` en la spec del backend |
| ARQ-120 | §16.3 · `pages/cover`: portada, dedicatoria y nota del autor | FE:IMP-17 | CUBIERTO | El **bloque de paratexto** lo devuelve el endpoint de versión (`BE:P-110`) |
| ARQ-121 | §16.3 · `pages/versions`: historial, diff de manifiestos y novedades | FE:IMP-18, FE:IMP-25 | CUBIERTO | — |
| ARQ-122 | §16.3 · `shared/api`: cliente de la API y tipos de transporte, **sin reglas de negocio** | FE:IMP-05, FE:IMP-09, FE:IMP-10 | CUBIERTO | — |
| ARQ-123 | §16.3 · `shared/ui`: kit de componentes | FE:IMP-11 | CUBIERTO | — |
| ARQ-124 | §16.3 · `shared/lib`: utilidades y hooks | FE:IMP-12 | CUBIERTO | — |
| ARQ-125 | §16.3 · `shared/config`: rutas y variables de entorno | FE:IMP-08 | CUBIERTO | — |
| ARQ-126 | §16.3 · `app/`: providers, router, estilos globales y fuentes | FE:IMP-06, FE:IMP-07 | CUBIERTO | — |
| ARQ-127 | §16.3 · **API pública por segmento** de `shared`, no un `shared/index.ts` único | FE:IMP-02 | CUBIERTO | Criterio de hecho de IMP-02: el índice único no existe |
| ARQ-128 | §16.3 · Las dos reglas de importación: solo de capas estrictamente inferiores, y ningún cruce entre slices de la misma capa | FE:IMP-03, FE:IMP-04, FE:IMP-08 | CUBIERTO | Los constructores de ruta de IMP-08 son lo que evita el cruce entre páginas |
| ARQ-129 | §16.3 · **Assets junto al código que los usa**; estilos globales y fuentes en `app/` | FE:IMP-06 | CUBIERTO | — |
| ARQ-130 | §16.3 · La petición de cambio se ejerce **dentro del lector**; extracción a `features/change-request/` solo si aparece un segundo consumidor | FE:IMP-20 | CUBIERTO | La condición de extracción está escrita en §4.2 de la spec del frontend |
| ARQ-131 | §4 Fase 5 · Contenido de la lectura web: **índice navegable, ficha de personajes y lugares enlazada a sus capítulos, portada con dedicatoria** | FE:IMP-14, FE:IMP-16, FE:IMP-17, FE:IMP-24 | CUBIERTO | Son los tres objetos que `render_visual` mira |
| ARQ-132 | §4 Fase 1 · La **Nota del autor** como paratexto que declara licencias y personajes históricos | FE:IMP-17 | CUBIERTO | La ambigüedad que R-04 anotó está resuelta: §16.3 asigna la nota del autor a `pages/cover/` |
| ARQ-133 | §16.3 · `pages/library`, declarada como pantalla propia, y `pages/print`, la novela entera en un documento | FE:IMP-39, FE:IMP-22, FE:IMP-23, FE:IMP-24, FE:IMP-25 | CUBIERTO | Cada una nace de una decisión ya tomada: el directorio como registro y el PDF impreso desde la ruta de lectura |
| ARQ-134 | §16.3 · **Cliente único**: ningún módulo fuera de `shared/api` emite red, y aquí es **condición de G5** | FE:IMP-09, FE:IMP-27 | CUBIERTO | Es lo que permite interceptar; sin ello `render_visual` juzgaría un render distinto del que se publica |
| ARQ-135 | §16.4 · **FastAPI sirve el frontend construido**, un solo origen, URL base en la configuración | BE:P-136, FE:IMP-26 | CUBIERTO | Un solo origen es lo que hace que el PDF sea literalmente lo que se ve |
| ARQ-136 | §4 Fase 5 · El navegador ve la versión candidata porque se le **sirven las peticiones interceptadas** desde el manifiesto de la transacción abierta | BE:P-92, FE:IMP-27 | CUBIERTO | Cierra el hueco que R-05 y R-06 dejaron a la vista: el validador que sostiene G5 no tenía forma de ver lo que juzga |
| ARQ-139 | §2, §15, §16.4 · **De una novela no vive nada en dos sitios**: el frontend no guarda copia local —ni almacenamiento del navegador, ni caché persistente, ni *service worker*— y no pide nada a terceros | FE:IMP-32, FE:IMP-56, FE:IMP-57, FE:IMP-06 | CUBIERTO | Es `ARQ-37` de la matriz del frontend. Antes lo afirmaba la spec y ningún criterio de hecho lo miraba |
| ARQ-140 | §16.1 · El PDF **conserva los enlaces internos** que necesitan el índice navegable y la página de novedades | FE:IMP-24, FE:IMP-25, FE:IMP-30 | CUBIERTO | Es `ARQ-38` de la matriz del frontend; estaba realizado y le faltaba la fila |
| ARQ-141 | §16.3 · **Una API pública por slice**: cada slice de `pages/` expone su `index.ts` y nadie importa su interior | FE:IMP-02 | CUBIERTO | Es `ARQ-39` de la matriz del frontend. `ARQ-127` cubre los segmentos de `shared` y no las slices |

---

## 2. Huérfanos del plan

Ítems de plan que no aparecen en la columna `IMP-IDs` de ninguna fila del inventario. El recorrido inverso completo de cada mitad vive en su matriz; aquí se listan solo los que quedan sin ancla.

| IMP-ID | Descripción | Resolución |
|---|---|---|
| FE:IMP-28 | Pruebas de componente e integración con MSW sobre los contratos de `shared/api`, incluidos los siete casos de error de §9 de la spec del frontend | JUSTIFICADO · Tarea transversal de verificación, no una decisión de la arquitectura: nace de `verification.md` §3.5 y rinde cuentas en G1 |

**Los 135 ítems del plan del backend están enlazados**, comprobado sobre el fichero y no a ojo: la lista de ítems de este inventario cubre `P-01` a `P-135` sin dejar ninguno fuera. Del frontend quedan enlazados 32 de 33.

---

## 3. Hallazgos del recorrido

Nueve cosas que este recorrido dejó por escrito.

| # | Hallazgo | Resolución |
|---|---|---|
| R-01 | `ARQ-83`, el semáforo que sumaría los techos de las micro-sesiones concurrentes, no tenía ítem: estaba declarado fuera de alcance porque la arquitectura lo condiciona a que algún día se paralelicen. Pero **la condición de la que cuelga esa exclusión —que corren en serie— tampoco la afirmaba nadie**, y el peor caso de §12 descansaba sobre una costumbre | Nuevo **P-134** en el plan del backend: `fill_gap` es secuencial y una prueba falla si se abre una segunda sesión sin cerrar la anterior. El semáforo sigue siendo la salida el día que se paralelicen |
| R-02 | `ARQ-116`, «los documentos pueden ser coherentes y estar equivocados», tenía por mitigación una inspección que ningún entregable recogía | Nuevo **P-135**: acta de grilling y de revisión por documento. Sin acta no hay constancia de que la inspección ocurriera, que es exactamente lo que el riesgo describe |
| R-03 | `ARQ-102`, el frontend en Feature-Sliced Design con Steiger, estaba declarado fuera de alcance en la matriz del backend porque no existía plan que lo recogiera | Cubierto por `FE:IMP-02`, `FE:IMP-03` y `FE:IMP-04` desde que existe `specs/frontend/plan.md` |
| R-04 | Dieciséis requisitos del frontend —las capas, las páginas, los segmentos de `shared`, las dos reglas de importación, los assets, el contenido de la lectura web y la Nota del autor— no figuraban en ninguna matriz | Entran como `ARQ-117` a `ARQ-132`. `ARQ-132` es **la única ambigüedad de la arquitectura** que el recorrido encontró: nombra la Nota del autor y no dice en qué superficie se enseña |
| R-05 | **RESUELTO.** La arquitectura se contradecía consigo misma en §11d: su cuerpo dice «PlusCal traducido» y enumera cuatro invariantes de seguridad, mientras su registro de cambios declara que la especificación se escribe directamente en TLA+ y añade un quinto, `CorpusSelladoNoSeToca` | El Autor decidió que manda lo ya decidido y escrito en código: §11d se reescribió entero —TLA+ directo, `Mueve(de, a)` sobre `Aristas`, cinco invariantes de estado y `PreviousVersionPreserved` como propiedad temporal— y la decisión bajó a `verification.md`, a la spec y al plan del backend |
| R-06 | **RESUELTO.** Los artefactos formales no estaban donde los documentos decían. La arquitectura declara `spec/harness.tla · harness.cfg` y `lean/` en el árbol de §16.3, y el plan del backend apunta a `spec/harness.tla` (`P-61`, `P-133`), `lean/lakefile.lean` (`P-49`), `lean/StoryMaker/` (`P-47`) y `docs/contraejemplos.md` (`P-63`). En disco están en `formal/tla/`, `formal/lean/lakefile.toml` y `docs/iteraciones.md` El Autor decidió a favor de `formal/`: el árbol de §16.3 pasa a declarar `formal/tla/` y `formal/lean/`, y `P-47`, `P-49`, `P-61`, `P-63` y `P-133` apuntan ya a los ficheros reales. `P-129` deja de nacer en rojo |
| R-07 | **RESUELTO.** `.claude/mcp.json` no existía. El árbol de §16.3 lo declaraba como sitio de Playwright MCP y `FE:IMP-29` lo nombraba por eso, pero el servidor está en `.mcp.json` de la raíz, que es donde Claude Code lee la configuración MCP de un proyecto | El árbol de §16.3 declara ya `.mcp.json` en la raíz, que es donde está el fichero y donde Claude Code lo lee, y `FE:IMP-29` lo nombra |
| R-08 | **RESUELTO.** `BE:P-129` prometía leer «todo `specs/*/plan.md`», pero su parser solo recoge filas que empiezan por `\| **P-` y su dirección inversa solo recorre `backend/src/storymaker/`: las rutas del plan del frontend no las comprueba nadie | Entra `FE:IMP-33`, compartido con `P-129` y `P-139`; §7.1 nº 21 de la spec del backend y `P-129` declaran las filas `IMP-nn` y el recorrido de `frontend/src/**`, y la prueba lo hace (It-16 en `docs/iteraciones.md`) |
| R-09 | **RESUELTO.** `BE:P-136` nombraba `Settings.frontend_dist` y no la URL base que §16.4 exige «declarada en la configuración»; `FE:IMP-26` nombraba solo la URL base. Ninguno de los dos campos existe todavía en `commons/config.py` | `P-136`, REQ-BE-113 y `FE:IMP-26` nombran ya los dos campos. Siguen sin existir en el código, y no hace falta hasta que haya `dist/` que servir |

**Las tres filas que dependían de huecos del backend ya no dependen de nada.** `ARQ-119` y `ARQ-120` tienen sus dos endpoints contratados en §5 de la spec del backend, y `ARQ-74` tiene en §4 Fase 5 de la arquitectura el mecanismo con el que el navegador ve el manifiesto candidato. El comportamiento degradado que el plan del frontend declaraba mientras tanto se ha retirado.

---

## 4. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | Entran `ARQ-157` a `ARQ-159`: los huecos con escena, rehacer la Trama y la revisión de la escaleta, sobre `BE:P-75`, `BE:P-77` y `BE:P-80`, con la forma exacta en `specs/trama-rehacible/plan.md` | Se mueve con §4 de la arquitectura y la spec `trama-rehacible` en la misma operación |
| 2026-09-24 | Donde está `FE:IMP-56` entra también `FE:IMP-57`: los temas de la aplicación y del libro, que también se guardan como preferencia | Se mueve con la spec del frontend, §4.6 y §8 |
| 2026-09-24 | `ARQ-93, ARQ-139` suman `FE:IMP-56`: las preferencias de lectura, lo único que el navegador guarda | Se mueve con la spec del frontend, §1 y §4.6 |
| 2026-09-24 | ARQ-33 y ARQ-53 recogen el veredicto parcial y `sin_respaldo` | Se propagan §4 y §7 de la arquitectura en la misma operación que el plan |
| 2026-09-24 | ARQ-33, ARQ-36 y ARQ-53 se reescriben: el verificador escribe solo `respaldo`, los hechos de la micro-sesión pasan por él y la firmeza se calcula al leer; ARQ-53 gana P-72 | Se propagan §4 y §7 de la arquitectura en la misma operación que el plan |
| 2026-09-24 | `ARQ-153` suma `FE:IMP-55`: las publicadas salen del tablero a un listado | Se mueve con la matriz del frontend |
| 2026-09-24 | `ARQ-43` suma `BE:P-186` y `FE:IMP-54`, el candidato de Regeneración elegido en el gate; `ARQ-42` suma `BE:P-185` y `FE:IMP-53`, el PDF con maqueta de libro | Se mueve con las matrices de las dos mitades, que los recogen en la misma operación |
| 2026-09-24 | Entra `ARQ-145`: el modo exhaustivo de la investigación de §4, con `BE:P-153` y `BE:P-154` | Se mueve con la matriz del backend, que recoge `A-122` en la misma operación |
| 2026-09-24 | `ARQ-23` suma `BE:P-180`, `FE:IMP-47` y `FE:IMP-48`, y `ARQ-150` suma `BE:P-181`, `FE:IMP-47` y `FE:IMP-48` | El encargo por conversación |
| 2026-09-24 | Entran **ARQ-150 a ARQ-156**, la operación desde la interfaz de arq. §16.5; IMP-13 e IMP-19, retirados, se sustituyen por IMP-39 o desaparecen de sus filas | La matriz consolidada se mueve con las dos mitades |
| 2026-09-24 | `ARQ-47` suma `BE:P-150` y `BE:P-151`, y `ARQ-75` suma `BE:P-152`. El inventario no cambia | Se mueve con la matriz del backend en la misma operación |
| 2026-09-24 | `ARQ-74` suma `BE:P-143` y entra `ARQ-143`, reintentar un capítulo, con `BE:P-144`. El inventario sube de 142 a 143 filas | Se mueve con la matriz del backend, que recoge `A-120` en la misma operación |
| 2026-09-24 | `ARQ-62` suma `BE:P-141` y `BE:P-142`. El inventario no cambia | Se mueve con la matriz del backend, que recoge los dos ítems en `A-62` en la misma operación |
| 2026-09-24 | Entra `ARQ-142`: los tres avisos fuera de gate de §10, con `BE:P-140`. El inventario sube de 141 a 142 filas | Se mueve con la matriz del backend, que recoge `A-119` en la misma operación |
| 2026-09-24 | La descripción de ARQ-114 dice que `anclas_de_procedencia` alcanza solo al backend | §11e de la arquitectura lo fija así; la fila se mueve con el documento que cambia |
| 2026-09-24 | ARQ-70, ARQ-104 y ARQ-107 se reescriben: Telegram solo avisa y los gates se deciden en el PC | Decisión del Autor en §10 de la arquitectura |
| 2026-09-24 | **R-07, R-08 y R-09 quedan resueltos**: §16.3 de la arquitectura declara `.mcp.json` en la raíz, `BE:P-129` lee las filas `IMP-nn` y recorre `frontend/src/**`, y `BE:P-136` nombra la URL base. Cambia la nota de `ARQ-112` | Las tres discrepancias se decidieron arriba y bajaron hasta el código en la misma operación |
| 2026-09-24 | Tercera pasada del frontend: entran `ARQ-139` a `ARQ-141` —nada de una novela en dos sitios, los enlaces internos del PDF y la API pública por slice—; `FE:IMP-32` y `FE:IMP-33` se reparten entre `ARQ-93`, `ARQ-111`, `ARQ-112` y `ARQ-137`; `ARQ-107` recoge `FE:IMP-08`; `ARQ-120` y `ARQ-132` dejan de contar una ambigüedad ya resuelta; entran R-07, R-08 y R-09, y la tabla de hallazgos vuelve a ser una sola. El inventario sube de 138 a 141 filas | La matriz del frontend encontró quince vacíos al leer la arquitectura entera y no solo §4 y §16. Esta vista se mueve con ella en la misma operación: una consolidación que va un paso por detrás afirma en verde lo que ya no ha comprobado |
| 2026-09-24 | Entra `ARQ-138`: el contrato de salida viaja con la llamada, realizado por `BE:P-27` | La primera ejecución real cayó porque ningún rol recibía la forma de su salida, y la arquitectura lo fijó en §5. El inventario sube de 137 a 138 filas |
| 2026-09-23 | `ARQ-111` recoge **`BE:P-137`**, el validador que comprueba estas matrices | Esta matriz afirmaba cobertura de todo el repositorio y era el único artefacto de §11e que nadie miraba. Ahora la mira la suite, y se verificó rompiéndola a propósito |
| 2026-09-23 | Entran `ARQ-133` a `ARQ-136`: las dos pantallas declaradas, el **cliente único** como condición de G5, **FastAPI sirviendo el `dist/`** y la **interceptación** de la versión candidata | Son las cuatro cosas que la arquitectura fijó al resolver las costuras del frontend. Estaban en los planes y no en el inventario, que es el fallo simétrico del hueco y el que menos se nota |
| 2026-09-23 | Tercera pasada, tras resolver el Autor las dos discrepancias: **R-05 y R-06 quedan cerrados** —§11d reescrito y los artefactos formales declarados en `formal/`— y con ellos las notas de `ARQ-65`, `ARQ-74`, `ARQ-76`, `ARQ-78`, `ARQ-79`, `ARQ-119` y `ARQ-120`. Entran en la trazabilidad `BE:P-136`, que sirve el frontend construido | Los hallazgos de una matriz solo valen si alguien los cierra, y cerrarlos sin moverla la deja afirmando un problema que ya no existe |
| 2026-09-23 | Segunda pasada: se anota que `CorpusSelladoNoSeToca` **ya está escrito** en `formal/tla/` aunque ni el cuerpo de §11d ni `P-61` lo nombren, y entra **R-06**, la deriva entre las rutas que los documentos declaran para los artefactos formales y el sitio donde están | Una matriz que afirma cobertura sobre ítems que apuntan a ficheros inexistentes afirma menos de lo que parece. Ninguna de las dos se corrige aquí: las dos son decisión del Autor sobre la fuente de verdad |
| 2026-09-23 | Versión inicial: 132 requisitos de arquitectura trazados contra los 135 ítems del plan del backend y los 31 del frontend, con un huérfano justificado, dos ítems nuevos y cero huecos | Las dos mitades tenían matriz y el repositorio no tenía ninguna: nadie podía decir, mirando un solo documento, que la arquitectura entera tuviera quien la implementara |
| 2026-09-23 | Entra `ARQ-137`: cada spec enumera sus requisitos con identificador propio, derivados de su propio contenido, y `BE:P-139` lo comprueba | Las specs eran prosa continua y no había forma de leerlas como una lista de compromisos ni de señalar cuál quedó sin implementar. El inventario sube de 136 a 137 filas, que es la única dirección en la que se mueve |
