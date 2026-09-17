---
description: Lista los puntos de control pendientes y recoge la decision del Autor.
argument-hint: "[pct_xxxxx <decision>]"
allowed-tools: Bash, Read, AskUserQuestion
---

Puntos de control (PC-1 a PC-7). Argumento recibido: `$ARGUMENTS`

## Sin argumentos: lista lo pendiente

```
storymaker --proyecto <prj> control listar --estado pendiente
```

Para cada uno, presenta **que se decide y que se le esta ensenando**, no solo el
identificador. Un punto de control que el Autor no entiende no es un control: es un
bloqueo.

| Punto | Que decide |
|---|---|
| PC-3 | Aprobar el Canon, rechazarlo con hallazgos, o replanificar |
| PC-4 | Aceptar o rechazar una replanificacion, con los capitulos que invalida |
| PC-5 | Bloqueo irresoluble: evitar el detalle, aportar fuente, autorizar licencia o modificar el Encargo |
| PC-6 | Agotamiento con bloqueantes: aceptar la deuda, ampliar presupuesto o abandonar |

## Con argumentos: resuelve

```
storymaker --proyecto <prj> control resolver --id <pct> --decision <d> --quien "<nombre>" --motivo "..."
```

Decisiones admitidas: `aprobar`, `rechazar`, `editar`, `regenerar`, `ramificar`,
`aportar_fuente`, `autorizar_licencia`, `modificar_encargo`, `ampliar_presupuesto`,
`ajustar_estilo`, `volver_al_canon`, `abandonar`.

## La regla que conviene tener delante

**Aprobar con bloqueantes abiertos solo se admite en PC-3, solo en modo humano, y
exigiendo motivo.** Y deja el Proyecto limitado a *finalizado con reservas* de forma
irreversible.

Antes de que el Autor apruebe con bloqueantes abiertos, **diselo con esas palabras**:
la novela ya no podra entregarse como finalizada por mucho que todo lo demas
converja despues. No es una formalidad que se pueda deshacer luego.

Un agente validador nunca puede hacerlo. Si te lo piden en modo agente, el nucleo
devolvera ERR-709.
