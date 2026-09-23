# Guardrails y policy

## El concepto

Un *guardrail* es una restricción de contenido que se aplica **fuera del modelo**, porque pedirle a un modelo que no haga algo no es garantía de que no lo haga. Hay dos formas de ponerlo: en el prompt (barato, no garantiza nada) y en código, entre el modelo y el mundo (garantiza, cuesta implementarlo).

## Cómo se aplica aquí

El caso de StoryMaker es concreto y humano: el comprador dice qué palabras **no quiere leer** en la novela. A veces por gusto —nada de piratas ni tesoros, que esto no es una novela de aventuras— y a veces por algo más delicado: quien perdió a alguien en el mar no quiere encontrarse la palabra `naufragio` en el regalo de jubilación de su padre.

Por eso hay **dos niveles**, y no uno:

| Nivel | Qué recoge |
|---|---|
| `global` | Lo que el sistema no escribe nunca |
| `novela` | Lo que este encargo concreto no quiere |
| `destinatario` | Lo que **esta persona** no debe leer |

El tercero es el que justifica el diseño. Una lista única mezclaría una preferencia estética con una herida, y la segunda no admite fallo.

## Dónde se aplica

`guardrail_prohibidas` corre **post `WriteChapter`**, antes de que el capítulo se acepte. Si hay coincidencia, el capítulo vuelve al editor con la incidencia; el editor reescribe; se vuelve a comprobar. Con **límite de reintentos**: agotado, el sistema se detiene e informa, no publica algo a medias.

Y se expone además como *hook* de `.claude/`, para que una persona que edite un capítulo a mano en el disco compruebe lo mismo antes de commitear. **No es una segunda implementación**: la validación vive en el Core Domain y tanto el nodo del grafo como el hook la invocan. Dos implementaciones de la misma regla divergen; es cuestión de tiempo.

## El trabajo de verdad está en la normalización

Prohibir `pirata` es un `LIKE`. Prohibirlo de verdad es esto:

- **Mayúsculas y acentos**: `Pirata`, `PIRATA`.
- **Plurales y derivados**: `piratas`, y aquí está el caso que importa — quien prohíbe `naufragio` quiere prohibir `naufragar` y `naufragó`. Sin *stemming*, el guardrail deja pasar justo lo que dolía.
- **Variantes simples**: separaciones, guiones.

Por eso `canon_prohibida` guarda dos columnas, `termino` y `normalizado`: la comparación se hace siempre contra la forma normalizada, del término y del texto.

El [red-team log](../red-team.md#rt-03--normalización-de-palabras-prohibidas-y-lo-que-se-le-escapa) tiene el análisis de hasta dónde llega esta normalización y qué se le escapa — con el veredicto de que los homóglifos y los caracteres de anchura cero son irrelevantes aquí (no hay adversario dentro del escritor) y los derivados legítimos, no.

## Lo que un guardrail de palabras no puede hacer

`contenido_admisible` —«sin violencia explícita»— **no es una palabra prohibida**. No hay término que buscar. Eso lo juzga el juez con la rúbrica, que es la herramienta adecuada para lo que no se puede calcular, y sería un error meterlo en `canon_prohibida` para que «esté cubierto».

Es la línea general del sistema: *determinista antes que modelo*, pero solo donde el determinismo puede decir algo.

## El audit log

Cada coincidencia se registra en `audit_log` y se emite a Langfuse como score. No es burocracia: sin registro no se puede responder a «¿por qué este capítulo tardó cuatro intentos?», que es exactamente la pregunta que se hace cuando una novela sale cara.

## Dónde mirar

- [`architecture.md` §15](../architecture.md#15-guardrails-y-policy)
- El esquema de `canon_prohibida`: [`diagramas.md`](../diagramas.md#esquema-sqlite)
