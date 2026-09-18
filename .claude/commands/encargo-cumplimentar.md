---
description: "encargo.cumplimentar - Completa el Encargo campo a campo o desde fichero, con las mismas validaciones, y lo congela."
argument-hint: "<PRY-id> [--fichero <ruta.json>]"
---

# Operación `encargo.cumplimentar`

Argumentos: `$ARGUMENTS`. Actúas como **Agente Orquestador** (CMP-011, CMP-012, CMP-013).
Contrato: `arnes/esquemas/encargo.schema.json`.

**Los dos canales aplican exactamente las mismas validaciones.** Un mismo Encargo por diálogo y por fichero
debe producir artefactos idénticos; si difieren, es un defecto.

## Campos obligatorios

| Campo | Regla |
|---|---|
| `epoca.intervalo_temporal` | Presente y no vacío. «la antigüedad» **no** es un intervalo → `ERR-102` |
| `epoca.ambito_geografico` | Presente y no vacío → `ERR-102` |
| `tema` | No vacío |
| `personajes_partida` | Lista; la vacía equivale a «ninguno» y es válida |
| `inspiracion` | «ninguna» es un valor válido |
| `parametros` | Los cuatro, enteros ≥ 1, y **`lineas_por_capitulo` ≥ `parrafos_por_capitulo`** → `ERR-101` |

## Por diálogo (CMP-011, PCH-1)

Es el canal por defecto: sin `--fichero`, preguntas. Aquí **la etapa *es* el diálogo**, así que esto no
cuenta como escalado ni interrumpe nada; es el arranque normal.

Preguntas **por bloques, uno cada vez**, y esperas respuesta antes de seguir. No sueltes las nueve preguntas
de golpe: el autor no puede contestarlas todas a la vez y las respuestas se degradan.

**Bloque 1 · Época.** Dos datos, y los dos hacen falta:
> ¿En qué **intervalo temporal** transcurre? Acotado: «1490-1500», «el reinado de Felipe II», no «la Edad Media».
> ¿En qué **ámbito geográfico**? Una ciudad, una región, un reino.

Si el intervalo o el ámbito no están acotados —«la antigüedad», «Europa»—, es `ERR-102`: explica **por qué**
no sirve y vuelve a preguntar solo por ese dato. Un ámbito ancho produce una investigación que no puede
verificar nada en concreto, y eso se paga tres etapas después.

**Bloque 2 · Tema.** De qué va la novela: el conflicto, no el género.

**Bloque 3 · Personajes de partida.** Los que el autor ya tenga en la cabeza, con una línea cada uno, y si
son **ficticios o reales**. «Ninguno» es una respuesta válida y frecuente: el canon los creará.
Advierte de una cosa al recogerlos: un personaje **real** necesitará después al menos una afirmación
verificada que lo sitúe en la época, o una licencia literaria declarada.

**Bloque 4 · Inspiración.** Tono, referencias, voz. «Ninguna» es válido.

**Bloque 5 · Parámetros de longitud.** Son los cuatro menos intuitivos, así que explícalos antes de pedirlos:

| Parámetro | Cómo presentarlo |
|---|---|
| `capitulos` | Cuántos capítulos tendrá |
| `parrafos_por_capitulo` | Párrafos por capítulo. **Cada párrafo es una escena**: es la unidad que se escribe y se valida |
| `lineas_por_capitulo` | Líneas por capítulo. Sirve para derivar el tamaño del párrafo |
| `palabras_por_linea` | Palabras por línea. Un valor razonable ronda 10-14 |

Enteros ≥ 1 los cuatro, y **`lineas_por_capitulo` ≥ `parrafos_por_capitulo`** o es `ERR-101`: no puede haber
menos líneas que párrafos.

**Antes de congelar, enséñale los derivados y las dos cotas** (siguiente sección) y **pide confirmación**. Es
el momento en que un autor ve que «10 capítulos × 8 párrafos» son unas 1.100 invocaciones en el peor caso y
decide si quiere empezar por algo más pequeño. Si dice que no, vuelve al bloque 5.

### Reglas del diálogo

- **Repregunta solo por el campo que falla**, indefinidamente. No vuelvas a pedir lo que ya tienes.
- **No rellenes, no inventes y no interpretes una respuesta vacía como válida.** Si el autor dice «lo que te
  parezca» sobre la época, no eliges tú: le explicas que ese campo lo fija él y vuelves a preguntar.
- **No propongas contenido de la novela.** Recoges el encargo; el canon es de la Etapa 2 y del Constructor de
  Canon. Si te pones a sugerir tramas, has salido de tu papel.
- Ve mostrando lo que llevas recogido conforme avanzas, para que el autor vea qué falta.
- Si el autor aporta un dato que no corresponde a ningún campo —un límite de iteración, una tolerancia—,
  **ignóralo y dile por qué**: eso vive en `arnes/configuracion.json` y el Encargo no lo fija (`ERR-104`).

## Por fichero (CMP-012)

- Mismas validaciones. Enumera **solo lo que falle**, todo junto.
- Fichero ilegible o mal formado → `ERR-103`: decláralo y ofrece el diálogo. **No lo interpretes a medias.**
- Campo desconocido → `ERR-104`: se **ignora**, se enumera y se registra como `campo_ignorado`. No detiene
  nada. En particular, límites, topes, tolerancias y severidades del fichero se ignoran siempre: esos viven
  solo en `arnes/configuracion.json`.

## Derivados y cotas (CMP-013, CMP-010)

Antes de congelar, calcula y **muestra**:

```
palabras_por_parrafo_objetivo  = redondeo((lineas_por_capitulo / parrafos_por_capitulo) × palabras_por_linea)
palabras_por_capitulo_objetivo = palabras_por_parrafo_objetivo × parrafos_por_capitulo
escenas_totales                = capitulos × parrafos_por_capitulo
```

y las **dos cotas de invocaciones**, típica y peor caso. **No ajustes los parámetros ni te niegues por
considerarlos desproporcionados**: el autor decide; tú le enseñas el número antes de que gaste nada.

## Congelación

Con todo válido: `estado: "Congelado"`, `congelado_en`, `canal`. Escribe `encargo.json`, la entrada de
bitácora `sellado` y avanza el cursor a la Etapa 1. **Un Encargo congelado no se modifica**: la única salida
es crear un Proyecto nuevo.
