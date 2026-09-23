# Evals

## El concepto

Un test comprueba igualdad: dada esta entrada, sale esto. Con un modelo generativo eso no se puede hacer — la misma entrada produce texto distinto cada vez, y el texto distinto puede ser igual de bueno.

Una *eval* renuncia a la igualdad y comprueba otra cosa: que la salida **cae dentro de un sobre**. No «escribió exactamente esto», sino «no usó ninguna palabra prohibida», «cubrió los cinco elementos obligatorios», «la cronología cierra», «el juez le dio más de 7 en continuidad».

## Cómo se aplica aquí

**Cinco briefs**, que corren en modo batch con los cinco gates desactivados — sin eso, cada ejecución pediría cinco aprobaciones y la tabla de resultados no se terminaría nunca. De ahí que `gates.enabled = false` no sea una comodidad sino una pieza del plan de evaluación.

Los cinco no se eligieron por representativos. Se eligieron por **incómodos**:

| Brief | Qué tensa |
|---|---|
| `01-caso-base` | El camino feliz, para tener línea base |
| `02-injection` | Texto libre con instrucciones embebidas |
| `03-incoherencia-temporal` | Fechas que no pueden ser a la vez |
| `04-prohibidas-dificiles` | Palabras prohibidas con derivados y variantes |
| `05-cobertura-imposible` | Más elementos obligatorios de los que caben |

El quinto es el más interesante y el menos obvio: pide cubrir más material del que cabe en diez capítulos. **No se espera que pase.** Se espera que *falle bien*: que `cobertura_anclada` lo detecte en el gate de Plotting —cuando cuesta un `SELECT`— y no después de escribir y pagar diez capítulos.

Esa es la diferencia entre una eval que mide calidad y una que mide **diseño**: la primera pregunta si la novela es buena, la segunda si el sistema se entera pronto de que no puede hacerla.

## Qué se mide por brief

Una tabla por ejecución: qué validadores pasan y cuáles fallan, **con números** — cuántos intentos por capítulo, cuántas incidencias por validador, qué puntuó el juez en cada criterio, cuánto costó. Sin números no hay antes/después, y sin antes/después no hay tuning: hay cambios de prompt y una sensación.

## La trampa de las evals con juez

El juez de las evals es el mismo modelo que escribe. Eso sesga, y no hay forma de que no sesgue. Dos mitigaciones, ninguna completa:

1. El juez **no puede tocar el texto**, así que no puede optimizar aquello que califica.
2. Una novela de la tanda se revisa **a mano con la misma rúbrica**, y se compara con lo que dijo el juez. Esa comparación es la que dice cuánto vale el resto de las puntuaciones.

Si el juez y la persona discrepan mucho, las puntuaciones del juez no sirven para comparar tandas — y eso es un resultado, no un fallo de la eval.

## El estado real

Los cinco briefs están escritos en [`evals/`](../../evals/). **Ninguno se ha ejecutado**: el arnés no corre todavía de punta a punta, así que no hay tabla de resultados ni iteración de tuning que documentar.

Se dice claro porque un directorio `evals/` con ficheros dentro se lee como si hubiera evaluación. Hay **casos de prueba**; no hay evaluación. [`requirements-audit.md`](../requirements-audit.md) lo distingue fila por fila (EVAL-01 a EVAL-03 frente a EVAL-04 y EVAL-05).

## Dónde mirar

- Los briefs y su lectura: [`evals/README.md`](../../evals/README.md)
- El marco de confianza que clasifica esto como **T/I**: [`verification.md` §4.2](../verification.md)
