# AGENTS.md — StoryMaker

Instrucciones para cualquier agente que trabaje en este repositorio.

## Rama de trabajo

Se trabaja **siempre sobre `zero`**. Los commits van directos a esa rama: no se crea una rama previa por cambio ni se ofrece fusionarla después. No se cambia de rama salvo que el Autor lo pida.

## Dónde vive cada cosa

| Documento | Contiene | Regla |
|---|---|---|
| [`docs/architecture.md`](docs/architecture.md) | **Toda decisión fija**: quién hace qué, cómo recibe su contexto, cómo se detiene, trade-offs registrados | Es la fuente de verdad. Si algo lo contradice, gana la arquitectura |
| [`docs/verification.md`](docs/verification.md) | Plan de verificación y **Quality Gates** (G0–G6), clasificación T/A/I/D/U, riesgos aceptados | Toda capacidad nueva declara aquí su clase y su gate |
| [`docs/definitions.md`](docs/definitions.md) | Glosario de la ontología del dominio | Vocabulario obligatorio: se usan estos términos, no sinónimos |
| [`docs/domain-knowledge.md`](docs/domain-knowledge.md) | Cómo se relacionan los conceptos del dominio | — |
| `specs/<nombre>/spec.md` | Qué hace exactamente una pieza: contratos, entradas, salidas, casos de error, y **sus requisitos enumerados** (`REQ-BE-nn`, `REQ-FE-nn`) derivados de su propio contenido | Deriva de la arquitectura, no la sustituye |
| `specs/<nombre>/plan.md` | **Solo la forma técnica exacta**: ficheros, funciones, orden de trabajo | Si contradice la arquitectura, para y pregunta |
| `specs/<nombre>/trace-matrix.md` y [`trace-matrix.md`](trace-matrix.md) | Correspondencia requisito↔ítem de plan, por mitad y consolidada en la raíz | Se mueve con el documento que cambia, en la misma operación. Una matriz desactualizada afirma en verde lo que ya no ha comprobado |
| [`docs/iteraciones.md`](docs/iteraciones.md) | Registro de iteraciones: qué se cambió al implementar, por qué y con qué efecto, incluidos los contraejemplos de TLC | Toda desviación respecto de la especificación deja aquí su entrada |
| [`docs/requirements-audit.md`](docs/requirements-audit.md) | Auditoría de `REQUIREMENTS.md` contra el repositorio, requisito a requisito | Se marca lo que se ha comprobado, no lo que se cree cierto |
| [`docs/red-team.md`](docs/red-team.md), [`docs/skills.md`](docs/skills.md), [`docs/diagramas.md`](docs/diagramas.md), [`docs/explainers/`](docs/explainers) | Material de apoyo: sesiones adversarias, skills del harness, diagramas y explicaciones | Derivan de los anteriores; no fijan decisiones |

## Spec-driven development

Este proyecto se desarrolla **dirigido por especificación**: la especificación manda y el código es su consecuencia. De ahí se siguen tres cosas que no son negociables:

- **Ningún cambio nace en el código.** Lo que haya que cambiar se cambia primero arriba —arquitectura, luego spec, luego plan— y baja. No se implementa algo para documentarlo después.
- **La especificación es la fuente de verdad, no un reflejo.** Si el código y el documento discrepan, el que está mal es el código, salvo que el Autor decida lo contrario. La desviación se propaga al documento y se anota en su registro de cambios.
- **Un documento sin grilling no está terminado.**

No se escribe código antes de haber recorrido esta secuencia. Cada paso termina con un *grilling*, y no se avanza al siguiente hasta que no queden hilos sueltos.

1. **Comprobar la arquitectura.** Leer `docs/architecture.md` y decidir si la petición ya está cubierta por una decisión fijada.
   - Si lo está, se implementa bajo ella.
   - Si la petición **contradice** una decisión fijada, **parar y preguntar al Autor**. No se resuelve por cuenta propia.
   - Si **no está**, se escribe en `docs/architecture.md`: la decisión, su consecuencia principal, las opciones consideradas con su criterio en la tabla de trade-offs, y una fila en el registro de cambios.
2. **Grilling de la arquitectura.** Invocar la skill `grilling` (o `/grill-me`) sobre lo recién escrito. Busca hilos sueltos e incompatibilidades con las decisiones ya fijadas. Lo que aparezca se resuelve en el documento antes de seguir.
3. **Escribir la spec** en `specs/<nombre>/spec.md`.
4. **Grilling de la spec.** Misma skill, mismo criterio: contradicciones con la arquitectura, casos no cubiertos, contratos ambiguos.
5. **Escribir el plan de implementación** en `specs/<nombre>/plan.md`.
6. **Grilling del plan.** Orden de trabajo, dependencias, qué se rompe mientras tanto.
7. **Implementar**, y solo entonces.

El motivo del grilling en los tres puntos es el mismo: este sistema tiene decisiones muy acopladas —validadores como nodos, inmutabilidad, sello del corpus, presupuesto de contexto— y una incompatibilidad detectada en el documento cuesta un párrafo; detectada en el código, cuesta una refactorización.

## Verificación

Toda pieza nueva declara, en su spec, **su clase de confianza y el gate que la cubre**, con el marco de `docs/verification.md`:

- **T** test · **A** análisis estático o formal · **I** inspección humana · **D** demostración en escenario realista · **U** riesgo aceptado.
- `U` solo es admisible si queda escrito en §5 de `verification.md` con su mitigación y su condición de revisión. Un riesgo sin fila es un riesgo olvidado, no aceptado.
- **A vence a T** cuando ambas son posibles: lo que se puede garantizar por construcción no se deja a una prueba.
- **G3 y G5 no admiten excepción.** Ninguna propuesta puede introducir un camino que publique una versión sin validar.

## Documentación

- **Todo cambio de implementación que se desvíe de la especificación se propaga a los documentos**, y el cambio se anota en el registro de cambios del documento afectado. El código no es la documentación.
- **Los documentos se reescriben, no se parchean.** Cuando un documento acumula remiendos y deja de leerse bien, se vuelve a redactar entero.
- **Alcance literal.** Si el Autor pide eliminar o cambiar algo en un documento, se aplica a todas sus apariciones, incluidas las del registro histórico.
- Castellano, con los términos técnicos en inglés. Prosa, no telegrama.

## Criterio de producto

StoryMaker es un **ejercicio académico sin impacto real**. Ante la duda entre que corra de principio a fin y que sea correcto en todos sus bordes, gana que corra. Ante una puerta que puede bloquear —una verificación extra, un invariante estricto—, la respuesta por defecto es ablandarla, no reforzarla. Los hallazgos se cuentan al Autor; no se convierten en paradas.

Esto no exime del flujo de arriba: el rigor va en los documentos, la ligereza en la ejecución.

## Operación

- **No se reinicia el servidor de la interfaz con Ejecuciones vivas.** Comprobar antes con `curl -s http://127.0.0.1:8765/api/procesos` y no reiniciar si hay alguna en `en_curso` o `esperando_al_autor`. Editar ficheros es inofensivo: los cambios entran en el siguiente arranque, que elige el Autor.
- **Lo que el Autor borra, borrado se queda.** No se rescata del historial de git para reutilizarlo como entrada de diseño.
