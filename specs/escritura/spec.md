# Spec — La Escritura que no se atasca

Qué pasa en la Fase 4 cuando un capítulo no pasa: qué cuenta como nombre mal escrito, qué hace el bucle con un parche que no cambia nada, qué cronología se comprueba y quién la calcula, y adónde van las contradicciones que encuentra el juez. Deriva de [`docs/architecture.md`](../../docs/architecture.md) §4 (Fase 4), §11a, §11b, §11c y §17, y de la spec del backend, [`specs/backend/spec.md`](../backend/spec.md) §4.4 y §7.2. **Si algo de este documento contradice a la arquitectura, manda la arquitectura.** La forma técnica exacta vive en [`plan.md`](plan.md).

## 1. Qué problema resuelve

El bucle de un capítulo —escribir, validar en dos pasadas, reparar, aprobar— tiene una promesa y un riesgo. La promesa es G3: **ningún capítulo se aprueba con una incidencia bloqueante**. El riesgo es que una pieza del bucle convierta esa promesa en un atasco: un validador que bloquea un texto correcto, un editor que no puede arreglar lo que no está roto, un bucle que no se da cuenta y paga los intentos hasta el `Fail`.

Y hay una promesa que no se estaba cumpliendo: la arquitectura dice que la cronología de la prosa se comprueba en cada capítulo y antes de publicar, y en el código nadie la llamaba.

Lo que esta spec fija es que **G3 y G5 se cumplen de verdad y sin atascos gratuitos**: el bucle no bloquea lo correcto, no reintenta lo inútil, comprueba la cronología donde dice que la comprueba y deja a la vista lo que el juez encontró.

## 2. El bucle de reparación

### 2.1 Qué es otra grafía

`nombres_exactos` bloquea cuando un nombre del canon aparece en el capítulo **solo al normalizar** —otra letra, una tilde de menos— y no tal como se escribe. **La inicial no cuenta como otra grafía, en las dos direcciones:**

- **en mayúscula**, siempre: «fray Luis de León» es «Fray Luis de León» a principio de frase;
- **en minúscula**, solo en la primera palabra de un nombre de varias: el personaje que el canon llama «Padre de Julia» es «el padre de Julia» en mitad de una frase.

El resto del nombre se escribe como en el canon: «manuel ferrer» y «Manuel ferrer» siguen siendo otra grafía, y un nombre de una sola palabra en minúscula —«tomasa»— también.

### 2.2 El parche que no cambia nada

El editor recibe el capítulo y las incidencias y devuelve el capítulo corregido. **Si el texto devuelto es el mismo**, sin contar espacios al principio y al final:

- **no se guarda como versión**: no es un intento;
- la versión que se estaba reparando gana una incidencia **`reparacion_sin_cambios`**, bloqueante, que dice que el editor no cambió nada y que, si el texto ya es correcto, el que falla es el validador;
- **los reintentos se agotan**: `intentos` pasa a `max_intentos` y `Validate` lleva a `Fail`, como pide G3.

La arista no cambia: `Repair` sigue yendo a `Validate`. Si lo que bloqueaba venía de la pasada determinista, `Validate` vuelve a verlo y va a `Fail` sin coste. Si venía de la pasada del extractor, esta corre una vez más antes del `Fail`; se admite, porque es una llamada barata frente a los dos parches que se ahorran.

### 2.3 Qué no cambia

G3 se mantiene tal cual: lo bloqueante vuelve al editor, y agotados los reintentos, `Fail`. **Nada de esta spec aprueba un capítulo con una incidencia bloqueante.**

## 3. La cronología del capítulo

### 3.1 Qué cronología

En la pasada del extractor, después de que el extractor escriba los eventos narrativos del intento, se compone **la cronología acumulada**:

- **las personas**: todos los personajes del canon, con su nacimiento —`NACIMIENTO_DESCONOCIDO` si no lo tienen— y su muerte;
- **los eventos**: los históricos, los narrativos de **las versiones aprobadas vigentes** de cada capítulo —la de mayor identificador entre las aprobadas— y los del **intento que se valida**.

Los eventos de un intento descartado no cuentan: describen algo que ya no está en la novela. Ningún evento lleva escenario, porque el extractor no lo da; el escenario desconocido deja fuera el invariante de los dos sitios, y cuentan el orden, el nacimiento y la muerte.

### 3.2 Cada intento escribe sus eventos

La clave de un evento narrativo es **`cap{N}-v{versión}-{clave del extractor}`**. Con la versión en la clave, cada intento escribe sus propias filas: un evento que el editor corrigió no deja atrás la fila errónea del intento anterior, que con la clave sin versión se quedaba —el `INSERT OR IGNORE` descartaba la nueva— y seguía tumbando el capítulo.

### 3.3 Qué bloquea

La cronología se comprueba con `verificar_cronologia` (§4) con severidad **bloqueante** y validador **`cronologia_capitulo`**. Solo se quedan las incidencias que **tocan a un evento del intento**: las que llevan `cap{N}-v{versión}-` en su ubicación o en su mensaje. Un choque entre dos capítulos ya aprobados no es algo que el editor de este pueda arreglar, y devolvérselo solo gastaría sus reintentos. Lo que queda se registra en la versión y vuelve al editor como cualquier otra incidencia bloqueante.

## 4. Quién calcula la cronología

`verificar_cronologia(novela, bloquea, validador)` es el único cálculo de la cronología, en sus tres paradas:

| Parada | `bloquea` | `validador` |
|---|---|---|
| Gate de Plotting, sobre la escaleta | no: aviso | el de quien la calcula |
| Pasada del extractor | sí | `cronologia_capitulo` |
| Publicación | sí | `cronologia_publicacion` |

**Calcula Lean si `lake` está en el `PATH`; si no, o si Lean falla por cualquier avería, los cuatro invariantes se evalúan en Python** sobre el mismo `NovelaLean`. La severidad la decide `bloquea`, no quién calcula. Sin eventos no hay nada que comprobar.

## 5. La publicación

Antes de publicar la versión —antes de escribirla, de modo que si falla no existe—, se compone la cronología **de lo aprobado**, sin intento en curso, y se comprueba con `bloquea`. Si queda alguna incidencia, **la versión no se publica**, como pide G5: `PublicacionRechazada` lleva las incidencias, `publish` las guarda citando los capítulos de los eventos culpables y la novela vuelve al gate de Writing (ver la [spec de validación](../validacion/spec.md) §3). Antes, la cronología de la publicación leía todos los eventos, también los de intentos descartados, y no la llamaba nadie.

## 6. Las contradicciones del juez

El juez lista las contradicciones de la novela antes de puntuar, y su número topa la nota de continuidad. Además, **cada contradicción queda como incidencia de aviso sin capítulo**, validador **`juez_contradiccion`**, con ubicación en los capítulos que cita —«Capítulo 1… el capítulo 5» da `cap1, cap5`—. Cada juicio retira las del anterior.

- **El gate de Writing** las enseña en su informe, «El juez encontró N contradicción(es)», con cada una. Llegan ahí cuando la nota no pasa el umbral y la novela vuelve al gate.
- **El aviso de Telegram** de ese gate dice cuántas hay.
- **El aviso de terminada** dice cuántas listó el juez cuando la nota pasó y la novela se publicó igual.

No se abre un camino para rehacer el capítulo que cita el juez: exigiría aristas nuevas en el modelo TLA+.

## 7. Contratos

| Pieza | Cambio |
|---|---|
| `nombres_exactos` | Admite la inicial en minúscula en la primera palabra de un nombre de varias |
| `reparar(...) -> int \| None` | `None` si el editor devolvió el mismo texto; en ese caso no escribe versión y registra `reparacion_sin_cambios` |
| `repair` | Con `None`, `intentos = max_intentos` y conserva la versión |
| `cronologia_evento.clave` | `cap{N}-v{versión}-{clave}` para los eventos narrativos |
| `commons/formal/cronologia.py` | Nuevo: `cronologia_de_la_novela(db, con_version=None)` y `verificar_cronologia(novela, bloquea, validador=None)` |
| `extraer` | Añade las incidencias `cronologia_capitulo` del intento |
| `publicar` | Comprueba la cronología de lo aprobado antes de escribir la versión |
| `cronologia_completa` | Devuelve la cronología de lo aprobado |
| `registrar_contradicciones(db, contradicciones)` | Nuevo, en `publication/nodos.py`; lo llama `judge` |
| `InformeDeWriting.contradicciones` | Nuevo campo, que enseña `como_texto` |
| `aviso_de_terminada(..., contradicciones=0)` | Nuevo parámetro |
| `regenerar(novela, *, settings, aprobada=True, ...) -> ResultadoInvocacion` | Nuevo, en `commons/graph/run.py` (§9) |
| `ResultadoInvocacion.nota` | Nuevo campo: lo que se cuenta cuando no se ejecutó el grafo |
| `tras_idle(estado)` | Nuevo router de `Idle`: `RequestChange` si `pc` lo dice, `END` si no |
| `checkpoint` | En regeneración saca el siguiente de `a_regenerar` y, con la cola vacía, revisa los invalidados |
| `regeneration/revision.py` | Nuevo: `revisar_invalidados(numeros) -> list[int]` y `pasa_coste_cero(version, numero)` |
| `DecisionTomada.fase` | Nuevo campo: la fase del gate decidido |
| `regeneration/retirados.py` | Nuevo: `pares`, `aparece`, `sustituir`, `incidencias`, `propagar` y `capitulos_que_lo_nombran` |
| `EstadoNovela.retirados` | Nuevo campo: los pares `[viejo, nuevo]` del cambio de nombre en curso |
| `calcular_alcance(..., pares=None)` | Suma los capítulos cuyo texto aprobado dice el valor viejo |
| `validar_determinista(..., retirados=None)` | Suma una incidencia bloqueante `valor_retirado` por cada nombre viejo que conserve el capítulo |
| `storymaker decidir` | Sobre un gate de Regeneración llama a `regenerar` en vez de reanudar |

## 8. Requisitos

| ID | Requisito | Clase | Gate |
|---|---|---|---|
| REQ-ES-01 | `nombres_exactos` no bloquea la inicial en minúscula de un nombre de varias palabras, y sigue bloqueando el resto de diferencias | T | G3 |
| REQ-ES-02 | Un parche que devuelve el mismo texto no se guarda, deja `reparacion_sin_cambios` y agota los reintentos | T | G3 |
| REQ-ES-03 | La pasada del extractor comprueba la cronología acumulada —aprobado vigente más el intento— y bloquea solo por lo que toca al intento | T | G3 |
| REQ-ES-04 | Cada intento escribe sus propios eventos narrativos | T | G3 |
| REQ-ES-05 | La cronología la calcula Lean si hay `lake` y Python si no o si se avería, con la severidad del sitio | T | G3, G5 |
| REQ-ES-06 | La publicación comprueba la cronología de lo aprobado antes de escribir la versión, y si falla no hay versión | T | G5 |
| REQ-ES-07 | Las contradicciones del juez quedan como avisos con sus capítulos, y las enseñan el gate de Writing y el aviso de terminada | T | G4 |
| REQ-ES-08 | Aprobar el gate de Regeneración de una novela en `Idle` ejecuta `RequestChange` y, con capítulos afectados, publica una versión nueva | T | G1 |
| REQ-ES-09 | En regeneración se reescriben solo los capítulos de `a_regenerar`, uno tras otro; nada posterior se reescribe en cascada | T | G1 |
| REQ-ES-10 | Con la cola vacía, cada invalidado pasa la determinista y la cronología sin invocar a nadie; el que pasa vuelve a `aprobado` y se reutiliza, el que no se reescribe | T | G3 |
| REQ-ES-11 | La versión nueva comparte con la anterior los capítulos no tocados, y la anterior sigue entera | T | G5 |
| REQ-ES-12 | Sin fila ni valor no se cambia nada; con una fila que nadie usa se aplica sin versión nueva; un hecho con el corpus sellado no se cambia; rehacer o editar descartan la petición | T | G1 |
| REQ-ES-13 | Un cambio de nombre reescribe el valor viejo, como palabra entera, en las columnas de texto de `plan_*` y `canon_*`, y no toca `mundo_*` | T | G1 |
| REQ-ES-14 | El alcance de un cambio de nombre incluye los capítulos cuyo texto aprobado dice el valor viejo | T | G1 |
| REQ-ES-15 | Mientras dura la regeneración, un capítulo que conserva el valor viejo tiene una incidencia bloqueante `valor_retirado`, también en la revisión de los invalidados | T | G3 |

Todos son **T**. La fidelidad de la evaluación en Python a `Cronologia.Basico`, que con esta spec pasa a bloquear en G3 y en G5 cuando no hay `lake`, queda bajo U-1 de [`verification.md`](../../docs/verification.md).

## 9. La regeneración que propaga

Detalla la Fase 6 de §4 de la [arquitectura](../../docs/architecture.md) y §4.6 de la [spec del backend](../backend/spec.md) en lo que toca al bucle de Writing, que es por donde pasa todo capítulo regenerado.

**La entrada.** El gate de Regeneración lo abre `POST /cambios` como fila, no un `interrupt()`, así que al decidirlo no hay nada que reanudar: el grafo terminó en `Idle`. `storymaker decidir` mira la fase del gate y, si es `regeneration`, llama a `regenerar`. Con la decisión «aprobar», `regenerar` resuelve la petición y, si hay capítulos afectados, escribe en el checkpoint `pc = RequestChange` **como salida de `Idle`** —con los intentos, la versión en curso y los rechazos del juez a cero— y reanuda por `invocar`. El router `tras_idle` lleva a `RequestChange`; recién publicada, `pc` es `Idle` y va a `END`. Es el mismo mecanismo que `reintentar` usa como salida de `SealCorpus`.

**Sin grafo.** Las aristas del modelo obligan a que `RegenerateAffected` lleve a `Validate`, y el grafo no se puede recorrer con el alcance vacío. Por eso `regenerar` decide antes de entrar, y en estos cuatro casos devuelve una `nota` y cierra la `fase_run` de la petición:

| Caso | Efecto |
|---|---|
| Decisión distinta de «aprobar» | Petición descartada; `fase_run` `abortada`; nada cambia |
| La aprobación no nombra fila y valor | Nada cambia |
| Un hecho del corpus con el corpus sellado | Nada cambia: el sello lo hace de solo lectura, como en `/ediciones` |
| Una fila que ningún capítulo usa | Se aplica con `cambio.aplicar`, sin versión nueva |

**La cola.** `RegenerateAffected` escribe el primero de `a_regenerar`, que pasa por `Validate`, `Extract` y `Repair` como cualquier capítulo. En regeneración, `Checkpoint` **no suma uno**: saca el siguiente de la cola y deja `capitulo` en él. Así se reescriben solo los afectados, y el router `tras_checkpoint` no cambia.

**Los invalidados.** Cuando la cola se vacía y `a_invalidar` no, `Checkpoint` llama a `revisar_invalidados`. Va aquí y no en `Invalidate` porque Lean mira la cronología entera, y antes de regenerar los afectados la comprobaría contra capítulos a punto de cambiar. Para cada invalidado, en orden, se toma su última versión `invalidado` y se le pasa la pasada determinista y la cronología de §3 con esa versión, bloqueando solo lo que lleva su marca. No se llama al escritor ni al extractor, porque sus filas están escritas desde que se aprobó. Si pasa, vuelve a `aprobado` y entra en la cronología del siguiente. Si no pasa, vuelve a la cola y se reescribe. Con todo resuelto, `regenerando` pasa a falso y `capitulo` queda más allá del último, que lleva al gate de Writing, al juez y a `PublishVersion`.

**El valor retirado.** Cambiar la fila del canon no basta para que un nombre llegue al texto. En la primera regeneración real, el paquete del escritor llevaba el nombre nuevo una sola vez, en la ficha, y el viejo de tres a seis veces, en los beats de la escaleta y en la prosa del capítulo anterior. La versión nueva salió con el nombre de siempre. Por eso un cambio de `nombre` de personaje o de `termino` de glosario tiene tres consecuencias más, todas en `regeneration/retirados.py`:

- **Los pares.** Son el nombre entero y, si el viejo y el nuevo tienen el mismo número de palabras, cada palabra que cambia y tiene al menos tres letras. Se buscan como palabra entera, y una mención del nombre entero no cuenta además por sus palabras.
- **La propagación.** `RequestChange` reescribe los pares en todas las columnas de texto de `plan_*` y `canon_*`, porque el nombre se copió en prosa al planificar. `mundo_*` está sellado y el texto de los capítulos es inmutable, así que no se tocan.
- **El alcance y la puerta.** `calcular_alcance` suma los capítulos cuya última versión aprobada dice el valor viejo, porque las tablas de uso no registran una mención de pasada. Los pares viajan en `EstadoNovela.retirados`. Mientras dura la regeneración, la pasada determinista, y con ella la revisión de los invalidados, marca como bloqueante cada valor viejo que conserve el capítulo, con la sustitución como propuesta para el editor. Al terminar la regeneración, `retirados` se vacía.

**Lo que no cambia.** `publicar` compone con la última versión `aprobado` de cada capítulo, así que la versión nueva reutiliza lo no tocado sin duplicarlo, y la anterior sigue entera en su manifiesto.

**Desviación registrada.** El modelo TLA+ guarda `Checkpoint → WriteChapter` con `~regenerando` e invalida un solo capítulo por petición. La arista existe y la prueba de identidad pasa, pero la guarda del código es más ancha. Queda para una pasada de TLC con una variable de pendientes (It-35).

## 10. Revisión adversaria

Las preguntas que se le hicieron a este documento y cómo se resolvieron. Las dos primeras eran del Autor y las decidió él; las demás se resolvieron contra el código y la arquitectura.

| Pregunta | Resolución |
|---|---|
| Si el editor no puede arreglar un bloqueante, ¿se aprueba el capítulo con aviso? | **Decisión del Autor: no.** G3 se mantiene; lo que se hace es cortar antes, sin pagar parches sobre el mismo texto (§2.2) |
| Sin `lake`, ¿Lean o nada donde la cronología bloquea? | **Decisión del Autor: Lean o Python, bloqueando** (§4), bajo U-1 |
| Si dos capítulos ya aprobados chocan entre sí, ¿se le devuelve al editor del capítulo en curso? | No: no puede arreglarlo, y gastaría sus reintentos. Solo bloquea lo que toca a su intento (§3.3). El choque entre aprobados lo para la publicación (§5) |
| Si el intento 2 corrige un evento del intento 1, ¿qué fila queda? | Con la clave sin versión, la del intento 1: el `INSERT OR IGNORE` descartaba la nueva. De ahí la versión en la clave (§3.2) |
| ¿Puede el corte del parche sin cambios costar una llamada más? | Sí, una del extractor, si lo que bloqueaba venía de su pasada. Se admite frente a los dos parches que se ahorran (§2.2) |
| ¿La cronología de la publicación mezclaba intentos descartados? | Sí: leía todos los eventos. Ahora solo lo aprobado (§5) |
| Sin escenario en los eventos del extractor, ¿se comprueba «dos sitios a la vez» en la prosa? | No, ni con Lean ni con Python: todos los eventos llevan el escenario desconocido, que en los dos iguala y en Python además exime. Cuentan orden, nacimiento y muerte (§3.1) |
| Un nombre descriptivo de una sola palabra en minúscula, ¿bloquea? | Sí, igual que «tomasa». Se admite: el caso que atascaba era el de varias palabras, y relajarlo para una sola dejaría pasar un nombre propio en minúscula (§2.1) |
| ¿Se puede rehacer el capítulo que cita el juez? | No sin aristas nuevas en el modelo TLA+; queda como aviso (§6) |

## 11. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-25 | §4: la cronología de la publicación ya no deshace una transacción ni termina la novela: el rechazo se guarda citando capítulos y vuelve al gate de Writing | Propagación de la [spec de validación](../validacion/spec.md) |
| 2026-09-25 | §9 gana **el valor retirado**: propagación a `plan_*` y `canon_*`, alcance por texto y bloqueante `valor_retirado`. Entran sus contratos en §7 y REQ-ES-13 a REQ-ES-15 | La primera regeneración real publicó una versión 2 que conservaba el nombre viejo en todos los capítulos (It-36) |
| 2026-09-25 | Entra §9, la regeneración que propaga, con sus contratos en §7 y REQ-ES-08 a REQ-ES-12 en §8. La revisión adversaria pasa a §10 y el registro a §11 | Aprobar el gate de Regeneración no ejecutaba nada (It-35). Escrito a la vez que el código, por petición del Autor, sin grilling previo |
| 2026-09-24 | Primera versión: la grafía de los nombres, el parche sin cambios, la cronología del capítulo y de la publicación con respaldo en Python, y las contradicciones del juez | Se propagan §4 (Fase 4), §11a, §11b, §11c y §17 de la arquitectura |
