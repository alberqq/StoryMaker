# Auditoría de requisitos — StoryMaker

Auditoría de este repositorio contra [`REQUIREMENTS.md`](../REQUIREMENTS.md). **No se ha modificado código**: esta auditoría solo lee, ejecuta comprobaciones y escribe este fichero.

Fecha: 2026-09-23 · Rama: `zero` · Último commit: `89cf09a`

## Estado del repositorio en el momento de auditar

El repositorio ha pasado el tramo **H1 del plan de implementación**: andamiaje, puertas estáticas, configuración tipada y **persistencia** existen y se prueban. Las seis fases, los nueve agentes, el frontend y los artefactos de entrega —presentación, novela de muestra, vídeo— no existen todavía.

> **Aviso sobre la estabilidad del árbol.** `backend/` cambió cuatro veces mientras esta auditoría corría, porque otro proceso lo estaba construyendo en paralelo: la primera pasada encontró diecinueve `__init__.py` vacíos, la segunda contó cero ficheros, la tercera encontró H0 y la cuarta H1 completo con nueve ficheros de esquema SQL. Todas las evidencias corresponden a la **última pasada**. Si `backend/` vuelve a moverse, esta auditoría envejece con él.

Lo que hay, comprobado:

```
$ cd backend && .venv/Scripts/python.exe -m pytest -q
........................................................................ [ 92%]
......                                                                   [100%]
78 passed in 3.31s

$ find backend/src backend/tests -name "*.py" | grep -v __pycache__ | wc -l
48
$ ls backend/src/storymaker/commons/db/esquema/
arnes.sql  canon.sql  cronologia.sql  inmutabilidad.sql  intake.sql
mundo.sql  plan.sql   texto.sql       vec.sql
$ ls README.md .env.example .mcp.json ejemplos/brief-ejemplo.yaml
(los cuatro existen)
$ ls formal/tla/harness.tla formal/tla/harness.cfg formal/lean/lakefile.toml
(los tres existen)
$ ls evals/briefs/ | wc -l
5
$ find semgrep -type f | wc -l
6
```

Lo que no hay, comprobado:

```
$ ls presentacion/
(no existe)
$ find . -path ./.git -prune -o -name "*.pdf" -print
(sin resultados: ni novela de muestra ni deck ni anexos)
$ ls -a .claude/
.  ..  skills                   (sin hooks/, commands/ ni agents/)
$ find frontend -type f | wc -l
0
$ ls evals/resultados/
(no existe: ninguna eval se ha ejecutado)
```

Y lo que **el entorno impide comprobar**, que es una categoría distinta y conviene no mezclar con la anterior:

```
$ lake build
bash: lake: command not found          (tampoco hay elan)
$ java -version
bash: java: command not found          (resuelto: JRE portátil en el scratchpad,
                                        con el que TLC ya ha corrido)
$ command -v npx
                                       (sin Node: el MCP no se puede levantar)
```

De ahí el reparto de estados, que se lee en tres montones. Lo que **está hecho y comprobado** va a `CUMPLE`. Lo que **está escrito pero no se ha podido ejecutar por falta de herramienta** —el proyecto Lean sin `lake`, el servidor MCP sin Node— va a `PARCIAL`, nunca a `CUMPLE`: un fichero en el árbol no es una verificación, y llamarlo así sería el único error que una auditoría no puede permitirse.

TLA+ estaba en ese montón y ha salido de él. Se descargó un JRE portátil y `tla2tools.jar` al directorio temporal, y **TLC corrió de verdad**: encontró tres violaciones, las tres reales y ninguna cosmética, incluida una —que la liveness necesita equidad *fuerte* y no *débil*— que corrige una afirmación de §11d de la arquitectura. Vale la pena decirlo porque es la mejor defensa del método que hay en este repositorio: la especificación llevaba horas escrita y revisada, y los tres defectos seguían ahí. Lo que **depende de las fases o de generar una novela** sigue en `NO_CUMPLE`, con la evidencia apuntando al lugar donde la capacidad está *especificada*.

Los marcados `[M]` en `REQUIREMENTS.md` se registran como `MANUAL`, y los `OPT-*` como `NO_APLICA`.

---

## ENT — Entregables y estructura de repos

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| ENT-01 | CUMPLE | Los cinco existen: código (`backend/src/storymaker/`, 48 ficheros `.py`), [`README.md`](../README.md), brief de ejemplo en [`ejemplos/brief-ejemplo.yaml`](../ejemplos/brief-ejemplo.yaml), [`.env.example`](../.env.example) en la raíz y `/docs` con doce documentos | Que el brief sea *reproducible* no se ha podido comprobar: exige generar la novela, que es ENT-06 |
| ENT-02 | MANUAL | Repositorio externo, no presente en este árbol de trabajo | No verificable desde aquí; requiere comprobación humana en GitHub |
| ENT-03 | NO_CUMPLE | `ls presentacion/` → el directorio no existe | — |
| ENT-04 | NO_CUMPLE | `find . -path ./.git -prune -o -name "*.pdf" -print` → sin resultados; no hay directorio de anexos | — |
| ENT-05 | NO_CUMPLE | `ls presentacion/README.md` → no existe | Depende de ENT-03 |
| ENT-06 | NO_CUMPLE | La entrada existe —[`ejemplos/brief-ejemplo.yaml`](../ejemplos/brief-ejemplo.yaml), el mismo brief que cita el README— pero la salida no: `find . -name "*.pdf"` → sin resultados. Y no hay con qué generarla: de las seis fases solo hay carpetas vacías bajo `backend/src/storymaker/` | Desbloqueado a medias: ya hay brief que reproducir, falta el arnés que lo ejecute |
| ENT-07 | NO_CUMPLE | No hay `presentacion/` ni vídeo en el árbol, y [`README.md`](../README.md) no enlaza ninguno | De los tres artefactos de entrega que quedan, el único que no depende del código |
| ENT-08 | CUMPLE | `git log -p --all` filtrado por `sk-[a-zA-Z0-9]{20}`, `api_key =`, `secret =` y `ANTHROPIC_API_KEY =` → 4 coincidencias, las cuatro de prueba: dos `export SM_WEB_API_KEY=...` (placeholder literal) y dos con un valor dummy dentro de un test que **afirma que ese valor no aparece** en la salida. `backend/.env.example:6-13` declara los secretos de Telegram y Langfuse con el valor vacío. Además hay gitleaks en las dos puertas: `.pre-commit-config.yaml:12-14` (G0) y `.github/workflows/ci.yml:36-40` (G1) | Ninguna credencial real en el árbol ni en el historial, y dos barreras para que siga así |
| ENT-09 | MANUAL | Acción del Autor fuera del repositorio | `[M]` en `REQUIREMENTS.md` |

## CFG — Configuración (agente entrevistador)

La fase de Intake está especificada con detalle en `docs/architecture.md` §4 · Fase 1, y su carpeta `backend/src/storymaker/intake/` sigue conteniendo solo un `__init__.py` vacío: ni H0 ni H1 la implementan. Las tablas que la sostendrán sí existen ya (`commons/db/esquema/intake.sql`), lo que convierte a esta familia en la primera que se cerrará cuando empiece H4.

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| CFG-01 | NO_CUMPLE | Especificado en `docs/architecture.md:108-129` (tabla del `Brief`: `nombre_homenajeado`, `fecha_nacimiento`, `rol_epoca`, `genero`, `tono`, `n_capitulos`/`palabras_por_capitulo`). Sin código: `backend/src/storymaker/intake/__init__.py` está vacío | El diseño cubre todos los campos exigidos, incluidos rasgos (`rol_epoca`) y recuerdos (`elementos_personalizacion`) |
| CFG-02 | NO_CUMPLE | Especificado en `docs/architecture.md:127` (`palabras_prohibidas`, niveles `novela` y `destinatario`). Sin código | — |
| CFG-03 | NO_CUMPLE | Especificado en `docs/architecture.md:106` («el entrevistador solo pregunta por lo que sigue vacío o ambiguo»). Sin código ni test: los 78 tests que pasan son de configuración, persistencia y dobles, ninguno de intake | — |
| CFG-04 | NO_CUMPLE | Especificado en `docs/architecture.md:140`: un `@model_validator` de Pydantic con cuatro contradicciones (edad contra período, nacimiento contra evento ancla, tono festivo contra duelo, dato que coincide con palabra prohibida). No existe el modelo `Brief` ni test que lo cubra | El requisito pide un tipo de contradicción; el diseño declara cuatro |
| CFG-05 | NO_CUMPLE | Especificado en `docs/architecture.md:138` (tabla de cuarentena más extractor a hechos tipados). Sin código | — |
| CFG-06 | NO_CUMPLE | Especificado en `docs/architecture.md:138`: defensa estructural, el texto en bruto no llega al prompt del escritor. Sin test de injection en `backend/tests/` | El enfoque documentado es más fuerte que el exigido: aislamiento por esquema, no instrucción al modelo |
| CFG-07 | NO_CUMPLE | Especificado en `docs/architecture.md:106` (esquema `Brief` de Pydantic) y `specs/backend/spec.md:72` (§3, contratos de `commons/`). El único modelo Pydantic que existe es `Settings` (`backend/src/storymaker/commons/config.py:94`), que no es el brief | — |

## LEC — Lectura interactiva (web o PDF)

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| LEC-01 | CUMPLE | `docs/architecture.md:827-834`: se eligen **ambos**, web en React y PDF impreso con `page.pdf()` de Playwright sobre la misma ruta de lectura, con la razón escrita (si el PDF se maquetara aparte, web y PDF divergirían) | Requisito `[E]` de documentación, cubierto |
| LEC-02 | NO_CUMPLE | Especificado en `docs/architecture.md:215`. No hay frontend: `find frontend -type f` → 0. Nada que inspeccionar con browser MCP | — |
| LEC-03 | NO_CUMPLE | Especificado en `docs/architecture.md:215` y `specs/backend/plan.md:217` (tarea P-94, tramo H6). `backend/src/storymaker/publication/__init__.py` está vacío | — |
| LEC-04 | NO_CUMPLE | Especificado en `docs/architecture.md:215` («ficha de personajes y lugares enlazada a sus capítulos»). Sin artefacto que abrir | — |
| LEC-05 | NO_CUMPLE | Especificado en `docs/architecture.md:215` y `docs/architecture.md:902` (`cover/`, portada y dedicatoria). Sin artefacto | — |
| LEC-06 | NO_CUMPLE | Especificado en `docs/architecture.md:221` (§4 · Fase 6 Regeneration). `backend/src/storymaker/regeneration/__init__.py` está vacío | — |
| LEC-07 | NO_CUMPLE | Especificado en `docs/architecture.md:201`: índice hecho→capítulo construido por el extractor sobre la tabla `uso_hecho`. Sin esquema ni base de datos | La tabla de hechos que el requisito pide está diseñada |
| LEC-08 | NO_CUMPLE | Especificado en `docs/architecture.md:221-232`. Sin código de regeneración | — |
| LEC-09 | NO_CUMPLE | Especificado en `docs/architecture.md:232` («página de novedades en el PDF, distintivo en el índice web», por `JOIN` de dos manifiestos). Sin artefacto | — |
| LEC-10 | PARCIAL | Garantizado por estructura: `commons/db/esquema/inmutabilidad.sql` instala triggers que abortan cualquier `UPDATE` sobre el texto, el intento o la procedencia de un `capitulo_version`, y `texto.sql:31` (`version_capitulo`) es el manifiesto. Falta la regeneración que produzca una segunda versión: `regeneration/` está vacío | El cerrojo está puesto antes que aquello que encierra, que es el orden correcto |

## HAR — Harness

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| HAR-01 | PARCIAL | Los nueve roles existen como dominio tipado: `backend/src/storymaker/commons/config.py:25-36` (`class Rol(StrEnum)` con `ENTREVISTADOR` … `JUEZ`), probados en `backend/tests/unit/test_config.py:66` (`test_son_nueve`) y `:69` (`test_estan_los_que_declara_la_arquitectura`), dentro de los 22 tests que pasan. Ningún agente está implementado: las carpetas de las seis fases contienen solo `__init__.py` vacíos | El requisito pide tres roles; hay nueve declarados y cero implementados. El enum no es el rol, pero sí el contrato que los nombra |
| HAR-02 | MANUAL | `CLAUDE.md` existe en la raíz; su contenido completo es una línea, `@AGENTS.md`, que importa `AGENTS.md` (6.020 bytes: rama de trabajo, mapa de documentos, flujo spec-driven, verificación y operación) | `[E][M]`: el fichero existe; si está «cuidado y legible» lo juzga una persona. La indirección vía `AGENTS.md` es deliberada |
| HAR-03 | CUMPLE | `git ls-files .claude` → 48 ficheros; doce skills bajo `.claude/skills/`, cada una con su origen y su propósito en `.claude/skills/PROCEDENCIA.md:11-24` | Todas son de terceros, instaladas por copia; ninguna es propia del proyecto. El requisito pide «reutilizable», no «creada aquí» |
| HAR-04 | NO_CUMPLE | `ls -a .claude/` → solo `skills`; no hay `hooks/` ni `settings.json`. Los hooks que sí existen, en `.pre-commit-config.yaml`, validan Python (ruff, mypy, gitleaks), no capítulos. El hook de capítulo está especificado en `docs/architecture.md:804` | Hay hooks de repositorio, pero ninguno es el hook de validación de capítulo que pide el requisito |
| HAR-05 | PARCIAL | El policy engine no existe como hook, pero sus reglas sí se aplican estáticamente: `semgrep/` contiene seis reglas propias del arnés —`validador-no-es-tool.yaml`, `core-domain-puro.yaml`, `no-update-inmutables.yaml`, `pii-fuera-del-investigador.yaml`, `sin-red-fuera-del-investigador.yaml`, `indice-solo-por-embeddings.yaml`— ejecutadas en `.github/workflows/ci.yml:41-42`. El policy engine en ejecución está especificado en `docs/architecture.md:791` (§15) y no está implementado | La policy está vigilada en CI, no en el bucle de generación. Media puerta |
| HAR-06 | NO_CUMPLE | Especificado en `docs/architecture.md:614` (`schema_guard`: la salida de cada rol cumple su modelo Pydantic, en la salida de cada nodo agente). No existen tools ni nodos: `backend/src/storymaker/commons/validation/__init__.py` está vacío | — |
| HAR-07 | PARCIAL | La constante configurable existe y está probada: `backend/src/storymaker/commons/config.py:66` (`REINTENTOS_POR_CAPITULO: Final = 2`) y `:132` (`reintentos_por_capitulo: int = Field(default=…, ge=0)`), con `backend/tests/unit/test_config.py:89` y `:130` (`test_un_limite_fuera_de_rango_no_se_acepta`). El bucle que la consume no existe: está especificado en `docs/architecture.md:197` y `:509-513` (`Validate --> Fail : reintentos agotados`) | El límite está declarado y validado; no hay retry que limitar todavía |
| HAR-08 | PARCIAL | El límite está en código como constante con nombre: `backend/src/storymaker/commons/config.py:76` (`TOKENS_CONCURRENTES_MAXIMOS: Final = 100_000`), probado en `backend/tests/unit/test_config.py:52` (`test_presupuesto_de_contexto`). La guarda que lo **aplica** —techo por rol y rechazo de la llamada antes de emitirla— está especificada en `docs/architecture.md:739` y no implementada: `commons/context/` está vacío, y ninguno de los 78 tests toca el paso de contexto | Declarado sí, aplicado no. El diseño explica por qué no se vigila en vivo: el Agent SDK no expone el consumo de la sesión |

## MEM — Memoria

El tramo H1 cerró la mitad de esta familia. El esquema existe y se prueba —nueve ficheros en `commons/db/esquema/`, con `apertura.py` y `transaccion.py`—, así que lo que es **estructura** está en `CUMPLE`. Lo que necesita las fases para poblarse o consumirse sigue en `NO_CUMPLE`.

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| MEM-01 | CUMPLE | Nueve ficheros de esquema en `backend/src/storymaker/commons/db/esquema/` —`intake`, `mundo`, `canon`, `plan`, `texto`, `cronologia`, `arnes`, `vec` e `inmutabilidad`—, con `apertura.py` y `transaccion.py`. `cd backend && pytest -q` → `78 passed` | Las siete familias de §7 más los triggers de inmutabilidad |
| MEM-02 | CUMPLE | `commons/db/esquema/texto.sql:39` (`uso_hecho`) y `:48` (`uso_hito`), a granularidad de escena y agregables a capítulo | Es el índice del que dependen la regeneración selectiva de LEC-07 y LEC-08 |
| MEM-03 | CUMPLE | `commons/db/esquema/cronologia.sql:6` (`cronologia_evento`, con momento, lugar y origen) y `:19` (`cronologia_participante`) | Mezcla a propósito eventos históricos y narrativos: es en la mezcla donde aparece lo que Lean detecta |
| MEM-04 | NO_CUMPLE | Las tablas de origen existen (`cronologia.sql:6,19`) y el formato de destino también (`formal/lean/Cronologia/Generado.lean`), pero no hay nada que las una: `commons/formal/__init__.py` está vacío | Es exactamente LEAN-01 visto desde el otro lado |
| MEM-05 | NO_CUMPLE | Especificado en `docs/architecture.md:268` (§6, paso de contexto en siete bloques) y `:449` (`vec_resumen` con filtro `vigente = 1`, para no arrastrar resúmenes de intentos rechazados). `commons/context/` está vacío | — |
| MEM-06 | NO_CUMPLE | Especificado en `docs/architecture.md:27` y `:199`: checkpoint en la misma transacción que el capítulo. El esquema y la transacción ya existen (`commons/db/transaccion.py`), pero no hay grafo que checkpointear ni test de fallo simulado: `commons/graph/__init__.py` está vacío | — |

## VAL — Validadores

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| VAL-01 | NO_CUMPLE | Once validadores deterministas especificados en la tabla `docs/architecture.md:612-624`. Ninguno implementado: `backend/src/storymaker/commons/validation/__init__.py` está vacío | Diseño muy por encima del mínimo de tres; implementación nula |
| VAL-02 | NO_CUMPLE | `schema_guard` en `docs/architecture.md:614`; contratos en `specs/backend/spec.md:378` (§7). El único esquema validado hoy es `Settings` (`config.py:94`), que no es ni el brief ni la salida de un rol | — |
| VAL-03 | NO_CUMPLE | `nombres_exactos` en `docs/architecture.md:615`, con punto de ejecución post `WriteChapter`. Sin código ni test | — |
| VAL-04 | NO_CUMPLE | El rango existe como constante —`backend/src/storymaker/commons/config.py:52` (`RANGO_PALABRAS: Final = (1000, 1500)`), probado en `backend/tests/unit/test_config.py:21`— pero el validador `longitud_capitulo` de `docs/architecture.md:616` no está implementado | La constante coincide exactamente con el 1.000–1.500 del enunciado; falta quien la comprueba |
| VAL-05 | NO_CUMPLE | Tres validadores de cobertura contra SQLite en `docs/architecture.md:620-622`: `cobertura_anclada`, `cobertura_capitulo` y `cobertura_personalizacion`. Sin código ni base de datos | — |
| VAL-06 | PARCIAL | Documentado: `docs/architecture.md:624` (`render_visual` con Playwright MCP, dentro de `PublishVersion` y antes del `commit`) y `:828`. Playwright está declarado como extra en `backend/pyproject.toml:24`. El servidor ya está configurado en [`.mcp.json`](../.mcp.json), pero no se ha podido levantar (sin Node) y el validador no existe: `commons/validation/` está vacío | La parte `[E] docs` está cubierta; la parte `[C]` no |
| VAL-07 | NO_CUMPLE | Especificado en `docs/architecture.md:215` («rúbrica de siete criterios», salida solo como esquema de puntuaciones) y `:634` (§11b). El número de criterios ya es constante —`config.py:87` (`CRITERIOS_RUBRICA: Final = 7`)— pero el juez no existe | La rúbrica documentada excede los cuatro criterios exigidos |
| VAL-08 | MANUAL | `docs/architecture.md:260` reserva a la revisión humana «exactamente el asiento del juez», con la misma rúbrica y sin poder editar. No hay novela que revisar ni acta de revisión en el repo | `[E][M]`: requiere que una persona revise una novela, y ninguna existe todavía |
| VAL-09 | CUMPLE | Tabla en `docs/architecture.md:612-624`: una fila por validador con nombre, qué comprueba y punto de ejecución (salida de nodo agente, post `WriteChapter`, hook, gate de Plotting, gate de Writing, dentro de `PublishVersion`) | Requisito `[E]` de documentación, cubierto |
| VAL-10 | NO_CUMPLE | Especificado en `docs/architecture.md:80` y `:776` (§14). `langfuse` está en `backend/pyproject.toml:14` y las claves en `backend/.env.example:10-12`, pero `commons/obs/__init__.py` está vacío: no hay emisión de scores | Dependencia y configuración listas; instrumentación ausente |

## LEAN — Validador formal de la historia

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| LEAN-01 | NO_CUMPLE | El formato de destino existe y está ejemplificado en [`formal/lean/Cronologia/Generado.lean`](../formal/lean/Cronologia/Generado.lean), con personas, objetos fechados, eventos, momento, lugar y participantes. El **generador** que lo emite desde SQLite no: `backend/src/storymaker/commons/formal/__init__.py` sigue vacío | Las tablas de origen ya existen (`commons/db/esquema/cronologia.sql:6,19`) |
| LEAN-02 | CUMPLE | Cuatro, no dos, en [`formal/lean/Cronologia/Basico.lean`](../formal/lean/Cronologia/Basico.lean): `I1_NadieAntesDeNacer`, `I2_NadieDespuesDeMorir`, `I3_NoEnDosLugares` e `I4_SinAnacronismos`, compuestos en `Coherente` | I3 compara igualdad exacta de momento y no solape de intervalos; la limitación queda declarada en el código y en el README, no omitida |
| LEAN-03 | NO_CUMPLE | `lake build` → `bash: lake: command not found`; tampoco hay `elan`. El proyecto está escrito (`lakefile.toml`, `lean-toolchain`, `Verificar.lean`) pero no compilado, y `.github/workflows/ci.yml` no tiene paso de Lean | Bloqueado por el entorno: no hay toolchain de Lean en la máquina |
| LEAN-04 | NO_CUMPLE | El contrato está definido —`lake exe verificar` sale 0 o 1, y el código de salida es lo que el nodo lee (`formal/lean/Verificar.lean`)— pero nadie lo invoca: `commons/formal/` está vacío y `publication/` también | Especificado y sin implementar |
| LEAN-05 | CUMPLE | `formal/lean/README.md`, apartado «El caso que solo Lean ve»: Gravina muere el 09-03-1806 y el tono del brief empuja el desenlace a 1808. Se razona por qué no lo ven los once validadores deterministas, ni el juez, ni el Autor en el gate | El requisito admite «caso real **o** justificación». Como no hay novela generada, es la justificación, y se dice así |

## TLA — Validador formal del sistema

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| TLA-01 | CUMPLE | [`formal/tla/harness.tla`](../formal/tla/harness.tla): las seis fases, de `Configure` a `PublishVersion`, más `Idle`, `RequestChange`, `Invalidate` y `RegenerateAffected`. Los 24 estados en la definición `Estados` | Escrita en TLA+ directo y no en PlusCal; la desviación está razonada en `formal/tla/README.md` y en el registro de iteraciones |
| TLA-02 | CUMPLE | Reintentos: `Repair` con sus dos aristas de entrada, desde `Validate` y desde `Extract`, compartiendo el contador `intentos`. Reanudación: la acción `Checkpoint`. Regeneración: `RequestChange`, `Invalidate` y `RegenerateAffected`, las tres declaradas en `Aristas` (`formal/tla/harness.tla`) | Los tres elementos que el requisito nombra, cada uno con su acción propia |
| TLA-03 | CUMPLE | Cinco, no tres: `NoPublishUnvalidated`, `ResumeIsExactlyOnce`, `RetriesBounded` y `CorpusSelladoNoSeToca`, más `TypeOK`; los cinco declarados en `formal/tla/harness.cfg` bajo `INVARIANTS` | `PublishVersion` no lleva guarda de validación a propósito, para que `NoPublishUnvalidated` interrogue al grafo y no a sí mismo |
| TLA-04 | CUMPLE | `Termina`, al final de `formal/tla/harness.tla`: toda ejecución alcanza `Idle`, `Fail` o `Branch`. Declarada en `harness.cfg` bajo `PROPERTIES` | Vale bajo la equidad débil que `Spec` declara sobre `AutorAprueba`: si el Autor acaba respondiendo, toda generación termina |
| TLA-05 | CUMPLE | [`formal/tla/harness.cfg`](../formal/tla/harness.cfg) fija el modelo pequeño (`NCapitulos = 5`, `MaxIntentos = 2`, `MaxRechazosJuez = 2`) y **TLC se ha ejecutado sobre él**: `java -cp tla2tools.jar tlc2.TLC -config harness.cfg harness.tla` → `93794 states generated, 59236 distinct states found`. Encontró tres violaciones reales, las tres corregidas | El JDK 21 y `tla2tools.jar` se descargaron al scratchpad y **no están en el repositorio**: reproducirlo exige bajarlos. La reverificación final con equidad fuerte es más cara y quedó corriendo |
| TLA-06 | CUMPLE | [`README.md`](../README.md) mapea las 21 acciones de la especificación a su nodo de LangGraph y a su efecto en SQLite, una fila por acción | Los nodos todavía no existen: la tabla mapea contra el código previsto. La prueba `identidad_nodo_accion` que la comprobará vive en el tramo H3 del plan |
| TLA-07 | CUMPLE | Tres contraejemplos en la tabla de [`formal/tla/README.md`](../formal/tla/README.md), cada uno con su traza y el cambio que provocó: `ResumeIsExactlyOnce` (el rehacer del gate de Writing se trataba como pasada inicial → acción `RehacerWriting`), `Termina` (nada acotaba los rechazos del juez → `rechazosJuez` y arista `Judge → Fail`), y `Termina` otra vez (la equidad débil no bastaba → equidad fuerte) | Ninguno se corrigió debilitando la propiedad: los tres se arreglaron en el modelo o añadiendo el tope que faltaba |

## EVAL — Evaluación del sistema

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| EVAL-01 | CUMPLE | Cinco en [`evals/briefs/`](../evals/briefs/): `01-caso-base`, `02-injection`, `03-incoherencia-temporal`, `04-prohibidas-dificiles` y `05-cobertura-imposible`, cada uno con su bloque `esperado` | Elegidos por incómodos, no por representativos: tres de los cinco esperan fallar |
| EVAL-02 | CUMPLE | [`evals/briefs/02-injection.yaml`](../evals/briefs/02-injection.yaml): cinco cargas en el texto libre —cambio de idioma, anulación de prohibidas, cadena centinela, capítulo extra e instrucción disfrazada de anécdota— con las comprobaciones de que ninguna se ejecuta | La quinta prueba el hallazgo RT-01 del red-team log, que predice que es la que puede sobrevivir |
| EVAL-03 | CUMPLE | [`evals/briefs/03-incoherencia-temporal.yaml`](../evals/briefs/03-incoherencia-temporal.yaml): nacimiento en 1831 contra período 1803-1806, Gravina muerto en 1806 contra un desenlace posterior, y un telégrafo eléctrico en 1805 | Mide **dónde** se detecta, no si se detecta: espera parada en el gate de Intake con cero tokens gastados en investigación |
| EVAL-04 | NO_CUMPLE | `evals/README.md` fija qué se anota por ejecución —validadores, intentos, rúbrica de siete criterios, coste— y `evals/resultados/` no existe: no ha habido ejecución | El arnés no corre de punta a punta todavía. No se rellena con números inventados |
| EVAL-05 | NO_CUMPLE | Sin ejecuciones no hay antes ni después. Los prompts versionados en Langfuse que vincularían el tuning con sus resultados están especificados en `docs/architecture.md:785` y no implementados | Depende de EVAL-04 |

## OBS — Observabilidad (Langfuse)

La dependencia (`backend/pyproject.toml:14`) y las claves de `.env.example` están puestas; `backend/src/storymaker/commons/obs/__init__.py` sigue vacío, así que no hay instrumentación que auditar. H1 no tocó esta familia.

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| OBS-01 | NO_CUMPLE | Especificado en `docs/architecture.md:32` (sesión = novela, span = capítulo/rol/intento). Sin código en `commons/obs/` | — |
| OBS-02 | NO_CUMPLE | Especificado en `docs/architecture.md:32` y `:776` (§14). El dominio de roles existe (`config.py:25`) pero ningún span lo usa | — |
| OBS-03 | NO_CUMPLE | Especificado en `docs/architecture.md:776` (§14) y en `specs/backend/trace-matrix.md`. Sin código | — |
| OBS-04 | NO_CUMPLE | Especificado en `docs/architecture.md:80` («Langfuse: trazas, scores, prompts») y `:215` (el juez solo emite puntuaciones, que se inyectan como scores). Sin validadores que puntúen y sin emisión | — |
| OBS-05 | NO_CUMPLE | Especificado en `docs/architecture.md:785`: los prompts de rol viven en Langfuse como fuente de verdad y el id de versión viaja en el span. Sin código y sin resultados de tuning a los que vincularlos (ver EVAL-05) | — |

## GR — Guardrails

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| GR-01 | NO_CUMPLE | `guardrail_prohibidas` especificado en `docs/architecture.md:617`, post `WriteChapter` y expuesto también como hook. Sin código en `commons/validation/` | — |
| GR-02 | CUMPLE | `commons/db/esquema/canon.sql:83` (`canon_prohibida`, con columna `nivel`) y `:93` (índice sobre `normalizado`). Los tres niveles son `global`, `novela` y `destinatario` | El requisito pide global y por novela; el esquema añade `destinatario`, que es el que no admite fallo |
| GR-03 | NO_CUMPLE | La columna `normalizado` de `docs/architecture.md:352` y «tres niveles, con normalización» en `:617` lo prevén. Sin código ni test | — |
| GR-04 | NO_CUMPLE | Especificado en `docs/architecture.md:197` (parche del editor con límite de reintentos) y `:513` (`Validate --> Fail : reintentos agotados`). El límite existe como constante (`config.py:66`), pero no hay reescritura ni parada que limitar | — |
| GR-05 | NO_CUMPLE | Especificado en `docs/architecture.md:791` (§15) y `:80`. Sin audit log y sin emisión a Langfuse | — |
| GR-06 | NO_CUMPLE | `cd backend && .venv/Scripts/python.exe -m pytest -q` → `22 passed in 0.25s`, pero los 22 son de `test_config.py` (defaults, roles y `Settings`) y `test_agente_falso.py` (el doble de agente). Ninguno cubre niveles de guardrail ni variantes con acento o plural | Hay suite, y verde; no hay estos casos en ella |
| GR-07 | NO_CUMPLE | Especificado en `docs/architecture.md:791` (§15) y `:799` (Core Domain único, sin implementación duplicada). La pureza de ese Core Domain ya tiene guardia estática en `semgrep/core-domain-puro.yaml`, pero el audit log no existe | — |

## DOC — Documentación de proceso (/docs)

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| DOC-01 | CUMPLE | `docs/architecture.md` (1.063 líneas), `specs/backend/spec.md:1` y `specs/backend/plan.md:1` preceden al código: lo único implementado es H0, el primer tramo de `specs/backend/plan.md:28`, y cada módulo cita su origen en la cabecera (`backend/src/storymaker/commons/config.py:1` → `"""spec: §2.2 · arq: §19`) | El orden exigido se cumple, y además queda trazado desde el propio código |
| DOC-02 | CUMPLE | `docs/architecture.md:954` (§17 Trade-offs registrados) y la tabla de decisiones fijadas de `:17-36`, con opción elegida y consecuencia principal en cada fila | — |
| DOC-03 | CUMPLE | Ocho explainers en [`docs/explainers/`](explainers/), uno por concepto del curso aplicado: harness y orquestación, memoria y contexto, validadores, verificación formal, guardrails y policy, observabilidad, evals, y MCP con skills y hooks | Con índice en `docs/explainers/README.md` |
| DOC-04 | CUMPLE | Los cuatro, reunidos en [`docs/diagramas.md`](diagramas.md): arquitectura (`architecture.md:59`), máquina de estados (`architecture.md:488`), tabla de validadores (`architecture.md:612`) y el **esquema SQLite**, que faltaba y se dibuja aquí como diagrama entidad-relación | El de SQLite vivía solo en prosa y DDL suelto |
| DOC-05 | CUMPLE | [`docs/iteraciones.md`](iteraciones.md), con cinco iteraciones en formato causa → qué se hizo → efecto medido → deuda, incluida una que declara que su efecto **no** se midió y por qué | Es distinto del registro de cambios de cada documento, que anota el qué y no el porqué |
| DOC-06 | CUMPLE | [`docs/red-team.md`](red-team.md), con seis ataques (RT-01 a RT-06), su clase de evidencia, veredicto y mitigación aplicada o candidata, más un apartado explícito de lo que esta ronda **no** ha mirado | Los hallazgos son de análisis de la especificación y están marcados como clase `A`, no como ejecutados |
| DOC-07 | NO_CUMPLE | Las menciones a browser MCP son de diseño, no de uso: `docs/architecture.md:624`, `:828` y `:876`. No hay registro de qué se inspeccionó, qué se detectó ni qué se cambió | Sin `.mcp.json` y sin frontend, no ha podido haber uso real |
| DOC-08 | CUMPLE | [`docs/skills.md`](skills.md) inventaría las trece skills agrupadas por la parte del sistema a la que sirven, enlaza la procedencia exacta de `.claude/skills/PROCEDENCIA.md` y declara la skill propia que falta (`continuity-check`, §19) | Documenta además por qué no hay subagentes ni comandos propios, que es lo que pide DOC-09 |
| DOC-09 | CUMPLE | `ls -a .claude/` → solo `skills`; no existen `.claude/agents/` ni `.claude/commands/`. El requisito aplica «si existen», y no existen, luego no hay nada que documentar | Cumplido por ausencia del supuesto |

## CC — Uso de Claude Code

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| CC-01 | PARCIAL | `git ls-files .claude` → 48 ficheros commiteados, todos bajo `.claude/skills/`. No hay memoria ni comandos: `ls -a .claude/` → solo `skills` | La carpeta está commiteada, pero le faltan las dos cosas que el requisito nombra |
| CC-02 | PARCIAL | [`.mcp.json`](../.mcp.json) en la raíz declara el servidor `playwright` con `npx -y @playwright/mcp@latest`. No se ha podido levantar: `npx` no está en el entorno (`command -v npx` → nada) | Configurado, no verificado. Sin Node no hay forma de confirmar que arranca |

## PRE — Presentación

Los ocho son `[M]` en `REQUIREMENTS.md`, y además no existe `presentacion/` (`ls presentacion/` → el directorio no existe), de modo que tampoco hay material que juzgar todavía.

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| PRE-01 | MANUAL | `[M]`; `ls presentacion/` → el directorio no existe | Juicio humano sobre material que aún no existe |
| PRE-02 | MANUAL | `[M]`; no hay deck en el repo | — |
| PRE-03 | MANUAL | `[M]`; no hay deck en el repo | — |
| PRE-04 | MANUAL | `[M]`; sin coste real que citar, porque no hay instrumentación de Langfuse (ver OBS-03) | — |
| PRE-05 | MANUAL | `[M]`; no hay deck en el repo | — |
| PRE-06 | MANUAL | `[M]`; no hay deck en el repo | — |
| PRE-07 | MANUAL | `[M]`; no hay deck en el repo | — |
| PRE-08 | MANUAL | `[M]`; las tres evidencias que pide dependen de EVAL-04, OBS-03 y LEC-08, los tres en `NO_CUMPLE` | — |

## OPT — Opcionales

Ninguno implementado; `REQUIREMENTS.md` permite marcarlos `NO_APLICA` y no bloquean.

| ID | Estado | Evidencia | Notas |
|---|---|---|---|
| OPT-01 | NO_APLICA | No hay servidor MCP en el repo | — |
| OPT-02 | NO_APLICA | No hay tools MCP | — |
| OPT-03 | NO_APLICA | No hay linters de prosa | — |
| OPT-04 | NO_APLICA | El linter de edición manual está previsto en `docs/architecture.md:804` como skill y hook de `.claude/`, pero no implementado | Cuando se implemente, cae bajo HAR-04 |
| OPT-05 | NO_APLICA | No hay proyecto Lean (ver LEAN-01) | — |
| OPT-06 | NO_APLICA | No hay especificación TLA+ (ver TLA-01) | — |
| OPT-07 | NO_APLICA | No hay autenticación | — |
| OPT-08 | NO_APLICA | `ls docs/security-report.md` → no existe | — |

---

## Lectura de conjunto

La segunda pasada de esta auditoría cambió el retrato. La primera describía un proyecto que había construido **el suelo y las barandillas antes que la casa**: documentación densa, dos puertas estáticas reales, y seis fases que eran carpetas vacías. Sigue siendo cierto, pero la casa ha empezado.

Lo que se movió, y por qué importa que se moviera en ese orden:

- **La persistencia entera** (H1), con los triggers de `inmutabilidad.sql` que abortan cualquier `UPDATE` sobre el texto de un capítulo. El cerrojo está puesto **antes** que aquello que encierra, que es el único orden en que un invariante de este tipo llega a existir: puesto después, siempre hay una excepción que ya se coló.
- **Las dos especificaciones formales**, TLA+ y Lean, que llevaban meses descritas en la arquitectura y nunca escritas.
- **Los entregables que no dependían de nadie** —README, brief de ejemplo, `.mcp.json`— y que estaban bloqueando requisitos más caros: sin brief no había novela de muestra que reproducir.

### El patrón que sigue gobernando el resto

Los nueve `PARCIAL` no son medias tintas repartidas al azar. Responden a dos patrones, y conviene distinguirlos porque se cierran de formas distintas:

**«La constante existe y quien la aplica no.»** `HAR-07` tiene `REINTENTOS_POR_CAPITULO` y no el bucle; `HAR-08` tiene `TOKENS_CONCURRENTES_MAXIMOS` y no la guarda que rechaza la llamada; `VAL-04` tiene `RANGO_PALABRAS` y no el validador; `HAR-01` tiene los nueve roles como `StrEnum` y ningún agente detrás; `LEC-10` tiene los triggers de inmutabilidad y ninguna regeneración que produzca una segunda versión. Estos cinco se cierran solos cuando lleguen los tramos H2 a H7 del plan. **No hay que hacer nada con ellos ahora.**

**«Está escrito y el entorno no deja ejecutarlo.»** `TLA-05` necesita una JVM; `LEAN-03` necesita `lake`; `CC-02` necesita Node. Los tres están completos en lo que depende del repositorio y bloqueados en lo que depende de la máquina. **No se cierran trabajando más, se cierran instalando tres herramientas.** Esa distinción es la información más accionable de todo el documento, y es la razón de que ninguno esté marcado `CUMPLE`: una especificación TLA+ que nadie ha pasado por TLC no es una verificación, por muy bien escrita que esté.

### Lo que queda, en tres montones

**1 · Un `lake`, un JDK y un Node.** Cierran `TLA-05`, `LEAN-03` y `CC-02`, y desbloquean `TLA-07` —los contraejemplos de TLC, que hoy no existen porque no ha habido ejecución que los produzca—. Es el trabajo de menor coste y mayor rendimiento que queda en la lista.

**2 · Las fases, H2 a H7.** Arrastran las familias CFG, LEC, MEM parcial, VAL, GR y OBS: unos cincuenta requisitos que se mueven todos juntos porque dependen de lo mismo. Y arrastran también `EVAL-04` y `EVAL-05`, porque los cinco briefs están escritos y **ninguno se ha ejecutado**: hay casos de prueba, no evaluación.

**3 · Los artefactos de entrega.** La presentación (`ENT-03`, `ENT-04`, `ENT-05` y las ocho `PRE-*`), la novela de muestra (`ENT-06`) y el vídeo (`ENT-07`). No dependen del código sino de generar y montar, y son los únicos que ninguna cantidad de ingeniería cierra sola.

### Dos avisos sobre las herramientas del enunciado

`check_requirements.py` vive en la raíz y no en `scripts/`, pese a lo que dice su propio docstring: el comando real es `python check_requirements.py`.

Y en modo `--strict` esta auditoría **falla, y debe fallar**. `--strict` exige que ningún requisito obligatorio esté en `NO_CUMPLE` o `PARCIAL`, lo que equivale a exigir que el proyecto esté terminado. El modo de auditoría, que es el que corresponde a este documento, pide otra cosa: que cada uno de los 106 IDs tenga fila, estado válido y evidencia reproducible. Eso sí se cumple.

### Sobre la honestidad de este documento

Tres requisitos podrían haberse marcado `CUMPLE` con una interpretación generosa, y no se han marcado: `TLA-05` (el modelo está, TLC no ha corrido), `LEAN-03` (el proyecto está, `lake` no existe) y `CC-02` (el MCP está configurado, nunca se ha levantado). Y `TLA-07` se queda vacío en lugar de rellenarse con contraejemplos plausibles.

Se dice explícitamente porque una auditoría cuyo autor tiene un incentivo en que salga verde solo vale si se sabe dónde estuvo la tentación.
