---
name: inspeccion-visual
description: Inspecciona en el navegador la lectura de una novela publicada de StoryMaker —indice, capitulos, portada y fichas— con el MCP de Playwright, y anota lo que encuentre. Usar despues de publicar una version, o cuando se toque la interfaz de lectura o la maqueta del render.
---

# inspeccion-visual

Abre la interfaz de lectura real (React) de una version publicada, la recorre como un
lector y anota lo que no se ve bien. **No es un validador del grafo**: el que decide si una
version se publica es `render_visual`, un nodo que conduce Chromium sin agente de por medio
(arq. §11a). Esta inspeccion es exploratoria y mira lo que `render_visual` no puede mirar,
porque juzga la version candidata antes de que la interfaz pueda servirla.

## Antes de empezar

- El servidor de la interfaz tiene que estar levantado en `http://127.0.0.1:8765`.
  **No se reinicia con Ejecuciones vivas** (AGENTS.md, Operacion).
- El MCP `playwright` esta declarado en `.mcp.json`. Si no conecta, la misma inspeccion se
  puede hacer con la libreria de Playwright desde `backend/`, con el enrutado en proceso que
  usa `publication/render.py::imprimir_version`, sin servidor levantado.

## Recorrido

Para la novela `<n>` y la version `<k>`:

1. **Indice** — `browser_navigate` a `/novelas/<n>/v/<k>`. `browser_snapshot`: tiene que
   haber un enlace por capitulo de la version.
2. **Capitulos** — pulsa cada enlace del indice (`browser_click`), no navegues por URL: lo
   que se comprueba es que el indice lleva. En cada uno, el texto tiene que estar y el
   titulo tiene que ser el del capitulo.
3. **Portada** — `/novelas/<n>/v/<k>/portada`: titulo y dedicatoria visibles.
4. **Personajes y lugares** — `/novelas/<n>/v/<k>/personajes`: cada ficha con sus capitulos.
   Un personaje o un lugar que «no aparece en ningun capitulo» en una novela que transcurre
   ahi es un hallazgo, no un detalle.
5. **Consola** — `browser_console_messages`: ningun error.
6. Captura de lo que falle con `browser_take_screenshot`.

## Que se hace con lo que aparezca

Cada inspeccion se anota en `docs/inspeccion-visual.md`, con lo que se inspecciono, lo que
se detecto y el cambio que provoco en el codigo o en los prompts. Un hallazgo que el grafo
deberia haber parado se sube arriba: primero la arquitectura, luego la spec (AGENTS.md).
