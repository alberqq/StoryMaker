# Lo que queda — el repositorio contra la arquitectura

Estado del árbol frente a [`docs/architecture.md`](docs/architecture.md), que es la fuente de verdad, y frente a los dos planes que la realizan, [`specs/backend/plan.md`](specs/backend/plan.md) y [`specs/frontend/plan.md`](specs/frontend/plan.md).

Este documento **no decide nada y no sustituye a ninguno de los anteriores**: anota lo que falta. La cola de trabajo detallada del backend, con los comandos para reproducir cada cosa, está en [`specs/backend/continuacion.md`](specs/backend/continuacion.md). Si este documento y el árbol discrepan, el que miente es este documento y hay que reescribirlo: un estado desfasado es peor que ninguno.

---

## 1. El estado en una tabla

| Qué | Estado |
|---|---|
| Ítems del plan del backend | **139**, todos con código |
| Nodos del grafo | **24 de 24** resueltos; `nodos_pendientes()` devuelve `[]` |
| Correspondencia | Anclas, inventario del plan, matrices y requisitos: **los cuatro informes en cero** |
| Requisitos | 131 `REQ-BE-nn` y 51 `REQ-FE-nn`, sin fantasmas ni repetidos |
| `ruff` | Limpio sobre `src/`, `tests/` y `evals/` |
| Recorrido de extremo a extremo | De `Configure` a `PublishVersion` **con un transporte falso**, en `tests/integracion/test_extremo_a_extremo.py` |
| Recorrido con un modelo real | **Nunca ha ocurrido** |
| Frontend | **0 de 31 ítems**; el directorio `frontend/` no existe |

Los seis hitos del backend están cerrados en código. Lo que falta no es escribir más, sino **correr el sistema contra el modelo** y cerrar con esa ejecución los ítems que solo ella puede cerrar.

---

## 2. Lo que falta en el backend

### 2.1 La primera novela real

El sistema recorre una novela entera con dobles, y ninguna ejecución ha hablado todavía con el modelo. La única puerta al modelo es el Claude Agent SDK, que lanza Claude Code como subproceso y hereda su sesión: hace falta una máquina con el CLI `claude` autenticado. Los pasos están en §3 de `continuacion.md`.

### 2.2 Los cinco ítems que cuelgan de esa ejecución

Tienen el código escrito y les falta haber corrido.

| Ítem | Qué falta |
|---|---|
| **P-120** | Los cinco briefs de evaluación en modo batch: cero incidencias críticas, 5/5 completan, ≥ 70 % de capítulos al primer intento |
| **P-121** | La varianza del juez sobre N ejecuciones de la misma novela |
| **P-122** | La primera revisión humana con la rúbrica, con su acta en `docs/revision-humana.md` |
| **P-123** | Las aserciones de G6 contra la traza real de Langfuse |
| **P-124** | `ejemplos/novela-ejemplo.pdf` commiteado con su manifiesto |

Ninguno corre en CI. La nocturna de G2 lleva `mutmut` y CrossHair, que sí caben en un *runner*; los briefs no, porque un *runner* de GitHub no tiene sesión de Claude Code.

### 2.3 Una decisión pendiente del Autor

**Las aristas de aborto.** §10 de la arquitectura ofrece «abortar» en los cinco gates, y el modelo TLA+ solo declara la arista a `Fail` desde el gate de Intake. `tras_gate` revienta a propósito en los demás en lugar de inventarse una transición que TLC no ha explorado. Las dos salidas —añadir las aristas a `formal/tla/harness.tla` y volver a correr TLC, o estrechar §10— están descritas en §5.2 de `continuacion.md`.

---

## 3. Lo que falta en el frontend

Todo. Sus 31 ítems están en [`specs/frontend/plan.md`](specs/frontend/plan.md), organizados en Feature-Sliced Design v2.1, y consumen los endpoints de lectura, decisión y cambio que el backend ya expone. El backend levanta sin el `dist/` del frontend: lo que falla sin él es la ruta de la aplicación y, con ella, el render del PDF de la publicación.

---

## 4. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-23 | Reescrito entero contra el estado real: los 139 ítems del backend tienen código, los 24 nodos están resueltos y lo que queda es la primera ejecución real, los cinco ítems que cuelgan de ella, la decisión de las aristas de aborto y el frontend | La versión anterior era de antes de la implementación y describía H6 y H7 como sin empezar, con 503 pruebas. Se leía como estado y ya no lo era |
