# Lo que queda — el repositorio contra la arquitectura

Recorrido completo del árbol frente a [`docs/architecture.md`](docs/architecture.md), que es la fuente de verdad, y frente a los dos planes que la realizan, [`specs/backend/plan.md`](specs/backend/plan.md) y [`specs/frontend/plan.md`](specs/frontend/plan.md).

Este documento **no decide nada y no sustituye a ninguno de los anteriores**: anota diferencias. Donde dice que algo falta, falta en el árbol; donde dice que hay deriva, el documento y el código nombran cosas distintas. La matriz de trazabilidad de la raíz comprueba que cada decisión de la arquitectura tenga **ítem de plan**; esto comprueba algo distinto y complementario: que cada ítem de plan tenga **código**.

**Cómo se ha hecho.** Se han extraído las rutas y los símbolos de la columna «Ficheros y símbolos» de los dos planes y se han cotejado contra el árbol real, en las dos direcciones; se ha ejecutado la suite —503 pruebas pasan y una se salta—; se ha resuelto la tabla de nodos de `commons/graph/nodos.py` para ver cuáles siguen siendo el sustituto ruidoso de `NodoSinImplementar`; y se han leído las seis carpetas de fase y las tres de punto de entrada.

---

## 1. El estado en una tabla

| Hito | Qué deja en pie | Estado |
|---|---|---|
| **BE·H0** | Andamiaje, configuración, puertas estáticas, inventario y anclas | **Cerrado** |
| **BE·H1** | Persistencia: nueve ficheros de esquema, inmutabilidad, repositorios, transacción | **Cerrado**, con una deriva de forma (§4, D-1) |
| **BE·H2** | Núcleo transversal: embeddings, agentes, ensamblador, Core Domain, Lean, observabilidad | **Casi cerrado**: faltan el reembedding y la exportación OTLP |
| **BE·H3** | Grafo, estado, invocación, cerrojo, TLA+ y la prueba de identidad | **Cerrado** |
| **BE·H4** | Fases 1 a 3: del brief al corpus sellado | **Casi cerrado**: faltan las dos suites adversarias |
| **BE·H5** | Fase 4: el bucle de capítulo completo | **Cerrado** |
| **BE·H6** | Fases 5 y 6: publicar y regenerar | **Sin empezar**: `publication/` y `regeneration/` contienen solo su `__init__.py` |
| **BE·H7** | Puntos de entrada, gates humanos y cierre de verificación | **Sin empezar**: `gates/`, `api/` y `cli/` contienen solo su `__init__.py` |
| **FE·H0–H5** | El frontend entero | **Sin empezar**: `frontend/` es un directorio vacío |

De los **136 ítems** del plan del backend, **45** siguen sin código. De los **31** del frontend, los **31**.

Lo que esto significa en el grafo: de los veinticuatro nodos de `NODOS`, **nueve** se resuelven todavía al sustituto que revienta si alguien lo pisa — los cuatro `AwaitApproval`, `Judge`, `PublishVersion`, `RequestChange`, `Invalidate` y `RegenerateAffected`. Una novela hoy no llega ni al final de Intake, porque el nodo que le sigue es un gate y el gate es justamente uno de los que faltan.

---

## 2. Lo que falta, por bloques

### 2.1 Las dos fases sin código — `publication/` y `regeneration/`

Es el bloque que más pesa, porque de él cuelga la única puerta que la arquitectura declara sin excepción junto a G3: **G5**.

| Ítem | Qué falta | Fichero declarado |
|---|---|---|
| P-90 | Nodo `publication.judge` y la rúbrica de siete criterios | `publication/nodos.py::judge`, `publication/rubrica.yaml` |
| P-91 | Lean sobre la cronología completa antes de publicar | `publication/verificacion.py` |
| P-92 | Nodo `publication.publish`, con la interceptación que sirve al navegador el manifiesto candidato | `publication/nodos.py::publish`, `publication/candidata.py` |
| P-93 | El `manifiesto` con sus seis campos, incluido `embeddings_json` | `publication/manifiesto.py` |
| P-94 | Render de la lectura y PDF con `page.pdf()` desde esa misma ruta | `publication/render.py` |
| P-95 | Nodo `regeneration.request`, con resolución semántica de la petición | `regeneration/nodos.py::request` |
| P-96 | Modificar la fila del hecho, nunca el texto, con su fila en `audit_log` | `regeneration/cambio.py` |
| P-97 | Nodo `regeneration.invalidate` y la revalidación de coste cero | `regeneration/nodos.py::invalidate` |
| P-98 | Nodo `regeneration.regenerate` y el manifiesto que reutiliza lo no tocado | `regeneration/nodos.py::regenerate` |
| P-99 | Diff por `JOIN` de dos manifiestos | `regeneration/diff.py` |
| P-100 | Gate de Regeneration con el recuento de afectados antes de pagarlos | `regeneration/gate.py` |
| P-101 | Edición humana directa como entrada de primera clase, con re-sello y reembedding | `regeneration/edicion_humana.py` |

Hay una consecuencia que conviene ver: `commons/validation/registro.py` ya declara `render_visual` apuntando a `storymaker.publication.render:render_visual`, de modo que el undécimo validador del registro está **cableado a una ruta que todavía no existe**. El registro es correcto —declara rutas como cadena precisamente para esto— pero la pasada de `PublishVersion` no tiene hoy nada que componer.

Lo único de H6 que sí está es **P-102**, la ramificación: `commons/graph/branch.py` copia el fichero y escribe `procedencia`.

### 2.2 Los puntos de entrada — `gates/`, `api/` y `cli/`

Sin este bloque el sistema no tiene forma de ser usado por nadie: no hay comando que cree una novela ni endpoint que reanude un gate.

| Ítem | Qué falta | Fichero declarado |
|---|---|---|
| P-103 | Nodo `gates.await`: `interrupt()`, fila `gate` pendiente y fin de la invocación | `gates/nodos.py::await_approval` |
| P-104 | Las cuatro decisiones: aprobar, rehacer con comentario, editar, abortar | `gates/decisiones.py` |
| P-105 | Interfaz `Notifier` y Telegram con botones inline | `gates/notifier.py`, `gates/telegram.py` |
| P-106 | Notificaciones informativas desactivadas por defecto | `gates/notifier.py::informativa` |
| P-107 | *Timeout* que aparca, nunca auto-aprobación | `gates/timeout.py` |
| P-108 | `gates_enabled = false` para el modo batch, registrado en el manifiesto | `gates/nodos.py`, `publication/manifiesto.py` |
| P-109 | `POST /webhook/telegram`, con secreto, respuesta inmediata, tarea de fondo e idempotencia | `api/webhook.py` |
| P-110 | Los cinco endpoints de lectura y `POST /novelas/{id}/cambios` | `api/lectura.py`, `api/cambios.py` |
| P-111 | `GET /novelas` listando el directorio `proyectos/` | `api/novelas.py` |
| P-112 | Contrato OpenAPI y Schemathesis sobre el endpoint de decisión | `tests/api/test_schemathesis.py` |
| P-113 | Los siete comandos de Typer | `cli/comandos.py` |
| P-136 | FastAPI sirviendo el `dist/` del frontend, con su URL base en `Settings` | `api/estaticos.py`, `commons/config.py` |
| P-128 | **Parcial**: `commons/errores.py` existe; falta su traducción única a código HTTP y a mensaje de CLI | `api/manejadores.py`, `cli/salida.py` |

El directorio `proyectos/` existe y está vacío, que es su estado correcto: no hay base de datos global de novelas y el registro es el propio directorio.

### 2.3 El frontend entero

`frontend/` existe como carpeta vacía. **Los treinta y un ítems `IMP-01` a `IMP-31` están por escribir**, empezando por el andamiaje de Vite y el árbol FSD con el juego mínimo `app/ pages/ shared/`.

Dos de ellos son la frontera con el backend y valen más que los demás, porque de ellos cuelga G5:

- **IMP-26 / P-136** — FastAPI monta el `dist/` construido, de modo que la lectura, el PDF y `render_visual` comparten origen. Mientras no exista, `render_visual` no tiene URL que abrir y el PDF tampoco.
- **IMP-27 / P-92** — el contrato de cliente único: ningún módulo fuera de `shared/api` emite una petición de red. Es lo que permite interceptar las peticiones y servirle al navegador el manifiesto candidato que vive en la transacción abierta.

Falta también el trabajo de CI `frontend-estructura` que publica la salida de **Steiger** informando sin bloquear (IMP-04): hoy `.github/workflows/ci.yml` tiene cuatro trabajos y ninguno mira el frontend.

### 2.4 Piezas sueltas de `commons/`

| Ítem | Qué falta |
|---|---|
| P-26 | `commons/embeddings/reembedding.py::reindexar_edicion` — el reembedding que dispara `edicion_humana`. Sin él, la búsqueda semántica sigue devolviendo el texto anterior a una corrección del Autor, que es lo contrario de lo que promete §10 |
| P-53 | `commons/obs/otlp.py` — la exportación OTLP nativa, opcional y activable por variable de entorno |
| P-66 | `intake/extractor.py` — la cuarentena está entera en `intake/cuarentena.py`, pero el extractor de intake no tiene módulo propio |

### 2.5 El cierre de verificación

Es el bloque donde el repositorio está más lejos de lo que `verification.md` promete, y conviene leerlo con el criterio de producto delante: son puertas de evidencia, no de funcionamiento.

| Ítem | Qué falta |
|---|---|
| P-115 | `tests/propiedades/` existe **vacío**: ninguna propiedad de Hypothesis refleja todavía los invariantes de TLA+ sobre el código real |
| P-116 | Hay **dos** pruebas de contrato de las seis declaradas: `test_identidad_nodos.py` y `test_nodo_vs_hook.py` |
| P-117 | Hay **una** prueba de integración, `test_invocacion.py`. Faltan la atomicidad del checkpoint, la reanudación, la Fase 6, la ramificación y los reintentos agotados — y tres de ellas no se pueden escribir hasta que exista H6 |
| P-118 | `tests/adversarias/` existe **vacío**: ni inyección por texto pegado (P-67), ni exfiltración de PII (P-74), ni página hostil, herramienta prohibida o evasión del guardrail |
| P-119 | No hay *workflow* nocturno: ni CrossHair sobre las cinco funciones puras ni `mutmut` con mutación ≥ 80 % en `commons/validation/` |
| P-120 | Los cinco briefs están escritos, pero falta `evals/correr.py` que los ejecute en batch |
| P-121 | `evals/varianza_juez.py` — la medición de la varianza del juez, que es lo que convierte «Haiku basta» en un resultado en vez de una suposición |
| P-122 | `publication/rubrica.yaml` y `docs/revision-humana.md`: sin el fichero de rúbrica compartido, el juicio humano y el del modelo no son comparables |
| P-123 | `tests/traza/test_g6.py` — las aserciones sobre la traza real contra la API de Langfuse |
| P-124 | `ejemplos/novela-ejemplo.pdf` con su manifiesto. Hoy `ejemplos/` solo contiene `brief-ejemplo.yaml` |
| P-134 | `tests/propiedades/test_sesiones_en_serie.py` — la serialidad de las micro-sesiones del arquitecto, que es lo que sostiene el peor caso de 45.000 tokens de §12 |
| P-135 | `docs/actas/` y `specs/*/acta-grilling.md` — el acta de grilling y de revisión por documento, que es la mitigación de §18 que no es código sino inspección |

---

## 3. Lo que sí está en pie

Conviene decirlo, porque el listado de arriba se lee como si no hubiera nada:

- **La persistencia entera**: los nueve ficheros de esquema, `STRICT` y `CHECK` en todas las tablas, los *triggers* de inmutabilidad, los seis repositorios y el envoltorio transaccional que mete checkpoint y dominio en el mismo `BEGIN IMMEDIATE`.
- **El grafo completo y comprobado**: los veinticuatro nodos cableados por ruta, las aristas condicionales leyendo booleanos de Python, el cerrojo de fichero, la especificación directa en TLA+ con `Aristas` gobernando el `Next`, TLC en CI y la prueba de identidad que compara nombres **y** aristas.
- **El núcleo transversal**: la única puerta al Agent SDK con sus techos por rol, los dos *hooks* que cuentan invocaciones y truncan salidas, el ensamblador de los siete bloques con su truncado por prioridad, los embeddings con `sqlite-vec` y el generador de Lean con su *runner*.
- **El Core Domain con sus once validadores registrados**, expuesto a la vez como nodo y como *hook* de Claude Code, con la prueba de contrato que exige el mismo veredicto por los dos caminos.
- **Las fases 1 a 4**: intake con su cuarentena y sus contradicciones, investigation con su sesión de tres búsquedas y su verificador por lotes, plotting con el canon, la escaleta, los huecos y el sello, y el bucle de Writing entero con sus dos pasadas.
- **Las cuatro pruebas de correspondencia de §11e**, que son las que han permitido escribir este documento sin leer nada a mano.

---

## 4. Derivas entre documento y código

No son ausencias sino desacuerdos: el documento nombra una cosa y el árbol tiene otra. Cada una se cierra **cambiando el documento**, que es donde la arquitectura dice que se cambian las cosas, salvo que el Autor decida lo contrario.

| # | Deriva | Dónde |
|---|---|---|
| D-1 | P-18 declara `commons/db/migraciones/` como carpeta y un símbolo `migrar`. La implementación aplica los ficheros de `esquema/` desde `_migrar`, privado, con `VERSION_ESQUEMA` y negativa a abrir un esquema del futuro. La capacidad está; la forma declarada, no |`specs/backend/plan.md` P-18 |
| D-2 | P-29 declara `commons/agents/hooks.py::cuota_herramientas`; el código tiene la clase `CuotaDeHerramientas` | `specs/backend/plan.md` P-29 |
| D-3 | P-76 declara `plotting/canon.py::volcar_diales`; los diales se vuelcan dentro de `volcar_canon` | `specs/backend/plan.md` P-76 |
| D-4 | P-136 declara `Settings.frontend_dist` e IMP-26 declara `Settings.frontend_base_url`: **dos nombres para el mismo ajuste**, y ninguno existe todavía. Hay que elegir uno antes de escribirlo | ambos planes |
| D-5 | P-120 declara `evals/briefs/*.json`; los cinco briefs están en **`.yaml`**, igual que `ejemplos/brief-ejemplo.yaml`. La CLI, además, contrata `storymaker nueva <brief.json>` en §6 de la spec | `specs/backend/plan.md` P-120, `specs/backend/spec.md` §6 |
| D-6 | La arquitectura declara `.claude/agents/` con las definiciones de los nueve roles en el árbol de §16.3; el directorio no existe. Convive con §14, que pone los prompts de rol en Langfuse como fuente de verdad: **o el árbol se corrige, o se explica qué queda en `agents/` cuando el prompt vive fuera** | `docs/architecture.md` §16.3 |
| D-7 | La arquitectura y IMP-29 declaran `.claude/mcp.json`; el fichero está en la raíz como `.mcp.json` | `docs/architecture.md` §16.3, `specs/frontend/plan.md` IMP-29 |
| D-8 | `inventario_del_plan` recorre `specs/*/plan.md` pero solo lee las filas cuyo identificador empieza por `P-`, así que el plan del frontend entero queda fuera del cotejo. Es informativo y no bloquea, pero hoy calla sobre algo que no ha mirado | `backend/tests/correspondencia/test_inventario.py` |
| D-9 | `docs/requirements-audit.md` está **desactualizado**: afirma que `commons/validation/`, `commons/context/` y las seis carpetas de fase están vacías, y eso dejó de ser cierto con H2, H4 y H5. Una auditoría que describe un árbol anterior es peor que no tenerla | `docs/requirements-audit.md` |
| D-10 | La CI no tiene el trabajo de `lake build` del *fixture* que G1 exige en `verification.md` §6, ni el de Steiger (IMP-04), ni ninguna ejecución nocturna para G2 (P-119) | `.github/workflows/ci.yml` |

---

## 5. Orden sugerido

No es una decisión, es la lectura de las dependencias que los propios planes declaran.

1. **`gates/` (P-103 a P-108).** Es lo que más desatasca por lo poco que cuesta: hoy una novela se detiene en el primer `AwaitApproval` porque ese nodo no existe, de modo que ninguna de las cuatro fases ya escritas puede recorrerse de principio a fin. Con los gates —aunque sea con `gates_enabled = false` y sin Telegram— el camino de Intake a Writing se puede correr entero.
2. **`cli/` (P-113, P-128).** El segundo punto de entrada es el que usa el Autor y el que corre las evaluaciones; sin él no hay forma de crear una novela que no sea una prueba.
3. **`publication/` (P-90 a P-94).** Cierra G5 por el lado del backend y da la primera versión publicada, que es lo que el frontend necesita tener delante.
4. **El frontend (IMP-01 a IMP-19).** Andamiaje, `shared/` y las seis pantallas leyendo de la API.
5. **`api/` (P-109 a P-112, P-136) e IMP-20 a IMP-27.** Los endpoints y el modo impresión, que es donde las dos mitades se tocan.
6. **`regeneration/` (P-95 a P-101).** La Fase 6 es la prueba de fuego del resto, y conviene abordarla cuando el resto ya se sostiene.
7. **El cierre de verificación (P-114 a P-124, P-134, P-135) e IMP-28 a IMP-31.** Las suites que hoy están vacías y la evidencia final.

Las derivas de §4 no tienen sitio en esta lista porque no dependen de nada: se cierran cuando el Autor decida, y cada una cuesta un párrafo.

---

## 6. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-23 | Versión inicial: recorrido del árbol completo contra la arquitectura y los dos planes, con el reparto por bloques, las diez derivas documento↔código y el orden sugerido | El Autor pidió saber qué queda para tener el repositorio completo. La matriz de trazabilidad comprueba que toda decisión tenga ítem de plan; faltaba la comprobación complementaria, que todo ítem de plan tenga código |
