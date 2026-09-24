# Matriz de trazabilidad — arquitectura ↔ plan del backend

Este documento no decide nada: **comprueba**. Recorre [`architecture.md`](../../docs/architecture.md) requisito a requisito y [`plan.md`](plan.md) ítem a ítem, y deja escrito que ninguna decisión fijada se queda sin código que la realice y que ningún ítem de trabajo llegó al plan sin que alguien lo pidiera.

Se recorre en las dos direcciones porque los dos fallos son distintos y ninguno se ve desde el otro lado. Un requisito sin ítem es **una decisión que nadie va a implementar**: la arquitectura la da por cerrada y el código nunca la tendrá. Un ítem sin requisito es **trabajo que nadie pidió**: puede ser una buena idea, pero no está acordada, y el sitio donde se acuerda es la arquitectura, no el plan.

**Convenio.** `A-nn` identifica un requisito de la arquitectura y lleva el apartado del que sale. `P-nn` identifica un ítem del plan. Los identificadores no se reutilizan: si un requisito desaparece, su fila se queda con estado `retirado` en lugar de dejar el hueco a otro.

---

## 1. Arquitectura → plan

### §1 · Decisiones fijadas

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-01 | Motor de orquestación LangGraph con estado explícito, un nodo por acción de la especificación TLA+ | P-54, P-55 | Cubierto |
| A-02 | Agentes por Claude Agent SDK, todos en Haiku 4.5, con modelo, herramientas y turnos fijados por invocación | P-27, P-32 | Cubierto |
| A-03 | Los nueve roles, cada uno con su punto de invocación | P-27, P-66, P-68, P-69, P-72, P-75, P-81, P-83, P-86, P-90 | Cubierto |
| A-04 | Los validadores son nodos del grafo, nunca herramientas; las aristas condicionales leen booleanos de Python | P-06, P-56 | Cubierto |
| A-05 | Paso de contexto por empuje determinista en siete bloques | P-33 | Cubierto |
| A-06 | Un único fichero SQLite por novela; checkpoint y dominio en la misma transacción | P-18, P-19, P-20, P-21, P-87 | Cubierto |
| A-07 | Capítulos inmutables más manifiesto | P-12, P-17, P-98 | Cubierto |
| A-08 | Grafo de `fase_run` inmutables: rehacer, reanudar, ramificar y regenerar son la misma operación | P-58, P-71, P-102 | Cubierto |
| A-09 | Cinco gates bloqueantes con notificación, desactivables en batch | P-103, P-127, P-73, P-78, P-89, P-100 | Cubierto |
| A-10 | Validación formal en dos planos: Lean 4 para la historia, TLA+ para el arnés | P-47, P-48, P-61 | Cubierto |
| A-11 | Observabilidad en Langfuse con spans manuales autorizados y OTLP opcional | P-50, P-53 | Cubierto |
| A-12 | Presupuesto de 100.000 tokens concurrentes, garantizado por construcción | P-28, P-32 | Cubierto |
| A-13 | Pila: FastAPI *package by feature* con `commons`; React en FSD v2.1 | P-01 · frontend en §3 | Cubierto en su mitad |
| A-14 | Embeddings FastEmbed local, 384 dimensiones, indexados con `sqlite-vec` | P-22, P-23 | Cubierto |
| A-111 | Correspondencia documento↔código comprobada por **tests de trazabilidad y no por lectura**: lo que la spec declara y el plan nombra tiene quien lo compruebe en CI | P-62, P-129, P-130, P-131, P-132, P-133, P-137 | Cubierto |
| A-117 | Cada spec **enumera sus requisitos con identificador propio** —`REQ-BE-nn` y `REQ-FE-nn`—, derivados de su propio contenido, con el apartado del que nacen y los ítems que los realizan en su propia fila | P-139 | Cubierto |

### §2 · Principios

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-15 | El agente no busca su contexto, lo recibe | P-33, P-81 | Cubierto |
| A-16 | Quien escribe no aprueba: escritor, editor, juez y extractor separados | P-81, P-83, P-86, P-90 | Cubierto |
| A-17 | Determinista antes que modelo | P-40, P-82 | Cubierto |
| A-18 | El canon manda sobre el texto | P-96 | Cubierto |
| A-19 | Nada se sobrescribe | P-06, P-17 | Cubierto |
| A-20 | El orquestador no acumula: todo su conocimiento está en SQLite | P-21, P-57 | Cubierto |

### §3 · Topología

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-21 | El ensamblador de paquetes como pieza propia, y conviene que no tenga nada de inteligente | P-33 | Cubierto |
| A-22 | Core Domain con una sola implementación y dos puntos de ejecución | P-40, P-46, P-116 | Cubierto |

### §4 · Las seis fases

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-122 | Modo exhaustivo de la investigación: ocho sesiones dirigidas en serie, elegido al crear la novela y guardado en el estado | P-153, P-154 | Cubierto |
| A-23 | Extracción previa y entrevistador que solo pregunta por lo vacío o ambiguo | P-68, P-180 | Cubierto |
| A-24 | Los tres bloques de campos del `Brief` | P-64 | Cubierto |
| A-25 | Los diales de la frontera viajan por `canon_obra.estilo_json` hasta el bloque 6 | P-37, P-76 | Cubierto |
| A-26 | `evento_ancla` opcional y orientativo, contrastado en el `@model_validator` | P-65 | Cubierto |
| A-27 | Cuarentena del texto libre y extracción a filas tipadas; el bruto no llega a ningún prompt | P-66, P-67 | Cubierto |
| A-28 | Contradicciones detectadas por Pydantic y traducidas a pregunta | P-65, P-68 | Cubierto |
| A-29 | Una sesión, tres `WebSearch` y tres `WebFetch`, seis dimensiones, impuesto por el arnés | P-29, P-69 | Cubierto |
| A-30 | Cada `WebFetch` acotado a 10.000 tokens | P-30 | Cubierto |
| A-31 | El hecho con enunciado, estado, fuentes, `fase_run_id` y cita de 300 caracteres | P-70 | Cubierto |
| A-32 | Rehacer no contamina el corpus | P-71 | Cubierto |
| A-33 | Verificador de respaldo sin red, por lotes de veinte, que degrada sin borrar ni bloquear | P-72 | Cubierto |
| A-34 | El arquitecto inventa Premisa y Tema y construye canon y escaleta jerárquica | P-75 | Cubierto |
| A-35 | El hueco: una única llamada, tope de cinco, invención autorizada que no se topa sino que se cuenta | P-77, P-78 | Cubierto |
| A-36 | Los hechos del arquitecto no pasan por el verificador de respaldo | P-77 | Cubierto |
| A-37 | Sello del corpus al aprobar la escaleta; de solo lectura a partir de ahí | P-79 | Cubierto |
| A-38 | El bucle por capítulo en seis pasos | P-81, P-82, P-83, P-86, P-87 | Cubierto |
| A-39 | El escritor redacta el capítulo entero de una vez | P-81 | Cubierto |
| A-40 | `Validate` en dos pasadas, con el extractor dentro y antes de `ApproveChapter` | P-82, P-83 | Cubierto |
| A-41 | Las filas del extractor cuelgan del intento, no del capítulo | P-85 | Cubierto |
| A-42 | Fase 5: juez sin escritura, `render_visual` antes del `commit`, PDF desde la ruta de lectura, sin gate humano | P-90, P-92, P-94 | Cubierto |
| A-43 | Fase 6: resolver, modificar el hecho, regenerar afectados, invalidar barato, manifiesto nuevo y diff | P-95, P-96, P-97, P-98, P-99 | Cubierto |

### §5 · Los nueve roles

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-44 | La tabla de roles con su entrada, su salida y sus herramientas | P-27, P-32 | Cubierto |
| A-45 | Solo el investigador tiene acceso a internet | P-06, P-74, P-123 | Cubierto |
| A-46 | La varianza del juez se mide, no se supone | P-121 | Cubierto |
| A-118 | El contrato de salida viaja con la llamada: la puerta de invocación adjunta al prompt el JSON Schema del modelo Pydantic del rol, dentro de su techo | P-27 | Cubierto |

### §6 · Paso de contexto

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-47 | Siete bloques con sus techos, 12.000 en total | P-33, P-34, P-150, P-151 | Cubierto |
| A-48 | El bloque 4 lleva el texto íntegro de N−1 | P-36 | Cubierto |
| A-49 | Bloques 2, 4 y 5 llenados por relevancia semántica, con `k = 8` | P-23, P-35 | Cubierto |
| A-50 | Truncado por prioridad, con el bloque 3 como último en tocarse | P-38 | Cubierto |
| A-51 | El paquete se persiste entero y se enlaza desde su span | P-39 | Cubierto |

### §7 · Modelo de datos

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-52 | `intake_*`, con las filas como verdad y el JSON del brief como fotografía | P-08, P-66 | Cubierto |
| A-53 | `mundo_*`, con `estado` y `respaldo` separados | P-09, P-16 | Cubierto |
| A-54 | `canon_*`, con `canon_arco`, `canon_arco_hito` y `canon_obra.homenajeado_id` | P-10, P-75 | Cubierto |
| A-55 | `plan_*`, con `dato_id` anulable en `plan_anclaje` | P-11 | Cubierto |
| A-56 | `texto_*`, con `uso_hecho`, `uso_hito` y `continuidad` | P-12 | Cubierto |
| A-57 | `cronologia_*`, que mezcla deliberadamente lo histórico y lo narrativo | P-13 | Cubierto |
| A-58 | `arnes_*`, las ocho tablas de estado del sistema | P-14, P-16 | Cubierto |
| A-59 | `vec_*`, los tres índices `vec0` con sus metadatos y auxiliares | P-15, P-25 | Cubierto |
| A-60 | Nunca un `UPDATE` sobre un capítulo; la versión es el manifiesto | P-12, P-17 | Cubierto |
| A-61 | `uso_hecho` a granularidad de escena, agregada a capítulo | P-85 | Cubierto |

### §8 · El grafo de ejecuciones de fase

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-62 | `fase_run` con `input_run_id` y las cuatro operaciones sobre un solo camino de código | P-14, P-58, P-141, P-142 | Cubierto |
| A-63 | Ramificar es copiar el fichero y escribir `procedencia` | P-102, P-113 | Cubierto |
| A-64 | La edición humana dispara la maquinaria de la Fase 6, con re-sello y reembedding | P-26, P-101 | Cubierto |

### §9 · Máquina de estados

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-65 | Los nodos se llaman igual que las acciones de la especificación TLA+, y la identidad se comprueba sobre nombres **y aristas** | P-55, P-62, P-133 | Cubierto |
| A-66 | La máquina de estados con sus aristas, y `Fail` como estado declarado | P-56, P-60, P-128 | Cubierto |
| A-67 | `ResumeFromCheckpoint` como arista de entrada a cualquier nodo | P-58 | Cubierto |

### §10 · Gates humanos

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-68 | `interrupt()`, el estado en disco y la invocación que termina | P-103 | Cubierto |
| A-69 | Las cuatro decisiones: aprobar, rehacer con comentario, editar, abortar | P-104 | Cubierto |
| A-70 | `Notifier` con Telegram, solo para avisar; la decisión se toma en el PC | P-105, P-109 | Cubierto |
| A-71 | Notificaciones informativas, desactivadas por defecto | P-106 | Cubierto |
| A-72 | El *timeout* aparca; nunca se auto-aprueba | P-107 | Cubierto |
| A-119 | Tres avisos fuera de gate —parada, final y aparcamiento— que salen siempre, también en batch, y nunca cambian el resultado de la invocación | P-140 | Cubierto |
| A-73 | `gates.enabled = false` desactiva los cinco para el modo batch | P-02, P-108, P-120 | Cubierto |

### §11 · Validación

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-74 | Los once validadores programáticos, cada uno en su punto de ejecución | P-31, P-41, P-42, P-43, P-44, P-80, P-89, P-92, P-143 | Cubierto |
| A-75 | Los cinco validadores semánticos, tres de ellos no bloqueantes, con los avisos que viajan | P-43, P-72, P-88, P-90, P-122, P-152 | Cubierto |
| A-76 | Los cuatro invariantes de Lean, verificados por `decide` | P-47, P-49 | Cubierto |
| A-77 | Lean en tres puntos: escaleta, pasada del extractor y publicación | P-80, P-84, P-91, P-97 | Cubierto |
| A-78 | TLA+ directo sobre las seis fases, con `Extract` como acción propia, los **cinco invariantes de estado** —incluido `CorpusSelladoNoSeToca`— y `PreviousVersionPreserved` como propiedad temporal | P-61, P-115, P-133 | Cubierto |
| A-79 | *Liveness* bajo equidad débil, y TLC en desarrollo y no en cada generación | P-61, P-63 | Cubierto |
| A-110 | §11 delega en `verification.md` el plan de verificación completo: técnica, clase de confianza y gate por riesgo | P-04, P-05, P-07, P-45, P-49, P-112, P-114 a P-124 | Cubierto |
| A-112 | §11e `inventario_del_plan`: rutas y símbolos del plan contra el árbol y a la inversa, informando **en dos cubos** | P-129 | Cubierto |
| A-113 | §11e `registro_de_validadores`: el registro **es el cableado**, con la ruta como cadena, y se comparan **tres tablas por pares** sobre los once de §11a. **Bloquea** | P-131, P-132 | Cubierto |
| A-114 | §11e `anclas_de_procedencia`: ancla de docstring en las dos direcciones, con la inversa acotada a §3 y §4 de la spec del backend. Solo el backend: el frontend se traza por el inventario y los requisitos. Informa | P-130 | Cubierto |
| A-115 | §11e y §9: `identidad_nodo_accion` compara **nombres y aristas**, leyendo la definición `Aristas` que gobierna el `Next`. **Bloquea** | P-62, P-133 | Cubierto |

### §12 · Presupuesto de contexto

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-80 | La tabla de techos por rol, los diez | P-32 | Cubierto |
| A-81 | La guarda que rechaza la llamada antes de emitirla | P-28 | Cubierto |
| A-82 | Los hooks `PreToolUse` y `PostToolUse`, programados una vez en `commons/agents` | P-29, P-30 | Cubierto |
| A-83 | El semáforo que sumaría los techos si las micro-sesiones se paralelizaran | P-134 | Cubierto en su condición: P-134 afirma la serialidad que hoy lo hace innecesario. El semáforo sigue fuera de alcance |

### §13 · Reproducibilidad

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-84 | El manifiesto que sostiene la auditabilidad | P-93 | Cubierto |
| A-85 | La estabilidad métrica, declarada y publicada | P-121 | Cubierto |
| A-86 | No se promete el mismo texto: la evidencia es el PDF commiteado con su manifiesto | P-124 | Cubierto |

### §14 · Observabilidad

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-87 | Una sesión por novela y un span por invocación, con su nombre | P-50 | Cubierto |
| A-88 | *Scores* de los tres tipos de validador y decisiones de gate en la traza | P-51, P-123 | Cubierto |
| A-89 | Prompts en Langfuse como fuente de verdad; *skills* y `CLAUDE.md` por hash | P-52 | Cubierto |
| A-90 | Exportación OTLP nativa, opcional y de la que nada depende | P-53 | Cubierto |
| A-91 | `total_cost_usd` etiquetado siempre como estimación en cliente | P-51 | Cubierto |

### §15 · Guardrails y policy

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-92 | Palabras prohibidas en tres niveles, normalizando antes de comparar | P-41 | Cubierto |
| A-93 | Datos personales que no salen del fichero, y texto libre que nunca llega en bruto | P-67, P-74, P-118 | Cubierto |
| A-94 | Audit log de las decisiones de policy, de gate y de las ediciones humanas | P-101, P-104 | Cubierto |

### §16 · Pila y organización

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-95 | La pila técnica de §16.1 | P-01, P-94, P-105 | Cubierto |
| A-96 | Los cuatro usos de los embeddings | P-35, P-95, P-125, P-126 | Cubierto |
| A-97 | El índice se escribe en la misma transacción que la fila, y la edición humana dispara el reembedding | P-24, P-26 | Cubierto |
| A-98 | El modelo de embeddings viaja en el manifiesto | P-93 | Cubierto |
| A-99 | No se usan claves de partición | P-23 | Cubierto |
| A-100 | La carga de `sqlite-vec` se comprueba al abrir y nunca degrada en silencio | P-19, P-128 | Cubierto |
| A-101 | La organización del backend *package by feature*, con el grafo en `commons/graph/` | P-01, P-55 | Cubierto |
| A-102 | El frontend en FSD v2.1 con Steiger informando sin bloquear | `specs/frontend/plan.md`: IMP-02, IMP-03, IMP-04 | Cubierto en el plan del frontend |
| A-103 | Dos puntos de entrada sobre un solo camino de código | P-57, P-109, P-113, P-138 | Cubierto |
| A-104 | La invocación que reanuda un gate corre en el proceso de la CLI que decide | P-109 | Cubierto |
| A-105 | Cerrojo de fichero por novela; quien llega segundo es rechazado, no encolado | P-59, P-113, P-128 | Cubierto |
| A-120 | Un capítulo que agotó sus reintentos se reabre con `storymaker reintentar`, sin tocar lo aprobado | P-144 | Cubierto |
| A-106 | El directorio `proyectos/` es el registro; no hay base de datos global de novelas | P-111 | Cubierto |
| A-107 | Ningún endpoint reanuda una ejecución, y la API queda abierta por decisión declarada (U-17) | P-109, P-110, P-136, P-138 | Cubierto |

### §18 y §19 · Riesgos y valores por defecto

| # | Requisito | Ítems | Estado |
|---|---|---|---|
| A-108 | Las mitigaciones de §18 que son código: recuento por dimensión, tope de fetch, recuento de afectados, carga comprobada, varianza medida | P-19, P-30, P-73, P-100, P-121 | Cubierto |
| A-109 | Los valores por defecto de §19, parametrizables y con nombre | P-02, P-03 | Cubierto |
| A-116 | §18 · «Los documentos pueden ser coherentes y estar equivocados»: la familia §11e comprueba que código y especificación dicen lo mismo, no que lo que dicen sea correcto | P-135 | Cubierto por inspección: el acta de grilling y de revisión es su entregable |
| A-130 | §16.5 · La API **calcula el estado** de cada novela y de cada fase, del fichero y sin memoria, y sirve panel, gate y salidas | P-160, P-161, P-181, P-183, P-184 | Cubierto |
| A-131 | §16.5 · **Lo que ejecuta el grafo lo lanza la API como CLI aparte**, desacoplado, con registro y `202` | P-162, P-164, P-182 | Cubierto |
| A-132 | §16.5 · **Las ediciones de un gate y la petición de cambio las escribe la API** tomando el cerrojo, con la maquinaria de `regeneration/` | P-162, P-166 | Cubierto |
| A-133 | §16.5 · **Solo se desbloquea un cerrojo cuyo proceso ha muerto** | P-162, P-163 | Cubierto |
| A-134 | §16.5, U-17 · **Acciones solo locales y en JSON**, sin CORS, con el servidor en `127.0.0.1` | P-162 | Cubierto |
| A-135 | §10 · **Abortar solo desde el gate de Intake** | P-165 | Cubierto |

---

## 2. Plan → arquitectura

Cada ítem del plan, con el requisito del que nace. **Ninguna fila está vacía**: un ítem sin requisito sería trabajo que nadie acordó.

| Ítem | Cubre | Ítem | Cubre |
|---|---|---|---|
| P-01 | A-13, A-101 | P-65 | A-26, A-28 |
| P-02 | A-73, A-109 | P-66 | A-27, A-52 |
| P-03 | A-109 | P-67 | A-93 |
| P-04 | A-110 | P-68 | A-23 |
| P-05 | A-110 | P-69 | A-29 |
| P-06 | A-04, A-19, A-22, A-45, A-93, A-97 | P-70 | A-31 |
| P-07 | A-110 | P-71 | A-08, A-32 |
| P-08 | A-52 | P-72 | A-33, A-75 |
| P-09 | A-53 | P-73 | A-09, A-108 |
| P-10 | A-54 | P-74 | A-45, A-93 |
| P-11 | A-55 | P-75 | A-34, A-54 |
| P-12 | A-07, A-56, A-60 | P-76 | A-25 |
| P-13 | A-57 | P-77 | A-35, A-36 |
| P-14 | A-58, A-62 | P-78 | A-09, A-35 |
| P-15 | A-59 | P-79 | A-37 |
| P-16 | A-53, A-58 | P-80 | A-74, A-77 |
| P-17 | A-07, A-19, A-60 | P-81 | A-15, A-38, A-39 |
| P-18 | A-06 | P-82 | A-17, A-40 |
| P-19 | A-06, A-100, A-108 | P-83 | A-16, A-40 |
| P-20 | A-06 | P-84 | A-74, A-77 |
| P-21 | A-06, A-20 | P-85 | A-41, A-61 |
| P-22 | A-14 | P-86 | A-38 |
| P-23 | A-14, A-49, A-99 | P-87 | A-06, A-38 |
| P-24 | A-97 | P-88 | A-75 |
| P-25 | A-59 | P-89 | A-09, A-74 |
| P-26 | A-64, A-97 | P-90 | A-42, A-75 |
| P-27 | A-02, A-03, A-44, A-118 | P-91 | A-77 |
| P-28 | A-12, A-81 | P-92 | A-42, A-74 |
| P-29 | A-29, A-82 | P-93 | A-84, A-98 |
| P-30 | A-30, A-82, A-108 | P-94 | A-42, A-95 |
| P-31 | A-74 | P-95 | A-43, A-96 |
| P-32 | A-02, A-44, A-80 | P-96 | A-18, A-43 |
| P-33 | A-05, A-15, A-21, A-47 | P-97 | A-43, A-77 |
| P-34 | A-47, A-75 | P-98 | A-07, A-43 |
| P-35 | A-49, A-96 | P-99 | A-43 |
| P-36 | A-48 | P-100 | A-09, A-108 |
| P-37 | A-25 | P-101 | A-64, A-94 |
| P-38 | A-50 | P-102 | A-08, A-63 |
| P-39 | A-51 | P-103 | A-09, A-68 |
| P-40 | A-17, A-22 | P-104 | A-69, A-94 |
| P-41 | A-74, A-92 | P-105 | A-70, A-95 |
| P-42 | A-74 | P-106 | A-71 |
| P-43 | A-74, A-75 | P-107 | A-72 |
| P-44 | A-74 | P-108 | A-73 |
| P-45 | A-110 | P-109 | A-70, A-103, A-104, A-107 |
| P-46 | A-22 | P-110 | A-107 |
| P-47 | A-10, A-76 | P-111 | A-106 |
| P-48 | A-10 | P-112 | A-110 |
| P-49 | A-76, A-110 | P-113 | A-63, A-103, A-105 |
| P-50 | A-11, A-87 | P-114 | A-110 |
| P-51 | A-88, A-91 | P-115 | A-78, A-110 |
| P-52 | A-89 | P-116 | A-22, A-110 |
| P-53 | A-11, A-90 | P-117 | A-110 |
| P-54 | A-01 | P-118 | A-93, A-110 |
| P-55 | A-01, A-65, A-101 | P-119 | A-110 |
| P-56 | A-04, A-66 | P-120 | A-73, A-110 |
| P-57 | A-20, A-103 | P-121 | A-46, A-85, A-108 |
| P-58 | A-08, A-62, A-67 | P-122 | A-75, A-110 |
| P-59 | A-105 | P-123 | A-45, A-88 |
| P-60 | A-66 | P-124 | A-86, A-110 |
| P-61 | A-10, A-78, A-79 | P-125 | A-96 |
| P-62 | A-65, A-111, A-115 | P-126 | A-96 |
| P-63 | A-79, A-110 | P-127 | A-09 |
| P-64 | A-24 | P-128 | A-66, A-100, A-105 |
| | | P-129 | A-111, A-112 |
| | | P-130 | A-111, A-114 |
| | | P-131 | A-113 |
| | | P-132 | A-111, A-113 |
| | | P-133 | A-65, A-78, A-115 |
| P-137 | A-111 |
| P-139 | A-117 |
| P-140 | A-119 |
| P-153 | A-122 |
| P-154 | A-122 |
| P-141 | A-62 |
| P-142 | A-62 |
| P-143 | A-74 |
| P-144 | A-120 |
| P-150 | A-47 |
| P-151 | A-47 |
| P-152 | A-75 |
| P-160 | A-130 |
| P-161 | A-130 |
| P-162 | A-131, A-132, A-133, A-134 |
| P-163 | A-133 |
| P-164 | A-131 |
| P-165 | A-135 |
| P-166 | A-132 |
| P-180 | A-23 |
| P-181 | A-130 |
| P-182 | A-131 |
| P-183 | A-130 |
| P-184 | A-130 |
| P-138 | A-103, A-107 |
| P-134 | A-83 |
| P-135 | A-116 |
| P-136 | A-103, A-107 |

---

## 3. Requisitos fuera del alcance de este plan

**Ninguno.** Este apartado listaba tres, y los tres se han cerrado: `A-102`, el frontend en FSD, lo cubre su propio plan desde que existe; `A-116`, la veracidad de los documentos, tiene entregable en `P-135`, el acta de grilling y de revisión; y `A-83`, el semáforo de sesiones concurrentes, tiene ítem para **su condición** en `P-134`, que afirma por construcción la serialidad de las micro-sesiones.

Conviene precisar lo último, porque no es una cobertura completa y decir que lo es sería justo lo que esta matriz existe para evitar: **el semáforo no se construye**. La arquitectura lo condiciona a que algún día las micro-sesiones se paralelicen, y lo que `P-134` garantiza es que hoy no lo están y que nadie podrá paralelizarlas por descuido sin que una prueba se queje. El día que se decida paralelizarlas, el semáforo vuelve a ser trabajo pendiente con el techo de 14.000 ya declarado en §12.

---

## 4. Hallazgos del recorrido

Lo que la comparación destapó, con lo que se hizo. Cuatro eran contradicciones entre documentos —y en esas manda la arquitectura— y seis eran huecos del plan.

| # | Hallazgo | Resolución |
|---|---|---|
| V-01 | La spec situaba los cuatro invariantes de Lean en la **pasada determinista** de `Validate`; la arquitectura los baja a la **pasada del extractor**, porque las filas de `cronologia_evento` con `origen = 'narrativo'` las escribe el extractor al leer el capítulo | Corregida la spec en §4.4 y §7.2c. Sin el cambio, Lean habría verificado en el capítulo N una cronología que llega hasta N−1 |
| V-02 | La spec declaraba Lean en dos puntos; la arquitectura declara **tres**, y el que faltaba era el más barato: la cronología deducida de la escaleta en el gate de Plotting | Corregida la spec en §3.7 y §7.2c, y recogido en P-80 |
| V-03 | La spec definía `arco_anclado` sobre «personaje principal», que es exactamente el concepto que la arquitectura descarta por no ser computable, y omitía el arco plano y la excepción del homenajeado | Corregida la spec en §7.2a: ≥3 escenas sobre `plan_escena_personaje`, arco plano admitido, homenajeado como única excepción. Recogido en P-42 |
| V-04 | §16.4 de la arquitectura citaba **U-16** como el riesgo de la API de lectura sin autenticación; en `verification.md` ese riesgo es **U-17**, y U-16 es la fiabilidad de `ejecucion_escaleta` y `arco_ejecutado` | Corregida la referencia en la arquitectura, con su fila en el registro de cambios |
| V-05 | Que los hechos del arquitecto no pasen por el verificador de respaldo no estaba dicho en ningún ítem, y quedaba a merced de que nadie lo implementara «por simetría» con Investigation | Declarado en P-77 |
| V-06 | El uso 3 de los embeddings —localizar hechos relevantes para el arquitecto sin volcarle el corpus entero— no tenía ítem | Nuevo P-125 |
| V-07 | El uso 4 —detectar repeticiones y auto-similitud entre capítulos como linter de prosa— no tenía ítem | Nuevo P-126 |
| V-08 | De los cinco gates, el de Intake era el único sin informe, pese a que la spec dice que se abre igualmente con lo que falte | Nuevo P-127 |
| V-09 | El semáforo de sesiones concurrentes de §12 no aparecía ni como ítem ni como exclusión | Declarado fuera de alcance en el plan §11 y en §3 de esta matriz |
| V-10 | Steiger y el frontend no aparecían ni como ítem ni como exclusión, pese a ser un validador con gate asignado en la spec | Declarado fuera de alcance en el plan §11 y en §3 de esta matriz |

---

## 5. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | `A-130` suma `P-184` | El PDF por la API |
| 2026-09-24 | `A-130` suma `P-183` | El nombre corto de los escenarios |
| 2026-09-24 | Entra `A-122` —el modo exhaustivo de la investigación— con sus ítems `P-153` y `P-154`, y la dirección inversa recoge los dos pares | La arquitectura fijó en §4 el modo exhaustivo. Una matriz que no lo recogiera afirmaría en verde una cobertura que no comprueba entera |
| 2026-09-24 | `A-131` suma `P-182` | El modo de investigación al encargar |
| 2026-09-24 | `A-23` suma `P-180` y `A-130` suma `P-181`; la dirección inversa recoge los dos | El encargo por conversación |
| 2026-09-24 | Entran **A-130 a A-135** (arq. §16.5 y la restricción de abortar en §10) con sus ítems P-160 a P-166 | La matriz se mueve con el documento que cambia. Los números saltan a 130 para no pisar los que otra línea de trabajo numera en paralelo |
| 2026-09-24 | `A-47` suma `P-150` y `P-151`, y `A-75` suma `P-152`; la dirección inversa recoge los tres pares | La arquitectura amplió en §6 los bloques 3 y 6 y en §11b el juicio de la continuidad |
| 2026-09-24 | `A-74` suma `P-143` y entra `A-120` —reintentar el capítulo que agotó sus reintentos— con `P-144`; la dirección inversa recoge los dos pares | La arquitectura fijó en §11a que `cobertura_capitulo` avisa y en §16.5 el comando `reintentar` |
| 2026-09-24 | `A-62` suma `P-141` y `P-142` —una `fase_run` por fase y el consumo contado en el transporte— y la dirección inversa recoge los dos pares | El plan del backend los declara al propagar §9.1 y §9.2 de la spec de ejecución real; §8 de la arquitectura es la decisión que realizan |
| 2026-09-24 | Entra `A-119` —los tres avisos fuera de gate— con su ítem `P-140`, y la dirección inversa recoge el par | La arquitectura fijó en §10 los avisos de parada, final y aparcamiento. Una matriz que no los recogiera afirmaría en verde una cobertura que no comprueba entera |
| 2026-09-24 | La descripción de A-114 dice que `anclas_de_procedencia` alcanza solo al backend | §11e de la arquitectura lo fija así; la fila se mueve con el documento que cambia |
| 2026-09-24 | A-70, A-104 y A-107 se reescriben: Telegram solo avisa, la reanudación de un gate corre en la CLI y ningún endpoint reanuda. P-109 cubre además A-70 | Se propaga la decisión del Autor en §10 y §16.4 de la arquitectura |
| 2026-09-24 | Entra `A-118` —el contrato de salida viaja con la llamada— con su ítem `P-27`, y la dirección inversa recoge el par | La arquitectura fijó en §5 cómo llega al rol la forma de su salida después de que la primera ejecución real cayera por no mandarla. Una matriz que no lo recogiera afirmaría en verde una cobertura que no comprueba entera |
| 2026-09-23 | Se propaga la reescritura de §11d —A-10, A-65 y A-78 dejan de hablar de PlusCal y A-78 recoge los cinco invariantes—, `A-83` y `A-102` dejan de estar fuera de alcance con `P-134` y el plan del frontend, y entran `P-134`, `P-135` y `P-136` en el recorrido inverso | La arquitectura resolvió su contradicción y aparecieron dos planes donde había uno. Una matriz que no se mueve con ellos afirma en verde una cobertura que ya no ha comprobado |
| 2026-09-23 | Se incorpora la familia **§11e** llegada a los tres documentos: entran A-111 a A-115 con sus ítems P-129 a P-133, A-65 pasa a comprobarse sobre nombres **y aristas**, y A-116 queda en §3 como requisito cuya mitigación es inspección y no código | La matriz se escribió antes de que §11e existiera, y una matriz desactualizada es peor que no tenerla: afirma en verde una cobertura que ya no ha comprobado |
| 2026-09-23 | Pasada de congruencia entre la spec y el plan: entra **P-128** —la taxonomía de errores—, que sube el plan a 128 ítems; se corrigen las filas de A-66, A-100 y A-105 | La comparación con la spec, y no con la arquitectura, destapó cuatro contratos sin ítem. La matriz se mantiene al día en la misma operación o deja de servir para nada |
| 2026-09-23 | Versión inicial: 110 requisitos de arquitectura y 127 ítems de plan, trazados en ambas direcciones, con diez hallazgos resueltos y dos requisitos declarados fuera de alcance | Un plan derivado a mano de un documento de mil líneas pierde cosas, y las pierde en silencio. La matriz convierte esa pérdida en una fila vacía que se ve |
| 2026-09-23 | Entra `A-117` —los requisitos enumerados de cada spec— con su ítem `P-139`, y la dirección inversa recoge el par | La arquitectura fijó el requisito como unidad que se traza contra el plan, y una matriz que no lo recogiera afirmaría en verde una cobertura que ya no comprueba entera |
