---
name: emitir-hallazgo
description: La forma canonica de un hallazgo -- severidad, causa raiz, localizacion, accion exigida y evidencia -- y por que su identidad excluye el enunciado. Cargala antes de criticar cualquier artefacto.
---

# Emitir un hallazgo

Un hallazgo no es una opinion sobre un texto. Es un **defecto localizado con una
accion exigida**, y esa diferencia es lo que permite que un bucle converja: sobre
una opinion no se puede decidir si se resolvio.

## Las cinco piezas, y ninguna es opcional

| Pieza | Que es | Por que |
|---|---|---|
| `severidad` | bloqueante, mayor o menor | Decide si fuerza iteracion |
| `causa_raiz` | entrada, investigacion, diseno, redaccion, refinamiento | Decide a que etapa va |
| `localizacion` | Escena, pasaje, elemento del Canon | Sin ella no es accionable |
| `accion_exigida` | Que hay que hacer, no que esta mal | Sin ella el redactor adivina |
| `evidencia` | La restriccion, el hecho o la ficha que se incumple | Sin ella no es verificable |

Un bloqueante **sin localizacion el nucleo lo rechaza por contrato**. Una critica
sin pasaje identificable no es un hallazgo: es una preferencia, y nace menor.

## La escala de severidad, que no negocias

| Severidad | Que la merece | Efecto |
|---|---|---|
| **Bloqueante** | Anacronismo; contradiccion con el Canon o con lo escrito; revelacion anticipada; hilo que no avanza cuando debia; afirmacion historica sin respaldo ni licencia | Impide cerrar la unidad |
| **Mayor** | Personaje fuera de su voz declarada; funcion narrativa a medias; desviacion de un parametro **declarado** de estilo; extension fuera de tolerancia | Fuerza iteracion mientras haya presupuesto |
| **Menor** | Preferencia sobre un parametro no declarado; adjetivo mejorable; observacion sin pasaje identificable | No fuerza iteracion |

El nucleo **impone la escala canonica sobre lo que propongas**. Un anacronismo es
bloqueante lo llames como lo llames. Elevar si se admite -- elevar nunca relaja una
puerta -- pero rebajar, no.

Los menores se acumulan, y su acumulacion por encima del umbral eleva un **mayor
agregado**. Es la valvula que da sentido a que un menor no fuerce iteracion: no la
fuerza uno, pero doce si, porque doce ya no son ruido.

## Causa raiz: el enrutado

| Causa raiz | Destino | Cuando |
|---|---|---|
| `entrada` | E1 | El Encargo pide algo imposible o contradictorio |
| `investigacion` | E2 | Falta el dato, o la fuente no sostiene lo que se le atribuye |
| `diseno` | E3 | La ficha de la escena es irrealizable, o el plan se contradice |
| `redaccion` | E5 | **La ruta por defecto.** El texto no cumple lo planificado |
| `refinamiento` | E6 | El refinado rompio algo que estaba bien |

Atribuir a diseno lo que es de redaccion reabre el Canon sin necesidad, y eso
invalida capitulos ya validados. Atribuir a redaccion lo que es de diseno produce un
bucle que no converge, porque el redactor no puede arreglar lo que no depende de el.

## La identidad, y por que no lleva tu enunciado

El identificador de un hallazgo se calcula sobre **(unidad, categoria, elemento
senalado normalizado)**. Deja fuera dos cosas que parecerian naturales:

- **El enunciado**, porque lo redactas tu y cambia entre iteraciones.
- **Los desplazamientos de caracter**, porque se mueven en cuanto el redactor
  corrige el texto de mas arriba.

Con cualquiera de los dos dentro, el mismo defecto reaparecido recibiria identidad
nueva y **el estancamiento no se detectaria jamas**: el mecanismo fallaria justo en
el momento para el que se diseno.

Consecuencia practica: **el `elemento_senalado` importa mas que la descripcion**.
Pon ahi el termino anacronico, el nombre del personaje, el identificador del hilo.
Eso es lo que sobrevive a que el parrafo se reescriba.

## Forma

```json
{
  "unidad": "cap_003",
  "categoria": "anacronismo",
  "elemento_senalado": "reloj de pulsera",
  "severidad": "bloqueante",
  "causa_raiz": "redaccion",
  "descripcion": "La escena menciona un reloj de pulsera en 1560.",
  "accion_exigida": "Sustituir por una referencia horaria de epoca.",
  "evidencia": "rst_a1b2c3d4e5f6",
  "localizacion": {"escena": "esc_003_002", "fragmento": "miro su reloj"}
}
```

```
storymaker --proyecto <prj> hallazgo emitir --hallazgos @lote.json
```
