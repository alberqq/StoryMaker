# Presentación — Novela Relicario

Propuesta técnico-comercial de StoryMaker, presentada por **Qapítulo, una iniciativa de Qaracter** («Cada persona merece su capítulo») al cliente ficticio **Relicario**, un e-commerce de regalos personalizados. Diez minutos de propuesta y cinco de preguntas técnicas.

**Idioma:** castellano, con los términos técnicos en inglés (harness, planner, writer, gate, checkpoint, trace, score…).

## Contenido

| Fichero | Qué es | Estado |
|---|---|---|
| `storymaker-propuesta.pptx` | Deck principal, formato editable: 23 slides, texto editable, fuentes incrustadas y el guion como notas del orador | Hecho |
| `storymaker-propuesta.pdf` | Deck principal en PDF, 23 slides | Hecho |
| `anexo-arquitectura.pdf` | A1 · Topología del harness y techos de contexto por rol | Hecho · 6 páginas |
| `anexo-tla-spec.pdf` | A2 · Máquina de estados TLA+ comentada y contraejemplos de TLC | Hecho · 6 páginas |
| `anexo-esquema-sqlite.pdf` | A3 · Story bible en SQLite, por familias de tablas | Hecho · 5 páginas |
| `anexo-validadores.pdf` | A4 · Validadores, punto de ejecución y si bloquean | Hecho · 5 páginas |
| `anexo-evals-tabla.pdf` | A5 · Resultados completos por brief, con juez por criterio, tokens y coste | Hecho · 4 páginas |
| `anexo-juez-vs-humano.pdf` | A6 · Rúbrica aplicada por el juez y por una persona a la misma novela (Barcelona 1929) | Hecho · 3 páginas |
| `anexo-red-team.pdf` | A7 · Casos adversariales, clase de evidencia y mitigación | Hecho · 5 páginas |
| `anexo-sensibilidad.pdf` | A8 · Margen frente a precio de tokens y revisiones, y escenarios de la versión 2 | Hecho · 4 páginas |
| `demo.mp4`, o su enlace aquí si supera el límite de GitHub | Vídeo de la demo: un cambio del lector propagado a los capítulos afectados | Por grabar |
| [`guion.md`](guion.md) | Guion slide por slide, con tiempos y preparación de preguntas | Hecho |
| [`deck/`](deck) | Fuentes del deck: `index.html`, `datos.json` (todas las cifras y los datos de portada), `construir.py` (PDF + PPTX, desde `backend/`: `uv run --with python-pptx python ../presentacion/deck/construir.py`) e `incrustar_fuentes.ps1` | Hecho |
| [`prompts-claude-design.md`](prompts-claude-design.md) | Especificación de contenido de cada slide, escrita al principio como prompts para Claude Design | Histórico |
| [`anexos/`](anexos) | Fuentes HTML de los anexos, con `marca.css`, `marca.js` e `imprimir.py` (se ejecuta desde `backend/`: `uv run python ../presentacion/anexos/imprimir.py`) | Hecho |
| [`capturas/`](capturas) | Capturas de la lectura web, de Langfuse (con la clave tapada), de la demo y de la inspección con el MCP de Playwright | Hecho |
| [`datos/`](datos) | `extraer.py` saca de las bases, en solo lectura, las cifras de evals y costes a `evals.md` y `evals.json` | Hecho |
| [`hoja-revision-humana.md`](hoja-revision-humana.md) | Hoja para puntuar a mano una novela con la rúbrica del juez | Usada: el acta está en `docs/revision-humana.md` §5 |

## De dónde salen las cifras

Las cifras del deck no se escriben a mano: salen de las bases SQLite de las novelas generadas, en `backend/proyectos/<novela>/<novela>.db`. El coste por fase sale de `fase_run`, las puntuaciones de `score`, los fallos de los validadores de `incidencia` y las versiones de `version_novela` y `version_capitulo`. El histórico de cambios que explica cada ajuste está en [`docs/iteraciones.md`](../docs/iteraciones.md), y lo que verificó TLC, en [`formal/tla/README.md`](../formal/tla/README.md).

Las cifras económicas que no son medidas —tarifa horaria, supervisión humana, infraestructura, precio de venta, tipo de cambio— están marcadas como estimación en la propia slide, con su supuesto.
