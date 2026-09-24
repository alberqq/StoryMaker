# Spec — El gate de Investigación con el corpus a la vista

Qué ve y qué puede hacer el Autor en el gate de Investigación, que es el único momento en que alguien revisa el corpus antes de que la novela se construya encima. Deriva de [`docs/architecture.md`](../../docs/architecture.md) §4 (Fase 2), §7 (`mundo_*`) y §10, y de la spec del backend, [`specs/backend/spec.md`](../backend/spec.md) §3.6 y §4.2. **Si algo de este documento contradice a la arquitectura, manda la arquitectura.** La forma técnica exacta vive en [`plan.md`](plan.md).

## 1. Qué problema resuelve

El veredicto del verificador no gobierna ninguna arista del grafo: un hecho sin respaldo baja de firmeza, pero no bloquea. Así que lo único que impide que un corpus flojo llegue a la novela es que el Autor lo mire, y para mirarlo bien necesita tres cosas en el mismo sitio donde decide:

- **Ver cada hecho como lo verá el escritor**: con su firmeza delante y, si el enunciado dice algo que la cita no sostiene, ese añadido señalado.
- **Saber por qué el verificador no respaldó un hecho**, sin tener que abrir la fuente para adivinarlo.
- **Poder actuar sobre cada hecho** —corregirlo o quitarlo— antes de aprobar, que es lo que la arquitectura promete: ante un hecho sin respaldo, «el Autor decide si lo corrige, lo borra a mano o lo deja pasar».

## 2. Qué enseña el gate

**El corpus por dimensión**: las seis dimensiones como pestañas, con su recuento, **y ninguna pestaña más**. Es la misma vista que la salida de la fase, de modo que el Autor no tiene que aprender dos. Lo que hay que revisar no se aparta en otra pestaña: se lee debajo de cada hecho, en su dimensión —lo que no dice la cita, el motivo del verificador—, y el informe del gate lista los no respaldados.

**Mientras el verificador no ha pasado por un hecho**, su etiqueta es **«En proceso de verificación»**, en gris, en lugar de la firmeza: `inferido` sería cierto para el escritor, pero al Autor le haría creer que el hecho ya se juzgó. Hay un caso en que la etiqueta no se va: un hecho de la micro-sesión de Plotting cuyo verificador falló se queda `pendiente` y la conserva. Es raro, el informe de Plotting ya lo cuenta, y se acepta antes que añadir un estado nuevo. **Cada hecho verificado lleva una sola etiqueta: su firmeza**, con un tono por valor: `documentado` en verde, `debatido` en ámbar, `inferido` en gris, `desconocido` en rojo e `inventado` en azul, que no es ni bueno ni malo: es una licencia. El estado que declaró el investigador y el respaldo siguen guardados, pero no salen como insignias: lo que explican se lee en texto, debajo del enunciado.

- **La cita**, entre comillas.
- **Las fuentes**, enlazadas.
- **Lo que dice el verificador**, en un desplegable **cerrado por defecto** y sin color de alarma, rotulado «Nota del verificador». Aparece solo en los hechos no respaldados y en los parciales, y dentro lleva, si lo hay, lo que no dice la cita —«No lo dice la cita: …», mientras el añadido siga en el enunciado; no sustituye a la cita ni a las fuentes: señala el trozo del enunciado que la cita no sostiene— y el motivo del verificador. Los corpus verificados antes de que el motivo se guardara no lo tienen. Si el Autor quita el añadido al corregir, deja de aparecer.

**El informe del gate**, en texto, dice el total, el recuento por dimensión —con las dimensiones vacías marcadas—, **el recuento por firmeza** y, si los hay, los hechos sin respaldo con su cita y su fuente, bajo el rótulo «su firmeza no pasa de inferido». En el modo exhaustivo añade una línea por sesión dirigida.

## 3. Qué puede hacer el Autor

Mientras el corpus no esté sellado, cada hecho lleva dos acciones:

- **Corregir**: edita el enunciado en línea, con un motivo opcional. Es la edición humana general (`POST /novelas/{id}/ediciones`, objeto `hecho`, campo `enunciado`). **No reabre el veredicto**: el respaldo y el añadido guardado se quedan como estaban, porque sobre el corpus decide el Autor y su corrección queda trazada. Si al corregir quita el añadido, este deja de mostrarse porque ya no está en el enunciado.
- **Descartar**: pide confirmación y un motivo opcional, y quita el hecho del corpus.

Las dos se escriben en el acto, se reflejan en la lista sin recargarla y quedan trazadas. Después el Autor aprueba o rehace como en cualquier gate; la sección genérica «Editar antes de decidir» no aparece en este, porque solo tendría los mismos hechos.

**La salida de cualquier fase con su gate pendiente enlaza al gate**, con un aviso y el botón «Decidir en el gate →».

## 4. Contratos

| Método y ruta | Cuerpo | Respuesta | Errores |
|---|---|---|---|
| `GET /api/novelas/{id}/fases/investigacion` | — | Cada `Hecho` lleva `estado`, `respaldo`, `origen`, **`firmeza`**, **`no_lo_dice_la_cita: string \| null`** y `motivo_respaldo: string \| null` | — |
| `POST /api/novelas/{id}/hechos/{hecho_id}/descartar` | `{ "motivo": "" }` | `200` `Hecha` | `422` si el corpus está sellado o la novela no tiene fichero; `404` si el hecho no existe; `409` si algo ya lo usa —`canon_licencia`, `plan_anclaje`, `uso_hecho`— o si hay una ejecución en curso; `403` y `415` como toda la operación |

**`firmeza` y `no_lo_dice_la_cita` los calcula el servidor** con las funciones del Core Domain —`firmeza` y `anadido_vigente`, spec del backend §3.6—, y el frontend los enseña tal cual. El frontend no recalcula nada: si lo hiciera, la regla viviría en dos sitios y podrían discrepar sobre el mismo hecho.

**El motivo del verificador se guarda en `audit_log`**: `actor = 'verificador'`, `accion = 'respaldo'`, `objeto = 'hecho:<id>'`, con `respaldado`, `sin_respaldo` y `motivo`. La salida lo lee de ahí.

**Descartar borra de verdad**: la fila de `mundo_hecho`, sus filas de `mundo_hecho_fuente` y su vector de `vec_hecho`, con el cerrojo tomado. No pasa a ningún estado, porque un hecho que el Autor no quiere no debe llegar al arquitecto de ningún modo. Queda en `edicion_humana` —`tabla = 'mundo_hecho'`, `campo = 'descartado'`, el enunciado como `antes`, `NULL` como `despues`, el motivo— y en `audit_log` con `accion = 'descartar'`.

## 5. Requisitos

| ID | Requisito | Clase | Gate |
|---|---|---|---|
| REQ-GI-01 | El gate de Investigación enseña el corpus con una pestaña por dimensión y ninguna más | T | G1 |
| REQ-GI-02 | Cada hecho de un corpus sin sellar se puede corregir y descartar desde el gate; descartar pide confirmación | T | G1 |
| REQ-GI-03 | Descartar borra el hecho con sus fuentes y su vector, y queda en `edicion_humana` y `audit_log` | T | G1 |
| REQ-GI-04 | Descartar se rechaza con el corpus sellado, con un hecho inexistente o con un hecho que algo ya usa | T | G1 |
| REQ-GI-05 | El motivo de cada veredicto del verificador se guarda y se enseña, en un desplegable cerrado y sin color de alarma, bajo el hecho no respaldado o parcial | T | G1 |
| REQ-GI-06 | La salida de una fase con su gate pendiente enlaza a ese gate | T | G1 |
| REQ-GI-07 | La salida de Investigación sirve cada hecho con su `firmeza` y su `no_lo_dice_la_cita`, calculados en el servidor con las funciones del Core Domain | T | G1 |
| REQ-GI-08 | Cada hecho enseña una sola etiqueta, su firmeza; ni el estado declarado ni el respaldo salen como insignias | T | G1 |
| REQ-GI-09 | El informe del gate cuenta los hechos por firmeza y rotula los no respaldados con «su firmeza no pasa de inferido» | T | G4 |
| REQ-GI-10 | Corregir el enunciado de un hecho en el gate no cambia su respaldo ni el añadido guardado | T | G1 |
| REQ-GI-12 | Un hecho con `respaldo = 'pendiente'` lleva la etiqueta «En proceso de verificación» en lugar de su firmeza | T | G1 |
| REQ-GI-11 | Lo que no dice la cita se enseña, dentro del desplegable del verificador, solo mientras siga en el enunciado | T | G1 |

Todos son **T**: son superficie de lectura y operación, sin nada que se pueda garantizar por construcción. Las reglas que deciden la firmeza y si un añadido sigue vigente no están aquí sino en la spec del backend; este documento solo exige que se sirvan y se enseñen.

## 6. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | §2: lo que el verificador aún no ha mirado se etiqueta **«En proceso de verificación»**. Entra REQ-GI-12 | Petición del Autor: viendo la salida a mitad de la investigación, todo salía `inferido` y parecía que el verificador lo había rechazado |
| 2026-09-24 | §2: lo que dice el verificador —su motivo y lo que no dice la cita— pasa a **un desplegable cerrado, sin rojo**. REQ-GI-05 y REQ-GI-11 se reescriben | Petición del Autor: llamaba demasiado la atención |
| 2026-09-24 | §2: **solo pestañas de dimensión**; se retira «Por revisar». REQ-GI-01 se reescribe | Petición del Autor: la pestaña no se entendía. Lo que juntaba sigue a la vista bajo cada hecho y en el informe del gate |
| 2026-09-24 | Se reescribe el documento entero. **Una sola etiqueta**: la firmeza; el estado declarado y el respaldo dejan de salir como insignias. Entra **«No lo dice la cita»**, el añadido del veredicto parcial; la pestaña «Sin respaldo» pasa a **«Por revisar»** y la salida sirve `no_lo_dice_la_cita`. REQ-GI-01, 05, 07, 08 y 10 se reescriben; entra REQ-GI-11 | Petición del Autor: una sola etiqueta por hecho. Se propaga el veredicto parcial de §4 de la arquitectura |
| 2026-09-24 | Se reescribe el documento entero. **Entra la firmeza**: la salida la sirve por hecho, el gate la enseña como etiqueta principal con el estado declarado solo cuando difiere, y el informe la cuenta. Entran REQ-GI-07 a REQ-GI-10 | Se propaga §7 de la arquitectura: el verificador ya no reescribe el estado, y lo que el Autor tiene que ver es lo mismo que verá el escritor |
| 2026-09-24 | Primera versión: el corpus por dimensión en el gate, con Corregir y Descartar, el motivo del verificador y el enlace de la salida al gate | Petición del Autor: en la Investigación no podía descartar hechos, no encontraba cómo rehacer desde la salida y no sabía por qué el verificador rechazaba un hecho |
