# Checklist de requisitos — storyMaker / MyFactory

Cada requisito tiene un ID. La auditoría (`docs/requirements-audit.md`) debe tener una fila por ID con:
`| ID | Estado | Evidencia | Notas |`

- **Estado**: `CUMPLE`, `PARCIAL`, `NO_CUMPLE` o `MANUAL` (no verificable por un agente; requiere revisión humana).
- **Evidencia**: ruta de archivo + línea/función, y cuando aplique el comando ejecutado y su resultado. "Parece que sí" no es evidencia.
- Tipo de verificación: **[E]** existencia de archivo · **[C]** lectura de código · **[X]** ejecutar comando/test · **[M]** manual.

---

## ENT — Entregables y estructura de repos

| ID | Requisito | Verif. |
|---|---|---|
| ENT-01 | Repo storyMaker con código, README, brief de ejemplo reproducible, `.env.example` y `/docs` | [E] |
| ENT-02 | Repo MyFactory existe y contiene las herramientas del curso | [E] |
| ENT-03 | `/presentacion/` con deck en PDF **y** en formato editable | [E] |
| ENT-04 | Anexos como ficheros individuales con nombres descriptivos | [E] |
| ENT-05 | `/presentacion/README.md` lista contenido e idioma elegido | [E] |
| ENT-06 | `/ejemplos/novela-ejemplo.pdf` con 10 capítulos, generada con el brief del README | [E][X] |
| ENT-07 | Vídeo de demo en `/presentacion/` o enlazado desde README | [E] |
| ENT-08 | Ninguna API key ni secreto en el repo ni en el historial de git | [X] `git log -p \| grep -iE "sk-\|api_key\|secret"` o gitleaks |
| ENT-09 | Email de entrega (asunto, links a commits, frase ≤3 líneas) | [M] |

## CFG — Configuración (agente entrevistador)

| ID | Requisito | Verif. |
|---|---|---|
| CFG-01 | Entrevistador recoge nombre, edad, rasgos, recuerdos, género, tono y extensión | [C] |
| CFG-02 | Recoge palabras/temas prohibidos por el cliente | [C] |
| CFG-03 | Detecta datos que faltan | [C][X] |
| CFG-04 | Detecta al menos un tipo de contradicción (p. ej. edad vs género/tono) | [C][X] test |
| CFG-05 | Acepta texto libre (anécdota, carta) y extrae hechos | [C] |
| CFG-06 | El texto libre se trata como no confiable (delimitado, no ejecuta instrucciones) | [C][X] test injection |
| CFG-07 | Salida = brief estructurado validado con schema | [C][X] |

## LEC — Lectura interactiva (web o PDF)

| ID | Requisito | Verif. |
|---|---|---|
| LEC-01 | Formato elegido (web o PDF) documentado | [E] |
| LEC-02 | Índice de capítulos navegable | [X] browser MCP / PDF links |
| LEC-03 | Ficha de personajes y lugares generada desde la story bible | [C] |
| LEC-04 | Cada entrada de la ficha enlaza al capítulo donde aparece | [X] |
| LEC-05 | Portada con dedicatoria personalizada | [X] |
| LEC-06 | Cambio del lector (web: selección en página / PDF: formulario o CLI) | [C][X] |
| LEC-07 | Se identifican los capítulos que usan el hecho (vía tabla de hechos) | [C][X] |
| LEC-08 | Solo se regeneran esos capítulos, manteniendo continuidad | [C][X] |
| LEC-09 | Web: se marcan capítulos cambiados / PDF: página de "novedades" con enlaces internos | [X] |
| LEC-10 | Se conserva la versión anterior de la novela | [C][X] |

## HAR — Harness

| ID | Requisito | Verif. |
|---|---|---|
| HAR-01 | Roles planner, writer y editor/critic (≥3) | [C] |
| HAR-02 | `CLAUDE.md` en raíz, cuidado y legible | [E][M] |
| HAR-03 | Al menos una skill reutilizable | [E] |
| HAR-04 | Hook de validación de capítulo | [E][C] |
| HAR-05 | Hook de policy | [E][C] |
| HAR-06 | Tools con schema validado | [C] |
| HAR-07 | Retries con límite (constante configurable) | [C][X] test |
| HAR-08 | Límite de 100.000 tokens concurrentes aplicado en código | [C] |

## MEM — Memoria

| ID | Requisito | Verif. |
|---|---|---|
| MEM-01 | Story bible en SQLite | [C] |
| MEM-02 | Cada hecho registra en qué capítulos se usa | [C] esquema |
| MEM-03 | Tabla de cronología (evento, momento, personajes, lugar) | [C] esquema |
| MEM-04 | La cronología alimenta el validador Lean | [C] |
| MEM-05 | Resúmenes por capítulo usados como contexto de los siguientes | [C] |
| MEM-06 | Checkpoint por capítulo; reanuda desde el último completado | [C][X] test de fallo simulado |

## VAL — Validadores (cada uno: nombre, punto de ejecución, score en Langfuse)

| ID | Requisito | Verif. |
|---|---|---|
| VAL-01 | ≥3 validadores programáticos deterministas | [C] |
| VAL-02 | Schema de brief y salida de cada rol | [C][X] |
| VAL-03 | Nombres escritos exactamente como en la story bible | [C][X] |
| VAL-04 | Longitud de capítulo en rango (1.000–1.500) | [C][X] |
| VAL-05 | Cada elemento obligatorio del brief aparece ≥1 vez, comprobado contra SQLite | [C][X] |
| VAL-06 | Validación visual vía browser MCP; errores vuelven al rol correspondiente | [C][E] docs |
| VAL-07 | LLM-as-judge con rúbrica: continuidad, tono, calidad narrativa, personalización natural; puntuación + justificación por criterio | [C] |
| VAL-08 | Revisión humana de ≥1 novela con la misma rúbrica y comparación con el judge | [E][M] |
| VAL-09 | Cada validador tiene nombre y punto de ejecución (hook / editor / gate) documentado | [E] tabla en docs |
| VAL-10 | Cada validador envía su resultado a Langfuse como score | [C] |

## LEAN — Validador formal de la historia

| ID | Requisito | Verif. |
|---|---|---|
| LEAN-01 | Generador SQLite → fichero Lean (eventos, momento, personajes, lugar, nacimientos) | [C][X] |
| LEAN-02 | ≥2 invariantes definidos en Lean | [C] |
| LEAN-03 | Verificación automática (`lake build` / `lean`) integrada en el flujo | [C][X] |
| LEAN-04 | Si falla, la versión no se publica y el fallo vuelve al editor | [C][X] |
| LEAN-05 | Caso real documentado detectado solo por Lean, o justificación | [E] |

## TLA — Validador formal del sistema

| ID | Requisito | Verif. |
|---|---|---|
| TLA-01 | Spec TLA+/PlusCal: configuración → planificación → escritura → validación → publicación | [E] |
| TLA-02 | Incluye retries, reanudación desde checkpoint y regeneración por cambio del lector | [C] |
| TLA-03 | ≥3 invariantes de seguridad | [C] |
| TLA-04 | ≥1 propiedad de liveness (termina publicando o con error) | [C] |
| TLA-05 | Config TLC en repo con modelo pequeño (p. ej. 5 capítulos, 2 reintentos) | [E][X] ejecutar TLC |
| TLA-06 | README mapea cada acción de la spec a estado/transición del código | [E][C] |
| TLA-07 | Contraejemplos de TLC documentados con el cambio en código (si hubo) | [E] |

## EVAL — Evaluación del sistema

| ID | Requisito | Verif. |
|---|---|---|
| EVAL-01 | 5 briefs de prueba | [E] |
| EVAL-02 | ≥1 brief adversarial (injection en texto libre) | [E] |
| EVAL-03 | ≥1 brief que provoca incoherencia temporal | [E] |
| EVAL-04 | Tabla por brief: validadores que pasan/fallan, con números | [E] |
| EVAL-05 | Iteración de tuning documentada con antes/después | [E] |

## OBS — Observabilidad (Langfuse)

| ID | Requisito | Verif. |
|---|---|---|
| OBS-01 | Una traza por generación, agrupada en una sesión por novela (entrevista + regeneraciones) | [C] |
| OBS-02 | Span identificable por rol (entrevistador, planner, writer, editor) y por tool | [C] |
| OBS-03 | Tokens, coste y latencia por llamada, capítulo y novela | [C] |
| OBS-04 | Scores de todos los validadores (programáticos, semánticos, Lean) en la traza | [C] |
| OBS-05 | Prompts versionados en Langfuse, vinculados a los resultados del tuning | [C][E] |

## GR — Guardrails

| ID | Requisito | Verif. |
|---|---|---|
| GR-01 | Guardrail de palabras prohibidas en código, antes de aceptar cada capítulo | [C] |
| GR-02 | Listas en SQLite en niveles global y por novela | [C] esquema |
| GR-03 | Normalización: mayúsculas, acentos, plurales, variantes simples | [C][X] |
| GR-04 | Coincidencia → reescritura con límite; agotado → se detiene e informa | [C][X] |
| GR-05 | Cada coincidencia en audit log y en Langfuse | [C] |
| GR-06 | Tests: un caso por nivel + un caso de variante (acento o plural) | [X] |
| GR-07 | Audit log de decisiones del policy engine | [C] |

## DOC — Documentación de proceso (/docs)

| ID | Requisito | Verif. |
|---|---|---|
| DOC-01 | Spec inicial (antes del código) | [E] |
| DOC-02 | Trade-offs como decisiones (opciones, criterios, elección) | [E] |
| DOC-03 | Explainers, uno por concepto del curso aplicado | [E] |
| DOC-04 | Diagramas: arquitectura, máquina de estados TLA+, esquema SQLite, tabla de validadores | [E] |
| DOC-05 | Registro de iteraciones (causa → efecto) | [E] |
| DOC-06 | Red-team log | [E] |
| DOC-07 | Uso real del browser MCP documentado (qué inspeccionó, qué detectó, qué cambió) | [E] |
| DOC-08 | Skills usadas/creadas en el repo y referenciadas desde /docs | [E] |
| DOC-09 | Subagentes y comandos propios documentados (si existen) | [E] |

## CC — Uso de Claude Code

| ID | Requisito | Verif. |
|---|---|---|
| CC-01 | Carpeta `.claude/` con memoria y comandos commiteada | [E] `git ls-files .claude` |
| CC-02 | Config MCP con servidor de inspección de browser (Playwright/Chrome MCP) | [E] |

## PRE — Presentación

| ID | Requisito | Verif. |
|---|---|---|
| PRE-01 | Identidad corporativa consistente (nombre, logo, paleta, tipografía) | [M] |
| PRE-02 | Portada: empresa, cliente ficticio, fecha, estudiante | [M] |
| PRE-03 | Todos los bloques de la agenda cubiertos | [M] |
| PRE-04 | Slide de presupuesto: coste unitario (tokens de Langfuse + infra + margen), precio, margen | [M] |
| PRE-05 | Coste de desarrollo en horas × tarifa | [M] |
| PRE-06 | 3 escenarios de volumen | [M] |
| PRE-07 | Sensibilidad: tokens +50 % y >3 revisiones | [M] |
| PRE-08 | Evidencias: tabla de evals, coste real Langfuse, demo de propagación | [M] |

## OPT — Opcionales (no bloquean; marcar `NO_APLICA` si no se implementan)

| ID | Requisito | Verif. |
|---|---|---|
| OPT-01 | Servidor MCP read-only (list_novels, get_chapter, list_versions, query_story_bible, download_novel), schemas, Langfuse, README | [C][X] |
| OPT-02 | Tools MCP de escritura con permisos y confirmación | [C] |
| OPT-03 | Linters de prosa adicionales | [C] |
| OPT-04 | Linter para edición manual contra story bible y palabras prohibidas | [C] |
| OPT-05 | Invariantes Lean adicionales o demostraciones generales | [C] |
| OPT-06 | TLA+ del MCP o de concurrencia entre regeneraciones | [C] |
| OPT-07 | Login con SQLite, bcrypt, JWT, aislamiento por usuario + tests | [C][X] |
| OPT-08 | Agente/skill de seguridad con `/docs/security-report.md` | [E] |
