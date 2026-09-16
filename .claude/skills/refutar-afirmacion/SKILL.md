---
name: refutar-afirmacion
description: Estrategia de busqueda inversa por tipo de afirmacion, la exigencia de fuente distinta y los cinco veredictos. Cargala antes de refutar cualquier afirmacion del Contexto historico.
---

# Refutar una afirmacion

Refutar no es comprobar. Comprobar es preguntarle a la fuente si dice lo que se le
atribuye -- eso es RF-100, y lo hace el investigador. Refutar es **buscar en una
direccion distinta, con la intencion de encontrar lo que la tumbe**.

La diferencia esta en la consulta. Quien comprueba busca la afirmacion; quien refuta
busca su contrario.

## La estrategia depende del tipo

### Existencial negativa: «no existia X en el periodo»

La mas facil de tumbar y la mas peligrosa si nadie lo intenta, porque es la que
produce Restricciones lexicas -- las que prohiben terminos -- y una Restriccion
lexica falsa censura la novela por nada.

**Basta una sola aparicion documentada.** Busca el termino en corpus del periodo, en
inventarios, en documentos notariales, en la lengua de la epoca. Busca tambien su
primera atestacion: si es posterior al periodo, la afirmacion aguanta; si es
anterior, cae.

### Existencial positiva: «existia X»

Dos frentes. Busca quien lo niegue, y busca **si X pertenece a otro periodo o a otro
lugar**: la confusion geografica es mas frecuente que la cronologica y casi nunca se
detecta, porque la fecha cuadra.

### Datacion: «X ocurrio en el ano N»

Busca dataciones alternativas y, sobre todo, **revisiones posteriores**. Las fechas
de manual son las que mas se han corregido en los ultimos cincuenta anos. Una fuente
de 1950 y una de 2015 sobre la misma fecha no valen lo mismo.

Atiende al calendario: juliano y gregoriano difieren, y el ano no empezaba en enero
en todas partes.

### Atribucion: «X lo hizo, lo dijo o lo escribio Y»

Busca otras atribuciones, disputas de autoria y atribuciones tradicionales sin
respaldo. Las citas celebres son el caso tipico: la mitad no son de quien se dice.

### Cuantitativa: «habia N de X»

Busca otras cifras **y el metodo con que se obtuvieron**. Una poblacion estimada a
partir de hogares con un multiplicador discutido no es un dato: es una estimacion
con un supuesto dentro. Si el metodo no consta, eso ya es un matiz.

### Cualitativa: «se pensaba que», «se sentia que»

Casi nunca es refutable documentalmente, y **decirlo es la respuesta correcta**. No
fuerces un veredicto de confirmada sobre algo que no se puede desmentir.

## Los cinco veredictos

| Veredicto | Cuando | Que puede sostener |
|---|---|---|
| `confirmada` | Buscaste en contra y no encontraste nada | Restriccion comprobable |
| `matizada` | Se sostiene con limites. Declara el alcance | Restriccion comprobable, dentro del matiz |
| `disputada` | Fuentes solventes en ambos sentidos | Nada comprobable |
| `refutada` | Una fuente distinta la desmiente | Nada. Y cae lo que sostenia |
| `no_refutable_documentalmente` | No hay documentacion que pueda desmentirla | **Solo criterio cualitativo** |

**El ultimo no es una confirmacion.** Mezclarlo con las que han resistido una
busqueda en contra enganaria a quien lea la entrega, que es exactamente a quien la
entrega existe para informar.

## Tres reglas que el nucleo impone

1. **Fuente distinta de la citada.** Una fuente contraria que ya esta entre las de
   la afirmacion no contradice nada: se apoya en lo mismo. El nucleo lo rechaza.
2. **Sin fuente contraria no hay refutacion.** Un veredicto de `refutada`,
   `matizada` o `disputada` sin fuente que lo sostenga no se registra.
3. **Las consultas son obligatorias**, con su texto, su modo, cuantos resultados
   examinaste y por que los descartaste. Son lo que impide que `confirmada`
   signifique `no se busco`.

## Forma de las consultas

```json
[
  {
    "consulta": "primera atestacion 'boligrafo' castellano siglo XVI",
    "modo": "web",
    "resultados_examinados": 12,
    "motivo_descarte": "todas las atestaciones son posteriores a 1888"
  }
]
```

## Registro

```
storymaker --proyecto <prj> contexto refutar \
  --afirmacion <aff> --veredicto <v> --tipo <tipo> \
  --consultas @consultas.json --fuente-contraria <fnt> [--alcance-matiz "..."]
```
