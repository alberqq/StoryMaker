# Observabilidad

## El concepto

Un sistema con nueve roles, reintentos y gates humanos produce, por cada novela, decenas de llamadas al modelo repartidas en días. Cuando algo sale mal —o sale caro— la pregunta no es «¿qué falló?» sino «¿dónde miro?». La observabilidad es la disciplina de que esa pregunta tenga respuesta.

En sistemas con LLM hay tres cosas que medir y se confunden a menudo: **qué pasó** (trazas), **cuánto costó** (tokens, dinero, latencia) y **qué tal salió** (scores).

## Cómo se aplica aquí

Langfuse, con la semántica puesta por el orquestador y no por la librería:

- **Sesión = novela.** Todo lo que pertenece a la misma novela cuelga de la misma sesión: la entrevista, las seis fases, y las regeneraciones que lleguen meses después.
- **Traza = generación.**
- **Span = rol, capítulo o intento.**

Que la semántica la ponga el orquestador es el punto. La instrumentación automática produce spans por llamada HTTP, que es verdad y no sirve: nadie se pregunta «¿cuánto costó esa petición?», se pregunta «¿cuánto costó el capítulo 7, contando sus tres intentos?».

## Lo que se mide

**Coste**, en tres granularidades —llamada, capítulo, novela—, porque son tres decisiones distintas: si un rol está mal calibrado, si un capítulo se atascó, si el producto es rentable. La tabla `fase_run` guarda `tokens_in`, `tokens_out` y `coste_usd` de cada ejecución de fase, así que el dato vive también en el fichero de la novela y no solo en Langfuse.

**Scores de todos los validadores.** Los once deterministas, el juez y Lean emiten su resultado como score en la traza. Eso permite la pregunta que de verdad importa al afinar: *¿qué validador falla más, y en qué capítulos?*

**Prompts versionados.** Los prompts de rol viven **en Langfuse como fuente de verdad** y se inyectan como `system_prompt`; el id de versión viaja en el span. Es lo que permite cambiar un prompt sin tocar el repositorio y ver el efecto en las métricas — el requisito real detrás de «la iteración de tuning muestra qué versión de prompt produjo cada resultado».

Las *skills* y `CLAUDE.md`, que Claude Code carga por su cuenta desde el disco, se quedan en el repositorio y se registran por su hash.

## La decisión que hace que los números signifiquen algo

**El editor y el juez son dos agentes distintos, y esto no es negociable.**

El editor pertenece al bucle de control: su trabajo es arreglar lo que los validadores marcaron. El juez pertenece a la capa de observabilidad: su trabajo es puntuar. Si se fusionan, **el mismo agente que optimiza la métrica es el que la produce**, y las puntuaciones dejan de medir la novela para medir la capacidad del agente de darse el visto bueno.

Es el problema de la ley de Goodhart, resuelto por separación de roles en lugar de por buena voluntad. Y tiene un efecto secundario útil: la revisión humana ocupa **exactamente el asiento del juez** —misma rúbrica, mismos criterios, sin poder editar tampoco—, lo que permite comparar ambas y saber cuánto vale la del juez.

## Lo que no se puede medir, y qué se hace entonces

El presupuesto de contexto. El Agent SDK **no ofrece forma documentada de consultar cuánto contexto lleva consumido una sesión mientras corre**, así que el límite de 100.000 tokens concurrentes no se vigila: se garantiza por construcción, con un techo declarado por rol y una guarda que rechaza la llamada antes de emitirla.

Es un patrón que merece la pena retener: **cuando no puedes medir, acota**. Y déjalo escrito, porque un límite que nadie comprueba y nadie documenta es un límite que no existe.

## Dónde mirar

- [`architecture.md` §14](../architecture.md#14-observabilidad) y [§12](../architecture.md#12-presupuesto-de-contexto)
- La matriz de qué se instrumenta: [`specs/backend/trace-matrix.md`](../../specs/backend/trace-matrix.md)
