# Skills, subagentes y comandos

Qué capacidades de Claude Code usa este repositorio, de dónde vienen y para qué sirve cada una **en esta pila concreta**. El inventario con la procedencia exacta —repositorio de origen, commit y reparaciones aplicadas— vive en [`.claude/skills/PROCEDENCIA.md`](../.claude/skills/PROCEDENCIA.md); este documento es la vista desde el proyecto, que es lo que hace falta para decidir si una skill sobra o falta.

## El criterio

**Las skills se instalan copiando el directorio desde su fuente, y no se editan a mano** salvo para reparar rutas que solo tienen sentido en el repositorio de origen. Si hace falta cambiar una, se vuelve a copiar desde el origen. La razón es que una skill editada localmente es una bifurcación silenciosa: sigue pareciendo la de upstream, deja de comportarse como ella, y nadie lo nota hasta que upstream cambia.

Cada reparación aplicada queda anotada en `PROCEDENCIA.md` con lo que se tocó y por qué.

## Las quince instaladas

`.claude/skills/` tiene diecisiete carpetas: **quince instaladas de terceros**, que son las que inventaría `PROCEDENCIA.md`, y **dos propias**, `continuity-check` e `inspeccion-visual`, que se cuentan más abajo. Las quince, agrupadas por la parte del sistema a la que sirven.

### El motor de orquestación

| Skill | Sirve a |
|---|---|
| `langgraph-architecture` | Las decisiones de §3, §8 y §9 de la arquitectura: el grafo, las ejecuciones de fase y la máquina de estados |
| `langgraph-implementation` | La escritura de los nodos y las aristas condicionales |
| `langgraph-code-review` | La revisión de lo anterior |

### La persistencia y el contexto

| Skill | Sirve a |
|---|---|
| `sqlite-vec` | Las tablas `vec0` de los índices semánticos (§7 y §16.2). Son la gestión de contexto: deciden qué porción del material entra en cada paquete |

### La superficie web

| Skill | Sirve a |
|---|---|
| `fastapi-code-review` | La API, el webhook de Telegram y la reanudación de gates (§10) |
| `feature-sliced-design` | La organización del frontend en FSD v2.1 (§16.3) |
| `webapp-testing` | La validación visual del lector y la ruta desde la que se imprime el PDF (§16.1) |

### La verificación formal

| Skill | Sirve a |
|---|---|
| `lean-proof` | Los invariantes de la cronología (§11c). Del repositorio **oficial** de Lean |
| `lean4-setup` | El proyecto Lake y las toolchains de `elan` |
| `tlaplus` | La especificación del arnés y las ejecuciones de TLC (§11d) |

### El método

| Skill | Sirve a |
|---|---|
| `grilling` | El *grilling* que `AGENTS.md` exige al cerrar la arquitectura, la spec y el plan: una entrevista por rondas que recorre el árbol de decisiones hasta que no quedan hilos sueltos. Los hechos los busca el agente; las decisiones son del Autor |
| `grill-me` | El mismo *grilling*, invocado a mano con `/grill-me` |

### El código Python

| Skill | Sirve a |
|---|---|
| `python-code-review` | Backend Python 3.12 |
| `pytest-code-review` | La técnica 5 del plan de verificación |
| `review-verification-protocol` | No se usa sola: las dos anteriores y `fastapi-code-review` la referencian por ruta relativa, y sin ella quedan rotas |

## Las dos skills propias

No se instalan desde ninguna fuente, así que no figuran en `PROCEDENCIA.md` y el criterio de no editarlas a mano no se les aplica: se mantienen aquí, como el resto del código del proyecto.

### `continuity-check`, la skill reutilizable

§19 de la arquitectura la declara **la skill reutilizable del proyecto**, y existe en [`.claude/skills/continuity-check/SKILL.md`](../.claude/skills/continuity-check/SKILL.md). Sirve a quien edita a mano un capítulo en el disco: antes de commitear o de regenerar el PDF, comprueba que la edición no ha roto los guardrails ni la continuidad, con los validadores deterministas del arnés —longitud, nombres exactos del canon, anacronismos fechados, anclajes y términos prohibidos—.

Se invoca con `/continuity-check`, o Claude Code la carga sola cuando se edita un fichero de capítulo. Lo que ejecuta es un módulo del backend, con la ruta del capítulo como argumento:

```bash
cd backend && uv run python -m storymaker.commons.validation.cli_hook <capitulo.md>
```

El contexto —nombres del canon, prohibidas, entidades fechadas, fecha narrativa y rango de palabras— lo lee de un `<capitulo>.contexto.json` al lado del fichero; sin él, valida solo las reglas que no lo necesitan. Cada incidencia sale como **BLOQUEA** (en producción el capítulo volvería al editor) o como **aviso** (viajaría al encargo del capítulo siguiente).

El punto importante de su diseño es que **no es una segunda implementación**. §15 lo dice con todas las letras: la validación vive en el Core Domain, y tanto el nodo del grafo como la skill y los hooks la invocan. `cli_hook` llama a `commons/validation/entrada_manual.py`, que a su vez llama a `validar_capitulo` de `chapter_validator.py` y a `guardrail_prohibidas` de `policy_checker.py`: los mismos objetos que el grafo ejecuta como nodos. Una prueba de contrato, `backend/tests/contratos/test_nodo_vs_hook.py`, comprueba capítulo a capítulo que el nodo y el hook dan el mismo veredicto.

Lo que **no** comprueba es lo que necesita la base de datos o un modelo: la cobertura de personalización, la ejecución de la escaleta y el arco, y los invariantes de Lean sobre la cronología acumulada.

La acompañan los dos hooks de `.claude/settings.json`, que corren las mismas reglas sin que nadie las pida y solo sobre ficheros de capítulo: el `PreToolUse` de policy (`commons/validation/cli_policy.py`) deniega un `Write`, `Edit` o `MultiEdit` que introduzca un término prohibido, y el `PostToolUse` de validación (`cli_hook.py`) pasa el capítulo entero por los validadores y devuelve el informe al agente si algo bloquea.

### `inspeccion-visual`

[`.claude/skills/inspeccion-visual/SKILL.md`](../.claude/skills/inspeccion-visual/SKILL.md) recorre en el navegador la lectura de una versión publicada como lo haría un lector: índice, cada capítulo entrando por su enlace, portada, fichas de personajes y lugares y errores de consola. Usa el MCP de Playwright que declara `.mcp.json`, y se invoca con `/inspeccion-visual` después de publicar una versión o de tocar la interfaz de lectura o la maqueta del render.

**No es un validador del grafo.** El que decide si una versión se publica es `render_visual`, un nodo que conduce Chromium desde Python sin agente de por medio (arq. §11a). La inspección es exploratoria y mira lo que `render_visual` no puede, porque este juzga la versión candidata antes de que la interfaz pueda servirla. Cada inspección se anota en [`inspeccion-visual.md`](inspeccion-visual.md) con lo que se inspeccionó, lo que se detectó y el cambio que provocó. La primera, del 2026-09-25, se hizo con la librería de Playwright porque el MCP no conectó en esa sesión, y es la que llevó a `resolver_escenario`.

## Comandos propios

Viven en `.claude/commands/` y son *slash commands* de Claude Code: un Markdown con su `description` en el frontmatter, que Claude Code ofrece como `/<nombre>` y que recibe lo que se escriba detrás en `$ARGUMENTS`. Los cuatro recogen operaciones que se repetían a mano durante el desarrollo, y los cuatro dicen expresamente que no reinician el servidor de la interfaz.

| Comando | Para qué | Qué hace |
|---|---|---|
| `/tlc` | Comprobar que el modelo del arnés sigue pasando | Corre TLC desde `formal/tla/` sobre `harness.cfg` y `harness_batch.cfg` (o solo uno, con `interactivo` o `batch`) mediante el envoltorio de la skill `tlaplus`, y resume por modelo el veredicto, los estados generados y distintos y la profundidad, comparándolos con la tabla de `formal/tla/README.md`. Un contraejemplo se cuenta al Autor; no toca el modelo para que pase |
| `/lean` | Comprobar que el validador formal de la historia compila y decide | `lake build` y `lake exe verificar` en `formal/lean/`, buscando `lake` también en `~/.elan/bin`, e interpreta el código de salida, que es el contrato: `0` coherente, `1` incoherente. Sobre el ejemplo versionado lo esperado es `1` |
| `/estado-novelas` | Saber qué está pasando sin tocar nada | Lee `GET /api/novelas` (o el panel de una novela) si la interfaz está levantada, y si no `storymaker estado <novela>`, y resume fase, estado, gate, capítulos, versiones y coste. Señala las Ejecuciones vivas, que son las que impiden reiniciar el servidor |
| `/evaluar` | Generar los briefs de evaluación | Lanza `storymaker evaluar --briefs ../ejemplos/evals` en modo batch. Pasa la ruta explícita porque el valor por defecto de la opción apunta a `evals/briefs`, que ya no existe. Avisa de que son ejecuciones reales y de pago, y **no lanza nada sin confirmación expresa del Autor** |

## Subagentes

**No hay `.claude/agents/`, y es deliberado.** Los nueve roles de este sistema **no son subagentes de Claude Code**: son invocaciones del Claude Agent SDK desde el orquestador, con su modelo, sus herramientas y su techo de turnos fijados por invocación. Definirlos además como subagentes de `.claude/` crearía dos definiciones del mismo rol —una que el arnés usa en producción y otra que solo existe cuando el Autor trabaja en el repositorio— y la segunda derivaría de la primera sin que nada lo detectara.

Otra cosa es cómo se ha **desarrollado** el repositorio. Durante el desarrollo se usaron los subagentes que Claude Code trae de serie, sin definición propia: `Explore` para las búsquedas amplias por el código y `general-purpose` para tareas de varios pasos, como auditorías del repositorio contra el enunciado o pasadas de documentación hechas en paralelo con otras sesiones. Esta misma revisión de `docs/skills.md`, de `CLAUDE.md` y de `.claude/commands/` la hizo un subagente `general-purpose`. No dejan artefacto propio: lo que producen es un cambio en los documentos o en el código, y su rastro está en esos ficheros y en `docs/iteraciones.md`.

La skill que más se ha usado es `grilling`, porque `AGENTS.md` la exige al cerrar la arquitectura, la spec y el plan. `docs/iteraciones.md` recoge lo que dio en varias iteraciones —It-24, It-27, It-32 e It-37, entre otras— y también dónde se saltó: It-36 se implementó sin grilling a petición del Autor, y su spec y su plan se escribieron después.

## La memoria del proyecto

En Claude Code, la memoria de proyecto que se versiona son los ficheros `CLAUDE.md`, que Claude Code carga al abrir el repositorio junto con los ficheros que importan con `@ruta`. Aquí son dos:

- [`CLAUDE.md`](../CLAUDE.md), en la raíz: la orientación de quien abre el repositorio —qué es el arnés, los nueve roles y su equivalencia con los del enunciado, las fases y los gates, dónde está cada cosa, cómo se corren las pruebas, Lean y TLC, las tools, los hooks, las skills y los comandos— y las reglas operativas que no se pueden olvidar. Termina importando `AGENTS.md`.
- [`AGENTS.md`](../AGENTS.md): el proceso de trabajo —la rama, dónde vive cada decisión, el flujo dirigido por especificación con su grilling en cada paso, la verificación, la documentación, el criterio de producto y las reglas de operación—. Es el que manda, y es también lo que leería cualquier otro agente que no fuera Claude Code.

Las lecciones que el Autor ha ido corrigiendo en el camino —no reiniciar el servidor con Ejecuciones vivas, no rescatar del historial lo que se ha borrado— están escritas en `AGENTS.md`, y por eso no hay un mecanismo de memoria aparte en `.claude/`: Claude Code no leería uno inventado.

La **memoria automática de usuario** de Claude Code vive fuera del repositorio, en `~/.claude/` (la del proyecto, en `~/.claude/projects/<proyecto>/memory/`). Es personal de cada máquina, no se versiona y el arnés no depende de ella.

## Lo que este documento no cubre

El inventario de skills **deliberadamente no instaladas**, con el motivo de cada descarte, está al final de [`PROCEDENCIA.md`](../.claude/skills/PROCEDENCIA.md). Se mantiene allí y no aquí porque es una decisión sobre el entorno de trabajo, no sobre la arquitectura del producto.
