---
description: "etapa.repetir - Archiva los artefactos de una etapa y sus derivados, y la vuelve a ejecutar desde cero."
argument-hint: "<PRY-id> <etapa-1|etapa-2|etapa-3>"
---

# Operación `etapa.repetir`

Argumentos: `$ARGUMENTS`. Actúas como **Agente Orquestador**.

Es la **única vía** de cambiar un artefacto sellado o congelado. No existe la edición parcial ni el parcheo:
se repite la etapa entera, y **se archiva; no se borra nada, jamás**.

## Procedimiento

1. **Calcula el alcance**: la etapa pedida y **todos sus derivados aguas abajo**.
   Repetir la Etapa 1 archiva también el Canon y el Manuscrito; repetir la Etapa 2 archiva el Manuscrito.
2. **Presenta la lista de lo que se archivará** y **espera confirmación explícita**. Sin ella, `ERR-203`.
3. Con la confirmación: mueve los artefactos a `archivo/<etapa>-<aaaammdd-hhmmss>/`, íntegros. La rama
   anterior se conserva entera y la bitácora nunca pierde su historia.
4. Añade el evento `archivado` a la bitácora con el motivo y lo archivado.
5. Reinicia el estado de esa etapa a `No_iniciada`, limpia sus contadores y sitúa el cursor en su primer paso.
6. Continúa con `/etapa-lanzar`.

Los artefactos archivados **siguen siendo legibles y auditables para siempre**. Es una rama por repetición de
etapa, no un árbol de versiones.
