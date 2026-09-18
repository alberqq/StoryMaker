# StoryMaker, de principio a fin

Este documento sirve para entender el sistema entero y poder responder por él. Recorre
una novela desde la chispa inicial hasta el fichero entregado, y en cada momento dice
tres cosas: **quién actúa**, **qué produce** y **dónde queda guardado**. Después
desglosa las piezas una por una.

Cuando el código y la especificación discrepen, gana la especificación. Cuando este
documento y la especificación discrepen, gana la especificación: esto es un mapa, no
la decisión.

---

## 1. La tesis

StoryMaker genera novelas históricas largas sin que una persona tenga que sostener en
la cabeza la coherencia de cien mil palabras. El problema que resuelve no es «escribir
bien»: es **mantener consistente un artefacto más grande que cualquier ventana de
contexto**, y hacerlo de forma que se pueda comprobar desde fuera.

La observación de la que sale todo el diseño es esta:

> Un modelo que ha consumido ochenta mil palabras de contexto y lleva tres iteraciones
> discutiendo una escena no es un guardián fiable de una invariante. Y el problema no
> es la obediencia: es que **una garantía cuyo cumplimiento no se puede comprobar
> desde fuera no es una garantía, es una esperanza**.

De ahí la decisión maestra, ADR‑01: **los agentes proponen, el núcleo escribe.** Todo
lo que es estado —Encargo, Contexto histórico, Canon, Novela, presupuestos, hallazgos—
lo escribe únicamente un programa Python determinista, invocado como herramienta. Los
agentes leen lo que necesitan, producen su propuesta y la pasan por esa puerta.

Si en la defensa hay una sola frase que retener, es esa. Todo lo demás es su
consecuencia.

---

## 2. Las tres capas

```
Piel          .claude/commands/     siete comandos de barra
              gui/                  interfaz web y orquestador
              CLAUDE.md             las reglas que siempre están en contexto

Agentes       .claude/agents/       siete subagentes, contexto aislado
              .claude/skills/       cinco procedimientos cargados a demanda

Núcleo        src/storymaker/       propietario único del estado
              .claude/hooks/        siete puertas deterministas
              proyectos/<prj>/      ficheros: Canon, Contexto, Novela, ledger
```

**La piel** es donde el Autor decide. No ejecuta etapas: las despacha.

**La capa de agentes** es la única parte no determinista. Genera, critica y juzga. No
escribe estado.

**El núcleo** es un ejecutable Python con superficie de línea de órdenes. Es el único
que abre en modo escritura los ficheros de estado. Valida contra esquema, comprueba
invariantes, versiona, contabiliza consumo, anexa al ledger y devuelve un sobre
tipado.

### La frontera se impone, no se pide (ADR‑02)

Tres mecanismos concéntricos, y **ninguno depende de que un agente colabore**:

1. **Permisos.** `.claude/settings.json` deniega a los agentes toda escritura bajo
   `proyectos/**`, con la única excepción de `proyectos/<prj>/tmp/`. Escribir el Canon
   no es «algo que el agente no debe hacer»: es algo que no puede.
2. **Hooks `PreToolUse`.** Antes de que una llamada a herramienta se ejecute, un
   programa determinista la examina y puede denegarla con un motivo.
3. **El núcleo**, que vuelve a comprobar las invariantes antes de persistir.

La redundancia es deliberada: los dos primeros protegen de un agente descaminado, el
tercero protege de un error en los dos primeros. Es la misma regla que el arnés aplica
a los hallazgos: **lo que no se puede comprobar desde fuera, no cuenta**.

---

## 3. El flujo completo de una novela

La Ejecución se conduce en **tres tramos** con **dos paradas** del Autor. Cada tramo
es una sola sesión de Claude Code que hace su trecho seguido, despachando subagentes
según le toca.

> **Por qué tres tramos y no ocho.** Antes había una sesión por etapa. Cada una
> arrancaba de cero, releía el Encargo y volvía a orientarse antes de hacer nada: la
> mayor parte del gasto se iba en reorientación, y cada arranque era un sitio más
> donde algo podía romperse.

### Momento 0 · Crear el Proyecto

| | |
|---|---|
| **Quién** | El Autor, desde la interfaz o con `storymaker proyecto crear` |
| **Genera** | El árbol de carpetas del Proyecto y su ficha de estado |
| **Dónde** | `proyectos/<prj>/proyecto.json` |

El identificador `prj_…` se genera en `ids.py` y no se reutiliza jamás.

### Momento 1 · El Encargo (E1)

| | |
|---|---|
| **Quién** | `sm-entrada`, o el Autor rellenando el formulario / subiendo un JSON |
| **Herramientas** | `Read`, `Glob`, `Grep`, `Bash`, **`AskUserQuestion`** |
| **Genera** | El Encargo cerrado: época, ámbito geográfico, premisa, extensión por capítulo, Guía de estilo con sus siete parámetros |
| **Contrato** | CT‑2 · `encargo` |
| **Dónde** | `proyectos/<prj>/encargo/enc_<prj>_v1.json` |

El Encargo parte de una **Semilla** incompleta —un personaje, una época, una imagen— y
se cierra a preguntas. `sm-entrada` es la única etapa con `AskUserQuestion`, porque es
la única cuyo trabajo *es* preguntar.

Un parámetro de estilo puede quedar **sin preferencia**, y eso no es un hueco: es una
declaración de que el arnés elige. La skill `voz-y-estilo` define qué significa
exactamente.

**Puntos de control PC‑1 y PC‑2.** Todo el contenido del Encargo lo decide el Autor, y
su cierre exige confirmación explícita. Una contradicción del Encargo **no se resuelve
en silencio**: se eleva.

### Momento 2 · El Contexto histórico (E2) — primer tramo

| | |
|---|---|
| **Quién** | `sm-investigacion` |
| **Herramientas** | `Read`, `Glob`, `Grep`, `Bash`, **`WebSearch`**, **`WebFetch`** |
| **Genera** | Afirmaciones con sus Fuentes; el contenido consultado conservado; fichas de figuras históricas reales; lagunas declaradas; **Restricciones de época** |
| **Contrato** | CT‑3 · `contexto_historico` |
| **Dónde** | `contexto/ctx_<prj>_vN.json`, `contexto/afirmaciones.jsonl`, `contexto/figuras_reales/*.json`, `fuentes/<xx>/<sha256>`, `blobs/<xx>/<sha256>` |

Es **la única etapa que sale al exterior**, y por tanto el único punto por el que entra
información no generada por un modelo.

Dos cosas merecen defensa propia:

**Las lagunas se declaran, no se rellenan.** Si el período es oscuro y una sección
queda sin cubrir, se registra como laguna con su impacto evaluado. Rellenarla con
verosimilitud sería exactamente el fallo que el sistema existe para evitar.

**Las Restricciones de época son el producto real de esta etapa.** El Contexto
*describe*; una Restricción *decide*. Hay cinco categorías, y sólo la primera se
barre automáticamente:

| Categoría | Qué prohíbe o exige | Comprobable |
|---|---|---|
| `lexica` | Palabras que no existían aún | **Sí**, por barrido de términos. Debe declarar `terminos_prohibidos` |
| `material` | Objetos, tejidos, alimentos, materiales | Normalmente cualitativa |
| `tecnologica` | Técnicas y procedimientos | Normalmente cualitativa |
| `institucional` | Cargos, leyes, monedas, jerarquías | Normalmente cualitativa |
| `mentalidad` | Creencias y actitudes de la época | Siempre cualitativa |

Lo que no se puede enunciar de forma comprobable se marca `--cualitativa` y se evalúa
con rúbrica, no con puerta binaria. La skill `derivar-restricciones` es el
procedimiento.

**Invariante INV‑8:** toda Restricción es trazable a una afirmación vigente, y ninguna
cuelga de una descartada o refutada.

### 🛑 Parada 1 · El Autor firma el Contexto (PC‑2b)

**Aquí el trabajo se detiene y no continúa hasta que el Autor decide.** No consume
presupuesto mientras espera.

El Autor lee las afirmaciones y las Restricciones en la pestaña *Contexto histórico* y
tiene tres salidas:

| Decisión | Qué pasa | Núcleo |
|---|---|---|
| **Firmar** | El Contexto queda aceptado, con su nombre y la fecha | `contexto firmar --quien "<nombre>"` |
| **Descartar** | Retira afirmaciones o Restricciones concretas. Nada se borra: se marca, y **descartar una afirmación arrastra lo que colgaba de ella** | `contexto descartar` |
| **Rehacer el tramo** | Vuelve a lanzar la investigación con el motivo del rechazo por delante | La interfaz relanza el tramo |

Rehacer **exige un motivo**. Un rechazo que no dice qué cambiar obliga a adivinar, y lo
más probable es que salga lo mismo.

### Momento 3 · El Canon (E3) — segundo tramo

| | |
|---|---|
| **Quién** | `sm-diseno` |
| **Herramientas** | `Read`, `Glob`, `Grep`, `Bash` |
| **Genera** | Arco, hilos de trama, reparto de personajes, capítulos, escenas con su ficha y su presupuesto de palabras, línea temporal, **plan de revelaciones** |
| **Contrato** | CT‑4 · `canon_plan` |
| **Dónde** | `canon/plan/can_<prj>_v1.json`, `canon/hechos.jsonl`, `licencias.jsonl` |

El tramo empieza cerrando el Contexto (`contexto cerrar`) y sigue construyendo el
Canon. El Canon es **la fuente única de verdad narrativa**: a partir de aquí, todo se
valida contra él y no contra lo ya escrito.

Antes de proponerlo, el núcleo corre ocho invariantes de plan (`comprobar_plan`): que
todo hilo tenga resolución, que toda revelación esté plantada antes de resolverse, que
ningún personaje aparezca sin estar en el reparto, que la línea temporal sea
consistente. La skill `plantar-y-resolver` es la que define qué cuenta como
preparación: *un hilo que se resuelve con algo que el lector no vio venir ni pudo ver
venir no está resuelto, está abandonado*.

**E4, la crítica del Canon.** `sm-diseno` escribe al final de su tramo una crítica
breve de su propio plan, para que el Autor la lea. No tiene subagente propio y **no
decide nada**.

> Esto fue antes una etapa de validación con subagente dedicado (`sm-validador-canon`)
> que podía rechazar el Canon. Se retiró en la versión 1.7 por decisión del Autor:
> «que sea muy sencilla, como una crítica, se revisa y punto». Es una pérdida real de
> garantía, declarada como tal en §18.2 de la Funcional.

### 🛑 Parada 2 · El Autor aprueba el Canon (PC‑3)

Segunda detención. El Autor lee el plan y la crítica en la pestaña *Canon* y aprueba,
o rechaza con motivo y se rehace el tramo.

```
storymaker --proyecto <prj> canon aprobar --modo-aprobacion humano --quien "<nombre>"
```

**Un Canon aprobado es inmutable.** Cambiarlo exige versión nueva, y las anteriores no
se destruyen (INV‑6). Aprobarlo mueve el Proyecto a producción.

**Sin Canon aprobado no se redacta una sola escena** (INV‑1). Esto lo comprueban dos
sitios: el hook `guard_canon.py` antes de que la llamada exista, y
`proyecto.exigir_canon_aprobado` antes de persistir.

### Momento 4 · La producción (E5, E6, E7) — tercer tramo

Para cada capítulo, y dentro de él para cada escena en orden:

#### 4a · Redacción (E5)

| | |
|---|---|
| **Quién** | `sm-redactor` |
| **Genera** | La prosa de una escena |
| **Contrato** | CT‑7 · `escena_version` |
| **Dónde** | `novela/escenas/<esc>/esv_<esc>_v1.md` (el texto) y `.json` (sus metadatos) |

**No recibe la novela previa.** Recibe tres sustitutos más baratos y más fiables, que
son el corazón de la gestión de contexto:

1. La **ficha de la escena** del Canon y la Guía de estilo efectiva.
2. Los **hechos de los sujetos presentes** (`canon hechos`), no el Canon entero.
3. Las **sinopsis de los capítulos ya cerrados** — actas de lo ocurrido, sin prosa ni
   citas — más las escenas anteriores del mismo capítulo.

Esto es lo que hace que el coste **no crezca con el cuadrado de la extensión**. La
alternativa obvia —dar al agente todo lo escrito— falla justo donde más importa: en el
último tercio, cuando el contexto acumulado es mayor y el presupuesto menor.

#### 4b · Refinamiento (E6) — bucle interno B2

| | |
|---|---|
| **Quién** | `sm-refinador` |
| **Genera** | Una versión nueva de la escena, y hallazgos sobre lo que no le toca arreglar |
| **Dónde** | `novela/escenas/<esc>/esv_<esc>_v2.md`, y los hallazgos en `hallazgos.jsonl` |

Su alcance es **la escena**: no el capítulo, no la novela. Eleva la calidad lingüística
y **señala** los problemas estructurales sin decidir sobre ellos. Si ve algo que
contradice el Canon, emite un hallazgo; no lo arregla por su cuenta.

Cada pasada produce una **versión numerada** de la escena. Por eso una escena que dio
problemas tiene `v3` y sus vecinas `v2`: la tercera versión existe porque hubo un
hallazgo bloqueante que obligó a reescribirla.

La escena se cierra con `escena cerrar --modo-cierre convergencia`, y ahí entra el
invariante **INV‑4**: la Novela conserva **la mejor versión evaluada**, no la última.

#### 4c · Validación del capítulo (E7) — bucle externo B3

| | |
|---|---|
| **Quién** | `sm-validador` |
| **Genera** | Un veredicto de capítulo y su lote de hallazgos |
| **Contratos** | CT‑10 · `capitulo_para_validar`, CT‑15 · `capitulo_validado`, CT‑11/CT‑16 · `lote_hallazgos` |
| **Dónde** | `novela/veredictos.jsonl`, `hallazgos.jsonl` |

**No relee la novela.** Valida **contra estructuras**: el Canon, los hechos, las
Restricciones de época y el plan de revelaciones. Es lo que le permite ser barato y
consistente en el capítulo 38 igual que en el 4.

Si devuelve bloqueantes, se corrigen las escenas señaladas y se vuelve a validar. Un
capítulo rechazado **no se aprueba sin que su texto haya cambiado** (comprobado por
hash). Cuando la nueva validación los da por buenos, cada hallazgo se cierra con
`hallazgo transicionar --a resuelto`.

Cerrado el capítulo, se escribe su **sinopsis** —acta de lo ocurrido, quién estaba, qué
cambió de estado, qué quedó pendiente— y **se congela**: es la única ventana del
redactor a lo ya escrito.

#### El pasaje protegido

Cuando una reescritura resuelve un hallazgo bloqueante, ese pasaje se **protege**.
Reescribirlo sin justificación registrada lo deniega el hook `guard_proteccion.py`.

Existe para evitar una oscilación concreta y observada: el validador señala un
anacronismo, el redactor lo corrige, el refinador reescribe el párrafo por razones de
estilo y devuelve el anacronismo, y el bucle no termina nunca.

### Momento 5 · La pasada global (E8)

| | |
|---|---|
| **Quién** | `sm-global` |
| **Genera** | Hallazgos de conjunto: deriva de voz, hilos sin cerrar, personajes indistinguibles, repeticiones a larga distancia, ritmo |
| **Dónde** | `hallazgos.jsonl`, y el cierre en `proyecto.json` |

Es **la única etapa con permiso de lectura total**, y se invoca **una sola vez**, con
todos los capítulos validados.

Al cerrar, el núcleo hace además un **barrido de Deuda de calidad**: todo hallazgo no
bloqueante que siga abierto pasa a `aceptado_como_deuda` y el Proyecto queda en
*finalizado con reservas*. Existe porque E8 es la última etapa y sus hallazgos no
tienen ninguna detrás que los corrija: antes se quedaban abiertos para siempre en un
fichero que no miraba nadie, y la novela se entregaba como *finalizada* igual. Los
bloqueantes no entran en el barrido —su ausencia es una de las cinco condiciones de
cierre—, así que con uno abierto no se llega hasta aquí.

Antes de cerrar, el núcleo **recalcula el estado de los hilos** (`novela hilos`)
recorriendo las escenas cerradas, en lugar de leerlo del índice `idx_hilos_estado`. La
razón es MD‑6: un índice puede estar obsoleto, y **una decisión no puede apoyarse en
algo que puede estarlo**.

### Momento 6 · La entrega

| | |
|---|---|
| **Genera** | La novela en Markdown y PDF, el paquete de trazabilidad, la Deuda de calidad y el informe de calibración |
| **Contrato** | CT‑17 · `paquete_entrega` |
| **Dónde** | `proyectos/<prj>/entrega/` |

El PDF usa `pandoc` si está en el entorno; si no, se entrega sólo Markdown y **se
declara** (ERR‑902). Nada se degrada en silencio.

---

## 4. Las partes deterministas

Todo lo de esta sección es Python sin modelo. Es lo que se puede probar, y lo que está
probado: **155 pruebas en verde**.

| Fichero | Qué decide |
|---|---|
| `cli.py` | La única puerta de escritura. Diecinueve grupos de órdenes |
| `almacen.py` | Disposición del almacén, cerrojo del Proyecto y **orden canónico** de escritura |
| `invariantes.py` | Las invariantes no expresables en esquema |
| `esquemas.py` | Validación de contratos: un subconjunto de JSON Schema, sin dependencias |
| `presupuesto.py` | Contabilidad, admisión previa y los dos tramos de reserva |
| `bucles.py` | Los cinco modos de terminación y la elección de la mejor versión |
| `hallazgos.py` | Severidad, causa raíz e identidad de un hallazgo |
| `manifiesto.py` | Qué ve cada etapa, y en qué orden se recorta |
| `ledger.py` | El Run Ledger: dieciocho tipos de evento, ninguno fuera de catálogo |
| `ids.py` | Identificadores, que no se reutilizan |
| `indices.py` | Índices derivados, reconstruibles, **que nunca deciden** |
| `version_esquema.py` | Promoción en lectura al reanudar sobre un esquema anterior |
| `errores.py` | La taxonomía completa, con la acción prescrita de cada código |

### Las ocho invariantes

Cada una se comprueba en al menos dos sitios.

| INV | Enunciado | Hook | Núcleo |
|---|---|---|---|
| INV‑1 | No se redacta sobre un Canon no aprobado | `guard_canon.py` | `proyecto.exigir_canon_aprobado` |
| INV‑2 | Ninguna escena revela antes de tiempo | — | `validacion.comprobar_revelaciones_anticipadas` |
| INV‑3 | Toda afirmación histórica, respaldada o con licencia | — | `validacion.comprobar_licencia_de_figura` |
| INV‑4 | La Novela contiene la mejor versión, no la última | — | `novela.conservar_mejor` · `bucles.mejor_version` |
| INV‑5 | Ningún bloqueante convive con una unidad cerrada | — | `validacion.cerrar_capitulo` |
| INV‑6 | Toda modificación del Canon genera versión | — | `canon.aprobar` · `canon.replanificar` |
| INV‑7 | Ninguna Ejecución supera su presupuesto | `guard_presupuesto.py` | `presupuesto.Contabilidad.admitir` |
| INV‑8 | Toda Restricción es trazable a una afirmación vigente | — | `invariantes.comprobar_derivacion_restriccion` |

### Los cinco modos de terminación de un bucle

Un bucle que sólo termina «cuando esté bien» no termina. Por eso la terminación está
enumerada:

| Modo | Cuándo | Cierra | Emite Deuda |
|---|---|---|---|
| **T1 · convergencia** | No quedan bloqueantes ni mayores por encima del umbral | Sí | No |
| **T2 · estancamiento** | El conjunto no mejora, o reaparece un hallazgo resuelto | Sí | Sí |
| **T3 · regresión** | La evaluación empeora respecto a la anterior | Sí, con la versión anterior | Sí |
| **T4 · agotamiento** | Se agota cualquiera de los presupuestos | Sí | Sí |
| **T5 · escalado** | Bloqueo irresoluble | **No.** Detiene y eleva al Autor | — |

Un bloqueante que no se puede resolver dentro del arnés —falta fuente documental,
contradice una decisión del Autor, exige cambiar el Encargo— **se escala, no se
itera**. Escalar no consume iteraciones.

### El presupuesto y sus dos tramos

Toda Ejecución arranca con un límite de coste y de iteraciones. El control **no es un
aviso a posteriori**: hay una **admisión previa** que deniega la unidad cuya estimación
supera el remanente, antes de gastar. Un sobrecoste que se descubre cuando ya se gastó
no se puede deshacer.

Del presupuesto se aparta un **20 % de reserva**, partido en dos tramos: el 60 % es
libre y el 40 % restante **sólo lo libera el último tercio de la novela**. Existe
porque el final es donde el contexto acumulado es mayor y el dinero menor, y sin
segmentar la reserva se la come la primera mitad.

### Escribir sin transacciones (ADR‑04)

El almacén son ficheros, sin motor de base de datos. No hay transacciones, así que la
consistencia se consigue con dos cosas: un **cerrojo por Proyecto** y un **orden
canónico** de escritura, de modo que un corte en cualquier punto deje el Proyecto en un
estado del que se puede reanudar. Hay una suite de pruebas entera (`test_almacen_y_recuperacion.py`) que simula el corte en cada paso de ese orden.

---

## 5. Los agentes y sus modelos

Siete subagentes, uno por etapa. Cada uno vive en `.claude/agents/<nombre>.md` con sus
instrucciones, su modelo y su lista de herramientas.

| Subagente | Etapa | Modelo | Herramientas | Por qué esas |
|---|---|---|---|---|
| `sm-entrada` | E1 | `haiku` | `Read`, `Glob`, `Grep`, `Bash`, `AskUserQuestion` | Su trabajo es preguntar |
| `sm-investigacion` | E2 | `haiku` | + `WebSearch`, `WebFetch` | La única que sale al exterior |
| `sm-diseno` | E3 (y la crítica de E4) | `haiku` | `Read`, `Glob`, `Grep`, `Bash` | No redacta prosa ni busca fuentes |
| `sm-redactor` | E5 | `haiku` | `Read`, `Glob`, `Grep`, `Bash` | No lee la novela: recibe su manifiesto |
| `sm-refinador` | E6 | `haiku` | `Read`, `Glob`, `Grep`, `Bash` | Su alcance es la escena |
| `sm-validador` | E7 | `haiku` | `Read`, `Glob`, `Grep`, `Bash` | Valida contra estructuras |
| `sm-global` | E8 | `haiku` | `Read`, `Glob`, `Grep`, `Bash` | Único con lectura total, una sola vez |

**Sobre los modelos, hay que ser honesto en la defensa.** Los siete declaran `haiku`.
No es una afirmación de que haiku sea el modelo adecuado para redactar literatura: es
una elección de *este montaje de pruebas*, donde lo que se quiere medir es que el flujo
entero corra y converja, no la calidad de la prosa. El modelo es un campo del fichero
de cada agente y se cambia ahí, sin tocar el núcleo. La sesión que conduce cada tramo
usa el modelo por defecto de Claude Code.

**La lista recortada de herramientas no es una optimización: es la primera línea de la
frontera de ADR‑02.** `Bash` aparece en las siete porque es el canal por el que se
llama al núcleo —un subagente propone ejecutando `storymaker <grupo> <acción>`— y no
tiene ninguna otra forma de escribir estado. Que pueda ejecutar órdenes no debilita la
frontera: los hooks deniegan antes, y el núcleo comprueba después.

### Las tres memorias

| Memoria | Dónde vive | Cuánto dura |
|---|---|---|
| **Larga** | `proyectos/<prj>/` | Toda la vida del Proyecto |
| **De trabajo** | El manifiesto que `manifiesto.construir` inyecta | Una unidad |
| **Efímera** | `proyectos/<prj>/tmp/<udt>/` | Se borra al cerrar la unidad |

El manifiesto de cada etapa está declarado **como dato**, no como prosa en un prompt:
`manifiesto.PRELACION` dice qué bloques ve cada etapa y en qué orden se recortan si no
caben; `manifiesto.NO_RECORTABLES` dice lo que ningún recorte puede tocar. Dar a un
agente un bloque que su etapa no declara se rechaza con ERR‑105.

Que esté declarado como dato es lo que permite **reconstruir con qué información se
tomó cada decisión**.

---

## 6. Las skills

Procedimientos que varios agentes comparten, o demasiado extensos para vivir en las
instrucciones de uno. Se cargan **a demanda**, que es lo que evita pagar su coste en
cada llamada.

| Skill | Qué encapsula | Quién la usa |
|---|---|---|
| `derivar-restricciones` | Cómo convertir una afirmación en regla comprobable, sus cinco categorías y cuándo declararla cualitativa | `sm-investigacion` |
| `evaluar-con-rubrica` | La rúbrica por etapa, su escala y la regla de evaluar **sin historial de iteraciones previas** | `sm-refinador`, `sm-validador`, `sm-global` |
| `emitir-hallazgo` | La forma canónica de un hallazgo: severidad, causa raíz, localización, acción exigida y evidencia | Todos los agentes críticos |
| `plantar-y-resolver` | Cómo se declara que una resolución está preparada | `sm-diseno` |
| `voz-y-estilo` | Cómo se lee la Guía de estilo efectiva y qué significa un parámetro sin preferencia | `sm-redactor`, `sm-refinador` |

Dos detalles defendibles:

**La rúbrica se aplica sin historial.** Un evaluador que sabe que ésta es la cuarta
iteración tiende a premiar la mejora en lugar de juzgar el resultado.

**La identidad de un hallazgo excluye su enunciado.** Dos hallazgos que describen el
mismo defecto con distintas palabras son el mismo hallazgo. Si el enunciado formara
parte de la identidad, el sistema no detectaría jamás que un defecto resuelto ha
reaparecido, que es precisamente lo que dispara la terminación por estancamiento (T2).

---

## 7. Los hooks

Siete programas deterministas que se ejecutan **fuera del modelo** y pueden denegar.

| Hook | Momento | Qué hace |
|---|---|---|
| `guard_escritura.py` | `PreToolUse` | Deniega cualquier escritura de estado que no venga del núcleo |
| `guard_canon.py` | `PreToolUse` | Deniega redactar si el Canon no está aprobado (INV‑1) |
| `guard_presupuesto.py` | `PreToolUse` | Deniega la unidad cuya estimación supera el remanente, **antes de gastar** |
| `guard_proteccion.py` | `PreToolUse` | Deniega reescribir un pasaje protegido sin justificación registrada |
| `ledger_llamada.py` | `PostToolUse` | Anexa al ledger cada llamada con tokens, coste, latencia y hashes |
| `cierre_unidad.py` | `SubagentStop` | Cierra la unidad, registra el modo de terminación y libera el cerrojo |
| `arranque.py` | `SessionStart` | Carga el estado, comprueba el esquema y avisa de puntos de control pendientes |

**Por qué `cierre_unidad` es un hook y no una llamada del agente:** un subagente puede
terminar sin llamar a nada —porque se quedó sin contexto, porque falló, porque lo
interrumpieron—. Si el cierre dependiera de que el agente colabore, el cerrojo se
quedaría tomado y la contabilidad incompleta.

Una escritura denegada **queda en el ledger** como `escritura_denegada`. No es un fallo
silencioso: es un dato.

---

## 8. Los contratos

Quince esquemas en `contracts/`, sobre los que se declaran **veinte identificadores CT** —varios comparten forma, como los cuatro lotes de hallazgos—, más el sobre común. Definen la forma de lo que
cruza cada frontera. El núcleo valida contra ellos antes de persistir, y hay una suite
de pruebas que comprueba **los casos que deben rechazarse**, no sólo los que pasan.

| ID | Contrato | Qué cruza |
|---|---|---|
| CT‑1 | `ambito_investigacion` | Encargo → investigación |
| CT‑2 | `encargo` | El Encargo cerrado |
| CT‑3 | `contexto_historico` | El Contexto con sus fuentes |
| CT‑4 | `canon_plan` | El plan propuesto |
| CT‑5, CT‑8, CT‑11, CT‑16 | `lote_hallazgos` | Hallazgos de cada etapa crítica |
| CT‑6 | `canon_aprobado` | El Canon con su firma |
| CT‑7 | `escena_version` | Cada versión de escena |
| CT‑9 | `propuesta_replanificacion` | Replanificación durante la producción |
| CT‑10 | `capitulo_para_validar` | Lo que ve el validador |
| CT‑12, CT‑13 | `solicitud_investigacion` / `respuesta_investigacion` | Investigación bajo demanda |
| CT‑14 | `lote_hechos` | Hechos del Canon |
| CT‑15 | `capitulo_validado` | El veredicto |
| CT‑17 | `paquete_entrega` | La entrega |
| CT‑18 | `evento_ledger` | Cada evento de contabilidad |

**El sobre.** Toda respuesta del núcleo tiene la misma forma: `ok`, el comando, y datos
o error. El código de salida es 0 o 1 según `ok`. Eso permite que la interfaz devuelva
el sobre **tal cual**, error incluido, sin interpretar nada.

`storymaker errores listar` da el catálogo completo de códigos con su **acción
prescrita**. Los errores se agrupan en ocho familias: entrada, proveedor, esquema,
presupuesto, estado, contradicción, evaluación y entrega.

---

## 9. Cómo se almacena cada cosa

Todo son ficheros. No hay motor de base de datos, y es una restricción de diseño
declarada, no una carencia.

```
proyectos/<prj>/
├── proyecto.json              Estado: etapa, modo, versiones vigentes
├── encargo/
│   └── enc_<prj>_v1.json      El Encargo, versionado
├── contexto/
│   ├── ctx_<prj>_vN.json      El Contexto, una versión por cambio
│   ├── afirmaciones.jsonl     Una afirmación por línea, con su estado
│   └── figuras_reales/        Una ficha por figura histórica real
├── fuentes/<xx>/<sha256>      Metadatos de cada Fuente
├── blobs/<xx>/<sha256>        El contenido consultado, tal como se leyó
├── canon/
│   ├── plan/can_<prj>_vN.json El plan, versionado e inmutable una vez aprobado
│   └── hechos.jsonl           Los hechos del Canon
├── licencias.jsonl            Licencias literarias y de alcance
├── hallazgos.jsonl            Todos los hallazgos, con su historia de estados
├── novela/
│   ├── escenas/<esc>/
│   │   ├── esv_<esc>_vN.md    El texto de cada versión
│   │   └── esv_<esc>_vN.json  Sus metadatos, hash y evaluación
│   ├── ramas.json             Qué versión está vigente (ADR‑05)
│   ├── sinopsis/<cap>.md      Acta congelada de un capítulo cerrado
│   └── veredictos.jsonl       Cada validación de capítulo
├── ejecuciones/<eje>/
│   ├── ejecucion.json         Configuración congelada al arrancar
│   ├── ledger.jsonl           El Run Ledger
│   ├── consumo.jsonl          Tokens y coste por llamada
│   └── unidades.jsonl         Unidades de trabajo con su terminación
├── entrega/                   Markdown, PDF y trazabilidad
├── indices/                   Derivados, reconstruibles, que nunca deciden
└── tmp/<udt>/                 Borradores. Lo único escribible por un agente
```

Tres decisiones defendibles:

**Contenido direccionado por hash.** Fuentes y blobs se guardan bajo el SHA‑256 de su
contenido, en carpetas de dos caracteres. Eso da deduplicación gratis y, sobre todo,
hace que **la trazabilidad sobreviva a que el enlace muera**: el texto se guardó tal
como estaba el día de la consulta.

**Qué es autoritativo y qué no.**

| Artefacto | Autoritativo | Por qué |
|---|---|---|
| Encargo, Contexto, Canon, Novela, ledger | **Sí** | Es el estado |
| Borradores en `tmp/<udt>/` | No | Se borran al cerrar la unidad |
| `indices/` | No | Se reconstruyen. **Sirven para consultar, nunca para decidir** |
| Sinopsis de un capítulo cerrado | Sí, y **congelada** | Es la memoria del redactor; si cambiara, cambiaría el pasado |

**Nada se borra nunca.** Descartar una afirmación la marca; no la elimina. Las
versiones anteriores del Canon se conservan. Es lo que permite responder «¿por qué
dice esto la novela?» meses después.

---

## 10. El humano en el bucle

El Autor es el único actor humano, y también el Operador. Se le pregunta a través de
**puntos de control**, y nunca se decide por él.

| Punto | Momento | Qué decide |
|---|---|---|
| **PC‑1** | Durante la captura | Todo el contenido del Encargo |
| **PC‑2** | Cierre del Encargo | Confirmación del Encargo completo |
| **PC‑2b** | Contexto histórico compuesto | Firmar, descartar afirmaciones, o rehacer la investigación |
| **PC‑3** | Tras el diseño, antes de redactar | Aprobar, rechazar con hallazgos, o replanificar el Canon |
| **PC‑4** | Replanificación durante la producción | Aceptar o rechazar la propuesta |
| **PC‑5** | Bloqueo irresoluble | Evitar el detalle, aportar fuente, autorizar licencia o cambiar el Encargo |
| **PC‑6** | Agotamiento con bloqueantes abiertos | Aceptar la deuda, ampliar presupuesto o abandonar |

**Una Ejecución detenida en un punto de control no consume presupuesto mientras
espera.** Es lo que hace viable que la espera sea indefinida, y no es una promesa
suelta: el presupuesto de segundos se alimenta **sólo** de lo que `unidad llamada`
registra por cada llamada a modelo, nunca de reloj de pared. Una parada de tres horas
suma exactamente cero.

Lo que sí medía la espera era la **observabilidad**, que es otra cosa: el span de la
parada tiene su duración real, y sumada al total hacía parecer lentas las Ejecuciones
en las que el Autor tardó en mirar. Por eso los tiempos se dan ahora separados
—`minutos_trabajando` y `minutos_esperandote`— y las paradas quedan fuera del ranking
de pasos más lentos, donde una espera larga ganaría siempre sin decir nada útil.

De los siete, **dos son paradas del flujo automático**: PC‑2b y PC‑3. Son las dos
paradas de los tres tramos, y son las que el Autor ve en la interfaz.

### Un solo modo de operación

Hubo cuatro —asistido, autónomo supervisado, autónomo y Revisión del Autor—. **Queda
sólo `revision_del_autor`.** Los otros tres presuponían etapas de validación que ya no
existen, de modo que eran configuraciones sin implementación detrás.

Esto hay que saber defenderlo, porque es el cambio de fondo del proyecto. La evolución
fue:

1. **Hasta la 1.5**, el Contexto lo cruzaban dos etapas automáticas —verificación de
   fidelidad contra la fuente conservada, y una pasada adversarial de refutación— y el
   Canon lo juzgaba un validador con capacidad de rechazo.
2. **En la 1.5**, el modo Revisión del Autor permitía que el Autor **sustituyera** a
   esas etapas: firmaba él, y su firma quedaba registrada como suya.
3. **Desde la 1.7**, esas etapas **no existen**. El Autor no sustituye a nadie: es el
   único control sobre el Contexto y sobre el Canon.

La razón fue de coste y de fiabilidad: dos pasadas de modelo por afirmación costaban
más de lo que corregían, y una de ellas rompió una Ejecución entera sin producir nada.
**La consecuencia es una pérdida real de garantía**, y está declarada como tal en
§18.2 de la Funcional. Lo que sigue comprobado por código sobre el Contexto es la
**trazabilidad** —de dónde sale cada Restricción, y que no cuelgue de algo caído—, no
la **veracidad** de lo afirmado.

Si en la defensa preguntan «¿cómo sabéis que el Contexto histórico es cierto?», la
respuesta honesta es: **no lo sabemos por construcción; lo sabemos porque una persona
lo ha leído y lo ha firmado, y su firma queda registrada con su nombre**.

---

## 11. Los scripts y la interfaz

### El núcleo

```
storymaker --proyecto <prj> <grupo> <accion> [opciones]
```

Diecinueve grupos: `proyecto`, `encargo`, `contexto`, `canon`, `escena`, `sinopsis`,
`hallazgo`, `capitulo`, `novela`, `entrega`, `ejecucion`, `etapa`, `unidad`, `control`,
`traza`, `indices`, `informe`, `contratos` y `errores`.

### Los siete comandos de barra

| Comando | Qué hace |
|---|---|
| `/encargo` | Captura del Encargo, o ingesta de un JSON |
| `/ejecutar` | Arranca o reanuda una Ejecución |
| `/estado` | Etapa, unidad, hallazgos, consumo y proyección |
| `/control` | Puntos de control pendientes y su decisión |
| `/traza` | El origen de un pasaje, o el respaldo de una afirmación |
| `/entrega` | Markdown, PDF y paquete de trazabilidad |
| `/calibracion` | Consumo real frente a presupuestado |

### La interfaz gráfica

```bash
python gui/servidor.py     # http://127.0.0.1:8765
```

| Fichero | Qué hace |
|---|---|
| `gui/servidor.py` | Servidor HTTP de biblioteca estándar. Lee ficheros para pintar el panel e invoca el núcleo para todo lo demás |
| `gui/proceso.py` | Orquesta la Ejecución en tres tramos. Cada tramo es una sesión de `claude`, cuya salida se traduce a lenguaje legible según se produce |
| `gui/langfuse.py` | Envía la traza por HTTP. Sin credenciales, se declara que no hay traza y se sigue |
| `gui/comprobar_pagina.py` | Comprobación estática del JavaScript: las formas de romperlo que ya conocemos |
| `gui/index.html` | Página única. React y Babel por CDN, sin compilación |

Tres decisiones la gobiernan, y las tres son consecuencia de ADR‑01:

1. **El servidor no escribe un solo byte bajo `proyectos/`.** Cuando quiere cambiar
   algo invoca al núcleo y devuelve su sobre tal cual.
2. **Lista blanca de órdenes.** Su superficie es deliberadamente más estrecha que la
   del CLI: deja fuera `escena escribir` y `unidad admitir`, que producen prosa o
   consumen presupuesto y son trabajo de una etapa, no de un botón.
3. **Sólo escucha en `127.0.0.1`.** Esto expone el núcleo por HTTP, y abrirlo a la red
   sería dar a cualquiera la capacidad de escribir en el Proyecto.

Las puertas del orquestador están en el orquestador, no en el botón. Arrancar sobre una
Novela ya cerrada se rechaza con **GUI‑026** antes de lanzar nada: sin esa comprobación
la sesión arrancaba, se pagaba, y sólo entonces el núcleo iba rechazando paso a paso.
Ocultar el botón no habría bastado, porque la interfaz es una piel y no la única.

**Ninguna etapa tiene reloj.** Lo tuvo: media hora, y el tramo de la novela murió justo
en el tope dos veces, tirando lo escrito. Un límite que no distingue una etapa colgada
de una etapa larga corta más trabajo bueno del que salva. En su lugar, la pestaña
*Proceso* enseña **quién está despachado y desde cuándo**, y el botón de parar mata la
etapa en curso. Lo que el núcleo haya persistido sobrevive, así que una Ejecución
cortada se relanza y **continúa por donde iba**.

### Las herramientas de una sesión headless

Las etapas se lanzan como sesiones de Claude Code sin interfaz, que corren en modo de
permisos `default`: ahí todo lo que no esté en el `allow` de `settings.json` **se
deniega sin poder preguntar**, y la sesión muere sin producir nada. Por eso cada tramo
se lanza con `--allowed-tools` concediendo explícitamente `Task`, `Bash`, `Read`,
`Glob`, `Grep`, `Write`, `Edit`, `WebSearch`, `WebFetch`, `Skill` y `ToolSearch`.

Aflojar ahí **no afloja las garantías**: los permisos son el más romo de los tres
mecanismos de ADR‑02, y los hooks y el núcleo siguen en pie.

---

## 12. La observabilidad

Tres sitios, y no son equivalentes.

**El Run Ledger** (`ejecuciones/<eje>/ledger.jsonl`) registra lo que el núcleo
persiste: dieciocho tipos de evento, ninguno fuera de catálogo. Ahí están las
admisiones y denegaciones de presupuesto, los hallazgos, las evaluaciones, los puntos
de control y los errores. **Ningún error se traga.**

**Langfuse** registra lo que el ledger no puede ver. Se exporta por
**OpenTelemetry**, en OTLP sobre JSON y con biblioteca estándar: la API de ingestión
anterior se apaga en noviembre de 2026 y su propia respuesta declara que «el único
camino a datos en vivo es la ingesta por OpenTelemetry». La diferencia se nota: una
sonda enviada por la vía antigua no llegaba a aparecer nunca en la API de lectura, y
por OTLP aparece al instante. El gasto real ocurre en sesiones
de modelo que el núcleo no observa, y la primera Ejecución completa dejó el informe de
calibración con consumo cero. Se emite una traza por Ejecución, un tramo por paso y una
**generación por modelo** —no una agregada—, porque una etapa mezcla el modelo que
redacta con el que resuelve las llamadas pequeñas, y agregarlos esconde justo lo que se
quiere ver al calibrar.

Se consulta desde la conversación con el servidor MCP `sm-langfuse`, que es **de sólo
lectura**: quien escribe la traza es `gui/langfuse.py`. Separar las dos direcciones
evita que una consulta mal hecha escriba en la observabilidad, que es justo donde uno
quiere poder fiarse de lo que lee.

**El flujo de agentes** es la tercera, y contesta a «qué agente está trabajando y en qué
orden van». Hay dos vistas, y la diferencia importa:

| Vista | De dónde sale | Qué enseña | Su límite |
|---|---|---|---|
| Panel en vivo de cada tramo | La salida `stream-json` de la sesión, en memoria | Qué subagente está despachado **ahora mismo** y desde cuándo | Se pierde al reiniciar el servidor |
| *El flujo de agentes* (`/api/flujo/<prj>`) | El **Run Ledger**, en disco | Cada unidad de trabajo con su etapa, su duración, su modo de cierre y sus iteraciones | No es tiempo real: se ve cuando la unidad se cierra |
| Langfuse | La traza exportada por OTLP | El árbol entero: Ejecución → tramo → despacho de subagente (`agent`) → consumo por modelo (`generation`), con coste | Depende de que haya credenciales; el coste se lee por la API de métricas, no por la de observaciones |

El segundo se construye emparejando `unidad_iniciada` y `unidad_cerrada` por el
identificador de unidad. **No usa `unidades.jsonl` a propósito**: ahí el estado se queda
en `en_curso` aunque el cierre haya ocurrido, porque nadie reescribe ese fichero. El
ledger es de sólo añadir y por eso no tiene ese problema — que es, en pequeño, la misma
razón por la que el almacén entero se diseñó así.

Leído entero, el flujo cuenta la historia de un defecto sin abrir un solo fichero más:

```
 8  sm-validador   cap_encargo   regresion      ←┐
 9  sm-validador   cap_encargo   regresion       │ el bucle externo
10  sm-redactor    esc_trabajo   convergencia    │ sobre un bloqueante
11  sm-validador   cap_encargo   convergencia   ←┘
```

**El coste no se lee donde uno lo busca**, y esto costó varias tiradas de confusión.
El listado `/api/public/v2/observations` trae `inputPrice`, `outputPrice` y
`totalPrice`, y los tres vuelven **siempre nulos**: es una vista de lista y no calcula
precios. Dimos por hecho que las Ejecuciones salían a cero euros y buscamos el fallo
en lo que enviábamos, cuando el dato estaba en Langfuse desde el primer día — en
`/api/public/v2/metrics`, que es donde el servidor MCP lo lee ahora, cruzando por
traza y nombre de observación. La lección es genérica y vale para la defensa: **un
cero que viene de una API no siempre significa cero; a veces significa que la
pregunta iba a la puerta equivocada.**

**La observabilidad no bloquea. Sin credenciales, la Ejecución corre igual y la falta
de traza se declara. Bloquear el arranque por falta de telemetría convertía un problema
menor en uno mayor.

---

## 13. Las preguntas difíciles

Lo que conviene tener preparado, porque son las grietas reales.

**«¿Qué garantiza esto de verdad?»**
Con comprobación en código, no con instrucciones en un prompt: que no se redacta sobre
un Canon no aprobado; que ninguna Restricción cuelga de una afirmación caída; que un
capítulo rechazado no se aprueba sin que su texto haya cambiado; que la Novela conserva
la mejor versión evaluada y no la última; que ninguna Ejecución supera su presupuesto;
que toda modificación del Canon genera versión; que ninguna credencial aparece en un
artefacto persistido.

**«¿Garantiza que la prosa sea buena?»**
No, y está declarado. Las puntuaciones de rúbrica se calculan y se persisten, pero sólo
sirven para comparar una versión consigo misma: **ningún mínimo las convierte en
puerta**. La maquinaria está; falta el umbral, y ponerlo sin calibración empírica sería
inventarse un número. Los objetivos del arnés ponen la coherencia y la verosimilitud
por delante de la calidad de la prosa, y subordinan ésta explícitamente.

**«¿Garantiza que el Contexto histórico sea cierto?»**
No. Lo comprobado es la trazabilidad, no la veracidad. Se retiraron la verificación de
fidelidad y la pasada de refutación, y el control es que el Autor lo lea y lo firme.
Declarado en §18.2 de la Funcional.

**«¿Por qué un núcleo determinista si ya hay un modelo?»**
Porque una garantía que depende de que un modelo con ochenta mil palabras de contexto
recuerde una regla no es comprobable desde fuera. El núcleo permite responder «esto no
pudo pasar» en lugar de «esto no debería haber pasado».

**«¿Estaban los tres mecanismos de ADR‑02 realmente activos?»**
Durante un tiempo, **no**. Los hooks resuelven sobre qué Proyecto actúan con la
variable `STORYMAKER_PROYECTO` o, si no está, con el único Proyecto que haya; con
varios y sin variable devuelven `None` y **permiten en lugar de adivinar**. Esa
decisión es correcta —adivinar el Proyecto equivocado sería peor que no comprobar—
pero tenía una consecuencia que nadie había mirado: la interfaz no declaraba la
variable al lanzar sus sesiones, así que **en cuanto hubo una segunda novela en disco
los cinco hooks que dependen del Proyecto se apagaron solos y sin ruido**:
`guard_canon` (INV‑1), `guard_presupuesto` (INV‑7), `guard_proteccion`,
`ledger_llamada` y `cierre_unidad`.

El estado nunca estuvo en peligro: los permisos seguían denegando la escritura y el
núcleo seguía comprobando sus invariantes antes de persistir, que es el tercer
mecanismo y el único que de verdad escribe. Pero la **redundancia** que ADR‑02 declara
no existía, y el síntoma por el que se descubrió fue indirecto: las unidades de
trabajo no se cerraban nunca, porque quien las cierra es uno de esos hooks.

Es un buen ejemplo de la tesis del propio proyecto: una garantía que no se comprueba
desde fuera no es una garantía. Aquí el que falló fue el mecanismo de comprobación, y
tardamos en verlo porque **fallaba permitiendo**, que es la forma silenciosa de fallar.

**«¿Y si el agente decide saltarse el núcleo?»**
No puede. Los permisos deniegan la escritura, los hooks deniegan la llamada antes de
que exista, y el núcleo vuelve a comprobar. Y el intento queda registrado en el ledger
como `escritura_denegada`.

**«¿Está probado?»**
155 pruebas en verde, cubriendo cuatro de los cinco niveles previstos: unitario
determinista, contrato, recuperación ante cortes e integración sobre una novela mínima.
Cada invariante tiene su caso que pasa **y su caso que falla**: una invariante probada
sólo con datos válidos no ha demostrado que rechace nada.
El quinto nivel —regresión de arnés sobre un conjunto de encargos de referencia— **no
está implementado**, y sin él cada ajuste de un prompt es una apuesta. Es la carencia
más seria del proyecto y conviene decirla antes de que la pregunten.

**«¿Quién cierra los hallazgos, el sistema o la persona?»**
El sistema, salvo en dos casos previstos. RF‑065 enruta cada hallazgo a la etapa
responsable y el bucle lo corrige y lo cierra. Al Autor sólo le llegan **PC‑5**, un
bloqueo irresoluble que hay que escalar, y **PC‑6**, agotamiento del presupuesto con
bloqueantes abiertos. Lo demás se cierra solo, y lo que al final del todo no tiene
quien lo corrija se declara como Deuda de calidad en lugar de quedarse abierto.

**«¿Qué residuo queda de lo retirado?»**
Algunas entradas inertes en el código: `manifiesto.PRELACION` conserva las de
`sm-refutador` y `sm-validador-canon`, y `proyecto.ETAPAS` conserva la etapa
`Refutacion`, que ya nadie asigna. No afectan al comportamiento —ningún camino las
alcanza— y se dejaron ahí antes que tocar código probado por motivos cosméticos.

---

## 14. Resumen de una carrerilla

1. El Autor da una **Semilla**. `sm-entrada` la convierte en **Encargo** cerrado a
   preguntas. → `encargo/`
2. `sm-investigacion` sale a internet y compone el **Contexto histórico** con fuentes
   conservadas, y deriva las **Restricciones de época**. → `contexto/`, `fuentes/`,
   `blobs/`
3. 🛑 **El Autor firma el Contexto**, o descarta lo que no le vale, o manda rehacerlo.
4. `sm-diseno` cierra el Contexto y construye el **Canon**: hilos, personajes,
   capítulos, escenas, plan de revelaciones. Y escribe su propia crítica. → `canon/`
5. 🛑 **El Autor aprueba el Canon.** Sin eso no se escribe una línea.
6. Por cada escena: `sm-redactor` escribe, `sm-refinador` pule y señala, la escena se
   cierra con su mejor versión. → `novela/escenas/`
7. Por cada capítulo: `sm-validador` emite veredicto contra el Canon y las
   Restricciones. Los bloqueantes vuelven al redactor. Cerrado, se congela su
   **sinopsis**. → `novela/veredictos.jsonl`, `novela/sinopsis/`
8. `sm-global` hace una pasada única sobre la novela entera. Se recalculan los hilos y
   se cierra. → `hallazgos.jsonl`
9. Se genera la **entrega**: Markdown, PDF, trazabilidad, Deuda de calidad y
   calibración. → `entrega/`

En todo momento, lo único que escribe es el núcleo.
