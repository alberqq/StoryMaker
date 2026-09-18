---
description: "control.atender - Resuelve un punto de control pendiente con la decision del autor y reanuda la ejecucion."
argument-hint: "<PRY-id> <PCH-id> <opcion> [motivo]"
---

# Operación `control.atender`

Argumentos: `$ARGUMENTS`. Actúas como **Agente Orquestador** (CMP-006).

1. Lee `proyectos/<PRY-id>/puntos-control/<PCH>-<objeto>.solicitud.json`.
2. **Preséntalo entero** antes de pedir nada: el artefacto en su estado actual, **todos** los conjuntos de
   hallazgos acumulados —no solo el último—, los intentos consumidos, y cada opción **con su consecuencia**.
   El autor no decide a ciegas.
3. Si hay varios puntos abiertos, preséntalos **en el orden en que se generaron**.
4. Recoge la opción. Una opción fuera de las ofrecidas es `ERR-204`: recházala y vuelve a presentarlas.
5. Escribe `<PCH>-<objeto>.decision.json` con opción, motivo y `resuelto_en`.
6. Añade el evento `decision_autor` a la bitácora con la opción y su motivo.
7. Levanta `bloqueado`, recalcula el cursor y continúa. La decisión es un dato de entrada más del paso
   siguiente.

## Las cuatro opciones de bloqueo (PCH-7, PCH-8, PCH-10)

| Opción | Efecto |
|---|---|
| `continuar_aceptando_con_observaciones` | El artefacto pasa a `Aceptada_con_observaciones`. Sus hallazgos quedan **abiertos y registrados**, y aparecen uno a uno en el bloque 4 del informe |
| `conceder_intentos_adicionales` | Anota `intentos_concedidos` en el estado. El bucle se reanuda con el nuevo límite y la concesión consta en bitácora |
| `aportar_el_texto` | El texto del autor se escribe como un intento más con `autoria: "autor"`. **No pasa por el bucle interior**; sí entra en el bucle exterior y en la validación global: el autor decide sobre la forma, no sobre la coherencia |
| `abortar` | El Proyecto pasa a `Abortado` conservando **todo** lo aprobado. Nada se borra |

## Los demás puntos

| Punto | Opciones |
|---|---|
| PCH-2 · contradicciones | Cuál de las dos afirmaciones conservar, por cada par |
| PCH-3 · cobertura deficitaria | Continuar con la etapa **Incompleta** (se registra la confirmación, sin ella la Etapa 2 no arranca) o repetir la investigación |
| PCH-4 · revisar Contexto | Lanzar la Etapa 2 o repetir la Etapa 1 |
| PCH-5 · hueco estructural de canon | Aceptar el hueco, aportar el elemento o repetir la etapa |
| PCH-6 · revisar Canon | Lanzar la Etapa 3 o repetir la Etapa 2 |
| PCH-9 · entrega | Aceptar el manuscrito o repetir la Etapa 3 |

**Sin decisión, la ejecución permanece detenida indefinidamente.** No hay tiempo de espera y el sistema no
decide por su cuenta.
