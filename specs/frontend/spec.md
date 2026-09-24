# Spec — Frontend de StoryMaker

Qué construye el frontend, qué enseña cada pantalla, de dónde saca cada dato, qué puede hacer el Autor desde ella, qué pasa cuando algo va mal y con qué se comprueba que hace lo que dice.

Deriva de [`architecture.md`](../../docs/architecture.md), que es la fuente de verdad —§4 para las fases, §10 para los gates, §16.1 para la pila, §16.3 para la organización en Feature-Sliced Design y **§16.5 para la operación del arnés desde la interfaz**—, y de [`verification.md`](../../docs/verification.md), de donde toma el marco T·A·I·D·U y los Quality Gates. **Si algo de este documento contradice a la arquitectura, manda la arquitectura.** La forma técnica exacta —qué fichero, qué componente, en qué orden se construye— no vive aquí, sino en [`plan.md`](plan.md).

**Alcance.** Todo `frontend/src/`: el taller, el encargo, el panel de cada novela, la pantalla del gate, la salida de cada fase, las pantallas de lectura, el cliente de la API, el kit de componentes y el modo impresión del que sale el PDF. Queda fuera el backend, que tiene su propia spec en [`specs/backend/spec.md`](../backend/spec.md) y cuya API —§5 de aquel documento— este consume sin discutir; queda fuera también el PDF como artefacto, porque lo imprime Playwright desde el backend, aunque lo que imprime sea una ruta de este frontend.

---

## 1. La forma del frontend en una página

El frontend es **una aplicación React construida con Vite y organizada en Feature-Sliced Design v2.1**, con cuatro capas: `app/`, `pages/`, `entities/` y `shared/`. No tiene servidor propio, no guarda nada y no ejecuta nada.

Cuatro afirmaciones lo gobiernan, y conviene tenerlas delante al leer el resto:

1. **El frontend no tiene verdad propia.** Todo lo que enseña sale de la API, y la API lee el fichero SQLite de la novela. No hay estado de dominio en el cliente que sobreviva a una recarga, ni una copia local del canon, ni un almacén global de la novela. Seguir una ejecución es volver a preguntar, no acumular. **La única excepción son las preferencias de presentación** —el tema de la aplicación (§8) y los ajustes de lectura (§4.6)—, que no son de la novela sino de quien la mira y se guardan en el navegador desde un solo módulo.
2. **Operar es pedir, no ejecutar.** Cuando el Autor lanza una novela o decide un gate, el frontend envía la acción y la API lanza la CLI como proceso aparte (arq. §16.5). La pantalla dice que la acción está lanzada y sigue mirando el fichero; nunca espera a que el proceso termine ni simula su resultado.
3. **Se lee una Versión, no «la novela».** Un Capítulo publicado existe dentro de un manifiesto. Por eso **toda ruta de lectura lleva el número de versión**, y una URL de lectura sin versión es incorrecta, porque no identifica ningún texto.
4. **La ruta que lee el lector es la que se imprime y la que se juzga.** El PDF sale de imprimirla con `page.pdf()` de Playwright, y `render_visual` la mira dentro de `PublishVersion`. El frontend es, por tanto, **la única pieza del repositorio fuera del backend que puede impedir una publicación**.

```text
frontend/src/
├─ app/
│  ├─ providers/       proveedores de la aplicación
│  ├─ router.tsx       el mapa de rutas de §3, y el único sitio donde vive
│  ├─ styles/          tokens de diseño, estilos globales, fuentes y @media print
│  └─ main.tsx         punto de entrada
├─ pages/
│  ├─ library/         el taller: tablero por fases con todas las novelas
│  ├─ commission/      el encargo de una novela nueva
│  ├─ novel/           el panel de una novela
│  ├─ gate/            el gate que espera decisión
│  ├─ phase/           la salida de cada fase
│  ├─ reading/         lector, índice, navegación, selección y petición de cambio
│  ├─ characters/      fichas de personajes y lugares
│  ├─ cover/           portada, dedicatoria y nota del autor
│  ├─ versions/        historial, diff de manifiestos y novedades
│  └─ print/           la novela entera en una página, para PDF y render_visual
├─ entities/
│  └─ novela/          estado de una novela y su línea de fases
└─ shared/
   ├─ api/             cliente de la API y tipos de transporte
   ├─ ui/              kit de componentes
   ├─ lib/             utilidades y hooks
   └─ config/          rutas y variables de entorno
```

---

## 2. Puesta en marcha y configuración

### 2.1 Cómo se sirve

| Escenario | Quién sirve la aplicación | Quién sirve la API | Por qué |
|---|---|---|---|
| Desarrollo | `vite dev` | FastAPI en otro puerto, alcanzado por el **proxy de Vite** en `/api` | Recarga en caliente sin pagar CORS |
| Uso normal, impresión y `render_visual` | **FastAPI**, sirviendo el `dist/` construido | FastAPI, el mismo proceso | Un solo origen |

**En todo lo que no es desarrollo, el frontend lo sirve FastAPI desde su construcción estática** (arq. §16.4). Con un solo origen, la URL que abre `render_visual`, la que imprime el PDF y la que teclea el Autor son literalmente la misma.

**La API vive bajo `/api` en los dos escenarios.** La aplicación y la API tienen rutas que empiezan por `/novelas`, y sin prefijo recargar la página de una novela devolvería JSON. FastAPI sirve `index.html` en toda ruta de la aplicación que no sea un fichero, y un endpoint inexistente sigue siendo un `404`. **El servidor escucha solo en `127.0.0.1`** (arq. §16.5): la interfaz se usa en el PC del Autor.

### 2.2 Configuración

Solo hay dos variables, y ninguna es un secreto: **este frontend no tiene credenciales que guardar**, porque la API no lleva autenticación (riesgo aceptado U-17).

| Clave | Valor por defecto | Para qué |
|---|---|---|
| `VITE_API_URL` | vacío, es decir, el mismo origen | Base del cliente de la API |
| `VITE_BASE_PATH` | `/` | Prefijo de rutas cuando FastAPI monta la aplicación bajo un camino |

Los alias de importación —`@/app`, `@/pages`, `@/entities`, `@/shared`— se declaran a la vez en `tsconfig.json` y en `vite.config.ts`, para que el resolutor de TypeScript y el de Vite no puedan discrepar.

---

## 3. El mapa de rutas

| Ruta | Página | De dónde saca los datos |
|---|---|---|
| `/` | `library` | `GET /novelas` |
| `/encargo` | `commission` | `GET /ejemplos`, `POST /encargos/validar` |
| `/novelas/:id` | `novel` | `GET /novelas/{id}/panel` |
| `/novelas/:id/gate` | `gate` | `GET /novelas/{id}/gate` |
| `/novelas/:id/fases/:fase` | `phase` | `GET /novelas/{id}/fases/{fase}` |
| `/novelas/:id/v/:n` | `reading`, índice | `GET /novelas/{id}/versiones/{n}` |
| `/novelas/:id/v/:n/capitulos/:k` | `reading`, capítulo | `GET /novelas/{id}/versiones/{n}/capitulos/{k}` |
| `/novelas/:id/v/:n/portada` | `cover` | `GET /novelas/{id}/versiones/{n}` |
| `/novelas/:id/v/:n/personajes` | `characters` | `GET /novelas/{id}/versiones/{n}/personajes` |
| `/novelas/:id/versiones` | `versions` | `GET /novelas/{id}` y el endpoint de diff |
| `/novelas/:id/v/:n/imprimir` | `print` | Todo lo de lectura, de la versión `n` |

Las rutas de la API se escriben aquí sin su prefijo `/api`. `:fase` toma el nombre castellano de la fase en la URL —`encargo`, `investigacion`, `trama`, `escritura`, `publicacion`, `regeneracion`—, porque la URL la lee el Autor.

**El mapa vive entero en `app/router.tsx`, y las páginas no se conocen entre sí.** Para enlazar a otra pantalla, una página llama a un constructor de URL de `shared/config/rutas.ts` en lugar de importar nada de la slice vecina, que es lo que la segunda regla de FSD prohíbe.

---

## 4. Las pantallas

Cada una declara qué enseña, de dónde sale y qué hace cuando el dato no está. Los estados de carga, de error y de vacío **son parte del contrato**: una pantalla nunca se queda en blanco, y un esqueleto de carga eterno es un render roto.

### 4.1 `pages/library` — el taller

**Es un tablero por fases, al estilo de Jira** (arq. §16.5). Tiene cinco columnas: Encargo, Investigación, Trama, Escritura y Publicación. Cada novela en curso del directorio `proyectos/` es una tarjeta en la columna de su fase actual.

**Las publicadas van debajo, en un listado.** Una novela con versiones publicadas y sin trabajo en marcha sale del tablero y pasa a una tabla bajo él, titulada «Publicadas», con una fila por novela: el título, que abre su panel, el homenajeado, las versiones, lo gastado, cuándo se tocó por última vez y el enlace para leer la última versión. Una novela en Regeneración también va ahí, con su insignia, y si espera al Autor su fila enlaza al gate, que es donde se elige el candidato. Sin novelas publicadas, el listado no aparece.

La tarjeta enseña el título, el homenajeado, **el estado de la novela** (§5.2) con su insignia de color, los capítulos aprobados sobre el total, lo gastado y, si espera al Autor, qué gate. Pulsarla abre su panel. Una novela sin versiones publicadas aparece igual, pero sin enlace de lectura: lo que se lee es una versión.

**Arrastrar decide un gate, con confirmación.** Solo se arrastran las tarjetas con un gate pendiente, salvo el de Regeneración, que exige elegir candidato y se decide en su pantalla. Una tarjeta solo se puede soltar en dos sitios:

- **La columna siguiente es aprobar.**
- **Su misma columna es rehacer.**

Soltar no decide nada. Abre un diálogo con el resumen del gate, el enlace a su pantalla completa y, para rehacer, la casilla del comentario, y solo el botón de confirmar envía la decisión. Mientras se arrastra, las columnas que aceptan la tarjeta se iluminan y las demás no reaccionan. **Cada gesto tiene su alternativa por botones** en la propia tarjeta, para el teclado y para quien no quiera arrastrar.

Desde el taller se abre **el encargo de una novela nueva**. Un directorio sin novelas se anuncia como vacío, con esa misma llamada a encargar, y no como un error.

### 4.2 `pages/commission` — el encargo

**El encargo empieza por una conversación con el entrevistador**, que es como la Fase 1 está pensada (arq. §4): el comprador escribe unas líneas y el entrevistador pregunta solo por lo que falta. La pantalla tiene dos modos, y el primero es el que se abre:

- **Conversación**, por defecto. Pide el nombre del homenajeado —lo único imprescindible— y **la novela contada con tus palabras**, en una sola caja de texto grande. Esa descripción viaja como `descripcion` del encargo y entra en la premisa que lee el entrevistador, no en la cuarentena. Este modo **lanza siempre con gates**, porque sin gates no hay entrevista, y al lanzar lleva a la pantalla del gate de la novela, donde la conversación continúa.
- **Formulario completo**, para quien ya lo tiene todo decidido. Es el formulario guiado por los bloques del encargo —homenajeado, mundo y obra—, con los campos obligatorios marcados, la posibilidad de **partir de uno de los briefs de `ejemplos/`** y la elección entre **con gates o en batch**. Lanzar lleva al panel.

En los dos modos se puede pedir **investigación exhaustiva** con una casilla, que explica que tarda y cuesta más y que se decide al crear la novela (arq. §4, Fase 2). En los dos modos **la validación la hace el backend**, con el mismo lector que `storymaker nueva`, y los errores se enseñan junto a su campo. El nombre de la novela es opcional: por defecto, el del homenajeado.

### 4.3 `pages/novel` — el panel de una novela

Es la pantalla desde la que se sigue una ejecución entera:

- **La cabecera** lleva el título, el homenajeado, el estado de la novela y **las acciones que ese estado admite** (§5.3), y nada más: una acción que la API rechazaría no se ofrece.
- **La línea de las seis fases** enseña, para cada fase, su estado, lo que costó, los tokens y lo que duró. Cada fase enlaza a su salida. El estado de cada fase lo calcula el backend a partir de sus ejecuciones y, en las novelas empezadas antes de que se registraran todas, **de si la fase dejó salida** (§5.2).
- **La actividad**, interpretada: qué fase trabaja, en qué capítulo e intento, cuál fue la última decisión de gate y las incidencias recientes. Lo que se lee es lo que está pasando, no un volcado.
- **La rejilla de capítulos**, con el estado de cada uno —pendiente, en curso, aprobado, invalidado— y sus intentos.
- **El consumo acumulado**: coste y tokens de entrada y salida.
- **El registro del proceso**, plegado, para cuando haga falta mirar la salida literal.
- **Las versiones publicadas**, con el acceso a leer cada una y a **descargar su PDF**.

### 4.4 `pages/gate` — la decisión

Enseña **qué fase espera**, desde cuándo, el resumen del gate —los mismos recuentos que lleva el aviso— y el enlace a la salida completa de esa fase.

**En el gate de Intake, la pantalla es una conversación con el entrevistador** (arq. §4, Fase 1). Enseña primero la descripción del encargo, después cada ronda anterior con las respuestas que se le dieron, y al final las preguntas nuevas, cada una con su casilla. Contestar es **rehacer**, con el conjunto de respuestas como comentario. Tras enviar, **la pantalla no se va**: dice que el entrevistador está pensando mientras la novela corre, y la ronda siguiente aparece sola cuando el gate vuelve a abrirse. Cuando el entrevistador ya no pregunta nada, lo dice, enseña el brief que ha cerrado y propone aprobar para pasar a la Investigación.

**Las decisiones que ofrece:**

- **Aprobar** y **rehacer con comentario**, en todos los gates.
- **Abortar**, solo en el de Intake y con una confirmación explícita (arq. §10).

**Editar no es una decisión en esta pantalla** (arq. §16.5). Abre el editor de filas, que alcanza los hechos del corpus, los personajes, los escenarios y el glosario. Cada cambio se guarda en el momento, con su motivo, y queda trazado; cuando el Autor termina, aprueba o rehace. La pantalla **nunca envía la decisión `editar`**. Un hecho de un corpus ya sellado no se ofrece como editable, porque la base no lo admitiría.

**El gate de Regeneración** enseña la petición que lo abrió y **los candidatos como opciones a elegir**, cada uno con su descripción y los capítulos que regeneraría y los que solo revisaría. Debajo, la casilla **«Valor nuevo»**, precargada con el valor que el campo por defecto del candidato elegido tiene hoy; cambiar de candidato la vuelve a precargar. Aprobar envía `<objeto>:<fila_id> <campo>=<valor>`, que el backend aplica a esa fila sin volver a buscar (spec del backend §4.6, con los campos de cada candidato de §5.2); el primer candidato viene elegido, y aprobar sin cambiar el valor no cambia nada. Un candidato sin fila guardada se enseña pero no se elige, y sin candidatos aprobar deja pasar la regeneración de largo. Rehacer sigue llevando el comentario libre. Sin gate pendiente, la pantalla lo dice y enlaza al panel; si la novela está trabajando, dice en qué fase y espera, porque el gate puede estar a punto de abrirse. Tras decidir, vuelve al panel, donde se ve la novela reanudarse.

### 4.5 `pages/phase` — la salida de cada fase

Una pestaña por fase. En todas, arriba, **sus ejecuciones** —estado, tokens, coste, inicio y duración— y **las decisiones de sus gates**, con su comentario. Debajo, lo que la fase dejó escrito:

| Fase | Qué enseña |
|---|---|
| Encargo | El brief tal como quedó, los datos del encargo con su tipo, si son obligatorios y su origen, y el texto que entró en cuarentena |
| Investigación | Los hechos **agrupados por dimensión**, con su firmeza como única etiqueta, lo que no dice la cita, su cita y sus fuentes enlazadas; el recuento por dimensión; las entidades; y el sello del corpus si ya existe |
| Trama | La obra —título, premisa, tema, voz y estilo—, los personajes con sus arcos e hitos, las relaciones, los escenarios, las Licencias, el glosario y **la escaleta** capítulo → escena → beat, con los anclajes de cada escena |
| Escritura | Cada capítulo con **sus intentos**, su estado y sus palabras, **las incidencias de cada intento** con su validador, severidad y propuesta, y el texto de cualquier intento |
| Publicación | Las versiones con **la rúbrica del juez por criterio**, el manifiesto y el acceso a leer cada versión |
| Regeneración | Las peticiones, lo que cambió cada una y las ediciones humanas registradas |

Una fase sin salida todavía lo dice. No es un error.

### 4.6 `pages/reading` — el lector

Dos vistas sobre la misma slice:

- **El índice** lista los capítulos del manifiesto en orden, con su número y su título, y **marca los que cambiaron respecto de la versión anterior** cuando la hay. La marca sale del endpoint de diff, no de comparar textos en el cliente.
- **El capítulo** muestra el texto tal como esa versión lo fija, con navegación a anterior y siguiente y vuelta al índice.

Sobre el texto del capítulo se ejercen **la selección de fragmento y la petición de cambio** (§6). Viven aquí, y no en una slice propia, porque solo se ejercen aquí.

**Los ajustes de lectura, como en un lector electrónico.** Toda pantalla del registro de libro —capítulo, índice, portada, personajes, historial— lleva arriba a la derecha el botón **«Aa»**, que despliega una pestaña con cinco controles que se aplican en vivo, sin recargar:

- **Tamaño de letra**, en cinco pasos, con «A−» y «A+».
- **Fuente**, entre tres: **Garamond**, la del libro y la de por defecto; **Georgia**, otra serif más abierta; y **Inter**, una sin serifa. Las tres están ya en la máquina —Garamond e Inter servidas con la aplicación, Georgia del sistema—, así que cambiar de fuente no pide nada a la red.
- **Interlineado**, en tres pasos: compacto, normal y amplio.
- **Negrita**, que engruesa el texto corrido para quien lee mejor con más peso.
- **Fondo del libro**: igual que la aplicación, claro u oscuro. **Es independiente del tema de la aplicación** (§8): se puede tener el panel oscuro y leer el libro en claro, o al revés.

La pestaña se cierra al pulsar fuera o con Escape. Los ajustes **se recuerdan entre visitas** en el almacenamiento del navegador, bajo una sola clave y desde un solo módulo de `shared/lib`; si el navegador no deja guardar, se aplican igual durante la visita. **No tocan la ruta de impresión**: el PDF se maqueta siempre igual, lea quien lea.

El lector **no ofrece imprimir**: la novela se lleva en papel con el PDF, que se descarga desde el índice. La ruta `/imprimir` sigue existiendo porque es de la que sale el PDF, pero ninguna pantalla enlaza a ella.

### 4.7 `pages/characters` — personajes y lugares

Las fichas de la biblia de la obra. Los personajes llevan su tipo, sus rasgos y su relación con el homenajeado; los escenarios, su **nombre corto** como título, su lugar de época y su descripción debajo. **Cada entrada enlaza a los capítulos en los que aparece**, con el número de versión que la ruta lleva puesto, porque un capítulo fuera de un manifiesto no es una dirección válida.

### 4.8 `pages/cover` — portada, dedicatoria y nota del autor

El **título** con su tratamiento de portada, la **dedicatoria** al homenajeado con su ocasión, y la **nota del autor**, que declara las Licencias. Sin Licencias declaradas se omite la nota, que es un caso legítimo.

### 4.9 `pages/versions` — el historial

Lista las versiones publicadas con su fecha y su puntuación del juez, y enseña **qué capítulos cambian** entre dos cualesquiera. Desde aquí se abre cualquier versión anterior, que sigue entera y legible.

### 4.10 `pages/print` — la novela entera en una página

Un único documento con, en este orden: portada y dedicatoria, nota del autor, índice, los capítulos del manifiesto, la ficha de personajes y lugares y —si la versión tiene predecesora— la **página de novedades**. §7 fija sus condiciones.

---

## 5. El seguimiento y la operación

### 5.1 El seguimiento

**El taller, el panel y el gate vuelven a preguntar cada tres segundos** mientras la pestaña está visible, y dejan de hacerlo cuando se oculta. No hay canal empujado ni caché: lo que la pantalla enseña es lo que el fichero dice en ese momento, que es la misma verdad que leería `storymaker estado`. Las pantallas de lectura no sondean, porque una versión publicada no cambia.

Un refresco nunca borra lo que el Autor está haciendo. No cierra un diálogo abierto, no vacía un comentario a medio escribir y no mueve una tarjeta mientras se arrastra.

### 5.2 El estado de una novela

**El estado lo calcula el backend.** El frontend solo lo nombra y le da color:

| Estado | Cuándo | Color |
|---|---|---|
| **En marcha** | El cerrojo está tomado y su proceso vive | azul |
| **Arrancando** | Se acaba de lanzar una acción y el proceso aún no ha tomado el cerrojo | azul |
| **Espera tu decisión** | Hay un gate pendiente | ámbar |
| **Aparcada** | Un gate agotó su *timeout* | ámbar |
| **Detenida** | El cerrojo está tomado y su proceso ya no vive | rojo |
| **Parada por un fallo** | La última ejecución de fase terminó `fallida` | rojo |
| **Terminada** | Hay versión publicada y nada pendiente | verde |
| **En pausa** | Ninguno de los anteriores: se puede continuar | gris |

El estado de cada fase en la línea de fases sale de sus filas de `fase_run`: `en_curso`, `esperando_gate`, `completada`, `fallida`, `aparcada` o `abortada`. Una fase sin filas pero con salida se enseña como completada, con una nota que lo explica. Una fase sin filas y sin salida está pendiente.

### 5.3 Las acciones

| Acción | Se ofrece cuando | Qué hace |
|---|---|---|
| **Encargar** | Siempre, desde el taller | Valida el brief y lanza `storymaker nueva` |
| **Continuar** | En pausa, parada por un fallo o aparcada | Lanza `storymaker continuar` |
| **Decidir** | Espera tu decisión | Lanza `storymaker decidir` con la decisión y el comentario |
| **Reintentar el capítulo** | Parada por un fallo en Escritura | Lanza `storymaker reintentar`, que reabre el capítulo que agotó sus reintentos |
| **Desbloquear** | Detenida | Rompe el cerrojo huérfano y ofrece continuar |
| **Editar filas** | En la pantalla del gate, con gate pendiente | Escribe la edición, sin lanzar nada |
| **Pedir un cambio** | En el lector | Registra la petición (§6) |

**Toda acción responde en el acto.** La pantalla enseña que la acción está lanzada y el seguimiento hace el resto: la novela pasa a «Arrancando» y luego a «En marcha». **Una acción rechazada se cuenta con el motivo del backend**, sin reintento automático: novela ocupada, sin gate que decidir, brief inválido, o reintento que no procede. Las acciones con consecuencias que no se deshacen —abortar y desbloquear— piden confirmación.

---

## 6. La petición de cambio del lector

El lector selecciona un fragmento del capítulo, escribe en lenguaje natural qué quiere cambiar —*«el perro se llama Nala, no Toby»*— y lo envía, con el fragmento, el capítulo y la versión desde los que se pide.

**Lo que el frontend no hace es resolver nada.** La petición abre la Fase 6, que se detiene en su gate, y quien decide es el Autor. Lo que la pantalla devuelve al lector es un acuse: queda registrada, el Autor la revisará. De ahí tres consecuencias:

- **No hay espera ni sondeo en el lector.** La novela cambia cuando aparece una versión nueva en el historial; el Autor ve el gate en su taller.
- **Una selección vacía no se envía.** Sin fragmento, el formulario no se habilita.
- **Un `409` se cuenta tal cual.** Si la novela está ocupada, la petición no se encola.

---

## 7. El modo impresión y `render_visual`

Esta sección es la que hace al frontend parte de un Quality Gate, y todo lo que dice es condición de G5.

**Es un libro, no una página impresa.** El documento se maqueta en A5 con el registro de libro de §8: una **portada** a página completa con el título y la dedicatoria, la **nota del autor** y el **índice** cada uno en su página, **cada capítulo empezando en página nueva** con su número, su título y capitular en el primer párrafo, texto justificado con partición de palabras y sin líneas viudas ni huérfanas, y al final los personajes y lugares y las novedades. Los números de página los pone la impresión, al pie. En pantalla, la misma ruta enseña el documento como una sucesión de páginas.

**Un solo documento y enlaces internos de verdad.** La ruta de impresión no navega: todo está en la misma página, y el índice enlaza por ancla (`#capitulo-7`), no por router.

**Anclas estables, declaradas y feas a propósito.** Las regiones que `render_visual` comprueba se marcan con atributos que no cambian con el estilo:

| Región | Marca |
|---|---|
| Índice de capítulos | `data-render="indice"` |
| Portada con dedicatoria | `data-render="portada"` |
| Ficha de personajes y lugares | `data-render="personajes"` |
| Página de novedades | `data-render="novedades"` |

Que sean atributos, y no clases de CSS ni textos visibles, es deliberado: el contrato tiene que sobrevivir a la maquetación. El documento completo lleva además `data-estado="listo"`, para que quien imprime o juzga no lo haga sobre un estado de carga.

**Ningún módulo fuera de `shared/api` emite una petición de red.** `render_visual` corre con la transacción abierta, sobre una versión candidata que la API no ve, y el navegador que conduce la publicación la sirve interceptando las peticiones. Lo que no pasa por el cliente único no se puede interceptar, y lo juzgado dejaría de ser lo que se publica.

**La hoja de impresión vive en `app/styles`**, y usa el registro de libro de §8, no el del panel.

---

## 8. El diseño visual

La interfaz tiene que parecer un producto, no un esqueleto. Tiene **dos registros visuales**, porque sirve a dos cosas distintas:

- **El panel** —taller, encargo, panel, gate y salidas— es una interfaz de trabajo moderna. Usa una tipografía sin serifa, densidad media y **modo claro y oscuro según el sistema**, con una barra de navegación persistente que lleva al taller y al encargo y dice en qué novela se está. **El tema se elige en la propia barra**: según el sistema, que es el de por defecto, claro u oscuro. Se aplica a toda la aplicación, libro incluido, salvo que el lector haya fijado el fondo del libro en su pestaña «Aa» (§4.6). La impresión no lo sigue: el PDF se maqueta siempre en claro.
- **El libro** —lector, portada, personajes, historial e impresión— tiene tipografía de libro con serifa, medida de línea de lectura y márgenes generosos. La impresión se maqueta en A5.

**La interfaz lleva la marca de la empresa del Autor**: su logo en la barra de navegación y como icono de la pestaña, y su naranja `#ff7932` con el blanco roto `#f5f5f5` como color de acento y de fondo del panel. Donde el naranja no se lee como texto sobre fondo claro, los enlaces usan una variante más oscura del mismo tono. El registro de libro conserva su papel y su tinta: es la novela, no la empresa.

**Los tokens de diseño viven en `app/styles`**: colores, tipografías, espacios, radios y sombras, para los dos modos. Ningún componente escribe un color suelto; todos usan tokens, y así el modo oscuro es una redefinición de tokens y no un segundo juego de estilos.

**El color de estado tiene significado fijo**: azul para lo que trabaja, ámbar —tirando a amarillo, para no confundirse con el naranja de la marca— para lo que espera al Autor, rojo para lo detenido y verde para lo terminado. Siempre va acompañado de su texto, porque el color solo no es accesible.

Las transiciones son breves y sirven para orientarse —una tarjeta que se levanta al arrastrar, una columna que se ilumina al aceptar—, nunca de adorno. Las fuentes de las dos familias se sirven desde el propio origen. La interfaz se usa desde 360 px de ancho: en pantallas estrechas, el tablero se desplaza en horizontal columna a columna.

---

## 9. Contratos de `shared/` y de `entities/`

`shared/` no tiene slices: se organiza por segmentos, y **cada segmento expone su propia API pública** —`shared/api/index.ts`, `shared/ui/index.ts`— en lugar de un `shared/index.ts` único.

| Segmento | Qué contiene | Qué no |
|---|---|---|
| `shared/api` | El cliente único; las funciones de lectura, seguimiento y operación; los tipos de transporte; y los errores tipados (`NoEncontrado`, `NovelaOcupada`, `Rechazada`, `SinRespuesta`, `ErrorDelServidor`) | Ninguna regla de negocio, ninguna decisión sobre qué significa un dato |
| `shared/ui` | El kit: marco de la aplicación, tarjeta, tabla, botón, insignia, pestañas, diálogo, campo de formulario, métrica, barra de progreso, enlace, marca de cambiado y los estados de carga, error y vacío | Nada que sepa qué es un Capítulo o una novela |
| `shared/lib` | Hooks y utilidades sin dominio: carga de un recurso, sondeo, selección de texto, formateo de fechas, cifras y dinero | — |
| `shared/config` | Los constructores de ruta de §3 y la lectura de las dos variables de entorno | — |
| `entities/novela` | Los nombres y colores de los estados de §5.2, los nombres de las fases, la insignia de estado y la línea de fases | Ninguna llamada a la API |

**Los tipos de transporte no se escriben a mano: se derivan del OpenAPI que FastAPI publica.** Un cambio de contrato en el backend rompe la construcción del frontend en lugar de romper la pantalla.

**El error se traduce una sola vez, en `shared/api`.** Cada página decide qué enseña ante un `NoEncontrado` o un `Rechazada`, pero ninguna vuelve a mirar un código HTTP.

---

## 10. Reglas estructurales y cómo se comprueban

Las dos reglas de FSD que sostienen la organización son comprobables sin ejecutar nada:

1. **Un módulo solo importa de capas estrictamente inferiores.** `app → pages → entities → shared`.
2. **Dos slices de la misma capa nunca se importan entre sí.** De ahí los constructores de ruta de §3.

A ellas se suman las reglas de la metodología que este frontend adopta:

- **`entities/novela` existe porque cumple las tres condiciones de extracción** (arq. §16.3): tres pantallas enseñan el estado y la línea de fases, cambian por un motivo propio y su responsabilidad es acotada. **`features/` no se crea**: cada acción la ejerce una sola pantalla.
- **`widgets/` no se usa.**
- **Los assets van junto al código que los usa**; las hojas globales, los tokens y las fuentes, a `app/`.
- **Los ficheros se nombran por dominio**, no por rol técnico.

**Steiger lo verifica e informa, pero no bloquea.** El cliente único, que sí sostiene una puerta, lo comprueba una prueba de repositorio.

---

## 11. Casos de error, en una tabla

| Caso | Qué hace el frontend |
|---|---|
| Novela, versión, capítulo o fase inexistente (`404`) | Pantalla de «no existe» con vuelta al taller. Nunca una página en blanco |
| Novela ocupada al actuar o al pedir un cambio (`409`) | Se dice que hay una ejecución en curso. No se encola ni se reintenta solo |
| Acción que no procede (`422`): brief inválido, sin gate que decidir, abortar fuera de Intake, reintento imposible | Se enseña el motivo del backend; en el encargo, junto a cada campo |
| API caída o sin respuesta | Aviso de que el servidor no responde, con reintento. El sondeo sigue intentándolo sin apilar avisos |
| Novela sin versiones publicadas | Aparece en el taller sin enlace de lectura, con su fase y su estado |
| Versión sin predecesora | El índice no marca capítulos cambiados y la impresión omite la página de novedades |
| Selección de fragmento vacía | El formulario de petición no se habilita |
| Ficha de personaje sin capítulos que enlazar | Se enseña la ficha sin enlaces; la entrada no se oculta |
| Fase sin salida todavía | La pestaña lo dice; no es un error |
| Cerrojo huérfano | La novela sale como detenida y se ofrece desbloquear |

---

## 12. Clases de confianza declaradas

| Pieza | Clase | Gate |
|---|---|---|
| Organización en capas y API pública por segmento (Steiger) | **A** | G1, informa |
| Tipos de transporte derivados del OpenAPI | **A/T** | G1 |
| Constructores de ruta y ausencia de imports entre slices | **A** | G1 |
| Pantallas de operación contra los contratos de la API, con MSW | **T** | G1 |
| Tablero: qué se arrastra, adónde y que nada se decide sin confirmar | **T** | G1 |
| Recorrido completo —encargar, seguir, decidir, leer— sobre el servidor real | **D** | G2 |
| Índice, portada y ficha de personajes renderizan (`render_visual`) | **D** | G5 |
| PDF impreso desde la ruta de lectura | **D** | G5 |
| Cliente único como condición de interceptación | **A** | G5 |
| Acabado visual | **I** | G4 |
| API sin autenticación, con acciones | **U-17** | — |

**No se declara ninguna U nueva.** La operación desde la interfaz agranda U-17, que `verification.md` ya recoge con su nueva mitigación.

---

## 13. Requisitos

Los apartados anteriores son el contrato, y están en prosa porque un contrato necesita decir también **por qué**. Esta tabla es ese mismo contrato en su forma comprobable: **cada fila enuncia una sola cosa y se puede responder con un sí o un no**. Si una fila y su apartado discrepan, manda el apartado.

El identificador `REQ-FE-nn` es estable y **no se reutiliza jamás**: un requisito retirado deja su fila con la nota. El apartado es de dónde se extrae el enunciado y de dónde hereda su clase y su gate (§12). Los ítems son los de [`plan.md`](plan.md), con el prefijo `BE:` cuando los realiza el plan del backend.

### 13.1 La forma, la puesta en marcha y las rutas

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-FE-01 | El frontend no guarda estado de dominio que sobreviva a una recarga: ni copia local del canon, ni almacén global de la novela; solo las preferencias de lectura, desde un único módulo | §1 | IMP-32, IMP-56 |
| REQ-FE-02 | **Toda ruta de lectura lleva el número de versión** | §1, §3 | IMP-07, IMP-08 |
| REQ-FE-03 | En desarrollo, `vite dev` sirve la aplicación y alcanza la API por el proxy de Vite en `/api` | §2.1 | IMP-01 |
| REQ-FE-04 | Fuera de desarrollo, **FastAPI sirve el `dist/` construido** desde un solo origen | §2.1 | IMP-26, BE:P-136 |
| REQ-FE-05 | Solo hay dos variables de configuración y **ninguna es un secreto** | §2.2 | IMP-08 |
| REQ-FE-06 | Los alias de importación se declaran **con el mismo mapa** en `tsconfig.json` y en `vite.config.ts` | §2.2 | IMP-03 |
| REQ-FE-07 | El mapa de rutas vive entero en `app/router.tsx` | §3 | IMP-07, IMP-44 |
| REQ-FE-08 | *Retirado el 2026-09-24.* Decía que `/novelas/:id` redirigía a la última versión publicada; esa ruta es ahora el panel de la novela (REQ-FE-62) | §3 | — |
| REQ-FE-09 | Para enlazar a otra pantalla, una página usa un constructor de URL de `shared/config` y **no importa nada de la slice vecina** | §3 | IMP-08 |

### 13.2 Las pantallas

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-FE-10 | Los estados de carga, de error y de vacío son **parte del contrato** de cada pantalla | §4 | IMP-11, IMP-28 |
| REQ-FE-11 | El taller enseña una tarjeta por novela de `proyectos/`, con título, fase en curso y versiones publicadas | §4.1 | IMP-13, IMP-39 |
| REQ-FE-12 | Una novela sin ninguna versión publicada aparece igualmente, pero **sin enlace de lectura** | §4.1 | IMP-39 |
| REQ-FE-13 | Un directorio sin novelas se anuncia como vacío y **no como un error** | §4.1 | IMP-39 |
| REQ-FE-14 | El índice lista los capítulos del manifiesto en orden, con su número y su título | §4.6 | IMP-14 |
| REQ-FE-15 | El índice **marca los capítulos cambiados**, y la marca sale del endpoint de diff | §4.6 | IMP-14, IMP-25 |
| REQ-FE-16 | La vista de capítulo muestra el texto de esa versión, con anterior, siguiente y vuelta al índice | §4.6 | IMP-15 |
| REQ-FE-17 | La selección de fragmento y la petición de cambio viven en `pages/reading` | §4.6 | IMP-20 |
| REQ-FE-18 | Cada entrada de la ficha de personajes **enlaza a los capítulos en los que aparece**, con la versión de la ruta | §4.7 | IMP-16, BE:P-110 |
| REQ-FE-19 | La portada lleva el título, la **dedicatoria** con su ocasión y la **nota del autor** con las Licencias | §4.8 | IMP-17, BE:P-110 |
| REQ-FE-20 | El historial lista las versiones con fecha y puntuación, y para dos cualesquiera enseña qué capítulos cambian | §4.9 | IMP-18 |
| REQ-FE-21 | Desde el historial se abre cualquier versión anterior | §4.9 | IMP-18 |
| REQ-FE-22 | `print` es un solo documento con portada, nota del autor, índice, capítulos, ficha y —si hay predecesora— novedades, en ese orden | §4.10 | IMP-22 |

### 13.3 La petición de cambio

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-FE-23 | La petición envía el fragmento seleccionado, el capítulo, la versión y el texto | §6 | IMP-20 |
| REQ-FE-24 | El frontend **no resuelve nada** y devuelve un acuse, no un resultado | §6 | IMP-21 |
| REQ-FE-25 | El lector no espera ni sondea el resultado de su petición | §6 | IMP-21 |
| REQ-FE-26 | Una selección vacía no habilita el formulario | §6 | IMP-20 |
| REQ-FE-27 | Un `409` se cuenta tal cual y la petición **no se encola** | §6 | IMP-21 |

### 13.4 El modo impresión, `shared/` y la estructura

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-FE-28 | La ruta de impresión **no navega**: el índice enlaza por ancla | §7 | IMP-24 |
| REQ-FE-29 | Las cuatro regiones que `render_visual` comprueba se marcan con `data-render` | §7 | IMP-23 |
| REQ-FE-30 | **Ningún módulo fuera de `shared/api` emite una petición de red** | §7 | IMP-27, IMP-09 |
| REQ-FE-31 | La hoja `@media print` vive en `app/styles` | §7 | IMP-06 |
| REQ-FE-32 | Cada segmento de `shared/` expone su propia API pública | §9 | IMP-02 |
| REQ-FE-33 | `shared/api` no contiene ninguna regla de negocio | §9 | IMP-09, IMP-35 |
| REQ-FE-34 | `shared/ui` no contiene nada que sepa qué es un Capítulo o una novela | §9 | IMP-11, IMP-37 |
| REQ-FE-35 | Los tipos de transporte **se derivan del OpenAPI** | §9 | IMP-05 |
| REQ-FE-36 | El error se traduce una sola vez en `shared/api`, y **ninguna página mira un código HTTP** | §9 | IMP-10, IMP-35 |
| REQ-FE-37 | Un módulo solo importa de capas estrictamente inferiores: `app → pages → entities → shared` | §10 | IMP-02, IMP-04 |
| REQ-FE-38 | Dos slices de la misma capa nunca se importan entre sí | §10 | IMP-08, IMP-04 |
| REQ-FE-39 | *Retirado el 2026-09-24.* Decía que ni `features/` ni `entities/` se creaban; `entities/novela` cumple ahora las tres condiciones de extracción (REQ-FE-90) | §10 | — |
| REQ-FE-40 | `widgets/` no se usa | §10 | IMP-02 |
| REQ-FE-41 | Los assets van junto al código que los usa; no hay carpeta `assets/` de primer nivel | §10 | IMP-06 |
| REQ-FE-42 | Los ficheros se nombran por dominio y no por rol técnico | §10 | IMP-02 |
| REQ-FE-43 | Steiger **informa y no bloquea** | §10 | IMP-04 |

### 13.5 Errores, comprobación y alcance

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-FE-44 | Un `404` lleva a una pantalla de «no existe» con vuelta al taller, **nunca a una página en blanco** | §11 | IMP-10 |
| REQ-FE-45 | Con la API caída se avisa y se ofrece reintento; **nada se cachea para fingir que sigue viva** | §11 | IMP-10, IMP-32 |
| REQ-FE-46 | Una versión sin predecesora no marca capítulos cambiados y omite la página de novedades | §11 | IMP-25 |
| REQ-FE-47 | Una ficha sin capítulos que enlazar se enseña sin enlaces; la entrada **no se oculta** | §11 | IMP-16 |
| REQ-FE-48 | El recorrido completo sobre el servidor real se demuestra y deja acta | §12 | IMP-29 |
| REQ-FE-49 | El PDF de ejemplo se imprime con `page.pdf()` desde la ruta de impresión | §12 | IMP-30, BE:P-94 |
| REQ-FE-50 | La interfaz va en castellano, **sin capa de internacionalización** | §14 | IMP-31 |
| REQ-FE-51 | Los identificadores de este apartado no se repiten ni se reutilizan, y todo ítem citado existe en el plan | §13 | IMP-33, BE:P-139 |

### 13.6 El taller y el encargo

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-FE-52 | El taller es un tablero con cinco columnas —Encargo, Investigación, Trama, Escritura y Publicación—, y cada novela en curso es una tarjeta en la columna de su fase actual | §4.1 | IMP-39, IMP-55 |
| REQ-FE-53 | La tarjeta enseña título, homenajeado, estado con su insignia, capítulos aprobados sobre el total, coste y, si espera, qué gate | §4.1 | IMP-39, IMP-34 |
| REQ-FE-54 | Solo se arrastran tarjetas con gate pendiente distinto del de Regeneración, y solo a la columna siguiente o a la suya | §4.1 | IMP-39 |
| REQ-FE-55 | Soltar en la columna siguiente propone aprobar y en la suya propone rehacer; **nada se decide sin confirmar** en un diálogo con el resumen del gate | §4.1 | IMP-39 |
| REQ-FE-56 | Cada gesto del tablero tiene su alternativa por botones en la tarjeta | §4.1 | IMP-39 |
| REQ-FE-57 | Desde el taller se abre el encargo de una novela nueva | §4.1 | IMP-39 |
| REQ-FE-58 | El encargo es un formulario por los bloques del `Brief`, con los obligatorios marcados | §4.2 | IMP-40 |
| REQ-FE-59 | El encargo puede partir de un brief de `ejemplos/` | §4.2 | IMP-40, BE:P-162 |
| REQ-FE-60 | El brief lo valida el backend antes de lanzar, y cada error se enseña junto a su campo | §4.2 | IMP-40, BE:P-162 |
| REQ-FE-61 | Al lanzar se elige el nombre y con gates —por defecto— o en batch, y lanzar lleva al panel | §4.2 | IMP-40 |

### 13.7 El panel, el gate y las salidas

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-FE-62 | El panel enseña el estado de la novela y la línea de las seis fases, cada una con su estado, coste, tokens y duración, y enlazada a su salida | §4.3 | IMP-41, IMP-34, BE:P-160 |
| REQ-FE-63 | La actividad se enseña interpretada —fase, capítulo, intento, última decisión e incidencias recientes— y el registro del proceso solo plegado | §4.3 | IMP-41, BE:P-160 |
| REQ-FE-64 | El panel enseña la rejilla de capítulos con su estado e intentos, el consumo acumulado y las versiones publicadas | §4.3 | IMP-41 |
| REQ-FE-65 | El panel solo ofrece las acciones que el estado admite | §4.3, §5.3 | IMP-41 |
| REQ-FE-66 | La pantalla del gate enseña qué fase espera, desde cuándo, su resumen y el enlace a la salida completa | §4.4 | IMP-42, BE:P-160 |
| REQ-FE-67 | En Intake, las preguntas del entrevistador se contestan en casillas, y contestar es rehacer con las respuestas como comentario | §4.4 | IMP-42 |
| REQ-FE-68 | Aprobar y rehacer con comentario se ofrecen en todos los gates; abortar, solo en Intake y con confirmación | §4.4 | IMP-42, BE:P-165 |
| REQ-FE-69 | Editar abre el editor de hechos, personajes, escenarios y glosario, guarda cada cambio al momento, y la pantalla **nunca envía la decisión `editar`** | §4.4 | IMP-42, BE:P-162 |
| REQ-FE-70 | Un hecho de un corpus sellado no se ofrece como editable | §4.4 | IMP-42, BE:P-160 |
| REQ-FE-71 | El gate de Regeneración enseña la petición que lo abrió y sus candidatos con su alcance, y se decide en su pantalla | §4.4 | IMP-42, BE:P-166 |
| REQ-FE-72 | Cada fase enseña sus ejecuciones —estado, tokens, coste, inicio y duración— y las decisiones de sus gates | §4.5 | IMP-43, BE:P-161 |
| REQ-FE-73 | La salida de Encargo enseña el brief, los datos del encargo con tipo, obligatoriedad y origen, y el texto en cuarentena | §4.5 | IMP-43, BE:P-161 |
| REQ-FE-74 | La salida de Investigación agrupa los hechos por dimensión, con su firmeza como única etiqueta, lo que no dice la cita, cita y fuentes enlazadas, su recuento, las entidades y el sello | §4.5 | IMP-43, BE:P-161 |
| REQ-FE-75 | La salida de Trama enseña la obra, los personajes con arcos e hitos, relaciones, escenarios, Licencias, glosario y la escaleta capítulo → escena → beat con anclajes | §4.5 | IMP-43, BE:P-161 |
| REQ-FE-76 | La salida de Escritura enseña por capítulo sus intentos, las incidencias de cada intento y el texto de cualquiera | §4.5 | IMP-43, BE:P-161 |
| REQ-FE-77 | La salida de Publicación enseña las versiones con la rúbrica del juez por criterio y el manifiesto | §4.5 | IMP-43, BE:P-161 |
| REQ-FE-78 | La salida de Regeneración enseña las peticiones, lo que cambió cada una y las ediciones humanas | §4.5 | IMP-43, BE:P-161 |
| REQ-FE-79 | Una fase sin salida todavía lo dice, y no es un error | §4.5 | IMP-43 |

### 13.8 El seguimiento, la operación y el diseño

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-FE-80 | Taller, panel y gate vuelven a preguntar cada tres segundos con la pestaña visible, y dejan de hacerlo cuando se oculta | §5.1 | IMP-36 |
| REQ-FE-81 | Un refresco no cierra un diálogo, no vacía un comentario y no mueve una tarjeta que se arrastra | §5.1 | IMP-36, IMP-39 |
| REQ-FE-82 | El estado de una novela y el de cada fase los calcula el backend; el frontend solo los nombra y colorea | §5.2 | IMP-34, BE:P-160 |
| REQ-FE-83 | Una fase sin filas en `fase_run` pero con salida se enseña como completada, con una nota que lo explica | §5.2 | IMP-34, BE:P-160 |
| REQ-FE-84 | Toda acción responde en el acto, y la pantalla dice que está lanzada sin esperar al proceso | §5.3 | IMP-35, BE:P-162 |
| REQ-FE-85 | Una acción rechazada se cuenta con el motivo del backend, sin reintento automático | §5.3 | IMP-35 |
| REQ-FE-86 | Abortar y desbloquear piden confirmación, y desbloquear solo se ofrece con la novela detenida | §5.3 | IMP-41, IMP-42 |
| REQ-FE-87 | Reintentar el capítulo se ofrece cuando la novela se paró por un fallo en Escritura | §5.3 | IMP-41, BE:P-162 |
| REQ-FE-88 | La interfaz tiene dos registros visuales —panel sin serifa con modo claro y oscuro según el sistema, y libro con serifa— y la impresión usa el de libro | §8 | IMP-38, IMP-45 |
| REQ-FE-89 | Los colores, tipografías, espacios, radios y sombras son tokens de `app/styles`, y ningún componente escribe un color suelto | §8 | IMP-38 |
| REQ-FE-90 | `entities/novela` existe y no llama a la API; `features/` no se crea | §10 | IMP-34, IMP-02 |
| REQ-FE-91 | El color de estado tiene significado fijo y siempre va con su texto | §8 | IMP-34 |
| REQ-FE-92 | La interfaz se usa desde 360 px de ancho | §8 | IMP-38 |

### 13.9 El encargo por conversación

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-FE-93 | El encargo se abre en modo conversación: nombre del homenajeado y la novela contada con tus palabras | §4.2 | IMP-47 |
| REQ-FE-94 | En modo conversación, la descripción viaja como `descripcion` del encargo, se lanza siempre con gates y se llega a la pantalla del gate | §4.2 | IMP-47, BE:P-180 |
| REQ-FE-95 | El formulario completo sigue disponible como segundo modo, con ejemplos y la elección de gates o batch | §4.2 | IMP-47 |
| REQ-FE-96 | En Intake, el gate enseña la conversación: descripción, rondas anteriores con sus respuestas y preguntas nuevas con su casilla | §4.4 | IMP-48, BE:P-181 |
| REQ-FE-97 | Tras contestar, la pantalla del gate se queda, dice que el entrevistador está pensando y enseña sola la ronda siguiente | §4.4 | IMP-48 |
| REQ-FE-98 | Sin preguntas pendientes, el gate de Intake lo dice, enseña el brief cerrado y propone aprobar | §4.4 | IMP-48, BE:P-181 |
| REQ-FE-99 | Los dos modos del encargo ofrecen una casilla de investigación exhaustiva, que viaja como modo de investigación del encargo | §4.2 | IMP-50, BE:P-182 |
| REQ-FE-100 | Los lugares se titulan con su nombre corto, y su descripción completa va debajo; la impresión y la salida de la Trama usan el mismo nombre | §4.7 | IMP-51, BE:P-183 |
| REQ-FE-101 | Cada versión publicada ofrece descargar su PDF desde el panel, el índice de lectura y la salida de la Publicación, con la URL construida en `shared/api` | §4.3 | IMP-52, BE:P-184 |
| REQ-FE-102 | La ruta de impresión se maqueta como un libro A5: portada a página completa, nota del autor e índice en su página, cada capítulo en página nueva con capitular, texto justificado sin viudas ni huérfanas | §7 | IMP-53 |
| REQ-FE-103 | En el gate de Regeneración el Autor elige un candidato y escribe su valor nuevo, precargado con el actual; aprobar envía `<objeto>:<fila_id> <campo>=<valor>` | §4.4 | IMP-54, BE:P-186 |
| REQ-FE-104 | Las novelas publicadas sin trabajo en marcha, y las que están en Regeneración, van en un listado bajo el tablero con título, homenajeado, versiones, gasto, última actividad y enlace a leer la última versión; si esperan en el gate de Regeneración, enlazan a él | §4.1 | IMP-55 |
| REQ-FE-105 | Las pantallas del registro de libro llevan el botón «Aa», con tamaño de letra en cinco pasos, tres fuentes, tres interlineados, negrita y fondo del libro, aplicados en vivo y recordados entre visitas, sin afectar a la impresión | §4.6 | IMP-56, IMP-57 |
| REQ-FE-107 | La barra permite elegir el tema de la aplicación —sistema, claro u oscuro—, y el fondo del libro puede fijarse aparte, en claro u oscuro, sea cual sea el tema de la aplicación | §8, §4.6 | IMP-57 |
| REQ-FE-106 | Ninguna pantalla enlaza a la ruta de impresión; la novela en papel es el PDF | §4.6 | IMP-56 |

---

## 14. Lo que este documento deja fuera a propósito

- **La forma técnica exacta** —qué componente, qué biblioteca, en qué orden— va en [`plan.md`](plan.md).
- **El backend entero**, incluida la forma interna de los endpoints que aquí se consumen y la del lanzador de procesos.
- **Ramificar y evaluar**, que se quedan en la CLI (arq. §16.5).
- **La internacionalización**: la novela y la interfaz van en castellano.
- **La autenticación**, que no existe por decisión declarada en U-17.
- **Las anclas de procedencia**: §11e de la arquitectura acota `anclas_de_procedencia` al backend, y el frontend se traza por `inventario_del_plan` y `requisitos_declarados`.

---

## 15. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | §4.5: cada hecho lleva **una sola etiqueta**, su firmeza, y lo que no dice la cita; REQ-FE-74 se reescribe | Petición del Autor; el detalle vive en la spec del gate de Investigación |
| 2026-09-24 | §4.5: la salida de Investigación enseña **la firmeza** de cada hecho, con el estado declarado solo cuando difiere; REQ-FE-74 se reescribe. El detalle vive en la spec del gate de Investigación | Se propaga §7 de la arquitectura: el verificador ya no reescribe el estado y la firmeza se calcula al leer |
| 2026-09-24 | §4.6: la pestaña «Aa» gana **interlineado, negrita y fondo del libro**. §8: **el tema de la aplicación se elige en la barra**, y el del libro puede fijarse aparte. §1 habla ya de preferencias de presentación. REQ-FE-105 cambia; entra REQ-FE-107 | Petición del Autor: poder tener la aplicación en oscuro y el libro en claro |
| 2026-09-24 | §4.6: **ajustes de lectura** —tamaño y fuente, en la pestaña «Aa»— y el lector **deja de ofrecer imprimir**. §1 admite guardar en el navegador las preferencias de lectura, y solo ellas. REQ-FE-01 cambia; entran REQ-FE-105 y REQ-FE-106 | Petición del Autor: leer como en un Kindle, y quitar un «Imprimir» que duplicaba el PDF |
| 2026-09-24 | §4.1: **las novelas publicadas salen del tablero** a un listado debajo, y el tablero queda con cinco columnas. REQ-FE-52 cambia y entra REQ-FE-104 | Petición del Autor: la sexta columna estiraba el tablero hacia la derecha |
| 2026-09-24 | §4.4: en el gate de Regeneración **el Autor elige el candidato** y escribe el valor nuevo; aprobar envía `<objeto>:<fila_id> <campo>=<valor>`. Entra REQ-FE-103 | Petición del Autor: el backend deja de buscar con el texto del comentario al aprobar y aplica la fila elegida |
| 2026-09-24 | §7: la ruta de impresión **se maqueta como un libro**. Entra REQ-FE-102 | El PDF pasa a imprimirse desde esta ruta, y su maqueta es lo que el Autor recibe |
| 2026-09-24 | §4.3: las versiones publicadas ofrecen **descargar su PDF**. Entra REQ-FE-101 | El PDF se generaba y la interfaz no llevaba a él |
| 2026-09-24 | §4.7: los lugares se titulan con **su nombre corto** y la descripción va debajo. Entra REQ-FE-100 | Petición del Autor |
| 2026-09-24 | §4.2: el encargo ofrece **investigación exhaustiva** en los dos modos. Entra REQ-FE-99 | El modo exhaustivo de arq. §4, Fase 2, se elige al crear la novela |
| 2026-09-24 | §4.2: **el encargo empieza por una conversación con el entrevistador** —nombre del homenajeado y la novela contada con tus palabras, siempre con gates— y el formulario completo pasa a segundo modo. §4.4: el gate de Intake es **una conversación** con rondas, estado de «pensando» y brief cerrado. Entran REQ-FE-93 a REQ-FE-98 | Petición del Autor: que el encargo lo haga el primer agente, como describe la Fase 1. El formulario completo dejaba al entrevistador sin nada que preguntar |
| 2026-09-24 | §8: la interfaz lleva **la marca de la empresa del Autor** —logo en la barra y en la pestaña, naranja `#ff7932` y blanco roto `#f5f5f5`—, y el ámbar de los estados tira a amarillo para no confundirse con ella | Petición del Autor al ver la interfaz |
| 2026-09-24 | **Reescrita entera**: la interfaz opera el arnés. Entran el taller como **tablero por fases tipo Jira**, donde arrastrar una tarjeta aprueba o rehace su gate tras confirmar; el encargo; el panel de la novela; la pantalla del gate con su editor de filas; la salida de cada fase; el seguimiento por sondeo; las acciones y sus estados; y **§8, el diseño visual**, con dos registros —panel y libro— y tokens en `app/styles`. Aparece `entities/novela`. Se retiran REQ-FE-08 (la redirección, ahora es el panel) y REQ-FE-39 (`entities/` ya se crea); entran REQ-FE-52 a REQ-FE-92. La antigua §11, que contaba las costuras ya cerradas, se retira: su historia queda en este registro | Decisión del Autor tras ver la interfaz de lectura: «súper pobre», sin todas las novelas y sin forma de lanzar, seguir ni consultar la salida de cada fase. La arquitectura lo recogió en §16.5, y este documento baja de ahí. Una spec que ha cambiado de alcance se reescribe, no se remienda |
| 2026-09-24 | §2.1 fija que la API vive bajo `/api` también cuando FastAPI sirve la aplicación | Aplicación y API comparten origen y las dos tienen rutas `/novelas/…` |
| 2026-09-24 | Las anclas de procedencia se declaran fuera de alcance | §11e de la arquitectura acota `anclas_de_procedencia` al backend |
| 2026-09-24 | Cuatro requisitos se reasignan a los ítems que de verdad los comprueban: REQ-FE-01 y REQ-FE-45 a IMP-32, REQ-FE-05 a IMP-08 y REQ-FE-51 a IMP-33 | La tercera pasada de trazabilidad encontró ítems cuyo criterio de hecho miraba otra cosa |
| 2026-09-23 | Las cinco costuras con el backend —paratexto, ficha versionada, quién sirve la aplicación, la versión candidata legible para `render_visual`, y las pantallas `library` y `print`— quedan cerradas en la arquitectura y en la spec del backend | Una spec que enumera lo que le falta al de al lado sirve una vez, para pedirlo |
| 2026-09-23 | Entran los 51 requisitos `REQ-FE-nn`, derivados de los propios apartados | El contrato estaba escrito para leerse y no para comprobarse |
| 2026-09-23 | Versión inicial | Fijar el contrato del frontend: las pantallas de lectura, el mapa de rutas, la petición de cambio y las condiciones del modo impresión |
