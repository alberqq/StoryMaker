---
name: voz-y-estilo
description: Como se lee la Guia de estilo efectiva y que significa exactamente un parametro sin preferencia. Cargala antes de redactar o refinar cualquier escena.
---

# Voz y estilo

## La regla que gobierna todo lo demas

**Un parametro sin preferencia no tiene valor por defecto.**

No significa "haz lo que te parezca dentro de lo normal". Significa que el Autor no
se pronuncio, que **el parametro no se evalua**, y que ningun agente puede aplicarle
un valor por detras. Si el refinador aplicara su preferencia a un parametro no
declarado, estaria convirtiendo una ausencia de decision del Autor en una decision
suya, y el Autor se enteraria leyendo.

Consecuencias concretas:

- El **redactor** escribe con naturalidad sobre los parametros no declarados, sin
  forzar ninguna direccion.
- El **refinador** no emite hallazgos sobre ellos. Si le molesta algo de un
  parametro no declarado, es un hallazgo **menor** -- una preferencia -- y no fuerza
  iteracion.
- El **validador** no los comprueba.

## Como se lee la guia

```
storymaker --proyecto <prj> encargo estilo
```

Devuelve tres cosas:

```json
{
  "declarados": {"persona_narrativa": "tercera", "tiempo_verbal": "pasado"},
  "no_evaluables": ["registro", "prohibiciones"],
  "hash": "..."
}
```

Solo `declarados` se comprueba. `no_evaluables` esta ahi para que sepas que **no**
tienes que comprobar, que es tan importante como saber que si.

El `hash` se registra en cada version de escena. Si la guia cambia -- porque el
Autor ajusto el estilo tras el piloto -- el hash cambia, y se puede saber que
escenas se escribieron bajo que voz.

## Los parametros

| Parametro | Que fija |
|---|---|
| `persona_narrativa` | Primera, segunda o tercera |
| `tiempo_verbal` | Pasado o presente |
| `registro` | Culto, neutro, coloquial, arcaizante |
| `densidad_descriptiva` | Cuanto espacio ocupa lo que se ve |
| `recursos_apertura` | In medias res, escena de encuadre, otros |
| `longitud_media_frase` | Objetivo en palabras |
| `prohibiciones` | Lo que el Autor no quiere leer |

## El piloto es la linea base

Una vez que el Autor acepta la escena piloto, **esa escena es la referencia de voz
de toda la Ejecucion**. Los parametros declarados dicen que se busca; el piloto
enseña como suena.

Si tu escena cumple todos los parametros y no suena al piloto, **es tu escena la que
se desvia**. La guia es una descripcion parcial de una voz; el piloto es la voz.

El piloto no se vuelve a redactar: entra en la novela como cualquier otra escena.

## Registro de epoca

La guia fija la voz del narrador, no la lengua del siglo XVI. Salvo que el Autor
pida `registro: arcaizante` de forma explicita, **se escribe en castellano
contemporaneo legible**, evitando los anacronismos lexicos que las Restricciones
prohiben pero sin imitar la prosa de la epoca.

Esos son dos ejes distintos y se confunden con facilidad: las Restricciones lexicas
dicen que palabras **no** pueden aparecer; el registro dice **como** suena la prosa.
Cumplir las primeras no obliga a arcaizar la segunda.

## Voz de personaje

Cada personaje declara su voz en su ficha del Canon. Eso si se comprueba siempre, y
un personaje fuera de su voz declarada es un hallazgo **mayor** -- no menor --
porque afecta a algo que el Canon fijo, no a una preferencia no declarada.
