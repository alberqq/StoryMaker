# Verificación — Métodos para comprobar que el código y la salida de los agentes son correctos

Este documento reúne, a modo de catálogo de referencia, los métodos de verificación disponibles para comprobar tanto el código del arnés como lo que producen los agentes. No prescribe cuáles se aplican en StoryMaker ni sustituye a `architecture.md`: es el vocabulario común a partir del cual decidir, caso por caso, qué puerta usar en qué punto del sistema.

Se divide en dos bloques —verificación del código y verificación del proceso (¿se comporta el agente de forma fiable?)— y cierra con el marco de clasificación del Trust Spec, que sitúa cada método en una de cinco categorías según cómo se obtiene la garantía.

## 1. Verificación de código

### Type checking (comprobación de tipos)
Comprobación automática de que los valores se usan de forma consistente con lo que las operaciones esperan de ellos (por ejemplo, que nunca se pase una cadena donde se requiere un número).

### Static analysis / SAST (análisis estático)
Escaneo del código fuente sin ejecutarlo, para contrastarlo con patrones conocidos como problemáticos: vulnerabilidades de seguridad, code smells, anti-patrones.

### Symbolic execution (ejecución simbólica)
Ejecutar el código con entradas simbólicas (no valores concretos) para derivar, mediante un SMT solver, las condiciones exactas y los contraejemplos concretos que lo romperían.

### Formal verification / theorem proving (verificación formal)
Demostración matemática de que el código cumple una especificación para todas las entradas posibles, no solo para las probadas o exploradas.

### Unit / integration testing (pruebas unitarias e de integración)
Comprobación del comportamiento frente a entradas de ejemplo concretas y elegidas, contrastadas con la salida esperada.

### Property-based testing (pruebas basadas en propiedades)
Se especifica una propiedad general que debe cumplirse para cualquier entrada, y luego se generan automáticamente muchas entradas para buscar una violación.

### Mutation testing (pruebas de mutación)
Introducir deliberadamente pequeños errores en el código para comprobar si la batería de pruebas existente realmente los detecta.

### Contract testing (pruebas de contrato)
Verificar que la interfaz (forma de la petición/respuesta) entre dos servicios se mantiene consistente, con independencia de los internos de cada lado.

## 2. Verificación de proceso (¿se comporta el agente de forma fiable?)

### Runtime observability / tracing (observabilidad y trazas en ejecución)
Instrumentar un agente para que su trayectoria real (llamadas a herramientas, tokens, latencia, errores) quede visible y consultable a posteriori.

### Evals (evaluaciones)
Pruebas estructuradas del comportamiento de un modelo o agente contra un dataset y un método de puntuación (golden-dataset, LLM-as-judge, finalización de tarea, adversarial, en vivo/online).

### Sandboxed execution (ejecución en entorno aislado)
Ejecutar el código del agente en un entorno aislado (contenedor, microVM) para que una acción errónea falle de forma segura en lugar de llegar a producción.

### Guardrails (barreras)
Políticas o filtros que restringen qué acciones o salidas puede producir un agente, antes de que actúe.

### Human-in-the-loop review (revisión humana en el bucle)
Una persona aprueba, rechaza o edita las acciones del agente de alta consecuencia, y esa decisión se realimenta como señal de entrenamiento.

### Multi-agent verification (verificación multiagente)
- **Critic/verifier**: un segundo modelo revisa al primero.
- **Self-consistency**: voto mayoritario entre ejecuciones repetidas.
- **Debate**: dos modelos argumentan y un juez decide.
- **Reflection**: autocrítica y revisión por el propio modelo.
- **Ensembles**: combinación de distintos modelos.

### CI/CD integration (integración en CI/CD)
Hacer pasar los cambios generados por el agente por el mismo pipeline, pruebas y revisión que el código escrito por humanos, más el etiquetado de procedencia.

### Progressive rollout (despliegue progresivo)
Publicar un cambio tras un feature flag a un pequeño porcentaje de tráfico, monitorizado antes de la liberación completa.

### Red-teaming / adversarial testing (pruebas adversariales)
Buscar deliberadamente fallos bajo un modelo de amenaza adversarial (inyección de prompts, cadenas de mal uso de herramientas, deriva de objetivo, exfiltración de datos), no solo el error ordinario.

### Model checking (comprobación de modelos)
Explorar exhaustivamente los estados y transiciones alcanzables por un agente para verificar invariantes (por ejemplo, «nunca borrar antes de respaldar»); es el análogo, para flujos multiagente, de la ejecución simbólica.

## 3. Marco de clasificación (Trust Spec)

Cada método de verificación obtiene su garantía por una vía distinta. El Trust Spec las agrupa en cinco categorías:

| Categoría | Significado | Verificado por... |
|---|---|---|
| **T — Test** | Verificado ejecutando el sistema contra entradas concretas. | Unit/integration testing, property-based testing, mutation testing, contract testing, evals (golden-dataset, task-completion), red-teaming (casos adversariales automatizados). |
| **A — Analysis** | Verificado por razonamiento estático: tipos, SAST, ejecución simbólica o prueba formal. | Type checking, static analysis/SAST, symbolic execution, formal verification, model checking. |
| **I — Inspection** | Verificado por una persona o un modelo crítico que lee y juzga. | Human-in-the-loop review, multi-agent verification (critic/verifier, debate, reflection), evals (LLM-as-judge), red-teaming manual. |
| **D — Demonstration** | Verificado observando el funcionamiento correcto en un escenario realista (staging, sandbox). | Sandboxed execution, progressive rollout, runtime observability (como evidencia de comportamiento correcto sostenido). |
| **U — Unverifiable / Accepted Risk** | No aplica ningún método, o no compensa el coste; se nombra explícitamente en lugar de dejarlo como supuesto silencioso. | Cualquier aspecto del sistema o del agente para el que, de forma deliberada, no se aplica ninguna de las categorías anteriores. |

Algunos métodos no encajan de forma limpia en una sola casilla:
- **Guardrails** son preventivos, no verificadores en sí mismos: según estén implementados como reglas fijas o como un clasificador aprendido, se apoyan en A o en I.
- **CI/CD integration** no es un método de verificación sino el mecanismo que hace que T y A se ejecuten de forma sistemática en cada cambio.
- **Self-consistency y ensembles** aportan una garantía estadística que no es exactamente I (no hay juicio cualitativo) ni T en sentido estricto (no hay un resultado esperado fijo); se anotan como una variante propia dentro de la verificación multiagente.

La utilidad del marco T/A/I/D/U no es clasificar por clasificar, sino que, para cada componente del sistema o cada salida de un agente, quede explícito qué categoría lo respalda —y, si es U, que quede dicho en voz alta en lugar de darlo por hecho.
