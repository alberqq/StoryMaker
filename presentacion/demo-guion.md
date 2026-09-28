# Guion del vídeo demo

Unos **diez minutos** de vídeo sobre las decisiones que sostienen StoryMaker, en el orden en que una novela las atraviesa: encargo, grafo, contexto, estado, escritura, verificación formal, gates, lectura y regeneración. Cada bloque trae tres cosas: los **planos** que hay que grabar, la **locución** que se lee y lo que hay que **resaltar** en pantalla.

La locución está calculada a unas 150 palabras por minuto. Las cifras coinciden con las de `guion.md` y el deck. Si cambias alguna, cámbiala en los tres sitios.

| # | Bloque | Pantalla | Tiempo | Acumulado |
|---|---|---|---|---|
| 0 | Apertura | Taller | 0:30 | 0:30 |
| 1 | Encargo y cuarentena | Encargo + código | 0:50 | 1:20 |
| 2 | Los validadores son nodos | Código + TLA+ | 1:20 | 2:40 |
| 3 | El contexto se entrega, no se busca | Código | 0:50 | 3:30 |
| 4 | Una novela, un fichero; nada se sobrescribe | Código + SQL | 0:40 | 4:10 |
| 5 | Escritura: validar, reparar, aprobar | Fase de Escritura + código | 0:50 | 5:00 |
| 6 | Lean: la cronología | Lean + terminal | 0:40 | 5:40 |
| 7 | TLA+: el propio arnés | TLA+ + terminal | 0:35 | 6:15 |
| 8 | Gates humanos | Taller, gate + código | 0:45 | 7:00 |
| 9 | Publicación y lectura | Lectura web + PDF | 0:50 | 7:50 |
| 10 | Regeneración | Lectura, gate, versiones + código | 1:20 | 9:10 |
| 11 | Claude Code en el repositorio | Claude Code | 0:30 | 9:40 |
| 12 | Cierre | Taller | 0:20 | 10:00 |

Si hay que recortar, se quitan primero el bloque 11 y después el 7, dejando en este una sola frase.

---

## Antes de grabar

**Servidor.** Construye el frontend y levanta la API, que sirve la interfaz:

```bash
cd frontend && npm run build
cd ../backend && uv run uvicorn storymaker.api.app:crear_app --factory --port 8765
```

Si ya hay un servidor corriendo, no lo reinicies sin mirar antes `curl -s http://127.0.0.1:8765/api/novelas`: si alguna tarjeta está en `en_marcha`, `arrancando` o `esperando_autor`, espera.

**Novelas que se usan.** Todas ya están generadas, así que el vídeo no gasta un céntimo:

| Carpeta | Escenario | Para qué |
|---|---|---|
| `pepa` | Cádiz, 1812 | Palabras prohibidas y rechazo de «tesoro» (bloques 1 y 5) |
| `metro` | Madrid, 1919 | El caso de Lean (bloque 6) |
| `lozoya` | Madrid, 1858, el aguador | Regeneración, versión 3 (bloques 9 y 10) |
| `fase-6-regeneracion` | — | Tiene un gate de Regeneración pendiente, por si quieres enseñarlo abierto |

**Editor.** VS Code en modo Zen o con la barra lateral cerrada, sin minimapa, tema claro y zoom a 150 % o más (`Ctrl+=`). Para cada fragmento, `Ctrl+G` al número de línea y selecciona el rango indicado: la selección es el resaltado. Abre de antemano todas las pestañas del bloque en el orden en que salen.

**Navegador.** Ventana de 1920×1080, zoom al 125 %, sin marcadores ni extensiones visibles.

**Terminal.** Fuente grande y el prompt corto.

**Privacidad, antes de publicar el vídeo.**
- No abras nunca `.env` ni ningún fichero de configuración con claves. En Langfuse, tapa la clave, como en `capturas/langfuse-sesion.png`.
- La portada, la dedicatoria y los capítulos llevan el nombre de la persona homenajeada. Si alguna de esas personas es real, desenfoca su nombre en edición o usa una novela de evaluación con un homenajeado ficticio.

**Plano del hook (bloque 11).** Prepara una carpeta `demo/` con dos ficheros. Ya está probado: la edición se deniega con salida 2.

`demo/capitulo_demo.contexto.json`:
```json
{"nombres_canonicos": ["Cayetano"], "prohibidas": [{"nivel": "novela", "termino": "tesoro"}], "rango_palabras": [20, 2000]}
```

`demo/capitulo_demo.md`: un párrafo cualquiera de más de veinte palabras que contenga «agua nueva».

---

## 0 · Apertura (0:30)

**Plano.** Navegador en `http://127.0.0.1:8765/`: el Taller, con el tablero de novelas por fases. Movimiento lento del ratón de izquierda a derecha por las columnas.

**Locución.**
> Esto es StoryMaker: un arnés multiagente que escribe novelas históricas personalizadas para regalo. Convierte a la persona homenajeada en protagonista de un momento histórico real y documentado. Por dentro hay seis fases, nueve roles del Claude Agent SDK, todos en Haiku 4.5, y un orquestador LangGraph. En los próximos diez minutos voy a enseñar las decisiones de las que cuelga todo lo demás, en el código y en la interfaz.

**Resaltar.** Los encabezados de las seis columnas del tablero.

---

## 1 · Encargo y cuarentena (0:50)

**Plano A.** `http://127.0.0.1:8765/encargo`: la conversación con el entrevistador. Escribe una premisa corta y deja que aparezca la primera pregunta. No sigas: una entrevista completa lanza ejecuciones reales.

**Plano B.** [intake/cuarentena.py](../backend/src/storymaker/intake/cuarentena.py), líneas 1-13.

**Locución.**
> Todo empieza con una entrevista corta. El comprador escribe una premisa libre y el entrevistador pregunta solo lo que falta. Sale un brief validado con schema, con una lista de lo que no debe aparecer: en la novela de Cádiz, «pirata», «tesoro» y «naufragio». Si el comprador pega una carta, ese texto no es de fiar. Va a cuarentena, y la defensa contra prompt injection es estructural, no una instrucción: no se le pide a ningún modelo que ignore órdenes. Un extractor con salida restringida por schema saca personas, lugares, fechas, objetos y anécdotas. Lo que llega al escritor es «un reloj de bolsillo», no la frase que lo rodeaba.

**Resaltar.** En el código, las líneas 9-13: «La defensa contra *prompt injection* es estructural, no una instrucción» y el ejemplo `{"tipo": "objeto", …}`.

---

## 2 · Los validadores son nodos del grafo (1:20)

Es el bloque más importante del vídeo: tómate tu tiempo.

**Plano A.** [commons/graph/construccion.py](../backend/src/storymaker/commons/graph/construccion.py), líneas 105-151: la función `construir`, con el `StateGraph` y sus aristas.

**Plano B.** [commons/graph/aristas.py](../backend/src/storymaker/commons/graph/aristas.py), líneas 79-102: `_comprobada` y `tras_validate`.

**Plano C.** [formal/tla/harness.tla](../formal/tla/harness.tla), línea 82, la definición `Aristas`, y a la derecha, en pantalla partida, [tests/contratos/test_identidad_nodos.py](../backend/tests/contratos/test_identidad_nodos.py), líneas 86-87.

**Locución.**
> Esta es la decisión de la que cuelga el sistema: los validadores son nodos del grafo, no herramientas que un agente decide llamar. Lo que un modelo puede olvidarse de invocar no es una comprobación. Aquí se cablea el grafo. Después de WriteChapter viene siempre Validate, y de Validate solo se sale por tres sitios: Repair, Extract o Fail.
>
> ¿Quién decide la salida? Un booleano calculado en Python, contando incidencias en una lista, nunca lo que diga un modelo. Si no hay bloqueantes, se va a Extract; si quedan reintentos, al editor; si no, se detiene. Y cada enrutador pasa por `_comprobada`, que revienta si alguien elige una arista que no está declarada.
>
> Esa relación de aristas es la misma que la del modelo TLA+, y un test lo comprueba arista por arista. Así, lo que TLC verifica sobre el modelo es lo que el código hace.

**Resaltar.**
- En `construccion.py`, la línea 141: `("Validate", tras_validate, ["Repair", "Extract", "Fail"])`.
- En `aristas.py`, la línea 98 (`if not estado["hay_bloqueantes"]`) y la 87 (`raise AssertionError`).
- En el test, el nombre `test_la_relacion_de_transicion_es_la_misma`.

---

## 3 · El contexto se entrega, no se busca (0:50)

**Plano A.** [commons/context/paquete.py](../backend/src/storymaker/commons/context/paquete.py), líneas 19-35.

**Plano B.** [commons/agents/techos.py](../backend/src/storymaker/commons/agents/techos.py), líneas 59-102, y después [commons/agents/hooks.py](../backend/src/storymaker/commons/agents/hooks.py), líneas 62-76.

**Locución.**
> El escritor no busca su contexto: lo recibe. Un módulo de código, sin nada de inteligente, le arma un paquete de siete bloques con doce mil tokens de techo: el encargo, el canon que sale en el capítulo, la continuidad, la memoria, los hechos históricos, las reglas y la personalización. Si se pasa, se recorta en un orden fijo, y la continuidad es lo último que se toca, porque es lo que impide contradecir lo que ya pasó.
>
> Cada rol tiene su techo declarado, y el límite de cien mil tokens concurrentes no se vigila: se garantiza por construcción. El peor caso es el investigador, con cuarenta y cinco mil, y es el único rol con red. Un hook PreToolUse le deniega la cuarta búsqueda, y otro PostToolUse recorta cada página antes de que entre en su contexto.

**Resaltar.**
- `TECHO_TOTAL: Final = 12_000` (línea 30) y `ORDEN_DE_RECORTE` (línea 35), con el 3 al final.
- En `techos.py`, la fila del investigador, con `45_000` y `cuota_de_herramientas=(("WebSearch", 3), ("WebFetch", 3))`.
- En `hooks.py`, `"permissionDecision": "deny"` (línea 65).

---

## 4 · Una novela, un fichero; nada se sobrescribe (0:40)

**Plano A.** [commons/graph/run.py](../backend/src/storymaker/commons/graph/run.py), líneas 197-206: el checkpointer de LangGraph se abre sobre la misma conexión que la story bible.

**Plano B.** [commons/db/esquema/inmutabilidad.sql](../backend/src/storymaker/commons/db/esquema/inmutabilidad.sql), líneas 1-32.

**Plano C (opcional).** El explorador de ficheros en `backend/proyectos/lozoya/`: se ve que la novela es un `.db`.

**Locución.**
> El estado vive en un solo sitio: un fichero SQLite por novela. Ahí está la story bible, con el corpus, el canon y la escaleta, y ahí escribe también LangGraph su checkpoint, sobre la misma conexión. Si el proceso muere en el capítulo seis, `storymaker continuar` reanuda desde el seis, sin perder ni duplicar nada.
>
> Y nada se sobrescribe. Un capítulo regenerado es una fila nueva, y una versión de la novela es la lista de qué versiones de capítulo la componen. La regla tiene dos cerrojos: una regla Semgrep impide escribir el UPDATE, y este trigger impide ejecutarlo. Un principio con un solo cerrojo es una convención; con dos, es una propiedad.

**Resaltar.** En el SQL, las líneas 4-5 («Un principio con un solo cerrojo es una convención…») y el `RAISE(ABORT, 'capitulo_version es inmutable…')` de la línea 25.

> **Cuidado con esta frase.** La arquitectura (§7) dice que el checkpoint y el capítulo se escriben «en la misma transacción», pero en el código el envoltorio que lo haría, `paso_atomico` ([commons/db/transaccion.py](../backend/src/storymaker/commons/db/transaccion.py)), no lo llama nadie, y la conexión se abre en autocommit ([commons/db/apertura.py:172](../backend/src/storymaker/commons/db/apertura.py#L172)). Por eso la locución dice «en el mismo fichero, sobre la misma conexión» y no «en la misma transacción». No enseñes `transaccion.py` como prueba.

---

## 5 · Escritura: validar, reparar, aprobar (0:50)

**Plano A.** [writing/validacion.py](../backend/src/storymaker/writing/validacion.py), líneas 1-17 (el docstring de las dos pasadas) y 177-178 (`hay_bloqueantes`).

**Plano B.** Navegador en `http://127.0.0.1:8765/novelas/pepa/fases/escritura`. Despliega el capítulo que tiene más de un intento y enseña la incidencia bloqueante del primero y el segundo, aprobado.

**Locución.**
> Cada capítulo pasa dos filtros, y en este orden. Primero lo gratis: longitud, nombres exactos del canon, anacronismos y palabras prohibidas, todo en Python determinista. Solo si sale limpio se paga una llamada al extractor, que saca el resumen, la continuidad y los hechos usados, y entonces corre Lean sobre la cronología. Si algo falla, el editor emite un parche. Tiene dos reintentos como máximo y un contador compartido.
>
> Aquí se ve en una novela real, la de Cádiz. El escritor puso «no el oro, sino el tesoro que permanecería». El guardrail lo cazó, el capítulo volvió al editor y el segundo intento salió sin la palabra. Quien escribe no aprueba.

**Resaltar.** En la interfaz, la incidencia bloqueante con «tesoro» y el paso de «rechazado» a «aprobado». Si el capítulo que la contiene no es evidente, búscalo antes de grabar y apunta su número aquí: ___.

---

## 6 · Lean: la cronología de la historia (0:40)

**Plano A.** [formal/lean/Cronologia/Basico.lean](../formal/lean/Cronologia/Basico.lean), líneas 94-105 (I1, «nadie participa en un evento antes de nacer») y 158-162 (`Coherente`).

**Plano B.** [commons/formal/runner.py](../backend/src/storymaker/commons/formal/runner.py), líneas 1-20.

**Plano C.** Terminal:
```bash
cd formal/lean && lake build && lake exe verificar; echo "salida: $?"
```

**Locución.**
> Para la cronología usamos Lean 4. Los cuatro invariantes se escriben a mano una vez: nadie actúa antes de nacer, nadie después de morir, nadie está en dos sitios a la vez y ningún objeto aparece fuera de su época. De cada novela solo se generan datos, nunca teoremas. El contrato es el código de salida: cero, coherente; uno, no.
>
> En la novela del metro de Madrid, la homenajeada nacía en 1967 y la novela la ponía en 1917. Ningún validador de texto lo vio, y el juez le dio un siete. Lean falló en nueve escenas. Y si Lean no está instalado, el capítulo no se aprueba por avería: un error de entorno no es un veredicto.

**Resaltar.** En `runner.py`, las líneas 4-5 («El código de salida es el contrato») y 10-14 (incidencia frente a error de entorno). En la terminal, `salida: 0`.

---

## 7 · TLA+: el propio arnés (0:35)

**Plano A.** [formal/tla/harness.tla](../formal/tla/harness.tla), líneas 636-657: `NoPublishUnvalidated`, `ResumeIsExactlyOnce` y `RetriesBounded`.

**Plano B.** En Claude Code, `/tlc`, o la salida guardada si no quieres esperar. Necesita la JVM y `tla2tools.jar` (ver `formal/tla/README.md`).

**Locución.**
> Lean verifica la historia; TLA+ verifica el sistema. TLC recorre todos los estados del modelo, doce mil seiscientos en interactivo y cuatro mil cuatrocientos en batch, y comprueba que nunca se publica un capítulo sin validar, que reanudar no duplica ni pierde capítulos y que los reintentos están acotados. Antes de llegar a cero violaciones cazó tres errores de diseño, entre ellos un «rehacer» que duplicaba capítulos.

**Resaltar.** Las líneas 638-642: el invariante se comprueba sobre una variable de historia y no sobre una guarda, «para que el invariante interrogue al grafo y no a sí mismo».

---

## 8 · Gates humanos (0:45)

**Plano A.** El Taller. Arrastra una tarjeta que espera en un gate hacia la columna siguiente, hasta que salga el diálogo de confirmación, y **cancela**. Aprobar lanza una ejecución real.

**Plano B.** La página del gate pendiente: `http://127.0.0.1:8765/novelas/fase-6-regeneracion/gate`, o la de cualquier novela que espere. Enseña el informe, el corpus o la escaleta a la vista y los botones de decisión.

**Plano C.** [gates/nodos.py](../backend/src/storymaker/gates/nodos.py), líneas 111-118: la llamada a `interrupt()`.

**Locución.**
> En cinco puntos decide una persona: al cerrar el encargo, la investigación, la trama y la escritura, y ante cada cambio del lector. El gate llama a `interrupt()` de LangGraph: el checkpoint se persiste y el proceso termina. No hay nada en memoria esperando. La decisión entra después con el mismo mecanismo con el que se reanuda tras un fallo, así que hay un solo camino de código. Desde la interfaz, el Autor ve lo que tiene que decidir, corrige filas si hace falta, y aprueba o rehace. Y la interfaz no ejecuta el grafo: lanza la misma CLI que usaría desde la terminal.

**Resaltar.** `decision: Any = interrupt(` (línea 111) y, en la interfaz, el diálogo de confirmación del arrastre.

---

## 9 · Publicación y lectura (0:50)

**Plano A.** `http://127.0.0.1:8765/novelas/lozoya/v/3`: el índice. Entra en un capítulo, vuelve, abre la ficha de personajes (`/personajes`) y pulsa un enlace a un capítulo; termina en la portada (`/portada`).

**Plano B.** El PDF junto a la misma página web, en pantalla partida. En la carpeta solo está `backend/proyectos/lozoya/lozoya.v1.pdf`, así que ponlo al lado de `/novelas/lozoya/v/1`, o enseña la ruta de impresión `/novelas/lozoya/v/3/imprimir`, que es la que imprime Playwright. Después, [publication/render.py](../backend/src/storymaker/publication/render.py), líneas 275-293.

**Plano C (rápido).** [publication/nodos.py](../backend/src/storymaker/publication/nodos.py), líneas 126-133: `topar_continuidad`.

**Locución.**
> Antes de publicar, la novela entera pasa por Lean y por un render visual con Playwright, y el juez la puntúa con una rúbrica de ocho criterios. El juez mide pero no toca el texto, y no pone la última palabra: enumera las contradicciones y Python le topa la nota de continuidad. Lo añadimos cuando una lectura humana encontró un ocho en continuidad en una novela con cinco contradicciones.
>
> La novela se lee en web, con un índice, fichas de personajes y lugares enlazadas a los capítulos, y una portada con dedicatoria. El PDF no se maqueta aparte: es esta misma ruta, impresa con Playwright. Así no pueden divergir.

**Resaltar.** En `render.py`, la línea 275 («Imprime la misma ruta que lee el navegador») y `pagina.pdf(` en la 293. En `nodos.py`, `techo = max(1, 10 - 2 * len(notas.contradicciones))`.

---

## 10 · Regeneración: un cambio del lector (1:20)

El cierre natural de la demo: aquí se ven juntas casi todas las decisiones anteriores.

**Plano A.** `http://127.0.0.1:8765/novelas/lozoya/v/1/capitulos/1`. Selecciona con el ratón un nombre en el texto y enseña que aparece el formulario de petición de cambio. Escribe la petición, pero **no la envíes**: enviarla registra un cambio de verdad. Si quieres enseñar el envío, usa la novela `fase-6-regeneracion`.

**Plano B.** La página del gate de Regeneración (`/novelas/fase-6-regeneracion/gate`): los candidatos que encontró la story bible, con los capítulos que habría que regenerar y revisar.

**Plano C.** [regeneration/cambio.py](../backend/src/storymaker/regeneration/cambio.py), líneas 1-11, y [regeneration/nodos.py](../backend/src/storymaker/regeneration/nodos.py), líneas 37-70 (`calcular_alcance`).

**Plano D.** `http://127.0.0.1:8765/novelas/lozoya/versiones` y el índice de la versión 3, con la marca de los capítulos cambiados. Cierra con [regeneration/diff.py](../backend/src/storymaker/regeneration/diff.py), líneas 1-11.

**Locución.**
> Y lo que pasa cuando el lector quiere cambiar algo. En la novela del aguador, no quiere que un personaje se llame Cayetano. Lo selecciona en el capítulo uno y escribe «se llama Amancio».
>
> El sistema busca en la story bible y enseña al Autor los candidatos. Ningún modelo interpreta la petición: el Autor confirma la fila y el valor nuevo. Y el cambio se aplica a la fila, nunca al texto. El canon manda sobre el texto: un buscar y reemplazar sobre la prosa dejaría mintiendo a la biblia.
>
> Como cada hecho sabe en qué capítulos se usa, el alcance sale de una consulta: se regeneraron los capítulos uno, dos, cuatro y cinco, y se revisó el tres. Pasan por los mismos validadores, Lean incluido, y se publica la versión tres. Las anteriores siguen intactas, y «qué cambió» es un JOIN entre dos manifiestos, no un diff de prosa. Este cambio costó noventa y cuatro céntimos de dólar.

**Resaltar.**
- La selección del nombre en el capítulo y el formulario que aparece.
- En `cambio.py`, la línea 3: «modificar la fila, nunca el texto».
- En `nodos.py`, `texto.capitulos_afectados(db, fila_id)` (línea 55): de ahí sale el alcance.
- En el índice de la v3, las marcas de capítulo cambiado y el aviso «N capítulo(s) cambian respecto de la versión…».

---

## 11 · Claude Code en el repositorio (0:30)

**Plano A.** [.claude/settings.json](../.claude/settings.json), con los dos hooks.

**Plano B.** En Claude Code, pídele: «En demo/capitulo_demo.md cambia "agua nueva" por "agua, su verdadero tesoro,"». Se ve la edición denegada: «Aparece el término prohibido «tesoro» (nivel novela)».

**Locución.**
> Para trabajar sobre el propio repositorio con Claude Code hay un CLAUDE.md, una skill de continuidad y dos hooks sobre los ficheros de capítulo. El de policy deniega una edición que introduzca un término prohibido antes de que llegue al disco. El de validación pasa el capítulo por los validadores deterministas después. Y los dos usan el mismo código que el grafo, no una copia: una prueba de contrato exige el mismo veredicto por los dos caminos.

**Resaltar.** El mensaje de edición denegada.

---

## 12 · Cierre (0:20)

**Plano.** Vuelta al Taller, o la sesión de Langfuse de una novela con la clave tapada (`capturas/langfuse-sesion.png`).

**Locución.**
> En resumen, tres decisiones lo explican todo: validar no es opcional, el estado vive en un solo sitio y nada se sobrescribe. Todo lo demás, del contexto acotado a Lean y TLA+, se construye sobre ellas. Cada novela es una sesión en Langfuse, con el coste de cada llamada, y cuesta entre dos y tres dólares y medio. Gracias.
