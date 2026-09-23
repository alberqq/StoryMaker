# Arquitectura — StoryMaker

Arnés multiagente para la generación de **novelas históricas personalizadas**.

Este documento no define *qué* se gestiona —eso está en [`definitions.md`](definitions.md) y [`domain-knowledge.md`](domain-knowledge.md)— sino *quién* lo gestiona, *cómo recibe su contexto*, *cómo se detiene* y *cómo se demuestra que funciona*.

---

## 0. El producto en una frase

El comprador quiere regalar una novela. StoryMaker convierte a la persona homenajeada en **personaje de un escenario histórico real y documentado**: el padre que se jubila aparece como armador en el Cádiz de 1805, la pareja como copista en un *scriptorium* del siglo XII. La personalización es el *qué*; el rigor histórico es el *cómo*, y es lo que distingue el producto de pedirle un cuento a un modelo generalista.

Esa decisión de dominio gobierna todo lo demás: justifica una fase de investigación con acceso a internet por novela, llena de contenido real la validación formal —las fechas históricas son duras y comprobables— y proporciona una familia entera de validadores deterministas que una novela contemporánea no tendría.

---

## 1. Decisiones fijadas

| Decisión | Elegida | Consecuencia principal |
|---|---|---|
| Dominio | Novela histórica personalizada | La investigación y la validación formal tienen materia real que verificar. |
| Motor de orquestación | LangGraph con estado explícito | Un nodo por acción de la especificación TLA+, con el mismo nombre. La correspondencia código↔spec es literal, no narrada. |
| Agentes | Claude Code vía **Claude Agent SDK** (Python), todos en Haiku 4.5 | Modelo, herramientas y turnos se fijan por invocación. Internet entra por `WebSearch`/`WebFetch`, sin proveedor adicional. |
| Roles | Nueve: entrevistador, extractor de intake, investigador, verificador, arquitecto, escritor, editor, extractor de capítulo, juez | El **editor repara dentro del bucle**; el **juez mide fuera** y no puede tocar el texto; el **verificador comprueba el corpus** contra las citas guardadas y no puede añadirle nada; los **dos extractores tipan y miden lo que no puede declarar quien lo produjo**. |
| Validadores | Nodos del grafo, nunca herramientas de un agente | Ningún modelo puede saltarse una validación. Las aristas condicionales leen booleanos de Python. |
| Paso de contexto | Empuje determinista en siete bloques | El escritor no tiene herramientas de recuperación. Contexto acotado, reproducible y auditable. |
| Estado | Un único fichero SQLite por novela | Checkpoint del grafo y datos de dominio en la misma transacción. Imposible que se desincronicen. |
| Versiones | Capítulos inmutables + manifiesto | Conservar la versión anterior es una propiedad de la estructura, no una disciplina. |
| Ejecuciones de fase | Grafo de `fase_run` inmutables | Rehacer, reanudar, ramificar y regenerar son **la misma operación** con distinto punto de entrada. |
| Intervención humana | Cinco gates bloqueantes; **Telegram solo avisa y el Autor decide en su PC**, con la CLI | La máquina duerme en disco mientras espera. No hay superficie pública que reanude una ejecución. Desactivables en modo batch. |
| Validación formal | Lean 4 (la historia) + TLA+ (el arnés) | Lean verifica la cronología concreta; TLC verifica el comportamiento del sistema. |
| Observabilidad | Langfuse con spans manuales autorizados + OTLP nativo opcional | La semántica que importa (sesión = novela, span = capítulo/rol/intento) la pone el orquestador. |
| Presupuesto de contexto | 100.000 tokens concurrentes, garantizados por construcción | No se puede medir en vivo, así que se acota *a priori*. Ver §12. |
| Pila | FastAPI organizado *package by feature* con `commons`; React + Vite organizado en **Feature-Sliced Design v2.1** | En el backend, una fase es una carpeta. En el frontend manda la metodología estándar con su juego mínimo de capas. Ver §16.3. |
| Embeddings | FastEmbed local (ONNX), `paraphrase-multilingual-MiniLM-L12-v2`, 384d, indexados con **`sqlite-vec`** | Con SQLite, son la gestión de contexto: deciden qué porción del material entra en cada paquete. Locales, sin red y deterministas. Ver §16.2. |
| Correspondencia documento↔código | Comprobada por tests de trazabilidad, no por lectura | Lo que la spec declara y lo que el plan nombra tiene quien lo compruebe en CI. Un apartado especificado que nadie implementó, o un validador que dejó de bloquear, se ven en G1. Ver §11e. |
| Requisitos de la spec | **Enunciados numerados derivados del propio documento**: `REQ-BE-nn` en el backend, `REQ-FE-nn` en el frontend | Una spec se lee como una lista de compromisos comprobables y no solo como prosa. El enunciado sale del contrato que el propio documento fija, nunca de un checklist externo, de modo que la spec sigue siendo su propia fuente. Ver §11e. |

### La decisión de la que cuelga todo

**Los validadores son nodos del grafo, no herramientas que un agente elige llamar.**

Si el editor decidiera cuándo validar, un modelo que se olvida de invocar una herramienta produciría un capítulo aprobado sin comprobar, indistinguible de uno comprobado y correcto. El arnés ejecuta los validadores siempre, y lo que el editor recibe es el **informe de incidencias ya producido**. Su único trabajo es emitir el parche. Con eso, las transiciones del grafo dependen de valores calculados en Python y no de la salida de un modelo — que es exactamente lo que TLC puede verificar.

---

## 2. Principios

1. **El agente no busca su contexto, lo recibe.** Un módulo determinista arma el paquete de cada capítulo, y para llenarlo puede consultar SQLite y buscar por similitud — pero lo hace él, con una consulta derivada de la escaleta, no el agente decidiendo sobre la marcha. Si la recuperación la hiciera el escritor, cada capítulo recibiría un contexto distinto y la estabilidad métrica dejaría de ser sostenible.
2. **Quien escribe no aprueba.** El escritor no valida. El editor no puntúa. El juez no edita.
3. **Determinista antes que modelo.** Fechas, disponibilidad de objetos, léxico fechado, longitudes, nombres exactos, palabras prohibidas: todo eso lo comprueba código. El modelo solo juzga lo que no se puede calcular.
4. **El canon manda sobre el texto.** Un cambio se aplica al hecho en la base de datos y el texto se regenera como consecuencia. Nunca al revés: un `buscar-y-reemplazar` sobre la prosa deja mintiendo a la biblia.
5. **Nada se sobrescribe.** Capítulos, versiones y ejecuciones de fase son inmutables. Lo que parece una modificación es siempre una fila nueva que apunta a la anterior.
6. **El orquestador no acumula.** Todo su conocimiento está en SQLite. Se puede matar el proceso en cualquier punto y reanudar sin pérdida.

---

## 3. Topología

```mermaid
graph TD
    H["Humano<br/>comprador / autor"] -->|brief, gates| ORQ
    ORQ -->|solo notificación| TG["Bot de Telegram"]
    CLI["CLI en el PC del Autor"] -->|decisión de gate| ORQ
    ORQ["Orquestador LangGraph<br/>estado explícito"] --> DB[("SQLite<br/>una novela = un fichero")]
    ORQ --> PK["Ensamblador de paquetes<br/>código, no agente"]
    ORQ --> VAL["Validadores<br/>Core Domain en Python puro"]
    VAL --> LEAN["Lean 4<br/>cronología"]

    ORQ -. "Agent SDK" .-> A1["entrevistador"]
    ORQ -. "Agent SDK" .-> A2["investigador"]
    ORQ -. "Agent SDK" .-> A2B["verificador"]
    ORQ -. "Agent SDK" .-> A3["arquitecto"]
    ORQ -. "Agent SDK" .-> A4["escritor"]
    ORQ -. "Agent SDK" .-> A5["editor"]
    ORQ -. "Agent SDK" .-> A6["juez"]

    PK --> A4
    PK --> A5
    A2 -->|WebSearch / WebFetch| NET(("Internet"))

    ORQ --> LF["Langfuse<br/>trazas, scores, prompts"]
    ORQ --> OUT["PDF + lectura web<br/>+ informe de trazabilidad"]

    CC[".claude/<br/>skills · hooks · agents · MCP"] -. "mismo Core Domain" .-> VAL
```

Hay dos piezas que no son ni agente ni base de datos, y son las que sostienen el sistema:

- **El ensamblador de paquetes** traduce «voy a redactar el capítulo 7» en un fichero de contexto concreto. Es el corazón del arnés y conviene que no tenga nada de inteligente.
- **El Core Domain de validación** son scripts de Python puros, agnósticos a quién los llame. El grafo los llama como nodos en producción; Claude Code los llama como skill y como hook cuando un humano edita a mano. **Una sola implementación, dos puntos de ejecución.**

---

## 4. Las seis fases

| Fase | Nombre | Agente | Artefacto | Gate |
|---|---|---|---|---|
| 1 | **Intake** | entrevistador | `Brief` validado | ✅ |
| 2 | **Investigation** | investigador · verificador | Corpus histórico con respaldo comprobado | ✅ |
| 3 | **Plotting** | arquitecto | Premisa, tema, canon, escaleta · **sello del corpus** | ✅ |
| 4 | **Writing** | escritor · validadores · extractor · editor | Capítulos aprobados, resúmenes, continuidad | ✅ |
| 5 | **Publication** | juez | Versión publicada, PDF, lectura web | — |
| 6 | **Regeneration** | escritor · editor | Versión nueva con diff marcado | ✅ |

### Fase 1 · Intake

El sistema arranca de una **premisa inicial** libre que el comprador escribe. Esa premisa no es la Premisa narrativa del módulo 2 de la ontología: es materia prima. Se pasa por una extracción que rellena los huecos del esquema `Brief` (Pydantic) que pueda, y el entrevistador **solo pregunta por lo que sigue vacío o ambiguo** — es lo que impide que la conversación sea un formulario disfrazado.

**Qué recoge el `Brief`.** Tres bloques, y el reparto no es cosmético: el primero describe a quién se regala la novela, el segundo el mundo en el que va a vivir y el tercero las reglas con las que se escribe. Nada de lo que el arquitecto puede inventar entra aquí.

| Bloque | Campo | Quién lo consume |
|---|---|---|
| **Homenajeado** | `nombre_homenajeado`, tal como debe aparecer escrito | `nombres_exactos` |
| | `fecha_nacimiento` | `canon_personaje`, detección de contradicciones |
| | `rol_epoca` — su oficio o posición en el período: armador, copista, boticaria | `canon_personaje` (estatus, voz), estructura social del corpus |
| | `ocasion` — jubilación, aniversario, despedida | Tono y dedicatoria |
| | `elementos_personalizacion` — lista tipada, cada elemento marcable como obligatorio | Bloque 7 del paquete, `cobertura_personalizacion` |
| **Mundo** | `periodo` — inicio, fin, denominación historiográfica | Sub-encargos del investigador |
| | `lugar` | Sub-encargos del investigador |
| | `evento_ancla`, opcional y orientativo — el acontecimiento del que cuelga la novela | Contradicciones, solo si viene relleno |
| | `personajes_historicos` — figuras reales que deben aparecer o que deben evitarse | Plotting, Nota del autor |
| **Obra y frontera** | `genero` con su subgénero | `canon_obra` |
| | `tono` | Voz y estilo, contradicciones |
| | `punto_de_vista`, opcional — por defecto lo fija el arquitecto | Escaleta |
| | `grado_licencia` — estricto, moderado o amplio | `canon_obra.estilo_json` → bloque 6 del paquete; `canon_licencia`, rúbrica del juez |
| | `arcaismo` — mínimo, moderado o marcado | `canon_obra.estilo_json` → bloque 6 del paquete; `canon_glosario` |
| | `contenido_admisible` — violencia, sexo, crudeza | `canon_obra.estilo_json` → bloque 6 del paquete; rúbrica del juez |
| | `palabras_prohibidas`, niveles `novela` y `destinatario` | `canon_prohibida`, `guardrail_prohibidas` |
| | `n_capitulos` y `palabras_por_capitulo`, con los valores de §19 | `longitud_capitulo`, `canon_obra` |

**Los diales de la frontera historia–ficción viajan por el canon.** `grado_licencia`, `arcaismo` y `contenido_admisible` **no los lee ningún validador por sí solos**, y aun así son obligatorios: son la política contra la que el juez puntúa la autenticidad de época y contra la que se decide si comprimir el tiempo es una Licencia legítima o un error. Sin declararlos, esa política existe igualmente pero la pone el modelo, que es justo lo que este arnés evita en todo lo demás.

Para que lleguen a quien escribe, el arquitecto los copia a `canon_obra.estilo_json` al construir el canon, y de ahí entran en el **bloque 6 del paquete de contexto** junto a la voz, el estilo y el glosario (§6). No se convierten en validador nuevo: `contenido_admisible` en particular no es una palabra prohibida —«sin violencia explícita» no es un término que buscar en `canon_prohibida`—, así que lo juzga el juez con la rúbrica, que es la herramienta adecuada para lo que no se puede calcular.

`evento_ancla` es **opcional y orientativo**, y nadie lo rellena por el comprador. Si viene, el `@model_validator` lo contrasta con la fecha de nacimiento del homenajeado y el arquitecto debe anclarlo en la escaleta; si viene vacío, el arquitecto elige sus anclajes contra el corpus, que es lo que ya hace de todos modos. La comprobación vive en un solo sitio y en una sola fase, en lugar de repetirse en el gate de Plotting sobre un dato aparecido más tarde.

**Lo que no entra.** La Premisa, el Tema, la trama, los conflictos, los arcos y la escaleta son obra del arquitecto (Fase 3). Recogerlos en la entrada sería pedirle al comprador que escriba la novela.

**Texto libre no confiable.** Si el comprador pega una anécdota o una carta, el texto entra en una tabla de cuarentena y pasa por un extractor cuya salida está **restringida por esquema a hechos tipados** (`persona`, `lugar`, `fecha`, `objeto`, `anécdota`). El texto en bruto **no llega jamás al prompt del escritor**: solo llegan las filas extraídas, marcadas con `origen = 'texto_libre_no_confiable'`. La defensa contra *prompt injection* es estructural, no una instrucción de «ignora órdenes embebidas»: una inyección tiene que sobrevivir a convertirse en una fila tipada para hacer daño, y no sobrevive.

**Contradicciones.** Las detecta un `@model_validator` de Pydantic sobre el brief ya poblado, no un modelo: edad del homenajeado contra el período elegido, fecha de nacimiento contra el evento histórico ancla, tono festivo contra un período de duelo, dato aportado que coincide con una palabra prohibida. El agente captura el `ValueError`, lo traduce a pregunta y obliga a resolverlo antes de cerrar el brief.

### Fase 2 · Investigation

La fase tiene dos pasos y dos agentes distintos: uno **rellena** el corpus y otro **comprueba** que lo que dice está donde dice que está. La separación es la misma que rige al editor y al juez —quien escribe no aprueba—, aplicada aquí a los hechos históricos.

**Paso 1 · Una sesión, tres búsquedas.** El investigador no recibe «investiga el XIX», y tampoco una tanda de sub-encargos sueltos. Recibe el período y el lugar del brief y una **lista cerrada de seis dimensiones** que definen un período histórico: cronología y eventos, lugar y toponimia de época, cultura material, lenguaje de época, mentalidad, estructura social. Corre en **una única sesión macro con exactamente tres `WebSearch` permitidas**, y su trabajo es repartir esas tres búsquedas entre las seis dimensiones y dejarlas todas pobladas.

El límite lo impone el arnés, no una instrucción del prompt: `allowed_tools` y el contador de invocaciones lo aplican por construcción, y la llamada que sobra no se emite. Y el tope es doble, **tres `WebSearch` y tres `WebFetch`**, porque quien llena la ventana no es la búsqueda sino la página: una búsqueda devuelve una lista de resultados, así que topar solo las búsquedas permitiría abrir doce páginas y reventar el presupuesto igual que antes. Cada fetch va además acotado a 10.000 tokens. Con eso, «tres llamadas a internet» significa literalmente tres páginas leídas.

Que sea una sesión y no seis tiene una contrapartida que conviene decir en voz alta. A favor: el investigador ve a la vez lo que lleva encontrado para cada dimensión y puede cruzarlo, porque la toponimia y la cultura material de un mismo lugar suelen venir de la misma página. En contra: arrastra en su ventana el material de las tres páginas a la vez, y por eso su techo declarado en §12 es el más alto del sistema y gobierna el peor caso de todo el arnés.

Cada hecho se guarda con su enunciado, su estado epistémico, la fuente de la que sale, la ejecución de fase que lo escribió y la **cita textual** en la que se apoya: el fragmento de la fuente copiado tal cual, **acotado a 300 caracteres**. Ese límite hace dos cosas a la vez —obliga al investigador a señalar el fragmento que sostiene ese enunciado concreto en lugar de volcar media página, y mantiene acotado el contexto del verificador—, y la cita no es adorno: es lo único que hace verificable el paso 2. Las referencias que devuelve `WebSearch` —URL y título— se mapean directamente a la entidad `Fuente`.

**Rehacer no contamina el corpus.** Si el Autor rehace la fase desde el gate, el investigador vuelve a correr y escribe hechos nuevos; los de la ejecución anterior **no se borran ni se mezclan**, porque cada hecho lleva el `fase_run_id` que lo escribió y solo cuentan los de la ejecución vigente. Los antiguos quedan como historia consultable. Es el mismo mecanismo que §8 usa para todo lo demás —rehacer, reanudar y ramificar son la misma operación sobre `fase_run` inmutables—, no una excepción de esta fase, y el sello de §4 se calcula sobre las filas vigentes.

**Paso 2 · El verificador de respaldo.** El investigador deja, junto a cada hecho, **el fragmento de la fuente en el que se apoya, copiado como texto**. Cerrada su sesión, un agente distinto lee los pares —enunciado del hecho, fragmento citado— y responde una sola pregunta por hecho: **¿el fragmento dice lo que el hecho afirma, sí o no?**

| Veredicto | Significado | Efecto |
|---|---|---|
| `respaldado` | El fragmento sostiene el enunciado | El hecho conserva su estado epistémico |
| `no_respaldado` | El fragmento no lo dice, dice otra cosa, o no hay fragmento | El hecho **se degrada a `inferido`** y queda marcado |

El verificador **no tiene herramientas y no sale a internet**: todo lo que necesita está ya en la base de datos. Eso lo hace barato, acotado y repetible, y mantiene en pie la regla de que la única puerta a la red es el investigador. Lo que comprueba es exactamente lo que se puede comprobar sin volver a la página: la correspondencia entre lo que el hecho afirma y lo que la referencia guardada dice. Que el fragmento fuera copiado fielmente de la URL es un riesgo que se acepta y queda anotado en §18.

Corre **por lotes de veinte hechos**, una sesión por lote. El troceo evita que el tamaño del corpus convierta la comprobación en una llamada que la guarda de §12 rechaza por pasarse de contexto, que sería el peor final posible: el corpus se quedaría sin verificar y nadie se enteraría.

**Nada de esto borra hechos ni detiene la fase.** Un hecho sin respaldo no desaparece: baja de categoría y aparece destacado en el informe del gate, donde el Autor decide si lo corrige, lo borra a mano o lo deja pasar sabiendo lo que es. La degradación tiene consecuencia real más adelante —el bloque 5 del paquete lleva el estado epistémico hasta el escritor, que ve que ese dato es inferido y no verificado— sin convertir una fase de documentación en una puerta que se atasca.

### Fase 3 · Plotting

El arquitecto consume el brief validado y el corpus, e **inventa la Premisa y el Tema** (que pertenecen al módulo 2 de la ontología y no los escribe ni el cliente ni el entrevistador). Después construye el canon —personajes, relaciones, escenarios, voz, glosario de época— y la escaleta jerárquica: **capítulos → escenas → beats**, con sus anclajes históricos previstos.

**El hueco del arquitecto.** La investigación inicial se hizo sin saber todavía qué iba a necesitar la trama, así que la escaleta destapa huecos: un detalle de cultura material, el nombre de época de una calle, cómo se llamaba un oficio. Para cada hueco el arquitecto dispara **una única llamada** al investigador —una micro-sesión con `max_turns` de 1 o 2 y una sola `WebSearch`— que termina siempre de una de estas dos formas:

- **Lo encuentra.** El hecho entra en `mundo_hecho` con `origen = 'micro_arquitecto'` y sus fuentes, y el arquitecto lo ancla como cualquier otro.
- **No lo encuentra.** Devuelve un veredicto `no_encontrado` que **autoriza al arquitecto a inventarlo**. El dato inventado entra igualmente como fila de `mundo_hecho`, con `estado = 'inferido'`, `origen = 'invencion_autorizada'` y sin fuente.

**El número de huecos está topado en cinco por ejecución de Plotting.** Sin tope, un arquitecto aplicado abre un hueco por escena y la fase que costó tres búsquedas se convierte en la más cara del sistema. Alcanzado el tope el arquitecto no se queda bloqueado: le queda la invención autorizada, que no cuesta nada y produce exactamente la misma fila.

La invención, en cambio, **no se topa: se cuenta**. Poner límite a lo que el arquitecto puede inventar solo le dejaría salidas peores —fallar, o declarar otro origen—, así que lo que hace el arnés es enseñarlo: el informe del gate de Plotting dice cuántos hechos inventados hay y en qué dimensiones. Cuánta libertad es aceptable ya lo declara `grado_licencia` en el brief, y quien la juzga es el juez con el criterio de autenticidad de época.

Que el invento sea una fila del corpus y no prosa suelta no es burocracia: `anclaje_valido` exige en Writing que todo anclaje apunte a un hecho del corpus sellado o a una Licencia declarada. Un detalle inventado que viviera solo en la cabeza del arquitecto tumbaría ese validador en cuanto el escritor lo usara.

**Estos hechos no pasan por el verificador de respaldo**, y es deliberado. Un hecho inventado no tiene fuente que comprobar, y uno recién buscado para tapar un hueco concreto no justifica una segunda ronda de fetches: son pocos, llegan tarde y su estado epistémico ya dice al escritor lo que son. La verificación de respaldo cubre el cuerpo del corpus, que es de donde sale la mayor parte del material de la novela.

**Sello del corpus.** Al aprobarse la escaleta en el gate, se calcula un hash sobre el contenido ordenado de las tablas `mundo_*` y queda registrado en el manifiesto. A partir de ese instante el corpus es de solo lectura: durante Writing nadie puede añadir hechos históricos, solo **anclar** a los existentes o **declarar una Licencia**. El sello se coloca aquí y no al cerrar Investigation por dos razones: permite las micro-sesiones del arquitecto, y garantiza que cualquier rama posterior parta del mismo corpus, sin lo cual las ramas no serían comparables.

### Fase 4 · Writing

Bucle por capítulo, la unidad de generación, validación, checkpoint y regeneración:

1. El **ensamblador** monta el paquete del capítulo N (§6).
2. El **escritor** redacta de una sola vez. Se genera el capítulo entero, no escena a escena: coser escenas generadas por separado es la forma más fiable de producir la prosa mecánica y los saltos que el enunciado prohíbe. La escena queda como unidad de planificación y de traza, no de redacción.
3. **`Validate` corre en dos pasadas**, y las dos viven dentro del bucle de reparación:
   - **Determinista**, de coste cero: los validadores programáticos de §11a que actúan sobre el capítulo. Solo texto contra filas ya escritas.
   - **Del extractor**, una sola llamada y solo si la anterior no dejó incidencias: un **extractor independiente** lee el capítulo y devuelve resumen, delta del estado de continuidad, hechos realmente usados, elementos de personalización usados, **eventos de cronología narrativa** y **veredicto de ejecución** — qué beats planificados y qué hitos de arco anclados a las escenas de este capítulo ocurrieron. Sobre su salida corren `cobertura_capitulo`, `ejecucion_escaleta`, `arco_ejecutado` y **los cuatro invariantes de Lean sobre la cronología acumulada**.
4. Si hay incidencias **bloqueantes**, el **editor** recibe el informe y emite un parche; vuelta a (3), con límite de reintentos.
5. **`ApproveChapter`** marca el estado del capítulo.
6. **Checkpoint** en la misma transacción.

**El extractor es independiente porque mide lo que no puede declarar quien lo hizo.** Si el escritor dijera qué hechos ha usado, el índice hecho→capítulo se construiría sobre la autodeclaración de quien tiene incentivo en decir que los usó todos; y si dijera qué beats ha ejecutado, la comprobación de que el capítulo cumple la escaleta sería el escritor dándose el visto bueno. Es el mismo argumento que separa al editor del juez y al investigador del verificador.

**Corre antes de aprobar y no después, y esto es lo que hace que sirva.** Un veredicto emitido después de `ApproveChapter` no tendría adónde ir: el capítulo ya estaría aprobado y la máquina de estados no tiene ninguna arista de vuelta desde `Checkpoint` a `Repair`. Dentro de `Validate`, en cambio, un beat no ejecutado es una incidencia como cualquier otra. El coste es que el extractor se invoca una vez por intento que supere la pasada determinista, tres veces por capítulo en el peor caso — una llamada de Haiku sobre un texto de mil doscientas palabras, que es el precio más barato al que se puede comprar la comprobación de que el texto ejecutó el plan.

**Dos pasadas y no una, porque preguntar cuesta y contar no.** No tiene sentido preguntarle a un modelo si los beats ocurrieron en un capítulo al que le faltan cuatrocientas palabras o que escribe mal el nombre del homenajeado. Primero lo que es gratis y seguro; la llamada, solo cuando el capítulo ya es defendible.

**Lean va en la segunda pasada y no en la primera, porque depende del extractor.** Lean se genera desde `cronologia_evento`, y las filas con `origen = 'narrativo'` del capítulo N **las escribe el extractor al leerlo**: nadie más sabe qué ocurrió en esa prosa. Ponerlo en la pasada determinista lo dejaría verificando una cronología que llega hasta N−1, es decir, detectando un capítulo tarde justo el fallo que mejor detecta. Sigue siendo barato —generar el fichero y correr `decide` no cuesta tokens— y sigue estando dentro del bucle, que es lo que importa: su veredicto todavía puede volver al editor.

Eso no deja la cronología sin vigilar hasta el capítulo N: lo que la escaleta ya declara —qué día ocurre cada escena y quién está en ella— Lean lo verifica en el **gate de Plotting**, antes de redactar una línea. Los tres puntos en los que corre y qué mira cada uno están en §11c.

**Las filas del extractor cuelgan del intento, no del capítulo.** `uso_hecho`, `intake_uso_dato` y `continuidad` se escriben con el `capitulo_version_id` del intento que las produjo, así que las de un intento descartado quedan colgando de una versión que nunca se aprueba y que ningún manifiesto recoge. No hace falta marcarlas ni borrarlas: la inmutabilidad de §7 ya las deja fuera.

### Fase 5 · Publication

El **juez** lee la novela terminada y aplica la rúbrica de siete criterios. No tiene permiso de escritura sobre el texto: su única salida es un esquema de puntuaciones que se inyecta como *scores* en la traza de Langfuse. Si pasa el gate del juez y el de Lean, se arma el manifiesto de la **versión candidata** y se renderiza contra él la lectura web —índice navegable, ficha de personajes y lugares enlazada a sus capítulos, portada con dedicatoria—. `render_visual` comprueba ese render **antes del `commit`**: si algo no renderiza, la transacción se deshace y no hay versión publicada. Solo después se maqueta el PDF imprimiendo esa misma ruta.

**El navegador ve la versión candidata porque se le sirve, no porque la lea.** La transacción sigue abierta, así que ningún otro proceso puede consultar ese manifiesto: pedirlo a la API devolvería la versión anterior o nada. Lo que hace el nodo es **conducir el navegador con las peticiones de datos interceptadas**, respondiéndolas desde el manifiesto candidato que tiene en memoria. De ahí sale una exigencia sobre el frontend que §16.3 recoge: **todas sus peticiones salen de un único cliente**, porque un componente que se trajera los datos por su cuenta dejaría de ser interceptable y el validador estaría juzgando un render distinto del que se va a publicar.

**Que el render se compruebe antes de publicar y no después es lo que lo hace una puerta.** G5 no admite excepción, y un índice roto detectado tras `PublishVersion` sería una versión ya publicada con la portada mal: no habría adónde volver, igual que le pasaba al extractor antes de meterlo dentro de `Validate`. No hace falta nodo nuevo ni arista nueva, porque la comprobación cabe dentro del propio nodo mientras la transacción sigue abierta.

Publication no lleva gate humano porque el manuscrito ya se aprobó al cerrar Writing, y lo único que queda entre medias es automático.

**En modo batch el umbral del juez informa y no detiene.** Sin gates nadie puede decidir qué capítulo rehacer, y volver a juzgar el mismo texto solo llevaría a `Fail` al segundo rechazo. La nota se registra igual y la novela se publica. **El PDF se imprime después de publicar y su fallo es un aviso**, porque se deriva de una versión ya validada y un navegador ausente no dice nada sobre el texto.

### Fase 6 · Regeneration

El lector pide un cambio: *«el perro se llama Nala, no Toby»*. Por CLI al principio, desde la propia página cuando exista la web.

1. La petición se resuelve contra la story bible y **se modifica la fila del hecho**, no el texto.
2. El índice `uso_hecho` dice qué capítulos lo usan. Digamos 2, 5 y 9.
3. **Esos tres se regeneran**, produciendo filas nuevas en `capitulo_version`.
4. Los posteriores pasan a `Invalidado` y se les corren **solo los validadores de coste cero** —Python y Lean—. Si ninguno falla, se quedan como están y no cuestan un token. Solo se paga la reescritura de los que Lean tumbe.

   Que Lean viva en la pasada del extractor no rompe esto: un capítulo ya aprobado **tiene sus filas de `cronologia_evento` escritas desde que se aprobó**, así que verificarlo es generar el fichero y correr `decide`, sin invocar a nadie. El extractor solo hace falta cuando hay prosa nueva que leer.
5. Se publica un manifiesto nuevo que reutiliza los capítulos no tocados. La versión anterior sobrevive entera.
6. El diff sale de comparar dos manifiestos con un `JOIN`: página de novedades en el PDF, distintivo en el índice web.

Esta política —**invalidación barata, regeneración cara**— existe porque las alternativas son malas: regenerar solo los que usan el hecho deja incoherencias, y regenerar en cascada todo lo posterior convierte un cambio de nombre en reescribir media novela.

La Fase 6 es la prueba de fuego del resto del sistema: solo funciona si el índice hecho→capítulo se pobló bien, si los capítulos son inmutables, si el canon es la fuente de verdad y si Lean puede juzgar la continuidad sin reescribir nada. Si cualquiera de esas cuatro piezas falla, la regeneración lo destapa.

---

## 5. Los nueve roles

| Rol | Fase | Entrada | Salida | Herramientas |
|---|---|---|---|---|
| **entrevistador** | 1 | Premisa libre, respuestas, texto pegado | `Brief` Pydantic | — |
| **extractor de intake** | 1 | Texto pegado en cuarentena | Filas tipadas de `intake_dato` | — |
| **investigador** | 2, 3 | Período y lugar del brief (fase 2) · hueco concreto (fase 3) | Filas `mundo_hecho` + `mundo_fuente`, o veredicto `no_encontrado` | `WebSearch` (3 en fase 2, 1 en fase 3), `WebFetch` |
| **verificador** | 2 | Hechos del corpus con su cita textual | Veredicto `respaldado` / `no_respaldado` por hecho | — |
| **arquitecto** | 3 | Brief + corpus | Premisa, tema, canon, escaleta | — |
| **escritor** | 4, 6 | Paquete de contexto (7 bloques) | Prosa del capítulo | — |
| **editor** | 4, 6 | Capítulo + informe de incidencias | Parche de corrección | — |
| **extractor de capítulo** | 4, 6 | Capítulo redactado + escaleta de sus escenas, con sus beats y los hitos de arco anclados a ellas | Resumen, delta de continuidad, hechos usados, elementos usados, eventos de cronología narrativa y veredicto de ejecución | — |
| **juez** | 5 | Novela completa + rúbrica | Puntuaciones 1-10 + justificación | — |

Todos en **Haiku 4.5**, con `max_turns` y `allowed_tools` declarados por invocación. Solo el investigador tiene acceso a internet; el resto —verificador incluido— trabaja exclusivamente sobre lo que el arnés le entrega.

**El contrato de salida viaja con la llamada.** La salida de cada rol es un modelo Pydantic, y es ese mismo modelo el que le dice al rol qué forma tiene que tener su respuesta: la puerta única de invocación adjunta al prompt el **JSON Schema generado del modelo**, y `schema_guard` valida contra el mismo modelo. El prompt de Langfuse dice *qué* hacer; la *forma* no la escribe nadie a mano, así que no hay dos descripciones que puedan divergir. El esquema es parte del prompt y **cuenta contra el techo del rol** como cualquier otra. Sin esto, un rol que solo recibe su prompt de rol improvisa los nombres de los campos: es lo que hizo el entrevistador en la primera ejecución real.

**Los dos extractores son roles y no funciones del arnés**, y conviene decirlo porque su salida no es prosa: es estructura. Lo son porque consumen contexto y por tanto necesitan techo declarado —el presupuesto de §12 se garantiza sumando techos, y un agente sin fila sería un hueco en ese método—, y porque su independencia es exactamente la misma que la del verificador: el de intake convierte texto no confiable en filas tipadas sin que el texto llegue nunca a un prompt de redacción, y el de capítulo mide qué se usó y qué se ejecutó sin ser quien lo escribió.

**Investigador y verificador son dos agentes distintos por la misma razón que editor y juez.** Si el propio investigador declarase que sus hechos están respaldados, el respaldo mediría la seguridad en sí mismo de quien tiene incentivo en haber terminado, no si la página dice lo que él afirma. Es el mismo argumento que hace independiente al extractor que puebla `uso_hecho` en §4.

**Editor y juez son dos agentes distintos y esto no es negociable.** El editor pertenece al bucle de control; el juez, a la capa de observabilidad. Si los fusionas, el mismo agente que optimiza la métrica es el que la produce, y los *scores* dejan de significar nada. La separación además hace que la revisión humana del apartado 5b del enunciado ocupe **exactamente el asiento del juez**: misma rúbrica, mismos criterios, y sin poder editar tampoco.

### Sobre el juez en Haiku

Un Haiku puntuando siete criterios es más ruidoso que un modelo mayor, y la estabilidad métrica es una de las dos promesas de reproducibilidad del sistema (§13). No se asume: **se mide**. El juez se ejecuta N veces sobre la misma novela y se publica la desviación por criterio. Si cae dentro de la tolerancia declarada, queda *demostrado* que Haiku basta, que es un resultado más fuerte que suponerlo. Si no, subir solo ese rol es una línea en el frontmatter del agente, y la tabla antes/después es la iteración de tuning documentada.

---

## 6. Paso de contexto

El escritor **no tiene herramientas de recuperación**. Un módulo Python puro lee SQLite y monta el paquete del capítulo N con siete bloques, en este orden:

| # | Bloque | Contenido | Techo |
|---|---|---|---|
| 1 | **Encargo** | Capítulo N, sus escenas con sus beats, objetivo dramático, extensión objetivo, los hitos de arco que este capítulo debe cubrir y **lo que quedó pendiente en N−1** | 800 |
| 2 | **Canon relevante** | Fichas de los personajes presentes en esas escenas y de sus escenarios, más los que la búsqueda semántica marque como relevantes. No la biblia entera | 2.500 |
| 3 | **Continuidad** | Estado estructurado al cierre de N−1: dónde está cada personaje, qué sabe, qué posee, heridas, relaciones, fecha narrativa | 1.500 |
| 4 | **Memoria** | **Texto íntegro de N−1** + los resúmenes previos más relevantes para este capítulo, ordenados por similitud | 4.000 |
| 5 | **Anclajes** | Los hechos anclados por la escaleta a las escenas de este capítulo, más los vecinos semánticos del corpus sellado, con estado epistémico y fuente | 1.500 |
| 6 | **Reglas** | Voz, estilo, glosario de época, palabras prohibidas, y la política de licencia, arcaísmo y contenido admisible | 1.200 |
| 7 | **Personalización** | Elementos del brief que este capítulo tiene que tocar | 500 |
| | **Total** | | **12.000** |

El bloque 4 incluye el **texto íntegro** del capítulo anterior y no solo su resumen porque la voz y el gancho se heredan de la prosa, no de un sumario.

### Selección por relevancia

Los bloques 2, 4 y 5 no se llenan por orden ni por recencia, sino **por relevancia semántica**. El ensamblador construye la consulta a partir del texto de las escenas del capítulo N —objetivo, conflicto, escenario, personajes, fecha narrativa— la vectoriza con FastEmbed y recupera los `k` vecinos más próximos con una consulta KNN de `sqlite-vec` sobre los tres índices: corpus sellado, canon y resúmenes previos. Los anclajes explícitos de la escaleta entran siempre; la búsqueda añade lo que el arquitecto no previó, típicamente cultura material y léxico de época.

Esto es lo que hace que el sistema escale a novelas largas: en el capítulo 10 no hacen falta los nueve resúmenes anteriores con el mismo peso, hacen falta los tres que importan. Sin recuperación por relevancia, la única política posible es recortar por antigüedad, que es tanto como decidir que lo viejo no importa.

El ensamblador **trunca por prioridad** al llegar al techo: se corta por la cola de la lista ya ordenada por relevancia, y el bloque 3 es el último que se toca.

**La recuperación la hace el ensamblador, no el agente, y por eso el principio del §2 sigue en pie.** Sigue siendo determinista: FastEmbed corre en local con el modelo fijado, el corpus está sellado, la consulta se deriva mecánicamente de la escaleta, `k` es un parámetro declarado y la búsqueda de `sqlite-vec` es exhaustiva y no aproximada (§16.2). Con las mismas entradas salen los mismos vecinos, siempre. Lo que cambia respecto a una selección puramente estructural es que **el contexto pasa a depender del corpus**: si el corpus cambia —una edición humana, una regeneración posterior a un cambio de hecho—, el paquete puede recuperar hechos distintos. Es el comportamiento deseado, y es auditable porque el paquete se persiste entero.

**Cada paquete se persiste y se enlaza desde su span en Langfuse.** Poder abrir, delante del evaluador, literalmente lo que el modelo vio cuando escribió el capítulo 7 es la definición operativa de «interpretable». Cuesta casi nada y vale mucho.

---

## 7. Modelo de datos

Un único fichero SQLite por novela, con siete familias de tablas más las propias de LangGraph. La razón de que sea uno solo: el checkpoint del grafo y el capítulo recién aprobado se escriben **en la misma transacción**. Con ficheros separados existiría un instante en que el grafo cree que el capítulo 6 está hecho y la biblia no lo tenga — y ese es justo el fallo que TLC encontraría.

### `intake_*` — encargo y material del comprador

```sql
intake_brief(id, fase_run_id, version, json, hash, creado_en)
intake_texto_crudo(id, texto, recibido_en, procesado_en)
intake_dato(id, texto_crudo_id, tipo, valor_json, origen, obligatorio)   -- texto_crudo_id anulable
intake_uso_dato(capitulo_version_id, escena_id, dato_id, tipo_uso)
```

**La verdad son las filas de `intake_dato`, no el JSON del brief.** `intake_brief` guarda el `Brief` serializado tal como se cerró en el gate, con el `hash` que después viaja al `manifiesto`, y **no se consulta para decidir nada**: es la fotografía que permite enseñar meses después qué se encargó exactamente, y sostiene la auditabilidad de §13. Lo vivo son las filas: se editan, se cuentan, se anclan, y si se borran disparan la invalidación. Guardar el mismo dato en los dos sitios y dejar que ambos manden sería el error que el resto del documento evita en todas partes — es el mismo razonamiento de «el canon manda sobre el texto», aplicado a la entrada.

`intake_texto_crudo` es la tabla de cuarentena de §4: el texto pegado vive ahí y **no sale de ahí**. Las filas de `intake_dato` son tipadas (`persona`, `lugar`, `fecha`, `objeto`, `anécdota`) y entran por dos puertas, que su columna `origen` distingue: `entrevista`, dictado por el comprador, y `texto_libre_no_confiable`, extraído de la cuarentena. Solo las segundas tienen texto de procedencia, y por eso `texto_crudo_id` admite nulo.

`intake_dato.obligatorio` es lo que hace contable la cobertura, y se comprueba **dos veces**: `cobertura_anclada` verifica en el gate de Plotting que cada elemento obligatorio está anclado a alguna escena, y `cobertura_personalizacion` verifica en el gate de Writing, contra `intake_uso_dato`, que acabó apareciendo en algún capítulo. La primera cuesta un `SELECT` y convierte un fallo de diez capítulos escritos y pagados en un fallo de escaleta; la segunda se queda como red de seguridad, porque anclar no es lo mismo que haber escrito. El índice lo puebla el mismo extractor independiente que puebla `uso_hecho` al aprobar un capítulo, y por el mismo motivo: si lo declarase el escritor, la cobertura se mediría sobre el testimonio de quien tiene interés en decir que lo cubrió todo.

Los datos del comprador viven en esta familia y **no se mezclan con `mundo_*`**, que es corpus histórico y se sella. La consecuencia es que `plan_anclaje` lleva una columna `dato_id` anulable junto a `hecho_id`: una escena puede anclarse a un hecho del corpus, a una entidad o a un elemento de personalización, y los tres caminos quedan registrados igual.

### `mundo_*` — corpus histórico (append-only hasta el sello)

```sql
mundo_fuente(id, tipo, autor, fecha, url, titulo, fiabilidad)
mundo_hecho(id, fase_run_id, enunciado, estado, entidades_json, dimension, origen,
            cita, respaldo, creado_en)
mundo_hecho_fuente(hecho_id, fuente_id)
mundo_entidad(id, tipo, nombre, nombre_epoca, fecha_inicio, fecha_fin, atributos_json)
mundo_sello(id, hash, fase_run_id, calculado_en)
```

`mundo_entidad` cubre períodos, lugares, personajes históricos, cultura material y léxico. Sus columnas `fecha_inicio` y `fecha_fin` son las que alimentan el detector de anacronismos y el cuarto invariante de Lean.

En `mundo_hecho`, `dimension` dice a cuál de las seis dimensiones del período pertenece el hecho; `origen` distingue las tres procedencias posibles —`investigacion_inicial`, `micro_arquitecto`, `invencion_autorizada`—; `fase_run_id` dice qué ejecución lo escribió, y solo son vigentes los de la última; `cita` guarda el fragmento textual de la fuente, de 300 caracteres como mucho, y `respaldo` el veredicto del verificador.

**`estado` y `respaldo` no dicen lo mismo, y conviene que quede claro porque se parecen.** `estado` es una propiedad **del hecho en la historiografía**: si la fuente lo da por asentado, si es materia de debate entre historiadores, si es una inferencia o si sencillamente no se sabe. `respaldo` es una propiedad **de la cita**: si el fragmento guardado sostiene o no el enunciado. Un hecho puede estar perfectamente respaldado por su cita y ser `debatido` —la fuente dice con todas las letras que los historiadores discuten esa fecha—, y otro afirmarse como `verificado` y resultar `no_respaldado` porque la cita hable de otra cosa. La primera viaja al bloque 5 del paquete para que el escritor sepa qué firmeza tiene lo que está usando; la segunda, al informe del gate.

Los hechos con `origen = 'invencion_autorizada'` nacen con `cita` vacía y `respaldo = 'no_aplica'`: no hay nada que comprobar en un dato que el arquitecto inventó con permiso.

### `canon_*` — biblia de la obra (viva)

```sql
canon_obra(id, titulo, premisa, tema, genero, n_capitulos, palabras_por_capitulo, voz, estilo_json,
          homenajeado_id)
canon_personaje(id, nombre, tipo, rasgos_json, objetivo, miedo, voz, estatus,
                personaje_historico_id, fecha_nacimiento, fecha_muerte)
canon_relacion(a_id, b_id, tipo, intensidad)
canon_arco(id, personaje_id, tipo, estado_inicial, estado_final)
canon_arco_hito(id, arco_id, orden, descripcion, escena_id)
canon_escenario(id, lugar_entidad_id, descripcion, detalles_json)
canon_licencia(id, hecho_id, alteracion, justificacion, declarada)
canon_glosario(id, termino, significado, registro)
canon_prohibida(id, nivel, termino, normalizado)
```

`canon_prohibida.nivel` toma tres valores: `global`, `novela` y `destinatario`.

**El Arco tiene tabla porque si no, no puede tener validador.** La ontología de [`definitions.md`](definitions.md) declara el Arco de personaje con su tipo, su estado inicial, su estado final y sus **hitos**, y era lo único del módulo de Historia que el modelo de datos no llevaba: `canon_personaje` guarda objetivo, miedo, voz y estatus, que son estados, no transformación. La consecuencia era que el arco solo podía juzgarlo el juez, sobre la novela entera y una sola vez, porque **todos los validadores deterministas de este sistema hacen lo mismo — comparar el texto contra una fila —** y no había fila.

`canon_arco_hito.escena_id` ancla cada hito a una escena de la escaleta, igual que `plan_anclaje` ancla los hechos. Eso es lo que permite preguntar en el capítulo N si el hito que le tocaba ocurrió, y lo que convierte `plan_beat.cambio_de_valor` —el giro de valor de cada beat, que hasta ahora se rellenaba y no lo leía nadie— en la materia prima de esa comprobación.

`canon_arco.tipo` toma los tres valores de la ontología: **positivo**, **negativo** y **plano**. Que el plano sea un tipo legítimo es lo que hace exigible el arco sin volverlo una carga: declarar que un personaje no se transforma es una decisión sobre él, y es justo la decisión que `arco_anclado` reclama.

`canon_obra.homenajeado_id` apunta a la ficha de la persona a quien se regala la novela. Hasta ahora el homenajeado solo existía como cadena en el `Brief`, que sirve para que `nombres_exactos` compruebe cómo se escribe, pero no para que ninguna consulta sepa **cuál de las fichas es la suya** — y sin eso no se le puede exigir nada distinto que a los demás.

### `plan_*` — escaleta

```sql
plan_capitulo(id, numero, titulo, funcion, gancho)
plan_escena(id, capitulo_id, orden, escenario_id, fecha_narrativa,
            pdv_personaje_id, objetivo, conflicto, resultado)
plan_beat(id, escena_id, orden, accion, cambio_de_valor)
plan_escena_personaje(escena_id, personaje_id)
plan_anclaje(id, escena_id, hecho_id, entidad_id, dato_id, tipo_vinculo)
```

### `texto_*` — capítulos inmutables y versiones

```sql
capitulo_version(id, capitulo_id, fase_run_id, intento, texto, palabras,
                 resumen, estado, creado_en)
version_novela(id, numero, gate_id, judge_score_json, creada_en)
version_capitulo(version_id, capitulo_version_id)
uso_hecho(capitulo_version_id, escena_id, hecho_id, tipo_uso)
uso_hito(capitulo_version_id, escena_id, hito_id, ejecutado)
continuidad(id, capitulo_version_id, personaje_id, escenario_id, fecha_narrativa,
            conocimiento_json, posesiones_json, estado_json)
```

**Nunca se reescribe el contenido de un capítulo.** Lo único que cambia de una fila ya escrita es su `estado`, que es lo que hace `ApproveChapter` en §9; el texto, el intento y a qué capítulo pertenece son intocables, y un `DELETE` no existe. La distinción importa porque una inmutabilidad literal de la fila entera haría imposible cerrar una `fase_run` con su consumo y obligaría a una fila nueva para registrar que algo terminó. Una versión de la novela es el manifiesto `version_capitulo`: la lista ordenada de qué `capitulo_version_id` la componen. De ahí salen gratis tres cosas: la versión anterior se conserva **por construcción y no por disciplina**, el «qué cambió» es comparar dos manifiestos en vez de diffear texto, y un capítulo no regenerado se comparte entre versiones sin duplicarse.

`uso_hecho` registra a granularidad de **escena**; la consulta de regeneración lo agrega a **capítulo**, que es la unidad de reescritura.

`uso_hito` es su gemelo para el arco y existe por la misma razón. [§8](#8-el-grafo-de-ejecuciones-de-fase) fija que la edición humana dispara la misma maquinaria que la petición del lector, y esa maquinaria es un índice: sin él, mover un hito del capítulo 8 al 5 o cambiar el estado final de un arco no invalidaría nada y los avisos de ejecución quedarían calculados contra un arco que ya no existe. Lo puebla el mismo extractor y en la misma llamada —su veredicto de ejecución dice exactamente qué hitos ocurrieron y en qué escena—, así que la tabla cuesta un `CREATE` y ningún token.

### `cronologia_*` — la materia prima de Lean

```sql
cronologia_evento(id, clave, descripcion, momento, lugar_entidad_id, origen)
cronologia_participante(evento_id, personaje_id)
```

`origen` distingue `historico` de `narrativo`. Mezclar ambos en la misma tabla es deliberado: es en esa mezcla donde aparecen las incoherencias que ningún validador semántico detecta.

### `arnes_*` — estado del sistema

```sql
fase_run(id, fase, estado, input_run_id, artefacto_hash, prompt_nombre, prompt_version,
         modelo, tokens_in, tokens_out, coste_usd, trace_id, inicio, fin)
gate(id, fase_run_id, estado, decision, comentario, decidido_por, notificado_en, decidido_en)
incidencia(id, capitulo_version_id, validador, severidad, ubicacion, mensaje, propuesta)
score(id, objeto_tipo, objeto_id, validador, valor, detalle_json)
audit_log(id, momento, actor, accion, objeto, antes_json, despues_json)
edicion_humana(id, fase_run_id, tabla, fila_id, campo, antes, despues, motivo)
procedencia(origen_db, origen_fase_run_id, creada_en)
manifiesto(id, version_novela_id, brief_hash, sello_corpus_hash, prompts_json,
           modelos_json, embeddings_json, sdk_version, creado_en)
```

### `vec_*` — índices semánticos

```sql
CREATE VIRTUAL TABLE vec_hecho USING vec0(
  hecho_id integer primary key,
  embedding float[384] distance_metric=cosine,
  estado text,                     -- metadato: verificado, debatido, inferido, desconocido
  dimension text                   -- metadato: la dimensión del período a la que pertenece
);

CREATE VIRTUAL TABLE vec_canon USING vec0(
  id integer primary key,
  embedding float[384] distance_metric=cosine,
  familia text,                    -- metadato: personaje, escenario, glosario
  +tabla text,                     -- auxiliar: canon_personaje, canon_escenario, canon_glosario
  +fila_id integer                 -- auxiliar: la fila que el vector describe
);

CREATE VIRTUAL TABLE vec_resumen USING vec0(
  capitulo_version_id integer primary key,
  embedding float[384] distance_metric=cosine,
  capitulo_numero integer,         -- metadato: permite pedir solo lo anterior al capítulo N
  vigente integer                  -- metadato: 1 si es la versión que compone la novela hoy
);
```

**Tres índices y no uno**, porque son los tres que el §6 consulta por separado y sus identificadores viven en espacios distintos. `vec_hecho` y `vec_resumen` toman como clave primaria el identificador de la fila de dominio que describen, así que la unión es directa. `vec_canon` no puede: la biblia son tres tablas —personajes, escenarios y glosario— y la clave primaria de una tabla `vec0` es un único entero, de modo que ese índice lleva identificador propio y guarda en **columnas auxiliares** —las del prefijo `+`, que se almacenan sin indexar— a qué tabla y a qué fila apunta.

`estado`, `dimension`, `familia`, `capitulo_numero` y `vigente` son **columnas de metadato**, y por eso se filtran dentro de la propia consulta KNN. `tabla` y `fila_id` son auxiliares porque nunca se filtra por ellas: solo se leen al resolver el resultado.

**`vec_resumen` necesita `vigente` porque de un mismo capítulo hay varias `capitulo_version`**: los reintentos del bucle de Writing y las que deja cada regeneración. El bucle pone `vigente = 1` al aprobar una versión y a 0 la que sustituye, y el bloque 4 del paquete pide `capitulo_numero < N AND vigente = 1`. Sin ese filtro, el escritor del capítulo 7 podría recibir el resumen de un intento rechazado del 3: un fallo silencioso, porque el capítulo saldría bien escrito recordando algo que ya no está en la novela. No se filtra contra el manifiesto porque las columnas de metadato de `vec0` no admiten `IN`.

Ninguna tabla de dominio guarda ya el vector. `mundo_hecho` y `canon_personaje` han perdido su columna `vector`, y recuperar es la consulta KNN seguida de un `JOIN` por identificador.

Las tablas de checkpoint de LangGraph y las tablas `vec0` viven en el mismo fichero.

---

## 8. El grafo de ejecuciones de fase

Una novela no es una cadena lineal de fases: es un **grafo de ejecuciones**. Cada `fase_run` es una fila inmutable que apunta a la ejecución que le sirvió de entrada (`input_run_id`) y registra el hash de su artefacto, la versión de prompt que la produjo, el modelo, el consumo y el coste.

Esto unifica cuatro operaciones que parecían distintas:

| Operación | Es un `fase_run` nuevo cuyo `input_run_id` es… |
|---|---|
| Rehacer tras un gate | la ejecución de la fase anterior |
| Reanudar tras un fallo | el último checkpoint válido |
| Ramificar | cualquier ejecución pasada que el autor elija |
| Regenerar por petición del lector | la ejecución de Writing de los capítulos afectados |

Un solo camino de código y un solo conjunto de invariantes. Y trazabilidad completa: cualquier capítulo de cualquier versión se rastrea hasta la escaleta, el canon y el corpus exactos que lo produjeron, con la versión de prompt de cada paso.

### Ramificación

Ramificar es **copiar el fichero**. `novela-7.db` → `novela-7b.db`, se escribe una fila en `procedencia` con el fichero y el `fase_run` de origen, y se continúa desde ahí. El caso de uso es el del autor que, con la novela terminada, quiere ver qué habría salido retomando desde la escaleta.

La alternativa —ramas conviviendo en un mismo fichero con una columna de rama— obligaría a meter un filtro en **todas** las consultas del sistema (índice hecho→capítulo, continuidad, manifiestos, generación de Lean) y bastaría con que una lo olvidara para que la rama B leyese capítulos de la rama A. El coste de copiar es unos cientos de kilobytes de corpus duplicado, y se conserva una propiedad cómoda: una novela es un fichero, y descargarla es copiarlo.

### Edición humana directa

El autor puede eliminar afirmaciones del corpus y modificar el canon o la escaleta. Es una operación de primera clase: queda como fila en `edicion_humana` y en `audit_log` con `origen = 'humano'`, y **dispara exactamente la misma maquinaria que la petición del lector**. Si se borra un hecho que tres capítulos estaban usando, esos tres se invalidan solos por `uso_hecho`. No hace falta código nuevo: es el motor de la Fase 6 entrando por otra puerta. El corpus se re-sella y el manifiesto registra qué sello se usó.

---

## 9. Máquina de estados

Los nodos de LangGraph y las acciones de la especificación TLA+ **se llaman igual**. La tabla de correspondencia del README no es una narración: es una lista de identidades.

```mermaid
stateDiagram-v2
    [*] --> Configure
    Configure --> AwaitApproval : gate Intake
    AwaitApproval --> Research : aprobado
    AwaitApproval --> Configure : rehacer con comentario
    AwaitApproval --> [*] : abortado

    Research --> VerifyCorpus
    VerifyCorpus --> AwaitApproval2 : gate Investigation
    AwaitApproval2 --> Plan : aprobado
    AwaitApproval2 --> Research : rehacer

    Plan --> FillGap : hueco, con huecos disponibles
    FillGap --> Plan
    Plan --> AwaitApproval3 : gate Plotting
    AwaitApproval3 --> SealCorpus : aprobado
    AwaitApproval3 --> Plan : rehacer

    SealCorpus --> WriteChapter
    WriteChapter --> Validate
    Validate --> Repair : incidencias y reintentos disponibles
    Validate --> Extract : pasada determinista limpia
    Extract --> Repair : incidencias bloqueantes y reintentos disponibles
    Repair --> Validate
    Validate --> Fail : reintentos agotados
    Extract --> Fail : reintentos agotados
    Extract --> ApproveChapter : sin incidencias bloqueantes
    ApproveChapter --> Checkpoint
    Checkpoint --> WriteChapter : quedan capitulos
    Checkpoint --> AwaitApproval4 : gate Writing

    AwaitApproval4 --> Judge : aprobado
    AwaitApproval4 --> WriteChapter : rehacer
    Judge --> PublishVersion : umbral superado
    Judge --> AwaitApproval4 : umbral no superado

    PublishVersion --> Idle
    Idle --> RequestChange : peticion del lector o edicion humana
    RequestChange --> Invalidate
    Invalidate --> RegenerateAffected
    RegenerateAffected --> Validate
    Idle --> Branch : ramificar
    Branch --> [*]
    Fail --> [*]
```

`VerifyCorpus` es un nodo y no una herramienta que el investigador decida invocar, por la razón de §1: lo que un agente puede olvidarse de llamar no es una comprobación. `FillGap` también lo es, y además por una razón práctica: el contador de huecos vive en el estado del grafo, que es el único sitio donde un tope se puede imponer de verdad.

`ResumeFromCheckpoint` no aparece como estado porque es una **arista de entrada** a cualquier nodo desde el checkpoint persistido: el mismo mecanismo sirve para reanudar tras un fallo, tras un gate y tras una ramificación.

### Correspondencia acción ↔ implementación

| Acción TLA+ | Nodo LangGraph | Efecto en SQLite |
|---|---|---|
| `Configure` | `intake.configure` | Inserta `Brief`, abre `fase_run` |
| `Research` | `investigation.research` | Puebla `mundo_*` con la ejecución vigente |
| `VerifyCorpus` | `investigation.verify` | Escribe `respaldo` y degrada `estado` en `mundo_hecho` |
| `Plan` | `plotting.plan` | Puebla `canon_*` y `plan_*` |
| `FillGap` | `plotting.fill_gap` | Inserta un `mundo_hecho` con `origen = 'micro_arquitecto'` o `'invencion_autorizada'`; descuenta un hueco |
| `SealCorpus` | `plotting.seal` | Escribe `mundo_sello` |
| `WriteChapter` | `writing.write` | Inserta `capitulo_version` |
| `Validate` | `writing.validate` | Inserta `incidencia` y `score` de la pasada determinista |
| `Extract` | `writing.extract` | Puebla `uso_hecho`, `uso_hito`, `intake_uso_dato`, `continuidad` y `cronologia_evento` del intento; inserta `incidencia` y `score` de cobertura, ejecución y Lean |
| `Repair` | `writing.repair` | Inserta `capitulo_version` con `intento+1` |
| `ApproveChapter` | `writing.approve` | Marca el estado del capítulo |
| `Checkpoint` | `writing.checkpoint` | Checkpoint de LangGraph, misma transacción |
| `AwaitApproval` | `gates.await` | `interrupt()`, inserta `gate` pendiente |
| `HumanDecide` | endpoint FastAPI | Actualiza `gate`, reanuda con `Command(resume=...)` |
| `Judge` | `publication.judge` | Inserta `score` del juez |
| `PublishVersion` | `publication.publish` | Renderiza la versión candidata, corre `render_visual` e inserta `version_novela` y `version_capitulo` en la misma transacción |
| `RequestChange` | `regeneration.request` | Modifica el hecho, registra en `audit_log` |
| `Invalidate` | `regeneration.invalidate` | Marca capítulos posteriores |
| `RegenerateAffected` | `regeneration.regenerate` | Nuevas `capitulo_version` |
| `ResumeFromCheckpoint` | `graph.invoke(Command(...))` | Lee checkpoint |
| `Branch` | `branch.fork` | Copia el fichero, inserta `procedencia` |

**La identidad se comprueba sobre los nombres y sobre las aristas.** Un grafo con las veintiuna acciones bien nombradas y el cableado equivocado pasaría una comparación de conjuntos de nombres sin parecerse en nada al modelo que TLC verificó, porque lo que TLC explora son transiciones. Por eso la prueba compara además el conjunto de aristas del `StateGraph` con la relación de transición de `harness.tla`. Esa relación no se extrae parseando el modelo, que estaría desparramada por las guardas de cada `process`: la especificación la declara en una definición TLA+ explícita, `Aristas`, **que gobierna el `Next` que TLC explora**. Leerla desde la prueba es entonces trivial y no puede divergir de lo verificado; si la definición solo acompañara al modelo en vez de gobernarlo, sería una tercera copia más que mantener a mano. Es donde más importa: que `Repair` tenga dos aristas de entrada compartiendo un único contador de intentos es, según §11d, la razón por la que `RetriesBounded` existe.

La tercera columna de la tabla —el efecto en SQLite— no la comprueba ninguna prueba de identidad, sino las de integración, y cada una declara qué fila de esta tabla demuestra.

---

## 10. Gates humanos y notificación

Cinco gates bloqueantes: **Intake, Investigation, Plotting, Writing y Regeneration**. Publication no lo lleva porque solo maqueta lo ya aprobado.

### Mecánica

El nodo del gate llama a `interrupt()` de LangGraph; el checkpointer persiste el estado en el mismo SQLite de la novela y **el proceso termina**. Cuando el autor decide, lo hace **en su PC**: `storymaker decidir` escribe la decisión en `gate` y reanuda el grafo con `Command(resume=...)`.

Tres consecuencias encadenadas: no hay un proceso vivo doce horas, reiniciar el servidor no mata nada porque el estado está en disco y no en memoria, y **la reanudación por gate usa exactamente el mismo mecanismo que la reanudación por fallo** — un solo camino de código.

### Decisiones disponibles

| Decisión | Efecto |
|---|---|
| **Aprobar** | Avanza a la fase siguiente |
| **Rehacer con comentario** | El texto libre se inyecta como bloque extra en el prompt de esa fase. Cuenta contra el límite de reintentos |
| **Editar** | Modificación directa del corpus, canon o escaleta (§8) |
| **Abortar** | Termina la ejecución con estado de error |

«Rehacer» a secas hace que el agente vuelva a tirar el dado; el comentario es lo que convierte el reintento en dirigido. Todo comentario y toda edición se guardan como fila, se versionan y van al audit log y a Langfuse — la intervención del autor queda trazada igual que la de un agente, y de paso es parte de la revisión humana que exige el enunciado.

### Canal

**Telegram, y solo para avisar**, detrás de una interfaz `Notifier`. WhatsApp exige Meta Business, número verificado y aprobación previa de plantillas de mensaje; Telegram es un token en el `.env`. El mensaje de un gate dice qué fase espera, resume su informe y trae **el comando exacto** para decidir, pero no lleva botones: **la decisión se toma en el PC**, donde el informe se lee entero y no en una pantalla de móvil. Esto tiene además una consecuencia de superficie: sin decisiones por Telegram no hace falta webhook, ni URL pública, ni túnel, ni secreto compartido, y **nada fuera de la máquina del Autor puede reanudar una ejecución**. Si el envío falla, se avisa en la salida del proceso y el gate sigue bloqueando igual: se pierde el aviso, no la puerta. La interfaz `Notifier` deja WhatsApp Business como un adaptador futuro.

Aparte de los gates, y desactivadas por defecto, hay **notificaciones informativas** que no bloquean: «capítulo 6 de 10 aprobado, 0,41 $ acumulados».

### Si el autor no contesta

Por defecto, un *timeout* declarado **aparca** la ejecución con estado propio y la detiene. No hay auto-aprobación: eso convertiría un gate de calidad en un temporizador.

Y los gates **se desactivan enteros** con `gates.enabled = false`. Es imprescindible, no un lujo: los cinco briefs de evaluación tienen que correr desatendidos, y si cada uno pidiera cinco aprobaciones, la tabla de resultados no se terminaría nunca.

---

## 11. Validación

Cinco familias: los **programáticos** de §11a, los **semánticos** de §11b, la **formal de la historia** de §11c, la **formal del sistema** de §11d y la de **correspondencia** de §11e. Las cuatro primeras miran la novela mientras se genera, cada una con su nombre, su punto de ejecución y su *score* en Langfuse; la quinta mira el repositorio y no ve ninguna novela. El plan completo de verificación —qué técnica cubre cada riesgo, con qué clase de confianza y en qué Quality Gate— está en [`verification.md`](verification.md).

### a) Programáticos (deterministas)

| Nombre | Comprueba | Punto de ejecución |
|---|---|---|
| `schema_guard` | La salida de cada rol cumple su modelo Pydantic | Salida de cada nodo agente |
| `nombres_exactos` | Destinatario y personajes escritos exactamente como en el canon | Post `WriteChapter` |
| `longitud_capitulo` | Palabras dentro del rango del brief | Post `WriteChapter` |
| `guardrail_prohibidas` | Palabras prohibidas en tres niveles, con normalización | Post `WriteChapter` (hook) |
| `anacronismo_fechado` | Ningún objeto, término o concepto con `fecha_inicio` posterior a la fecha narrativa | Post `WriteChapter` |
| `anclaje_valido` | Todo anclaje apunta a un hecho del corpus sellado o a una Licencia declarada | Post `WriteChapter` |
| `cobertura_anclada` | Cada elemento obligatorio del brief está anclado a ≥1 escena de la escaleta, contra `plan_anclaje.dato_id` | Gate de Plotting |
| `cobertura_capitulo` | Cada elemento obligatorio que la escaleta ancló a una escena de este capítulo aparece en él, contra `intake_uso_dato` | Post `Extract` |
| `arco_anclado` | Todo personaje presente en ≥3 escenas tiene fila en `canon_arco`; si su arco es positivo o negativo, ≥2 hitos anclados a escenas de capítulos estrictamente crecientes. El homenajeado no puede tener arco plano y su último hito cae en el tercio final | Gate de Plotting |
| `cobertura_personalizacion` | Cada elemento obligatorio del brief aparece en ≥1 capítulo, contra `intake_uso_dato` | Gate de Writing |
| `render_visual` | Índice, ficha de personajes y portada renderizan bien (Playwright MCP) | Dentro de `PublishVersion`, sobre la versión candidata y **antes del `commit`** |

`anacronismo_fechado` y `anclaje_valido` existen solo porque el dominio es histórico, y son los que llevan el sistema bastante por encima del mínimo de tres exigido.

**`arco_anclado` cuenta apariciones, no importancia, y es deliberado.** «Personaje principal» no es algo que el modelo de datos sepa responder: `canon_personaje.tipo` distingue procedencia —inventado, histórico ficcionalizado, histórico de fondo—, no peso en la trama. Contar sobre `plan_escena_personaje` sí es computable, y además dice lo que interesa: de todo personaje que vuelve, el arquitecto tiene que haber decidido qué hace a lo largo de la obra. Con tres escenas de mínimo sobre las veinte o cuarenta de una novela de diez capítulos, recoge a quien recurre sin barrer al que cruza dos veces una taberna.

Lo que evita que esa exigencia se convierta en una puerta atascada es que **el arco plano cuenta**. Al tabernero que sale en cuatro escenas no se le pide una transformación —pedírsela sería mala literatura impuesta por un validador—, se le pide que alguien haya decidido que no la tiene. La única excepción es el homenajeado, a quien sí se le exige arco con hitos y cierre en el tercio final, y se justifica sola: la novela es para él.

**La cobertura se comprueba tres veces, y cada una cuesta menos que la siguiente.** `cobertura_anclada` verifica en el gate de Plotting que cada elemento obligatorio está anclado a alguna escena, y convierte un fallo de diez capítulos escritos y pagados en un fallo de escaleta. `cobertura_capitulo` verifica al escribir el capítulo N que lo que la escaleta le encomendó aparece en él, y convierte un fallo de novela en un reintento de capítulo. `cobertura_personalizacion` se queda en el gate de Writing como red de seguridad, porque las tres miran cosas distintas: anclar no es escribir, y escribir el capítulo N no garantiza que ningún capítulo se quedara sin su parte.

### b) Semánticos

| Nombre | Comprueba | Punto |
|---|---|---|
| `juez_rubrica` | Siete criterios 1-10 con justificación: continuidad, arco, coherencia de personajes, ritmo, prosa, naturalidad de la personalización, autenticidad de época | `Judge` |
| `respaldo_fuente` | Que el fragmento citado por el investigador sostenga el enunciado del hecho | Cierre de Investigation, antes del gate |
| `ejecucion_escaleta` | Que los beats planificados para las escenas de este capítulo hayan ocurrido | Post `Extract` |
| `arco_ejecutado` | Que los hitos de arco anclados a escenas de este capítulo hayan ocurrido | Post `Extract` |
| `revision_humana` | La misma rúbrica, aplicada por una persona a ≥1 novela completa | Fuera de línea |

Que `juez_rubrica` y `revision_humana` usen **el mismo fichero de rúbrica** es lo que hace comparable el juicio humano con el del modelo.

**Tres de ellos no bloquean, y es deliberado.** `respaldo_fuente` degrada el estado epistémico del hecho y alimenta el informe del gate de Investigation, pero ninguna arista del grafo depende de él: una novela de regalo no se detiene porque una fecha del contexto venga mal citada, y por eso el corpus es lo único que el Autor revisa con el informe delante.

`ejecucion_escaleta` y `arco_ejecutado` siguen el mismo criterio por una razón añadida: **son el juicio de un modelo sobre si algo narrativo ocurrió, y eso no es una puerta**. Un beat que el escritor resolvió de otra manera, o un hito que se insinúa en vez de declararse, no son errores; un validador bloqueante los trataría como tales y gastaría los dos reintentos del capítulo discutiendo con el editor sobre una lectura. Abren incidencia de severidad `aviso`, entran en el informe del gate de Writing y **viajan al bloque 1 del paquete del capítulo siguiente**, donde el escritor lee qué quedó pendiente y puede recogerlo.

Ese viaje al capítulo siguiente es lo que los distingue de un simple apunte: sin él, detectar en el capítulo 4 que un hito no ocurrió solo adelantaría la mala noticia. Con él, la corrección entra por donde entra todo lo demás en este sistema —el paquete de contexto ensamblado desde SQLite— y no hace falta ni un gate nuevo ni una arista nueva.

**Viajan los tres avisos más recientes, no todos.** El bloque 1 es el encargo, y es el bloque que nunca debería recortarse; un capítulo que arrastrase siete avisos se los comería. Además, un capítulo con siete avisos no tiene un problema de contexto sino de escritura, y volcárselos enteros al escritor siguiente no lo arregla. Tres son una nota al margen; siete, ruido que compite con lo que hay que escribir.

**En el último capítulo el aviso no viaja a ninguna parte, y es justo donde más importa.** No hay capítulo N+1, y es el capítulo donde cierra el arco del homenajeado, así que es donde `arco_ejecutado` tiene más probabilidad de saltar. Ahí el aviso se convierte en **entrada destacada del informe del gate de Writing**, con el hito concreto que falta escrito en el mensaje. No bloquea —seguiría siendo el juicio de un modelo gastando reintentos en la peor esquina para hacerlo—, pero llega a la única persona que puede decidir si importa, que es donde este sistema pone siempre esa clase de decisión.

**Lo que ninguno de los dos hace es juzgar si el arco está bien.** Cuentan si los hitos ocurrieron, que es contable; si la transformación está ganada o solamente anunciada lo sigue diciendo el juez sobre la obra entera, porque eso solo se puede juzgar entera. La separación es la misma que [`domain-knowledge.md`](domain-knowledge.md) pide al distinguir lo que se evalúa por escena de lo que se evalúa por obra: aquí se evalúa por capítulo la **ejecución**, y por obra la **calidad**.

### c) Formal de la historia — Lean 4

Desde `cronologia_evento`, `cronologia_participante` y las fechas de `canon_personaje` y `mundo_entidad` se genera un fichero Lean con la cronología concreta, verificada por decisión (`decide`). Cuatro invariantes:

1. Los eventos respetan el orden temporal declarado.
2. La edad de un personaje en cada evento es coherente con su fecha de nacimiento.
3. Un personaje no está en dos lugares en el mismo momento.
4. **Un personaje no aparece fuera de sus fechas vitales documentadas** ni después de un evento que lo excluye.

El cuarto es el caso demostrativo. Mezcla la cronología inventada con las fechas duras del corpus histórico, y es donde un LLM falla sin enterarse: un personaje histórico que aparece en una escena tres años después de su muerte documentada le parece perfectamente natural a un modelo, que no tiene modelo mental temporal. A Lean no.

Corre **en tres sitios**, y cada uno mira algo distinto:

| Dónde | Sobre qué | Si falla |
|---|---|---|
| **Gate de Plotting** | La cronología que se deduce de la escaleta: `plan_escena.fecha_narrativa`, `plan_escena_personaje` y las fechas vitales del canon y del corpus | La escaleta vuelve al arquitecto. Aún no hay una línea escrita |
| **Pasada del extractor**, en cada capítulo | La cronología acumulada, ya con los eventos narrativos que el extractor leyó del texto | Vuelve al editor, dentro del bucle y con los reintentos del capítulo |
| **Gate de publicación** | La cronología completa de la novela | La versión **no se publica** |

El primero es el que más barato sale y el último que se añadió: la escaleta ya declara qué día ocurre cada escena y quién está en ella, así que un personaje en dos sitios a la vez, o vivo tres años después de su muerte documentada, **es detectable antes de redactar**. El segundo no sobra por ello, porque el escritor puede meter en una escena a alguien que la escaleta no puso, y esa clase de fallo solo aparece leyendo el texto.

Que el segundo viva en la pasada del extractor y no en la determinista no es una preferencia: las filas de `cronologia_evento` con `origen = 'narrativo'` las escribe el extractor, así que antes de su llamada la cronología del capítulo N sencillamente no existe.

Se verifica una cronología concreta y no teoremas generales porque es automático y no se atasca. La demostración general queda como ampliación.

### d) Formal del sistema — TLA+

**La especificación se escribe directamente en TLA+, no en PlusCal traducido.** Los nombres de los nodos de LangGraph son valores del contador de programa `pc` en lugar de `process`, y **toda acción mueve el `pc` a través de un único operador, `Mueve(de, a)`, que exige `<<de, a>> \in Aristas`**. Modela las **seis fases**, incluidas reanudación y regeneración: si solo se modelara el bucle de generación, los invariantes interesantes quedarían fuera, porque viven precisamente en lo que se habría excluido.

La forma directa conserva lo que la correspondencia de §9 pide de verdad —los mismos nombres y una relación de transición única y explícita— y evita lo que una traducción mantenida a mano introduciría: **una segunda copia con derecho a divergir de su fuente**, que es justo el problema que `Aristas` existe para evitar. Las transiciones se declaran ahí y de ahí se deriva el `Next` que TLC explora, de modo que la prueba de identidad de §9 compara cableado verificado en lugar de parsear el modelo.

**`Extract` es una acción propia de la especificación, no un detalle interno de `Validate`.** La correspondencia nombre a nombre de §9 es una lista de identidades y un nodo sin acción la rompería, pero hay una razón más fuerte: con las dos pasadas, **`Repair` pasa a tener dos aristas de entrada** —desde `Validate` y desde `Extract`— que comparten un único contador de intentos. Es exactamente la clase de interacción por la que `RetriesBounded` existe, y plegarla dentro de `Validate` dejaría al modelo sin comprobar lo único que el cambio introdujo.

**Invariantes de estado**, los que TLC comprueba sobre cada estado alcanzable:

| Nombre | Enunciado |
|---|---|
| `TypeOK` | Toda variable del modelo se mantiene dentro de su dominio declarado |
| `NoPublishUnvalidated` | Nunca se publica una versión que contenga un capítulo que no pasó todos los validadores |
| `ResumeIsExactlyOnce` | La reanudación desde checkpoint no duplica ni pierde capítulos |
| `RetriesBounded` | El número de reintentos por capítulo nunca supera el límite |
| `CorpusSelladoNoSeToca` | Sellado el corpus, ningún nodo vuelve a escribir en `mundo_*` |

`CorpusSelladoNoSeToca` cierra el único invariante de §4 que se sostenía solo sobre la observación de que ningún nodo posterior escribe ahí. Es cierto hoy y nadie lo comprobaba: un atajo futuro que dejara a `RegenerateAffected` tocar el corpus lo rompería sin que ninguna prueba se quejara.

**Propiedades temporales**, que hablan de la traza y no de un estado:

| Nombre | Enunciado |
|---|---|
| `PreviousVersionPreserved` | La secuencia de versiones es *append-only*: ningún elemento ya publicado cambia nunca |
| `Termina` | Toda generación acaba publicando, ramificando o parando con error |

**`PreviousVersionPreserved` es una propiedad de acción y no un invariante de estado**, y la distinción no es formalismo: «la versión anterior sigue siendo recuperable» no es algo que se pueda mirar en una foto del sistema, sino algo que se comprueba entre un estado y el siguiente. Enunciarla como invariante habría exigido una variable de historia que la duplicara.

**Liveness.** En modo batch (`gates.enabled = false`), la propiedad es la directa: toda generación termina publicando una versión o deteniéndose con error.

En modo interactivo, el humano se modela como un **proceso de entorno no determinista** y la propiedad se enuncia **bajo hipótesis de equidad débil** sobre su respuesta: *si el autor acaba respondiendo, toda generación termina*. No es un truco para esquivar el requisito: es la forma correcta de especificar un sistema con intervención humana, porque sin esa hipótesis la propiedad es sencillamente falsa y no hay diseño que la salve.

Verificación con TLC sobre un modelo pequeño —5 capítulos, 2 reintentos— con la especificación y su configuración en `formal/tla/`. TLC no ejecuta el código: explora exhaustivamente los estados alcanzables del modelo y, si encuentra una violación, devuelve el contraejemplo. Los contraejemplos hallados durante el desarrollo se documentan junto al cambio que provocaron, en el registro de iteraciones.

TLC corre en desarrollo, no en cada generación.

### e) De la correspondencia — el documento contra el código

Las cuatro familias anteriores comprueban que una novela está bien hecha. Esta comprueba algo distinto, y hasta ahora implícito: **que el código que corre es el que los documentos describen**. Corre en CI sobre el repositorio, no ve ninguna novela y no produce *score* en Langfuse, sino salida de build.

Existe porque en un proyecto dirigido por especificación la spec solo gobierna mientras alguien la lea. Un apartado especificado que nadie llegó a implementar, un fichero renombrado que el plan sigue nombrando por su nombre viejo, o un validador que en un refactor dejó de bloquear, son derivas silenciosas: no rompen ninguna prueba, porque las pruebas comparan el código consigo mismo.

| Nombre | Comprueba | Efecto del fallo |
|---|---|---|
| `inventario_del_plan` | Que toda ruta y todo símbolo nombrado en la columna «Ficheros y símbolos» de `plan.md` existe en el árbol, y a la inversa | Informa, en dos cubos separados |
| `registro_de_validadores` | Que el registro de validadores deterministas, la tabla de §11a y la de §7.2 de la spec coinciden por pares: mismo conjunto, mismo punto de ejecución, misma condición de bloqueo | **Bloquea.** Un validador que deja de bloquear en silencio destruye la confianza en todos los demás |
| `anclas_de_procedencia` | Que toda ancla `spec:` o `arq:` citada en un docstring existe en el documento, y que todo apartado de §3 y §4 de la spec tiene al menos un símbolo que lo cite | Informa |
| `identidad_nodo_accion` | Nombres **y aristas** del grafo contra `harness.tla` (§9) | **Bloquea** |
| `requisitos_declarados` | Sobre la tabla de requisitos de cada spec: que todo ítem de plan citado en la columna «Ítems» exista en el plan de esa mitad, que ningún apartado de §3 y §4 se quede sin ningún requisito que lo cite, y que ningún identificador se repita ni se reutilice | Informa |

**El registro es el cableado, no un inventario aparte.** `commons/validation/registro.py` es de donde el grafo saca qué validadores componen cada pasada, y de donde el hook de `.claude/` saca los que expone. Un validador que no está registrado sencillamente no corre, de modo que no puede existir un validador vivo fuera del registro: la prueba no confronta dos listas mantenidas a mano, confronta el cableado real contra el documento. Eso sube su garantía de **T** a **A/T** y refuerza la prueba de contrato nodo↔hook en lugar de duplicarla.

**Cada entrada declara la ruta de su implementación como cadena, no como `import`.** Es lo que permite que el registro cubra los once validadores de §11a sin que el Core Domain importe nada de fuera: `schema_guard` vive en `commons/agents/` y `render_visual` conduce un navegador desde `publication/`, y ninguno de los dos podría entrar en un módulo que `core-domain-puro` mantiene limpio. Quien resuelve la ruta es quien compone la pasada.

**Se comparan tres tablas, no dos.** Los mismos validadores están descritos en §11a de este documento y en §7.2 de la spec del backend, y la arquitectura es la fuente de verdad de ambas. Comparar solo el registro contra la spec dejaría a §11a derivar en silencio, así que la prueba confronta las tres por pares. Su alcance son **los once validadores de §11a**: los semánticos, el juez y la revisión humana no tienen fila en el registro porque no son código, y exigírsela convertiría la prueba en una lista de excepciones.

**El inventario informa en dos cubos, y durante el desarrollo solo importa uno.** Mientras el plan se ejecuta, la mayoría de sus ítems todavía no existen —es el estado normal, declarado en §10 del plan—, así que un informe de ausencias sería ruido durante meses. La salida separa lo **declarado y ausente**, que se mira al cerrar cada hito, de lo **presente y no declarado**, que es código que nadie especificó y se mira siempre. En un proyecto donde el documento manda, la segunda deriva es la que contradice el método.

**Las dos direcciones importan, y la segunda es la que no suele escribirse.** Comprobar que cada símbolo del código apunta a un apartado existente detecta el documento que se quedó atrás. Comprobar que cada apartado tiene quien lo implemente detecta lo contrario: lo que se especificó, se dio por hecho y nunca se escribió. Es la única comprobación del proyecto capaz de señalar una **ausencia**, y una ausencia es justamente lo que ninguna suite de pruebas puede ver, porque nadie escribe la prueba de un código que no existe. El alcance de esa dirección se declara para que no sea una exigencia difusa: **§3 y §4 de la spec**, que son sus contratos y sus fases. El resto del documento es prosa de justificación y no se le pide implementación.

**El requisito es la unidad que se traza, y la escribe la spec.** Hasta aquí la correspondencia iba del documento al código pasando por el plan, y el eslabón del documento era el apartado — una unidad cómoda para escribir prosa y mala para comprobar nada, porque un apartado afirma muchas cosas a la vez y se puede implementar a medias sin que se note. Por eso **cada spec enumera sus requisitos con identificador propio**, `REQ-BE-nn` y `REQ-FE-nn`, y cada enunciado dice una sola cosa comprobable. Los identificadores son estables y no se reutilizan: un requisito retirado deja su fila con la nota, igual que en las matrices.

**Cada requisito declara dónde nace y quién lo realiza, en su propia fila.** Los requisitos viven en un apartado propio al final de la spec, en una tabla única, y cada fila lleva el apartado del que se extrae y los ítems del plan que lo materializan. Así la correspondencia requisito↔ítem vive donde vive el requisito y no abre una cuarta lista que mantener: las tres matrices siguen tratando arquitectura↔plan, que es una pregunta distinta. **La clase de confianza y el gate se heredan del apartado citado**, que ya los declara, y un requisito que se compruebe de otra manera lo dice como excepción en su fila.

**El apartado sigue siendo la unidad del docstring.** `anclas_de_procedencia` no cambia: el ancla de un módulo cita `spec: §3.6 · arq: §11a`, no un requisito. Medir la cobertura inversa sobre requisitos sería más fino, pero exigiría que cada uno tuviera ya código que lo citara, y durante la ejecución del plan eso convierte un informe en una lista de ausencias. El requisito es la unidad que se traza contra el plan; el apartado, la que se traza contra el código.

**Las tablas de validadores de la spec no generan requisitos.** §7.1 y §7.2 de la spec del backend ya son listas con identificador propio —el nombre del validador—, comparadas por pares contra §11a y contra el registro. Duplicarlas con un segundo identificador añadiría cincuenta y siete filas sin añadir ninguna comprobación. Lo que sí se enuncia como requisito es lo que esos apartados afirman alrededor de las tablas: que ningún validador sea una herramienta, que las dos pasadas de `Validate` corran en ese orden, que tres semánticos no bloqueen.

**Los requisitos se derivan del propio documento, no de `REQUIREMENTS.md`.** El checklist del encargo vive en su carril y se audita aparte, en `docs/requirements-audit.md`. Importar sus identificadores a la spec ataría el contrato técnico a un documento que no lo gobierna —la spec deriva de esta arquitectura, no del encargo— y dejaría sin enunciado la mayor parte de lo que la spec decide, que el encargo ni menciona. Enunciar lo que el documento ya afirma no le añade decisiones: le da una forma comprobable.

**Tres informan y dos bloquean**, y el reparto sigue el criterio de producto: bloquea lo que protege una puerta —el registro, porque sostiene G3, y la identidad, porque sostiene lo que TLC verificó—, e informa lo que solo describe la forma del repositorio o el estado de avance de un plan que todavía se está ejecutando.

**Lo que esta familia no puede comprobar** es que los documentos digan la verdad sobre el dominio. Que la tabla de la spec y el registro del código coincidan no dice nada sobre si esa tabla es la correcta. Eso sigue siendo inspección del Autor —el grilling antes de implementar y el gate de cada hito—, y queda anotado como **U-18** en `verification.md`.

---

## 12. Presupuesto de contexto

El límite es **100.000 tokens concurrentes**. El Agent SDK **no ofrece forma documentada de consultar cuánto contexto lleva consumido una sesión mientras corre**, así que el límite **no se vigila: se garantiza por construcción**, con un techo declarado por rol y una guarda que rechaza la llamada antes de emitirla si el prompt ensamblado lo excede.

Lo que sí se puede imponer, y es lo que sostiene el techo del investigador, son las dos piezas que gobiernan lo que entra por herramientas. **Contar invocaciones** se hace con un hook `PreToolUse` que devuelve `permissionDecision: "deny"` en cuanto se agota la cuota, de modo que la cuarta búsqueda no llega a emitirse. **Acotar el tamaño de una respuesta** se hace con un hook `PostToolUse` que reescribe el resultado con `updatedToolOutput` antes de que entre en el contexto del agente. Ninguna de las dos es declarativa —no hay opción en `settings.json` ni en `ClaudeAgentOptions` para esto—: se programan una vez en `commons/agents/` y se aplican por invocación.

Esa es exactamente la diferencia que hace honesto el método de este apartado: no se puede preguntar cuánto contexto va consumido, pero sí se puede decidir de antemano cuánto se deja entrar.

| Rol | Prompt + skills | Contexto entregado | Salida máx. | Techo |
|---|---|---|---|---|
| entrevistador | 2.000 | 4.000 | 2.000 | 8.000 |
| extractor de intake | 1.500 | texto en cuarentena ≈ 3.000 | 1.500 | 6.000 |
| investigador (inicial) | 2.000 | 1.000 + 3 × `WebFetch` acotado a 10.000 | 6.000 | 45.000 |
| investigador (micro, fase 3) | 2.000 | 1.000 + 1 × `WebFetch` acotado a 10.000 | 1.000 | 14.000 |
| verificador | 2.000 | hechos con su cita ≈ 8.000 | 2.000 | 12.000 |
| arquitecto | 2.000 | 15.000 | 8.000 | 25.000 |
| escritor | 5.000 | 12.000 | 3.000 | 20.000 |
| editor | 5.000 | 12.000 + capítulo + incidencias | 3.000 | 20.000 |
| extractor de capítulo | 2.000 | capítulo ≈ 2.000 + escaleta de sus escenas ≈ 6.000 | 2.000 | 12.000 |
| juez | 3.500 | novela completa ≈ 26.000 | 3.000 | 32.500 |

El grafo es secuencial, así que el peor caso es un solo agente abierto: **45.000 tokens, la sesión inicial del investigador**. Es el único rol que mete páginas enteras en su ventana, y lo hace tres veces en la misma sesión; de ahí que gobierne el techo del sistema. El número se sostiene sobre dos cosas declaradas: **tres búsquedas como máximo**, impuestas por el arnés y no por el prompt, y **cada `WebFetch` acotado a 10.000 tokens**.

Si algún día se paralelizan las micro-sesiones del arquitecto en Plotting, un semáforo suma los techos declarados de las sesiones abiertas y bloquea antes de abrir la siguiente: con techo de 14.000, admite **siete concurrentes** y rechaza la octava. Hoy corren en serie y el semáforo no hace falta.

Así el límite se afirma con una suma, no con la observación de que nunca se ha llegado.

---

## 13. Reproducibilidad

El sistema promete dos cosas y **no promete una tercera**, y conviene decirlo así porque un modelo generativo no es determinista bit a bit ni a temperatura cero:

- **Auditabilidad.** Cada versión publicada lleva un `manifiesto` con el hash del brief, el hash del corpus sellado, la versión de cada prompt en Langfuse, el id exacto de cada modelo, el modelo de embeddings con su dimensión y la versión del SDK. Cualquier resultado se puede explicar hacia atrás.
- **Estabilidad métrica.** N ejecuciones del mismo brief producen puntuaciones de validadores dentro de una tolerancia declarada y publicada.
- **No se promete el mismo texto.** No hay caché de *replay*. La evidencia de que el sistema funciona es el PDF commiteado en `/ejemplos` más su manifiesto, no la capacidad de reconstruirlo carácter a carácter.

---

## 14. Observabilidad

**Langfuse**, con dos capas:

- **Spans manuales emitidos por los nodos de LangGraph: la fuente autorizada.** Una **sesión por novela**, que incluye la entrevista y todas las regeneraciones posteriores. Un **span por invocación**, nombrado `capitulo_07 · escritor · intento_2`. Tokens, coste y latencia salen del `ResultMessage` del Agent SDK (`usage` desglosado en input, output, `cache_creation` y `cache_read`, más `total_cost_usd`).
- **Exportación OTLP nativa de Claude Code: capa enriquecedora, opcional.** Activable por variable de entorno. Añade por debajo los spans internos de cada agente —llamadas al modelo, ejecuciones de herramientas y de hooks, cadenas de subagentes— sin instrumentar nada. Está en beta y no está documentado que funcione por la vía del SDK de Python, así que **la observabilidad no depende de ella**.

Todos los *scores* de validadores —programáticos, semánticos y Lean— se envían asociados a su traza. Las decisiones de los gates también.

**Prompts.** Los prompts de rol viven en **Langfuse como fuente de verdad** y se inyectan como `system_prompt` en la invocación; el id de versión viaja en el span. Es lo que permite cambiar un prompt sin tocar el repositorio y ver el efecto en las métricas, que es el requisito real detrás de «la iteración de tuning muestra qué versión de prompt produjo cada resultado». Las *skills* y `CLAUDE.md`, que Claude Code carga por sí mismo desde el disco, se quedan en el repositorio y se registran por su hash.

Nota honesta para la propuesta económica: `total_cost_usd` del SDK es una **estimación en cliente**, no facturación.

---

## 15. Guardrails y policy

**Palabras prohibidas**, en `canon_prohibida`, tres niveles: `global` (insultos y términos ofensivos), `novela` (temas que el comprador excluye) y `destinatario` (por ejemplo el nombre de una expareja). La detección **normaliza antes de comparar**: mayúsculas, acentos, plurales y variantes simples. Si hay coincidencia, el capítulo vuelve al escritor con límite de intentos; agotado el límite, la generación se detiene e informa. Cada coincidencia va al `audit_log` y a Langfuse. Hay tests para un caso de cada nivel y un caso de variante con acento o plural.

**Datos personales.** Los datos del homenajeado viven en el fichero de su novela y no salen de él. El texto libre pegado por el comprador nunca llega en bruto a ningún prompt (§4).

**Audit log.** Toda decisión del policy engine, toda decisión de gate y toda edición humana quedan registradas con actor, momento, objeto y estados antes y después.

### El Core Domain, y por qué no hay código duplicado

`chapter_validator.py` y `policy_checker.py` son **Python puro y agnósticos a quién los llama**. Tienen dos consumidores:

- **En producción**, el grafo los ejecuta como nodos y aristas condicionales. Se disparan automáticamente por cada capítulo generado; si fallan, el flujo vuelve al escritor.
- **En desarrollo y edición manual**, se exponen a Claude Code como *skill* y como *hook* desde `.claude/`. Cuando una persona edita un capítulo a mano en el disco, la misma validación comprueba que la edición no haya roto los guardrails ni la continuidad antes de commitear o de regenerar el PDF. Esto cubre el «linter para edición manual» del enunciado sin escribir una segunda implementación.

Una sola lógica, dos puntos de ejecución. Si divergieran, el producto y el editor dejarían de estar de acuerdo sobre qué es válido.

---

## 16. Pila técnica y organización del código

### 16.1 Pila

| Capa | Elección |
|---|---|
| Lenguaje del backend | Python 3.12 |
| API | **FastAPI** — API de lectura y petición de cambio del lector |
| Orquestación | **LangGraph** con `SqliteSaver` |
| Agentes | **`claude-agent-sdk`**, todos los roles en Haiku 4.5 |
| Esquemas | **Pydantic v2** |
| Datos | **SQLite** (`aiosqlite`) con la extensión **`sqlite-vec`**, un fichero por novela |
| Embeddings | **FastEmbed** local (ONNX), `paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensiones |
| Observabilidad | **`langfuse`** |
| Notificación | **`httpx`** contra la Bot API de Telegram, solo saliente |
| CLI | **Typer** |
| Frontend | **React** + Vite, organizado en **Feature-Sliced Design v2.1**, consumiendo la API |
| PDF | **Playwright** `page.pdf()` sobre la propia ruta de lectura de React |
| Validación visual | **Playwright MCP** desde Claude Code |
| Formal | **Lake** (Lean 4) por subproceso · **TLC** (`tla2tools.jar`) solo en desarrollo |
| Entorno y dependencias | **uv** — resolución, *lockfile* y entorno virtual |
| Tests | **pytest** |
| Linter de estructura | **Steiger** sobre `frontend/src`, el linter oficial de FSD — informa, no bloquea |

**El PDF se imprime desde la misma ruta que lee el navegador.** Es la contrapartida de elegir React: si el PDF se maquetara aparte, web y PDF divergirían y la divergencia aparecería el día de la demo. Imprimiendo la ruta de lectura con Playwright —que ya es dependencia por la validación visual— el PDF es literalmente lo que se ve, conserva los enlaces internos que necesitan el índice navegable y la página de novedades, y no hay una segunda maquetación que mantener.

### 16.2 Embeddings: para qué sí y para qué no

FastEmbed corre **en local sobre ONNX**: sin llamada de red, sin credenciales y sin catálogo externo que pueda cambiar bajo los pies. Con el modelo fijado, el mismo texto produce siempre el mismo vector, de modo que la búsqueda semántica es **determinista** y no erosiona la reproducibilidad.

Su función principal es la **gestión de contexto**: son, junto con SQLite, lo que permite que un agente con ventana acotada trabaje sobre una novela cuyo material crece capítulo a capítulo. SQLite guarda la verdad completa; los embeddings deciden qué porción de esa verdad cabe y merece entrar en cada paquete. Cuatro usos:

1. **Llenar por relevancia los bloques 2, 4 y 5 del paquete de contexto** (§6): canon relevante, resúmenes previos y hechos del corpus. Es el uso principal, y el que hace que el sistema no dependa de recortar por antigüedad.
2. **Resolver la petición del lector a un hecho** (Fase 6). «El perro se llama Nala» no dice qué fila tocar; la búsqueda sobre canon y corpus devuelve los candidatos y el autor confirma en el gate. Sin esto, la Fase 6 exigiría que el lector conociera los identificadores internos.
3. **Localizar hechos relevantes para el arquitecto** sin volcarle el corpus entero en la ventana, durante Plotting.
4. **Detectar repeticiones y auto-similitud** entre capítulos, como linter de prosa y de originalidad.

La línea que sí se mantiene es **quién** recupera: el ensamblador, con una consulta derivada mecánicamente de la escaleta, nunca el agente sobre la marcha. Es lo que distingue una gestión de contexto reproducible de un RAG cuyo resultado depende de lo que al modelo se le ocurra preguntar.

**Almacenamiento e índice: `sqlite-vec`.** Los vectores no viven en las tablas de dominio, sino en tablas virtuales `vec0` de la extensión **`sqlite-vec`**, dentro del mismo fichero de la novela y declaradas `float[384] distance_metric=cosine` (§7). Buscar es una consulta KNN —`WHERE embedding MATCH ? AND k = 8 ORDER BY distance`— y la fila de dominio se recupera uniendo por identificador. Tres razones lo sostienen:

1. **La propiedad «una novela es un fichero» queda intacta.** Una tabla `vec0` es una tabla más del mismo SQLite, así que indexar un hecho y escribirlo ocurren en la misma transacción, igual que el checkpoint y el capítulo. Una base vectorial aparte rompería justo el invariante del que cuelga el §7.
2. **El filtro ocurre dentro del índice y no después en Python.** Las columnas de metadato de `vec0` se filtran en la propia consulta KNN con `=`, `!=`, `<`, `>` y `BETWEEN`. Eso importa en el bloque 4 del paquete: pedir los resúmenes más parecidos *entre los capítulos anteriores a N* es una condición de la consulta, no una lista de vecinos que haya que descartar después sin saber cuántos quedarán.
3. **No hay código de búsqueda que mantener.** Con el vector como `BLOB` en la fila, la similitud, el orden y el recorte son código propio repetido en cada sitio que busca.

**El índice se escribe en la misma transacción que la fila.** Lo hace el módulo `commons/embeddings`, no cada feature por su cuenta: quien inserta un hecho, una ficha de canon o un resumen, lo indexa en el mismo `commit`. Importa sobre todo en el canon, que el §7 llama biblia *viva*: cuando el Autor edita una ficha en un gate, la fila de `edicion_humana` dispara el reembedding de lo que tocó. Sin eso, la búsqueda semántica seguiría devolviendo el texto anterior a la corrección, que es justo lo contrario de lo que promete el §10.

**El modelo de embeddings viaja en el manifiesto.** El sello hashea el contenido de las tablas `mundo_*` (§4) y los vectores ya no están ahí, así que el sello no los cubre: reindexar con otro modelo cambiaría lo que el escritor ve en cada paquete sin alterar el hash. Meter 384 *floats* en un hash lo haría frágil sin aportar nada, de modo que lo que se registra es el identificador del modelo y su dimensión, en `manifiesto.embeddings_json`, al lado de `sdk_version`. Así, reindexar con otro modelo se detecta comparando manifiestos —que además dicen cuál era el anterior— y no por un hash que solo sabría decir que algo cambió.

**No se usan claves de partición.** La documentación de la extensión pide cien o más vectores por valor de partición, y una novela tiene unos cientos de hechos en total: particionar por dimensión o por familia sería sobrefragmentar el índice. Lo que en otro sistema serían particiones, aquí son columnas de metadato.

**La extensión no erosiona el determinismo.** `vec0` hace búsqueda **exhaustiva**, no aproximada: no hay índice ANN ni parámetro de *recall* que pueda devolver un vecino distinto en dos ejecuciones. Con el mismo corpus, el mismo modelo y la misma `k` salen los mismos vecinos en el mismo orden, exactamente como con el coseno en NumPy, que es lo que el §13 necesita.

**El precio es una dependencia nativa.** `sqlite-vec` se carga en tiempo de ejecución con `enable_load_extension`, y hay intérpretes de Python compilados sin soporte de extensiones. Es la única pieza de la pila que puede fallar por cómo esté construido el intérprete, así que la carga se comprueba al abrir la base: si falla, el arranque se detiene con un mensaje explícito en vez de degradar en silencio a un sistema sin búsqueda semántica. Queda registrada en §18.

### 16.3 Organización del código

**El backend se organiza *package by feature*; el frontend, en Feature-Sliced Design v2.1.** La asimetría es deliberada. En el backend las features son las fases, y una fase toca a la vez su nodo del grafo, su agente, sus esquemas, sus validadores y sus consultas: tenerlo junto hace que añadir o rehacer una fase sea una sola carpeta, en lugar de un recorrido por seis capas técnicas. En el frontend no hay fases, hay pantallas, y ahí FSD aporta lo que una convención propia no da: capas con una regla de importación comprobable, una API pública por slice y un linter oficial que verifica ambas cosas. FSD es además una metodología *de frontend*: llevarla al backend no describiría un grafo de ejecución mejor de lo que lo describe una carpeta por fase.

```
storyMaker/
├─ CLAUDE.md                     instrucciones del harness, parte del examen
├─ .claude/
│  ├─ agents/                    definiciones de los nueve roles
│  ├─ skills/continuity-check/   skill reutilizable sobre el Core Domain
│  ├─ settings.json              hooks: validación de capítulo y policy
│  └─ mcp.json                   Playwright MCP
│
├─ backend/src/storymaker/
│  ├─ intake/                    entrevistador, Brief, extracción de texto libre
│  ├─ investigation/             sesión inicial, verificador de respaldo, corpus
│  ├─ plotting/                  arquitecto, canon, escaleta, sello
│  ├─ writing/                   escritor, editor, bucle de capítulo
│  ├─ publication/               juez, manifiesto de versión, render
│  ├─ regeneration/              petición de cambio, invalidación, propagación
│  ├─ gates/                     interrupt, decisiones, Notifier de Telegram (solo aviso)
│  └─ commons/
│     ├─ graph/                  `StateGraph`, estado compartido, cableado de nodos
│     ├─ db/                     esquema, migraciones, consultas
│     ├─ agents/                 invocación del Agent SDK, techos por rol
│     ├─ context/                ensamblador de paquetes
│     ├─ validation/             Core Domain: chapter_validator, policy_checker
│     ├─ embeddings/             FastEmbed, tablas `vec0` y búsqueda KNN
│     ├─ formal/                 generador del fichero Lean, runner de lake
│     └─ obs/                    Langfuse: spans, scores, prompts
│
├─ frontend/src/                 Feature-Sliced Design v2.1
│  ├─ app/                       providers, router, estilos globales y fuentes
│  ├─ pages/
│  │  ├─ library/                listado de novelas del directorio proyectos/
│  │  ├─ reading/                lector, índice de capítulos, navegación,
│  │  │                          selección de fragmento y petición de cambio
│  │  ├─ characters/             fichas de personajes y lugares
│  │  ├─ cover/                  portada, dedicatoria y nota del autor
│  │  ├─ versions/               historial, diff de manifiestos, novedades
│  │  └─ print/                  la novela entera en una página, para el PDF
│  │                             y para `render_visual`
│  └─ shared/
│     ├─ api/                    cliente de la API y tipos de transporte
│     ├─ ui/                     kit de componentes
│     ├─ lib/                    utilidades y hooks
│     └─ config/                 rutas y variables de entorno
│
├─ formal/
│  ├─ tla/harness.tla · harness.cfg  especificación en TLA+ y modelo para TLC
│  └─ lean/                         proyecto Lake con los cuatro invariantes
├─ ejemplos/novela-ejemplo.pdf
└─ docs/
```

Cada feature del backend contiene sus nodos de LangGraph, su agente, sus esquemas Pydantic y sus validadores propios. **El grafo que los cablea vive en `commons/graph/`**, porque es justo lo que `commons/` alberga: algo que todas las fases usan y ninguna posee. La dirección de las importaciones queda así en su sitio —el grafo importa los nodos de cada fase, y ninguna fase importa de otra—, y el estado compartido, como el contador de huecos de Plotting, tiene un dueño claro en lugar de acabar definido dentro de la fase que primero lo necesitó. En `commons/validation` viven los dos módulos que el enunciado exige como piezas identificables y que tienen dos consumidores —el grafo y Claude Code—, precisamente porque son transversales a todas las fases.

**El frontend arranca con el juego mínimo de capas: `app/`, `pages/` y `shared/`.** Es FSD válido, y es lo que la propia metodología recomienda. La capa `widgets/` está desaconsejada por la referencia oficial y no se usa. `features/` y `entities/` **no se crean de entrada**, porque la regla de extracción de FSD exige tres condiciones a la vez —uso real en más de un sitio hoy, motivo de cambio independiente de cualquier consumidor, y responsabilidad acotada— y ninguna pantalla las cumple todavía. Crear las carpetas vacías «por si acaso» es justamente el antipatrón que la metodología nombra.

**`library/` y `print/` completan el juego de pantallas, y cada una nace de una decisión ya tomada.** `library/` existe porque §16.4 decide que **el directorio es el registro**: si listar las novelas es listar `proyectos/`, alguien tiene que enseñar esa lista. `print/` existe porque §16.1 decide que **el PDF se imprime desde la propia ruta de lectura**: el lector recorre la novela capítulo a capítulo y la impresora la necesita entera en un solo documento, así que la misma decisión que evita una segunda maquetación obliga a una segunda ruta. Es la única pantalla que no está hecha para un humano — la abren Playwright y `render_visual`.

**Dónde fue `changes/`.** La selección de fragmento y la petición de cambio se ejercen *dentro del lector*, no desde otra pantalla, así que viven en `pages/reading/`. Si el historial de versiones acaba ofreciendo la misma acción, entonces —y solo entonces— se extrae a `features/change-request/`. Es literalmente el caso que la regla de extracción describe, y anticiparlo costaría una capa que hoy no sostiene nada.

**`commons/` pasa a ser `shared/`**, segmentado en `api`, `ui`, `lib` y `config`. Cada segmento expone su propia API pública —`shared/api/index.ts`, `shared/ui/index.ts`— en lugar de un `shared/index.ts` único que mezclaría módulos sin relación. En `shared/api` viven el cliente de la API y los tipos de transporte que devuelve FastAPI; las reglas de negocio no bajan ahí.

**Y el cliente es uno solo: ningún módulo fuera de `shared/api` emite una petición de red.** En otro proyecto sería una regla de higiene; aquí es condición de G5, porque es lo que permite que `render_visual` sirva al navegador la versión candidata que todavía vive en una transacción abierta (§4, Fase 5). Un `fetch` suelto en una pantalla no se puede interceptar, y lo que el validador juzgaría entonces no sería lo que se publica.

**Las dos reglas que el linter comprueba** son que un módulo solo importa de capas estrictamente inferiores, y que dos slices de la misma capa nunca se importan entre sí. **Steiger**, el linter oficial de FSD, las verifica sobre `frontend/src`. Eso convierte la organización del frontend en una propiedad de clase **A** —análisis estático— en vez de una disciplina que haya que recordar, y es la razón principal para preferir FSD a una convención propia.

**Steiger informa, no bloquea.** Una violación de capas se reporta y se arregla, pero no detiene nada: las dos puertas que no admiten excepción son G3 y G5, y ambas van sobre publicar una versión sin validar, no sobre la forma de las carpetas.

**Los assets estáticos van junto al código que los usa**, nunca en una carpeta `assets/` de primer nivel; las hojas de estilo globales y las fuentes van a `app/`.

### 16.4 Procesos, puntos de entrada y ubicación de las novelas

**Lo que termina en cada gate es la invocación del grafo, no el servidor.** El §10 dice que el estado se persiste y que «el proceso termina», y conviene precisar de qué proceso se habla, porque de ello depende la forma entera del backend. Lo que termina es la **invocación**: `graph.invoke(...)` avanza de nodo en nodo hasta encontrar un `interrupt()` o hasta llegar al final, y entonces devuelve el control. Entre una invocación y la siguiente no queda nada vivo —ni un hilo esperando, ni una cola, ni una sesión de agente abierta—, y el servidor de FastAPI sigue en pie únicamente porque atiende otras peticiones: de la novela no guarda nada, porque todo lo que sabía está en su fichero SQLite.

De ahí que haya **dos puntos de entrada y un solo camino de código**:

| Punto de entrada | Quién lo usa | Qué hace |
|---|---|---|
| **CLI (Typer)** | El Autor y las ejecuciones de evaluación | Crea la novela, lanza la invocación, **decide los gates y reanuda**, la reanuda tras un fallo, ramifica y corre los cinco briefs en modo batch |
| **API (FastAPI)** | El frontend | Sirve la lectura y recibe la petición de cambio del lector |

Los dos llaman a la misma función de `commons/graph/`, que abre el fichero de la novela, construye el `StateGraph` con su checkpointer y lo invoca. Un tercer punto de entrada —una cola de trabajos con su worker— añadiría un segundo lugar donde el estado puede vivir, que es justo lo que el §7 evita al meter checkpoint y dominio en la misma transacción.

**La invocación que reanuda un gate corre en el proceso de la CLI.** `storymaker decidir` escribe la decisión en `gate` y, en el mismo proceso, reanuda la invocación hasta el siguiente gate o el final. Si el proceso cae a mitad no se pierde nada que no se pierda con un fallo cualquiera: la decisión ya está escrita, el último checkpoint está en disco y `continuar` retoma por el camino de siempre. El backend no tiene ninguna tarea de fondo.

**Una invocación por novela a la vez, y el fichero es el cerrojo.** Dos invocaciones simultáneas sobre la misma novela —el Autor que decide dos veces desde dos terminales, o un `continuar` lanzado mientras otro proceso reanuda— escribirían sobre el mismo checkpoint y podrían duplicar un capítulo, que es exactamente lo que `ResumeIsExactlyOnce` prohíbe en §11d. Un cerrojo en memoria no basta, porque el CLI y la API son procesos distintos, así que el cerrojo es un fichero `.lock` junto al de la novela, tomado en exclusiva al empezar la invocación y soltado al acabar. **Quien llega segundo es rechazado, no encolado**: una cola sería ese segundo lugar donde vive el estado que este apartado acaba de descartar, y el rechazo no pierde nada porque la decisión del gate ya está escrita y reanudar es el camino de siempre. Un cerrojo huérfano —el que deja un proceso muerto— se rompe a mano desde el CLI, que es la operación de mantenimiento que el Autor hará una vez cada muchas.

**FastAPI sirve el frontend construido, y por eso hay un solo origen.** Fuera del desarrollo —donde Vite recarga en caliente y habla con la API por su proxy— la aplicación de React se construye a estáticos y **los sirve el propio FastAPI**, con la URL base declarada en la configuración. La alternativa, dejar el servidor de Vite levantado al lado, ataría la publicación a un segundo proceso vivo y obligaría al navegador que conduce `render_visual` a conocer dos orígenes, justo cuando este apartado acaba de argumentar que de una novela no debe vivir nada en dos sitios. Con un solo origen, la URL que abre el validador, la que imprime el PDF y la que teclea el lector son la misma, y esa identidad es lo que hace que el PDF sea literalmente lo que se ve.

**Una novela es un fichero, y el directorio es el registro.** Los ficheros viven en `proyectos/`, uno por novela, y ramificar deja el nuevo al lado del original tal como describe el §8. **No hay una base de datos global de novelas, y no la va a haber**: si el registro viviera fuera del fichero, copiarlo dejaría de ser ramificar y descargar una novela dejaría de ser copiarla, que son las dos propiedades de las que cuelga aquella decisión. Listar las novelas es listar el directorio, y los datos que la lista enseña —título, fase en curso, número de versiones— se leen abriendo cada fichero. El precio es que listar cuesta tantas aperturas como novelas haya; con las decenas que este sistema contempla es instantáneo, y no aspira a miles.

**No hay superficie pública que reanude nada.** Ningún endpoint decide un gate ni reanuda una ejecución: eso solo lo hace la CLI, en la máquina del Autor. La API —lectura y petición de cambio, que no toca nada hasta el gate de Regeneration— no lleva autenticación: es un ejercicio académico que corre en local, y montar usuarios y sesiones costaría más que el riesgo que cubre. Queda anotado como riesgo aceptado U-17 en [`verification.md`](verification.md).


---

## 17. Trade-offs registrados

| Decisión | Opciones consideradas | Criterio | Elección |
|---|---|---|---|
| Dominio | Histórica personalizada · contemporánea personalizada · género configurable | Materia real para investigación y validación formal; diferenciación comercial | Histórica |
| Motor | LangGraph · máquina de estados propia · Claude Agent SDK solo · Temporal | Correspondencia con TLA+ sin renunciar a checkpointing y vocabulario estándar | LangGraph con estado explícito |
| Invocación de agentes | Agent SDK · `claude -p` con `stream-json` | Control de modelo, herramientas y turnos por llamada; uso y coste estructurados | Agent SDK |
| Editor y juez | Un agente · dos agentes | Integridad de la métrica | Dos |
| Ubicación de los validadores | Herramientas del editor · nodos del grafo | Que ningún modelo pueda saltarse una validación | Nodos |
| Paso de contexto | Pull con tools · push determinista · híbrido | Reproducibilidad y presupuesto acotable | Push |
| Unidad de generación | Escena · capítulo · planificar por escena y generar por capítulo | Evitar costuras de prosa sin perder granularidad de traza | Planificar escena, generar capítulo |
| Base de datos | Tres ficheros · uno · dos | Atomicidad entre checkpoint y dominio | Uno por novela |
| Versiones | Copia completa · capítulos inmutables + manifiesto · diffs | Que conservar la versión anterior sea estructural | Inmutables + manifiesto |
| Propagación en regeneración | Solo afectados · cascada completa · afectados + revalidación | Corrección sin coste desbocado | Afectados + revalidación |
| Ramificación | Copia de fichero · columna de rama | Simplicidad de consulta y ausencia de contaminación cruzada | Copia de fichero |
| Sello del corpus | Al cerrar Investigation · al cerrar Plotting | Permitir micro-investigación del arquitecto y hacer comparables las ramas | Al cerrar Plotting |
| Forma de la investigación inicial | Una micro-sesión por dimensión · una sesión con tres búsquedas · búsqueda libre | Coste y latencia acotados de antemano, y poder cruzar dimensiones que vienen de la misma página | Una sesión, tres búsquedas, seis dimensiones |
| Verificación del corpus | No verificar · agente que relee la URL · agente que lee la cita guardada | Comprobar el respaldo sin abrir una segunda puerta a internet ni pagar los fetches dos veces | Agente sobre la cita guardada |
| Efecto de un hecho sin respaldo | Borrarlo · bloquear el gate · degradar su estado epistémico | No detener una novela de regalo por una cita floja, sin perder la señal | Degradar a `inferido` e informar al Autor |
| Hueco que el investigador no encuentra | Reintentar · bloquear la escaleta · autorizar la invención | Que Plotting no se atasque por un detalle de cultura material | Invención autorizada, registrada como hecho `inferido` |
| Canal de notificación | Telegram · WhatsApp · ambos | Coste de puesta en marcha | Telegram tras interfaz `Notifier` |
| Dónde se decide un gate | Botones inline en Telegram con webhook · CLI en el PC · pantalla del frontend | Leer el informe entero antes de decidir, y no abrir una superficie pública que reanude ejecuciones | CLI en el PC; Telegram solo avisa |
| Sin respuesta en un gate | Auto-aprobar · aparcar · esperar indefinidamente | No convertir un gate de calidad en un temporizador | Aparcar, y gates desactivables en batch |
| Alcance de Lean | 2 invariantes · 4 · teoremas generales | Maximizar detección sin atascarse en demostraciones | 4 sobre cronología concreta |
| Alcance de TLA+ | Solo el bucle · las seis fases · grafo completo con ramas | Que los invariantes interesantes queden dentro sin que TLC explote | Seis fases, rama como reanudación |
| Trazas | Manuales · OTLP nativo · ambos | Semántica de dominio frente a detalle automático | Ambos, manuales autorizados |
| Frontend | Jinja2 + HTMX servido por FastAPI · React + Vite · Next.js | Ergonomía de la lectura interactiva, aceptando el coste de mantener dos entornos | React, con el PDF impreso desde su propia ruta para que no diverjan |
| Embeddings | FastEmbed local ONNX · proveedor remoto · sin búsqueda semántica | Determinismo, ausencia de red y de credenciales por petición | FastEmbed local, 384d |
| Almacenamiento de los vectores | `BLOB` en la fila + coseno en NumPy · extensión `sqlite-vec` · base vectorial aparte | Filtrar dentro del índice sin salir del fichero de la novela | `sqlite-vec` con tablas `vec0` |
| Alcance de los embeddings | Solo resolución de peticiones y linters · también la gestión de contexto del escritor | Escalar a novelas largas sin recortar por antigüedad, sin perder determinismo | Gestión de contexto, recuperando el ensamblador y no el agente |
| Organización del backend | Por capa técnica · *package by feature* con `commons` | Que rehacer una fase sea tocar una carpeta | Por feature |
| Organización del frontend | *package by feature* con `commons` · Feature-Sliced Design v2.1 · por capa técnica | Reglas de importación comprobables por un linter, en vez de una convención que hay que recordar | FSD v2.1, con el juego mínimo `app/ pages/ shared/` |
| Ejecución del grafo | Dentro del proceso que lo invoca · worker con cola de trabajos · un demonio por novela | Que no haya un segundo lugar donde el estado pueda vivir | Dentro del proceso que lo invoca, también al decidir un gate |
| Registro de novelas | El directorio es el registro · base de datos global de novelas | Que copiar el fichero siga siendo ramificar y descargarlo siga siendo descargar la novela | El directorio |
| Protección de la API | Sin protección · secreto en el webhook · usuarios y sesiones | Superficie real de un proyecto local frente al coste de la alternativa | Sin protección: la API solo lee y registra peticiones, y ningún endpoint reanuda |
| Invocaciones simultáneas sobre una novela | Cerrojo de fichero que rechaza al segundo · cola de trabajos · cerrojo en memoria | Proteger `ResumeIsExactlyOnce` sin crear un segundo lugar donde viva el estado | Cerrojo de fichero, y el segundo se rechaza |
| Modelo | Haiku para todos · mixto | Coste, con la varianza del juez medida en vez de supuesta | Haiku, revisable por evidencia |
| Momento del extractor | Tras aprobar el capítulo · dentro de `Validate`, antes de aprobar | Que su veredicto pueda disparar una reparación en vez de llegar cuando ya no hay arista de vuelta | Dentro de `Validate`, a costa de invocarlo una vez por intento |
| Orden dentro de `Validate` | Una pasada con todo · determinista primero y extractor después | No pagar una llamada para preguntar por los beats de un capítulo que ya falla el recuento de palabras | Dos pasadas, la barata primero |
| Ejecución de la escaleta y del arco | Solo el juez sobre la obra · validador bloqueante por capítulo · aviso por capítulo | Detectar pronto sin convertir el juicio de un modelo en una puerta que gasta reintentos | Aviso por capítulo, que viaja al encargo del siguiente |
| El Arco de personaje | Prosa dentro de `canon_personaje` · tabla propia con hitos anclados a escenas | Sin fila no hay validador posible, porque todos comparan el texto contra una fila | Tabla propia |
| A quién se le exige arco | Solo al homenajeado · columna `principal` que rellena el arquitecto · derivado de apariciones en la escaleta | Que el validador sea computable sin inventar un concepto que el modelo de datos no tiene | Derivado: ≥3 escenas, con el arco plano admitido |
| Dónde corre Lean | Solo sobre el texto · también sobre la escaleta en el gate de Plotting | Detectar la cronología imposible antes de redactar, donde cuesta un párrafo | En los tres puntos, cada uno sobre algo distinto |
| `Extract` en la especificación | Detalle interno de `Validate` · acción propia | Que TLC compruebe el contador con las dos aristas nuevas hacia `Repair` | Acción propia |
| Invalidación al editar un arco | Nada · en bloque desde el primer hito · índice `uso_hito` | Reutilizar la maquinaria de la Fase 6 sin convertir mover un hito en reescribir media novela | Índice `uso_hito`, gemelo de `uso_hecho` |
| Correspondencia documento↔código | Revisión humana por hito · tests de trazabilidad en CI · generar el código desde la spec | Que la deriva se vea sola, sin depender de que alguien compare dos ficheros largos | Tests en CI |
| Qué bloquea de la familia §11e | Todo · solo lo que sostiene una puerta · nada, todo informa | No convertir la forma de una carpeta en una parada, sin dejar sin puerta lo que sostiene G3 | Bloquean el registro y la identidad; informan el inventario y las anclas |
| Alcance de la identidad nodo↔acción | Solo nombres · nombres y aristas · refinamiento demostrado | Cubrir el cableado, que es lo que TLC explora, sin pagar una demostración de refinamiento | Nombres y aristas |
| Cobertura inversa spec→código | No comprobarla · anclas de procedencia en los docstrings · índice de trazabilidad aparte | Detectar el apartado que nadie implementó sin mantener un tercer documento que también se queda atrás | Anclas en el código, que viven donde vive el código |
| Requisitos de la spec | No enumerarlos, dejándolos en prosa · importarlos de `REQUIREMENTS.md` · derivarlos del propio documento | Que la spec se lea como una lista de compromisos comprobables sin atarla a un documento que no la gobierna ni duplicar el encargo | Derivados del propio documento, con identificador propio |
| Forma del registro de validadores | Lista mantenida aparte · el registro **es** el cableado del que grafo y hook se sirven | Que no pueda existir un validador vivo fuera del registro, en vez de comprobar que dos listas coinciden | El cableado |
| Contra qué compara el registro | Solo §7.2 de la spec · solo §11a · las tres por pares | Que §11a no pueda derivar en silencio siendo la fuente de verdad | Las tres, sobre el subconjunto determinista |
| Ruido del inventario durante el desarrollo | Informar de todo · marcar hitos cerrados · dos cubos separados | Ver el código no especificado desde el primer día sin inventar un estado de hito que mantener a mano | Dos cubos |
| Aristas del modelo TLA+ | Parsear `harness.tla` · volcado del grafo de estados de TLC · definición `Aristas` que gobierna el `Next` | Que lo que lee la prueba sea exactamente lo que TLC exploró, sin fragilidad ni una copia más | Definición `Aristas` |
| Cómo conoce el rol la forma de su salida | Describirla en el prompt de Langfuse · adjuntar al prompt el JSON Schema del modelo Pydantic · salida estructurada del SDK (`output_format`) | Una sola fuente para la forma, que funcione igual con el transporte falso y sin Langfuse, y que no ate el contrato a una opción del SDK | JSON Schema adjunto al prompt; `schema_guard` sigue siendo la garantía, y `output_format` queda como salida si el reintento con el error inyectado no basta |

---

## 18. Riesgos conocidos

- **Varianza del juez en Haiku.** Mitigación: se mide y se publica; si excede la tolerancia, se sube solo ese rol.
- **`WebFetch` sin restricción de dominios documentada en el SDK.** Mitigación: tres búsquedas como máximo y cada fetch acotado a 10.000 tokens, de modo que el peor caso de la sesión sea una suma conocida de antemano.
- **Cita fabricada.** El verificador comprueba que el fragmento guardado sostenga el hecho, no que el fragmento esté realmente en la URL: un investigador que invente la cita y el hecho a la vez pasa el control. Mitigación: la fuente queda registrada con su URL y el Autor la tiene a un clic en el informe del gate. Se acepta porque cerrarlo exigiría releer las páginas y duplicar el coste de la fase.
- **Seis dimensiones en tres búsquedas.** El reparto lo decide el modelo, así que una dimensión puede quedar mucho más pobre que las otras. Mitigación: el informe del gate muestra el recuento de hechos por dimensión, y «rehacer con comentario» permite dirigir la segunda pasada a lo que falte.
- **`sqlite-vec` es una extensión nativa.** Se carga en tiempo de ejecución con `enable_load_extension`, y un intérprete de Python compilado sin soporte de extensiones no puede abrirla. Es la única dependencia de la pila que puede fallar por cómo esté construido el intérprete y no por el código. Mitigación: la carga se comprueba al abrir la base y el arranque se detiene con un mensaje explícito, en vez de degradar en silencio a un sistema sin búsqueda semántica.
- **Trazas OTLP en beta.** Mitigación: la observabilidad autorizada son los spans manuales; OTLP es opcional.
- **Corpus insuficiente para la escaleta.** Mitigación: micro-sesiones del arquitecto antes del sello.
- **Regeneración en cascada patológica.** Un cambio que toque un hecho usado en nueve capítulos cuesta nueve regeneraciones. Es correcto, pero caro; el gate de Regeneration permite abortar antes de pagarlo.
- **Los documentos pueden ser coherentes y estar equivocados.** La familia §11e comprueba que el código y la especificación dicen lo mismo, no que lo que dicen sea lo correcto para el dominio: una tabla mal pensada y un registro fiel a ella pasan en verde. Mitigación: el grilling de cada documento antes de implementarlo y la revisión del Autor en el gate de cada hito, que son inspección y no análisis.

---

## 19. Valores por defecto

| Parámetro | Valor |
|---|---|
| Idioma de la novela y de la documentación | Castellano, términos técnicos en inglés |
| Capítulos | 10, parametrizable (`n_capitulos`) |
| Palabras por capítulo | 1.200, rango 1.000–1.500 (`palabras_por_capitulo`) |
| Escenas por capítulo | 2–4 |
| Modelo de todos los roles | Haiku 4.5 |
| Rúbrica del juez | 7 criterios, escala 1-10 con justificación |
| Búsquedas de la investigación inicial | 3 `WebSearch` + 3 `WebFetch`, impuestas por el arnés |
| Dimensiones del período histórico | 6 |
| Techo por `WebFetch` | 10.000 tokens |
| Longitud máxima de la cita | 300 caracteres |
| Hechos por lote del verificador | 20 |
| Huecos del arquitecto por ejecución de Plotting | 5 |
| Búsquedas por hueco del arquitecto | 1 |
| Reintentos por capítulo | 2 |
| Gates | Activos en interactivo, desactivados en batch |
| MCP de navegador | Playwright |
| Skill reutilizable | `continuity-check` |
| Granularidad de `uso_hecho` | Escena, agregada a capítulo |
| Escenas a partir de las cuales se exige arco | 3, contadas sobre `plan_escena_personaje` |
| Hitos por arco positivo o negativo | ≥2, en capítulos estrictamente crecientes |
| Hitos por arco plano | Ninguno |
| Arco del homenajeado | No puede ser plano; su último hito cae en el tercio final |
| Avisos de ejecución que viajan al capítulo siguiente | Los 3 más recientes |
| Severidad de `ejecucion_escaleta` y `arco_ejecutado` | `aviso`, no bloqueante |
| Invocaciones del extractor por capítulo | 1 por intento que supere la pasada determinista, 3 como máximo |
| Modelo de embeddings | `paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensiones |
| Vecinos devueltos en búsqueda semántica | `k = 8` |
| Grado de licencia histórica | Moderado |
| Arcaísmo | Moderado |
| Contenido admisible | Sin violencia explícita |
| Punto de vista | Tercera persona con focalización en el homenajeado |

---

## 20. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | **Telegram solo avisa y los gates se deciden en el PC**, con `storymaker decidir`. Se retira el webhook con su secreto; §1, §3, §10, §16.1, §16.3, §16.4 y §17 se reescriben en consecuencia | Decisión del Autor: el informe de un gate se lee entero antes de decidir, y en el móvil no se lee. Retirar el webhook elimina la única superficie pública que reanudaba ejecuciones, junto con la URL pública y el túnel que exigía en un portátil |
| 2026-09-24 | Fase 5: en modo batch **el umbral del juez informa y no detiene**, y el PDF se imprime tras publicar con su fallo como aviso | La auditoría previa a la primera ejecución real vio que, en batch, un juez por debajo de 6 volvía a juzgar el mismo texto y acababa en `Fail`, y que ningún camino llamaba a `imprimir_pdf`. Es ablandar una puerta que en batch no tiene a nadie detrás, como pide el criterio de producto |
| 2026-09-24 | §5 fija que **el contrato de salida viaja con la llamada**: la puerta de invocación adjunta al prompt el JSON Schema del modelo Pydantic del rol, que cuenta contra su techo. Entra la fila correspondiente en §17 | La primera ejecución real cayó en `Configure`: el entrevistador solo recibía su prompt de rol, no sabía qué campos llevaba un `Brief` e improvisó los suyos. La arquitectura no decía cómo llega la forma al rol, y el código no la mandaba |
| 2026-09-23 | Versión inicial | Cierre de la orquestación, el paso de contexto, la validación formal y los gates antes de escribir código |
| 2026-09-23 | Se extrae el plan de verificación a `verification.md` y se enlaza desde §11 | La arquitectura fija qué se valida; el plan de verificación fija cómo se demuestra, con qué gate y con qué clase de confianza (T/A/I/D/U) |
| 2026-09-23 | Se fija la pila (FastAPI + React), la organización *package by feature* y los embeddings locales con FastEmbed; §16 pasa a ser «Pila técnica y organización del código» | Faltaba declarar con qué se construye cada mitad del sistema, y la búsqueda semántica era un requisito no recogido |
| 2026-09-23 | Los embeddings pasan a ser la gestión de contexto: los bloques 2, 4 y 5 del paquete se llenan por relevancia semántica y no por estructura ni recencia (§6) | Recortar los resúmenes por antigüedad no escala a novelas largas. El determinismo se conserva porque recupera el ensamblador con una consulta derivada de la escaleta, no el agente |
| 2026-09-23 | Se fijan los campos del `Brief` en §4 y se añade la familia `intake_*` en §7, con `dato_id` en `plan_anclaje` | El esquema de entrada no estaba enumerado y el modelo de datos no tenía dónde guardar ni el brief ni el material del comprador. Los diales de la frontera historia–ficción —licencia, arcaísmo, contenido, personajes reales— se declaran aunque ningún validador los lea por sí solos: sin ellos esa política la pondría el modelo |
| 2026-09-23 | Tras el grilling del `Brief`: los diales de la frontera bajan a `canon_obra.estilo_json` y viajan en el bloque 6; `evento_ancla` queda opcional y orientativo; se añade `cobertura_anclada` en el gate de Plotting; §19 recoge los cuatro defaults nuevos | Los diales se declaraban sin llegar a ningún agente, `contenido_admisible` no cabía en una tabla de términos, la propuesta tardía del evento ancla dejaba su validador fuera de fase, y la cobertura solo se descubría con la novela ya escrita |
| 2026-09-23 | La fuente de verdad del encargo son las filas de `intake_dato`; `intake_brief.json` queda como fotografía auditable que no decide nada | Guardar el mismo elemento en el JSON y en la fila dejaba dos copias que discrepan en cuanto el Autor corrige un dato en el gate |
| 2026-09-23 | Investigation pasa de seis micro-sesiones por sub-encargo a **una sesión con tres búsquedas** que puebla las seis dimensiones del período; el techo del investigador sube a 45.000 y el peor caso del sistema con él | Seis sesiones aisladas no ven lo que han encontrado las demás, y las dimensiones de un mismo período suelen venir de la misma página. El coste sigue siendo acotable porque el límite de búsquedas lo impone el arnés |
| 2026-09-23 | Aparece el **verificador**, séptimo rol: lee el fragmento de fuente que el investigador guarda en `mundo_hecho.cita` y dicta si sostiene el enunciado. Un hecho sin respaldo se degrada a `inferido`, no se borra ni bloquea | El corpus era lo único que ningún control miraba antes de que la novela se construyera encima. Se resuelve con el mismo principio que separa al editor del juez, sin abrir una segunda puerta a internet |
| 2026-09-23 | Tras el grilling del plan de Investigation: se corrige §12, que afirmaba que el SDK no permite truncar la salida de herramientas —sí permite, con un hook `PostToolUse` y `updatedToolOutput`, y contar invocaciones con `PreToolUse`—, y §16.3 gana `commons/graph/` | La afirmación era falsa y sostenía el techo del investigador sobre un límite que nada imponía. El argumento de fondo no cambia: lo que sigue sin poder consultarse es el contexto ya consumido, que es la razón real de acotar *a priori*. Y el `StateGraph` no tenía carpeta, lo que acabaría con una fase importando de otra |
| 2026-09-23 | Tras el grilling de la spec de Investigation: el informe del gate de Plotting muestra el recuento de hechos inventados por dimensión | La invención autorizada es gratis y no tiene tope, así que la única defensa razonable es que se vea. Topara no dejaría al arquitecto más salida que fallar o mentir sobre el origen |
| 2026-09-23 | Tras el grilling de Investigation: el tope son 3 `WebSearch` **y 3 `WebFetch`**; `mundo_hecho` lleva `fase_run_id` para que rehacer no mezcle corpus; se separan por escrito `estado` (historiografía) y `respaldo` (la cita); la cita se acota a 300 caracteres y el verificador corre por lotes de 20; los huecos del arquitecto se topan en 5 | Cinco agujeros por los que el presupuesto acotado de §12 se escapaba sin que nadie lo notara: fetches sin tope, corpus acumulado entre ejecuciones, dos columnas que se pisan, citas de media página y huecos ilimitados |
| 2026-09-23 | El hueco que Plotting destapa se resuelve con **una única llamada**, y si no aparece nada el arquitecto queda autorizado a inventar el dato, que entra en el corpus como `invencion_autorizada` con estado `inferido` | Un detalle de cultura material no puede detener la escaleta. Entra como fila del corpus porque `anclaje_valido` exige en Writing que todo anclaje apunte a un hecho o a una Licencia |
| 2026-09-23 | El frontend pasa de *package by feature* con `commons` a **Feature-Sliced Design v2.1**, con el juego mínimo `app/ pages/ shared/` y Steiger como linter (§16.1, §16.3) | Una convención propia no tiene quien la verifique. FSD trae la regla de importación y la API pública por slice con un linter oficial detrás, así que la estructura del frontend pasa a ser clase A. El backend se queda *package by feature*: FSD describe interfaces, no grafos de ejecución |
| 2026-09-23 | Los vectores salen de las tablas de dominio y pasan a tablas virtuales `vec0` de **`sqlite-vec`**: nueva familia `vec_*` en §7, `mundo_hecho` y `canon_personaje` pierden su columna `vector`, y §16.2 se reescribe | El coseno en NumPy obligaba a filtrar después de recuperar, y el bloque 4 del paquete necesita pedir los resúmenes anteriores al capítulo N *dentro* de la consulta. `vec0` vive en el mismo fichero, así que la atomicidad del §7 se conserva, y su búsqueda es exhaustiva, así que el determinismo también |
| 2026-09-23 | Tras el grilling de los dos cambios anteriores: el modelo de embeddings entra en `manifiesto.embeddings_json`, `vec_resumen` gana la columna `vigente`, se declara que el índice se escribe en la misma transacción que la fila y que `edicion_humana` dispara el reembedding, y Steiger informa sin bloquear | Al salir del `mundo_*`, el vector dejó de estar cubierto por el sello. `vec_resumen` acumula una fila por intento y por regeneración, así que sin `vigente` el paquete podía recordar un capítulo descartado. Y nadie decía quién escribe los índices, lo que dejaba el canon vivo y su índice divergiendo en cuanto el Autor editaba una ficha |
| 2026-09-23 | **§11d se reescribe entero** para decir lo que el registro ya había decidido: especificación directa en TLA+, `Mueve(de, a)` sobre `Aristas`, cinco invariantes de estado —los cuatro más `TypeOK` y `CorpusSelladoNoSeToca`— y `PreviousVersionPreserved` enunciada como **propiedad temporal** y no como invariante. Desaparece «PlusCal» de §1, §9, §16.3 y §17 | El cuerpo del apartado seguía diciendo «PlusCal traducido» y enumerando cuatro invariantes mientras el registro y el código decían otra cosa: una fuente de verdad que se contradice a sí misma no es fuente de verdad, y quien la lea de arriba abajo se queda con la versión vieja |
| 2026-09-23 | El árbol de §16.3 pasa a declarar **`formal/tla/` y `formal/lean/`** en lugar de `spec/` y `lean/` | Es donde están los artefactos, y la propia arquitectura ya los citaba así en este registro. Importa más de lo que parece: `inventario_del_plan` compara esas rutas contra el árbol real |
| 2026-09-23 | El frontend gana dos pantallas en §16.3, **`library/` y `print/`**, cada una derivada de una decisión ya tomada —el directorio como registro y el PDF impreso desde la ruta de lectura—, y la portada pasa a llevar también la **nota del autor** | Las dos existían de hecho en cuanto alguien escribía el frontend, y ninguna estaba declarada. La nota del autor se nombraba en §4 como destino de `personajes_historicos` sin decir en qué superficie se enseña |
| 2026-09-23 | §16.4 declara que **FastAPI sirve el frontend construido**, con un solo origen y la URL base en la configuración; §4 Fase 5 declara que **`render_visual` sirve al navegador el manifiesto candidato interceptando sus peticiones**, y §16.3 convierte el **cliente único** de `shared/api` en condición de G5 | Escribir la spec del frontend destapó que el validador que sostiene G5 no tenía forma de ver lo que juzga: la versión candidata vive en una transacción abierta que ningún otro proceso puede leer, y nadie decía quién sirve la página que se abre |
| 2026-09-23 | §11d: la especificación del arnés se escribe **directamente en TLA+** y no en PlusCal traducido. Los nombres de los nodos son valores del contador de programa en lugar de `process`, y todas las acciones mueven el `pc` a través de un único operador `Mueve(de, a)` que exige `<<de, a>> \in Aristas` | El traductor de PlusCal no está disponible en el entorno, y una traducción mantenida a mano sería una segunda copia que puede divergir de su fuente — justo el problema que `Aristas` existe para evitar. La forma directa conserva lo que §11d pedía de verdad: la correspondencia literal de nombres con los nodos de LangGraph, y una relación de transición única que gobierna el `Next` en vez de acompañarlo. Ver `formal/tla/README.md` |
| 2026-09-23 | §11d gana un quinto invariante, `CorpusSelladoNoSeToca`: después del sello, ningún nodo vuelve a escribir en `mundo_*` | El sello del §4 era una propiedad afirmada en prosa y sostenida por que ningún nodo posterior escribía allí, lo cual es cierto hoy y nadie comprueba. Un atajo futuro que dejara a `RegenerateAffected` tocar el corpus lo rompería sin que ninguna prueba se quejara |
| 2026-09-23 | §11c: los invariantes de la cronología se concretan en cuatro y se declara la limitación de I3, que compara **igualdad exacta de momento** y no solape de intervalos | La granularidad de `cronologia_evento.momento` es el día, así que detecta «el mismo día en dos ciudades» y no «dos horas después a cuatrocientos kilómetros». Modelar lo segundo exigiría distancias y velocidades de época. Una limitación que no se declara se lee como una garantía |
| 2026-09-23 | §11d: **la liveness vale bajo equidad fuerte, no débil**, sobre la respuesta del Autor | Lo demostró TLC. La equidad débil solo obliga a una acción continuamente habilitada, y `Aprobar` en el gate de Writing se deshabilita en cuanto el Autor pide rehacer y arranca el bucle de escritura. La traza del Autor que rehace eternamente era admisible bajo `WF`. Los otros tres gates no tienen el problema porque rehacen fases que aún no han producido capítulos, y esa asimetría es invisible leyendo el documento |
| 2026-09-23 | §5 y §9: **los rechazos del juez se acotan**, con arista nueva `Judge → Fail` cuando se agotan | Lo pidió TLC. `Judge → AwaitApproval4 → Judge` era un ciclo sin tope: el Autor aprueba, el juez rechaza, indefinidamente. Era el único bucle del sistema sin acotar —`intentos` y `huecos` sí lo estaban— y ninguna lectura del documento lo había echado en falta |
| 2026-09-23 | §9: el *rehacer* del gate de Writing entra en **modo regeneración**, y no vuelve como pasada inicial | Lo encontró TLC violando `ResumeIsExactlyOnce`. Es lo que §8 ya decía —«rehacer, reanudar, ramificar y regenerar son la misma operación con distinto punto de entrada»—, pero la máquina de estados no lo reflejaba: al volver a `WriteChapter` quedaban los N capítulos aprobados colgando |
| 2026-09-23 | El bucle de Writing gana la comprobación de que el texto ejecutó el plan: `Validate` pasa a dos pasadas con el **extractor dentro y antes de `ApproveChapter`**, aparecen `canon_arco` y `canon_arco_hito`, y con ellos `arco_anclado` (gate de Plotting), `cobertura_capitulo` (bloqueante) y `ejecucion_escaleta` y `arco_ejecutado` (aviso, viajan al bloque 1 del capítulo siguiente). Se corrige además la posición de Lean, que §11c situaba tras aprobar el capítulo | El sistema validaba los hechos magníficamente y la narrativa casi nada, y la causa era la misma en los cuatro casos: los hechos tienen fila y la narrativa no. El Arco estaba declarado en la ontología y ausente del modelo de datos, la cobertura de personalización solo se descubría con la novela entera escrita, y el extractor registraba la deriva de la escaleta como estado oficial en vez de señalarla. Lean, tal como estaba escrito, emitía un veredicto que no tenía ninguna arista por la que volver |
| 2026-09-23 | Tras el grilling de los cambios anteriores: **Lean baja a la pasada del extractor** y gana un tercer punto de ejecución, la escaleta en el gate de Plotting; `arco_anclado` pasa a exigirse por **apariciones (≥3 escenas)** y admite el arco **plano**, con el homenajeado como única excepción; aparecen `uso_hito` y `canon_obra.homenajeado_id`; los avisos se topan en tres y el del último capítulo se destaca en el informe del gate; `Extract` entra como acción propia de la especificación | Cinco hilos que el grilling destapó. Lean en la pasada determinista habría verificado una cronología que llega hasta N−1, porque las filas narrativas las escribe el extractor. «Personaje principal» no existía en el modelo de datos, así que el validador no era computable. Editar un arco no invalidaba nada porque la maquinaria de la Fase 6 indexa hechos, no hitos. Y el aviso del último capítulo —donde cierra el arco— no tenía adónde viajar |
| 2026-09-23 | Se añade §16.4: el grafo corre dentro del proceso que lo invoca y lo que termina en cada gate es la invocación, hay dos puntos de entrada —CLI y API— sobre un solo camino de código, el directorio `proyectos/` es el registro de novelas el webhook de Telegram se protege con un secreto y una invocación por novela se garantiza con un cerrojo de fichero | Escribir la spec del backend obligaba a decidir tres cosas que ningún documento fijaba: qué proceso ejecuta el grafo, cómo encuentra la API las novelas sin romper «una novela es un fichero», y quién puede llamar al único endpoint que reanuda una ejecución |
| 2026-09-23 | §7 precisa que lo inmutable de `capitulo_version` y de `fase_run` es **el contenido**, no la fila entera: el estado del capítulo y el cierre de la ejecución sí se escriben | §7 decía «nunca se hace UPDATE sobre un capítulo» mientras §9 encargaba a `ApproveChapter` marcar su estado. Los dos *triggers* que implementan la regla necesitaban saber cuál de las dos lecturas manda |
| 2026-09-23 | §16.1 fija **uv** como gestor de entorno y dependencias del backend | La pila declaraba el lenguaje y las bibliotecas pero no con qué se resuelven ni se bloquean, y `pip-audit` corre precisamente sobre ese *lockfile*: sin elegirlo, la puerta G1 vigilaba un fichero sin dueño |
| 2026-09-23 | Tras el recorrido de trazabilidad entre `architecture.md` y el plan del backend: §16.4 pasa a citar **U-17** como el riesgo de la API de lectura sin autenticación, en lugar de U-16 | U-16 es en `verification.md` la fiabilidad de `ejecucion_escaleta` y `arco_ejecutado`. La referencia cruzada apuntaba a la fila equivocada, que es la forma más silenciosa de que un riesgo aceptado deje de estar aceptado por escrito |
| 2026-09-23 | Tras el grilling de la spec del backend: los dos extractores pasan a ser roles con techo declarado y §1 sube de siete a nueve; `render_visual` se mueve a **dentro de `PublishVersion`, sobre la versión candidata y antes del `commit`** | El presupuesto de §12 se garantiza sumando techos declarados, y dos agentes que consumían contexto sin fila eran un hueco en ese método, no un detalle. Y `render_visual` se declaraba posterior a `PublishVersion` mientras G5 lo exigía antes: un render roto detectado después es una versión ya publicada, que es justo lo que esa puerta existe para impedir |
| 2026-09-23 | Se añade **§11e, la familia de validadores de correspondencia** —`inventario_del_plan`, `registro_de_validadores`, `anclas_de_procedencia` e `identidad_nodo_accion`—, y esta última pasa a comparar también **aristas** y no solo nombres (§9). §1 gana la fila «Correspondencia documento↔código» y §18 el riesgo residual | En un proyecto dirigido por especificación, la conformidad del código con la spec era lo único que se sostenía solo por disciplina: nada comprobaba que un apartado especificado llegara a implementarse ni que un validador siguiera bloqueando. Bloquean las dos que sostienen una puerta; las otras dos informan, por el criterio de producto |
| 2026-09-23 | Tras el grilling de §11e: el registro de validadores **es el cableado** del que se sirven el grafo y el hook, y la comparación es a tres bandas —registro, §11a y §7.2— sobre el subconjunto determinista; el inventario informa en **dos cubos** y la cobertura inversa se acota a §3 y §4 de la spec; las transiciones del modelo se declaran en `Aristas`, que gobierna el `Next` (§9, §11d) | Cinco hilos: una lista paralela al cableado habría sido una tercera copia con derecho a derivar, §11a podía quedarse atrás siendo la fuente de verdad, el inventario habría informado de ciento veinte ausencias hasta H7, la cobertura inversa sin alcance declarado habría exigido implementar prosa, y las aristas no se pueden leer de la especificación sin parsearla |
| 2026-09-23 | §1 gana la fila «Requisitos de la spec» y §11e el validador `requisitos_declarados`: **cada spec enumera sus requisitos con identificador propio** —`REQ-BE-nn` y `REQ-FE-nn`—, derivados de sus propios contratos y no importados de `REQUIREMENTS.md`. §11e pasa de dos informadores a tres | Las dos specs estaban escritas como prosa continua: se podían leer, pero no comprobar. Sin enunciados numerados no hay forma de señalar cuál quedó sin implementar, y el apartado —que afirma muchas cosas a la vez— es una unidad demasiado gruesa para trazar. El encargo del ejercicio se audita en su carril: atarle la spec habría hecho que el contrato técnico dejara de derivar de esta arquitectura |
