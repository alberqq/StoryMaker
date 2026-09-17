# Ejemplos

Tres Encargos listos para ingerir y un recorrido completo del núcleo sin llamar a
ningún modelo. Sirven para dos cosas distintas: comprobar que la maquinaria muerde,
y arrancar una novela de verdad sin componer el Encargo a mano.

| Fichero | Qué es |
|---|---|
| [`encargo-revolucion-francesa.json`](encargo-revolucion-francesa.json) | **El peso del bronce.** Un fundidor de campanas en el París de 1793 |
| [`encargo-roma.json`](encargo-roma.json) | **La mano del copista.** Un copista griego en la Roma de Domiciano |
| [`encargo-tres-capitulos.json`](encargo-tres-capitulos.json) | El Encargo mínimo, con la conversión de líneas a palabras ya declarada |
| [`plan-tres-capitulos.json`](plan-tres-capitulos.json) | Un Canon de ejemplo. **En una Ejecución real lo produce `sm-diseno`** |
| [`prueba_tres_capitulos.py`](prueba_tres_capitulos.py) | El recorrido completo sin llamadas a modelo |

---

## El peso del bronce

Tres capítulos, 540 palabras. Un fundidor de campanas del faubourg Saint-Antoine
recibe el encargo de fundir en cañones las campanas que él mismo coló veinte años
antes, y reconoce su propia aleación en el metal que le traen.

Está escrito para **poner a trabajar las Restricciones de época**, que es la parte
del arnés más fácil de dar por buena sin comprobarla. El período elegido es un campo
de minas de anacronismos, y el Encargo declara cuatro de ellos en
`restricciones_autor` para que E2 no tenga que descubrirlos solo:

| Trampa | Por qué muerde |
|---|---|
| El sistema métrico | No existe en 1793. Se pesa en libras y se mide en pies y pulgadas de rey |
| El calendario republicano | Se introduce en octubre de 1793, a mitad del período. Los dos conviven un tiempo |
| El tratamiento | *Ciudadano* y *ciudadana*, no *señor* ni *señora* |
| Los asignados | El personaje cobra en papel que pierde valor mientras trabaja |

Es un buen caso para la categoría `lexica` **comprobable**: «kilogramo», «metro» y
«señor» son términos que se pueden barrer sobre el texto, y una Restricción léxica
comprobable está obligada a declarar sus `terminos_prohibidos`. El resto —la escasez
de estaño, el comité de vigilancia de la sección— cae en las categorías `material` e
`institucional`, que se evalúan con rúbrica.

La política de figuras reales prohíbe nombres propios históricos en escena pero
admite las instituciones. Es deliberado: obliga al diseño a sostener la tensión con
el oficio y con la sección, no con un cameo de Robespierre.

## La mano del copista

Dos capítulos, 600 palabras. Roma, años 85‑92. Un copista esclavo altera una palabra
de un testamento y el error echa a andar solo por los tribunales.

Más corto y más cerrado que el anterior. Su interés está en el **derecho testamentario
romano**: los siete testigos, el sellado, las *tabulae ceratae*. Un ámbito donde una
afirmación histórica falsa se propaga a toda la trama, que es justo lo que las
Restricciones existen para impedir.

## El Encargo mínimo

Tres capítulos, cuatro párrafos por capítulo, unas cuatro líneas por párrafo. En las
unidades del arnés:

| Lo que pides | En unidades del arnés |
|---|---|
| 4 líneas × 4 párrafos | 16 líneas por capítulo |
| Factor declarado en la captura (D28) | 11 palabras por línea |
| | **176 palabras por capítulo** |
| 3 capítulos | **528 palabras en total** |
| Repartidas en 2 escenas por capítulo | 6 escenas de 88 palabras |

**La línea no existe aguas abajo.** La palabra es la unidad canónica del arnés: la
conversión ocurre una vez, en la captura, y se conservan ambos valores más el factor
aplicado. Es lo que evita que una magnitud que depende de la maquetación contamine
los presupuestos y las métricas.

Los párrafos tampoco son una unidad del modelo. La unidad redactable es la
**escena** —un lugar, un tiempo continuo, una función narrativa declarada—. Dos
escenas de dos párrafos por capítulo es el reparto que mejor encaja sin inventar una
unidad nueva.

---

## Camino rápido: verificar la maquinaria

```bash
python ejemplos/prueba_tres_capitulos.py
python ejemplos/prueba_tres_capitulos.py --conservar   # lo deja en proyectos/
```

Recorre las etapas por la superficie del núcleo sin llamar a ningún modelo, y va
imprimiendo lo que cada puerta hace. Al final imprime la novela ensamblada.

Comprueba de paso que las puertas muerden de verdad: intenta redactar con el Canon en
borrador (`ERR-502`), derivar una Restricción de una afirmación descartada
(`ERR-606`, que es INV-8) y anexar un hecho que contradice otro (`ERR-601`).

**Lo que aquí son constantes —las afirmaciones históricas, el plan y la prosa— en una
Ejecución real lo producen los subagentes.** Esto no es el producto: es su banco de
pruebas.

## Camino real: que el arnés escriba la novela

### 1. Preparar el entorno, una sola vez

```bash
pip install -e .
```

Reinicia la sesión de Claude Code para que cargue `.claude/`: los subagentes, las
skills, los comandos y los hooks.

No hace falta configurar ninguna recuperación documental. Los servidores `sm-web` y
`sm-rag` se retiraron del arnés: E2 sale al exterior con `WebSearch` y `WebFetch`, y
la cobertura se declara reducida en el Contexto histórico.

### 2. Desde la interfaz gráfica

Es el camino más corto.

```bash
python gui/servidor.py     # http://127.0.0.1:8765
```

En **Componer Encargo**, sube el JSON que quieras de los tres. Manda sobre lo que
haya en el formulario, y el núcleo rechaza nombrándolo cualquier campo que no
conozca: no lo ignora ni lo corrige por su cuenta. Después, **Crear el Proyecto e
ingerir el Encargo**, confirmarlo, y arrancar desde *Proceso*.

La Ejecución se detiene **dos veces**: firmas el Contexto histórico y apruebas el
Canon. Nada más te pide nada.

### 3. O desde la sesión de Claude Code

```
/encargo @ejemplos/encargo-revolucion-francesa.json
/ejecutar --coste 25 --iteraciones 40
```

Con varios Proyectos en `proyectos/`, declara sobre cuál trabajan los hooks:

```bash
export STORYMAKER_PROYECTO=prj_...       # bash
$env:STORYMAKER_PROYECTO = "prj_..."     # PowerShell
```

Mientras corre:

```
/estado          # etapa, hallazgos, consumo y proyección
/traza esv_...   # de dónde salió un pasaje
/entrega         # cuando la novela cumpla las cinco condiciones de RF-077
/calibracion     # consumo real frente a presupuestado
```

---

## Qué esperar de una novela tan corta

Dos cosas se comportan distinto a esta escala, y las dos están declaradas en el
código, no disimuladas.

**La deriva de voz no se evalúa.** Comparar densidad adjetival entre dos muestras de
170 palabras mide la varianza del muestreo, no la voz. Por debajo de 1.000 palabras
por tercio el indicador se declara no evaluable, entrega sus valores como
informativos y no bloquea la entrega. Con una novela de verdad —33.000 palabras por
tercio— sí se mide.

**La tolerancia de extensión es proporcionalmente dura.** Un ±10 % sobre 540 palabras
son 54 palabras; sobre 100.000 son 10.000. Si el redactor se pasa un poco, se nota
mucho más aquí. Por eso los dos Encargos largos declaran `tolerancia_extension` a
0.15 en lugar de 0.10.
