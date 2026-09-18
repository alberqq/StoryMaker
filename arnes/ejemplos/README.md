# Ejemplos

`encargo-ejemplo.json` es un Encargo completo y valido conforme a `arnes/esquemas/encargo.schema.json`.
Sirve para la ejecucion de aceptacion y para probar el canal de fichero (RF-063) contra el de dialogo: el
mismo Encargo por ambos canales debe producir artefactos identicos.

Sus parametros son deliberadamente pequenos —2 capitulos x 4 parrafos— para que una ejecucion completa cueste
del orden de decenas de invocaciones y no de centenares. Sus derivados:

```
palabras_por_parrafo_objetivo  = 10 x 12 = 120
palabras_por_capitulo_objetivo = 120 x 4 = 480
escenas_totales                = 2 x 4 = 8
```

Uso:

```
/proyecto-crear --encargo arnes/ejemplos/encargo-ejemplo.json
```
