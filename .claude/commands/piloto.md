---
description: Muestra la escena piloto con su ficha del Canon y los parametros de estilo aplicados, y recoge la decision.
allowed-tools: Bash, Read, AskUserQuestion
---

La escena piloto (RF-046, PC-8, CT-19).

## Por que existe

Es la ultima oportunidad barata de corregir la voz. Despues de esto se producen
decenas de escenas, y cambiar el estilo entonces cuesta reescribirlas todas.

**Ninguna escena se produce en serie antes de que el Autor decida sobre el piloto**
(INV-9). El hook `guard-canon` lo impone, asi que no es una convencion que se pueda
saltar por prisa.

## Que ensenar

Localiza el piloto y presenta las tres cosas juntas:

1. **El texto completo** de la escena.
2. **Su ficha en el Canon**: funcion narrativa, personajes, lugar, momento, hilos que
   avanza, presupuesto de palabras.
3. **Los parametros de estilo aplicados y su procedencia**: cuales declaro el Autor y
   cuales quedaron sin preferencia. Esto ultimo importa: si algo no le gusta de un
   parametro que nunca declaro, la respuesta no es corregir la escena, es declarar el
   parametro.

```
storymaker --proyecto <prj> traza pasaje --version-escena <esv>
storymaker --proyecto <prj> encargo estilo
```

## Las tres salidas

| Decision | Que pasa |
|---|---|
| `aprobar` | El piloto entra en la novela y **es la referencia de voz de toda la Ejecucion**. Arranca la produccion |
| `ajustar_estilo` | Vuelve a E1 a cambiar el parametro que el Autor senale, y se repite el piloto |
| `volver_al_canon` | Vuelve a E3: el problema no es como esta escrito, es que esta planificado |

```
storymaker --proyecto <prj> control resolver --id <pct> --decision <d> --quien "<nombre>" --elemento <parametro>
```

Cuando no es una aceptacion, **la decision identifica que debe cambiar**. "No me
convence" no es accionable por ninguna etapa.

## El tope

Hay tres ciclos de piloto por Ejecucion. Tres pilotos rechazados indican que el
desacuerdo esta en el Canon o en el Encargo, no en la redaccion: el cuarto se eleva
al Autor como decision, no como repeticion (ERR-408).

En modo autonomo, PC-8 no detiene nada, pero **el piloto se redacta y se registra
igualmente**: su valor como linea base de estilo no depende de que alguien lo lea.
