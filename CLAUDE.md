# CLAUDE.md — StoryMaker

Este fichero orienta a quien abre el repositorio con Claude Code. **El proceso de trabajo no está aquí, sino en `AGENTS.md`**, que se importa al final y manda: rama `zero`, flujo arquitectura → spec → plan → código con *grilling* en cada paso, clases de verificación y reglas de operación.

## Qué es

StoryMaker es un arnés multiagente que escribe novelas históricas personalizadas para regalo: convierte a la persona homenajeada en personaje de un escenario histórico real y documentado. Un orquestador LangGraph con estado explícito en SQLite (un fichero por novela) invoca nueve roles del Claude Agent SDK, todos en Haiku 4.5, y ningún rol decide si su propio trabajo es válido: eso lo hacen validadores que son nodos del grafo, no *tools*. La salida es una versión inmutable de la novela, legible en web y en PDF, que solo se publica si pasa todos los validadores, Lean incluido.

## Los nueve roles

| Rol del enunciado | Rol en StoryMaker | Fase |
|---|---|---|
| entrevistador | `entrevistador` y `extractor de intake` (el texto pegado, en cuarentena) | 1 |
| — | `investigador` (único con red: `WebSearch`, `WebFetch`) y `verificador` | 2, 3 |
| **planner** | `arquitecto`: premisa, canon y escaleta | 3 |
| **writer** | `escritor` | 4, 6 |
| **editor/critic** | `editor` (bucle de control) **+** `juez` (rúbrica, observabilidad), separados a propósito | 4, 6 / 5 |
| — | `extractor de capítulo`: resumen, continuidad y hechos usados | 4, 6 |

La tabla completa, con entradas, salidas y herramientas, está en `docs/architecture.md` §5.

## Seis fases, cinco gates

Intake → Investigation → Plotting (sella el corpus) → Writing → Publication → Regeneration. Llevan gate humano bloqueante Intake, Investigation, Plotting, Writing y Regeneration; Publication no, porque solo maqueta lo ya aprobado (arq. §4 y §10). Un gate termina el proceso; `storymaker decidir` o la interfaz lo reanudan desde el checkpoint.

## Dónde está cada cosa

| Ruta | Contenido |
|---|---|
| `backend/src/storymaker/` | Python 3.12, *package-by-feature*: `intake/`, `investigation/`, `plotting/`, `writing/`, `publication/`, `regeneration/`, `gates/`, más `api/` (FastAPI), `cli/` (Typer) y `commons/` (grafo, agentes, contexto, BD, validación, formal, observabilidad) |
| `frontend/src/` | React + Vite en Feature-Sliced Design: `app/`, `pages/`, `entities/`, `shared/` |
| `formal/tla/` | `harness.tla` y sus dos modelos, `harness.cfg` (interactivo) y `harness_batch.cfg` (batch) |
| `formal/lean/` | Proyecto Lake de la cronología: `Cronologia/Basico.lean` (invariantes), `Generado.lean` (datos), `Verificar.lean` (ejecutable) |
| `docs/` | Arquitectura, verificación, glosario, iteraciones, explainers, skills |
| `specs/<nombre>/` | `spec.md`, `plan.md` y `trace-matrix.md` de cada pieza |
| `ejemplos/` | Briefs de ejemplo; los de evaluación en `ejemplos/evals/` |
| `backend/proyectos/` | Las novelas, una carpeta con su `.db` cada una |

## Cómo se comprueba

```bash
cd backend && uv run pytest -q                        # suite del backend
cd frontend && npm test                               # vitest; npm run comprobar = tsc -b
cd formal/lean && lake build && lake exe verificar    # 0 coherente · 1 incoherente
```

`lake` puede estar solo en `~/.elan/bin`: si no está en el PATH, el arnés cae a la evaluación en Python sin avisar, y `STORYMAKER_LEAN=0` lo apaga a propósito. TLC necesita una JVM y `tla2tools.jar`; el comando exacto está en `formal/tla/README.md`. El MCP de Playwright de `.mcp.json` necesita Node en el PATH y su navegador (`npx @playwright/mcp install-browser chrome-for-testing`). En la máquina del Autor, Node está como instalación portátil en la carpeta del usuario, y una sesión solo ve el MCP si arranca después de tener Node en el PATH.

## Lo que Claude Code tiene a mano

- **Tools con schema** del arnés: `backend/src/storymaker/commons/agents/herramientas.py` (`sumar_dias`, `edad_en_fecha`, para el arquitecto). El JSON Schema sale del modelo Pydantic y la entrada se valida otra vez dentro del manejador.
- **Dos hooks** en `.claude/settings.json`, solo sobre ficheros de capítulo:
  - `PreToolUse` de policy (`commons/validation/cli_policy.py`) deniega un `Write`/`Edit` que introduzca un término prohibido.
  - `PostToolUse` de validación (`commons/validation/cli_hook.py`) pasa el capítulo por los validadores deterministas y devuelve el informe si algo bloquea.
- **Skills propias** en `.claude/skills/`: `continuity-check` (valida a mano un capítulo con el mismo Core Domain que el grafo) e `inspeccion-visual` (recorre la lectura publicada con el MCP de Playwright de `.mcp.json`). Las demás son de terceros; inventario en `docs/skills.md`.
- **Comandos** en `.claude/commands/`: `/tlc`, `/lean`, `/estado-novelas` y `/evaluar`.

## Reglas que no se olvidan

- **No se reinicia el servidor de la interfaz con Ejecuciones vivas** (AGENTS.md, Operación). AGENTS.md cita `curl -s http://127.0.0.1:8765/api/procesos`, pero esa ruta no existe hoy en la API; lo que sí responde es `curl -s http://127.0.0.1:8765/api/novelas`, y no se reinicia si alguna tarjeta está en `en_marcha`, `arrancando` o `esperando_autor`.
- **Una ejecución real cuesta dinero**: no se lanza una novela ni `storymaker evaluar` sin que el Autor lo pida.
- **Lo que el Autor borra, borrado se queda.** No se rescata del historial de git.
- **G3 y G5 no admiten excepción**: ningún camino publica una versión sin validar.

## La memoria del proyecto

La memoria versionada que Claude Code lee es este fichero y el `AGENTS.md` que importa. La memoria automática de usuario vive en `~/.claude/`, fuera del repositorio. Detalle en `docs/skills.md`.

@AGENTS.md
