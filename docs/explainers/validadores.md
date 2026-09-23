# Validadores

## El concepto

Un sistema que genera texto con un modelo tiene que decidir **quién dice que el texto está bien**. Las opciones habituales son tres: que lo diga el propio modelo, que lo diga otro modelo, o que lo diga código determinista. La mayoría de los sistemas reales mezclan las tres, y la pregunta interesante no es cuál se usa sino **quién decide cuándo se usa**.

## Cómo se aplica aquí

La decisión de la que cuelga todo el diseño de StoryMaker cabe en una frase:

> **Los validadores son nodos del grafo, no herramientas que un agente elige llamar.**

Es la diferencia entre una comprobación y una sugerencia. Si `guardrail_prohibidas` fuera una *tool* que el escritor puede invocar, su ejecución dependería de que un modelo se acuerde — y un modelo que se olvida de llamarla produce exactamente el mismo texto que uno que decide no llamarla. Siendo un nodo, se ejecuta porque el grafo pasa por ahí, y las aristas condicionales que deciden si el capítulo avanza leen **booleanos calculados en Python**, no la opinión de nadie.

Esto sube la garantía de «el validador siempre corre» de clase **T** (hay una prueba que lo comprueba) a clase **A** (está garantizado por construcción). Y el plan de verificación tiene una regla sobre eso: *A vence a T cuando ambas son posibles*. Lo que se puede garantizar por construcción no se deja al criterio de una prueba que alguien puede borrar.

## Las tres capas

**Deterministas.** Once, y comprueban todos lo mismo: el texto contra una fila de la base de datos. `nombres_exactos` compara con `canon_personaje`; `longitud_capitulo`, con el rango del brief; `anacronismo_fechado`, con `mundo_entidad.fecha_inicio`. Son baratos, no fallan de forma distinta dos veces, y dan la respuesta en milisegundos.

Dos de ellos existen solo porque el dominio es histórico —`anacronismo_fechado` y `anclaje_valido`— y son los que llevan el sistema bastante por encima del mínimo que un proyecto así suele tener. Es el argumento de elegir bien el dominio: una novela contemporánea no tendría nada que comprobar de forma determinista.

**Semánticos.** Un juez con una rúbrica de siete criterios, que puntúa lo que no se puede calcular: continuidad, tono, calidad narrativa, si la personalización suena natural o pegada con cola. No puede tocar el texto. Su única salida es un esquema de puntuaciones.

**Humana.** El Autor, en cinco gates, con la misma rúbrica que el juez y sin poder editar tampoco. Ocupa exactamente el asiento del juez, lo que permite comparar ambas valoraciones y saber cuánto vale la del juez.

## La separación que parece burocrática y no lo es

**El editor repara dentro del bucle. El juez mide fuera y no puede tocar el texto.** Son dos agentes distintos y no es negociable: si los fusionas, el mismo agente que optimiza la métrica es el que la produce, y las puntuaciones dejan de significar nada.

El mismo argumento se repite tres veces en el sistema, y conviene verlo como un patrón y no como tres reglas sueltas:

- El **editor** no es el **juez**, porque quien repara no puede calificar su reparación.
- El **investigador** no es el **verificador**, porque quien trae la cita no puede dictaminar si la cita sostiene lo que afirma.
- El **escritor** no es el **extractor**, porque si el escritor declarase qué hechos usó, la cobertura se mediría sobre el testimonio de quien tiene interés en decir que los usó todos.

## El detalle que más se aprende

La cobertura de los elementos obligatorios del brief se comprueba **tres veces**, y cada una cuesta menos que la siguiente:

1. `cobertura_anclada`, en el gate de Plotting: ¿está cada elemento obligatorio anclado a alguna escena? Un `SELECT`. Convierte un fallo de diez capítulos escritos y pagados en un fallo de escaleta.
2. `cobertura_capitulo`, al escribir el capítulo N: ¿apareció lo que la escaleta le encomendó? Convierte un fallo de novela en un reintento de capítulo.
3. `cobertura_personalizacion`, en el gate de Writing: red de seguridad.

No es redundancia. Las tres miran cosas distintas, porque **anclar no es escribir**, y haber escrito el capítulo N no garantiza que ningún otro se quedara sin su parte. La lección general: cuando una comprobación cara puede adelantarse a un punto donde es barata, se adelanta *y se deja también la cara*.

## Dónde mirar

- La tabla completa, con punto de ejecución de cada validador: [`architecture.md` §11](../architecture.md#11-validación)
- Por qué cada uno tiene la clase de confianza que tiene: [`verification.md`](../verification.md)
