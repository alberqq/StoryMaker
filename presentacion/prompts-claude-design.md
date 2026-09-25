# Prompts para Claude Design — deck de StoryMaker

> **Nota.** El deck final no se genera en Claude Design: se construye en `presentacion/deck/` con la misma maqueta que los anexos, y la marca pasó de «Cronista Labs» a «Qapítulo». Este fichero queda como especificación de contenido de cada slide.

Prompts listos para pegar en Claude Design, uno por slide, precedidos de un prompt de sistema que fija la identidad visual. Todas las cifras salen del repositorio: las bases SQLite de las tres novelas publicadas en `backend/proyectos/` (tabla `fase_run`, `score`, `incidencia`, `capitulo_version`), `docs/iteraciones.md`, `formal/tla/README.md` y `docs/architecture.md`. Lo que no está medido va marcado como **estimación** o como **[PENDIENTE]**.

Cómo usarlo:

1. Pega el **Prompt 0** al abrir el proyecto. Fija la marca, la rejilla y las reglas del deck.
2. Pega los prompts de slide en orden, uno por mensaje. Cada uno es autosuficiente.
3. Sustituye los marcadores entre corchetes (`[NOMBRE_ESTUDIANTE]`, `[FECHA]`, las capturas) antes de exportar.
4. Exporta a **PPTX** (formato editable) y a **PDF**, y guarda ambos en `presentacion/`. Los anexos, además, como PDF sueltos con nombre descriptivo (lista al final).

---

## Prompt 0 — Sistema de marca y reglas del deck

```text
Vas a diseñar un deck de 16:9 en castellano, con los términos técnicos en inglés (harness, planner, writer, gate, checkpoint, trace, score, prompt, hook, skill). Es una propuesta técnico-comercial formal a un cliente, de 10 minutos, más anexos al final.

EMPRESA PRESENTADORA (ficticia): "Cronista Labs" — estudio de ingeniería de sistemas agénticos. Lema: "Historias que se pueden verificar".
CLIENTE (ficticio): "Relicario" — e-commerce español de regalos personalizados (bodas, aniversarios, jubilaciones, cumpleaños redondos).
PRODUCTO QUE SE PROPONE: "Novela Relicario", novelas históricas personalizadas para regalar, generadas por el sistema StoryMaker.

LOGOTIPO de Cronista Labs: un plumín de escritura visto de frente cuya ranura central forma un check (✓), dentro de un círculo fino. Versión horizontal: símbolo + "Cronista Labs" en Fraunces SemiBold. Versión monocroma para fondos oscuros. Colócalo pequeño abajo a la izquierda en todas las slides salvo la portada y la contraportada, donde va grande.
Logo del cliente Relicario (solo en portada y contraportada, más pequeño que el nuestro): un medallón ovalado con una "R" serif dentro, en Oro viejo.

PALETA (úsala siempre, sin colores fuera de ella):
- Tinta #1C2433 — fondos oscuros, títulos sobre claro
- Pergamino #F5EFE3 — fondo por defecto
- Lacre #B23A2B — acento, alertas, "falla", errores detectados
- Oro viejo #C9A34E — resaltados, cifras clave, línea de tiempo
- Salvia #5E8C6A — "pasa", verde de validación
- Piedra #7D7869 — texto secundario, pies, ejes
Contraste mínimo AA. Lacre y Salvia solo con significado (falla / pasa), nunca decorativos.

TIPOGRAFÍA (Google Fonts):
- Títulos: Fraunces (SemiBold 600, óptico grande), 40–48 pt
- Texto: Inter (Regular 400 / Medium 500), 16–22 pt; nunca por debajo de 14 pt
- Cifras de tabla, nombres de nodos, código: JetBrains Mono 500

RECURSO NARRATIVO: el deck se lee como un libro. Cada bloque es un "Capítulo" con numeral romano en versalitas sobre el título (p. ej. "CAPÍTULO III · ARQUITECTURA"). En el pie de cada slide, una línea fina de Oro viejo a lo ancho con marcas pequeñas, como una línea de tiempo, y el número de slide a la derecha en JetBrains Mono ("03 / 20").

REJILLA: márgenes de 64 px, 12 columnas, mucho aire. Un mensaje por slide: el título es una frase que afirma algo (no un rótulo). Máximo 5 bullets, máximo 12 palabras por bullet. Diagramas planos, trazo de 2 px, esquinas de 8 px, sin sombras, sin degradados, sin clip-art, sin fotos de stock. Iconos lineales finos coherentes entre sí.

ESTADOS VISUALES reutilizables:
- Chip "PASA": fondo Salvia 15 %, texto Salvia, ✓
- Chip "FALLA → REPARADO": fondo Lacre 12 %, texto Lacre, flecha a Salvia
- Chip "AVISO": fondo Oro viejo 18 %, texto Tinta
- Chip "PENDIENTE": borde discontinuo Piedra

Incluye notas del orador vacías en cada slide (las rellenaré yo). No inventes cifras: usa solo las que te doy en cada prompt. Si falta una imagen, deja un marco con borde discontinuo y el texto del marcador que te indique.
```

---

## Capítulo I · Portada y contexto (0:30)

### Slide 1 — Portada

```text
Slide 1, PORTADA (obligatoria). Fondo Tinta a sangre. Composición de cubierta de libro de tapa dura: un rectángulo vertical centrado-izquierda con filete dorado (Oro viejo) de 1 px a 12 px del borde, como una sobrecubierta.

Dentro, de arriba abajo:
- Logo grande de Cronista Labs en versión clara.
- Título en Fraunces 56 pt, Pergamino: "Novela Relicario"
- Subtítulo en Inter 22 pt, Oro viejo: "Novelas históricas personalizadas, verificadas antes de regalarse"
- Filete dorado corto.
- Tres líneas en Inter 16 pt, Pergamino al 80 %:
  "Propuesta técnico-comercial para Relicario"
  "[FECHA]"
  "Presenta: [NOMBRE_ESTUDIANTE] · Cronista Labs"

A la derecha, fuera de la "cubierta", el logo de Relicario pequeño con el texto "Preparado para Relicario" en Piedra. Sin pie de línea de tiempo en esta slide.
```

### Slide 2 — La propuesta en una frase

```text
Slide 2. CAPÍTULO I · EL ENCARGO. Fondo Pergamino.
Título: "Convertimos a la persona homenajeada en protagonista de un momento histórico real"

Debajo, una sola ilustración tipográfica en tres columnas unidas por flechas finas de Oro viejo:
1. "Lo que aporta el comprador" — nombre, época, recuerdos, palabras a evitar
2. "Lo que hace el sistema" — investiga la época, escribe 10 capítulos, verifica cada uno
3. "Lo que recibe el homenajeado" — una novela web + PDF con su dedicatoria

Franja inferior con tres ejemplos en cursiva Fraunces, cada uno con un pequeño año en JetBrains Mono Oro viejo:
"1858 · un aguador en el Madrid que estrena el Canal de Isabel II"
"1812 · una cajista de imprenta en el Cádiz de la Constitución"
"1919 · una telegrafista en la inauguración del Metro de Madrid"
Pie: "Tres novelas reales generadas por el sistema, ya publicadas."
```

---

## Capítulo II · Problema y cliente (1:00)

### Slide 3 — Quién compra y para qué

```text
Slide 3. CAPÍTULO II · EL PROBLEMA. Fondo Pergamino.
Título: "Relicario vende emoción, y el regalo personalizado de hoy se queda en la superficie"

Mitad izquierda — "Quién compra": tres tarjetas de persona sin foto (icono lineal + texto):
- "Hijos que buscan regalo de jubilación para su padre o su madre"
- "Parejas en un aniversario o una boda"
- "Amigos y familia en un cumpleaños redondo (50, 60, 70)"

Mitad derecha — "Qué esperan": tres frases cortas con ✓ Oro viejo:
- "Que la persona se reconozca: su nombre, sus manías, sus recuerdos"
- "Que se lea de un tirón, sin tropiezos"
- "Que sea único y no una plantilla con el nombre cambiado"

Franja inferior en Tinta con texto Pergamino: "Dos exigencias igual de importantes: personalización y calidad narrativa mínima."
```

### Slide 4 — Por qué las alternativas no funcionan

```text
Slide 4. CAPÍTULO II · EL PROBLEMA. Fondo Pergamino.
Título: "Ninguna alternativa actual da a la vez personalización, calidad y precio"

Tabla comparativa de 4 filas × 4 columnas (cabecera en Tinta, texto Pergamino; celdas con chips):
Columnas: "Personalización real" | "Calidad narrativa" | "Precio" | "Plazo"
Filas:
1. "Libro de plantilla con el nombre insertado" — AVISO "Solo el nombre" | PASA "Correcta, pero genérica" | PASA "30–40 €" | PASA "Días"
2. "Escritor por encargo" — PASA "Total" | PASA "Alta" | FALLA "Cientos o miles de €" | FALLA "Semanas"
3. "Pedírselo a un chatbot generalista" — PASA "Alta" | FALLA "Contradicciones, finales abruptos, prosa repetitiva" | PASA "Casi gratis" | PASA "Minutos"
4. Fila destacada con borde Oro viejo: "Novela Relicario" — PASA "Recuerdos + época documentada" | PASA "Validada capítulo a capítulo" | PASA "59 €" | PASA "Horas"

Nota al pie en Piedra: "Un modelo generalista escribe bien una escena; falla en la coherencia de diez capítulos. Ese es el hueco que cubre el harness."
```

---

## Capítulo III · Configuración y lectura (1:00)

### Slide 5 — Cómo se configura una novela

```text
Slide 5. CAPÍTULO III · CONFIGURACIÓN. Fondo Pergamino.
Título: "Una entrevista corta produce un brief validado con schema"

Diagrama horizontal de izquierda a derecha, cajas redondeadas con borde Tinta:
[Comprador: premisa libre + texto pegado] → [Entrevistador (agente): pregunta solo lo que falta] → [Brief Pydantic validado] → [Gate de Intake: el autor aprueba]

Debajo del diagrama, cuatro recuadros pequeños en fila, cada uno con icono lineal:
- "Datos que faltan" — "El entrevistador pregunta por los campos vacíos"
- "Contradicciones" — "4 detectores deterministas: edad vs. época, nacimiento vs. evento, tono vs. época, dato vs. palabra prohibida"
- "Texto libre = no confiable" — "Va a cuarentena; solo salen filas tipadas (persona, lugar, fecha, objeto, anécdota)"
- "Lo que no debe aparecer" — "Palabras prohibidas por novela y por destinatario"

Esquina inferior derecha: un fragmento de YAML en JetBrains Mono sobre fondo Tinta, 8 líneas:
homenajeado:
  rol_epoca: armador de navío mercante
  ocasion: jubilación tras cuarenta años en el puerto
mundo:
  periodo: { inicio: 1803, fin: 1806 }
  evento_ancla: la batalla de Trafalgar
obra:
  palabras_prohibidas: { novela: [pirata, tesoro], destinatario: [naufragio] }
```

### Slide 6 — Cómo se lee y cómo se corrige

```text
Slide 6. CAPÍTULO III · LECTURA. Fondo Pergamino.
Título: "Se lee en web o en PDF, y un cambio se pide seleccionando el texto"

Composición: a la izquierda un mockup plano de navegador (marco fino Tinta, sin sombras) con la captura capturas/pepa-v1-personajes.png (ficha de personajes con enlaces a capítulos). A la derecha, superpuesto parcialmente, un mockup de página PDF con capturas/pepa-v1-impresion.png (portada impresa con dedicatoria). Abajo a la derecha, pequeña y con borde Oro viejo, capturas/pepa-v1-pedir-cambio.png (fragmento seleccionado + petición). Si cabe, una miniatura de capturas/pepa-v1-indice.png junto a la etiqueta 1.

Cuatro etiquetas numeradas con líneas guía hacia las capturas:
1. "Índice navegable, con marca en los capítulos que cambiaron"
2. "Ficha de personajes y lugares desde la story bible, enlazada a cada capítulo"
3. "Portada con dedicatoria personalizada"
4. "Selecciona un fragmento → 'pedir cambio' → gate de Regeneración"

Franja inferior: "Web y PDF salen de la misma ruta de lectura: Playwright imprime la web. Toda versión anterior se conserva."
```

---

## Capítulo IV · Arquitectura del harness (2:00)

### Slide 7 — Seis fases, nueve roles, cinco gates

```text
Slide 7. CAPÍTULO IV · ARQUITECTURA. Fondo Pergamino.
Título: "Seis fases, nueve roles especializados y un humano en cinco puntos de control"

Diagrama principal: una banda horizontal de 6 bloques conectados (flecha fina Tinta), cada bloque con nombre de fase arriba en Fraunces y roles debajo en Inter:
1. Intake — entrevistador · extractor de intake
2. Investigation — investigador (única salida a internet) · verificador
3. Plotting (planner) — arquitecto → canon + escaleta · sello del corpus
4. Writing — escritor (writer) · editor (editor/critic) · extractor de capítulo
5. Publication — juez (LLM-as-judge)
6. Regeneration — escritor · editor

Encima de las fases 1, 2, 3, 4 y 6, un pequeño icono de "mano/sello" en Oro viejo con la etiqueta "gate humano". Sobre Publication no hay gate.

Debajo, tres chips a lo ancho:
- "Orquestación: LangGraph con estado explícito"
- "Agentes: Claude Agent SDK, todos en Haiku 4.5"
- "Estado: un fichero SQLite por novela"

Pie: "Planner = arquitecto · Writer = escritor · Editor/critic = editor + juez, separados: quien escribe no aprueba."
```

### Slide 8 — El bucle del capítulo

```text
Slide 8. CAPÍTULO IV · ARQUITECTURA. Fondo Pergamino.
Título: "Los validadores son nodos del grafo: ningún agente puede saltárselos"

Diagrama de estados circular, nodos en JetBrains Mono dentro de cápsulas:
WriteChapter → Validate (pasada determinista, coste cero) → Extract (pasada del extractor + Lean) → ApproveChapter → Checkpoint → (siguiente capítulo) WriteChapter
Desde Validate y desde Extract, flecha en Lacre a "Repair" (editor emite parche) que vuelve a Validate. Etiqueta sobre esa flecha: "máx. 2 reintentos, contador compartido".
Desde Validate y Extract, flecha discontinua a "Fail" con etiqueta "reintentos agotados → para e informa".
Checkpoint con icono de disco y la etiqueta "misma transacción que el capítulo aprobado".

A la derecha, una columna de tres afirmaciones con icono:
- "Las aristas leen booleanos calculados en Python, no la opinión de un modelo"
- "Primero lo gratis (longitud, nombres, prohibidas), luego la llamada"
- "Si el proceso muere, se reanuda desde el último capítulo aprobado"
```

### Slide 9 — Contexto y story bible

```text
Slide 9. CAPÍTULO IV · ARQUITECTURA. Fondo Pergamino.
Título: "El writer no busca su contexto: lo recibe, acotado a 12.000 tokens"

Izquierda: una barra vertical apilada (como un lomo de libro) con 7 segmentos proporcionales, cada uno con su etiqueta y su techo en JetBrains Mono:
1 Encargo del capítulo — 800
2 Canon relevante — 2.500
3 Continuidad + lo que ya pasó — 2.500
4 Memoria: capítulo N−1 íntegro + resúmenes relevantes — 3.000
5 Anclajes históricos con su firmeza — 1.500
6 Reglas, estilo, prohibidas, repeticiones ya gastadas — 1.200
7 Personalización que toca este capítulo — 500
Total: 12.000

Derecha: un esquema mínimo de la story bible en SQLite con 5 cajas enlazadas: "intake_dato" → "uso_hecho / intake_uso_dato (qué capítulo usa qué dato)" ; "mundo_hecho (corpus sellado)" ; "canon_personaje" ; "cronologia_evento (alimenta Lean)" ; "capitulo_version + version_novela (inmutables)".

Franja inferior en Tinta: "Límite de 100.000 tokens concurrentes garantizado por construcción: grafo secuencial, peor caso = 45.000 (investigador)."
```

### Slide 10 — Tools, hooks, skill y por qué este diseño

```text
Slide 10. CAPÍTULO IV · ARQUITECTURA. Fondo Pergamino.
Título: "Tres decisiones explican el resto del sistema"

Tres columnas iguales, cada una con un número grande en Fraunces Oro viejo:
1. "Validar no es opcional" — "Validadores como nodos; tools con schema Pydantic; toda salida de rol pasa schema_guard."
2. "El estado vive en un solo sitio" — "Un SQLite por novela: checkpoint y capítulo en la misma transacción. Ramificar = copiar el fichero."
3. "Nada se sobrescribe" — "Capítulos inmutables + manifiesto por versión: la versión anterior se conserva por estructura."

Debajo, una fila de 4 chips técnicos:
- "CLAUDE.md + AGENTS.md: instrucciones del repo"
- "Skill continuity-check"
- "Hook PostToolUse: valida el capítulo editado"
- "Hook PreToolUse: policy de palabras prohibidas"
Y un quinto chip: "Retries con límite: 2 por capítulo · 5 huecos por Plotting · 2 rechazos del juez".
```

---

## Capítulo V · Validación, evaluación y observabilidad (2:00)

### Slide 11 — Cuatro tipos de validadores y dónde actúan

```text
Slide 11. CAPÍTULO V · VALIDACIÓN. Fondo Pergamino.
Título: "Cuatro familias de validadores, cada una en su punto del harness"

Matriz: filas = familias, columnas = punto de ejecución (Intake · Gate de Plotting · Post WriteChapter · Post Extract · Antes de publicar · Desarrollo). Marca con un punto Oro viejo dónde actúa cada validador y escribe su nombre en JetBrains Mono.

Filas:
- "Programáticos (11)": schema_guard (todos los roles), nombres_exactos, longitud_capitulo, guardrail_prohibidas, anacronismo_fechado, anclaje_valido (post WriteChapter); cobertura_anclada, arco_anclado (gate de Plotting); cobertura_capitulo (post Extract, aviso); cobertura_personalizacion (gate de Writing); render_visual con Playwright (antes de publicar)
- "Semánticos": juez_rubrica, 8 criterios 1–10 con justificación (continuidad, arco, coherencia de personajes, ritmo, tono, prosa, naturalidad de la personalización, autenticidad de época) (antes de publicar); respaldo_fuente, ejecucion_escaleta, arco_ejecutado (avisan); revisión humana con la misma rúbrica (fuera de línea)
- "Formal de la historia — Lean 4": 4 invariantes de cronología en gate de Plotting, post Extract y antes de publicar
- "Formal del sistema — TLA+": TLC en desarrollo, no en cada novela

Nota lateral: "Todos envían su resultado a Langfuse como score."
```

### Slide 12 — Resultados por brief

```text
Slide 12. CAPÍTULO V · EVALUACIÓN. Fondo Pergamino.
Título: "Tres novelas reales publicadas: todo capítulo que falló un validador se reparó antes de publicar"

Tabla principal (JetBrains Mono para cifras, chips para estados). Filas = brief, columnas:
Brief | Capítulos | Versiones escritas | nombres_exactos | longitud | prohibidas | Lean (escaleta) | Juez (media / continuidad) | Tokens | Coste
1. "Madrid 1858 · aguador" | 5 | 7 | PASA | FALLA→REPARADO ×2 | FALLA→REPARADO ×1 | AVISO ×1 | 7,71 / 8 | 508 K | 1,93 $
2. "Madrid 1919 · telegrafista" | 5 | 9 | FALLA→REPARADO ×4 (1 capítulo agotó reintentos y se reabrió) | PASA | PASA | AVISO ×6 | 7,14 / 6 | 645 K | 2,39 $
3. "Cádiz 1812 · cajista" | 5 | 6 | PASA | FALLA→REPARADO ×1 | PASA | PASA | 6,29 / 4 | 512 K | 1,91 $
4. "Brief adversarial · injection en texto libre" | toda la fila con chip PENDIENTE y el texto "[PENDIENTE: ejecución real]"
5. "Brief de incoherencia temporal" | toda la fila con chip PENDIENTE y el texto "[PENDIENTE: ejecución real]"

Debajo, en pequeño y Piedra: "Modelo: Haiku 4.5 en los 9 roles. Novelas de 5 capítulos × ~1.000 palabras. Umbral de publicación del juez: 6,0. Fuente: tablas fase_run, score e incidencia de cada novela."
A la derecha, un recuadro Oro viejo con una cifra grande: "5 de 5" y el texto "capítulos con un fallo bloqueante, reparados antes de publicar".
```

### Slide 13 — Tuning: antes y después

```text
Slide 13. CAPÍTULO V · EVALUACIÓN. Fondo Pergamino.
Título: "La lectura humana destapó un juez demasiado generoso; el tuning lo corrigió"

Dos columnas "ANTES" y "DESPUÉS", separadas por una flecha grande Oro viejo.

ANTES (novela de Sevilla, 10 capítulos):
- Juez: 7,4 de media y 8 en continuidad
- Lectura humana: la firma del mapa se contradice en 5 capítulos; "precisión" aparece 63 veces; dos capítulos cierran con el mismo párrafo
- Causa: el writer solo veía el capítulo N−1; el juez no dependía de las contradicciones

DESPUÉS (It-26):
- El juez enumera las contradicciones antes de puntuar
- Python topa la continuidad: 10 − 2 × nº de contradicciones
- El writer recibe "lo que ya pasó" y las palabras ya gastadas

Debajo, un pequeño gráfico de barras horizontal (3 barras, Salvia/Oro/Lacre según valor) con la continuidad posterior: "Madrid 1858: 1 contradicción → 8" · "Madrid 1919: 1 contradicción → 6" · "Cádiz 1812: 3 contradicciones → 4".
Pie: "Segundo ajuste medido (It-25): el guardrail cazaba 'hereje' pero dejaba pasar 'herejía'; ahora busca la raíz dentro de cada palabra."
```

### Slide 14 — El fallo que solo vio Lean

```text
Slide 14. CAPÍTULO V · VALIDACIÓN FORMAL. Fondo Pergamino.
Título: "Lean vio una protagonista que existía antes de nacer; ni el juez ni los validadores de texto lo vieron"

Izquierda: una línea de tiempo horizontal Oro viejo de 1900 a 1970. Marcas en Lacre en 1900, 1917, 1917-12, 1918, 1918-12 y 1919 etiquetadas "escenas de la escaleta"; una marca en Tinta en 1967 etiquetada "nacimiento copiado del encargo". Una llave en Lacre abarcando las escenas: "I1 · nadie participa antes de nacer — 9 escenas de la escaleta y 26 eventos de la prosa".

Derecha: bloque de código en JetBrains Mono sobre Tinta:
theorem I1_NadieAntesDeNacer :
  ∀ e ∈ eventos, ∀ p ∈ e.participantes,
    p.nacimiento ≤ e.momento := by decide
-- lake exe verificar → exit 1

Debajo, tres líneas con chip:
- FALLA "nombres_exactos y el resto de deterministas: no miran fechas de vida"
- FALLA "juez (7,14): vio una edad incoherente, no el nacimiento imposible"
- PASA "Lean (lake build + verificar): exit 1, con los eventos culpables"
Pie: "Novela de Madrid 1919. Cuando se generó, la cronología solo avisaba en el gate de Plotting y la novela se publicó. Qué cambió: Lean corre ahora con el toolchain instalado y bloquea la publicación, y el canon usa una fecha de nacimiento de época para el personaje del homenajeado. Lean y su evaluación en Python coinciden en las tres novelas publicadas."
```

### Slide 15 — TLA+: el harness verificado

```text
Slide 15. CAPÍTULO V · VALIDACIÓN FORMAL. Fondo Pergamino.
Título: "TLC agota todos los estados del harness sin violaciones, después de cazar tres errores de diseño"

Izquierda: lista de propiedades con chip PASA, en JetBrains Mono:
- NoPublishUnvalidated — nunca se publica un capítulo sin validar
- ResumeIsExactlyOnce — reanudar no duplica ni pierde capítulos
- RetriesBounded — los reintentos nunca superan el límite
- CorpusSelladoNoSeToca — tras el sello, nadie escribe en el corpus
- PreviousVersionPreserved — la versión anterior se conserva
- Termina (liveness) — toda generación publica o para con error
Modelo: 5 capítulos · 2 reintentos · 1 caída · 1 reintento manual · 1 cambio del lector.
Cifras grandes en Oro viejo debajo: "12.650 estados (interactivo)" · "4.425 estados (batch)" · "0 violaciones".
Nota: "Control de vacuidad: con weak fairness en vez de strong, TLC viola Termina, así que la comprobación no es vacía."

Derecha: tres "fichas de contraejemplo" apiladas, borde Lacre:
1. "Rehacer el gate de Writing se trataba como pasada inicial → capítulos duplicados. Cambio: acción RehacerWriting."
2. "El juez podía rechazar para siempre → bucle infinito. Cambio: tope de 2 rechazos y arista a Fail."
3. "Weak fairness no bastaba: el autor podía rehacer eternamente. Cambio: strong fairness en la especificación."

Pie: "Los nodos de LangGraph y las acciones TLA+ se llaman igual; un test compara las aristas del StateGraph con la definición Aristas."
```

### Slide 16 — Una traza real en Langfuse

```text
Slide 16. CAPÍTULO V · OBSERVABILIDAD. Fondo Pergamino.
Título: "Cada novela es una sesión en Langfuse: tokens, coste y latencia por llamada"

Ocupa el 70 % del ancho con un marco plano: [CAPTURA LANGFUSE: sesión de una novela con los spans intake · investigation · plotting · capitulo_03 · escritor · intento_2 · judge, y la pestaña de scores]. Mientras no exista, usa capturas/pepa-v1-panel.png (panel de la novela con coste, tokens y minutos por fase) con la etiqueta "Panel de la novela · el mismo consumo que se envía a Langfuse".

A la derecha, cuatro etiquetas con líneas guía:
- "Una sesión por novela, entrevista y regeneraciones incluidas"
- "Un span por rol y por intento: capitulo_07 · escritor · intento_2"
- "Scores de todos los validadores, Lean incluido"
- "Versión del prompt en cada span"

Franja inferior: coste por fase medido en la novela de Cádiz 1812 (la del panel), como barra horizontal apilada con leyenda: Intake 0,05 $ · Investigation 0,20 $ · Plotting 0,71 $ · Writing 0,74 $ · Publication 0,20 $ = 1,91 $.
```

---

## Capítulo VI · Guardrails (0:30)

### Slide 17 — Guardrails

```text
Slide 17. CAPÍTULO VI · GUARDRAILS. Fondo Pergamino.
Título: "Lo que no debe aparecer no aparece, y queda registrado, incluso cuando el guardrail se pasa de estricto"

Izquierda (60 %): un caso real en tres pasos verticales, como un antes y un después de manuscrito:
Paso 1: fragmento «…no dejaría oro a sus herederos, sino el tesoro que permanecería eternamente…», con «tesoro» subrayado en Lacre y la etiqueta "Capítulo 2, intento 1 · guardrail_prohibidas · nivel novela"
Paso 2: "El capítulo vuelve al editor con la incidencia"
Paso 3: chip PASA "Intento siguiente sin el término"
Debajo, un recuadro con borde Lacre titulado "Lo que encontró el red-team (RT-07)": "De 4 rechazos reales, 1 era la palabra. Los otros 3 eran raíces dentro de otras palabras: «res·pirat·orio» por «pirata», «despid·iéndose» por «despido», «suspens·ión» por «suspenso». Uno detuvo una novela." Y una línea en Piedra: "Mitigación propuesta: que el aviso nombre la palabra que saltó y que la coincidencia por raíz avise en vez de bloquear."

Derecha (40 %), tres recuadros:
- "Datos personales": "El único rol con internet nunca recibe el nombre, la fecha ni los recuerdos del homenajeado: regla Semgrep + guarda de PII sobre cada prompt"
- "Injection": "Una carta con 5 órdenes inyectadas: 0 llegaron al texto. Al writer solo llegan filas tipadas"
- "Audit log": "Cada decisión de policy, de gate y cada edición humana, con actor, momento, antes y después"
Pie: "Niveles de la lista: global · novela · destinatario, guardados en SQLite. Normaliza mayúsculas, acentos, plurales y derivados."
```

---

## Capítulo VII · Presupuesto y coste (1:00)

### Slide 18 — Coste unitario, precio y margen

```text
Slide 18. CAPÍTULO VII · PROPUESTA ECONÓMICA. Fondo Pergamino. Aspecto de propuesta formal: tabla limpia, cifras en JetBrains Mono alineadas a la derecha.
Título: "Cada novela cuesta 14,87 € y se vende a 59 €: margen del 69,5 %"

Bloque izquierdo — "Coste unitario por novela (10 capítulos, 300 novelas/mes)":
| Tokens (Haiku 4.5) | 3,50 € |
| Revisiones del lector (1,5 de media × 0,70 €) | 1,05 € |
| Supervisión editorial de gates (20 min × 25 €/h) | 8,35 € |
| Infraestructura y mantenimiento (70 € + 520 € al mes ÷ 300) | 1,97 € |
| TOTAL | 14,87 € | (fila en Tinta con texto Pergamino)

Bloque derecho — "Precio y margen":
Cifra grande Oro viejo: "59 €" con subtítulo "PVP con IVA · 48,76 € sin IVA · 3 revisiones incluidas"
Cifra grande Salvia: "33,89 €" con subtítulo "margen por novela (69,5 %)"

Nota al pie en Piedra, dos líneas:
"Tokens medidos: 1,91–2,39 $ por novela de 5 capítulos (media 2,08 $), total_cost_usd del Agent SDK registrado por fase. Extrapolado a 10 capítulos × 1.200 palabras: ≈ 3,9 $ ≈ 3,50 € (1 $ ≈ 0,90 €). Revisión: 0,70 € estimados (2–4 capítulos reescritos + juez). El coste registrado coincide con el de la sesión en Langfuse (novela de prueba de 2 capítulos: 1,7172 $ en los dos)."
"El coste dominante no son los tokens: es la supervisión humana de los gates."
```

### Slide 19 — Proyecto, escenarios y sensibilidad

```text
Slide 19. CAPÍTULO VII · PROPUESTA ECONÓMICA. Fondo Pergamino. Tres bloques.
Título: "El margen aguanta una subida del 50 % en tokens; lo que hay que proteger son las revisiones"

Bloque 1 (arriba izquierda) — "Coste del proyecto de desarrollo" (tarifa 65 €/h):
| Diseño: arquitectura, specs, TLA+, Lean | 90 h |
| Desarrollo: harness, 9 roles, validadores, web | 220 h |
| Validación: evals, revisión humana, red-team, tuning | 70 h |
| Despliegue: API propia, infra, Langfuse, formación | 40 h |
| TOTAL | 420 h · 27.300 € |

Bloque 2 (arriba derecha) — "Escenarios de volumen (margen mensual)". Gráfico de barras verticales de 3 barras en Salvia, con la cifra encima y el % debajo:
- 50 novelas/mes: 1.203 € (49 %)
- 300 novelas/mes: 10.168 € (70 %)
- 1.000 novelas/mes: 35.140 € (72 %)
Leyenda: "Ingreso 48,76 €/novela · variable 12,90 €/novela · fijo 590 €/mes (720 € a 1.000/mes)". Línea discontinua en 590 € etiquetada "costes fijos".

Bloque 3 (abajo, a lo ancho) — "Sensibilidad (300 novelas/mes)". Gráfico tornado de dos barras sobre el margen base de 33,89 €:
- "Tokens +50 %": 31,61 € (−6,7 %) — barra corta en Oro viejo
- "6 revisiones por novela en vez de 1,5": 21,38 € (−37 %) — barra larga en Lacre
- Nota junto a la segunda: "Mitigación: desde la 4.ª revisión, 4,90 € cada una → margen vuelve a ≈ 33,5 €"
```

---

## Capítulo VIII · Demo y cierre (1:00)

### Slide 20 — Demo: un cambio del lector que se propaga

```text
Slide 20. CAPÍTULO VIII · DEMO. Fondo Tinta (slide oscura para marcar el cambio de ritmo), texto Pergamino.
Título: "El lector cambia un dato; solo se reescriben los capítulos que lo usan"

Flujo horizontal de 5 pasos con iconos claros, cada uno con un hueco para su dato real en JetBrains Mono Oro viejo debajo:
1. "Selecciona el fragmento y pide el cambio" — [CAMBIO_PEDIDO]
2. "Gate: el autor confirma fila y valor nuevo" — [FILA=VALOR]
3. "La story bible dice qué capítulos lo usan" — uso_hecho · continuidad · uso_hito
4. "Se regeneran esos; el resto pasa Python + Lean a coste cero" — [CAPS_REESCRITOS] reescritos · [CAPS_REUTILIZADOS] reutilizados
5. "Versión 2 publicada; la 1 se conserva" — Lean · render_visual

Debajo, dos bloques:
- Izquierda, marco grande para vídeo o captura: [VÍDEO/CAPTURA DEMO: índice web de la versión 2 con los capítulos cambiados marcados, y el historial con las versiones 1 y 2].
- Derecha, una mini-tabla de manifiestos en JetBrains Mono, columnas "v1" y "v2", una fila por capítulo: celdas de v2 en Lacre para los capítulos nuevos y en Salvia para los reutilizados.

Franja inferior con dos cifras grandes en Oro viejo: "[COSTE] la revisión" · "[DURACIÓN]".
```

### Slide 21 — Riesgos y siguientes pasos

```text
Slide 21. CAPÍTULO VIII · CIERRE. Fondo Pergamino.
Título: "Lo que queda por hacer antes de vender la primera novela"

Dos columnas.
"Riesgos" (icono de advertencia Lacre, 4 items):
- "Hoy el modelo se usa a través de una sesión de Claude Code: producción necesita API propia con límites de throughput"
- "El juez y el writer son el mismo modelo: sesgo; se compensa con revisión humana y el tope de continuidad"
- "Sin el toolchain de Lean instalado, la cronología se evalúa en Python: la instalación de producción debe llevar lake"
- "El coste de tokens es una estimación en cliente del SDK, no facturación"

"Siguientes pasos" (numerados en Oro viejo, 4 items):
1. "Piloto con 50 novelas reales de clientes de Relicario"
2. "Revisión humana con la rúbrica en cada lote, para calibrar al juez"
3. "Migrar a API propia y fijar SLA de 24 h por novela"
4. "Servidor MCP de solo lectura para atención al cliente"
```

### Slide 22 — Contraportada

```text
Slide 22, CONTRAPORTADA. Fondo Tinta a sangre, simétrica a la portada (misma sobrecubierta con filete dorado).
Centro: logo grande de Cronista Labs en claro y el lema "Historias que se pueden verificar" en Fraunces cursiva, Oro viejo.
Debajo, datos de contacto en Inter 16 pt, Pergamino al 80 %:
"[NOMBRE_ESTUDIANTE] · Cronista Labs"
"[EMAIL_DE_CONTACTO]"
"[URL_DEL_REPOSITORIO]"
Abajo, pequeño: "Gracias. Preguntas técnicas: 5 minutos." y el logo de Relicario en Piedra.
Sin línea de tiempo en el pie.
```

---

## Anexos (después de la contraportada)

Cada anexo lleva la cabecera "ANEXO A1…A8" en versalitas y el mismo sistema visual, con más densidad permitida (texto hasta 14 pt).

### A1 — Arquitectura detallada

```text
Anexo A1 "Arquitectura detallada del harness". Diagrama de topología a página completa: Humano (comprador/autor) → Interfaz web 127.0.0.1 → CLI → Orquestador LangGraph → SQLite (una novela = un fichero). Del orquestador salen: Ensamblador de paquetes (código, no agente), Validadores (Core Domain en Python puro) → Lean 4, los 9 agentes vía Agent SDK (entrevistador, extractor de intake, investigador, verificador, arquitecto, escritor, editor, extractor de capítulo, juez), Langfuse (trazas, scores, prompts), Salida (PDF + web). El investigador es el único con flecha a "Internet (WebSearch/WebFetch)". Telegram con flecha discontinua "solo avisa". Caja .claude/ (skills, hooks, .mcp.json con Playwright) unida a Validadores con la etiqueta "mismo Core Domain". Debajo, la tabla de techos de contexto por rol: entrevistador 8.000 · extractor intake 6.000 · investigador inicial 45.000 · micro 14.000 · dirigido 15.000 · verificador 12.000 · arquitecto 25.000 · escritor 20.000 · editor 20.000 · extractor capítulo 12.000 · juez 32.500.
```

### A2 — Máquina de estados y especificación TLA+ comentada

```text
Anexo A2 "Máquina de estados TLA+". Diagrama de estados completo: Configure → AwaitApproval (gate Intake; rehacer vuelve a Configure; abortar termina) → Research → VerifyCorpus → AwaitApproval2 → Plan ⇄ FillGap (máx. 5 huecos) → AwaitApproval3 → SealCorpus → WriteChapter → Validate → (Repair | Extract | Fail) ; Extract → (Repair | ApproveChapter | Fail) ; ApproveChapter → Checkpoint → (WriteChapter | AwaitApproval4) ; AwaitApproval4 → (Judge | RehacerWriting) ; Judge → (PublishVersion | AwaitApproval4 | Fail) ; PublishVersion → Idle → (RequestChange → Invalidate → RegenerateAffected → Validate | Branch). Al lado, el operador comentado en JetBrains Mono:
Mueve(de, a) == /\ pc = de /\ <<de, a>> \in Aristas /\ pc' = a
con la nota "Aristas gobierna el Next que explora TLC y el test de identidad la compara con el StateGraph". Cifras actuales: 12.650 estados (harness.cfg) y 4.425 (harness_batch.cfg), sin violaciones. Tabla de 3 contraejemplos (fecha 2026-09-23): ResumeIsExactlyOnce (35 estados, rehacer tras aprobar los 5 capítulos), Termina 1.ª (bucle Judge ↔ AwaitApproval4), Termina 2.ª (weak fairness insuficiente).
```

### A3 — Esquema SQLite

```text
Anexo A3 "Story bible en SQLite". Diagrama entidad-relación agrupado en 7 familias por color de borde: intake_* (brief, dato, texto_crudo, uso_dato) · mundo_* (hecho, fuente, entidad, sello) · canon_* (obra, personaje, arco, arco_hito, relacion, licencia, prohibida) · plan_* (capitulo, escena, beat, anclaje, hueco) · texto (capitulo_version, version_novela, version_capitulo, manifiesto, uso_hecho, uso_hito, continuidad, incidencia) · cronologia_* (evento, participante) · arnes_* (fase_run, gate, score, audit_log, checkpoints). Tres notas: "Nunca UPDATE sobre un capítulo: una versión es un manifiesto", "mundo_* es append-only hasta el sello y de solo lectura después", "uso_hecho es el índice de la regeneración".
```

### A4 — Tabla completa de validadores

```text
Anexo A4 "Validadores y punto de ejecución". Tabla de 3 columnas (Nombre en JetBrains Mono · Qué comprueba · Dónde corre · ¿Bloquea?): schema_guard · nombres_exactos · longitud_capitulo · guardrail_prohibidas · anacronismo_fechado · anclaje_valido · cobertura_anclada · cobertura_capitulo (aviso) · arco_anclado · cobertura_personalizacion · render_visual · juez_rubrica · respaldo_fuente (aviso) · ejecucion_escaleta (aviso) · arco_ejecutado (aviso) · revision_humana · Lean I1–I4 (gate de Plotting avisa; post Extract y publicación bloquean) · TLC (desarrollo). Los 4 invariantes de Lean al pie: I1 nadie antes de nacer · I2 nadie después de morir · I3 nadie en dos lugares el mismo día · I4 ningún objeto antes de existir.
```

### A5 — Resultados completos de las evals

```text
Anexo A5 "Resultados de evaluación". Tabla ampliada con una fila por novela real y columnas: capítulos · versiones escritas · incidencias por validador · juez por criterio (continuidad, arco, coherencia de personajes, ritmo, prosa, naturalidad de la personalización, autenticidad de época) · tokens in/out · coste · duración · gates rehechos.
Madrid 1858: 5 · 7 · longitud 2, prohibidas 1, arco_anclado 4 (Plotting), cronología 1 aviso · 8/7/8/7/8/8/8 = 7,71 · 309 K / 199 K · 1,93 $ · 73 min · 0
Madrid 1919: 5 · 9 · nombres_exactos 4, cronología 6 avisos, anclaje_resuelto 8 avisos · 6/7/7/7/7/8/8 = 7,14 · 411 K / 234 K · 2,39 $ · 56 min · 1 (Plotting)
Cádiz 1812: 5 · 6 · longitud 1, auto_similitud 1 aviso, 3 contradicciones del juez · 4/7/7/6/8/6/6 = 6,29 · 326 K / 186 K · 1,91 $ · 41 min · 0
Filas históricas (de docs/iteraciones.md, 10 capítulos): Salamanca 1572–76 · juez 7,86 · Barcelona 1888 · juez 7,43 · Sevilla 1517–19 · juez 7,4.
Filas [PENDIENTE]: brief adversarial (injection) y brief de incoherencia temporal.
```

### A6 — Juez frente a revisión humana

```text
Anexo A6 "Juez vs. revisión humana". Tabla de 8 criterios × 3 columnas (Persona · Juez · Justificación de la persona) para la versión 1 de la novela de Madrid 1858. Columna Juez: continuidad 8 · arco 7 · coherencia de personajes 8 · ritmo 7 · tono — (no existía en la rúbrica cuando se juzgó) · prosa 8 · naturalidad de la personalización 8 · autenticidad de época 8 · media 7,71. Columna Persona: [PENDIENTE, sale de presentacion/hoja-revision-humana.md]. Debajo, un gráfico de puntos por criterio (Persona en Tinta, Juez en Oro viejo) y la línea "Divergencias > 2 puntos: [PENDIENTE]". Nota: "La rúbrica sale del mismo fichero rubrica.yaml para los dos."
```

### A7 — Red-team log

```text
Anexo A7 "Red-team log". Tabla: ID · Ataque · Clase de evidencia (A análisis / T test / D ejecución) · Estado · Mitigación.
RT-01 Inyección en una anécdota del texto libre · A · abierto · cuarentena + filas tipadas; candidatas: techo de longitud, delimitadores, validador de imperativos
RT-02 Inyección desde una web investigada (cita de 300 caracteres) · A · abierto · cita topada, micro-sesiones, verificador
RT-03 Variantes de palabras prohibidas (homóglifos, derivados) · A → T · derivados resueltos en It-25
RT-04 Usar un cambio del lector para tocar el corpus sellado · A · resuelto por diseño (invariante CorpusSelladoNoSeToca)
RT-05 Agotar presupuesto con el bucle de huecos · A · cerrado (contador en el estado del grafo)
RT-06 Reanudar dos veces el mismo gate · A · cerrado por diseño (fichero .lock; quien llega segundo es rechazado)
```

### A8 — Sensibilidad extendida y comparación de modelos

```text
Anexo A8 "Sensibilidad extendida". Tabla de margen por novela (300/mes) con dos ejes: subida de tokens (0 %, +50 %, +100 %) × revisiones por novela (1,5 · 3 · 6). Valores base: margen 33,89 €; cada 50 % de subida de tokens resta 2,28 €; cada revisión extra resta 2,78 € (0,70 € de tokens + 2,08 € de supervisión). Colorea en Salvia > 25 €, en Oro viejo 15–25 €, en Lacre < 15 €.
Segunda tabla, "Si se sube de modelo": el escritor y el juez en un modelo mayor multiplican su parte de tokens; muestra la fila "Haiku 4.5 en todo (actual): 3,50 €" y deja "[ESTIMAR]" para las alternativas.
```

---

## Ficheros que debe acabar teniendo `presentacion/`

| Fichero | Qué es |
|---|---|
| `storymaker-propuesta.pptx` | Deck editable exportado de Claude Design |
| `storymaker-propuesta.pdf` | El mismo deck en PDF |
| `anexo-arquitectura.pdf` | A1 |
| `anexo-tla-spec.pdf` | A2 |
| `anexo-esquema-sqlite.pdf` | A3 |
| `anexo-validadores.pdf` | A4 |
| `anexo-evals-tabla.pdf` | A5 |
| `anexo-juez-vs-humano.pdf` | A6 |
| `anexo-red-team.pdf` | A7 |
| `anexo-sensibilidad.pdf` | A8 |
| `demo.mp4` o enlace en el README | Vídeo de la demo |
| `README.md` | Lista del contenido y el idioma elegido (castellano) |
