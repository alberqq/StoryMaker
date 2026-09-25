# Matriz de trazabilidad — arquitectura ↔ plan del frontend

Correspondencia ítem a ítem entre [`docs/architecture.md`](../../docs/architecture.md), que es **la fuente de verdad y no se modifica desde aquí**, y [`plan.md`](plan.md), el plan de implementación del frontend.

**Cómo se lee.** Cada fila `ARQ-nn` es una decisión o un componente que la arquitectura fija y que cae del lado del frontend. Se marca `CUBIERTO` **solo si algún ítem `IMP-nn` del plan lo materializa con entregable concreto y un criterio de hecho que compruebe lo que la fila afirma**; «implementar X» no cuenta, y un criterio que comprueba otra cosa tampoco. La columna de notas señala además las coberturas que dependen de algo que todavía no existe. Se marca `GAP` en cualquier otro caso.

**Reglas que esta matriz respeta.** Ninguna fila `ARQ` se elimina ni se fusiona para reducir huecos: el inventario nació con **31 filas** y hoy son **41**; puede crecer cuando la arquitectura decide algo nuevo o cuando un recorrido encuentra una decisión que nadie había listado, nunca menguar. Un hueco se cierra añadiendo o ampliando ítems en el plan, nunca borrando la exigencia. Donde la arquitectura es ambigua o no asigna superficie, queda anotado y **no se inventa requisito**.

**Alcance.** El frontend, en detalle. La vista consolidada de todo el repositorio está en [`trace-matrix.md`](../../trace-matrix.md) de la raíz: allí las filas propias del frontend son `ARQ-117` a `ARQ-136` y `ARQ-139` a `ARQ-141`, y los ítems `FE:IMP-nn` aparecen además en filas compartidas con el backend —`ARQ-74`, `ARQ-93`, `ARQ-102`, `ARQ-105` a `ARQ-107`, `ARQ-109`, `ARQ-111`, `ARQ-112` y `ARQ-137`—.

**Las dos mitades.** La correspondencia del backend vive en [`specs/backend/trace-matrix.md`](../backend/trace-matrix.md) con su propio espacio de identificadores (`A-nn` ↔ `P-nn`), y las dos matrices no se pisan. Cuando un ítem es compartido, la nota nombra su contraparte `P-nn`.

---

## 1. Inventario: arquitectura → plan

| ARQ-ID | Descripción | IMP-IDs | Estado | Nota |
|---|---|---|---|---|
| ARQ-01 | §1, §16.1 · Frontend en **React + Vite** consumiendo la API | IMP-01, IMP-09 | CUBIERTO | — |
| ARQ-02 | §16.1 · **PDF con `page.pdf()` de Playwright sobre la propia ruta de lectura**, sin segunda maquetación | IMP-22, IMP-26, IMP-30 | CUBIERTO | La impresión es una ruta del frontend; quien la conduce es `publication/render.py::imprimir_pdf` (P-94), que es lo que IMP-30 nombra |
| ARQ-03 | §16.1 · Validación visual con **Playwright MCP** | IMP-23, IMP-29 | CUBIERTO | IMP-29 aporta el recorrido que lo usa y nombra `.mcp.json` de la raíz, que es donde §16.3 declara la configuración, donde está el fichero y donde Claude Code la lee |
| ARQ-04 | §16.1, §16.3 · **Steiger** sobre `frontend/src`, que **informa y no bloquea** | IMP-04 | CUBIERTO | — |
| ARQ-05 | §16.3 · Juego mínimo de capas `app/ pages/ shared/`; `widgets/` no se usa y `features/`/`entities/` no se crean de entrada | IMP-02, IMP-03 | CUBIERTO | El criterio de IMP-02 nombra las tres capas ausentes; antes solo prohibía la carpeta vacía, y una `widgets/` llena lo habría pasado |
| ARQ-06 | §16.3 · `pages/reading`: lector, índice de capítulos, navegación, selección de fragmento y petición de cambio | IMP-14, IMP-15, IMP-20 | CUBIERTO | — |
| ARQ-07 | §16.3 · `pages/characters`: fichas de personajes y lugares | IMP-16 | CUBIERTO | El endpoint es `GET /novelas/{id}/versiones/{n}/personajes`, contratado en la spec del backend (P-110) |
| ARQ-08 | §16.3 · `pages/cover`: portada, dedicatoria y nota del autor | IMP-17 | CUBIERTO | El **bloque de paratexto** lo devuelve el endpoint de versión (P-110) |
| ARQ-09 | §16.3 · `pages/versions`: historial, diff de manifiestos y novedades | IMP-18, IMP-25 | CUBIERTO | — |
| ARQ-10 | §16.3 · `shared/api`: cliente de la API y tipos de transporte, **sin reglas de negocio** | IMP-05, IMP-09, IMP-10 | CUBIERTO | «Sin reglas de negocio» lo comprueba el criterio de IMP-09: las funciones devuelven el tipo de transporte tal cual, sin calcular, filtrar ni reordenar |
| ARQ-11 | §16.3 · `shared/ui`: kit de componentes | IMP-11 | CUBIERTO | — |
| ARQ-12 | §16.3 · `shared/lib`: utilidades y hooks | IMP-12 | CUBIERTO | — |
| ARQ-13 | §16.3 · `shared/config`: rutas y variables de entorno | IMP-08 | CUBIERTO | — |
| ARQ-14 | §16.3 · `app/`: providers, router, estilos globales y fuentes | IMP-06, IMP-07 | CUBIERTO | — |
| ARQ-15 | §16.3 · **API pública por segmento** de `shared`, no un `shared/index.ts` único | IMP-02 | CUBIERTO | Criterio de hecho de IMP-02: no existe el índice único |
| ARQ-16 | §16.3 · Las dos reglas de importación: solo de capas estrictamente inferiores, y ningún cruce entre slices de la misma capa | IMP-03, IMP-04, IMP-08 | CUBIERTO | Los constructores de ruta de IMP-08 son lo que evita el cruce entre páginas |
| ARQ-17 | §16.3 · **Assets junto al código que los usa**; estilos globales y fuentes en `app/` | IMP-06 | CUBIERTO | El criterio de IMP-06 prohíbe la carpeta `assets/` de primer nivel; antes solo cubría la mitad de la fila, la de los estilos y las fuentes |
| ARQ-18 | §16.3 · La petición de cambio se ejerce **dentro del lector**, no en una slice propia; extracción a `features/change-request/` solo si un segundo consumidor aparece | IMP-20 | CUBIERTO | La condición de extracción está escrita en §4.2 de la spec y en el criterio de hecho de IMP-20 |
| ARQ-19 | §4 Fase 5 · Lectura web contra el manifiesto: **índice navegable, ficha de personajes y lugares enlazada a sus capítulos, portada con dedicatoria** | IMP-14, IMP-16, IMP-17, IMP-24 | CUBIERTO | Son los tres objetos que `render_visual` mira |
| ARQ-20 | §4 Fase 5, §11a · **`render_visual` corre dentro de `PublishVersion`, sobre la versión candidata y antes del `commit`** | IMP-23, IMP-27 | CUBIERTO | El nodo es del backend (P-92); del frontend dependen las anclas y ser interceptable |
| ARQ-21 | §4 Fase 5 · El PDF se maqueta **después** del render, imprimiendo esa misma ruta | IMP-22, IMP-30, IMP-53 | CUBIERTO | IMP-53 es la maqueta de libro que imprime `P-185` |
| ARQ-22 | §4 Fase 6 · El lector pide el cambio **desde la propia página** | IMP-20, IMP-21 | CUBIERTO | — |
| ARQ-49 | §4 Fase 6 · Los candidatos se muestran y **el Autor confirma en el gate** cuál es la fila | IMP-54 | CUBIERTO | Contrapartes `P-186` (los campos del candidato) y `P-95` (la elección aplicada) |
| ARQ-23 | §4 Fase 6 · El diff de dos manifiestos produce **página de novedades en el PDF y distintivo en el índice web** | IMP-14, IMP-25 | CUBIERTO | — |
| ARQ-24 | §4 Fase 6, §7 · **La versión anterior sobrevive entera** y se puede seguir leyendo | IMP-18 | CUBIERTO | — |
| ARQ-25 | §16.4 · La API sirve la lectura y la petición de cambio **sin autenticación** (U-17) | IMP-08, IMP-09 | CUBIERTO | IMP-09 no envía credenciales ni las guarda, e IMP-08 garantiza que ninguna de las dos variables es un secreto. Riesgo aceptado con fila en `verification.md` §5 |
| ARQ-26 | §16.4 · **El directorio `proyectos/` es el registro**: listar novelas es listar el directorio | IMP-39 | CUBIERTO | — |
| ARQ-27 | §16.4 · Una invocación por novela: **quien llega segundo es rechazado, no encolado** | IMP-21 | CUBIERTO | Del lado del frontend significa no encolar ni reintentar solo ante un `409` |
| ARQ-28 | §19 · Idioma **castellano**, términos técnicos en inglés | IMP-31 | CUBIERTO | — |
| ARQ-29 | §19 · **MCP de navegador: Playwright** | IMP-29 | CUBIERTO | — |
| ARQ-30 | §4 Fase 1 · La **Nota del autor** como paratexto que declara licencias y personajes históricos | IMP-17 | CUBIERTO | §16.3 le asigna superficie: `pages/cover/` |
| ARQ-31 | §7 · Una versión **es** su manifiesto: un capítulo solo existe dentro de una versión | IMP-07, IMP-15 | CUBIERTO | De aquí sale que toda ruta de lectura lleve el número de versión |
| ARQ-32 | §16.3 · `pages/library`, declarada como pantalla propia: si listar las novelas es listar `proyectos/`, alguien tiene que enseñar esa lista | IMP-39 | CUBIERTO | Nace de §16.4, que hace del directorio el registro |
| ARQ-33 | §16.3 · `pages/print`, la novela entera en un documento: la misma decisión que evita una segunda maquetación obliga a una segunda ruta | IMP-22, IMP-23, IMP-24, IMP-25 | CUBIERTO | Es la única pantalla que no está hecha para un humano: la abren Playwright y `render_visual` |
| ARQ-34 | §16.3 · **Cliente único**: ningún módulo fuera de `shared/api` emite una petición de red, y aquí es **condición de G5** y no higiene | IMP-09, IMP-27 | CUBIERTO | El criterio de hecho de IMP-09 es una prueba que falla si aparece red fuera de `shared/api` |
| ARQ-35 | §16.4 · **FastAPI sirve el frontend construido**, con un solo origen y la URL base en la configuración | IMP-26 | CUBIERTO | Contraparte `P-136`. IMP-26 nombra ya sus mismos símbolos —`montar_frontend`, `Settings.frontend_dist` y `Settings.frontend_base_url`, la URL base que la fila exige—. Ninguno existe todavía en el código, y no hace falta hasta que haya `dist/` que servir |
| ARQ-36 | §4 Fase 5 · El navegador ve la versión candidata porque `publication.publish` **le sirve las peticiones interceptadas** desde el manifiesto que vive en la transacción abierta | IMP-27 | CUBIERTO | El nodo es `P-92`; del frontend depende solo ser interceptable, que es lo que ARQ-34 garantiza |
| ARQ-37 | §2, §15, §16.4 · **De una novela no vive nada en dos sitios**, y los datos del homenajeado no salen de su fichero: el frontend no guarda copia local —ni almacenamiento del navegador, ni caché persistente, ni *service worker*— y no pide nada a terceros | IMP-32, IMP-56, IMP-57, IMP-06 | CUBIERTO | IMP-32 es nuevo: el criterio de IMP-09 solo miraba la red y nada impedía un `localStorage`. IMP-06 cubre las peticiones a terceros al servir las fuentes desde el propio origen |
| ARQ-38 | §16.1 · El PDF **conserva los enlaces internos** que necesitan el índice navegable y la página de novedades | IMP-24, IMP-25, IMP-30 | CUBIERTO | La fila faltaba; el plan ya lo realizaba en IMP-24 y lo comprueba en IMP-30 (enlaces que saltan en el PDF impreso) |
| ARQ-39 | §16.3 · **Una API pública por slice**: cada slice de `pages/` expone su `index.ts` y nadie importa su interior | IMP-02 | CUBIERTO | IMP-02 declaraba el `index.ts` de `library/` y de ninguna otra página; ahora nombra las seis y su criterio prohíbe importar el interior de una slice |
| ARQ-40 | §1, §11e · **La spec enumera sus requisitos `REQ-FE-nn`** derivados de su propio contenido, y `requisitos_declarados` los coteja contra este plan | IMP-33 | CUBIERTO | Contraparte `P-139`, que ya declara la lectura de §12 de la spec del frontend. El enunciado de los requisitos vive en la spec; el ítem solo los comprueba |
| ARQ-41 | §1, §11e · **La correspondencia documento↔código se comprueba en G1**: `inventario_del_plan` coteja la columna «Ficheros y símbolos» de este plan contra el árbol, en las dos direcciones y en dos cubos | IMP-33 | CUBIERTO | Contraparte `P-129`, que lee ya las filas `IMP-nn` y recorre `frontend/src/**` en la dirección inversa. Hoy informa de 47 rutas declaradas y ausentes, todas de este plan, porque `frontend/` todavía no existe. Es también lo que sustituye a `anclas_de_procedencia`, que §11e acota al backend: la pantalla especificada y sin escribir cae en ese cubo |
| ARQ-42 | §16.5 · **La interfaz opera la novela entera**: encargar, lanzar, seguir fase a fase, consultar la salida de cada fase, decidir los gates y continuar | IMP-39, IMP-40, IMP-41, IMP-42, IMP-43, IMP-44, IMP-47, IMP-48, IMP-50, IMP-51, IMP-52 | CUBIERTO | Contraparte `P-160` a `P-162`, y `P-180` y `P-181` para el encargo por conversación |
| ARQ-43 | §16.5 · **Lo que ejecuta el grafo lo lanza la API como CLI aparte**; la interfaz pide y sigue, y dice «lanzado» sin esperar al proceso | IMP-35, IMP-41 | CUBIERTO | El lanzador es `P-162` |
| ARQ-44 | §16.5 · **Seguimiento sondeando el fichero**, con la actividad interpretada y el registro del proceso solo consultable | IMP-36, IMP-41 | CUBIERTO | El estado lo calcula `P-160` |
| ARQ-45 | §16.5 · **El taller es un tablero por fases tipo Jira**: arrastrar a la columna siguiente aprueba y a la suya rehace, siempre tras confirmar con el informe, y solo con gate pendiente | IMP-39, IMP-55 | CUBIERTO | — |
| ARQ-46 | §16.5, §10 · En la interfaz **editar es corregir filas antes de decidir**, y **abortar solo cabe en Intake** | IMP-42, IMP-54 | CUBIERTO | Contrapartes `P-162` (ediciones) y `P-165` (abortar) |
| ARQ-47 | §16.3 · **`entities/novela`**: estado y línea de fases, compartidos por taller, panel y gate | IMP-34 | CUBIERTO | — |
| ARQ-48 | §16.5 · **Un cerrojo cuyo proceso no vive es una novela detenida**, y se ofrece desbloquear y continuar | IMP-41 | CUBIERTO | Contraparte `P-163` |

---

## 2. Huérfanos del plan

Ítems del plan que no aparecen en la columna `IMP-IDs` de ninguna fila del inventario.

| IMP-ID | Descripción | Resolución |
|---|---|---|
| IMP-37 | Kit ampliado de `shared/ui` | JUSTIFICADO · Soporte de las pantallas de ARQ-42; nace de spec §8 y §9, no de una decisión propia de la arquitectura |
| IMP-38 | Tokens de diseño y los dos registros visuales | JUSTIFICADO · Nace de spec §8, el acabado que el Autor pidió; la arquitectura no fija estilo |
| IMP-45 | La lectura en el registro de libro | JUSTIFICADO · Restyling de pantallas cuyos contratos ya cubren ARQ-06 a ARQ-09 |
| IMP-46 | Pruebas de las pantallas de operación | JUSTIFICADO · Tarea transversal de verificación, como IMP-28 |
| IMP-49 | Pruebas del encargo por conversación | JUSTIFICADO · Tarea transversal de verificación, como IMP-28 |
| IMP-28 | Pruebas de componente e integración con MSW sobre los contratos de `shared/api`, incluidos los siete casos de error de §9 de la spec | JUSTIFICADO · Tarea transversal de verificación, no una decisión de la arquitectura: nace de `verification.md` §3.5 y se cubre en G1 |

No hay ningún otro ítem sin ancla: los treinta y dos restantes, de `IMP-01` a `IMP-33`, están enlazados a al menos una fila `ARQ`, comprobado sobre el fichero y no a ojo. Todo ítem del plan cita además en su columna «Arq.» un apartado de la arquitectura, salvo IMP-28, que cita el de `verification.md` por la razón de su resolución.

---

## 3. Hallazgos del recorrido

**Lo que las dos primeras pasadas encontraron está cerrado arriba**, en la arquitectura y en la spec del backend: `pages/library` y `pages/print` figuran en el árbol de §16.3; el bloque de paratexto, la ficha versionada y la interceptación del manifiesto candidato están contratados; la Nota del autor tiene superficie en `pages/cover/`; y el cliente único, FastAPI sirviendo el `dist/` y la interceptación tienen fila.

**La tercera pasada leyó la arquitectura entera y no solo §4 y §16**, y encontró quince vacíos de cuatro clases:

1. **Cinco decisiones sin fila o sin ítem.** Que de una novela no viva nada en dos sitios (`ARQ-37`), que el PDF conserve los enlaces internos (`ARQ-38`), la API pública por slice (`ARQ-39`), los requisitos `REQ-FE-nn` (`ARQ-40`) y la comprobación en CI de este plan contra el árbol (`ARQ-41`). La segunda ya estaba realizada en el plan y solo le faltaba la fila; las otras cuatro necesitaron ítem nuevo o ampliado: IMP-32, IMP-33 e IMP-02.
2. **Cuatro filas en `CUBIERTO` con un criterio que no comprobaba lo que afirmaban**: `ARQ-05`, `ARQ-10`, `ARQ-17` y `ARQ-25`. Es el vacío que menos se ve, porque la fila está en verde y el ítem existe; lo que falta es que el criterio de hecho mire la cosa. Se amplían los criterios de IMP-02, IMP-06, IMP-08 e IMP-09.
3. **Cuatro ítems mal anclados o desalineados con su contraparte.** IMP-10 no citaba ningún apartado de la arquitectura, IMP-23 escribía sus cuatro anclas separadas por barras sin escapar que partían su fila de la tabla y desplazaban su columna «Arq.», IMP-26 nombraba `Settings.frontend_base_url` donde `P-136` nombra `Settings.frontend_dist`, e IMP-30 nombraba un `publication/pdf.py` que no existe, mientras `P-94` y el árbol tienen `render.py::imprimir_pdf`.
4. **Una nota que contradecía al plan** (`ARQ-03` decía `.mcp.json` e IMP-29 decía `.claude/mcp.json`) y **el desfase de la vista consolidada**, que se corrige en la misma operación en la matriz de la raíz.

**Las tres cosas que esta pasada elevó al Autor están resueltas**, y cada una bajó desde donde se decide:

- **La configuración MCP vive en `.mcp.json` de la raíz.** §16.3 de la arquitectura la declaraba en `.claude/mcp.json`, un sitio del que Claude Code no lee; el árbol y la arquitectura ya dicen lo mismo, e IMP-29 los sigue.
- **`P-129` lee este plan.** §7.1 nº 21 de la spec del backend y `P-129` declaran las filas `IMP-nn` y el recorrido inverso de `frontend/src/**`, y la prueba lo hace: el cambio está anotado como It-16 en `docs/iteraciones.md`.
- **`P-136` nombra la URL base**, igual que REQ-BE-113 y que la tabla de configuración de la spec del backend.

**La ambigüedad que quedaba anotada está decidida arriba.** `anclas_de_procedencia` (§11e) se enunciaba sobre docstrings y sobre «§3 y §4 de la spec» sin decir de qué mitad. La arquitectura fija ahora que **alcanza solo al backend**, y que el frontend se traza por `inventario_del_plan` y `requisitos_declarados`; la spec lo declara fuera en su §13. No entra `ARQ-42`: la decisión deja algo fuera y no pide nada que implementar, y la parte que sí cae de este lado —que la comprobación del plan contra el árbol sustituya a las anclas— la lleva ya la nota de `ARQ-41`.

---

## 4. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | `ARQ-41` dice «en G1» en lugar de «en CI» | Se mueve con §1 de la arquitectura. Decisión del Autor: se retiran los workflows de GitHub Actions y G1 y G2 pasan a lanzarse a mano (arq. §17, verif. §4.7) |
| 2026-09-24 | Donde está `IMP-56` entra también `IMP-57`: los temas de la aplicación y del libro, que también se guardan como preferencia | Se mueve con la spec del frontend, §4.6 y §8 |
| 2026-09-24 | `ARQ-37` suma `IMP-56`: las preferencias de lectura, lo único que el navegador guarda | Se mueve con la spec del frontend, §1 y §4.6 |
| 2026-09-24 | `ARQ-45` suma IMP-55: las publicadas en un listado bajo el tablero | Arq. §16.5 saca las publicadas del tablero |
| 2026-09-24 | Entra `ARQ-49`, con IMP-54, y `ARQ-46` suma IMP-54 | El candidato de Regeneración se elige en su gate |
| 2026-09-24 | `ARQ-21` suma IMP-53 | La maqueta de libro de la impresión |
| 2026-09-24 | `ARQ-42` suma IMP-52 | Descargar el PDF |
| 2026-09-24 | `ARQ-42` suma IMP-51 | Los lugares con nombre corto |
| 2026-09-24 | `ARQ-42` suma IMP-50 | La casilla de investigación exhaustiva |
| 2026-09-24 | `ARQ-42` suma IMP-47 e IMP-48; IMP-49 se justifica como huérfano de verificación | El encargo por conversación |
| 2026-09-24 | Entran **ARQ-42 a ARQ-48**, las decisiones de arq. §16.5 y la nueva capa `entities/`, cubiertas por IMP-34 a IMP-44; IMP-37, IMP-38, IMP-45 e IMP-46 se justifican como huérfanos. ARQ-26 y ARQ-32 pasan de IMP-13 a IMP-39, y ARQ-31 deja de citar IMP-19, los dos retirados | La matriz se mueve con el documento que cambia, en la misma operación |
| 2026-09-24 | §3 deja de anotar como ambigua la extensión de `anclas_de_procedencia` y registra la decisión; la nota de `ARQ-41` dice que el inventario del plan es lo que la sustituye en el frontend | §11e de la arquitectura acota esa prueba al backend. Una pregunta que sigue abierta en la matriz después de decidida hace que el recorrido la vuelva a contar |
| 2026-09-24 | Se cierran los tres hallazgos que la tercera pasada elevó al Autor: la arquitectura declara `.mcp.json` en la raíz, `P-129` lee las filas `IMP-nn` y `P-136` nombra la URL base. `ARQ-03`, `ARQ-35` y `ARQ-41` dejan de señalar discrepancias | Lo que estaba abierto se decidió arriba y bajó hasta el código. Una nota que sigue anunciando una discrepancia cerrada hace dudar de una fila que ya está bien |
| 2026-09-24 | Tercera pasada, sobre la arquitectura entera: entran `ARQ-37` a `ARQ-41`; `ARQ-05`, `ARQ-10`, `ARQ-17` y `ARQ-25` pasan a apoyarse en criterios de hecho que comprueban lo que afirman; `ARQ-02`, `ARQ-03` y `ARQ-35` corrigen sus notas; el plan gana IMP-32 e IMP-33 y amplía seis ítems. El inventario sube de 36 a 41 filas y el plan de 31 a 33 ítems. **Quince vacíos encontrados, quince cerrados**, y tres discrepancias elevadas al Autor | Las dos pasadas anteriores recorrieron §4 y §16, que es donde el frontend se nombra, y dejaron fuera lo que lo gobierna sin nombrarlo: §2, §15 y §11e. Y una fila en verde con un criterio que mira otra cosa es un hueco con mejor aspecto |
| 2026-09-23 | Entran `ARQ-32` a `ARQ-36`, las cinco decisiones que la arquitectura fijó hoy sobre el frontend: las dos pantallas declaradas, el cliente único como condición de G5, FastAPI sirviendo el `dist/` y la interceptación de la versión candidata | El recorrido inverso las encontró como ítems de plan sin requisito detrás. Un ítem sin requisito es trabajo que nadie acordó, aunque en este caso el acuerdo existía y lo que faltaba era la fila |
| 2026-09-23 | Cerrados los tres hallazgos y las notas de dependencia de `ARQ-07`, `ARQ-08`, `ARQ-20` y `ARQ-30`: lo que faltaba se decidió en la arquitectura y en la spec del backend | Una nota que dice «depende de algo que no existe» es útil mientras no existe. Después es ruido que hace dudar de una fila que ya está bien |
| 2026-09-23 | Versión inicial: inventario de 31 filas `ARQ`, plan de 31 ítems `IMP`, un huérfano justificado y cero huecos | Cerrar la trazabilidad del frontend con el mismo rigor que la del backend, y dejar por escrito las tres dependencias y la única ambigüedad que el recorrido destapó |
| 2026-09-23 | La spec del frontend gana su §12 con **51 requisitos** `REQ-FE-nn`; el inventario `ARQ`/`IMP` de esta matriz no cambia, y quien comprueba la nueva tabla es `BE:P-139` | Los requisitos se derivan del contenido de la spec y se trazan contra el plan desde su propia fila, así que no abren inventario nuevo aquí: esta matriz sigue tratando arquitectura↔plan |
