# Spec — Validación de la novela antes de publicar

Qué hace cada validador que cierra la novela: `render_visual` en un navegador, el rechazo de la publicación y su vuelta al escritor, la cobertura de personalización en el gate de Writing, el octavo criterio del juez, la revisión humana, Lean dentro del flujo y el modelo TLA+ que lo verifica. Toca contratos de la [spec del backend](../backend/spec.md): §3.2 (el grafo), §3.6 (`commons/validation`), §3.7 (`commons/formal`) y §4.4-§4.5 (Writing y Publication). Deriva de [`docs/architecture.md`](../../docs/architecture.md) §9 y §11. La forma técnica exacta está en [`plan.md`](plan.md).

## 1. Qué problema resuelve

La novela tiene que pasar cuatro familias de validadores antes de publicarse, y cada uno tiene que tener un nombre, correr en un punto concreto y dejar su *score* en Langfuse. Cinco piezas no lo cumplían enteras:

- **`render_visual` no miraba lo que se ve.** Buscaba `id="indice"` y otros dos identificadores en el HTML generado. Una portada oculta o un enlace del índice que no lleva a ninguna parte pasaban en verde, y un fallo no volvía a ningún rol: tumbaba la invocación.
- **Un rechazo de la publicación terminaba la novela.** Lean o el render lanzaban una excepción y el grafo acababa en `Fail`, sin arista de vuelta ni motivo para nadie.
- **`cobertura_personalizacion` no corría.** Estaba escrita, registrada y documentada en el gate de Writing, y ningún nodo la llamaba.
- **El juez no puntuaba el tono**, que el brief declara y ningún otro criterio cubre.
- **La revisión humana no tenía herramienta.** El protocolo estaba escrito, pero registrar la nota y compararla con la del juez era código pegado a mano en una consola.

Y en la verificación formal, dos más:

- **Lean escribía sobre el fichero versionado** `formal/lean/Cronologia/Generado.lean` en cada capítulo, y con Lean instalado sus incidencias no decían quién ni cuándo.
- **TLC no terminaba.** El modelo no era finito —`versiones` crecía con cada regeneración— y no tenía acciones explícitas de caída, reanudación ni reintento manual.

Por el criterio de producto, nada de lo que se añade puede atascar una novela sin salida: el render sin navegador avisa y sigue, el rechazo vuelve al Autor y tiene tope, y la cobertura bloquea en el informe, donde decide una persona.

## 2. `render_visual`

### 2.1 Qué comprueba

Dos mitades, en este orden:

1. **La estructura**, sin navegador: que portada, índice y ficha de personajes estén en el HTML, que haya capítulos y que el índice tenga entradas.
2. **El navegador.** Abre la lectura en Chromium con una ventana de 1000 × 1200 y comprueba:
   - que portada, índice y ficha de personajes son visibles, tienen caja de tamaño no nulo y tienen texto;
   - que el índice tiene un enlace por capítulo;
   - que cada enlace, pulsado, lleva a un elemento que existe, lo deja en pantalla y contiene al menos un párrafo.

Cada incidencia es bloqueante y lleva en `ubicacion` la pieza (`portada`, `indice`, `personajes`) o el capítulo (`capN`). Si las dos mitades encuentran lo mismo, se cuenta una vez.

### 2.2 Qué lectura se abre

La **candidata**: el HTML de lectura armado con la lista exacta de `capitulo_version` que la versión va a tener, **antes** de escribir ninguna fila de la versión. Se arma con `construir_lectura_candidata(db, capitulo_version_ids)`, que produce la misma `Lectura` que `construir_lectura(db, version_id)` produciría después sobre la versión escrita.

### 2.3 Sin navegador

Si Playwright no se puede importar o Chromium no arranca, `en_navegador` devuelve `None`. `render_visual` devuelve entonces las incidencias de la estructura más un **aviso**, no bloqueante, que dice que el render solo se comprobó en el HTML.

### 2.4 Su *score*

Uno por paso por `PublishVersion`, con nombre `render_visual`, objeto `novela` y el número de la versión candidata: 1 si no hay bloqueantes, 0 si los hay.

## 3. El rechazo de la publicación

### 3.1 Dentro de `publicar`

`publicar` compone la candidata y corre **siempre las dos comprobaciones**, también si la primera falla, para que el Autor vea todo de una vez: la cronología completa, con validador `cronologia_publicacion`, y `render_visual`. Cada una deja su *score*. Si alguna trae bloqueantes, lanza `PublicacionRechazada` con esas incidencias y **no escribe nada**. Si no, escribe la versión y su manifiesto.

Una candidata que no se puede ni componer —un capítulo sin versión aprobada— sigue lanzando `PublicacionRechazada` **sin incidencias**.

### 3.2 En el nodo `publish`

| Caso | Efecto | Estado que devuelve |
|---|---|---|
| Publicada | Retira los rechazos anteriores | `pc = Idle`, `hay_bloqueantes = False` |
| Rechazada con incidencias | `registrar_rechazo`: retira las de `cronologia_publicacion` y `render_visual` sin capítulo y escribe las nuevas, bloqueantes, con los capítulos citados en `ubicacion` (`cap1, cap5`) | `pc = PublishVersion`, `hay_bloqueantes = True`, `rechazos_juez + 1` |
| Rechazada sin incidencias | Relanza la excepción | — |

### 3.3 Qué capítulos cita una incidencia

`capitulos_citados(incidencia)` busca `cap` o `capitulo` seguido de un número en `ubicacion`, `mensaje` y `propuesta`. Así lee la clave de un evento de la cronología (`cap4-esc10`), las líneas de eventos culpables que da Lean (`evento 5 · cap1-ritual`) y la ubicación del render (`cap3`).

### 3.4 La arista

`tras_publish`: sin bloqueantes → `Idle`; con bloqueantes y `rechazos_juez < max_rechazos_juez` → `AwaitApproval4`; si no → `Fail`. El contador es el del juez, y una petición del lector lo pone a cero.

## 4. El gate de Writing

### 4.1 Qué se revisa al llegar

Cada vez que la novela llega a `AwaitApproval4`, **en interactivo y en batch**, `revisar(db, observador)`:

1. construye el informe del manuscrito;
2. sustituye las incidencias sin capítulo de `cobertura_personalizacion` por las de esta llegada;
3. deja su *score* (objeto `novela`, id 1).

En interactivo se hace en la primera pasada del nodo, no al reanudar tras la decisión.

### 4.2 Qué enseña el informe

Además de lo que ya enseñaba —capítulos aprobados, avisos, contradicciones del juez—, los **rechazos de la publicación**: cuántos motivos y cuáles, con la advertencia de que rehacer reescribe los capítulos que citan. El informe sale entero por la salida del proceso y en la pantalla del gate.

### 4.3 Qué hace «rehacer»

Rehacer o editar en `AwaitApproval4` entra en **modo regeneración** sobre los capítulos citados por las incidencias sin capítulo de `juez_contradiccion`, `cronologia_publicacion` y `render_visual`, en orden y dentro del rango de la novela. Si ninguna cita ninguno, se rehace el último. El estado queda con `regenerando = True`, `capitulo` = el primero, `a_regenerar` = el resto, `intentos = 0` y `capitulo_version_id = None`. `Checkpoint` recorre la cola y, vacía, vuelve al gate.

### 4.4 Cómo llega el motivo al escritor

El bloque 1 del paquete del capítulo N añade, cuando alguna de esas incidencias cita `capN`, un fragmento con sus mensajes: «Este capitulo se reescribe por lo siguiente…». Va entre los fragmentos fijos del bloque, que no se recortan.

## 5. El juez y la revisión humana

### 5.1 El octavo criterio

`Criterio.TONO` (`tono`) entra en el esquema y en `rubrica.yaml`, con su pregunta: si el tono declarado en el brief se sostiene en todos los capítulos, sin saltos que no pida la historia. El juez pasa a puntuar ocho criterios; la media y el umbral no cambian de forma.

### 5.2 La hoja

`storymaker revision hoja NOMBRE [--version N] [--destino F]` escribe un YAML con la novela, la versión (por defecto la última publicada), el revisor, la duración de la lectura y, por criterio, `valor` y `justificacion` vacíos. **No copia las preguntas**, que se leen en `rubrica.yaml`, ni lleva las notas del juez.

### 5.3 El registro y el acta

`storymaker revision registrar NOMBRE HOJA [--acta F]`:

- **Rechaza la hoja** si falta o sobra un criterio, si una nota no es un entero de la escala, si una justificación tiene menos de diez caracteres, o si la versión no está publicada. Lo hace con `HojaInvalida`, que la CLI traduce a mensaje.
- **Registra** el *score* `revision_humana` en la tabla `score` y en la sesión de Langfuse, con objeto `novela`, el número de versión, la media y un detalle con las notas, las justificaciones y el revisor.
- **Compone el acta** con la forma de la plantilla de `docs/revision-humana.md` §5: la tabla criterio a criterio con la nota de la persona, la del último juicio y la justificación; las dos medias; y las divergencias de más de dos puntos. La escribe en `--acta` o la imprime.

## 6. Lean dentro del flujo

### 6.1 Quién decide y quién explica

`verificar_cronologia` evalúa siempre en Python. Con Lean activo:

| Lean | Python | Incidencias |
|---|---|---|
| Rechaza | Ve algo | Las de Python, que nombran personaje y fechas |
| Rechaza | No ve nada | Las de Lean |
| Aprueba | — | Ninguna |

Sin Lean, o si Lean se avería, las de Python. La severidad la sigue decidiendo `bloquea`.

### 6.2 Cuándo está activo

`lean_activo()` es cierto si hay `lake` en el PATH y `STORYMAKER_LEAN` no vale `0`, `no` ni `false`. La suite lo pone a `0` por defecto.

### 6.3 La copia de trabajo

`runner.verificar(novela)` sin `proyecto` copia `formal/lean`, con su `.lake`, a un directorio temporal, genera allí `Generado.lean`, ejecuta `lake exe verificar` y borra la copia. Con `proyecto` explícito trabaja sobre él, como hasta ahora.

### 6.4 Nombres y *scores*

- En el gate de Plotting las incidencias se llaman `cronologia_escaleta`, también las que produce Lean, para que el gate las encuentre.
- Hay un *score* por validador en cada uno de los tres puntos: `cronologia_escaleta`, junto a `cobertura_anclada` y `arco_anclado`, con objeto `escaleta`; `cronologia_capitulo`, con objeto `capitulo_version`; y `cronologia_publicacion`, con objeto `novela`.
- Fuera de una invocación, la revisión de la Trama puntúa con un observador nulo, solo en la base.
- En la pasada del extractor, una incidencia de Lean cuenta para el intento si su `propuesta` nombra un evento del intento.

## 7. El escenario de cada escena

`resolver_escenario(nombre, claves, *, clave_de_escena, sin_resolver, resueltos_por_parecido)` resuelve, en orden:

1. la clave exacta `escenario:<nombre>`;
2. la clave normalizada, con la misma `normalizar` que el guardrail;
3. la única clave que contiene al nombre o está contenida en él.

Lo resuelto en el segundo o el tercer paso se añade a `resueltos_por_parecido`, y lo no resuelto, a `sin_resolver`. El gate de la Trama ya enseña las dos listas.

## 8. El modelo TLA+

`formal/tla/harness.tla` gana:

- **Tres constantes de entorno**: `MaxCaidas`, `MaxReintentos` y `MaxCambiosLector`.
- **Cuatro variables**: `vivo`, `caidas`, `reintentos` y `cambios`. `Mueve` exige `vivo`.
- **Tres acciones fuera de `Aristas`**:
  - `Caida`: cualquier nodo que no sea terminal ni `Idle`, con caídas disponibles.
  - `ResumeFromCheckpoint`: no toca más que `vivo`.
  - `Reintentar`: desde `Fail`, con el corpus sellado, el capítulo en curso sin validar y reintentos disponibles; exige la arista `SealCorpus → WriteChapter` y lleva a `WriteChapter` con `intentos = 0`.
- **Dos aristas**, `PublishVersion → AwaitApproval4` y `PublishVersion → Fail`, con el tope de `rechazosJuez`.
- **`RehacerWriting`** elige un capítulo aprobado y lo saca de `validados`.
- **`IdleRequest`** exige cambios disponibles y pone a cero `rechazosJuez`.

`harness.cfg` fija 5 capítulos, 2 reintentos, gates activos, 2 rechazos y una caída, un reintento y un cambio, y comprueba los cinco invariantes, `PreviousVersionPreserved` y `Termina`. `harness_batch.cfg` hace lo mismo con los gates apagados.

## 9. Contratos

| Pieza | Contrato |
|---|---|
| `publication/render.py` | `construir_lectura_candidata(db, ids) -> Lectura`; `estructura(lectura) -> list[Incidencia]`; `async en_navegador(lectura) -> list[Incidencia] \| None`; `async render_visual(lectura) -> list[Incidencia]` |
| `publication/nodos.py` | `PublicacionRechazada(mensaje, incidencias=())`; `VALIDADORES_DE_PUBLICACION`; `capitulos_citados(i) -> list[int]`; `registrar_rechazo(db, incidencias)`; `publish` según §3.2 |
| `commons/graph/aristas.py` | `ARISTAS` con las dos aristas nuevas; `tras_publish(estado) -> str` |
| `writing/gate.py` | `InformeDeWriting.rechazos`; `revisar(db, observador)`; `capitulos_a_rehacer(db, n) -> list[int]`; `motivos_para(db, n) -> list[str]` |
| `gates/nodos.py` | `AwaitApproval4` revisa al llegar y rehace según §4.3 |
| `commons/db/repos/arnes.py` | `QUE_DEVUELVEN_CAPITULOS`; `incidencias_que_devuelven_capitulos(db) -> list[tuple[str, str]]` |
| `commons/context/bloques.py` | `motivos_para_rehacer(db, n) -> list[str]`, en el bloque 1 |
| `publication/esquemas.py`, `rubrica.yaml` | `Criterio.TONO` y su pregunta |
| `publication/revision_humana.py` | `criterios()`, `hoja(novela, version)`, `leer_hoja(texto)`, `notas_del_juez(db)`, `registrar_revision(db, observador, texto) -> Acta`, `Acta.como_markdown()`, `HojaInvalida` |
| `cli/comandos.py` | `storymaker revision hoja` y `storymaker revision registrar` |
| `commons/formal/cronologia.py` | `lean_activo()`; `verificar_cronologia` según §6.1 |
| `commons/formal/runner.py` | `verificar(novela, *, proyecto=None)` según §6.3 |
| `plotting/gate.py` | `PUNTUADOS_EN_LA_TRAMA`, `puntuar(db, incidencias)` |
| `plotting/escaleta.py` | `resolver_escenario` según §7 |
| `formal/tla/harness.tla`, `harness.cfg`, `harness_batch.cfg` | §8 |

## 10. Requisitos

| ID | Requisito | Clase | Gate |
|---|---|---|---|
| REQ-VA-01 | `render_visual` abre la lectura candidata en Chromium y bloquea si portada, índice o ficha de personajes no son visibles, no tienen tamaño o están vacíos | T | G5 |
| REQ-VA-02 | Cada enlace del índice, pulsado, deja en pantalla su capítulo con al menos un párrafo; lo que no, bloquea citando `capN` | T | G5 |
| REQ-VA-03 | Sin navegador, `render_visual` devuelve la estructura y un aviso no bloqueante | T | G5 |
| REQ-VA-04 | La lectura que se juzga es la de la candidata, igual a la de la versión que se escribiría, y se juzga antes de escribir ninguna fila | T | G5 |
| REQ-VA-05 | Un rechazo de la publicación no deja versión, queda como incidencia bloqueante que cita capítulos y sustituye al rechazo anterior | T | G5 |
| REQ-VA-06 | `PublishVersion` va a `Idle`, a `AwaitApproval4` o a `Fail` según `tras_publish`, con el contador del juez | A/T | G3 |
| REQ-VA-07 | Rehacer en el gate de Writing reescribe los capítulos citados, o el último si no hay citas, en modo regeneración | T | G4 |
| REQ-VA-08 | El escritor del capítulo citado recibe el motivo en el bloque 1, entre lo que no se recorta | T | G4 |
| REQ-VA-09 | `cobertura_personalizacion` corre en cada llegada al gate de Writing, en interactivo y en batch, y deja incidencia y *score* | T | G4 |
| REQ-VA-10 | `render_visual`, `cronologia_publicacion`, `cronologia_capitulo`, `cronologia_escaleta`, `cobertura_anclada`, `arco_anclado` y `cobertura_personalizacion` dejan un *score* también cuando pasan | T | G6 |
| REQ-VA-11 | El juez puntúa ocho criterios, entre ellos `tono`, y el esquema y `rubrica.yaml` nombran los mismos | T | G1 |
| REQ-VA-12 | La hoja de revisión humana nombra todos los criterios, sin copiar sus preguntas ni las notas del juez | T | G2 |
| REQ-VA-13 | Una hoja incompleta, fuera de escala, sin justificación o de una versión no publicada no se registra | T | G2 |
| REQ-VA-14 | Registrar la hoja deja el *score* `revision_humana` y compone el acta con las dos notas y las divergencias de más de dos puntos | T | G2 |
| REQ-VA-15 | Al menos una novela completa revisada por una persona, con su acta en `docs/revision-humana.md` | I | G2 |
| REQ-VA-16 | Con Lean activo, Lean decide y Python redacta cuando ve lo mismo | T | G3 |
| REQ-VA-17 | `runner.verificar` sin proyecto no modifica `formal/lean` | T | G1 |
| REQ-VA-18 | `STORYMAKER_LEAN=0` apaga Lean aunque haya `lake` | T | G1 |
| REQ-VA-19 | La escena se enlaza a su escenario por clave exacta, normalizada o parecido único, y lo adivinado y lo perdido se enseñan | T | G4 |
| REQ-VA-20 | TLC agota el espacio de `harness.cfg` y de `harness_batch.cfg` sin violar ningún invariante ni propiedad | A | G1 |
| REQ-VA-21 | Con equidad débil sobre la aprobación, TLC encuentra una violación de `Termina` | A | G1 |
| REQ-VA-22 | Las aristas del grafo y `Aristas` del modelo siguen siendo la misma relación | A/T | G1 |

REQ-VA-15 es **I** y es la única que no se cierra con código: la herramienta está, y el acta la escribe una persona que ha leído la novela. REQ-VA-20 y REQ-VA-21 son **A** porque las cierra el *model checker* sobre el modelo, no una prueba sobre el código; REQ-VA-21 existe para saber que la comprobación de `Termina` no es vacía.

## 11. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-25 | Primera versión, con REQ-VA-01 a REQ-VA-22 | Deriva de arq. §9 y §11 tal como quedaron el 2026-09-25 |
