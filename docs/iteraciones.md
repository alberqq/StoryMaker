# Registro de iteraciones

Qué se cambió, **por qué** y qué efecto tuvo. Una fila por iteración, en orden cronológico inverso: lo más reciente arriba.

No es un registro de commits —para eso está `git log`— ni el registro de cambios de un documento, que anota qué párrafo se tocó. Aquí se anota la **cadena causa → efecto**: qué observación provocó el cambio, qué se hizo y qué se midió después. Una iteración sin efecto medido es una iteración sin terminar, y se marca como tal.

Cada documento mantiene además su propio registro de cambios al final. Cuando una iteración de aquí toca un documento, se anota en ambos sitios: aquí el porqué, allí el qué.

---

## 2026-09-23 · Auditoría contra `REQUIREMENTS.md` y cierre de los huecos baratos

### It-11 · TLC corrigió la arquitectura: la liveness necesita equidad **fuerte**

**Causa.** Con el tope del juez puesto, TLC volvió a violar `Termina`. La traza: `AwaitApproval4 → RehacerWriting → WriteChapter → … → Checkpoint → AwaitApproval4`, indefinidamente. El Autor pide rehacer Writing para siempre.

**El diagnóstico.** §11d de la arquitectura afirmaba que la liveness vale «bajo hipótesis de **equidad débil** sobre su respuesta». Es falso, y TLC lo demostró. La equidad débil solo obliga a una acción que esté *continuamente* habilitada, y `Aprobar` en el gate de Writing no lo está: en cuanto el Autor pide rehacer, arranca el bucle de escritura y la aprobación queda deshabilitada durante decenas de estados.

**Qué se hizo.** `Spec` pasa de `WF_vars(AutorAprueba)` a `SF_vars(AutorAprueba)`. En castellano llano: *el Autor puede pedir que se rehaga tantas veces como quiera, pero no infinitas*, que es lo que se quería decir y no lo que se había escrito.

**Por qué es el hallazgo que más enseña.** Los otros tres gates no tienen el problema, porque rehacen fases que aún no han producido capítulos y la aprobación se rehabilita enseguida. Solo el de Writing intercala una computación larga entre dos oportunidades de aprobar. Esa asimetría es **invisible leyendo el documento** — y el documento llevaba meses escrito y había pasado varios grillings.

**Efecto medido.** Parcial: la reverificación con equidad fuerte es mucho más cara que con débil y quedó corriendo al cerrar la sesión. Lo verificado con certeza es que las tres violaciones anteriores desaparecieron y que el espacio explorado creció de 235 a 59.236 estados distintos.

### It-10 · Un tope que faltaba: los rechazos del juez

**Causa.** Corregido It-09, TLC violó `Termina` con el ciclo `Judge → AwaitApproval4 → Judge`: el Autor aprueba, el juez rechaza por no superar el umbral, y vuelta a empezar. Sin fin.

**Qué se hizo.** Se añade `rechazosJuez` con su constante `MaxRechazosJuez`, y una arista nueva `Judge → Fail` para cuando se agotan. Se propagó a §5 y §9 de la arquitectura.

**Por qué importa más de lo que parece.** Todo lo demás en este sistema está acotado: `intentos` por capítulo, `huecos` del arquitecto, `max_turns` por sesión. El bucle del juez era **el único sin tope**, y no porque alguien decidiera dejarlo abierto: porque nadie lo miró. Es justo la clase de omisión que sobrevive a una revisión humana —no hay nada escrito que esté mal, falta algo que nadie echa en falta— y que un explorador exhaustivo encuentra en tres segundos.

### It-09 · El primer contraejemplo: rehacer no era la pasada inicial

**Causa.** Primera ejecución de TLC. Violación de `ResumeIsExactlyOnce` en 35 estados: escritos y aprobados los cinco capítulos, el Autor pide rehacer en el gate de Writing y la ejecución vuelve a `WriteChapter` con `aprobados = {1..5}` y `capitulo = 5`. La pasada inicial exige `aprobados = 1..capitulo-1`.

**Qué se hizo.** El *rehacer* del gate de Writing se separa en la acción `RehacerWriting`, que entra en modo regeneración.

**La decisión que hubo que tomar.** Había dos formas de hacer desaparecer el error: estrechar el invariante para que no cubriera este caso, o arreglar el modelo. Se arregló el modelo, porque §8 ya decía que «rehacer, reanudar, ramificar y regenerar son la misma operación con distinto punto de entrada» — la máquina de estados era la que no lo reflejaba. Estrechar el invariante habría sido cambiar la pregunta para que la respuesta saliera bien.

**Efecto medido.** `ResumeIsExactlyOnce` deja de violarse sobre 42.145 estados distintos.

### It-08 · La auditoría volvió a quedarse obsoleta, y esta vez se vio venir

**Causa.** Mientras se cerraban los huecos documentales, el otro proceso completó el tramo **H1**: nueve ficheros de esquema SQL, `apertura.py`, `transaccion.py`, los repositorios y los triggers de `inmutabilidad.sql`. La suite pasó de 22 tests a **78**. Seis filas de la auditoría y tres párrafos de prosa quedaron mintiendo.

**Qué se hizo.** Se actualizaron treinta filas y los bloques de estado, y se añadió al aviso de cabecera la cuarta pasada. Los cambios de estado por H1 fueron `MEM-01`, `MEM-02`, `MEM-03` y `GR-02` a `CUMPLE`, y `LEC-10` a `PARCIAL`.

**El detalle que merece la pena retener.** `LEC-10` —conservar la versión anterior— pasa a `PARCIAL` por una razón agradable: `inmutabilidad.sql` instala triggers que abortan cualquier `UPDATE` sobre el texto de un capítulo **antes de que exista una sola regeneración que pudiera romperlo**. El cerrojo está puesto antes que aquello que encierra, que es el único orden en que un invariante de este tipo llega a existir. Puesto después, siempre hay una excepción que ya se coló.

**Efecto medido.** `python check_requirements.py` → `CUMPLE: 27 | MANUAL: 12 | NO_APLICA: 8 | NO_CUMPLE: 50 | PARCIAL: 9`, código 0. De 7 `CUMPLE` a 27.

### It-07 · Dos clases de `PARCIAL`, y por qué no se juntan

**Causa.** Al recontar los `PARCIAL` apareció que no todos significan lo mismo, y tratarlos igual daba una lista de trabajo engañosa.

**Qué se aprendió.** Hay dos patrones distintos:

- **«La constante existe y quien la aplica no»**: `HAR-07`, `HAR-08`, `VAL-04`, `HAR-01`, `LEC-10`. Se cierran solos al avanzar el plan. No hay que hacer nada con ellos.
- **«Está escrito y el entorno no deja ejecutarlo»**: `TLA-05` sin JVM, `LEAN-03` sin `lake`, `CC-02` sin Node. No se cierran trabajando más, **se cierran instalando tres herramientas**.

**Efecto.** El apartado final de la auditoría pasa a separarlos, y la lista de pendientes se ordena en tres montones por tipo de esfuerzo en vez de por familia de requisito. Es la información más accionable del documento y estaba enterrada.

### It-06 · Lo que se decidió NO marcar en verde

**Causa.** Tres requisitos podían haberse marcado `CUMPLE` con una interpretación generosa: `TLA-05` (el modelo está escrito, TLC no ha corrido), `LEAN-03` (el proyecto está, `lake` no existe) y `CC-02` (el MCP está configurado, nunca se ha levantado). Y `TLA-07` pedía contraejemplos de TLC que podrían haberse redactado de forma plausible.

**Qué se hizo.** Los tres quedan en `PARCIAL` y `TLA-07` en `NO_CUMPLE` con la tabla vacía. Se añadió a la auditoría un apartado que **nombra explícitamente dónde estuvo la tentación**.

**Por qué.** Un fichero `.tla` en el árbol no es una verificación. La distancia entre «especificado» y «verificado» es justamente lo que estos requisitos miden, y borrarla habría convertido la auditoría en su contrario: un documento que tranquiliza en vez de informar. Una auditoría cuyo autor tiene incentivo en que salga verde solo vale si se sabe dónde pudo hacer trampa.

**Efecto.** No medible, por definición. Es la clase de decisión cuyo efecto solo se ve cuando alguien confía en el documento seis meses después.

### It-05 · Especificación TLA+ escrita directamente en TLA+, no en PlusCal

**Causa.** `TLA-01` a `TLA-07` estaban todos en `NO_CUMPLE`: no existía ningún fichero `.tla` en el árbol. La arquitectura (§11d) los daba por diseñados desde hacía tiempo, con los cuatro invariantes ya nombrados, pero nadie los había escrito.

**Qué se hizo.** [`formal/tla/harness.tla`](../formal/tla/harness.tla), con las seis fases, la reanudación y la regeneración; los cuatro invariantes de §11d más `CorpusSelladoNoSeToca`; la liveness bajo equidad débil sobre la respuesta del Autor; y `harness.cfg` con el modelo pequeño de 5 capítulos y 2 reintentos.

**Desviación respecto a la arquitectura, y por qué.** §11d pide «PlusCal traducido a TLA+, con los `process` nombrados igual que los nodos». La especificación está escrita **directamente en TLA+**, con los nombres de los nodos como valores del contador de programa. El traductor de PlusCal no está disponible en el entorno, y una traducción mantenida a mano sería una segunda copia que puede divergir de su fuente — exactamente el problema que la definición `Aristas` existe para evitar. La forma directa conserva lo que la arquitectura quería de verdad, que es la correspondencia literal de nombres y una relación de transición explícita y única.

**Efecto medido.** Parcial, y conviene ser exacto: la especificación existe y es legible, pero **TLC no se ha ejecutado**. No hay JVM en la máquina (`java -version` → `command not found`), así que la garantía de este directorio es de clase **A por inspección**, no por *model checking*. `TLA-05` sigue sin cerrarse y `TLA-07` no tiene contraejemplos que registrar porque no ha habido ejecución que los produzca. Inventarlos habría sido peor que no tenerlos.

**Propagado.** La desviación subió a la arquitectura y dejó de serlo: §11d se reescribió entero —TLA+ directo, `Mueve(de, a)` sobre `Aristas`, los cinco invariantes de estado y `PreviousVersionPreserved` como propiedad temporal— y el cambio bajó a `verification.md`, a la spec y al plan del backend.

**Pendiente.** Ejecutar TLC en un entorno con JVM y anotar aquí lo que encuentre.

### It-04 · Una decisión de diseño en el propio modelo: `PublishVersion` sin guarda

**Causa.** Al escribir `NoPublishUnvalidated` apareció la tentación de poner la comprobación como guarda de la acción `PublishVersion`, que es lo que haría el código.

**Qué se hizo.** Se dejó `PublishVersion` **sin guarda** y se introdujo una variable de historia, `publicoSinValidar`, sobre la que se enuncia el invariante.

**Por qué.** Con la guarda, el invariante sería una tautología: comprobaría la guarda recién escrita en lugar de comprobar el grafo, y pasaría siempre aunque el cableado fuera un desastre. Sin ella, TLC explora si existe **algún** camino —por reintentos, por un gate que rehace, por una regeneración a medias— que llegue a publicar con un capítulo sin validar. Es la diferencia entre una prueba que interroga al sistema y una que se interroga a sí misma.

**Efecto.** El invariante pasa a tener contenido. Queda por comprobar cuando haya JVM.

### It-03 · Entregables de raíz: el repositorio no se podía usar

**Causa.** `ENT-01` estaba en `NO_CUMPLE` por tres ausencias que no dependían de escribir ni una línea de backend: no había `README.md`, no había `.env.example` en la raíz y no había brief de ejemplo. Sin brief, `ENT-06` —la novela de muestra reproducible— no tenía entrada con la que reproducirse, así que un requisito barato estaba bloqueando uno caro.

**Qué se hizo.** [`README.md`](../README.md) con la puesta en marcha, el brief de ejemplo y la tabla de correspondencia acción ↔ nodo ↔ efecto en SQLite; [`.env.example`](../.env.example) en la raíz; [`ejemplos/brief-ejemplo.yaml`](../ejemplos/brief-ejemplo.yaml) con los tres bloques del brief comentados uno a uno; y [`.mcp.json`](../.mcp.json) con el servidor de Playwright.

**Efecto medido.** `ENT-01` pasa de `NO_CUMPLE` a `PARCIAL` —queda la novela de muestra— y `CC-02` de `NO_CUMPLE` a `PARCIAL`: el servidor MCP está configurado, pero no se ha podido levantar porque no hay Node en el entorno (`npx` → `command not found`), así que no cuenta como verificado.

**Deuda que deja.** Hay ahora dos `.env.example`, uno en la raíz y otro en `backend/`, escritos por dos manos distintas. El de la raíz es el canónico y el `README` apunta a él. Unificarlos es trabajo del siguiente que toque `backend/`.

### It-02 · La auditoría se reescribió entera a mitad de camino

**Causa.** La primera pasada de la auditoría encontró `backend/` con diecinueve `__init__.py` vacíos; la segunda, cero ficheros; la tercera, el tramo H0 completo y en el *index* de git. Otro proceso estaba construyendo el backend en paralelo, y el documento recién escrito describía un repositorio que ya no existía.

**Qué se hizo.** Se reescribió [`docs/requirements-audit.md`](requirements-audit.md) entero contra el estado final, en lugar de parchear las filas afectadas, y se añadió al principio un aviso explícito de que el árbol se movió durante la auditoría y de que las evidencias corresponden a la última pasada.

**Por qué reescribir y no parchear.** Una auditoría es un documento cuyo valor entero está en que sus evidencias sean ciertas a la vez. Parchear doce filas y dejar las demás con la evidencia vieja produce un documento internamente inconsistente, que es peor que uno desactualizado: el lector no sabe qué parte creer.

**Efecto medido.** `python check_requirements.py` → `Requisitos: 106 | CUMPLE: 7 | MANUAL: 12 | NO_APLICA: 8 | NO_CUMPLE: 69 | PARCIAL: 10`, código de salida 0. Diez `PARCIAL` frente a los cinco de la primera pasada, todos por la misma razón: H0 aporta las constantes y los tipos, pero no todavía quien los aplica.

### It-01 · El hallazgo que ordenó todo lo demás

**Causa.** Al auditar los 106 requisitos apareció un patrón que no era casualidad: **lo que el enunciado verifica leyendo documentos estaba cubierto, y lo que verifica leyendo o ejecutando código no lo estaba en absoluto**. Los siete `CUMPLE` salían todos de `docs/` y de `.claude/skills/`; los sesenta y nueve `NO_CUMPLE`, de la misma causa única.

**Qué se aprendió.** Los `PARCIAL` no son medias tintas repartidas al azar, sino un patrón repetido con nombre propio: **la constante existe y quien la aplica no**. `HAR-07` tiene `REINTENTOS_POR_CAPITULO` y no el bucle; `HAR-08` tiene `TOKENS_CONCURRENTES_MAXIMOS` y no la guarda que rechaza la llamada; `VAL-04` tiene `RANGO_PALABRAS` y no el validador; `HAR-01` tiene los nueve roles como `StrEnum` y ningún agente detrás.

**Efecto.** Ese patrón fija el orden de trabajo: los cuatro se cierran casi solos cuando lleguen los tramos H1 a H7 del plan, así que no se tocan ahora. El esfuerzo se dirigió a lo que **no** depende del backend —entregables de raíz, `/docs`, TLA+, Lean y evals—, que además es lo que otro proceso no estaba escribiendo al mismo tiempo.

---

## Cómo se anota una iteración

Cuatro campos, y ninguno es opcional:

- **Causa.** Qué se observó. Un número, un fallo, una traza, una fila de la auditoría. No «parecía mejorable».
- **Qué se hizo.** El cambio, con enlace al fichero.
- **Efecto medido.** Qué dice la misma medida después. Si no se midió, se escribe que no se midió — que es un resultado, no una omisión.
- **Deuda o pendiente**, cuando el cambio deja algo abierto.

Las iteraciones que nacen de un contraejemplo de TLC se anotan además en [`formal/tla/README.md`](../formal/tla/README.md), con la traza. Las que nacen de un hallazgo de red-team, en [`red-team.md`](red-team.md).
