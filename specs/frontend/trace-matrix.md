# Matriz de trazabilidad — arquitectura ↔ plan del frontend

Correspondencia ítem a ítem entre [`docs/architecture.md`](../../docs/architecture.md), que es **la fuente de verdad y no se modifica desde aquí**, y [`plan.md`](plan.md), el plan de implementación del frontend.

**Cómo se lee.** Cada fila `ARQ-nn` es una decisión o un componente que la arquitectura fija y que cae del lado del frontend. Se marca `CUBIERTO` **solo si algún ítem `IMP-nn` del plan lo materializa con entregable concreto y criterio de hecho**; «implementar X» no cuenta, y por eso la columna de notas señala también las coberturas que dependen de algo que todavía no existe. Se marca `GAP` en cualquier otro caso.

**Reglas que esta matriz respeta.** Ninguna fila `ARQ` se elimina ni se fusiona para reducir huecos: el inventario nació con **31 filas** y hoy son **36**; puede crecer cuando la arquitectura decide algo nuevo, nunca menguar. Un hueco se cierra añadiendo o ampliando ítems en el plan, nunca borrando la exigencia. Donde la arquitectura es ambigua o no asigna superficie, queda anotado en la nota y **no se inventa requisito**.

**Alcance.** El frontend, en detalle. La vista consolidada de todo el repositorio —la arquitectura entera contra los dos planes— está en [`trace-matrix.md`](../../trace-matrix.md) de la raíz, donde estas filas aparecen como `ARQ-74`, `ARQ-102`, `ARQ-107` y `ARQ-117` a `ARQ-132`.

**Las dos mitades.** La correspondencia del backend vive en [`specs/backend/trace-matrix.md`](../backend/trace-matrix.md) con su propio espacio de identificadores (`A-nn` ↔ `P-nn`), y las dos matrices no se pisan.

---

## 1. Inventario: arquitectura → plan

| ARQ-ID | Descripción | IMP-IDs | Estado | Nota |
|---|---|---|---|---|
| ARQ-01 | §1, §16.1 · Frontend en **React + Vite** consumiendo la API | IMP-01, IMP-09 | CUBIERTO | — |
| ARQ-02 | §16.1 · **PDF con `page.pdf()` de Playwright sobre la propia ruta de lectura**, sin segunda maquetación | IMP-22, IMP-26, IMP-30 | CUBIERTO | La impresión es una ruta del frontend; quien la conduce es `publication/` (P-94) |
| ARQ-03 | §16.1 · Validación visual con **Playwright MCP** | IMP-23, IMP-29 | CUBIERTO | El MCP ya está configurado en `.mcp.json`; IMP-29 aporta el recorrido que lo usa |
| ARQ-04 | §16.1, §16.3 · **Steiger** sobre `frontend/src`, que **informa y no bloquea** | IMP-04 | CUBIERTO | — |
| ARQ-05 | §16.3 · Juego mínimo de capas `app/ pages/ shared/`; `widgets/` no se usa y `features/`/`entities/` no se crean de entrada | IMP-02, IMP-03 | CUBIERTO | — |
| ARQ-06 | §16.3 · `pages/reading`: lector, índice de capítulos, navegación, selección de fragmento y petición de cambio | IMP-14, IMP-15, IMP-20 | CUBIERTO | — |
| ARQ-07 | §16.3 · `pages/characters`: fichas de personajes y lugares | IMP-16 | CUBIERTO | El endpoint pasó a ser `GET /novelas/{id}/versiones/{n}/personajes` en la spec del backend |
| ARQ-08 | §16.3 · `pages/cover`: portada, dedicatoria y nota del autor | IMP-17 | CUBIERTO | El **bloque de paratexto** lo devuelve el endpoint de versión; IMP-17 ya no declara render degradado |
| ARQ-09 | §16.3 · `pages/versions`: historial, diff de manifiestos y novedades | IMP-18, IMP-25 | CUBIERTO | — |
| ARQ-10 | §16.3 · `shared/api`: cliente de la API y tipos de transporte, **sin reglas de negocio** | IMP-05, IMP-09, IMP-10 | CUBIERTO | — |
| ARQ-11 | §16.3 · `shared/ui`: kit de componentes | IMP-11 | CUBIERTO | — |
| ARQ-12 | §16.3 · `shared/lib`: utilidades y hooks | IMP-12 | CUBIERTO | — |
| ARQ-13 | §16.3 · `shared/config`: rutas y variables de entorno | IMP-08 | CUBIERTO | — |
| ARQ-14 | §16.3 · `app/`: providers, router, estilos globales y fuentes | IMP-06, IMP-07 | CUBIERTO | — |
| ARQ-15 | §16.3 · **API pública por segmento** de `shared`, no un `shared/index.ts` único | IMP-02 | CUBIERTO | Criterio de hecho de IMP-02: no existe el índice único |
| ARQ-16 | §16.3 · Las dos reglas de importación: solo de capas estrictamente inferiores, y ningún cruce entre slices de la misma capa | IMP-03, IMP-04, IMP-08 | CUBIERTO | Los constructores de ruta de IMP-08 son lo que evita el cruce entre páginas |
| ARQ-17 | §16.3 · **Assets junto al código que los usa**; estilos globales y fuentes en `app/` | IMP-06 | CUBIERTO | — |
| ARQ-18 | §16.3 · La petición de cambio se ejerce **dentro del lector**, no en una slice propia; extracción a `features/change-request/` solo si un segundo consumidor aparece | IMP-20 | CUBIERTO | La condición de extracción está escrita en §4.2 de la spec y en el criterio de hecho de IMP-20 |
| ARQ-19 | §4 Fase 5 · Lectura web contra el manifiesto: **índice navegable, ficha de personajes y lugares enlazada a sus capítulos, portada con dedicatoria** | IMP-14, IMP-16, IMP-17, IMP-24 | CUBIERTO | Son los tres objetos que `render_visual` mira |
| ARQ-20 | §4 Fase 5, §11a · **`render_visual` corre dentro de `PublishVersion`, sobre la versión candidata y antes del `commit`** | IMP-23, IMP-27 | CUBIERTO | El nodo es del backend (P-92), que sirve el manifiesto candidato interceptando las peticiones; del frontend dependen las anclas y ser interceptable |
| ARQ-21 | §4 Fase 5 · El PDF se maqueta **después** del render, imprimiendo esa misma ruta | IMP-22, IMP-30 | CUBIERTO | — |
| ARQ-22 | §4 Fase 6 · El lector pide el cambio **desde la propia página** | IMP-20, IMP-21 | CUBIERTO | — |
| ARQ-23 | §4 Fase 6 · El diff de dos manifiestos produce **página de novedades en el PDF y distintivo en el índice web** | IMP-14, IMP-25 | CUBIERTO | — |
| ARQ-24 | §4 Fase 6, §7 · **La versión anterior sobrevive entera** y se puede seguir leyendo | IMP-18 | CUBIERTO | — |
| ARQ-25 | §16.4 · La API sirve la lectura y la petición de cambio **sin autenticación** (U-17) | IMP-09 | CUBIERTO | El frontend no guarda credenciales; riesgo aceptado con fila en `verification.md` §5 |
| ARQ-26 | §16.4 · **El directorio `proyectos/` es el registro**: listar novelas es listar el directorio | IMP-13 | CUBIERTO | — |
| ARQ-27 | §16.4 · Una invocación por novela: **quien llega segundo es rechazado, no encolado** | IMP-21 | CUBIERTO | Del lado del frontend significa no encolar ni reintentar solo ante un `409` |
| ARQ-28 | §19 · Idioma **castellano**, términos técnicos en inglés | IMP-31 | CUBIERTO | — |
| ARQ-29 | §19 · **MCP de navegador: Playwright** | IMP-29 | CUBIERTO | — |
| ARQ-30 | §4 Fase 1 · La **Nota del autor** como paratexto que declara licencias y personajes históricos | IMP-17 | CUBIERTO | La ambigüedad quedó resuelta arriba: §16.3 de la arquitectura asigna la nota del autor a `pages/cover/` |
| ARQ-31 | §7 · Una versión **es** su manifiesto: un capítulo solo existe dentro de una versión | IMP-07, IMP-15, IMP-19 | CUBIERTO | De aquí sale que toda ruta de lectura lleve el número de versión |
| ARQ-32 | §16.3 · `pages/library`, declarada como pantalla propia: si listar las novelas es listar `proyectos/`, alguien tiene que enseñar esa lista | IMP-13 | CUBIERTO | Nace de §16.4, que hace del directorio el registro |
| ARQ-33 | §16.3 · `pages/print`, la novela entera en un documento: la misma decisión que evita una segunda maquetación obliga a una segunda ruta | IMP-22, IMP-23, IMP-24, IMP-25 | CUBIERTO | Es la única pantalla que no está hecha para un humano: la abren Playwright y `render_visual` |
| ARQ-34 | §16.3 · **Cliente único**: ningún módulo fuera de `shared/api` emite una petición de red, y aquí es **condición de G5** y no higiene | IMP-09, IMP-27 | CUBIERTO | El criterio de hecho de IMP-09 es una prueba que falla si aparece red fuera de `shared/api` |
| ARQ-35 | §16.4 · **FastAPI sirve el frontend construido**, con un solo origen y la URL base en la configuración | IMP-26 | CUBIERTO | El lado del backend es `P-136`. Un solo origen es lo que hace que el PDF sea literalmente lo que se ve |
| ARQ-36 | §4 Fase 5 · El navegador ve la versión candidata porque `publication.publish` **le sirve las peticiones interceptadas** desde el manifiesto que vive en la transacción abierta | IMP-27 | CUBIERTO | El nodo es `P-92`; del frontend depende solo ser interceptable, que es lo que ARQ-34 garantiza |

---

## 2. Huérfanos del plan

Ítems del plan que no aparecen en la columna `IMP-IDs` de ninguna fila del inventario.

| IMP-ID | Descripción | Resolución |
|---|---|---|
| IMP-28 | Pruebas de componente e integración con MSW sobre los contratos de `shared/api`, incluidos los siete casos de error de §9 de la spec | JUSTIFICADO · Tarea transversal de verificación, no una decisión de la arquitectura: nace de `verification.md` §3.5 y se cubre en G1 |

No hay ningún otro ítem sin ancla: los treinta restantes están enlazados a al menos una fila `ARQ`, comprobado sobre el fichero y no a ojo.

---

## 3. Hallazgos del recorrido

Los tres hallazgos de la primera pasada **están cerrados arriba**, en la arquitectura, que es donde se decidían:

1. **`pages/library` y `pages/print`** figuran ya en el árbol de §16.3, cada una derivada de una decisión ya tomada: el directorio como registro y el PDF impreso desde la ruta de lectura.
2. **Las tres dependencias del backend** están contratadas: el bloque de paratexto y la ficha versionada en §5 de la spec del backend, y la interceptación del manifiesto candidato en §4 Fase 5 de la arquitectura y §4.5 de esa spec.
3. **La ambigüedad de la Nota del autor** desapareció: §16.3 le asigna superficie, `pages/cover/`.

Lo que queda del recorrido no es un hueco sino una precisión: `ARQ-03` depende de que el MCP de Playwright esté configurado, y lo está —aunque en la sesión en que se escribió esto el servidor no llegara a conectar, que es cosa del entorno y no del plan.

**La segunda pasada añadió cinco filas.** Al reescribirse hoy §16.3, §16.4 y §4 Fase 5, la arquitectura fijó cinco cosas que ninguna fila recogía: `library/` y `print/` como pantallas declaradas, el **cliente único** como condición de G5, **FastAPI sirviendo el frontend construido** y la **interceptación** con la que el navegador ve la versión candidata. Las cinco estaban ya implementadas en el plan —eran ítems sin requisito que las respaldara, que es el fallo simétrico y el que menos se nota— y ahora tienen fila.

---

## 4. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-23 | Entran `ARQ-32` a `ARQ-36`, las cinco decisiones que la arquitectura fijó hoy sobre el frontend: las dos pantallas declaradas, el cliente único como condición de G5, FastAPI sirviendo el `dist/` y la interceptación de la versión candidata | El recorrido inverso las encontró como ítems de plan sin requisito detrás. Un ítem sin requisito es trabajo que nadie acordó, aunque en este caso el acuerdo existía y lo que faltaba era la fila |
| 2026-09-23 | Cerrados los tres hallazgos y las notas de dependencia de `ARQ-07`, `ARQ-08`, `ARQ-20` y `ARQ-30`: lo que faltaba se decidió en la arquitectura y en la spec del backend | Una nota que dice «depende de algo que no existe» es útil mientras no existe. Después es ruido que hace dudar de una fila que ya está bien |
| 2026-09-23 | Versión inicial: inventario de 31 filas `ARQ`, plan de 31 ítems `IMP`, un huérfano justificado y cero huecos | Cerrar la trazabilidad del frontend con el mismo rigor que la del backend, y dejar por escrito las tres dependencias y la única ambigüedad que el recorrido destapó |
| 2026-09-23 | La spec del frontend gana su §12 con **51 requisitos** `REQ-FE-nn`; el inventario `ARQ`/`IMP` de esta matriz no cambia, y quien comprueba la nueva tabla es `BE:P-139` | Los requisitos se derivan del contenido de la spec y se trazan contra el plan desde su propia fila, así que no abren inventario nuevo aquí: esta matriz sigue tratando arquitectura↔plan |
