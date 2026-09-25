# Inspección visual de la lectura

Registro de las inspecciones de la interfaz de lectura en un navegador: qué se inspeccionó, qué se detectó y qué cambio provocó. Es material de apoyo de [§11a de la arquitectura](architecture.md#a-programáticos-deterministas): el validador que decide si una versión se publica es `render_visual`, un nodo del grafo; esto es la inspección exploratoria que describe la skill [`inspeccion-visual`](../.claude/skills/inspeccion-visual/SKILL.md), y mira lo que `render_visual` no puede mirar, porque juzga la versión candidata antes de que la interfaz pueda servirla.

Una entrada por inspección. Se añaden al final; las anteriores no se editan.

---

## 2026-09-25 · `lozoya`, `metro` y `pepa` · versión 1

**Cómo.** Con Playwright y Chromium 153, conducidos desde la sesión del agente de Claude Code. El MCP `playwright` de `.mcp.json` no conectó en esa sesión (`CONNECTION_CLOSED`), así que la inspección usó la librería con el mismo enrutado en proceso que la impresión del PDF (`publication/render.py::imprimir_version`): la aplicación de FastAPI respondiendo en memoria a un origen inventado, con los estáticos de `frontend/dist`. Es la misma interfaz que ve el lector, sin servidor levantado.

**Qué se inspeccionó.** De cada novela:

- el índice de la versión 1;
- los cinco capítulos, entrando por sus enlaces;
- la portada;
- las fichas de personajes y lugares;
- los errores de consola de todo el recorrido.

Además, el nuevo `render_visual` sobre la lectura de la versión 1 de las tres.

**Qué se detectó.**

| Novela | Índice | Capítulos | Portada | Fichas | Consola | `render_visual` |
|---|---|---|---|---|---|---|
| `lozoya` | 5 enlaces | 5 con texto (13 a 32 párrafos) | Título y dedicatoria | 6 personajes; 2 de 15 escenas sin escenario | Sin errores | Sin incidencias |
| `metro` | 5 enlaces | 5 con texto (13 a 29 párrafos) | Título y dedicatoria | 5 personajes; **los 5 lugares «no aparecen en ningún capítulo»** | Sin errores | Sin incidencias |
| `pepa` | 5 enlaces | 5 con texto (10 a 17 párrafos) | Título y dedicatoria | 5 personajes; lugares enlazados | Sin errores | Sin incidencias |

El hallazgo es el de `metro`. La ficha de lugares decía de los cinco escenarios —la cocina de la casa de la protagonista, la sala de telegrafía del Palacio de Comunicaciones, sus escaleras, una calle en obras y la primera estación del metro— que no aparecían en ningún capítulo, en una novela que transcurre entera en ellos. En la base, **ninguna de las once escenas tenía `escenario_id`**. En `lozoya` faltaban dos de quince.

**Por qué.** El volcado de la escaleta enlazaba cada escena con su escenario por **coincidencia exacta** de la clave que el arquitecto daba al escenario y la que repetía en la escena. Cuando las escribía distinto, el enlace quedaba vacío y nadie se enteraba: no había incidencia, y el gate de la Trama no lo enseñaba. El render candidato no lo podía ver, porque la ficha de lugares de la lectura mínima no lleva capítulos.

**Qué cambio provocó.**

- `plotting/escaleta.py::resolver_escenario`, que busca la clave exacta, luego la normalizada con el mismo `normalizar` del guardrail y luego la única que contiene al nombre o está contenida en él.
- Lo adivinado se dice como anclaje resuelto por parecido y lo que no se resuelve se enseña en el gate de la Trama, por el mismo camino que los anclajes perdidos.
- Queda en la fila correspondiente de §17 de la arquitectura, en REQ-VA-19 de la [spec de validación](../specs/validacion/spec.md) y en It-38.

Las tres novelas ya publicadas no se han vuelto a volcar, así que `metro` sigue enseñando sus lugares sin capítulos hasta que se rehaga su Trama.

---

## 2026-09-25 · `eval-01-jubilacion` v1 y `lozoya` v3 · con el MCP de Playwright

**Cómo.** Es la primera inspección hecha de verdad con el **MCP de Playwright** que declara `.mcp.json`, y no con la librería. En las sesiones anteriores el MCP no conectaba porque en la máquina no había Node. Se instaló Node 24 LTS portátil en la carpeta del usuario y el navegador del MCP (`npx @playwright/mcp install-browser chrome-for-testing`). Después se lanzó una sesión nueva de Claude Code en modo no interactivo con `--strict-mcp-config --mcp-config .mcp.json`, con permiso solo para `mcp__playwright` y sin `Bash`, `Edit` ni `Write`. El agente siguió la skill [`inspeccion-visual`](../.claude/skills/inspeccion-visual/SKILL.md): `browser_navigate`, `browser_snapshot`, `browser_click` sobre cada enlace del índice, `browser_console_messages` y `browser_take_screenshot`. Lo hizo contra el servidor levantado en `127.0.0.1:8765`, sin reiniciarlo y sin ningún POST. Las capturas y los snapshots están en [`presentacion/capturas/inspeccion-mcp/`](../presentacion/capturas/inspeccion-mcp).

**Qué se inspeccionó.**

| Lectura | Rutas | Capítulos recorridos pulsando el índice |
|---|---|---|
| `eval-01-jubilacion` v1, la novela de ejemplo de 10 capítulos | `/v/1`, sus 10 capítulos, `/v/1/portada` y `/v/1/personajes` | 10 de 10 |
| `lozoya` v3, regenerada tras cambiar el nombre de un secundario («Cayetano» → «Amancio») | `/v/3`, sus 5 capítulos, portada, personajes y `/versiones`; para contrastar, `/v/2/capitulos/1` y `/v/2/personajes` | 5 de 5 |

**Qué se detectó.**

| | `eval-01-jubilacion` v1 | `lozoya` v3 |
|---|---|---|
| Índice | 10 enlaces; cada uno lleva al capítulo cuyo `h1` coincide | 5 enlaces; cabecera «5 capítulo(s) cambian respecto de la versión 2», los 5 marcados |
| Capítulos | Todos con texto (≈1.065-1.518 palabras); navegación anterior/siguiente coherente. **Los capítulos 6 y 7 contienen texto ajeno a la novela** (hallazgo 1) | Todos con texto. «Amancio» aparece 13 veces y «Cayetano» ninguna |
| Portada | Título y dedicatoria | Título y dedicatoria |
| Fichas | El homenajeado y los 8 lugares, «no aparece en ningún capítulo» (hallazgos 2 y 4) | Ficha «Amancio» enlazada; el homenajeado, «no aparece» (hallazgo 2) |
| Historial | — | 3 versiones; «Qué cambia» entre la v2 y la v3 coincide con el índice |
| Consola | Sin mensajes | Sin mensajes |

**Hallazgos.**

1. **La política de privacidad de la organización se ha colado en la prosa publicada.** El capítulo 7 de `eval-01` termina con la «Nota de Privacidad» que la organización impone a las respuestas de Claude, y lleva siete etiquetas entre él y el capítulo 6 (`[NOMBRE_ANONIMIZADO]`). Las etiquetas están en el lugar de los nombres de la esposa y del hijo del protagonista, que son personajes inventados con ficha en el canon (captura `inspeccion-eval01-cap7-nota-privacidad.png`). Una búsqueda en todas las bases lo confirma. Solo pasa en `eval-01` y en sus dos ramas, `fase-6-*`: los capítulos 6 y 7 publicados y tres borradores del capítulo 8. Las demás novelas están limpias.
   - **Causa.** Los roles corren con el Claude Agent SDK, que hereda la sesión de Claude Code del Autor. Esa sesión lleva las instrucciones de la organización, que piden anonimizar los nombres que parezcan de personas reales y añadir la nota. Para el escritor, los personajes de una novela son indistinguibles de datos personales. Ningún validador lo paró: `nombres_exactos` solo mira que los nombres del canon estén bien escritos, no que no aparezcan etiquetas.
   - **Consecuencia.** `ejemplos/novela-ejemplo.pdf` es la versión 1 de `eval-01` y **lleva el defecto**. Ninguna de las cinco puertas es responsable: el defecto viene de fuera del arnés, de la capa de instrucciones del proveedor.
2. **El homenajeado sale como ausente de todos los capítulos**, en las dos novelas, aunque protagoniza todos. Es sistemático para el rol homenajeado. La inspección del 25 de septiembre de `lozoya` v1 ya lo había visto.
3. **Las fichas de una versión anterior enseñan el canon vigente.** En `lozoya` v2, el capítulo 1 dice «Cayetano» cinco veces, pero su ficha de personajes muestra «Amancio». Las fichas se sirven del canon actual y no de la versión, y eso choca con que las versiones sean inmutables (§7 de la arquitectura).
4. **Los 8 lugares de `eval-01` «no aparecen en ningún capítulo»**, aunque la novela transcurre en ellos. Además, «Txalupa de vela y remo» es una embarcación catalogada como lugar. En `lozoya` los lugares sí enlazan.
5. **Menores:** un título de lugar cortado con puntos suspensivos, el historial sin enlace de vuelta al índice y la columna «Puntuación del juez» con «—» en las tres versiones de `lozoya`.

**Qué cambio provocó.**

- **La novela de ejemplo no se entrega así.** Hay que sustituir `ejemplos/novela-ejemplo.pdf` por una novela limpia, o reescribir los capítulos 6 y 7 de `eval-01` antes de exportarla. Lo decide el Autor.
- **Un validador candidato para `guardrail_prohibidas`** o hermano suyo: que bloquee las etiquetas `[…_ANONIMIZADO]`, `[…_OCULTO]` y `[…_ELIMINADO]` y el texto «Nota de Privacidad» en un capítulo. Es texto ajeno a la novela, y el editor recibiría la incidencia para quitarlo. Sube primero a §11a de la arquitectura y a la spec (AGENTS.md).
- **Queda como riesgo de producción**, y es la mejor prueba de él: el arnés no puede correr sobre una sesión de Claude Code sujeta a las instrucciones de una organización. Necesita credencial propia de API. Se anota en el red-team como RT-08.
- **Los hallazgos 2 a 4 se pasan a la sesión que lleva la lectura y la regeneración,** para que suban a la spec del frontend y del backend.
