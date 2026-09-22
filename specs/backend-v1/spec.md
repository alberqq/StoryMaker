# SRS — Backend completo de StoryMaker

| | |
|---|---|
| **Cambio** | `backend-v1` |
| **Estado** | En revisión — pendiente de aprobación explícita |
| **Fecha** | 2026-09-21 |
| **Depende de** | `docs/architecture.md` (secciones 0, 3, 4, 5, 6, 7, 8, 10, 11, 12), skills `fastapi`, `sqlite`, `verification-methods` |

Este documento resulta de dos sesiones de grilling con el Autor: una para el alcance mínimo original, otra para ampliarlo a "absolutamente todo el backend". Recoge el *qué* y los límites del cambio; el *cómo* técnico (esquema exacto, casos de prueba, estructura de carpetas, rúbricas literarias completas) es trabajo de `plan.md` y de iteraciones posteriores, no de este documento.

---

## 1. Propósito

Construir el backend completo de StoryMaker en una sola spec: el núcleo (`storymaker`/`nh`), la envoltura FastAPI, el bucle de orquestación con el ciclo de reintentos/escalada completo, los seis agentes narrativos reales con una primera versión de sus skills de criterio, y la búsqueda semántica (`sqlite-vec` con embeddings generados en local vía FastEmbed).

El criterio de éxito es que **un capítulo completo se pueda escribir de principio a fin de verdad** — escaleta, investigación de huecos, redacción escena a escena con sus puertas de calidad, ensamblado final — no un esqueleto ni un camino feliz artificial con un agente de mentira.

Hasta ahora `backend/` está vacío; este es el primer código real que entra en el repositorio en la rama `zero`.

## 2. Alcance

### 2.1 Dentro de alcance

1. **Núcleo (`storymaker`/`nh`)** — esquema SQLite completo de `docs/architecture.md` sección 3 (registro histórico, biblia, personas, cronología y texto, control), incluidos `giro`, `gancho` y `extension_palabras` en `escenas`, más la tabla virtual `vec0` para embeddings. Un proyecto es un fichero SQLite propio, no una fila en una tabla. WAL, un solo escritor, transacción por escena, idempotencia por clave, tablas solo-anexado — según skill `sqlite`.
2. **Envoltura FastAPI** — endpoints para todos los verbos del CLI (sección 3.2), invocación por lista de argumentos nunca shell, sobre del núcleo propagado tal cual, streaming/polling para ejecuciones largas — según skill `fastapi`. Solo localhost, sin autenticación.
3. **Investigación bulk inicial** — antes de diseñar ninguna escaleta, el investigador recibe la lista cerrada de sub-encargos por dominio de `docs/architecture.md` sección 0/4/10 (léxico, material, trato, calendario...), cada uno con su `maxTurns`, y puebla `afirmaciones` y la biblia (`reglas`, `items_material`, `lexico`). Sustituye la carga manual de dosier que tenía antes la fase 1 de construcción.
4. **Bucle de orquestación completo** — script aparte (subproceso, no vive dentro del proceso FastAPI, sobrevive a un reinicio del servidor), que implementa el bucle de escena de `docs/architecture.md` sección 6 y la máquina de estados de convergencia de la sección 7: Redactada → Verificando → (limpio → Aceptada) | (incidencias, intentos<3 → Parche → Verificando) | (intentos=3 → Regenerada → Verificando, intentos<5) | (intentos=5 → Escalada → Aceptada marcada).
5. **Los seis agentes narrativos reales** — `.claude/agents/investigador.md`, `arquitecto.md`, `redactor.md`, `verificador.md`, `auditor.md`, `editor.md`, los seis en Haiku, cada uno con las herramientas recortadas y el `maxTurns` de la tabla de la sección 5 (`arquitecto` y `verificador` también lo llevan ahora, no solo `auditor`), invocados de verdad vía `Task` desde el bucle. El arquitecto cubre sus cuatro tareas (escaleta global, escaleta de capítulo, plan de investigación puntual sobre lo que la bulk no cubrió, auditoría de arco). El editor corre como pasada final por capítulo, con autoridad solo mecánica, una vez que todas las escenas de ese capítulo están `Aceptada`.
6. **Skills de dominio — primera versión** — las cinco familias (`investigacion/`, `mundo/`, `prosa/`, `control/`, `salida/`) con al menos: `registro-de-epoca`, `auditoria-arco`, `presentismo`, `arco`, `etica`, `verificacion-factual`. Son una primera versión razonable, no rúbricas perfeccionadas — se afinan en iteraciones posteriores, sin que eso bloquee esta spec. Al partir de Haiku en vez de Sonnet/Opus (sección 0), la calibración inicial de umbrales parte de una capacidad de razonamiento menor, no se hereda de una versión anterior con modelos distintos por agente.
7. **Búsqueda vectorial** — tabla `vec0` de `sqlite-vec`, embeddings generados en local con FastEmbed (sin API externa ni credenciales), pipeline de indexación del corpus de investigación (trocear fuentes, generar embedding, insertar), y consulta híbrida (filtro duro por fecha/lugar primero, semántica después — skill `sqlite`).
8. **Memoria a corto y largo plazo** — estado narrativo rodante comprimido al cerrar cada capítulo (skill de resumen vía modelo), ventana de 2-3 capítulos en el paquete de escena; tablas estructuradas de largo plazo filtradas por relevancia, sin ventana temporal, incluido el paquete de arco (`nh paquete arco`) ya como registro estructurado por escena y no como prosa completa — según `docs/architecture.md` sección 4.

### 2.2 Fuera de alcance (explícito)

- **Frontend** (React/Three.js) — esta spec es solo backend.
- **Autenticación, multiusuario, despliegue en red** — sigue siendo un backend local de un solo Autor.
- **Paralelismo real (agent teams)** — el sistema sigue siendo secuencial; el reparto del presupuesto de 100k tokens entre agentes concurrentes queda para cuando se aborde ese paralelismo (decisión ya fijada en `docs/architecture.md` sección 0).
- **Afinado profundo de las rúbricas literarias** — la primera versión de las skills de criterio es razonable, no definitiva; perfeccionarlas es trabajo continuo, no un bloqueo de esta spec.
- **Elegir el modelo ONNX exacto de FastEmbed** — cuál (multilingüe, según el idioma del corpus) se confirma al implementar (ver sección 6).

## 3. Requisitos funcionales

### 3.1 Esquema de datos

El esquema completo de `docs/architecture.md` sección 3: `fuentes`, `afirmaciones`, `vacios`, `reglas`, `items_material`, `lexico`, `personajes`, `arcos`, `estado_personaje`, `relaciones`, `eventos`, `itinerarios`, `escenas`, `hilos`, `prosa`, `continuidad`, `invenciones`, `incidencias`, `ejecuciones`. Más una tabla virtual `vec0` por tipo de contenido indexado semánticamente (empezando por `fuentes`/`afirmaciones`), enlazada por `rowid` — nunca embeddings inline (skill `sqlite`).

### 3.2 Verbos del CLI `nh`

Todos los descritos en `docs/architecture.md` sección 3.2, más los que hacen falta para lo nuevo de esta spec:

| Verbo | Qué hace |
|---|---|
| `nh proyecto crear` | Inicializa un fichero SQLite nuevo con el esquema completo aplicado. |
| `nh hechos buscar` | Consulta híbrida (filtro duro + FTS5 + vec) sobre el libro de hechos. |
| `nh material comprobar` | Verifica disponibilidad de objetos/cultura material por fecha y lugar. |
| `nh columna ventana` | Consulta la columna cronológica por ventana de fechas e itinerario. |
| `nh personaje estado` | Devuelve el estado de un personaje en un punto de la columna. |
| `nh proponer` / `nh aplicar` | Ciclo de propuesta y aplicación transaccional, idempotente por clave. |
| `nh escena consultar` | Devuelve una escena aplicada y su prosa. |
| `nh siguiente` | Trabajo pendiente — reanudación sin estado en la conversación. |
| `nh paquete escena` / `arco` / `etica` | Ensambla los paquetes de contexto por agente (sección 4). |
| `nh graduar` | Calcula el grado de evidencia de una afirmación investigada. |
| `nh lint lexico/material/cronologia/longitud` | Barridos deterministas tras redactar; `longitud` compara palabras de `prosa.texto` contra `escenas.extension_palabras`. |
| `nh embeddings indexar` | Trocea, genera embeddings en local con FastEmbed e inserta en la tabla `vec0` correspondiente. |

Cada verbo trunca su propia respuesta a un máximo de tokens fijo (`docs/architecture.md` sección 0, "Cómo se garantiza el techo de 100k") — el `--k` de `nh hechos buscar` u otro parámetro de tamaño no basta por sí solo, el CLI recorta igualmente si la respuesta se dispara.

### 3.3 Endpoints FastAPI

Un endpoint por verbo de 3.2, más un endpoint para lanzar el bucle de orquestación sobre un capítulo (dispara el script aparte y devuelve de inmediato) y un endpoint de estado para consultar el progreso vía polling/SSE.

### 3.4 Bucle de orquestación

Implementa el diagrama de secuencia de la sección 6 y la máquina de estados de la sección 7 completos: ensamblador arma el paquete → redactor escribe → linters deterministas (léxico, material, cronología, longitud) → verificador → si limpio, `nh aplicar` y siguiente escena; si hay incidencias, parche dirigido al redactor (hasta 3 intentos), luego regeneración (hasta 5), luego escalada con la escena marcada en la bandeja de excepciones pero aceptada igualmente — nunca bloquea el avance indefinidamente. Al completarse todas las escenas de un capítulo, invoca al editor para la pasada final.

Antes del bucle de escenas, y antes de diseñar ninguna escaleta, corre la investigación bulk (sección 2.1, punto 3): la lista cerrada de sub-encargos puebla `afirmaciones` y la biblia una sola vez por proyecto, no por capítulo.

### 3.5 Agentes y skills

Los seis agentes de la tabla de `docs/architecture.md` sección 5, en Haiku, con sus herramientas recortadas exactas y su `maxTurns` (`arquitecto`, `verificador` y `auditor`, los tres agentes que buscan o juzgan sin paquete acotado — sección 5, "Límite de turnos para quien busca en vez de recibir"). Las skills de criterio son una primera versión funcional: aplican un umbral y una salida concretos (puerta real, no un placeholder que siempre aprueba), aunque el umbral se vaya a recalibrar después con escenas reales — y ahora también contra la capacidad real de Haiku, no la de un modelo más grande.

### 3.6 Búsqueda vectorial y embeddings

- Generación local con FastEmbed (modelos ONNX), sin API externa, sin credenciales ni llamada de red por embedding — el modelo concreto (multilingüe, según el idioma del corpus) se confirma al implementar (ver riesgos, sección 6).
- Sin rate limit que gestionar: el pipeline de indexación no necesita cola ni backoff por esa razón. El límite real pasa a ser de cómputo local (CPU, tiempo de generación por lote), no de peticiones — el plan decide si el corpus de prueba necesita procesarse por lotes.
- Consulta híbrida: filtro duro primero, `MATCH` restringido a los `rowid` ya filtrados después — nunca al revés (skill `sqlite`).

## 4. Requisitos no funcionales

- **Presupuesto de contexto**: el techo de 100k tokens concurrentes (`docs/architecture.md` sección 0) sigue aplicando; con los seis agentes reales pero ejecución secuencial, cada invocación puede usar hasta el techo completo porque nunca hay dos agentes abiertos a la vez. Que hoy se cumpla por construcción no exime de los otros tres mecanismos que la sección 0 pide para que sea una garantía y no una expectativa: truncado por verbo del CLI (sección 3.2), `max_tokens` explícito en cada llamada de generación, y `maxTurns` × techo-por-turno como peor caso calculable por agente.
- **Modelo único (Haiku)**: los seis agentes usan Haiku (`docs/architecture.md` sección 0), no una mezcla de Sonnet/Opus. Reduce coste y latencia por invocación a cambio de capacidad de razonamiento; los umbrales de las rúbricas de criterio (sección 3.5) se calibran contra esa capacidad, no se asumen heredados.
- **TDD en núcleo y backend**: el núcleo (`storymaker`/`nh`) y la envoltura FastAPI se escriben test-first (paso 3 del Flujo de edición de `AGENTS.md`). El frontend no aplica.
- **Organización de carpetas**: backend por feature + `commons/`, según `AGENTS.md` y `docs/architecture.md` sección 11.
- **Coste de cómputo local de FastEmbed**, no rate limit: generar embeddings en local no tiene límite de peticiones, pero sí consume CPU de la máquina que ejecuta el backend — la investigación bulk (sección 2.1, punto 3) es la que más lo nota, al indexar de golpe al principio en vez de repartido escena a escena.

## 5. Criterio de aceptación (definición de hecho)

1. La investigación bulk corre antes que ninguna escaleta: puebla `afirmaciones` y la biblia a partir de la lista cerrada de sub-encargos, con embeddings e investigación reales (no simulados).
2. Un capítulo con varias escenas se escribe de principio a fin: el arquitecto diseña la escaleta (fijando `giro`, `gancho` y `extension_palabras` de cada escena) y detecta un hueco puntual que la bulk no cubrió, el investigador lo resuelve, el redactor escribe cada escena con su paquete de contexto, los linters deterministas corren incluida `longitud`, verificador y auditor corren de verdad (no stubs, los seis agentes en Haiku), y al menos una escena de prueba pasa por el ciclo de parche antes de quedar `Aceptada`, para demostrar que el ciclo de reintentos funciona.
3. El editor ensambla el capítulo completo al final y lo escribe a disco, con autoridad solo mecánica (sin introducir contenido nuevo).
4. Un corpus de prueba pequeño se indexa vía `nh embeddings indexar` (embeddings reales de FastEmbed, generados en local, no simulados) y una consulta híbrida devuelve resultados coherentes con el filtro duro aplicado primero.
5. `ejecuciones` registra tokens, coste y veredicto de cada invocación real (no nominal).
6. Reiniciar el proceso FastAPI mientras el bucle corre no mata la ejecución.
7. Idempotencia y WAL se cumplen bajo reintento.

Si el ciclo de reintentos nunca se ejerce en la demostración, si el editor reescribe contenido en vez de solo aplicar cambios mecánicos, si la investigación bulk no corre antes de la escaleta, o si la búsqueda semántica usa embeddings simulados en vez de los de FastEmbed, esta spec no está hecha aunque el resto funcione.

## 6. Riesgos y preguntas abiertas para el plan de implementación

- **Modelo ONNX exacto de FastEmbed.** El plan debe elegir un modelo concreto (candidato razonable: uno multilingüe, dado que el corpus puede estar en español) y confirmar que `fastembed` lo soporta al implementar, no fiarse de esta spec para el nombre exacto.
- **Coste de cómputo local como cuello de botella** para indexar corpus grandes en una máquina modesta — el plan decide si hace falta procesar por lotes o en segundo plano.
- **Redacción de las rúbricas de primera versión** de cada skill de criterio (arcaísmo, presentismo, arco, ética) — quién las escribe y contra qué se calibran inicialmente (no hay todavía escenas reales de referencia).
- Casos de prueba TDD concretos, y cómo se prueba el ciclo de reintentos/escalada sin gastar tokens reales en cada corrida.
- Cómo se representa y lanza el "script aparte" del bucle en concreto.
- Nombre y forma exacta de los campos de cada verbo del CLI.
- **Cifras concretas del presupuesto de 100k** (`docs/architecture.md` sección 0): cuántos tokens trunca cada verbo del CLI, qué `max_tokens` lleva cada llamada de generación, y qué `maxTurns` exacto llevan `arquitecto`, `verificador` y `auditor` — hoy son un mecanismo descrito, no números fijados.
- **Margen del lint de longitud** (`docs/architecture.md` sección 7): el ejemplo de la arquitectura usa ±20% sobre `extension_palabras`, pero el margen real y si es uniforme o varía por tipo de escena queda para el plan.
- **Calibración de rúbricas contra Haiku en vez de Sonnet/Opus** — al ser un modelo con menos capacidad de razonamiento que el que se asumía cuando se escribió la primera versión de esta spec, la primera versión de las skills de criterio (sección 2.1, punto 6) puede necesitar más iteración de la prevista, o umbrales más permisivos, antes de que las puertas de criterio no rechacen casi todo.
