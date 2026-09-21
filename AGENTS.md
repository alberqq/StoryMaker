# AGENTS.md — StoryMaker

## Estructura del repositorio

StoryMaker es un monorepo. El frontend está en Three.js y React; el backend, en Python con FastAPI.

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

Todo cambio en StoryMaker recorre un ciclo de tres procesos, siempre en este orden y siempre circular: terminar el tercero es volver al punto de partida del siguiente cambio, no un final.

1. **Edición de specs** (`specs/`), el contexto específico del cambio. Es el punto de entrada del ciclo: antes de tocar la spec, el agente usa la skill `grill-me` para preguntarle al usuario por qué pide ese cambio y qué decisión hay detrás, en vez de darlo por sabido o inferirlo. Solo con eso respondido se edita la spec y se cierra.
2. **Edición de código** (frontend en Three.js/React, backend en Python/FastAPI), que implementa lo que la spec ya cerrada describe. Este proceso no arranca mientras la spec correspondiente siga abierta: el código nunca va por delante de la spec que lo justifica.
3. **Edición de docs** (`docs/`), el contexto general (arquitectura, definiciones, dominio, verificadores). Arranca al terminar la edición de código, para que estos documentos queden alineados con lo ya implementado.

De ahí se vuelve a empezar por specs en el siguiente cambio.
