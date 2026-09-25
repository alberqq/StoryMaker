# Revisión humana

Cómo se revisa una novela de StoryMaker con la misma rúbrica que usa el juez, y qué se hace con lo que salga.

Esto es el protocolo de **P-122** y realiza §4.5 de [`verification.md`](verification.md). Es una capacidad de clase **I** —inspección— bajo la puerta **G2**: no bloquea una integración, pero sin ella no hay nada con lo que contrastar las notas del modelo, y un juez sin contraste es un número que nadie ha comprobado nunca.

---

## 1. Por qué existe

El juez es un agente que puntúa ocho criterios del 1 al 10, y de su media sale la decisión de publicar. Esa media gobierna una puerta, así que la pregunta obvia es quién juzga al juez.

La respuesta no puede ser otro modelo: eso solo mueve la pregunta un escalón. Tiene que ser una persona leyendo la novela entera. Y para que la comparación signifique algo, **la persona y el modelo tienen que estar respondiendo literalmente la misma pregunta**, no dos parecidas.

De ahí la única regla no negociable de este documento: **se puntúa desde [`rubrica.yaml`](../backend/src/storymaker/publication/rubrica.yaml), el fichero**, no desde una copia, un resumen ni un recuerdo de lo que pedía cada criterio. Si alguien reescribe los ocho criterios en una hoja aparte «para tenerlos a mano», la comparación deja de decir nada el día que el fichero cambie y la hoja no.

---

## 2. Cuándo se hace

- **Al menos una novela completa** revisada así antes de dar un hito por cerrado.
- **Una sesión de red-teaming manual por hito**, que se anota en [`red-team.md`](red-team.md) con su clase de evidencia.

Las dos son nocturnas en el sentido de G2: se hacen fuera del ciclo de integración, sin prisa, y un hallazgo abre defecto en lugar de detener a nadie.

---

## 3. El procedimiento

### 3.1 Antes de leer

Se necesita una novela **publicada**, con su versión y su manifiesto escritos. Sirve cualquiera de las tres formas de leerla: el PDF, la pantalla de impresión del frontend, o `storymaker estado <novela>` para localizar el número de versión y sacar el texto de la base.

**No se miran las notas del juez todavía.** Es la parte del procedimiento que más fácil se salta y la que más lo invalida: leer un 4 en «ritmo» antes de puntuar el ritmo contamina la nota, y lo que queda no es una revisión independiente sino un acuerdo fabricado. Las notas del juez se consultan **después** de tener las ocho propias escritas. La hoja que prepara la CLI no las lleva, y el acta las pone al lado solo al registrar.

### 3.2 Leyendo

Se lee la novela entera, seguida. No por muestreo: cinco de los ocho criterios —continuidad, arco, ritmo, tono y naturalidad de la personalización— son propiedades del conjunto y no se pueden juzgar sobre tres capítulos sueltos. Un objeto que cambia de sitio entre el capítulo 2 y el 9 solo lo ve quien ha leído los dos.

Conviene ir anotando al margen, con el número de capítulo, cualquier cosa que llame la atención. Al terminar, esas anotaciones son la materia prima de las ocho justificaciones.

### 3.3 Puntuando

Los ocho criterios, del 1 al 10, **cada uno con su justificación escrita**. La justificación no es un trámite: es lo que permite que la comparación con el juez sea por criterio y no por media, y es lo único que hace accionable una divergencia. «Ritmo: 5» no dice qué cambiar; «Ritmo: 5, los capítulos 4 a 6 repiten la misma función de aplazar la inspección» sí.

El umbral de publicación es **6.0 de media**, el mismo que aplica `supera_el_umbral`.

### 3.4 La hoja y el registro

Las dos cosas las hace la CLI, y ninguna de las dos toca la nota: la hoja la rellena la persona.

```bash
uv run storymaker revision hoja <novela>                 # la última versión publicada
uv run storymaker revision hoja <novela> --version 2     # o una concreta
```

Escribe `<novela>.v<n>.revision.yaml` al lado de la base, con un bloque por criterio —`valor` y `justificacion`, vacíos— y los campos del revisor y la duración de la lectura. **No copia las preguntas**, que se leen en `rubrica.yaml` por la regla de §1, **ni lleva las notas del juez**, por la de §3.1.

Con la hoja rellena:

```bash
uv run storymaker revision registrar <novela> <hoja.yaml> --acta acta.md
```

El registro rechaza una hoja a la que le falte o le sobre un criterio, con una nota que no sea un entero de la escala o con una justificación de menos de diez caracteres, y la de una versión que no esté publicada. Si la hoja vale:

- escribe el *score* `revision_humana` en la tabla `score` de la novela, al lado del del juez, con la media como valor y las notas, las justificaciones y el revisor en el detalle;
- lo envía a la sesión de Langfuse de la novela, con el mismo nombre;
- compone el acta con la forma de la plantilla de §5 —la tabla criterio a criterio con las dos notas, las dos medias y las divergencias de más de dos puntos— y la escribe en `--acta`, o la imprime si no se pasa.

El acta se añade a §5 de este documento, que es donde se acumulan, y se completa a mano con lo que la CLI no puede saber: qué se hace con cada divergencia y la sesión de red-teaming asociada.

---

## 4. Qué se hace con la divergencia

Este sistema **no reentrena nada**, y conviene no prometer más de lo que hay. Una divergencia entre la nota humana y la del juez tiene tres destinos posibles, y los tres son control, no aprendizaje:

| Qué se observa | Qué se hace |
|---|---|
| La persona puntúa sistemáticamente más bajo que el juez en un criterio | **Nueva versión del prompt del juez en Langfuse**, medida contra el eval anterior. Si no mejora, se revierte |
| La persona y el juez coinciden, y los dos puntúan bajo | El defecto está en la novela, no en la medición: va al hito como trabajo de la fase que lo produce |
| La persona detecta algo que la rúbrica no pregunta | Se propone un criterio nuevo **arriba**, en §11b de la arquitectura. La rúbrica no crece por el camino corto |

Un aviso sobre el segundo caso. La tentación al ver una nota baja es subir el rol del juez o ablandar el umbral. Eso no arregla la novela: la publica. El umbral está en el fichero de rúbrica precisamente para que moverlo sea un cambio visible y no un ajuste de paso.

Sobre la varianza del propio juez —el mismo juez puntuando dos veces la misma novela— no decide nada esta revisión: es la medida de *self-consistency* de G2 que declara [`verification.md`](verification.md) (N ejecuciones del juez sobre la misma novela), que hoy no tiene herramienta en el repositorio, y es un problema distinto. Conviene tener su número delante antes de concluir que una divergencia con la persona es sistemática: si el juez no se pone de acuerdo consigo mismo, no está discrepando de nadie.

---

## 5. Actas

Una entrada por sesión. Se añaden al final; las anteriores no se editan.

### Plantilla

```
### <fecha> · <novela> · versión <n>

**Revisor:** · **Duración de la lectura:**

| Criterio | Persona | Juez | Justificación de la persona |
|---|---|---|---|
| continuidad | | | |
| arco | | | |
| coherencia_de_personajes | | | |
| ritmo | | | |
| tono | | | |
| prosa | | | |
| naturalidad_de_la_personalizacion | | | |
| autenticidad_de_epoca | | | |
| **Media** | | | |

**Divergencias por encima de 2 puntos:**

**Qué se hace con ellas:**

**Sesión de red-teaming asociada:** RT-nn en `red-team.md`, o «ninguna».
```

### Actas registradas

### 2026-09-25 · eval-04-boda · versión 1

**Revisor:** Autor · **Duración de la lectura:** —

| Criterio | Persona | Juez | Justificación de la persona |
|---|---|---|---|
| continuidad | 9 | 7 | La trama fluye sin fisuras lógicas desde la llegada de la protagonista en el tren hasta la culminación del proyecto y la boda. Los saltos temporales siguen el avance real de la construcción de la Exposición. |
| arco | 8 | 9 | La protagonista tiene una evolución sólida: empieza como una técnica asustada que busca pasar desapercibida y termina asumiendo su genialidad como ingeniera principal sin renunciar a su identidad para casarse. |
| coherencia_de_personajes | 9 | 9 | Las motivaciones se mantienen firmes. La protagonista siempre mide sus pasos desde la lógica técnica; su pareja es un apoyo constante y respetuoso con su espacio; y Carles Buïgas actúa consistentemente como un genio estricto pero justo. |
| ritmo | 8 | 8 | Los saltos de meses (de junio a agosto, y luego a la urgencia de abril) están bien gestionados para no estancar la obra. El clímax del encendido es excelente, aunque la transición hacia los preparativos de la boda se siente ligeramente apresurada. |
| tono | 9 | 8 | Mantiene un registro épico, romántico y contenido. El tono equilibra muy bien la frialdad de la ingeniería (cables, relés, sincronización) con la calidez de la superación personal y el romance. |
| prosa | 8 | 7 | Las descripciones visuales del agua y los colores son inmersivas e impactantes («arco iris controlado», «fuego que quema pero no destruye»). Sin embargo, abusa ligeramente del recurso de comparar los sentimientos con circuitos eléctricos y sincronizaciones técnicas en los diálogos finales. |
| naturalidad_de_la_personalizacion | 10 | 7 | La novela es un regalo por la boda de la pareja homenajeada. La integración de sus nombres como los ingenieros protagonistas del relato es impecable, orgánica y central para la historia, sin sentirse como variables insertadas a la fuerza. |
| autenticidad_de_epoca | 9 | 8 | Ancla la historia perfectamente en la Barcelona de 1928-1929. La inclusión de la figura histórica de Carles Buïgas, la construcción en Montjuïc, la alusión a la sombra de Primo de Rivera y el escepticismo inicial ante una mujer técnico dotan al texto de gran verosimilitud. |
| **Media** | 8.75 | 7.88 | |

**Divergencias por encima de 2 puntos:**

- naturalidad_de_la_personalizacion: persona 10, juez 7 (+3)

**Qué se hace con ellas:** es una sola divergencia en una sola novela, y va en la dirección contraria a la que prevé §4: la persona puntúa **más alto** que el juez, no más bajo. El juez es más severo en naturalidad de la personalización (7 frente a 10) y, en menor medida, en continuidad (7 frente a 9). Con un solo punto no hay nada sistemático que corregir, así que no se sube una versión nueva del prompt del juez. Se anota como hipótesis para la siguiente revisión: el juez puede estar penalizando que los homenajeados sean protagonistas explícitos, justo lo que la persona valora más. En media, la persona da 8,75 y el juez 7,88. Los dos superan el umbral de 6,0, así que la decisión de publicar habría sido la misma.

**Sesión de red-teaming asociada:** la segunda ronda de [`red-team.md`](red-team.md), del mismo día (RT-07 y RT-08).

---

## 6. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-25 | §4 deja de enlazar `evals/varianza_juez.py`, que ya no existe, y remite a la medida de *self-consistency* de G2 en `verification.md`, declarando que hoy no tiene herramienta. Se comprueba que la rúbrica tiene ocho criterios (`rubrica.yaml`, con `tono`) y que la plantilla de §5 los recoge; la única mención a siete que queda es la de §5, que describe con qué rúbrica se juzgaron `lozoya`, `metro` y `pepa` | La auditoría del bloque 13 de `GAP-REPORT.md` encontró el enlace roto: el directorio `evals/` lo retiró el Autor, y un enlace a un fichero inexistente afirma una herramienta que no hay |
| 2026-09-25 | §3.4 se reescribe: **la hoja y el registro los hace la CLI** (`storymaker revision hoja` y `registrar`), que valida la hoja, deja el *score* en la base y en Langfuse y compone el acta. La rúbrica pasa a ocho criterios con `tono`, también en la plantilla | Registrar la nota era pegar código en una consola, y comparar con el juez era hacerlo a mano. Con la herramienta, lo único que queda es lo que tiene que hacer una persona |
| 2026-09-23 | Versión inicial: el protocolo de revisión con rúbrica y la plantilla de acta | P-122 declaraba este documento y no existía. Sin él, «una persona aplica la misma rúbrica que el juez» era una intención sin procedimiento: no decía desde qué fichero, ni en qué orden respecto a las notas del modelo, ni dónde se anota el resultado |
