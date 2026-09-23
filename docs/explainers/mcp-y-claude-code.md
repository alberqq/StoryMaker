# MCP, skills y hooks

## El concepto

**MCP** (Model Context Protocol) es un protocolo para que un modelo hable con herramientas externas a través de servidores que exponen *tools* con su esquema. **Skills** y **hooks** son mecanismos de Claude Code: las primeras cargan instrucciones especializadas cuando hacen falta, los segundos interceptan acciones para comprobar o bloquear.

Los tres viven en la misma carpeta y es fácil mezclarlos con el producto. Conviene trazar la línea.

## La línea: el arnés y la herramienta de quien lo construye

**El arnés no usa MCP para nada de su funcionamiento.** Los nueve roles se invocan con el Claude Agent SDK, sus herramientas son las que el SDK ofrece —`WebSearch` y `WebFetch`, y solo para el investigador— y los validadores son nodos del grafo, no *tools*. Una novela se genera sin que ningún servidor MCP esté levantado.

Lo que sí usa MCP es **el desarrollo y la validación visual**.

## Playwright MCP, y por qué está en el sitio raro

`render_visual` comprueba que el índice, la ficha de personajes y la portada se ven bien, y corre **dentro de `PublishVersion`, sobre la versión candidata y antes del `commit`**.

El detalle importa más de lo que parece. G5 no admite excepción, y un índice roto detectado *después* de `PublishVersion` sería una versión ya publicada con la portada mal: no habría adónde volver. Comprobándolo con la transacción todavía abierta, si algo no renderiza la transacción se deshace y sencillamente no hay versión publicada.

No hace falta un nodo nuevo ni una arista nueva: la comprobación cabe dentro del nodo que ya existe. Es un patrón que se repite en este diseño — **meter la comprobación dentro de la transacción en lugar de después de ella**.

Playwright hace además un segundo trabajo: **imprime el PDF** con `page.pdf()` sobre la misma ruta de lectura que ve el navegador. Como ya es dependencia por la validación visual, el PDF sale gratis y, sobre todo, sale *idéntico* a la web. Si se maquetara aparte, web y PDF divergirían, y la divergencia aparece siempre el día de la demo.

## Skills

Trece instaladas, todas de terceros, **copiadas desde su fuente y no editadas a mano**. Una skill editada localmente es una bifurcación silenciosa: sigue pareciendo la de upstream y deja de comportarse como ella.

La skill **propia** que el proyecto declara —`continuity-check`— todavía no existe. Expondría a Claude Code la misma validación de continuidad que corre dentro del grafo, para que quien edite un capítulo a mano compruebe que no ha roto nada antes de commitear.

El inventario completo, con procedencia y commit: [`docs/skills.md`](../skills.md).

## Hooks, y el que de verdad importa

Hay dos capas de hooks y no hacen lo mismo:

- Los de **repositorio** (`.pre-commit-config.yaml`): ruff, mypy, gitleaks. Son la puerta G0, la del portátil. Rápida por definición: lo que tarda —`mypy --strict` completo, semgrep, `pip-audit`— vive en G1, en CI.
- El de **capítulo**, previsto en `.claude/`: expone la validación del Core Domain a una persona que edita texto a mano.

El segundo es el interesante, porque cierra un agujero real. El sistema entero garantiza que **el modelo** no publica algo que no pasó los validadores. Una persona editando el fichero a mano se salta esa garantía por completo — y editar a mano es una cosa que el Autor va a hacer, porque es su novela.

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

Es la idea que más se puede robar de este proyecto: **una decisión de arquitectura que nadie comprueba es una decisión que se pierde en el tercer refactor**. Escribirla como regla de linter la convierte en algo que falla en CI en lugar de algo que alguien recuerda.

## Dónde mirar

- La configuración del servidor: [`.mcp.json`](../../.mcp.json)
- [`architecture.md` §16.1](../architecture.md#161-pila) y [§15](../architecture.md#15-guardrails-y-policy)
