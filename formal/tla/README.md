# Verificación formal del arnés — TLA+ / TLC

[`harness.tla`](harness.tla) especifica **cómo se comporta el arnés**, no qué escribe. Modela las seis fases, la caída del proceso y la reanudación desde checkpoint, el reintento manual de un capítulo, el rechazo de la publicación y la regeneración por cambio del lector, y declara **cinco invariantes de estado** —`TypeOK`, `NoPublishUnvalidated`, `ResumeIsExactlyOnce`, `RetriesBounded` y `CorpusSelladoNoSeToca`— y **dos propiedades temporales** —`PreviousVersionPreserved` y la liveness `Termina`— que TLC comprueba explorando exhaustivamente los estados alcanzables de un modelo pequeño.

Verifica una superficie de riesgo distinta a la de Lean. Lean comprueba que **la historia** es coherente —que nadie nace después de morir—; TLC comprueba que **el sistema** lo es: que no hay ningún entrelazado de reintentos, gates y regeneraciones que acabe publicando una versión sin validar o perdiendo un capítulo al reanudar.

## Cómo se corre

TLC necesita una JVM y `tla2tools.jar`, que no están en el repositorio.

```bash
# Con la JVM y tla2tools.jar disponibles:
java -XX:+UseParallelGC -cp tla2tools.jar tlc2.TLC -workers auto -config harness.cfg harness.tla
java -XX:+UseParallelGC -cp tla2tools.jar tlc2.TLC -workers auto -config harness_batch.cfg harness.tla

# O con la skill `tlaplus` de .claude/skills/, que envuelve lo anterior:
.claude/skills/tlaplus/scripts/tlc.sh formal/tla/harness.tla
```

**Resultado.** Con TLC 2026.09.23 sobre un JRE 21 portátil, las dos configuraciones agotan su espacio de estados sin ninguna violación de los cinco invariantes ni de las dos propiedades temporales:

| Configuración | Modo | Estados generados | Distintos | Profundidad | Tiempo |
|---|---|---|---|---|---|
| `harness.cfg` | Interactivo, equidad fuerte sobre el Autor | 22.349 | 12.650 | 71 | 1 s |
| `harness_batch.cfg` | Batch | 7.029 | 4.425 | 66 | 1 s |

**La comprobación de `Termina` no es vacía.** Cambiando en una copia `SF_vars(AutorAprueba)` por `WF_vars(AutorAprueba)`, TLC viola `Termina` con la traza ya conocida: el Autor rehace Writing, se reescriben los capítulos, se vuelve al gate y se rehace otra vez. Es la mutación que confirma que la equidad fuerte es la que sostiene la propiedad, y no una configuración que no llega a explorar nada.

**Por qué ahora termina y antes no.** El modelo anterior no era finito: `versiones` es una secuencia *append-only* y el lector podía pedir cambios sin límite, así que cada regeneración abría un estado nuevo y TLC corría con la cola estable y la profundidad creciendo. La cota `MaxCambiosLector` lo hace finito, y con ella la liveness cabe también en el modelo de cinco capítulos: no hace falta separarla en otro más pequeño.

## El modelo

`harness.cfg` fija **5 capítulos y 2 reintentos**, con una caída del proceso, un reintento manual y un cambio del lector. Es pequeño a propósito: lo que se verifica no depende del tamaño —que `Repair` tenga dos aristas de entrada compartiendo un único contador de intentos se ve igual con cinco capítulos que con diez— y el espacio de estados crece deprisa con `NCapitulos`.

### El entorno, acotado

Además del Autor, tres cosas que no son del arnés mueven el modelo, y cada una lleva su constante:

| Acción | Qué es en el código | Constante |
|---|---|---|
| `Caida` y `ResumeFromCheckpoint` | El proceso muere en cualquier nodo que no sea un reposo, y `storymaker continuar` lo reanuda con `Command(resume=...)`. Mientras está muerto, `Mueve` no deja pasar nada. Reanudar no toca más que `vivo`: el checkpoint se escribe en la misma transacción que las filas de dominio, así que lo no confirmado no existe | `MaxCaidas` |
| `Reintentar` | `storymaker reintentar`: reabre el capítulo que agotó sus reintentos escribiendo el checkpoint *como salida de `SealCorpus`*. Por eso exige la arista `SealCorpus → WriteChapter` y no una `Fail → WriteChapter`, que no existe. Solo cabe si el capítulo en curso no está validado | `MaxReintentos` |
| `IdleRequest` | Una petición del lector, que `regenerar` escribe como salida de `Idle`. Pone a cero los rechazos | `MaxCambiosLector` |

Lo que TLC comprueba con ellas es que una caída en cualquier punto —a mitad de un capítulo, entre reintentos, dentro de una regeneración— y un reintento manual dejan intactos los invariantes, en particular `ResumeIsExactlyOnce`.

### El rechazo de la publicación

`PublishVersion` tiene tres ramas: publica y va a `Idle`; rechaza, con rechazos disponibles, y vuelve a `AwaitApproval4`; o rechaza sin ellos y va a `Fail`. El rechazo no añade nada a `versiones`, y comparte contador con el juez. `RehacerWriting` elige un capítulo aprobado —en el código, los que citan las incidencias— y lo saca de `validados`, de modo que `NoPublishUnvalidated` notaría cualquier camino que publicara la versión nueva sin pasar por `Extract`.

### Los dos modos

`GatesActivos` distingue los dos modos. En **interactivo** el Autor se modela como un proceso de entorno no determinista que en cada gate puede aprobar, pedir que se rehaga o abortar. En **batch** (`GatesActivos = FALSE`, que es `gates.enabled = false` en el código) no hay a quién esperar.

## Los invariantes

| Nombre | Enunciado | Por qué existe |
|---|---|---|
| `NoPublishUnvalidated` | Nunca se publica una versión que contenga un capítulo que no pasó todos los validadores | Es G5, la puerta que no admite excepción |
| `ResumeIsExactlyOnce` | La reanudación desde checkpoint no duplica ni pierde capítulos | El checkpoint y el capítulo se escriben en la misma transacción justamente para que esto sea cierto; el invariante lo comprueba |
| `PreviousVersionPreserved` | Tras una regeneración, la versión anterior sigue siendo íntegramente recuperable | Los capítulos son inmutables y hay manifiesto, de modo que conservar es estructural; el invariante comprueba que ninguna acción rompe esa estructura |
| `RetriesBounded` | El número de reintentos por capítulo nunca supera el límite | `Repair` tiene **dos** aristas de entrada, desde `Validate` y desde `Extract`, que comparten un único contador. Esa es exactamente la clase de interacción que un humano no verifica leyendo |
| `CorpusSelladoNoSeToca` | Después del sello, ningún nodo vuelve a escribir en el corpus histórico | Durante Writing solo se puede anclar a hechos existentes o declarar una Licencia; si se pudiera añadir un hecho, el sello no significaría nada |

`TypeOK` acompaña a los cinco como invariante de tipos.

### Sobre `NoPublishUnvalidated` y por qué `PublishVersion` no lleva guarda

`PublishVersion` **no comprueba** que todos los capítulos estén validados antes de publicar, y es deliberado. Si llevara esa guarda, el invariante sería una tautología: comprobaría la guarda recién escrita en lugar de comprobar el grafo. Sin ella, TLC explora si existe **algún** camino —por reintentos, por un gate que rehace, por una regeneración a medias— que llegue a publicar con un capítulo sin validar. Esa es la pregunta que el invariante hace, y la única forma de que la respuesta signifique algo.

El mecanismo es una variable de historia, `publicoSinValidar`, que se pone a `TRUE` si alguna publicación incluyó un capítulo fuera de `validados`. El invariante dice que esa variable nunca se enciende.

## La liveness

`Termina` dice que toda generación acaba publicando una versión, ramificando o parándose con error.

En **batch** la propiedad es directa. En **interactivo** vale bajo la **equidad fuerte** que `Spec` declara sobre `AutorAprueba`: *el Autor puede pedir que se rehaga tantas veces como quiera, pero no infinitas*.

Que haga falta una hipótesis no es un truco para esquivar el requisito: es la forma correcta de especificar un sistema con intervención humana bloqueante. Sin ella la propiedad es sencillamente falsa —el Autor puede no contestar nunca, y §10 de la arquitectura contempla ese caso con un *timeout*— y no hay diseño que la salve.

Que la hipótesis tenga que ser **fuerte** y no débil lo descubrió TLC, y se explica en «débil no basta», más abajo.

## `Aristas`, y por qué la tabla del README no es una narración

Las transiciones se declaran **una sola vez**, en la definición `Aristas`, y todas las acciones mueven el `pc` a través del mismo operador:

```tla
Mueve(de, a) ==
    /\ pc = de
    /\ <<de, a>> \in Aristas
    /\ pc' = a
```

De ahí que `Aristas` **gobierne** el `Next` que TLC explora en lugar de solo acompañarlo. Eso es lo que permite que la prueba de identidad `identidad_nodo_accion` compare el conjunto de aristas del `StateGraph` de LangGraph contra esta definición y esté comparando cableado, no solo nombres — y contra la relación que TLC verificó de verdad, no contra una tercera copia mantenida a mano.

Importa porque un grafo con las veintiuna acciones bien nombradas y el cableado equivocado pasaría una comparación de conjuntos de nombres sin parecerse en nada al modelo verificado: lo que TLC explora son transiciones.

La correspondencia acción ↔ nodo ↔ efecto en SQLite está en el [README raíz](../../README.md#la-correspondencia-entre-la-especificación-formal-y-el-código).

## Registro de contraejemplos

Cuando TLC se ejecute, cada contraejemplo que encuentre se anota aquí con la traza que lo produjo y el cambio de código o de modelo que provocó, y se referencia desde [`docs/iteraciones.md`](../../docs/iteraciones.md).

| Fecha | Propiedad violada | Traza (resumen) | Qué se cambió |
|---|---|---|---|
| 2026-09-23 | `ResumeIsExactlyOnce` | 35 estados. Se escriben y aprueban los 5 capítulos, se llega a `AwaitApproval4`, y el Autor pide **rehacer**. La ejecución vuelve a `WriteChapter` con `aprobados = {1..5}` y `capitulo = 5`, cuando la pasada inicial exige `aprobados = 1..capitulo-1` | **El modelo, no el invariante.** El *rehacer* del gate de Writing se trataba como pasada inicial, y §8 dice que «rehacer, reanudar, ramificar y regenerar son la misma operación». Se separa en la acción `RehacerWriting`, que entra en modo regeneración |
| 2026-09-23 | `Termina` (1ª vez) | El ciclo `Judge → AwaitApproval4 → Judge`, indefinido: el Autor aprueba cada vez y el juez vuelve a rechazar | **Un tope que faltaba en el sistema.** Nada acotaba los rechazos del juez, mientras `intentos` y `huecos` sí lo estaban. Se añade `rechazosJuez` con su `MaxRechazosJuez`, y la arista `Judge → Fail` cuando se agotan |
| 2026-09-23 | `Termina` (2ª vez) | El ciclo `AwaitApproval4 → RehacerWriting → WriteChapter → … → Checkpoint → AwaitApproval4`: el Autor rehace Writing para siempre | **La hipótesis de equidad estaba mal elegida.** Ver abajo |

Con el modelo ampliado —caída, reanudación, reintento manual, rechazo de la publicación y entorno acotado— TLC no ha encontrado ningún contraejemplo nuevo. Lo que sí cambió al ampliarlo fue la finitud del modelo, que se cuenta arriba en «Por qué ahora termina».

### La corrección que más enseña: débil no basta

§11d de la arquitectura decía que la liveness vale «bajo hipótesis de **equidad débil** sobre su respuesta». TLC demostró que es falso.

La equidad débil solo obliga a una acción que esté **continuamente** habilitada. `Aprobar` en el gate de Writing no lo está: en cuanto el Autor pide rehacer, arranca el bucle de escritura y la aprobación queda deshabilitada durante decenas de estados. Weak fairness no tiene nada que decir sobre una acción que se habilita y se deshabilita alternativamente, así que la traza del Autor que rehace eternamente es admisible bajo `WF`.

La hipótesis correcta es la **equidad fuerte**: si la aprobación está habilitada infinitas veces, acaba ocurriendo. En castellano llano, *el Autor puede pedir que se rehaga tantas veces como quiera, pero no infinitas* — que es exactamente lo que se quería decir y no lo que se había escrito.

Lo interesante es dónde estaba escondido. Los otros tres gates no tienen el problema, porque rehacer una fase que aún no ha producido capítulos vuelve a habilitar la aprobación enseguida. Solo el gate de Writing intercala una computación larga entre dos oportunidades de aprobar, y esa asimetría es invisible leyendo el documento.

El cambio está en `Spec`, y se ha propagado al registro de cambios de `docs/architecture.md`.

## Cómo llegó esta forma a la arquitectura

Esta especificación nació como **desviación**: §11d pedía «PlusCal traducido a TLA+, con los `process` nombrados igual que los nodos», y está escrita directamente en TLA+, con los nombres de los nodos como valores del contador de programa. El motivo fue que el traductor de PlusCal no está disponible en el entorno, y una traducción escrita a mano sería una segunda copia que puede divergir de su fuente: exactamente el problema que `Aristas` existe para evitar.

**Ya no es una desviación.** La arquitectura adoptó la forma directa y reescribió §11d entero, así que lo que este directorio contiene es lo que la fuente de verdad pide. El recorrido —desviación, registro, propagación hacia arriba— queda en [`docs/iteraciones.md`](../../docs/iteraciones.md), que es donde vive esa clase de historia.
