# Evaluación del sistema

Cinco briefs que se pasan al arnés en modo batch y una tabla de resultados por cada uno.

> **Estado: escritos, no ejecutados.** El arnés no corre todavía de punta a punta, así que aquí hay **casos de prueba**, no evaluación. No hay tabla de resultados ni iteración de tuning que enseñar, y no se va a rellenar con números inventados. [`docs/requirements-audit.md`](../docs/requirements-audit.md) lo distingue: EVAL-01 a EVAL-03 se cubren con estos ficheros; EVAL-04 y EVAL-05 necesitan ejecución.

## Cómo se corren

```bash
cd backend
uv run storymaker eval --todos --batch
```

`--batch` desactiva los cinco gates. Sin eso, cada brief pediría cinco aprobaciones al Autor y la tabla no se terminaría nunca; por eso `gates.enabled = false` es una pieza del plan de evaluación y no una comodidad.

## Los cinco

No se eligieron por representativos. Se eligieron por **incómodos**: cada uno tensa una parte distinta del sistema, y tres de los cinco se espera que *fallen*, porque lo que miden es si el sistema se entera a tiempo.

| Brief | Tensa | Resultado esperado |
|---|---|---|
| [`01-caso-base.yaml`](briefs/01-caso-base.yaml) | Nada. Es la línea base | Publica. Todos los validadores en verde |
| [`02-injection.yaml`](briefs/02-injection.yaml) | La defensa contra *prompt injection* del texto libre | Publica, y **ninguna instrucción embebida se ejecuta** |
| [`03-incoherencia-temporal.yaml`](briefs/03-incoherencia-temporal.yaml) | La detección de contradicciones y el validador Lean | **Para en el gate de Intake**, con la contradicción explicada |
| [`04-prohibidas-dificiles.yaml`](briefs/04-prohibidas-dificiles.yaml) | La normalización de palabras prohibidas | Publica sin ninguna variante prohibida, o se detiene tras agotar reintentos |
| [`05-cobertura-imposible.yaml`](briefs/05-cobertura-imposible.yaml) | La cobertura de elementos obligatorios | **Falla en el gate de Plotting**, no después de escribir diez capítulos |

### Por qué el 05 es el más útil

Pide cubrir más material del que cabe en diez capítulos. No se espera que pase: se espera que **falle bien**.

Si `cobertura_anclada` lo detecta en el gate de Plotting, el fallo cuesta un `SELECT` y una escaleta. Si no lo detecta y el fallo aparece en `cobertura_personalizacion` al cerrar Writing, cuesta diez capítulos escritos y pagados. El brief mide la distancia entre esos dos sitios, que es una propiedad del **diseño**, no de la calidad de la prosa.

### Por qué el 03 debe parar antes de escribir nada

Lleva una contradicción entre la fecha de nacimiento del homenajeado y el período: nace en 1831 y la novela transcurre entre 1803 y 1806. El `@model_validator` del brief tiene que verla **en Intake**, traducirla a una pregunta y obligar a resolverla.

Si en cambio la novela se escribe y la incoherencia la caza Lean al final, el sistema funciona pero funciona caro. La eval distingue los dos casos.

## Qué se anota por ejecución

Una tabla por brief, con números y no con adjetivos:

- Qué validadores pasan y cuáles fallan, y cuántas incidencias produce cada uno
- Intentos por capítulo, y cuántos llegaron al tope
- Puntuación del juez por criterio, los siete
- Coste: tokens de entrada y salida, dinero, y en qué fase se fue
- Dónde se detuvo, si se detuvo

Sin números no hay antes/después, y sin antes/después no hay tuning: hay cambios de prompt y una sensación.

Los resultados van en `evals/resultados/<fecha>/`, y la iteración que provoquen se anota en [`docs/iteraciones.md`](../docs/iteraciones.md).

## La trampa conocida

El juez de estas evals es el mismo modelo que escribe la novela. Eso sesga y no hay forma de que no sesgue. Lo que lo acota: el juez **no puede tocar el texto**, y una novela de cada tanda se revisa a mano con la misma rúbrica para comparar. Esa comparación es la que dice cuánto valen las demás puntuaciones — y si juez y persona discrepan mucho, eso también es un resultado.
