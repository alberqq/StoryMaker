---
description: Etapa, unidad, iteracion, hallazgos por severidad, consumo y proyeccion a terminacion.
allowed-tools: Bash, Read
---

Panel de la Ejecucion en curso (RF-086). No interrumpe nada: solo lee.

```
storymaker --proyecto <prj> ejecucion estado
```

Presenta al Autor, en este orden:

1. **Donde esta**: etapa activa, unidad en proceso, numero de iteracion.
2. **Que hay abierto**: hallazgos por severidad. Los bloqueantes primero, porque son
   los que impiden avanzar.
3. **Cuanto queda**: consumo frente a presupuesto, y remanente de coste, tiempo e
   iteraciones. Distingue el tramo libre de la reserva del **tramo final**, que solo
   libera el ultimo tercio de la novela.
4. **Como va a acabar**: la proyeccion a terminacion, si el avance ya pasa del 25 %.
   Antes de ese punto la proyeccion no es informativa y el nucleo no la emite.
5. **Que espera de el**: puntos de control pendientes, con lo que cada uno necesita.

Si el Proyecto esta limitado a *finalizado con reservas*, **dilo arriba del todo**,
con el motivo. Es informacion que cambia lo que el Autor puede esperar del
resultado, y enterarse al final seria tarde.

Si hay lineas descartadas por truncamiento (ERR-503), dilo tambien: significa que
hubo un corte y que el trabajo posterior a esa linea se rehizo.

Para el estado de los hilos, usa:

```
storymaker --proyecto <prj> novela hilos
```

que lo **recalcula** en lugar de leerlo del indice. El indice sirve para mirar; no
para decidir.
