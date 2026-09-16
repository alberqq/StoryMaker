---
description: Emite el informe de consumo real frente a presupuestado de la Ejecucion.
allowed-tools: Bash, Read
---

Informe de calibracion (RF-079).

```
storymaker --proyecto <prj> informe calibracion
```

## Por que importa mas de lo que parece

Todos los valores de presupuesto por defecto del arnes son **suposiciones sin base
empirica**. Se fijaron sin datos de coste reales y estan declarados como tales en la
especificacion. Este informe es **la unica via por la que dejaran de serlo**.

Sin recalibrar, cada Ejecucion siguiente hereda las mismas cifras inventadas, y la
politica de agotamiento se dispara donde no debe o no se dispara donde deberia.

## Que presentar

1. **Iteraciones internas por escena** frente a las tres presupuestadas. Si la media
   real es de una, sobra presupuesto; si muchas escenas llegan a tres sin converger,
   el problema no es el presupuesto, es el Canon.
2. **Iteraciones externas por capitulo** frente a las dos presupuestadas.
3. **Uso de la reserva comun**, separando el tramo libre del tramo final. Esto es lo
   que dice si la particion en dos tramos esta bien calibrada: si el tramo final
   llego intacto al ultimo tercio y sobro, se reservo de mas; si se agoto enseguida,
   se reservo de menos.
4. **Solicitudes de investigacion bajo demanda**. Muchas indican una laguna
   estructural del Contexto historico, que se resuelve en E2 y no escena a escena.
5. **El factor de arnes**: coste total dividido entre el de una generacion en bruto
   de la extension objetivo. El presupuesto lo fija en 15 como techo, repartido
   entre redaccion, refinamiento, validacion, investigacion y pasada global.
6. **La distribucion de los modos de terminacion**. Una proporcion alta de
   estancamiento o regresion dice que algo aguas arriba no esta bien: el bucle no
   converge porque el problema no esta donde se esta iterando.

Termina con una **recomendacion concreta** de que valores ajustar para la Ejecucion
siguiente, y con la advertencia de que una sola novela no es una muestra.
