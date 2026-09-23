# Procedencia de las skills

Cada skill de esta carpeta se instala copiando su directorio desde una fuente externa.
No se editan a mano salvo para reparar rutas que solo tienen sentido en su repositorio de
origen, y esas reparaciones quedan anotadas abajo. Si hace falta cambiar una skill, se
vuelve a copiar desde el origen.

## Instaladas

| Skill | Origen | Para qué, en esta pila |
|---|---|---|
| `feature-sliced-design` | [`feature-sliced/skills`](https://github.com/feature-sliced/skills) @ `fd71da4` | La organización del frontend (§16.3 arq.). Se omite `evals/`, que solo sirve al desarrollo de la propia skill |
| `sqlite-vec` | [`existential-birds/beagle`](https://github.com/existential-birds/beagle) @ `7d9355fa` | Las tablas `vec0` de los índices semánticos (§7 y §16.2 arq.) |
| `langgraph-architecture` | `existential-birds/beagle` @ `d1a7489` | El motor de orquestación (§3, §8, §9 arq.) |
| `langgraph-implementation` | `existential-birds/beagle` @ `d1a7489` | — |
| `langgraph-code-review` | `existential-birds/beagle` @ `d1a7489` | — |
| `fastapi-code-review` | `existential-birds/beagle` @ `d1a7489` | La API, el webhook de Telegram y la reanudación de gates (§10 arq.) |
| `python-code-review` | `existential-birds/beagle` @ `d1a7489` | Backend Python 3.12 |
| `pytest-code-review` | `existential-birds/beagle` @ `d1a7489` | La técnica 5 del plan de verificación |
| `review-verification-protocol` | `existential-birds/beagle` @ `d1a7489` | No se usa sola: `fastapi-code-review` y `python-code-review` la referencian por ruta relativa y sin ella quedan rotas |
| `lean-proof` | [`leanprover/skills`](https://github.com/leanprover/skills) @ `7d3da02` | Los cuatro invariantes de la cronología (§11c arq.). Es el repositorio **oficial** de Lean |
| `lean4-setup` | `leanprover/skills` @ `7d3da02` | El proyecto Lake y las toolchains de `elan` |
| `tlaplus` | [`swingerman/engineer`](https://github.com/swingerman/engineer) @ `32947eb` | La especificación PlusCal del arnés y TLC (§11d arq.) |
| `webapp-testing` | [`anthropics/skills`](https://github.com/anthropics/skills) @ `34040c9` | Validación visual del lector y la ruta desde la que se imprime el PDF (§16.1 arq.) |

### Reparaciones aplicadas

- **`sqlite-vec`** fue retirada de `main` de `beagle` el 2026-05-27, en la reestructuración
  del marketplace (`242d64b`), aunque sigue publicada en
  [mcpmarket](https://mcpmarket.com/tools/skills/sqlite-vector-search-sqlite-vec). Se copia
  del último commit en que existía, `7d9355fa`, desde
  `plugins/beagle-core/skills/sqlite-vec/`.
- **`tlaplus`** venía de un plugin y resolvía sus rutas con `${CLAUDE_PLUGIN_ROOT}`, que
  aquí no existe. Las dos referencias a `scripts/tlc.sh` apuntan ahora a
  `.claude/skills/tlaplus/scripts/tlc.sh`, y se ha quitado el envío a
  `references/handoff-dispatch.md`, un fichero del plugin que no acompaña a la skill.
  Con él se fue la mención al flujo `/engineer`, ajeno a este repositorio; la instrucción
  que quedó —no abrir un PR sin el visto bueno del Autor— coincide con `AGENTS.md`.

## Deliberadamente no instaladas

- **`pydantic-ai-*`** (seis skills en `beagle-ai`). Cubren Pydantic AI, el framework de
  agentes, que no es lo que usa StoryMaker: la pila fija **Pydantic v2** para esquemas y
  **`claude-agent-sdk`** para los agentes. Instalarlas invitaría a confundirlos.
- **`beagle-react/*`** (Remix, React Router, React Flow, shadcn, Tailwind, Zustand).
  El frontend es React + Vite consumiendo la API, sin ninguno de esos añadidos.
- **`postgres-code-review`, `sqlalchemy-code-review`**. Los datos son SQLite con
  `aiosqlite`, un fichero por novela.
- **`lackeyjb/playwright-skill`**. Es una skill de Playwright sobre Node. La nuestra corre
  desde Python —`page.pdf()` sobre la ruta de lectura— así que se prefiere
  `webapp-testing`, que usa `playwright.sync_api`.
- **Las skills de mathlib** de `leanprover/skills` (`mathlib-build`, `mathlib-pr`,
  `mathlib-review`, `lean-bisect`, `lean-mwe`, `nightly-testing`). Sirven para contribuir a
  mathlib y para reportar regresiones del toolchain, no para escribir los invariantes de
  una cronología.
- **`claude-api`** ya viene con el harness, así que no se duplica aquí.
- **FastEmbed, Typer y `aiosqlite`** no llevan skill. Son superficies pequeñas y estables,
  y su parte difícil en este proyecto —cómo se indexa y cómo se consulta— está en la skill
  `sqlite-vec` y en §16.2 de la arquitectura, no en la API de la librería.

## Dos avisos

**Steiger necesita Node.** El linter oficial de FSD se ejecuta con `npx steiger src`, y
esta máquina no tiene `node` ni `npx` instalados. No es un problema propio: Vite ya exige
Node, de modo que llega con la cadena de herramientas del frontend. Mientras no esté, la
regla de capas de FSD no se comprueba sola. Por decisión del Autor, Steiger **informa y no
bloquea** (§16.3 arq. y §3.2 del plan de verificación).

**`sqlite-vec` es una extensión nativa.** Se carga con `enable_load_extension` y hay
intérpretes de Python compilados sin soporte de extensiones. Es la única dependencia de la
pila que puede fallar por cómo esté construido el intérprete. Queda registrada como riesgo
aceptado U-15 en el plan de verificación.
