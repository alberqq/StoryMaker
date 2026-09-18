# Especificación de mejoras de optimización

**Versión 1.0 · 17 de septiembre de 2026**

Este documento recoge **sólo mejoras**. No describe el arnés —para eso están la
Funcional y la Técnica— ni propone funcionalidad nueva: todo lo que hay aquí sale de
mirar la observabilidad de las Ejecuciones reales en Langfuse y preguntarse dónde se
va el dinero y el tiempo.

Cada mejora lleva su **evidencia medida**. Ninguna se propone por intuición, y las que
no he podido medir están marcadas como tales. Una mejora sin número detrás es una
opinión, y de esas el proyecto ya tiene bastantes.

---

## 1. La línea base

Todo lo que sigue se compara contra esto. Son datos reales de las Ejecuciones del 16 y
17 de septiembre de 2026, leídos de `/api/public/v2/metrics`.

### 1.1 Reparto del gasto entre el conductor y los subagentes

El **conductor** es la sesión de `claude -p` que dirige cada tramo: lee el prompt,
despacha subagentes y llama al núcleo. **No escribe una sola línea de prosa.** Los
**subagentes** son las etapas que sí hacen el trabajo.

| Tramo | Conductor | tokens | Subagentes | tokens | % conductor |
|---|---|---|---|---|---|
| `tramo_contexto` | $6,22 | 1.247.238 | $1,59 | 2.657.203 | **79,7 %** |
| `tramo_novela` | $5,56 | 1.025.841 | $0,46 | 84.566 | **92,3 %** |
| `tramo_canon` | $4,86 | 2.237.686 | $1,04 | 3.573.452 | **82,3 %** |
| **Total** | **$16,65** | | **$3,09** | | **84,3 %** |

**El 84,3 % del gasto se lo lleva quien no escribe.** En el tramo de la novela llega al
92,3 %: el conductor cuesta $5,56 y los subagentes que redactan, refinan y validan la
novela entera cuestan $0,46.

Y mueve doce veces más tokens que ellos: 1.025.841 frente a 84.566.

**Cómo está medido, y por qué eso importa.** Esta tabla se obtuvo **deduciendo el rol
del modelo**: el conductor corría en `opus`, los subagentes en `haiku`, así que bastaba
sumar por modelo. La deducción tiene un defecto grave: **deja de funcionar en cuanto se
aplique MEJ-01**, porque si el conductor pasa a `haiku` ya no hay forma de separarlo de
los subagentes. La medida que justifica el cambio se rompería al hacer el cambio.

Desde la versión técnica 2.13 la atribución es **exacta y no depende del modelo**. Cada
mensaje del flujo `stream-json` trae `parent_tool_use_id`: vale `null` en los del
conductor y trae el identificador de la llamada `Task` en los del subagente que esa
llamada despachó. El consumo se reparte por ahí, y cada span de tipo `agent` lleva sus
propios tokens. Las cifras de esta tabla son las últimas obtenidas por deducción; las
próximas ya serán medidas.

### 1.2 De qué está hecho el coste del conductor

Medido lanzando sesiones mínimas de un solo paso:

```
claude -p "usa WebFetch sobre example.com"
  claude-opus-5[1m]   in=6   out=264   cacheR=118.166   $0,215
```

Seis tokens de entrada real y **118.166 de lectura de caché**. El conductor no paga por
lo que escribe: paga por arrastrar su contexto en cada turno. Una sesión trivial cuesta
ya $0,22 sólo por existir.

### 1.3 Una Ejecución completa

`Ejecucion · El cartógrafo de Amberes`, 1h 31m 24s, **$8,51**:

| Paso | Duración | Coste |
|---|---|---|
| Contexto histórico | 22m 39s | **$5,50** |
| *Parada: el Autor acepta el Contexto* | 6m 43s | — |
| Cierre del Contexto y Canon | 11m 35s | **$3,01** |
| *Parada: PC-3, el Autor aprueba el Canon* | 20m 26s | — |
| Novela y entrega | 30m 00s | **ERROR, coste perdido** |

**27 de los 91 minutos eran el Autor decidiendo.** Y el tramo de la novela murió en el
límite de media hora sin emitir su evento `result`, de modo que todo lo que gastó
redactando **no aparece en esos $8,51**: se pagó y no se contabilizó.

### 1.4 Trabajo pagado dos veces

Del Run Ledger de *El cartógrafo de Amberes*:

| Unidad | Veces | Modos de cierre de la Ejecución |
|---|---|---|
| `sm-validador` sobre `cap_encargo` | **3** | 18 convergencia, **2 regresión** |
| `sm-redactor` sobre `esc_trabajo` | **2** | |

Tres unidades de más en una novela de 503 palabras.

---

## 2. Las mejoras

Por orden de impacto esperado.

### MEJ-01 — Bajar el modelo del conductor

- **Enunciado:** el modelo de la sesión que conduce cada tramo se declara
  explícitamente y se fija en uno más barato que el de los subagentes que despacha,
  en lugar de heredar el modelo por defecto de Claude Code.
- **Evidencia:** §1.1. El conductor es el **84,3 %** del gasto total y el **92,3 %**
  del tramo de la novela, corriendo en `claude-opus-5[1m]` mientras los siete
  subagentes declaran `haiku`.
- **Justificación:** el trabajo del conductor es orquestación: seguir un
  procedimiento escrito, despachar etapas en orden y llamar al núcleo. No genera
  prosa, no juzga calidad y no toma ninguna decisión narrativa —esas están en los
  subagentes y en el Autor—. Pagar el modelo más caro del catálogo por repartir
  trabajo es exactamente lo contrario de lo que el arnés hace con las etapas, donde
  cada una lleva su modelo declarado en su fichero.
- **Impacto estimado:** si el conductor bajara a `haiku`, y suponiendo la misma
  cantidad de tokens, el gasto total pasaría del orden de $19,74 a **unos $6**. La
  suposición es fuerte y hay que comprobarla, no darla por buena.
- **Riesgo:** un modelo más pequeño puede seguir peor un prompt de treinta líneas con
  bucles anidados —saltarse un paso, no cerrar una unidad, inventar una salida—. Es
  un riesgo real y es la razón por la que esta mejora se mide antes de adoptarse.
- **Cómo se mide:** lanzar el mismo Encargo dos veces, una con cada modelo de
  conductor, y comparar tres cosas: coste total, si la Ejecución llega al final sin
  intervención, y cuántas unidades se repiten. El reparto conductor/subagentes se lee
  ahora de `tokens_por_rol` en `tmp/consumo/<prj>.jsonl` y de los `usage_details` de
  cada span, no del modelo, de modo que la comparación sigue siendo válida **después**
  de bajar el modelo del conductor.
- **Coste de implementación:** bajo. Es un argumento en la invocación de `claude -p`
  en `gui/proceso.py`.

### MEJ-02 — Trocear el tramo de la novela por capítulo

- **Enunciado:** el tercer tramo deja de ser una sola sesión para la novela entera y
  pasa a ser una sesión por capítulo, más una final para la pasada global y la
  entrega.
- **Evidencia:** §1.1. En `tramo_novela` el conductor mueve **1.025.841 tokens** y los
  subagentes **84.566**: doce veces más. Y §1.2: lo que se paga son lecturas de caché,
  es decir, contexto acumulado releído en cada turno.
- **Justificación:** cada resultado de subagente vuelve al contexto del conductor y se
  queda ahí el resto del tramo. Con veinte despachos, el coste del contexto crece con
  el cuadrado del número de despachos. **Es el riesgo R-01 de la Funcional
  reapareciendo en otro sitio**: el arnés lo resolvió para el redactor con los
  manifiestos de §3, y lo ha reintroducido en quien despacha al redactor.
- **Contra qué hay que pesarlo:** la conducción pasó de ocho sesiones a tres
  precisamente para no pagar la reorientación de cada arranque. Pero ahora esa cifra
  está medida: **$0,22 por arranque** (§1.2), frente a una cola cuadrática que en un
  solo tramo ha llegado al millón de tokens. Con tres capítulos el cambio ya sale a
  favor; con treinta no hay comparación.
- **Impacto estimado:** en el tramo de la novela, reducción del contexto del conductor
  proporcional al número de capítulos. No se estima en euros porque depende de la
  extensión, y una cifra inventada aquí valdría menos que ninguna.
- **Riesgo:** un conductor por capítulo no ve los capítulos anteriores. No debería
  necesitarlos —para eso están las sinopsis congeladas— pero hay que comprobar que el
  arranque de cada sesión recibe lo que necesita para no repetir trabajo.
- **Cómo se mide:** tokens del conductor por capítulo, que deben quedar planos en
  lugar de crecer.

### MEJ-03 — Que el subagente no devuelva la prosa al conductor

- **Enunciado:** el resultado que un subagente devuelve al conductor se limita a lo
  que el conductor necesita para decidir el paso siguiente: identificadores, veredicto
  y hallazgos. El texto de la escena viaja al núcleo, no de vuelta.
- **Evidencia:** indirecta, y así se declara. Se deduce de §1.1 —el conductor acumula
  doce veces más tokens que los subagentes— pero **no está medido por separado** qué
  parte de esa acumulación es prosa devuelta. Medirlo es el primer paso de esta
  mejora.
- **Justificación:** una escena persistida ya está en el almacén y es recuperable por
  identificador. Devolverla además por el canal del conductor la mete en un contexto
  que se relee en cada turno hasta el final del tramo, y no aporta nada: el conductor
  no la lee, sólo la arrastra.
- **Riesgo:** bajo. Si el conductor necesitara el texto para algo, puede pedirlo al
  núcleo.
- **Cómo se mide:** comparar los tokens de entrada del conductor antes y después, a
  igual número de despachos.

### MEJ-04 — Persistir el consumo real en el Run Ledger

- **Enunciado:** el consumo que Claude Code reporta en su evento `result` —coste y
  tokens por modelo— se registra en el ledger mediante `unidad llamada`, en lugar de
  enviarse únicamente a Langfuse.
- **Evidencia:** `consumo.jsonl` escribe hoy `"coste": 0.0` y `tokens: 0` de forma
  literal. El informe de calibración de **RF-079** sale por tanto a cero en todas las
  Ejecuciones. Y §1.3: el tramo que murió en el límite de tiempo perdió su gasto
  entero de la contabilidad, porque nunca emitió el evento del que se lee.
- **Justificación:** esta mejora no ahorra un céntimo, y aun así va aquí porque **sin
  ella las demás no se pueden evaluar**. Una optimización cuyo efecto sólo se puede
  comprobar en un servicio externo, con credenciales, que ya cambió de API una vez y
  apaga la anterior en noviembre de 2026, no es una optimización medible. El dato ya
  está en la mano del orquestador: sólo hay que escribirlo.
- **Impacto:** nulo en coste, **prerrequisito de todo lo demás**.
- **Riesgo:** ninguno conocido. Es escribir en un fichero de sólo anexión.
- **Estado: implementado parcialmente** en la versión técnica 2.13. El consumo se
  escribe en `tmp/consumo/<proyecto>.jsonl` antes de enviarse a Langfuse, con el
  reparto por rol; se acumula durante el flujo, de modo que una etapa que muere sin
  emitir `result` conserva sus tokens marcados como parciales; y los spans que no se
  pueden exportar se apartan en `tmp/trazas_sin_enviar/` en vez de perderse. Queda
  fuera el Run Ledger propiamente dicho, porque `unidad llamada` exige un
  identificador de unidad y el gasto de un conductor no pertenece a ninguna.

### MEJ-05 — Acotar lo que la investigación trae de internet

- **Enunciado:** la etapa E2 declara un tope de fuentes recuperadas por sección del
  Contexto, y el contenido conservado entra en el contexto del agente recortado a lo
  que sostiene cada afirmación, no entero.
- **Evidencia:** §1.1. `tramo_contexto` es el tramo más caro en total ($7,81) y el que
  más tokens de subagente mueve con diferencia: **2.657.203**, tres veces los del
  tramo de la novela. §1.3 lo confirma en una Ejecución concreta: el Contexto fue el
  **65 %** del coste.
- **Justificación:** cada página recuperada entra entera en el contexto del
  investigador. Es el único sitio del arnés donde entra material externo sin ninguna
  cota declarada, y se nota.
- **Riesgo:** un tope demasiado bajo empobrece el Contexto, y el Contexto es lo que
  sostiene las Restricciones de época. Esta mejora **no** debe implementarse sin fijar
  antes cuál es el tope, y el criterio no puede ser el coste: tiene que ser la
  cobertura de las cinco secciones obligatorias.
- **Cómo se mide:** tokens de subagente en `tramo_contexto` frente al número de
  afirmaciones con fuente. Si el segundo baja con el primero, el tope está mal puesto.

### MEJ-06 — Reducir el trabajo pagado dos veces

- **Enunciado:** cuando el validador devuelve un capítulo, el hallazgo que lo motivó
  viaja al redactor con su localización y su acción exigida, y el redactor corrige
  **sólo** la escena señalada.
- **Evidencia:** §1.4. En una novela de 503 palabras, `sm-validador` se despachó tres
  veces sobre el mismo capítulo y `sm-redactor` dos sobre la misma escena, con dos
  cierres por **regresión**.
- **Justificación:** cada vuelta es una unidad entera pagada otra vez. Dos cierres por
  regresión significan que una versión evaluó peor que la anterior: el bucle no sólo
  no convergía, iba hacia atrás.
- **Estado:** **diagnosticable desde ahora.** Los spans de tipo `agent` que la traza
  emite desde la versión 2.11 registran cada despacho con su etapa y su tarea, de modo
  que en la próxima Ejecución se puede ver exactamente qué capítulo se validó tres
  veces y por qué. **Hasta tener ese dato, esta mejora no tiene solución concreta que
  proponer**, sólo el problema medido.

### MEJ-07 — Identificar el tercer modelo

- **Enunciado:** determinar qué componente consumió `claude-sonnet-5` en el
  `tramo_contexto` del 16 de septiembre y, si no está justificado, eliminarlo.
- **Evidencia:** $2,35 y 83.501 tokens, el **28 %** de esa Ejecución, en un modelo que
  ninguna pieza del arnés declara. La forma del consumo es anómala: 116 tokens de
  entrada y 83.385 de salida.
- **Descartado por medición:** no es `WebFetch` (declara opus + haiku), no es
  `WebSearch` (opus + haiku), no es un `Task` a un agente genérico (opus + haiku), y
  no son los subagentes, que declaran `haiku` tanto en disco como en la versión
  comiteada.
- **Estado:** **sin explicación.** La hipótesis en pie es que algún despacho resolvió
  su modelo al valor por defecto del entorno en aquel momento. Se resolverá con la
  próxima Ejecución: los spans `agent` dirán qué etapa lo consumió, o el modelo no
  volverá a aparecer y era una particularidad de aquella tirada.

---

## 3. Lo que queda fuera a propósito

| Asunto | Por qué no está aquí |
|---|---|
| Recortar el tiempo de las paradas del Autor | No es tiempo del arnés. Ya se contabiliza aparte y no consume presupuesto |
| Poner un límite de tiempo por etapa | Se retiró tras matar dos veces el tramo de la novela en el tope. Un reloj que no distingue una etapa colgada de una etapa larga corta más trabajo bueno del que salva |
| Bajar el modelo de los subagentes | Ya están todos en `haiku`, el más barato. Y son el 15,7 % del gasto: no hay nada que rascar ahí |
| Reducir las llamadas al núcleo | Son locales y deterministas. No cuestan modelo |

---

## 4. Orden de ejecución propuesto

1. **MEJ-04**, porque sin medida propia lo demás no se puede evaluar.
2. **MEJ-01**, que es un argumento de línea de órdenes y el mayor efecto por unidad de
   esfuerzo.
3. **MEJ-03**, barata y sin riesgo apreciable.
4. **MEJ-02**, la más invasiva, y sólo si MEJ-01 y MEJ-03 no bastan.
5. **MEJ-05**, que exige fijar antes un criterio de cobertura.
6. **MEJ-06** y **MEJ-07**, cuando la próxima Ejecución dé el dato que les falta.

---

## 5. Registro de versiones

| Versión | Resultado |
|---|---|
| **1.0** | **Vigente.** Primera emisión. Línea base medida sobre las Ejecuciones del 16 y 17 de septiembre de 2026, y siete mejoras derivadas de ella |
