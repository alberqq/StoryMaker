# Verificación formal

## El concepto

Un test comprueba que el sistema hace lo correcto **para las entradas que el test prueba**. Un método formal comprueba una propiedad **para todos los casos posibles**, razonando sobre el modelo en lugar de ejecutarlo. La diferencia no es de rigor: es de cuantificador.

El precio es que hay que escribir el modelo, y el modelo puede no parecerse al sistema. Un invariante demostrado sobre una especificación que no corresponde al código no demuestra nada sobre el código.

## Cómo se aplica aquí

Dos herramientas para **dos superficies de riesgo distintas**, y conviene no confundirlas:

| | Lean 4 | TLA+ / TLC |
|---|---|---|
| Verifica | **La historia** | **El sistema** |
| Pregunta que responde | ¿Es coherente la cronología de esta novela? | ¿Hay algún entrelazado que rompa el arnés? |
| Entrada | La cronología de *una* novela concreta | El modelo del comportamiento, sin novela |
| Cuándo corre | En el flujo, antes de publicar | En desarrollo, no en cada generación |

### Lean: la historia

De las tablas `cronologia_*` se genera un fichero Lean con los eventos, su momento, sus participantes y su lugar. Sobre eso se enuncian invariantes: nadie participa en un evento antes de nacer o después de morir, nadie está en dos lugares a la misma hora, ningún objeto aparece antes de existir.

La gracia de que el dominio sea **novela histórica** es que estas propiedades tienen materia real. Las fechas históricas son duras y comprobables; en una novela contemporánea inventada no habría nada contra lo que contrastar.

Y la tabla `cronologia_evento` mezcla a propósito eventos `historico` y `narrativo` en la misma tabla. **Es en esa mezcla donde aparecen las incoherencias interesantes**: el personaje inventado que asiste a Trafalgar tres días antes de que ocurra. Un validador semántico no lo ve; un juez humano tampoco, salvo que vaya con un calendario.

### TLA+: el sistema

TLC explora exhaustivamente los estados alcanzables de un modelo pequeño —5 capítulos, 2 reintentos— y, si encuentra una violación, devuelve el **contraejemplo**: la secuencia exacta de pasos que rompe el invariante.

Los cuatro invariantes dicen lo que nunca puede pasar: no publicar sin validar, no duplicar ni perder capítulos al reanudar, no perder la versión anterior al regenerar, no exceder el límite de reintentos.

## El detalle que justifica el esfuerzo

`Repair` tiene **dos aristas de entrada** —desde `Validate` y desde `Extract`— que comparten un único contador de intentos. Esa es la clase de interacción que un humano no detecta leyendo el código: cada camino, por separado, respeta el límite. La pregunta es si algún entrelazado de los dos lo excede.

Justamente por eso `Extract` se modela como acción propia y no se pliega dentro de `Validate`: plegarla dejaría el modelo sin comprobar lo único que ese cambio introdujo. El coste es un estado más en un modelo que ya se verifica en minutos.

## La honestidad sobre el estado actual

Ninguna de las dos se ha ejecutado en este repositorio. No hay `lake` ni JVM en el entorno de desarrollo (`lake` → *command not found*, `java` → *command not found*). Las especificaciones están escritas; las garantías son de clase **A por inspección**, no por demostración ni por *model checking*.

Es una distinción que conviene mantener viva, porque un directorio `formal/` con ficheros dentro se lee como si algo estuviera verificado. Está *especificado*. No es lo mismo, y [`requirements-audit.md`](../requirements-audit.md) lo dice fila por fila.

## Dónde mirar

- [`formal/tla/README.md`](../../formal/tla/README.md): los invariantes, la liveness bajo equidad débil, y por qué `PublishVersion` no lleva guarda
- [`formal/lean/README.md`](../../formal/lean/README.md): los invariantes de la cronología
- [`architecture.md` §11c y §11d](../architecture.md#11-validación)
