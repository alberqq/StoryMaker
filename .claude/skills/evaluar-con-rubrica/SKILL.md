---
name: evaluar-con-rubrica
description: La rubrica por etapa, su escala y la regla de evaluar sin historial de iteraciones previas. Cargala antes de puntuar cualquier version de Canon, escena, capitulo o novela.
---

# Evaluar con rubrica

El arnes distingue entre lo que se **comprueba** y lo que se **juzga**, y no las
mezcla. Una Restriccion lexica se comprueba: o el termino aparece o no aparece, y el
nucleo lo decide sin ti. La solidez de un arco se juzga: no hay regla que la decida.

Esta skill es para lo segundo.

## La regla que hace comparables dos iteraciones

**Evalua sin el historial de iteraciones previas.**

No es una recomendacion de higiene. Un evaluador que ha visto las tres versiones
anteriores se ablanda por acumulacion: la cuarta le parece mejor porque recuerda lo
mala que era la primera. Entonces la convergencia que mide es la suya, no la del
texto, y el bucle cierra por una mejora que no ha ocurrido.

Por eso cada evaluacion declara `sin_historial: true`, y el nucleo **solo compara
evaluaciones que lo declaren**, con la misma version de rubrica y los mismos
criterios. Dos evaluaciones que no cumplan eso no se comparan, y la regresion no se
declara sobre ellas.

## La escala

Cada criterio se puntua de 0 a 10. El total es la media. La puntuacion solo sirve
para **comparar una version consigo misma**: quedarse con la mejor y detectar la
regresion.

**Ningun minimo convierte la rubrica en puerta.** Conviene decirlo claro porque es
una carencia conocida y no un olvido: un Canon coherente pero mediocre, o una novela
correcta y topica, pasan todos los controles. Los objetivos del arnes ponen la
coherencia y la verosimilitud por delante de la calidad de la prosa, y subordinan
esta ultima explicitamente. Convertir la rubrica en puerta es una decision funcional
pendiente (T-02): la maquinaria ya esta, falta el umbral.

Consecuencia para ti: **no uses la puntuacion para bloquear**. Lo que bloquea es un
hallazgo bloqueante, y para eso esta `emitir-hallazgo`.

## Criterios por etapa

### E4 -- Validacion del Canon

| Criterio | Que miras |
|---|---|
| `solidez_arco` | Hay progresion, o hay sucesion de escenas |
| `diferenciacion_personajes` | Se distinguen por algo mas que por el nombre |
| `integracion_historica` | La epoca esta en la trama, o es decorado |
| `fidelidad_encargo` | El plan responde a la semilla que el Autor trajo |
| `viabilidad` | La extension admite esta trama |

### E6 -- Refinamiento

| Criterio | Que miras |
|---|---|
| `precision_lexica` | La palabra exacta, no la aproximada |
| `variedad_sintactica` | Las frases no tienen todas la misma forma |
| `economia_adjetival` | Cada adjetivo hace algo |
| `ritmo` | La frase acompaña a lo que cuenta |
| `voz_personajes` | Cada uno habla como su ficha dice |

### E7 -- Validacion de capitulo

| Criterio | Que miras |
|---|---|
| `continuidad` | Nada contradice lo establecido |
| `verosimilitud_historica` | La mentalidad es la de la epoca, no la nuestra con ropa antigua |
| `cumplimiento_funcion` | La escena cumple su funcion, no solo la menciona |
| `tratamiento_sensible` | Se ajusta a la politica declarada en el Encargo |

### E8 -- Pasada global

| Criterio | Que miras |
|---|---|
| `unidad_de_voz` | El capitulo 1 y el 40 son del mismo libro |
| `ritmo_de_conjunto` | Los actos estan equilibrados |
| `cierre` | Lo que se planto, se resolvio, y estaba preparado |

## Forma

```json
{
  "version_rubrica": "rub_escena_v1",
  "sin_historial": true,
  "puntuaciones": {
    "precision_lexica": 7.5,
    "variedad_sintactica": 6.0,
    "economia_adjetival": 8.0,
    "ritmo": 7.0,
    "voz_personajes": 8.5
  }
}
```

La version de la rubrica se registra en el ledger de la Ejecucion. Cambiar la
rubrica a mitad de una novela rompe la comparabilidad, y por eso la version va
dentro de la evaluacion y no en un fichero de configuracion que nadie mira.
