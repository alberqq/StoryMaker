# AGENTS.md — StoryMaker

## Estructura del repositorio

StoryMaker es un monorepo. El frontend está en Three.js y React; el backend, en Python con FastAPI. El backend se organiza por feature (una carpeta por feature, más `commons/` solo para infraestructura técnica transversal); el frontend sigue Feature-Sliced Design (FSD) v2.1, guiado por la skill `feature-sliced-design` (`.claude/skills/feature-sliced-design/`, copia sin modificar de la skill oficial). Detalle en [`docs/architecture.md`](docs/architecture.md), sección 11.

## Presupuesto de contexto

La ventana de contexto total del sistema —la suma de tokens de todos los agentes abiertos a la vez, orquestador incluido— tiene un techo de 100k tokens que no se puede superar en ningún momento. Al diseñar o activar agentes (subagentes, agent teams, lo que sea), cuenta este límite antes de asumir que corren varios a la vez. El detalle y su consecuencia sobre el paralelismo están en [`docs/architecture.md`](docs/architecture.md), sección 0 y sección 8.

## Rama de trabajo

Todo el desarrollo de StoryMaker ocurre en la rama `zero`. Los commits se hacen directamente sobre ella, sin crear ramas de trabajo intermedias.

## Documentación

La arquitectura, las definiciones y el conocimiento de dominio de StoryMaker no están en este archivo: están en `docs/`. Antes de razonar sobre el sistema, consulta el documento que corresponda en vez de reconstruir el criterio desde cero:

- [`docs/architecture.md`](docs/architecture.md) — arquitectura del sistema multiagente: quién gestiona qué, cómo recibe su contexto cada agente y cómo se controla el sistema sin humano en el bucle.
- [`docs/definitions.md`](docs/definitions.md) — glosario de la ontología del dominio (registro histórico, contrato de fidelidad, anacronismo y el resto de entidades). Cada término se define aquí una sola vez.
- [`docs/domain-knowledge.md`](docs/domain-knowledge.md) — las vistas del dominio y qué decisión encierra cada una, con lo que falla cuando esa decisión no se toma.
- [`docs/verificators.md`](docs/verificators.md) — catálogo de métodos de verificación disponibles (de código y de proceso) y el marco de clasificación Trust Spec (T/A/I/D/U), como vocabulario común para decidir qué puerta usar en cada punto del sistema.

**Estos documentos son la fuente de verdad, no un archivo aparte.** Cuando un cambio en el código o en el diseño del arnés se desvíe de lo que alguno de ellos describe, el documento correspondiente se actualiza en el mismo cambio, no después. Un documento que no refleja el sistema deja de servir para consultarlo.

## Flujo de edición

Todo cambio en StoryMaker recorre un ciclo de cuatro pasos, siempre en este orden y siempre circular: terminar el cuarto es volver al primero del siguiente cambio, no un final. Cada paso tiene una puerta de entrada explícita — no se avanza al siguiente porque el anterior "parece" terminado.

1. **Edición de specs** (`specs/<cambio>/spec.md`), el contexto específico del cambio. Es el punto de entrada del ciclo: antes de tocar la spec, el agente usa la skill `grill-me` para preguntarle al usuario por qué pide ese cambio y qué decisión hay detrás, en vez de darlo por sabido o inferirlo. Responder las preguntas de aclaración no basta: la spec no queda **aprobada** hasta que el usuario lo confirma explícitamente sobre lo escrito.
2. **Plan de implementación** (`specs/<cambio>/plan.md`), en la misma carpeta que la spec. No se puede crear un plan de implementación si la spec correspondiente no está aprobada — el plan traduce a pasos concretos una decisión que todavía no existe si la spec sigue abierta. Igual que la spec, el plan necesita aprobación explícita del usuario antes de pasar al siguiente paso; que el agente lo dé por bueno no cuenta.
3. **Edición de código** (frontend en Three.js/React, backend en Python/FastAPI), que implementa lo que el plan ya aprobado describe. No se escribe código si no hay un plan de implementación aprobado — el código nunca va por delante del plan que lo justifica, igual que antes no iba por delante de la spec. En el núcleo y el backend (`storymaker`/`nh`, FastAPI) el código se escribe con TDD: el test se escribe antes que la implementación, porque ahí un fallo corrompe estado o aprueba mal una escena. El frontend no lo exige — sigue el criterio de las skills `react`/`threejs`: que el flujo funcione de principio a fin antes que esté perfecto.
4. **Edición de spec y docs**, al terminar el código. Se actualiza la spec si la implementación reveló algo que no había previsto, y `docs/` (arquitectura, definiciones, dominio, verificadores) para que quede alineado con lo ya implementado. Arranca al terminar la edición de código, nunca antes.

De ahí se vuelve a empezar por specs en el siguiente cambio.
