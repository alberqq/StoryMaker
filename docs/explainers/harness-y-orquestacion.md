# Harness y orquestación

## El concepto

Un *harness* multiagente es el código que rodea a los modelos: decide qué rol se invoca, con qué contexto, con qué herramientas, cuántas veces puede reintentar y cuándo hay que parar a preguntarle a una persona. El modelo escribe; el arnés gobierna.

La tentación del diseño ingenuo es dejar que los agentes se coordinen entre sí — un agente «orquestador» que decide a quién llamar. Funciona en la demo y se desmorona en cuanto algo falla, porque el plan de ejecución vive en el prompt de alguien y no hay dónde mirarlo.

## Cómo se aplica aquí

**El orquestador es un grafo de estado explícito** (LangGraph), no un agente. Cada acción es un nodo con nombre, las transiciones son aristas, y las condicionales leen booleanos de Python. Ningún modelo decide el flujo.

Los **nueve roles** son invocaciones del Claude Agent SDK, todos en Haiku 4.5, con modelo, herramientas y turnos fijados por invocación:

| Rol | Hace | No puede |
|---|---|---|
| Entrevistador | Pregunta solo lo que falta del brief | Inventar campos |
| Extractor de intake | Convierte texto libre en filas tipadas | Dejar pasar el texto crudo al resto |
| Investigador | Busca en internet y guarda hechos con su cita | Escribir novela |
| Verificador | Dictamina si la cita sostiene el enunciado | Añadir hechos al corpus |
| Arquitecto | Decide premisa, tema, personajes, arcos y escaleta | Tocar el corpus tras el sello |
| Escritor | Escribe el capítulo | Buscar nada: recibe su contexto |
| Editor | Repara lo que los validadores marcaron | Calificar su reparación |
| Extractor de capítulo | Mide qué hechos y qué hitos se usaron | Escribir |
| Juez | Puntúa con la rúbrica | Tocar el texto |

**Ninguno tiene `Bash`, `Write` ni acceso al disco.** Solo el investigador tiene herramientas, y son las dos de red.

## Las tres restricciones que dan forma a todo

**El presupuesto de contexto se garantiza por construcción.** El límite son 100.000 tokens concurrentes, y el Agent SDK no ofrece forma documentada de consultar cuánto lleva consumido una sesión mientras corre. Así que no se vigila: se acota *a priori*, con un techo declarado por rol y una guarda que rechaza la llamada antes de emitirla si el prompt ensamblado lo excede. Cuando no puedes medir, acotas.

**Los reintentos viven en el estado del grafo, no en el prompt.** Un agente al que se le *pide* que no pase de dos intentos pasa de dos intentos. Un contador en el estado, leído por una arista condicional, no.

**La invocación termina en cada gate.** No queda un hilo esperando ni una sesión abierta: el grafo persiste su checkpoint y devuelve el control. La máquina duerme en disco mientras espera al Autor, que puede tardar un día. Reanudar es volver a invocar con el checkpoint.

## Lo que más cuesta entender de primeras

Que **rehacer, reanudar, ramificar y regenerar sean la misma operación** con distinto punto de entrada. Todas son «invocar el grafo desde un checkpoint», y las ejecuciones de fase son inmutables, así que rehacer Plotting no borra el Plotting anterior: crea otro, y el vigente es el último. Eso es lo que permite comparar dos ramas de la misma novela, porque ambas parten del mismo corpus sellado.

## Dónde mirar

- La topología y los nueve roles: [`architecture.md` §3 y §5](../architecture.md#3-topología)
- La máquina de estados, y su forma verificable: [`architecture.md` §9](../architecture.md#9-máquina-de-estados) y [`formal/tla/harness.tla`](../../formal/tla/harness.tla)
