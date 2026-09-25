# GAP-REPORT — storyMaker frente al enunciado

> Auditoría en modo solo lectura. Referencia: `enunciado.md` en la raíz del repositorio (no existe `docs/enunciado.md`). Estado de la auditoría en `docs/.audit-state.json`.
>
> Leyenda: ✅ cumplido con evidencia comprobable · 🟡 parcial, sin evidencia suficiente o solo documentado · ❌ ausente.
>
> Solo aparecen los bloques que siguen abiertos. Los que el Autor ha dado por cerrados (1, 2, 3, 4, 5, 7, 8, 10, 11 y 15) se han retirado de este documento a petición suya, y su registro queda en `docs/.audit-state.json`.

> ⚠️ **Parte de este informe está desfasada (2026-09-25, tras la auditoría).** Después del cierre hubo cambios que afectan a los bloques 9, 12, 13 y 14, y **todavía no se han re-auditado**:
> - Hay ejecuciones de evals en `backend/proyectos/eval-01…06`, con 04 a 06 provisionales, y datos en `presentacion/datos/evals.json`.
> - Hay cinco anexos PDF en `presentacion/`, `presentacion/README.md` y capturas.
> - Hay `CLAUDE.md` propio, `.claude/commands/` (con `tlc`, `lean`, `estado-novelas` y `evaluar`) y `docs/inspeccion-visual.md`.
> - `docs/skills.md`, los explainers, `architecture.md` §16-§17 y `revision-humana.md` están corregidos.
>
> Las cifras de abajo son las de la auditoría, no las de ahora.

## Resumen global

Auditoría cerrada el 2026-09-25, con los 15 bloques recorridos. Estado de los requisitos **obligatorios** de los bloques que siguen abiertos:

| Bloque | ✅ | 🟡 | ❌ |
|---|---|---|---|
| 6 · Validadores semánticos | 2 | 2 | 2 |
| 9 · Evals | 0 | 3 | 2 |
| 12 · Repo y entregables | 3 | 2 | 6 |
| 13 · /docs | 5 | 3 | 1 |
| 14 · Claude Code | 0 | 3 | 2 |
| **Total de los bloques abiertos** | **10** | **13** | **13** |

En los bloques abiertos, **10 de 36 obligatorios cumplidos (28 %)**. Contando también los bloques que el Autor dio por cerrados (1, 2, 3, 4, 5, 7, 8, 10 y 11: 47 ✅, 15 🟡 y 0 ❌), el global es **57 de 98 (58 %)**, con 28 🟡 y 13 ❌. Los opcionales (bloque 15: 0 ✅, 3 🟡 y 5 ❌) no cuentan, y el Autor los dio por cerrados el 2026-09-25: no se implementa ninguno.

**Lectura en una frase:** el arnés está construido y verificado a un nivel poco habitual (TLC y Lean pasan de verdad, más de 1.100 tests, trazabilidad spec↔código), pero **casi nada se ha ejecutado de verdad de principio a fin**. Casi todo lo que falta es evidencia real y entregables, no código.

## Bloqueantes para aprobar

Lo que el enunciado marca como «no aprueba»:

1. **Evals sin resultados medibles** (bloque 9). Hay 7 briefs nuevos en `ejemplos/evals/`, sin versionar, pero **ninguna ejecución, ninguna tabla brief × validador y ningún tuning con antes y después**. Hoy es el suspenso seguro.
2. **Documentación de proceso en /docs** (bloque 13). **No es bloqueante**: `/docs` es extensa y de calidad. Le falta el uso real del browser MCP, y hay que corregir afirmaciones desfasadas.

Evidencias obligatorias de la presentación, **las tres ausentes**:

| Evidencia | Estado | De qué depende |
|---|---|---|
| Tabla de resultados de los evals, con números | ❌ | Ejecutar los 7 briefs y agregar la tabla `score` de cada `eval-*.db` (bloque 9) |
| Coste real por novela sacado de Langfuse, y margen | ❌ | Una novela completa de 10 capítulos trazada en Langfuse. Hoy solo hay una de **2 capítulos**, `prueba-langfuse`, publicada con 263.058 + 190.192 tokens y **1,7172 $**, cifra que coincide con su sesión de Langfuse (`docs/iteraciones.md` It-39) |
| Demo de un cambio del lector propagado a los capítulos afectados | ❌ | Una regeneración real sobre una novela publicada, y además **arreglar el test que falla** `test_el_texto_que_nombra_entra_en_el_alcance_y_se_repara`: hoy renombrar un personaje no regenera ningún capítulo (ver riesgos) |

## Top 10 de pendientes

Ordenados por impacto en la nota frente a esfuerzo. La columna «Depende de» indica el orden obligado.

| # | Pendiente | Impacto | Esfuerzo | Depende de |
|---|---|---|---|---|
| 1 | **Commitear todo lo que está en el working tree**, que es mucho y crítico: `ejemplos/evals/`, `ejemplos/fases/`, `presentacion/`, `.claude/settings.json`, `.claude/skills/inspeccion-visual/`, `cli_policy.py`, `herramientas.py`, `cronologia.py`, `revision_humana.py`, `formal/tla/harness.tla`, `harness_batch.cfg` y sus tests. Solo cuenta el commit final | Crítico | S | — |
| 2 | Arreglar los 8 tests que fallan: el de regeneración por nombre y los 7 de `test_matrices`, que fallan por el `trace-matrix.md` borrado de la raíz. Hay que restaurarlo o retirar la comprobación | Alto | S | — |
| 3 | **Una novela real de 10 capítulos** con el brief del README → `ejemplos/novela-ejemplo.pdf`, traza completa en Langfuse (coste real y captura) y un caso real para la revisión humana | Crítico | M | 1, 2 |
| 4 | **Ejecutar los 7 briefs de eval** y generar la tabla brief × validador (script que lea `score`). Hay que corregir el valor por defecto de `storymaker evaluar` (`evals/briefs` → `ejemplos/evals`) y ejecutar con `lake` en el PATH para que el brief 07 dé el **caso real de Lean** | Crítico | L | 1, 2 |
| 5 | **Iteración de tuning**: sembrar los prompts en Langfuse, cambiar uno (nueva versión), repetir los evals y documentar antes y después en `docs/iteraciones.md` | Alto | M | 4 |
| 6 | **Demo del cambio del lector** sobre la novela del #3: petición → gate → capítulos regenerados → novedades. Grabarla, porque es también el vídeo | Alto | M | 2, 3 |
| 7 | **Revisión humana** de la novela del #3 con `storymaker revision hoja` / `registrar` y comparación con el juez. Antes, corregir `objeto_id=1` en `publication/nodos.py:278` | Alto | M | 3 |
| 8 | **Presentación**: deck PDF y editable con identidad corporativa, anexos (`anexo-evals-tabla.pdf`, `anexo-tla-spec.pdf`, esquema SQLite, red-team y capturas de Langfuse), `presentacion/README.md` y slide de presupuesto con el coste real | Alto | L | 3, 4, 5 |
| 9 | **Instalar Node** y hacer una sesión real con el Playwright MCP (skill `inspeccion-visual`), documentada en `docs/`: qué inspeccionó, qué detectó y qué cambió | Medio | M | 3 |
| 10 | Cierre documental y de Claude Code: `.claude/commands/` y memoria versionada, score de `schema_guard`, fila de trade-off de la validación visual, y corregir los desfasados («`continuity-check` no existe», «trece skills», «Playwright MCP» en `architecture.md:996`, TLC «corriendo», `docs/revision-humana.md` con siete criterios) | Medio | S | — |

## Tareas que requieren intervención humana

- **Autorizar y lanzar las ejecuciones reales** (#3, #4, #5 y #6): cuestan dinero y tiempo, y esta auditoría no las lanza.
- **Revisión humana** de una novela completa con la rúbrica de 8 criterios (#7).
- **Deck con identidad corporativa**: nombre de empresa (el guion propone «Novela Relicario»), logotipo, paleta y tipografía coherentes. Validarlo visualmente y ensayar los 10 minutos.
- **Grabar el vídeo de demo** y subirlo a `/presentacion/` o enlazarlo desde su README.
- **Instalar Node** en la máquina para el browser MCP (#9) y para correr los tests de frontend, que esta auditoría no pudo ejecutar.
- **Cifras de negocio** de la slide de presupuesto: precio de venta, tarifa por hora, horas por fase, escenarios de volumen y sensibilidad. Se razonan, pero las decide el Autor.
- **Repositorio MyFactory**: enlazarlo desde el README y dejar su commit final.
- **Email de entrega** con los dos enlaces a commits y la frase de diseño de no más de tres líneas.

## Riesgos detectados

- **Tests que fallan hoy** (suite de backend completa: 1.100 pasan, 8 fallan y 3 se saltan):
  - `tests/integracion/test_regeneracion.py::TestElNombreLlegaAlTexto::test_el_texto_que_nombra_entra_en_el_alcance_y_se_repara`: al cambiar el nombre de un personaje, el sistema responde «Ningun capitulo lo usa: no hay version nueva». **Es exactamente la demo obligatoria**, y el test está sin versionar, así que probablemente es trabajo en curso.
  - 7 de `tests/correspondencia/test_matrices.py`: `FileNotFoundError` sobre `trace-matrix.md` de la raíz, borrado en el working tree, aunque `AGENTS.md` lo declara documento del proyecto.
- **Tests de frontend sin verificar**: no hay `node` en esta máquina.
- **Inestabilidad durante la auditoría**: 8 fallos transitorios en `test_extremo_a_extremo.py` y 4 en `test_publicacion.py` desaparecieron al repetirse. Otra sesión editaba el código a la vez, y conviene una pasada completa en limpio antes del commit final.
- **Volumen enorme sin commitear**: más de 60 ficheros modificados y decenas sin versionar, incluidos entregables y el hook de policy. Si el commit final no los recoge, el corrector evalúa otra cosa.
- **Secretos**: ninguna clave en el historial (barrido completo con patrones de Langfuse, Anthropic, Telegram, GitHub y AWS). `backend/.env` está ignorado. Pero **los workflows de CI se retiraron** (commit `74acbcb`), así que `gitleaks` y `pip-audit` ya no corren solos: hay que pasarlos a mano antes de entregar.
- **Lean que no es Lean**: si `lake` no está en el PATH, el arnés cae en silencio a la evaluación en Python (`commons/formal/cronologia.py`). En esta máquina `lake` solo está en `~/.elan/bin`. Un «caso real de Lean» generado así no sería de Lean.
- **Código frágil**:
  - `objeto_id=1` fijo en la score del juez (`publication/nodos.py:278`).
  - En batch se publica aunque el juez suspenda (`publication/nodos.py:283-286`).
  - `storymaker evaluar` apunta a un directorio borrado.
  - `Branch`: el nodo existe (`commons/graph/branch.py:27`, `fork`) y la arista `Idle → Branch` está declarada en `commons/graph/aristas.py:70`, pero `commons/graph/construccion.py` **no añade el nodo al grafo compilado**. Ramificar solo funciona por `ramificar()` desde la CLI, no como transición del grafo. *(Corregido el 2026-09-25: una versión anterior de este informe decía que el módulo no existía.)*
  - La tabla spec↔código del README está desfasada respecto a `harness.tla`.

## Bloque 6 · Validadores semánticos

Auditado el 2026-09-25. Tests del juez en `tests/unit/test_publicacion.py`: **4 pasan y 1 falla**. Falla `TestJuez::test_la_rubrica_son_siete_criterios`, porque la rúbrica pasó a 8 criterios con `tono` en el working tree. Todo `backend/src/storymaker/publication/` está modificado sin commitear, y `revision_humana.py` está sin versionar. Otra sesión está trabajando en ello.

| Requisito | Estado | Evidencia o motivo | Qué falta exactamente | Esfuerzo | Riesgo de romper algo al implementarlo |
|---|---|---|---|---|---|
| Mínimo dos validadores semánticos | 🟡 | El primero (el juez) existe. El segundo (la revisión humana) tiene herramienta pero no se ha ejercido nunca (ver las filas siguientes). | Una revisión humana registrada. | — | — |
| LLM-as-judge con rúbrica: continuidad, tono, calidad narrativa (arco, coherencia de personajes, ritmo) y personalización natural | ✅ | `backend/src/storymaker/publication/rubrica.yaml` define 8 criterios: `continuidad`, `arco`, `coherencia_de_personajes`, `ritmo`, `tono`, `prosa`, `naturalidad_de_la_personalizacion` y `autenticidad_de_epoca`. Cubren todo lo que pide el enunciado. `Perfil.JUEZ` se invoca en `publication/nodos.py:75-103`. El juez no puede editar: su esquema no tiene ningún campo de texto (`publication/esquemas.py`). | Commitear `rubrica.yaml` y `esquemas.py`, que tienen `tono` solo en el working tree, y actualizar `test_la_rubrica_son_siete_criterios` a 8. | S | Bajo: el test ya describe el cambio. |
| Puntuación por criterio y justificación | ✅ | `Puntuacion` (`criterio`, `valor` de 1 a 10, `justificacion` de 10 a 600 caracteres) y `SalidaJuez.completa`, que exige los 8 criterios (`publication/esquemas.py`). El umbral de 6.0 se calcula en Python (`nodos.py:354`, `rubrica.yaml`). | — | — | — |
| El juez envía su resultado a Langfuse como score | 🟡 | Score `juez_rubrica` con la media y el detalle por criterio (`publication/nodos.py:273-281`). | `objeto_id=1` está **fijo en el código** (`nodos.py:278`): todas las versiones puntúan sobre el mismo objeto, mientras que `revision_humana` usa el número de versión. Así, al comparar la v2 con su revisión humana se leería la nota de la v1 o se mezclarían. Hay que usar el número de la versión candidata. Además, en modo batch la novela se publica aunque no supere el umbral (`nodos.py:283-286`). Es una decisión de producto defendible, pero hay que declararla en la arquitectura, porque el enunciado presenta el juez como gate. | S | Medio: `notas_del_juez` de `revision_humana.py` lee esas scores y habría que alinear las dos consultas. |
| Revisión humana de al menos una novela completa con la misma rúbrica | ❌ | Protocolo en `docs/revision-humana.md` y herramienta en la CLI `storymaker revision hoja` / `revision registrar` (`cli/comandos.py:273-330`, `publication/revision_humana.py`), que lee el mismo `rubrica.yaml`. Pero `docs/revision-humana.md` §5 dice «**Actas registradas: ninguna todavía**». | Leer una novela publicada completa, puntuar los 8 criterios con justificación y registrarla. Esto exige **intervención humana** y, antes, una novela real publicada (bloque 12). Además: `revision_humana.py` no tiene tests y está sin versionar. `docs/revision-humana.md` sigue hablando de «siete criterios», su plantilla no incluye `tono` y enlaza `evals/varianza_juez.py`, que está borrado. | M (humano) + S (documento) | Bajo: es ejecución y documentación. |
| Comparación del juicio humano con el del LLM | ❌ | `Acta` compara persona y juez por criterio (`revision_humana.py:180-230`), y el protocolo define qué hacer con las divergencias (`docs/revision-humana.md` §4). | No existe ninguna comparación hecha. Depende de la fila anterior. Cuando exista, conviene llevar la tabla persona↔juez también a `docs/iteraciones.md` y a un anexo de la presentación. | S (tras la revisión) | Bajo. |

**Resumen del bloque:** 2 ✅ / 2 🟡 / 2 ❌. El juez está bien diseñado. **La revisión humana y la comparación no existen**, y dependen de tener una novela real publicada y de que una persona la lea: es trabajo humano bloqueante.

**Actualización (2026-09-25, suite completa al cierre de la auditoría):** `test_la_rubrica_son_siete_criterios` ya no falla. La revisión humana sigue sin hacerse y `objeto_id=1` sigue fijo.

## Bloque 9 · Evals

Auditado el 2026-09-25 y **revisado el mismo día**, al aparecer briefs nuevos. El `evals/` antiguo sigue borrado en el working tree (`D evals/README.md`, `D evals/briefs/01…05`, `D evals/correr.py` y `D evals/varianza_juez.py`). En su lugar hay **7 briefs nuevos en `ejemplos/evals/`**, creados a las 01:22-01:23, junto con `ejemplos/README.md` y `ejemplos/fases/`. **Los tres están sin versionar** (`??`).

Como referencia, se consultaron **en solo lectura** las novelas locales de `backend/proyectos/`, que están en `.gitignore` y no se entregan. `lozoya`, `metro` y `pepa` tienen una versión publicada cada una, con **5 capítulos** y nota del juez de 7,71, 7,14 y 6,29. Ninguna es una ejecución de los briefs de eval.

| Requisito | Estado | Evidencia o motivo | Qué falta exactamente | Esfuerzo | Riesgo de romper algo al implementarlo |
|---|---|---|---|---|---|
| Cinco briefs de prueba | 🟡 | `ejemplos/evals/01-jubilacion.yaml` … `05-aniversario.yaml`, uno por cada ocasión del enunciado. Cada uno declara `espera:` con `validadores_que_deben_pasar` y se documenta en la tabla de `ejemplos/README.md`. | **Commitearlos**. Además, `storymaker evaluar` busca por defecto en `evals/briefs` (`backend/src/storymaker/cli/comandos.py:341`), que ya no existe: hay que cambiar el valor por defecto a `ejemplos/evals` o documentar el `--briefs`. `intake/encargo.py:22-24` y la cabecera de `formal/lean/Cronologia/Generado.lean` siguen citando `evals/briefs/`. | S | Bajo. |
| Al menos uno adversarial (injection en el texto libre) | 🟡 | `ejemplos/evals/06-adversarial-injection.yaml` mete cinco órdenes en una carta (testigo, idioma, personaje, palabra prohibida y revelar el prompt) y declara cómo se comprueba cada una sobre la base de la novela. La defensa tiene test unitario (`tests/adversarias/test_adversario.py:44-70`). | Ejecutarlo de verdad y anotar el resultado en `docs/red-team.md`. RT-01 sigue «pendiente» en `docs/red-team.md:29`. | S (tras ejecutar) | Bajo. |
| Al menos uno diseñado para provocar una incoherencia temporal | 🟡 | `ejemplos/evals/07-adversarial-temporal.yaml`: Gravina de padrino en 1808, dos años después de morir. Declara `validador_que_debe_saltar: lean_cronologia (I2, NadieDespuesDeMorir)` y `validadores_que_no_lo_ven`. | Ejecutarlo. Su resultado es a la vez **el caso real de Lean** que pide la presentación, y conviene ejecutarlo con `lake` en el PATH para que juzgue Lean y no el respaldo en Python. | S (tras ejecutar) | Bajo. |
| Tabla por brief de qué validadores pasaron y cuáles fallaron | ❌ | No hay ninguna ejecución de los briefs nuevos ni tabla con números. `storymaker evaluar` (`cli/comandos.py:340-375`) solo imprime el resultado de cada invocación y no agrega nada. | Ejecutar los 7 briefs (los básicos a 10 capítulos, los adversariales a 5) y generar la tabla brief × validador a partir de la tabla `score` de cada `eval-*.db`, con 1/0 por validador y la nota del juez. Publicarla en `docs/` y como anexo `anexo-evals-tabla.pdf`. **El enunciado dice que sin evals con resultados medibles no se aprueba**, y la tabla es una evidencia obligatoria de la presentación. | L (7 generaciones reales, cuestan dinero y tiempo) | Medio: 7 novelas completas pueden destapar fallos del pipeline, y conviene lanzarlas con la suite en verde. |
| Una iteración de tuning documentada, con resultados antes y después | ❌ | Ninguna de las 37 iteraciones de `docs/iteraciones.md` es un tuning sobre los evals con números antes y después (`requirements-audit.md:111`, `NO_CUMPLE`). | Cambiar un prompt en Langfuse (nueva versión), repetir los evals y documentar los números antes y después, indicando qué versión de prompt produjo cada resultado. | M (depende de la fila anterior) | Bajo en código. Coste de ejecución real. |

**Resumen del bloque:** 0 ✅ / 3 🟡 / 2 ❌. Ya hay material de partida, y es bueno: los briefs declaran qué debe pasar. Pero **sigue siendo el bloqueante número uno**, porque no hay ni una ejecución ni una tabla. Dependencias: arreglar los tests rotos de `publication/` → commitear `ejemplos/evals/` → ejecutarlos → tabla → tuning → ejecutarlos otra vez.

## Bloque 12 · Repo y entregables

Auditado el 2026-09-25. Barrido de secretos en **todo el historial** (`git log --all -p -G`) con patrones de claves de Langfuse (`sk-lf-`, `pk-lf-`), Anthropic (`sk-ant-`), token de bot de Telegram, GitHub (`ghp_`) y AWS (`AKIA`): **ninguna coincidencia**. `backend/.env` está en `.gitignore` (`.gitignore:3`) y no aparece en ningún commit.

| Requisito | Estado | Evidencia o motivo | Qué falta exactamente | Esfuerzo | Riesgo de romper algo al implementarlo |
|---|---|---|---|---|---|
| README con brief de ejemplo reproducible | ✅ | `README.md:54-116`: «El brief de ejemplo» con `uv run storymaker nueva ../ejemplos/brief-ejemplo.yaml --nombre ejemplo`, decisiones de gate y reanudación. Puesta en marcha en `README.md:23-52`. | Hay una incoherencia: el README usa `ejemplos/brief-ejemplo.yaml`, pero `ejemplos/README.md` dice que el brief del README y de `novela-ejemplo.pdf` es `evals/01-jubilacion.yaml`. Hay que decidir cuál es y usar el mismo en los dos sitios. | S | Bajo. |
| `.env.example` | ✅ | `.env.example` en la raíz y `frontend/.env.example`. Las variables secretas (`STORYMAKER_TELEGRAM_BOT_TOKEN`, `STORYMAKER_TELEGRAM_CHAT_ID`, `STORYMAKER_LANGFUSE_PUBLIC_KEY` y `STORYMAKER_LANGFUSE_SECRET_KEY`) están **vacías**. | — | — | — |
| Sin API keys en ningún repo ni en el historial | ✅ | Barrido de la cabecera: sin coincidencias en ningún commit. `backend/.env`, con las claves reales, está ignorado. | Solo se ha auditado storyMaker; MyFactory queda fuera de alcance. Recomendable pasar `gitleaks detect` antes del commit final, como declara `.env.example`. | S | Bajo. |
| `/ejemplos/novela-ejemplo.pdf` con una novela completa de 10 capítulos generada con el brief del README | ❌ | No existe. Las novelas reales locales (`backend/proyectos/{lozoya,metro,pepa}/*.v1.pdf`) tienen 5 capítulos y no están versionadas. | Generar la novela del brief del README a **10 capítulos**, exportar el PDF de la v1 y commitearlo en `ejemplos/novela-ejemplo.pdf`. El enunciado lo llama «la evidencia de que el sistema funciona de principio a fin». Esa misma ejecución da el coste real de una novela completa en Langfuse y la novela para la revisión humana (bloque 6). | M (una generación real) | Medio: la primera novela de 10 capítulos puede destapar fallos del pipeline, ya que las reales conocidas son de 5. |
| `/presentacion/`: deck en PDF y en formato editable | ❌ | `presentacion/` existe **sin versionar** y solo contiene `guion.md` (el guion por slides, «Novela Relicario») y `prompts-claude-design.md` (prompts para generar el deck). No hay deck. | Producir el deck con identidad corporativa (nombre, logotipo, paleta y tipografía consistentes; no una plantilla genérica), exportarlo a PDF y commitear también el editable (`.pptx` o similar). Requiere **intervención humana** para validar la identidad visual y ensayar. | L | Bajo en el repo. |
| `/presentacion/`: anexos como ficheros individuales con nombre descriptivo | ❌ | No hay ningún anexo. | Al menos: `anexo-evals-tabla.pdf` (depende del bloque 9), `anexo-tla-spec.pdf`, el esquema SQLite, el red-team log y capturas de Langfuse (sesión de la novela, traza y scores). | M | Bajo. |
| `/presentacion/README.md` con el contenido y el idioma | ❌ | No existe. | Un README que liste cada fichero y declare el idioma (castellano, con términos técnicos en inglés). | S | Bajo. |
| Vídeo de demo en `/presentacion/` o enlazado desde su README | ❌ | No hay vídeo ni enlace. | Grabar la demo, que debe incluir el cambio del lector propagado a los capítulos afectados (evidencia obligatoria), y subirla o enlazarla. **Intervención humana.** | M | Bajo. |
| Slides obligatorias de la presentación (portada con empresa, cliente, fecha y estudiante; presupuesto y coste; contraportada) | 🟡 | `presentacion/guion.md` recorre los 8 bloques de tiempo del enunciado (portada 0:30 … demo 1:00, 22 slides) y reserva las slides 18-19 para presupuesto y coste. | El guion existe, pero las cifras del presupuesto (coste real por novela de Langfuse, margen, escenarios de volumen y sensibilidad) dependen de ejecuciones reales que no existen (bloques 9 y 10). | M | Bajo. |
| Evidencias obligatorias: tabla de evals, coste real de Langfuse y margen, demo del cambio del lector | ❌ | Ninguna existe todavía: no hay ejecuciones de evals, ni coste de novela completa, ni una regeneración real grabada. | Todas dependen de ejecuciones reales: la tabla del bloque 9, el coste de una novela completa en Langfuse y la demo, que es una regeneración real sobre la novela de ejemplo. | L | Medio (ver las filas anteriores). |
| Repositorio MyFactory y email de entrega | 🟡 | Fuera de este repositorio. No hay enlace a MyFactory en el README (`docs/requirements-audit.md:46`). | Enlazar MyFactory desde el README y enviar el email con los dos enlaces a commits y la frase de diseño. **Intervención humana.** | S | Bajo. |

**Resumen del bloque:** 3 ✅ / 2 🟡 / 6 ❌. El repositorio está limpio de secretos y bien documentado para arrancar, pero **casi todos los entregables finales están por hacer**, y casi todos dependen de una o más ejecuciones reales.

## Bloque 13 · /docs

Auditado el 2026-09-25. En `docs/` hay 11 documentos y 8 explainers, unas 3.900 líneas. `architecture.md`, `iteraciones.md`, `red-team.md`, `verification.md` y `explainers/mcp-y-claude-code.md` están modificados sin commitear. El enunciado dice que **sin documentación de proceso en /docs no se aprueba**. Existe y es extensa. Lo que falta es concreto: el uso real del browser MCP y varias afirmaciones desfasadas.

| Requisito | Estado | Evidencia o motivo | Qué falta exactamente | Esfuerzo | Riesgo de romper algo al implementarlo |
|---|---|---|---|---|---|
| Spec inicial: qué se decidió construir y por qué, antes de escribir código | ✅ | `docs/architecture.md` §0-§1 («El producto en una frase» y «Decisiones fijadas») y `specs/*/spec.md`. El historial lo confirma: `architecture.md` nace en `e14b6a9` (21-09) y `specs/backend/spec.md` en `89cf09a` (23-09, 14:59), **antes** del primer código de `backend/src` en `6928e7c` (23-09, 18:07). | Ningún documento se llama «spec inicial». Conviene una línea en `docs/` o en el README que diga cuál es y en qué commit quedó fijada, para que el corrector la encuentre. | S | Bajo. |
| Trade-offs: cada decisión relevante con opciones, criterios y elección | ✅ | `architecture.md` §17, tabla «Decisión · Opciones consideradas · Criterio · Elección» con unas 70 filas. Incluye los ejemplos del enunciado: «Invocación de agentes» y «Editor y juez» (single frente a multi-agent), «Base de datos» (formato de la story bible), «Frontend» (modelo de lectura), «Alcance de TLA+» y «Alcance de Lean». | Añadir la fila de la validación visual (`render_visual` usa Playwright desde Python dentro del arnés, no un agente con browser MCP). | S | Bajo. |
| Explainers: uno por concepto del curso aplicado, breves | ✅ | 8 en `docs/explainers/` (harness y orquestación, memoria y contexto, validadores, verificación formal, evals, observabilidad, guardrails y policy, MCP y Claude Code), de 44 a 60 líneas cada uno, con índice en `explainers/README.md`. | `explainers/mcp-y-claude-code.md` §Skills está desfasado: dice «Trece instaladas» (`docs/skills.md` dice quince) y que `continuity-check` «todavía no existe» (sí existe). | S | Bajo. |
| Diagramas: arquitectura del harness, máquina de estados TLA+, esquema SQLite y tabla de validadores con su punto de ejecución | ✅ | `docs/diagramas.md` los reúne: arquitectura en `architecture.md` §3 (mermaid), máquina de estados en §9 (mermaid), esquema SQLite en el propio `diagramas.md` (mermaid) y tabla de validadores en §11a («Nombre · Comprueba · Punto de ejecución»). | Comprobar que el diagrama de §9 sigue coincidiendo con `harness.tla`, que acaba de cambiar (ver la tabla desfasada del README). | S | Bajo. |
| Registro de iteraciones: qué cambió tras cada eval o contraejemplo de TLC o Lean, y por qué | 🟡 | `docs/iteraciones.md`, 37 entradas con causa, qué se hizo, efecto medido y deuda. Las de TLC (It-09 a It-11) están muy bien. | No hay entradas **tras un eval**, porque no se ha ejecutado ninguno (bloque 9), ni tras un contraejemplo **real** de Lean. Llegarán con el tuning. Además, It-11 dice que la reverificación con equidad fuerte «quedó corriendo»: falta la entrada con el resultado (TLC pasa hoy, 12.650 estados). | S (redactar) tras M (ejecutar) | Bajo. |
| Red-team log: casos adversariales probados, qué validador los detectó (o no) y cómo se resolvió | 🟡 | `docs/red-team.md`: RT-01 a RT-06, con clase, estado y severidad. Lo que no cubre está declarado (§«Lo que esta ronda no ha mirado»). | Los casos son **análisis de diseño, no pruebas ejecutadas**. RT-01 (injection) está «abierto» con tres mitigaciones «ninguna aplicada todavía» y la decisión pendiente. RT-02 y RT-03 siguen abiertos. Falta ejecutar `ejemplos/evals/06-adversarial-injection.yaml` y anotar qué validador lo detectó y cómo se resolvió, y cerrar o aceptar como `U` en `verification.md` §5 los abiertos. | M | Medio: aplicar la mitigación de RT-01 (por ejemplo, un techo de longitud en `anécdota`) cambia el `Brief` y el Intake. |
| Uso real del browser MCP documentado: qué inspeccionó el agente, qué detectó y qué cambio provocó | ❌ | `docs/requirements-audit.md:130` (DOC-07) ya lo marcaba `NO_CUMPLE` y sigue igual: no hay ninguna sesión registrada. `explainers/mcp-y-claude-code.md` §«Playwright MCP» describe `render_visual`, que **no usa el MCP**. Además, `architecture.md:996` dice «Validación visual: Playwright MCP desde Claude Code», que contradice la implementación (Playwright en Python dentro del arnés, `publication/render.py`). El MCP ni siquiera conectó en esta sesión (`CONNECTION_CLOSED`). | Hacer una sesión real de Claude Code con el Playwright MCP sobre la lectura web de una novela (índice, fichas y portada) y documentarla en `docs/`: qué inspeccionó, qué detectó y qué cambio provocó en el código o en los prompts, con capturas. Corregir `architecture.md:996`. Necesita `node`/`npx` en la máquina, porque `.mcp.json` lanza `npx @playwright/mcp`, y **aquí no hay node** (ver el bloque 14). | M | Bajo en código. Requiere instalar Node, que queda fuera de esta auditoría. |
| Skills usados o creados en el repo y referenciados desde /docs | 🟡 | `docs/skills.md` inventaría las instaladas con su procedencia (`.claude/skills/PROCEDENCIA.md`), y las 16 carpetas de `.claude/skills/` están versionadas. | `docs/skills.md:60-66` §«La skill propia que falta» dice que `continuity-check` «hoy no existe». **Sí existe** (`.claude/skills/continuity-check/SKILL.md`). Hay que reescribir esa sección con su propósito, su uso y su resultado. | S | Bajo. |
| Subagentes y comandos propios documentados con propósito y resultado | ✅ | `docs/skills.md:68-74` declara que **no hay** `.claude/agents/` ni `.claude/commands/` y justifica por qué: los roles son invocaciones del SDK, no subagentes. El enunciado dice «si se han usado». | Si en el desarrollo se usaron subagentes de Claude Code (por ejemplo, Explore) o comandos como `/grill-me`, conviene decirlo, porque `AGENTS.md` exige la skill `grilling` en cada paso. | S | Bajo. |

**Resumen del bloque:** 5 ✅ / 3 🟡 / 1 ❌. `/docs` es abundante y de calidad, así que no es bloqueante por ausencia. Lo que falta es el **uso real del browser MCP**, cerrar el red-team con ejecuciones y corregir varias afirmaciones desfasadas: `continuity-check` «no existe», «trece skills», «Playwright MCP» en el arnés y TLC «corriendo».

## Bloque 14 · Claude Code

Auditado el 2026-09-25. `.claude/` contiene `settings.json` (hooks) y `skills/` (17 carpetas más `PROCEDENCIA.md`). En el working tree, `settings.json` y `skills/continuity-check/SKILL.md` están modificados, y hay una skill nueva, `skills/inspeccion-visual/`, **sin versionar**, que otra sesión está creando. `.claude/scheduled_tasks.lock` queda fuera de git por `.git/info/exclude`.

| Requisito | Estado | Evidencia o motivo | Qué falta exactamente | Esfuerzo | Riesgo de romper algo al implementarlo |
|---|---|---|---|---|---|
| La carpeta `.claude/` está commiteada | 🟡 | `git ls-files .claude` lista `settings.json` y todas las skills instaladas, más `continuity-check`. | En el working tree quedan sin commitear los hooks de `settings.json`, el cambio de `continuity-check` y la skill nueva `inspeccion-visual`. Sin ese commit, lo que el corrector ve en `.claude/` es la versión anterior, sin hook de policy. | S (commit) | Bajo. |
| Ficheros de memoria en `.claude/` | ❌ | No hay ficheros de memoria en `.claude/`. La memoria automática de Claude Code de este proyecto (`~/.claude/projects/…/memory/`) está vacía y además vive fuera del repositorio. La única «memoria» versionada es `CLAUDE.md` → `AGENTS.md`. | Decidir qué se entiende por memoria y dejarlo en el repositorio. Opción barata: un `.claude/memory/` (o una sección de `AGENTS.md`) con las lecciones que el Autor ha ido corrigiendo, por ejemplo «no se reinicia el servidor con ejecuciones vivas» y «lo borrado no se rescata», y mencionarlo en `docs/skills.md`. Conviene confirmar con el enunciado o con el profesor si `CLAUDE.md` basta. | S | Bajo. |
| Comandos personalizados en `.claude/` | ❌ | No existe `.claude/commands/`. `docs/skills.md:68-74` lo declara y lo justifica: los roles no son subagentes. | El enunciado pide «la carpeta `.claude/` con los ficheros de memoria y comandos personalizados». Hay que añadir al menos un comando útil y real, por ejemplo `/evaluar` (lanza `storymaker evaluar --briefs ../ejemplos/evals`), `/tlc` (corre TLC sobre `formal/tla`) o `/lean` (`lake build` más `verificar`), y documentarlo en `docs/skills.md` con su propósito y resultado. Las skills `continuity-check` e `inspeccion-visual` se invocan como `/…`, pero son skills, no comandos. | S | Bajo: son ficheros Markdown en `.claude/commands/`. |
| Configuración MCP (`.claude/mcp.json` o equivalente) con un servidor de inspección de browser | 🟡 | `.mcp.json` en la raíz declara `playwright` → `npx -y @playwright/mcp@latest --browser chromium`, commiteado en `6928e7c`. `architecture.md:1358` justifica la raíz: es el único sitio del que Claude Code lee los servidores de un proyecto. | Cumple la letra («o equivalente»). **No funciona en esta máquina**: no hay `node`/`npx`, y el servidor falla con `CONNECTION_CLOSED` (también en `docs/requirements-audit.md:31`). Sin Node no se puede hacer la sesión real que exige el bloque 13, ni usar la skill `inspeccion-visual`. | S (instalar Node, humano) | Bajo. |
| Claude Code puede abrir la lectura web y verificarla visualmente | 🟡 | Hay una skill nueva `inspeccion-visual` (`.claude/skills/inspeccion-visual/SKILL.md`, sin versionar), pensada justo para esto: recorrer índice, capítulos, portada y fichas con el MCP de Playwright y anotar lo que encuentre. | Commitearla, instalar Node, ejecutarla contra una novela publicada y documentar el resultado en `docs/`. Eso cierra también el ❌ del bloque 13. | M | Bajo. |

**Resumen del bloque:** 0 ✅ / 3 🟡 / 2 ❌. Las piezas están configuradas, pero **a medias en git y sin poder usarse aquí**. Falta: commitear `.claude/`, añadir comandos personalizados y memoria versionada, e instalar Node para que el browser MCP arranque.
