# MCP, skills y hooks

## El concepto

**MCP** (Model Context Protocol) es un protocolo para que un modelo hable con herramientas externas a través de servidores que exponen *tools* con su esquema. **Skills** y **hooks** son mecanismos de Claude Code: las primeras cargan instrucciones especializadas cuando hacen falta, los segundos interceptan acciones para comprobar o bloquear.

Los tres viven en la misma carpeta y es fácil mezclarlos con el producto. Conviene trazar la línea.

## La línea: el arnés y la herramienta de quien lo construye

**El arnés no depende de ningún servidor MCP externo.** Los nueve roles se invocan con el Claude Agent SDK; el investigador es el único con red (`WebSearch` y `WebFetch`), y los validadores son nodos del grafo, no *tools*. El único MCP del arnés es **en proceso**: el SDK sirve al arquitecto dos herramientas propias de calendario, `sumar_dias` y `edad_en_fecha` (`commons/agents/herramientas.py`), con su JSON Schema generado del modelo Pydantic. Una novela se genera sin levantar ningún servidor aparte.

El MCP de `.mcp.json` —Playwright— es otra cosa: lo usa **Claude Code durante el desarrollo**, no el arnés.

## Dos Playwright que no se deben confundir

**`render_visual` no usa el MCP.** Es Playwright programático desde Python (`publication/render.py`), que conduce Chromium sin agente de por medio para comprobar que el índice, la ficha de personajes y la portada se pintan. Corre **dentro de `PublishVersion`, sobre la versión candidata y antes del `commit`**.

El detalle importa más de lo que parece. G5 no admite excepción, y un índice roto detectado *después* de `PublishVersion` sería una versión ya publicada con la portada mal: no habría adónde volver. Comprobándolo con la transacción todavía abierta, si algo no renderiza la transacción se deshace y sencillamente no hay versión publicada.

No hace falta un nodo nuevo ni una arista nueva: la comprobación cabe dentro del nodo que ya existe. Es un patrón que se repite en este diseño — **meter la comprobación dentro de la transacción en lugar de después de ella**.

Playwright hace además un segundo trabajo: **imprime el PDF** con `page.pdf()` sobre la misma ruta de lectura que ve el navegador. Como ya es dependencia por la validación visual, el PDF sale gratis y, sobre todo, sale *idéntico* a la web. Si se maquetara aparte, web y PDF divergirían, y la divergencia aparece siempre el día de la demo.

**El MCP de Playwright** lo usa Claude Code a través de la skill `inspeccion-visual`: abre la lectura de una versión ya publicada y la recorre como un lector. Es exploratoria, no decide nada, y mira lo que `render_visual` no puede, porque este juzga la candidata antes de que la interfaz la sirva. Lo que encuentra se anota en [`inspeccion-visual.md`](../inspeccion-visual.md).

## Skills

Diecisiete en `.claude/skills/`. **Quince son de terceros**, copiadas desde su fuente y no editadas a mano: una skill editada localmente es una bifurcación silenciosa, que sigue pareciendo la de upstream y deja de comportarse como ella.

**Dos son propias.** `continuity-check` es la skill reutilizable del proyecto: valida un capítulo editado a mano con el mismo Core Domain que corre dentro del grafo, para que quien lo edite compruebe que no ha roto nada antes de commitear. `inspeccion-visual` es la de arriba.

El inventario completo, con procedencia y commit, y los comandos de `.claude/commands/`: [`docs/skills.md`](../skills.md).

## Hooks, y los que de verdad importan

Hay dos capas de hooks y no hacen lo mismo:

- Los de **repositorio** (`.pre-commit-config.yaml`): ruff, mypy, gitleaks. Son la puerta G0, la del portátil. Rápida por definición: lo que tarda —`mypy --strict` completo, semgrep, `pip-audit`— vive en G1, que el Autor lanza a mano antes de integrar.
- Los de **capítulo**, en `.claude/settings.json`: un `PreToolUse` de policy (`cli_policy`) que deniega la edición que introduce un término prohibido, y un `PostToolUse` de validación (`cli_hook`) que pasa el capítulo por los validadores del Core Domain.

La segunda capa es la interesante, porque cierra un agujero real. El sistema entero garantiza que **el modelo** no publica algo que no pasó los validadores. Una persona editando el fichero a mano se salta esa garantía por completo — y editar a mano es una cosa que el Autor va a hacer, porque es su novela.

## Las seis reglas de semgrep

`semgrep/` contiene seis reglas escritas para este repositorio, no genéricas de seguridad. Vigilan invariantes de la arquitectura:

| Regla | Impide |
|---|---|
| `validador-no-es-tool` | Que un validador se registre como herramienta de un agente |
| `core-domain-puro` | Que el Core Domain importe de fuera |
| `no-update-inmutables` | Un `UPDATE` sobre un capítulo |
| `sin-red-fuera-del-investigador` | Que otro rol toque la red |
| `pii-fuera-del-investigador` | Que datos del comprador salgan por donde no deben |
| `indice-solo-por-embeddings` | Que la selección de contexto se haga por otra vía |

Es la idea que más se puede robar de este proyecto: **una decisión de arquitectura que nadie comprueba es una decisión que se pierde en el tercer refactor**. Escribirla como regla de linter la convierte en algo que falla en G1 en lugar de algo que alguien recuerda.

## Dónde mirar

- La configuración del servidor: [`.mcp.json`](../../.mcp.json); los hooks: [`.claude/settings.json`](../../.claude/settings.json); las skills propias: [`continuity-check`](../../.claude/skills/continuity-check/SKILL.md) e [`inspeccion-visual`](../../.claude/skills/inspeccion-visual/SKILL.md)
- [`architecture.md` §16.1](../architecture.md#161-pila) y [§15](../architecture.md#15-guardrails-y-policy)
