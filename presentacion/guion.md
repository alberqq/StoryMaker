# Guion de la presentación: Novela Relicario

Diez minutos de propuesta formal y cinco de preguntas técnicas. El guion sigue **slide a slide** el deck `storymaker-propuesta.pdf` / `.pptx`. Cada bloque «Qué decir» es también la nota del orador de su slide en el PPTX, así que el guion y el deck dicen lo mismo. Si cambias uno, cambia el otro: las notas salen de este fichero al reconstruir el deck.

Suma **9:30** y deja medio minuto de margen. Si vas justo, se recorta primero en la slide 10 y después en la 16. El ritmo es de unas **150 palabras por minuto**. No hace falta decirlo literal, pero sí mantener las cifras, porque son las que el tribunal va a buscar.

| Bloque | Slides | Tiempo | Acumulado |
|---|---|---|---|
| Portada y contexto | 1-2 | 0:30 | 0:30 |
| Problema y cliente | 3-4 | 1:00 | 1:30 |
| Configuración y lectura | 5-6 | 1:00 | 2:30 |
| Arquitectura del harness | 7-10 | 2:00 | 4:30 |
| Validación, evaluación y observabilidad | 11-16 | 2:00 | 6:30 |
| Guardrails | 17 | 0:30 | 7:00 |
| Presupuesto y coste | 18-19 | 1:00 | 8:00 |
| Demo, versión 2 y cierre | 20-22 | 1:30 | 9:30 |
| Contraportada | 23 | — | — |

---

## Capítulo I · Portada y contexto (0:30)

### Slide 1 · Portada (0:15)

**Qué decir.**
> Buenos días. Soy [TU NOMBRE], de Qapítulo, una iniciativa de Qaracter. Venimos a proponer a Relicario una línea de producto nueva: la Novela Relicario, novelas históricas personalizadas para regalar, verificadas antes de llegar a quien las recibe. Lo que os enseñamos es la prueba de concepto, la versión 1, funcionando de verdad; al final veréis cómo sería la versión 2.

### Slide 2 · Convertimos a la persona homenajeada en protagonista de un momento histórico real (0:15)

**Qué decir.**
> La idea cabe en una frase. El comprador nos da un nombre, una época, unos recuerdos y lo que no debe aparecer. El sistema investiga la época, escribe diez capítulos y verifica cada uno antes de seguir. Abajo tenéis tres novelas reales de diez capítulos, ya publicadas: una cerera en la Santiago del Pórtico de la Gloria, un aprendiz de relojero en el Madrid de Carlos III y una ayudante de iluminación en la Fuente Mágica de Montjuïc.

---

## Capítulo II · Problema y cliente (1:00)

### Slide 3 · Relicario vende emoción, y el regalo personalizado de hoy se queda en la superficie (0:30)

**Qué decir.**
> Quien compra en Relicario no busca un objeto: busca que la otra persona se emocione. Son hijos que preparan una jubilación, parejas en un aniversario o una boda, amigos en unos sesenta. Todos esperan lo mismo: que el homenajeado se reconozca, con su nombre, sus manías y sus recuerdos; que se lea de un tirón, y que sea único, no una plantilla con el nombre cambiado. Y esas dos exigencias pesan igual.

### Slide 4 · Ninguna alternativa actual da a la vez personalización, calidad y precio (0:30)

**Qué decir.**
> Hoy hay tres opciones y cada una falla en algo. El libro de plantilla es barato, pero solo cambia el nombre. El escritor por encargo lo hace todo bien, pero cuesta cientos de euros y tarda semanas. Un chatbot escribe bien una escena, pero en diez capítulos se contradice, repite frases y cierra de golpe. Ese es nuestro hueco: no escribimos mejor que el modelo, lo controlamos capítulo a capítulo. A 59 euros y en horas.

---

## Capítulo III · Configuración y lectura (1:00)

### Slide 5 · Una entrevista corta produce un brief validado con schema (0:30)

**Qué decir.**
> Todo empieza con una conversación corta. El comprador escribe una premisa libre y un agente entrevistador pregunta solo lo que falta. Sale un brief validado con schema, que el autor aprueba en el primer gate. Por el camino, cuatro detectores de código, no del modelo, buscan contradicciones, como una edad que no encaja con la época. Si el comprador pega una carta, el texto se trata como no confiable: va a cuarentena y de ahí solo salen hechos tipados. Aquí también se dice qué no debe aparecer: en este brief de Cádiz, «pirata», «tesoro» y «naufragio».

**Gesto.** Señala la línea de palabras prohibidas del YAML: vuelve en la slide 17.

### Slide 6 · Se lee en web o en PDF, y un cambio se pide seleccionando el texto (0:30)

**Qué decir.**
> La novela se lee en web y en PDF, y las dos salen de la misma ruta: el PDF es la web impresa con Playwright, así que nunca divergen. Tiene un índice navegable que marca los capítulos que cambiaron, una ficha de personajes y lugares sacada de la story bible con enlaces a cada capítulo, y una portada con dedicatoria. Para pedir un cambio, el lector selecciona el fragmento y escribe lo que quiere: eso va al gate de Regeneración. La versión anterior se conserva siempre.

---

## Capítulo IV · Arquitectura del harness (2:00)

### Slide 7 · Seis fases, nueve roles especializados y un humano en cinco puntos de control (0:40)

**Qué decir.**
> Por dentro hay seis fases. En Intake se cierra el brief. En Investigation el investigador, el único con internet, busca los hechos de la época, y un verificador comprueba que cada cita dice lo que el hecho afirma. En Plotting, el planner, el arquitecto, escribe el canon y la escaleta, y se sella el corpus. En Writing trabajan el writer y el editor. Publication la cierra el juez con Lean y el render. Y Regeneration atiende los cambios del lector. Son nueve roles, todos en Haiku 4.5, orquestados con LangGraph, y con una regla: quien escribe no aprueba. El editor repara dentro del bucle y el juez mide fuera sin tocar el texto. En cinco puntos decide un humano.

### Slide 8 · Los validadores son nodos del grafo: ningún agente puede saltárselos (0:30)

**Qué decir.**
> Esta es la decisión de la que cuelga todo: los validadores son nodos del grafo, no herramientas que un agente decide llamar. Lo que un modelo puede olvidarse de invocar no es una comprobación. Cada capítulo pasa primero lo gratis, que es longitud, nombres y palabras prohibidas; solo si sale limpio se paga el extractor y Lean. Si algo falla, el editor emite un parche, con dos reintentos como máximo y un contador compartido. Y el checkpoint va en la misma transacción que el capítulo: si el proceso muere, se reanuda sin perder ni duplicar nada.

### Slide 9 · El writer no busca su contexto: lo recibe, acotado a 12.000 tokens (0:30)

**Qué decir.**
> El writer no busca su contexto: lo recibe. Un módulo de código sin nada de inteligente le arma un paquete de siete bloques, con doce mil tokens de techo: el encargo, los personajes que salen, lo que ya ha pasado, el capítulo anterior entero, los hechos históricos con su firmeza, las reglas y la personalización del capítulo. Todo sale de la story bible, un SQLite por novela en el que cada hecho sabe qué capítulos lo usan. Y los cien mil tokens concurrentes no se vigilan: se garantizan por construcción. El peor caso son cuarenta y cinco mil.

### Slide 10 · Tres decisiones explican el resto del sistema (0:20)

**Qué decir.**
> Tres decisiones lo explican todo. Validar no es opcional. El estado vive en un solo sitio. Y nada se sobrescribe: una versión es una lista de capítulos inmutables, así que conservar la anterior sale gratis. Para trabajar con Claude Code hay un CLAUDE.md, una skill de continuidad y dos hooks, uno que valida el capítulo editado y otro de policy, que usan el mismo código que el grafo.

**Si vas justo**, di solo las tres decisiones y pasa.

---

## Capítulo V · Validación, evaluación y observabilidad (2:00)

### Slide 11 · Cuatro familias de validadores, cada una en su punto del harness (0:25)

**Qué decir.**
> Hay cuatro familias de validadores. Once programáticos y deterministas, del schema al render visual con Playwright. Semánticos: el juez, con ocho criterios y justificación, y una revisión humana con la misma rúbrica; en la novela de Barcelona, la persona dio 8,75 y el juez 7,88. Lean 4 para la cronología de la historia. Y TLA+ para el propio harness. Cada uno en su punto del grafo, y todos mandan su resultado a Langfuse.

### Slide 12 · Diez novelas publicadas: lo que un validador cazó se reparó antes de publicar, y dos fallos se le escaparon (0:30)

**Qué decir.**
> Estas son las evals de verdad: cinco briefs de diez capítulos, dos adversariales y tres novelas de referencia, todas publicadas. Cada cruz convertida en check es un rechazo de un validador que el editor reparó antes de publicar: los sesenta capítulos pasan los deterministas y Lean. Y hay dos filas que no escondemos. En la de Cádiz se colaron en dos capítulos las etiquetas de privacidad de la organización, y en el adversarial temporal Lean no vio a Gravina vivo en 1808. Cada novela cuesta entre dos y tres dólares y medio, y el juez da una media de 7,49.

### Slide 13 · La lectura humana destapó un juez demasiado generoso; el tuning lo corrigió (0:20)

**Qué decir.**
> La mejora más importante la encontró una lectura humana. En la novela de Sevilla, el juez puso un ocho en continuidad mientras la firma de un mapa se contradecía en cinco capítulos. Cambiamos dos cosas: el juez enumera ahora las contradicciones antes de puntuar, y Python le topa la nota. En Cádiz 1812 encontró tres y la continuidad bajó a cuatro. Además, el writer recibe lo que ya pasó y las palabras ya gastadas.

### Slide 14 · Lean vio una protagonista que existía antes de nacer; ni el juez ni los validadores de texto lo vieron (0:20)

**Qué decir.**
> Este es el caso que pide el enunciado. En la novela de Madrid 1919, la homenajeada nace en 1967 y la novela la pone en 1917. Ningún validador de texto lo ve y el juez le dio un 7. Lean compara fechas: «nadie antes de nacer» falla en nueve escenas y veintiséis eventos. Hoy eso bloquea la publicación. Y el límite, que encontró nuestro propio adversarial: Lean es tan fiable como sus fechas. El arquitecto movió la muerte de Gravina a 1809 sin fuente, y Lean validó contra ella.

### Slide 15 · TLC agota todos los estados del harness sin violaciones, después de cazar tres errores de diseño (0:15)

**Qué decir.**
> Lean verifica la historia; TLA+ verifica el sistema. TLC recorre todos los estados del modelo, doce mil seiscientos en interactivo y cuatro mil cuatrocientos en batch, sin violaciones. Antes cazó tres errores de diseño: un «rehacer» que duplicaba capítulos, un juez que podía rechazar para siempre y una equidad que no bastaba.

### Slide 16 · Cada novela es una sesión en Langfuse: tokens, coste y latencia por llamada (0:10)

**Qué decir.**
> Todo se ve en Langfuse: un span por rol con sus herramientas y los scores de todos los validadores. Esta novela costó 3,62 dólares, exactamente lo que registra el arnés.

---

## Capítulo VI · Guardrails (0:30)

### Slide 17 · Lo que no debe aparecer no aparece y queda registrado, incluso cuando el guardrail se pasa de estricto (0:30)

**Qué decir.**
> ¿Recordáis «tesoro»? El writer escribió «no el oro, sino el tesoro que permanecería». El guardrail lo cazó, el capítulo volvió al editor y el siguiente intento salió sin la palabra. Pero el red-team encontró lo contrario: de cuatro rechazos reales, tres eran falsos positivos. «Respiratorio» contiene la raíz de «pirata», y eso detuvo una novela. Es el siguiente arreglo. Una carta con cinco órdenes inyectadas no metió ni una en el texto. Y el único rol con internet nunca recibe los datos del homenajeado.

---

## Capítulo VII · Presupuesto y coste (1:00)

### Slide 18 · Cada novela cuesta 13,90 € y se vende a 59 €: margen del 71,5 % (0:30)

**Qué decir.**
> Vamos a los números. Una novela de diez capítulos gasta en tokens una media de tres dólares, medida fase a fase: unos 2,77 euros. Las cinco novelas publicadas de diez capítulos lo confirman. Con las revisiones, la infraestructura, el mantenimiento y veinte minutos de supervisión humana, el coste es de 13,90 euros. La vendemos a 59, con tres revisiones incluidas: 34,86 euros de margen, un 71,5 %. Y ojo: lo caro no son los tokens, es la supervisión de los gates.

### Slide 19 · El margen aguanta una subida del 50 % en tokens; lo que hay que proteger son las revisiones (0:30)

**Qué decir.**
> El desarrollo lo estimamos en 420 horas a 65 euros: 27.300 euros entre diseño, desarrollo, validación y despliegue. Con 590 euros de fijos al mes, el margen mensual es de unos 1.250 euros con 50 novelas, 10.500 con 300 y 36.000 con mil. La sensibilidad dice dónde está el riesgo: si los tokens suben un 50 %, perdemos un 5 %; si un cliente pide seis revisiones, un 34 %. Por eso, a partir de la cuarta revisión se cobran 4,90 euros y el margen se recupera.

---

## Capítulo VIII · Demo, versión 2 y cierre (1:30)

### Slide 20 · El lector cambia un dato; solo se reescriben los capítulos que lo usan (0:40)

**Qué decir.**
> En la novela del aguador, el lector no quiere que un personaje se llame Cayetano. Lo selecciona en el capítulo 1 y escribe «se llama Amancio». El sistema busca en la story bible y enseña al autor los candidatos con su coste: habría que regenerar los capítulos 1, 2, 4 y 5 y revisar el 3. El autor confirma la fila y el nombre nuevo; ningún modelo interpreta la petición. Se reescriben esos capítulos, y aquí también el 3, porque su primer intento se pasó de longitud. Lean y el render dan el visto bueno, se publica la versión 3 y las anteriores quedan intactas. Costó 94 céntimos de dólar. En una novela de diez capítulos, un cambio parecido reescribió tres y reutilizó siete.

**Y en directo.** La rama `fase-6-regeneracion` tiene un gate de Regeneración pendiente. Si hay tiempo, apruébalo delante del tribunal y enseña cómo arranca. El resultado tarda minutos, así que remite a esta slide.

### Slide 21 · De la prueba de concepto a la versión 2: críticos internos en lugar de gates humanos (0:30)

**Qué decir.**
> Esto es la versión 1, una prueba de concepto. Hoy un humano aprueba cinco gates, y eso es lo que más cuesta: veinte minutos por novela. En la versión 2, esos gates los sustituyen críticos internos que revisan con más dureza la investigación histórica, el canon y la escaleta, y cada capítulo, con modelos mejores donde hace falta. Hay dos escenarios. Con Sonnet 5 en los roles clave, los tokens suben a 7,7 euros, pero la supervisión baja a cinco minutos por muestreo, y la novela cuesta prácticamente lo mismo, 14 euros, con un 71 % de margen. Con Opus 5 en el arquitecto, los críticos y el juez, cuesta 19,5 euros y el margen es del 60 %. Desarrollarlo son 210 horas, unos 14.000 euros.

**Si preguntan por qué no se hizo ya así.** Porque primero había que medir: sin los gates humanos no habríamos visto RT-07, RT-08 ni RT-09, y un crítico solo sustituye a un gate cuando las evals demuestran que caza lo mismo.

### Slide 22 · Lo que queda por hacer antes de vender la primera novela (0:20)

**Qué decir.**
> Los riesgos, con franqueza. Hoy el modelo corre sobre una sesión de Claude Code, y producción necesita una API propia. El juez es el mismo modelo que escribe, y lo calibramos con revisión humana. Y las fechas de los personajes históricos que no están en el corpus las pone el arquitecto. Lo siguiente, por orden: un piloto de cincuenta novelas con Relicario, sacar esas fechas del corpus, que es un arreglo determinista, y después la versión 2 con sus críticos.

### Slide 23 · Contraportada

**Qué decir.**
> Gracias. Quedamos a vuestra disposición para las preguntas técnicas.

---

## Preparación para los cinco minutos de preguntas

Son respuestas cortas a lo más probable. Cada una apunta al anexo o al documento donde está el detalle, por si hay que abrirlo.

**¿Por qué multiagente y no un solo agente?**
Porque la separación es lo que da valor a las métricas. Si el mismo agente escribe y se puntúa, optimiza la nota que produce. Por eso editor y juez son dos agentes, e investigador y verificador también. → `docs/architecture.md` §5, anexo A1.

**¿Por qué todo en Haiku?**
Porque es barato y el harness compensa lo que le falta: el contexto se entrega acotado, los validadores son código y el juez se calibra con revisión humana. Subir de modelo un rol es una línea de configuración. → §5 «Sobre el juez en Haiku», anexo A8.

**¿Por qué no quitáis ya los gates humanos?**
Porque en una prueba de concepto el humano es el instrumento de medida: gracias a él vimos los falsos positivos del guardrail, las etiquetas de privacidad y las fechas inventadas. Un crítico interno sustituye a un gate cuando las evals demuestran que caza lo mismo que el humano. Esa es la versión 2 (slide 21, anexo A8).

**¿Por qué no usáis ya un modelo mayor o más agentes revisores?**
Porque primero va lo determinista. El fallo del adversarial temporal se arregla exigiendo que las fechas salgan del corpus, sin gastar un token más. Un revisor de escaleta con un modelo mayor es el paso siguiente, para lo que no se puede calcular. El coste no es el freno: triplicar los tokens baja el margen del 71 % al 57 % (anexo A8).

**¿Cómo garantizáis los 100.000 tokens concurrentes si no se pueden medir en vivo?**
Por construcción. Cada rol tiene un techo declarado, el grafo es secuencial y el peor caso es el investigador, con 45.000. Un hook `PreToolUse` deniega la cuarta búsqueda y un hook `PostToolUse` recorta cada página a 10.000 tokens. → §12, anexo A1.

**¿Qué pasa si el proceso muere en el capítulo 6?**
El checkpoint del grafo y el capítulo aprobado se escriben en la misma transacción SQLite. `storymaker continuar` reanuda desde el capítulo 6. TLC lo comprueba con `ResumeIsExactlyOnce`, y en la novela de Barcelona 1888 pasó dos veces sin perder capítulos.

**¿La especificación TLA+ corresponde de verdad al código?**
Los nodos de LangGraph y las acciones TLA+ se llaman igual, y un test compara las aristas declaradas del grafo con la definición `Aristas`, que es la que explora TLC. → README raíz, anexo A2.

**¿Por qué `PublishVersion` no comprueba que todo esté validado?**
Porque con esa guarda `NoPublishUnvalidated` sería una tautología. Sin ella, TLC busca si hay algún camino que publique algo sin validar. → `formal/tla/README.md`.

**¿El brief adversarial temporal lo cazó Lean?**
No, y lo contamos. El corpus no tenía la muerte de Gravina, así que el arquitecto le puso una fecha inventada, 1809, que hacía encajar el encargo, y Lean comprobó la coherencia contra ella. Es RT-09 en `docs/red-team.md`, con sus mitigaciones.

**¿Qué es el texto de privacidad que apareció en la novela de Cádiz?**
Es RT-08. Los roles corren con el Agent SDK, que hereda la sesión de Claude Code y con ella las instrucciones de la organización, que anonimizan nombres. El escritor tomó a dos personajes inventados por personas reales. Lo encontró la inspección con el MCP de Playwright (`docs/inspeccion-visual.md`). Se arregla corriendo el producto con API propia y con un validador que bloquee esas etiquetas.

**¿Y si no está instalado Lean?**
El arnés evalúa los mismos cuatro invariantes en Python. En las novelas publicadas, Lean y Python dieron el mismo veredicto.

**¿Qué pasa con una inyección en el texto pegado?**
El texto va a cuarentena y solo salen filas tipadas. En la eval de Córdoba, ninguna de las cinco órdenes llegó al texto. La debilidad conocida es el tipo `anécdota`, que es prosa libre: está en RT-01, abierta. → anexo A7.

**¿El coste es real o inventado?**
Los tokens son medidos: `total_cost_usd` del Agent SDK, sumado por fase. En la novela de Cádiz, el arnés y Langfuse dan 3,621496 $. Es una estimación del SDK, no una factura, y lo decimos. Las revisiones salen de las demos reales. La infraestructura, la supervisión y la tarifa son estimaciones justificadas.

**¿Y si el cliente no contesta un gate?**
La novela se queda parada sin coste, y un *timeout* la aparca. No hay auto-aprobación.

---

## Antes de presentar

- Rellena `[TU NOMBRE]`, `[TU EMAIL]` y `[FECHA DE LA PRESENTACIÓN]` en `presentacion/deck/datos.json` y reconstruye el deck, o cámbialos directamente en las slides 1 y 22 del PPTX.
- Si vas a aprobar en directo el gate de `fase-6-regeneracion`, comprueba antes que el servidor del 8765 está levantado.
- Ensaya los nueve minutos con reloj.
