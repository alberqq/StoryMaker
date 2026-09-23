# Memoria y gestión de contexto

## El concepto

Un modelo no recuerda nada entre llamadas. Todo lo que «sabe» al escribir el capítulo 7 es lo que alguien le metió en el prompt. La gestión de contexto es la disciplina de decidir **qué entra**, y es donde se juega la mitad de la calidad de un sistema de generación larga.

Hay dos escuelas. En la de **recuperación**, el agente tiene herramientas de búsqueda y va a buscar lo que necesita. En la de **empuje**, alguien decide antes de invocarlo qué material le corresponde y se lo entrega montado.

## Cómo se aplica aquí

> **El agente recibe su contexto, no lo busca.**

El escritor no tiene herramientas de recuperación. Recibe un paquete de **siete bloques** ensamblado por código determinista, con un techo de tokens por bloque. La consecuencia es que el contexto de cualquier capítulo es reproducible: se puede volver a montar meses después y sale el mismo.

La escuela de recuperación tiene una ventaja real —el agente pide lo que le hace falta— y dos problemas que aquí pesaban más: el contexto deja de ser acotable *a priori*, y deja de ser auditable, porque lo que entró depende de qué decidió buscar el modelo ese día.

## La memoria

Toda vive en **un único fichero SQLite por novela**. Siete familias de tablas, y el checkpoint de LangGraph en el mismo fichero — que es la razón entera de que sea uno solo: el capítulo aprobado y el checkpoint se escriben **en la misma transacción**, así que no existe el instante en que el grafo cree que el capítulo 6 está hecho y la biblia no lo tenga.

Las piezas que hacen de memoria entre capítulos:

- **Resúmenes por capítulo** (`capitulo_version.resumen`), que alimentan el contexto de los siguientes.
- **Estado de continuidad** (`continuidad`): dónde está cada personaje, qué sabe, qué lleva encima al terminar el capítulo.
- **El índice hecho → capítulo** (`uso_hecho`), que no es memoria para escribir sino para **regenerar**: cuando el lector cambia un dato, dice exactamente qué capítulos hay que rehacer.

## El detalle que enseña más

`vec_resumen` —el índice semántico de los resúmenes— lleva una columna `vigente`, y la razón es sutil. De un mismo capítulo hay **varias** `capitulo_version`: los reintentos del bucle y las que deja cada regeneración. Sin filtrar por `vigente = 1`, el escritor del capítulo 7 podría recibir el resumen de un intento **rechazado** del capítulo 3.

Y sería un fallo silencioso, que es la peor clase: el capítulo 7 saldría bien escrito, coherente, sin que ningún validador se quejara — recordando algo que ya no está en la novela.

La lección general: en un sistema con reintentos e inmutabilidad, *toda* consulta que mire «lo que ya se escribió» necesita decir **cuál** de las versiones, y olvidarlo no rompe nada de forma visible.

## Los embeddings, y para qué no sirven

Son locales (FastEmbed sobre ONNX, 384 dimensiones) e indexados con `sqlite-vec` en el mismo fichero. No están para hacer búsqueda semántica bonita: **son la gestión de contexto**. Deciden qué porción del corpus investigado y de los resúmenes anteriores cabe en el paquete, cuando no cabe todo.

Que sean locales importa por dos motivos: no hay llamada de red en el camino crítico, y el resultado es determinista — el mismo texto produce el mismo vector, así que el mismo capítulo se monta igual dos veces.

## Dónde mirar

- Los siete bloques y sus techos: [`architecture.md` §6](../architecture.md#6-paso-de-contexto)
- El esquema completo, dibujado: [`diagramas.md`](../diagramas.md#esquema-sqlite)
