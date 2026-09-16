# Ejemplos

Una novela de prueba de **3 capítulos, 4 párrafos por capítulo y ~4 líneas por
párrafo**. En las unidades del arnés, eso es:

| Lo que pediste | En unidades del arnés |
|---|---|
| 4 líneas por párrafo × 4 párrafos | 16 líneas por capítulo |
| Factor declarado en la captura (D28) | 11 palabras por línea |
| | **176 palabras por capítulo** |
| 3 capítulos | **528 palabras en total** |
| Repartidas en 2 escenas por capítulo | 6 escenas de 88 palabras |

La línea no existe aguas abajo. La palabra es la unidad canónica del arnés: la
conversión ocurre **una vez, en la captura**, y se conservan ambos valores más el
factor aplicado. Es lo que evita que una magnitud que depende de la maquetación
contamine los presupuestos y las métricas.

Los párrafos tampoco son una unidad del modelo: la unidad redactable es la
**escena** —un lugar, un tiempo continuo, una función narrativa declarada—. Dos
escenas de dos párrafos por capítulo es el reparto que mejor encaja con lo que
pediste sin inventar una unidad nueva.

## Camino rápido: verificar la maquinaria

```bash
python ejemplos/prueba_tres_capitulos.py
python ejemplos/prueba_tres_capitulos.py --conservar   # lo deja en proyectos/
```

Recorre las ocho etapas por la superficie del núcleo sin llamar a ningún modelo, y
va imprimiendo lo que cada puerta hace. Al final imprime la novela ensamblada.

Comprueba de paso que las puertas muerden de verdad: intenta redactar con el Canon
en borrador (`ERR-502`), producir en serie sin piloto aceptado (`ERR-502`), derivar
una Restricción antes de verificar la fidelidad (`ERR-605`) y anexar un hecho que
contradice otro (`ERR-601`).

**Lo que aquí son constantes —las afirmaciones históricas, el plan y la prosa— en
una Ejecución real lo producen los subagentes.** Esto no es el producto: es su banco
de pruebas.

## Camino real: que el arnés escriba la novela

Aquí los agentes investigan, diseñan y redactan de verdad.

### 1. Preparar el entorno, una sola vez

```bash
pip install -e .
```

Reinicia la sesión de Claude Code para que cargue `.claude/`: los subagentes, las
skills, los comandos y los hooks.

### 2. Declarar sobre qué Proyecto trabajan los hooks

Los hooks necesitan saber de qué Proyecto hablas. Con un solo Proyecto en
`proyectos/` lo deducen; con varios, decláralo:

```bash
export STORYMAKER_PROYECTO=prj_...       # bash
$env:STORYMAKER_PROYECTO = "prj_..."     # PowerShell
```

### 3. Recuperación documental

E2 es la única etapa que sale al exterior. Sin al menos un modo de recuperación, la
etapa falla con `ERR-803`: redactar sin contexto contradice el segundo objetivo del
arnés.

```bash
export SM_RAG_CORPUS=/ruta/a/tu/corpus    # funciona sin nada más
export SM_WEB_PROVEEDOR=brave             # opcional
export SM_WEB_API_KEY=...                 # se resuelve del entorno, nunca se persiste
```

Con solo uno de los dos, el investigador degrada y **declara la cobertura reducida**
en el Contexto histórico.

### 4. El recorrido

```
/encargo @ejemplos/encargo-tres-capitulos.json
/ejecutar --coste 25 --iteraciones 40
```

A partir de ahí, `/ejecutar` despacha la etapa que toque. Se detendrá en los puntos
de control:

| Punto | Qué decides | Comando |
|---|---|---|
| PC-2 | Confirmar el Encargo | `/encargo` |
| PC-3 | Aprobar el Canon | `/control` |
| PC-8 | La escena piloto | `/piloto` |

Mientras tanto:

```
/estado          # etapa, hallazgos, consumo y proyección
/traza esv_...   # de dónde salió un pasaje
/entrega         # cuando la novela cumpla las cinco condiciones de RF-077
/calibracion     # consumo real frente a presupuestado
```

## Qué esperar de una novela tan corta

Dos cosas se comportan distinto a esta escala, y las dos están declaradas en el
código, no disimuladas:

**La deriva de voz no se evalúa.** Comparar densidad adjetival entre dos muestras de
170 palabras mide la varianza del muestreo, no la voz. Por debajo de 1.000 palabras
por tercio el indicador se declara no evaluable, entrega sus valores como
informativos y no bloquea la entrega. Con una novela de verdad —33.000 palabras por
tercio— sí se mide.

**La tolerancia de extensión es proporcionalmente dura.** ±10 % sobre 528 palabras
son 53 palabras; sobre 100.000 son 10.000. Si el redactor se pasa un poco, se nota
mucho más aquí. Si te estorba para probar, sube `tolerancia_extension` en el
encargo.

## Ficheros

| Fichero | Qué es |
|---|---|
| [`encargo-tres-capitulos.json`](encargo-tres-capitulos.json) | El Encargo, con la conversión de líneas a palabras ya declarada |
| [`plan-tres-capitulos.json`](plan-tres-capitulos.json) | Un Canon de ejemplo. **En una Ejecución real lo produce `sm-diseno`** |
| [`prueba_tres_capitulos.py`](prueba_tres_capitulos.py) | El recorrido completo sin llamadas a modelo |
