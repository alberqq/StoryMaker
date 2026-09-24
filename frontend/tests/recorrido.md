# Recorrido de la lectura — acta de IMP-29

Demostración de clase **D** de tres requisitos de `REQUIREMENTS.md` sobre la aplicación servida por FastAPI: **LEC-02** (índice navegable), **LEC-04** (la ficha de personajes enlaza a sus capítulos) y **LEC-05** (portada con dedicatoria). La pide §10 de la spec del frontend, con gate G2, y la herramienta declarada es **Playwright MCP**, configurado en [`.mcp.json`](../../.mcp.json) de la raíz.

## Cómo se repite

1. Construir el frontend: `npm run build` en `frontend/`. FastAPI sirve `frontend/dist` desde `Settings.frontend_dist`.
2. Levantar la API en un puerto libre, apuntando al directorio de proyectos que tenga la novela: `STORYMAKER_DIRECTORIO_PROYECTOS=<dir> uv run uvicorn --factory storymaker.api.app:crear_app --port 8123` desde `backend/`. **No reiniciar ningún servidor con Ejecuciones vivas.**
3. Desde Claude Code, con el MCP de Playwright, recorrer:
   - `/` → pulsar el título de la novela abre su panel → «Leer la última» lleva a `/novelas/<id>/v/<última>`, donde aparece `[data-render="indice"]`.
   - Pulsar un capítulo del índice → se ve su texto, con anterior, siguiente e índice.
   - `/novelas/<id>/v/<n>/personajes` → pulsar un enlace «capítulo k» de una ficha → se abre ese capítulo **de la misma versión**.
   - `/novelas/<id>/v/<n>/portada` → se ve el título y la dedicatoria al homenajeado con su ocasión.
   - `/novelas/<id>/v/<n>/imprimir` → existen las cuatro regiones `data-render` (`indice`, `portada`, `personajes` y, si hay versión anterior, `novedades`) y el documento lleva `data-estado="listo"`.
   - Recargar una ruta profunda (`/novelas/<id>/v/1/capitulos/2`) → responde 200 con la aplicación, no un 404.
4. La operación (spec §4.1 a §4.5):
   - `/` → el tablero reparte las novelas por columnas; una tarjeta con gate pendiente se arrastra a la columna siguiente y el diálogo de confirmación enseña el resumen del gate antes de enviar nada.
   - `/novelas/<id>` → el panel enseña las seis fases, los capítulos, la actividad y el consumo; en una novela en marcha, la actividad avanza sola cada tres segundos.
   - `/novelas/<id>/gate` → en Intake, contestar las preguntas relanza la entrevista; en los demás gates, aprobar vuelve al panel y la novela pasa a «Arrancando» y luego a «En marcha».
   - `/novelas/<id>/fases/<fase>` → cada pestaña enseña lo que su fase dejó escrito.

## Registro

| Fecha | Sobre qué novela | Con qué | Resultado |
|---|---|---|---|
| 2026-09-24 | `salamanca` y `sevilla`, las dos primeras novelas reales publicadas, servidas por FastAPI con la interfaz de operación | Playwright para Python, en modo claro y oscuro, sin errores de consola en nueve pantallas; y una acción real lanzada por la API | El taller reparte las dos novelas en «Publicadas»; el panel, las salidas de Trama y Escritura, el encargo y la lectura se ven completos. `POST /reintentar` responde `202`, la novela pasa a «arrancando», la actividad dice «Lanzado desde la interfaz: reintentar», y la CLI desacoplada escribe en su registro que no hay capítulo que reabrir. Queda por ensayar una novela nueva de principio a fin desde el encargo, que cuesta una ejecución completa |
| 2026-09-24 | La novela sembrada de las pruebas (`backend/tests/dobles/novela_de_lectura.py`): tres capítulos, dos versiones, la segunda regenera el capítulo 2 | Playwright para Python (el MCP de Playwright no conectó en esa sesión), contra FastAPI sirviendo `dist/` en el puerto 8123 | Los seis pasos pasan: redirección a `v/2`, índice con el capítulo 2 marcado como cambiado, capítulo con navegación, ficha → capítulo 3 de la v2, portada «Para … con motivo de su jubilacion», las cuatro regiones en `imprimir`, PDF A5 impreso con `page.pdf()` y recarga profunda en 200 |

**Pendiente para cerrar IMP-29:** repetir el recorrido con Playwright MCP, que no conectó en la sesión del 2026-09-24, y encargar desde la interfaz una novela nueva y seguirla hasta publicarla.
