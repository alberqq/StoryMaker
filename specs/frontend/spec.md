# Spec — Frontend de StoryMaker

Qué construye el frontend, qué enseña cada pantalla, de dónde saca cada dato, qué hace cuando algo va mal y con qué se comprueba que hace lo que dice.

Deriva de [`architecture.md`](../../docs/architecture.md), que es la fuente de verdad —§4 para las fases 5 y 6, §16.1 para la pila y §16.3 para la organización en Feature-Sliced Design—, y de [`verification.md`](../../docs/verification.md), de donde toma el marco T·A·I·D·U y los Quality Gates. **Si algo de este documento contradice a la arquitectura, manda la arquitectura.** La forma técnica exacta —qué fichero, qué componente, en qué orden se construye— no vive aquí, sino en [`plan.md`](plan.md).

**Alcance.** Todo `frontend/src/`: las pantallas, el cliente de la API, el kit de componentes y el modo impresión del que sale el PDF. Queda fuera el backend, que tiene su propia spec en [`specs/backend/spec.md`](../backend/spec.md) y cuya API este documento consume sin discutir; queda fuera también el PDF como artefacto, porque lo imprime Playwright desde el backend, aunque lo que imprime sea una ruta de este frontend.

---

## 1. La forma del frontend en una página

El frontend es **una aplicación React construida con Vite y organizada en Feature-Sliced Design v2.1**, con el juego mínimo de capas que la propia metodología recomienda: `app/`, `pages/` y `shared/`. No tiene servidor propio, no guarda nada y no decide nada.

Tres afirmaciones lo gobiernan, y conviene tenerlas delante al leer el resto:

1. **El frontend no tiene verdad propia.** Todo lo que enseña sale de la API, y la API lee el fichero SQLite de la novela. No hay estado de dominio en el cliente que sobreviva a una recarga, ni una copia local del canon, ni un almacén global de la novela. Es el mismo razonamiento que en el backend hace que el canon mande sobre el texto: una segunda copia de la verdad es una copia que acaba divergiendo, y aquí la única defensa contra eso es no tenerla.
2. **Se lee una Versión, no «la novela».** Un Capítulo no existe por sí solo: existe dentro de un manifiesto, que es la lista ordenada de qué `capitulo_version` la componen. Por eso **toda ruta de lectura lleva el número de versión**, y una URL sin versión no resulta incómoda ni ambigua: es incorrecta, porque no identifica ningún texto.
3. **La ruta que lee el lector es la que se imprime y la que se juzga.** El PDF sale de imprimirla con `page.pdf()` de Playwright, y `render_visual` la mira dentro de `PublishVersion`, con la transacción todavía abierta. El frontend es, por tanto, **la única pieza del repositorio fuera del backend que puede impedir una publicación**: si el índice, la portada o la ficha de personajes no renderizan, G5 no deja pasar la versión.

```text
frontend/src/
├─ app/
│  ├─ providers/       proveedores de la aplicación
│  ├─ router.tsx       el mapa de rutas de §3, y el único sitio donde vive
│  ├─ styles/          estilos globales, fuentes y la hoja de @media print
│  └─ main.tsx         punto de entrada
├─ pages/
│  ├─ library/         listado de novelas del directorio proyectos/
│  ├─ reading/         lector, índice de capítulos, navegación,
│  │                   selección de fragmento y petición de cambio
│  ├─ characters/      fichas de personajes y lugares
│  ├─ cover/           portada, dedicatoria y nota del autor
│  ├─ versions/        historial, diff de manifiestos y novedades
│  └─ print/           la novela entera en una página, para PDF y render_visual
└─ shared/
   ├─ api/             cliente de la API y tipos de transporte
   ├─ ui/              kit de componentes
   ├─ lib/             utilidades y hooks
   └─ config/          rutas y variables de entorno
```

`pages/library/` y `pages/print/` son las dos pantallas que la arquitectura añadió a §16.3 al escribirse esta spec, y cada una nace de una decisión ya tomada: la primera porque el directorio es el registro y alguien tiene que enseñar esa lista, la segunda porque el PDF se imprime desde la ruta de lectura y la impresora pide la novela entera en un documento mientras el lector la pide capítulo a capítulo.

---

## 2. Puesta en marcha y configuración

### 2.1 Cómo se sirve

| Escenario | Quién sirve la aplicación | Quién sirve la API | Por qué |
|---|---|---|---|
| Desarrollo | `vite dev` | FastAPI en otro puerto, alcanzado por el **proxy de Vite** en `/api` | Recarga en caliente sin pagar CORS |
| Demo, impresión y `render_visual` | **FastAPI**, sirviendo el `dist/` construido | FastAPI, el mismo proceso | Un solo origen |

**En todo lo que no es desarrollo, el frontend lo sirve FastAPI desde su construcción estática.** Lo declara §16.4 de la arquitectura. La alternativa —dejar el servidor de Vite levantado al lado— obligaría a que el navegador que Playwright conduce supiera de dos orígenes y a que la publicación dependiera de un segundo proceso vivo, justo cuando ese mismo apartado acaba de argumentar que nada de una novela debe vivir en dos sitios. Con un solo origen, la URL que abre `render_visual`, la que imprime el PDF y la que teclea el lector son literalmente la misma.

### 2.2 Configuración

Solo hay dos variables, y ninguna es un secreto: **este frontend no tiene credenciales que guardar**, porque la API de lectura no lleva autenticación (riesgo aceptado U-17).

| Clave | Valor por defecto | Para qué |
|---|---|---|
| `VITE_API_URL` | vacío, es decir, el mismo origen | Base del cliente de la API; solo se rellena en desarrollo |
| `VITE_BASE_PATH` | `/` | Prefijo de rutas cuando FastAPI monta la aplicación bajo un camino |

Los alias de importación —`@/app`, `@/pages`, `@/shared`— se declaran a la vez en `tsconfig.json` y en `vite.config.ts`, para que el resolutor de TypeScript y el de Vite no puedan discrepar. Steiger lee ese mismo mapa.

---

## 3. El mapa de rutas

| Ruta | Página | De dónde saca los datos | Requisito |
|---|---|---|---|
| `/` | `library` | `GET /novelas` | — |
| `/novelas/:id` | redirección | `GET /novelas/{id}` → última versión publicada | — |
| `/novelas/:id/v/:n` | `reading`, índice | `GET /novelas/{id}/versiones/{n}` | LEC-02 |
| `/novelas/:id/v/:n/capitulos/:k` | `reading`, capítulo | `GET /novelas/{id}/versiones/{n}/capitulos/{k}` | LEC-02 |
| `/novelas/:id/v/:n/portada` | `cover` | `GET /novelas/{id}/versiones/{n}` | LEC-05 |
| `/novelas/:id/v/:n/personajes` | `characters` | `GET /novelas/{id}/versiones/{n}/personajes` | LEC-03, LEC-04 |
| `/novelas/:id/versiones` | `versions` | `GET /novelas/{id}` y `GET /novelas/{id}/versiones/{a}/diff/{b}` | LEC-09, LEC-10 |
| `/novelas/:id/v/:n/imprimir` | `print` | Todo lo anterior, de la versión `n` | ENT-06, LEC-09 |

**El mapa vive entero en `app/router.tsx`, y las páginas no se conocen entre sí.** Para enlazar a otra pantalla, una página llama a un constructor de URL de `shared/config/rutas.ts` —`rutaCapitulo(id, n, k)`— en lugar de importar nada de la slice vecina. No es una precaución estética: es la manera de que la ficha de personajes pueda enlazar al capítulo donde aparece cada entrada sin que `pages/characters` importe de `pages/reading`, que es exactamente lo que la segunda regla de FSD prohíbe y Steiger detecta.

---

## 4. Las seis pantallas

Cada una declara qué enseña, de dónde sale y qué hace cuando el dato no está. Los estados de carga, de error y de vacío **son parte del contrato**, no un adorno: `render_visual` juzga un render, y un render que enseña un esqueleto de carga eterno es un render roto.

### 4.1 `pages/library` — el listado de novelas

Enseña una fila por fichero de `proyectos/`, con el título, la fase en curso y el número de versiones publicadas, tal como los devuelve `GET /novelas`. Una novela sin ninguna versión publicada aparece igualmente, pero sin enlace de lectura: lo que se puede leer es una versión, y todavía no hay ninguna.

Es la única pantalla que no cuelga de una versión, y por eso es también la única que puede estar legítimamente vacía: un directorio sin novelas se anuncia como tal y no como un error.

### 4.2 `pages/reading` — el lector

Es la pantalla principal y tiene dos vistas sobre la misma slice:

- **El índice**, que lista los capítulos del manifiesto en orden, con su número y su título, y **marca los que cambiaron respecto de la versión anterior** cuando la hay (LEC-09). La marca sale de `GET /novelas/{id}/versiones/{a}/diff/{b}`, no de comparar textos en el cliente: el diff es un `JOIN` entre dos manifiestos y ya está resuelto en el backend.
- **El capítulo**, que muestra el texto tal como esa versión lo fija, con navegación a anterior y siguiente y vuelta al índice.

Sobre el texto del capítulo se ejercen **la selección de fragmento y la petición de cambio** (§5). Viven aquí y no en una slice propia porque solo se ejercen aquí, que es la regla de extracción de FSD aplicada al pie de la letra: el día en que el historial de versiones ofrezca la misma acción, y solo ese día, se extraerá a `features/change-request/`.

### 4.3 `pages/characters` — la ficha de personajes y lugares

Enseña las fichas que salen de la biblia de la obra: personajes con su tipo, sus rasgos y su relación con el homenajeado, y escenarios con su lugar de época. **Cada entrada enlaza a los capítulos en los que aparece** (LEC-04), y ese enlace se construye con el número de versión que la ruta lleva puesto, porque un capítulo fuera de un manifiesto no es una dirección válida.

La ficha **cuelga de una versión, no de la novela**, y por eso el endpoint que la sirve lleva el número de versión: el canon es vivo, pero «los capítulos en los que aparece» solo tiene respuesta dentro de un manifiesto.

### 4.4 `pages/cover` — portada, dedicatoria y nota del autor

Tres piezas, y las tres son paratexto de la obra: el **título** con su tratamiento de portada, la **dedicatoria personalizada** al homenajeado con su ocasión —la jubilación, el aniversario, la despedida— y la **nota del autor**, que declara qué es histórico, qué es ficción y qué Licencias se tomaron.

La nota del autor no la pide ningún requisito de `REQUIREMENTS.md`, y aun así entra: la ontología la declara como el paratexto de la Transparencia, y el sistema lleva las Licencias declaradas en `canon_licencia` desde Plotting. Enseñarlas cuesta una consulta y es lo que convierte la trazabilidad en algo que el lector ve.

### 4.5 `pages/versions` — el historial

Lista las versiones publicadas con su fecha y su puntuación del juez, y para dos cualesquiera enseña **qué capítulos cambian**, que es lo que devuelve el endpoint de diff. Desde aquí se abre cualquier versión anterior, que sigue entera y legible: la versión previa se conserva por construcción (LEC-10), y esta pantalla es la prueba visible de ello.

### 4.6 `pages/print` — la novela entera en una página

Un único documento con, en este orden: portada y dedicatoria, nota del autor, índice, los capítulos del manifiesto, la ficha de personajes y lugares y —si la versión tiene predecesora— la **página de novedades** con lo que cambió. Es lo que Playwright imprime y lo que `render_visual` juzga, y §6 fija sus condiciones.

---

## 5. La petición de cambio del lector

El lector selecciona un fragmento del capítulo, escribe en lenguaje natural qué quiere cambiar —*«el perro se llama Nala, no Toby»*— y lo envía. El frontend hace `POST /novelas/{id}/cambios` con el fragmento seleccionado, el capítulo y la versión desde los que se pide, y el texto de la petición.

**Lo que el frontend no hace es resolver nada.** No busca el hecho, no toca el canon y no promete un resultado. La petición abre la Fase 6, que se detiene en su gate, y quien decide es el Autor con el recuento de capítulos afectados delante. Así que lo que la pantalla devuelve al lector es un acuse: queda registrada, el Autor la revisará. Prometer más sería mentir sobre una máquina que a propósito no avanza sola.

De ahí tres consecuencias de interfaz:

- **No hay espera ni sondeo.** El frontend no se queda mirando si el gate se resolvió; la novela cambia cuando aparece una versión nueva en el historial.
- **Una selección vacía no se envía.** El fragmento es lo que hace resoluble la petición por búsqueda semántica; sin él, el formulario no se habilita.
- **Un `409` se cuenta tal cual.** Si la novela está ocupada —hay una invocación en curso—, la petición no se encola: se rechaza y se pide reintentar más tarde. Encolarla sería crear ese segundo lugar donde vive el estado que §16.4 de la arquitectura descarta.

---

## 6. El modo impresión y `render_visual`

Esta sección es la que hace al frontend parte de un Quality Gate, y todo lo que dice es condición de G5.

**Un solo documento y enlaces internos de verdad.** La ruta de impresión no navega: todo está en la misma página y el índice enlaza por ancla (`#capitulo-7`), no por router. Es lo que permite que el PDF conserve los enlaces internos que necesitan el índice navegable y la página de novedades, porque en papel no hay historia de navegación que seguir.

**Anclas estables, declaradas y feas a propósito.** Las regiones que `render_visual` comprueba se marcan con atributos que no cambian con el estilo:

| Región | Marca |
|---|---|
| Índice de capítulos | `data-render="indice"` |
| Portada con dedicatoria | `data-render="portada"` |
| Ficha de personajes y lugares | `data-render="personajes"` |
| Página de novedades | `data-render="novedades"` |

Que sean atributos y no clases de CSS ni textos visibles es deliberado: un validador que buscara «Índice» por su rótulo se rompería al cambiar una mayúscula, y uno que buscara una clase se rompería con el primer refactor de estilos. Lo que aquí se compromete es un contrato, y un contrato tiene que sobrevivir a la maquetación.

**La versión candidata todavía no está en la base de datos cuando se renderiza.** `render_visual` corre dentro de `PublishVersion`, con la transacción abierta, sobre un manifiesto que ningún otro proceso puede leer. El frontend no puede pedirlo a la API, porque la API no lo ve. La salida es que **todas las peticiones de datos del frontend pasan por el cliente único de `shared/api`**, de modo que el navegador que conduce la publicación puede interceptarlas y servirlas desde el manifiesto candidato que tiene en memoria.

Eso convierte una regla de estilo de FSD en la condición de una puerta: un componente que se trajera sus datos por su cuenta —un `fetch` suelto, un JSON importado, una segunda instancia de cliente— dejaría de ser interceptable, y `render_visual` estaría juzgando un render distinto del que se va a publicar. **Ningún módulo fuera de `shared/api` emite una petición de red.** Es la afirmación más importante de este documento y la única cuyo incumplimiento no se paga en mantenimiento, sino en una versión publicada con la portada rota.

Quién paga la contrapartida está resuelto: §4 Fase 5 de la arquitectura declara que `publication.publish` conduce el navegador interceptando sus peticiones, y la spec del backend lo recoge en §4.5. Aquí solo queda la obligación de ser interceptable.

**La hoja de impresión vive en `app/styles`**, junto a los estilos globales y las fuentes, y no repartida por las páginas: `@media print` describe el documento entero, que es precisamente lo que la capa `app/` alberga.

---

## 7. Contratos de `shared/`

`shared/` no tiene slices: se organiza por segmentos, y **cada segmento expone su propia API pública** —`shared/api/index.ts`, `shared/ui/index.ts`— en lugar de un `shared/index.ts` único que mezclaría módulos sin relación.

| Segmento | Qué contiene | Qué no |
|---|---|---|
| `api` | El cliente único, los tipos de transporte que devuelve FastAPI y los errores tipados (`NoEncontrado`, `NovelaOcupada`, `SinRespuesta`) | Ninguna regla de negocio, ninguna decisión sobre qué significa un dato |
| `ui` | El kit: tipografía de lectura, tarjeta, tabla, botón, marca de capítulo cambiado | Nada que sepa qué es un Capítulo |
| `lib` | Utilidades y hooks sin dominio, como el de selección de texto o el formateo de fechas | — |
| `config` | Los constructores de ruta de §3 y la lectura de las dos variables de entorno | — |

**Los tipos de transporte no se escriben a mano: se derivan del OpenAPI que FastAPI ya publica.** Es lo que hace que un cambio de contrato en el backend rompa la construcción del frontend en lugar de romper la pantalla el día de la demo, y es lo que da a esta pieza su clase A/T en §10.

**El error se traduce una sola vez, en `shared/api`.** Cada página decide qué enseña ante un `NoEncontrado`, pero ninguna vuelve a mirar un código HTTP: eso es transporte, y el transporte no sube de capa.

---

## 8. Reglas estructurales y cómo se comprueban

Las dos reglas de FSD que sostienen la organización son comprobables sin ejecutar nada, y por eso la estructura del frontend es una propiedad de clase **A** y no una disciplina que haya que recordar:

1. **Un módulo solo importa de capas estrictamente inferiores.** `app → pages → shared`.
2. **Dos slices de la misma capa nunca se importan entre sí.** De ahí los constructores de ruta de §3.

A ellas se suman cuatro reglas de la metodología que este frontend adopta tal cual:

- **`features/` y `entities/` no se crean de entrada.** La regla de extracción de FSD exige tres condiciones a la vez —uso real en más de un sitio hoy, motivo de cambio independiente de cualquier consumidor y responsabilidad acotada— y ninguna pantalla las cumple todavía. Crear las carpetas vacías «por si acaso» es el antipatrón que la propia metodología nombra.
- **`widgets/` no se usa.** La referencia oficial la desaconseja, y lo que en otra organización sería un widget aquí es composición de una página.
- **Los assets van junto al código que los usa.** No hay carpeta `assets/` de primer nivel; las hojas de estilo globales y las fuentes van a `app/`.
- **Los ficheros se nombran por dominio, no por rol técnico.** `model/capitulo.ts`, no `model/types.ts`.

**Steiger lo verifica sobre `frontend/src` y publica su salida con el informe de G1, pero no bloquea.** Es el criterio que `verification.md` aplica en todas partes: bloquea lo que sostiene una puerta e informa lo que describe la forma del repositorio. La forma de una carpeta no pone en riesgo lo que G3 y G5 protegen; el cliente único de `shared/api`, en cambio, sí, y por eso esa condición no se deja a Steiger —que no la vería— sino al propio `render_visual`, que falla si el render no se puede alimentar.

---

## 9. Casos de error, en una tabla

| Caso | Qué hace el frontend |
|---|---|
| Novela, versión o capítulo inexistente (`404`) | Pantalla de «no existe» con vuelta al listado. Nunca una página en blanco |
| Novela ocupada al pedir un cambio (`409`) | Se dice que hay una ejecución en curso y que se reintente. No se encola |
| API caída o sin respuesta | Aviso de que el servidor no responde, con reintento. La lectura no se cachea para fingir que sigue viva |
| Novela sin versiones publicadas | Aparece en el listado sin enlace de lectura, con su fase en curso |
| Versión sin predecesora | El índice no marca capítulos cambiados y la impresión omite la página de novedades |
| Selección de fragmento vacía | El formulario de petición no se habilita |
| Ficha de personaje sin capítulos que enlazar | Se enseña la ficha sin enlaces; la entrada no se oculta |

---

## 10. Clases de confianza declaradas

Resumen de lo que este documento compromete, como exige `AGENTS.md`. Cada pieza con su clase primaria y el gate que la cubre.

| Pieza | Clase | Gate |
|---|---|---|
| Organización en capas y API pública por segmento (Steiger) | **A** | G1, informa |
| Tipos de transporte derivados del OpenAPI | **A/T** | G1 |
| Constructores de ruta y ausencia de imports entre slices | **A** | G1 |
| Índice, portada y ficha de personajes renderizan (`render_visual`) | **D** | G5 |
| Enlaces internos del índice y de la ficha, comprobados con Playwright MCP | **D** | G2 |
| PDF impreso desde la ruta de lectura | **D** | G5 |
| Petición de cambio de extremo a extremo | **T/D** | G1, G2 |
| Cliente único como condición de interceptación | **A** | G5 |
| Lectura sin autenticación | **U-17** | — |

**Riesgos aceptados que este frontend hereda**, con fila en §5 de `verification.md`: U-17, la API de lectura sin autenticación. **No se declara ninguna U nueva en este documento**, y hay una candidata que §11 deja planteada: la calidad visual de la lectura no la mide nadie, porque `render_visual` comprueba que algo renderiza, no que se lea bien.

---

## 11. Lo que este documento pidió, y dónde quedó resuelto

Escribir esta spec destapó cinco costuras. **Las cinco están cerradas**, y ninguna se resolvió aquí: subieron a la arquitectura o a la spec del backend, que es donde se deciden, y bajaron después.

| # | Costura | Dónde quedó |
|---|---|---|
| 1 | La portada no tenía de dónde salir | `GET /novelas/{id}/versiones/{n}` devuelve el **bloque de paratexto** —título, homenajeado, dedicatoria con su ocasión y Licencias declaradas— (spec del backend §5) |
| 2 | La ficha de personajes no estaba versionada | Pasa a `GET /novelas/{id}/versiones/{n}/personajes`, con los capítulos de esa versión (spec del backend §5) |
| 3 | Nadie declaraba quién sirve la aplicación | §16.4 de la arquitectura: **FastAPI sirve el `dist/` construido**, un solo origen, URL base en `Settings` |
| 4 | El manifiesto candidato no era legible desde fuera de la transacción | §4 Fase 5 de la arquitectura: `render_visual` **sirve la versión candidata interceptando las peticiones** del navegador, y §16.3 convierte el cliente único en condición de G5 |
| 5 | `library` y `print` no figuraban en §16.3 | Declaradas en el árbol de §16.3, cada una derivada de una decisión ya tomada — el directorio como registro y el PDF impreso desde la ruta de lectura |

El comportamiento degradado que IMP-15 e IMP-17 declaraban mientras los endpoints no existieran **deja de hacer falta**, y el plan lo retira: la portada se dibuja con el paratexto y la ficha enlaza con la versión de la ruta.

---

## 12. Requisitos

Los apartados anteriores son el contrato, y están en prosa porque un contrato necesita decir también **por qué**. Esta tabla es ese mismo contrato en su forma comprobable: **cada fila enuncia una sola cosa y se puede responder con un sí o un no**. No añade ninguna decisión; si una fila y su apartado discrepan, manda el apartado y la fila está mal escrita.

**Cómo se lee cada columna.** El identificador `REQ-FE-nn` es estable y **no se reutiliza jamás**: un requisito retirado deja su fila con la nota, nunca cede su número. El apartado es de dónde se extrae el enunciado, y es también **de dónde hereda su clase de confianza y su gate**, declarados en §10; un requisito que se compruebe de otra manera lo dice en su propia fila. Los ítems son los de [`plan.md`](plan.md) que lo materializan, con el prefijo `BE:` cuando quien lo realiza es el plan del backend. Un guion significa que **ningún ítem lo realiza todavía**, que es justamente lo que `requisitos_declarados` informa.

### 12.1 La forma, la puesta en marcha y las rutas

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-FE-01 | El frontend no guarda estado de dominio que sobreviva a una recarga: ni copia local del canon, ni almacén global de la novela | §1 | IMP-09 |
| REQ-FE-02 | **Toda ruta de lectura lleva el número de versión**; una URL sin versión no identifica ningún texto y es incorrecta | §1, §3 | IMP-07, IMP-08 |
| REQ-FE-03 | En desarrollo, `vite dev` sirve la aplicación y alcanza la API por el proxy de Vite en `/api` | §2.1 | IMP-01 |
| REQ-FE-04 | Fuera de desarrollo, **FastAPI sirve el `dist/` construido**: la URL que abre `render_visual`, la que imprime el PDF y la que teclea el lector son la misma | §2.1 | IMP-26, BE:P-136 |
| REQ-FE-05 | Solo hay dos variables de configuración y **ninguna es un secreto** | §2.2 | IMP-01 |
| REQ-FE-06 | Los alias de importación se declaran **con el mismo mapa** en `tsconfig.json` y en `vite.config.ts` | §2.2 | IMP-03 |
| REQ-FE-07 | El mapa de rutas vive entero en `app/router.tsx`, y es el único sitio donde vive | §3 | IMP-07 |
| REQ-FE-08 | `/novelas/:id` redirige a la última versión publicada | §3 | IMP-19 |
| REQ-FE-09 | Para enlazar a otra pantalla, una página usa un constructor de URL de `shared/config` y **no importa nada de la slice vecina** | §3 | IMP-08 |

### 12.2 Las seis pantallas y la petición de cambio

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-FE-10 | Los estados de carga, de error y de vacío son **parte del contrato** de cada pantalla: un esqueleto de carga eterno es un render roto | §4 | IMP-11, IMP-28 |
| REQ-FE-11 | `library` enseña una fila por fichero de `proyectos/` con título, fase en curso y número de versiones publicadas | §4.1 | IMP-13 |
| REQ-FE-12 | Una novela sin ninguna versión publicada aparece igualmente, pero **sin enlace de lectura** | §4.1 | IMP-13 |
| REQ-FE-13 | Un directorio sin novelas se anuncia como vacío y **no como un error** | §4.1 | IMP-13 |
| REQ-FE-14 | El índice lista los capítulos del manifiesto en orden, con su número y su título | §4.2 | IMP-14 |
| REQ-FE-15 | El índice **marca los capítulos cambiados** respecto de la versión anterior, y la marca sale del endpoint de diff, no de comparar textos en el cliente | §4.2 | IMP-14, IMP-25 |
| REQ-FE-16 | La vista de capítulo muestra el texto tal como esa versión lo fija, con navegación a anterior y siguiente y vuelta al índice | §4.2 | IMP-15 |
| REQ-FE-17 | La selección de fragmento y la petición de cambio viven en `pages/reading` y **no se extraen a `features/` hasta que una segunda pantalla las ejerza** | §4.2 | IMP-20 |
| REQ-FE-18 | Cada entrada de la ficha de personajes y lugares **enlaza a los capítulos en los que aparece**, con el número de versión que la ruta lleva puesto | §4.3 | IMP-16, BE:P-110 |
| REQ-FE-19 | La portada lleva el título, la **dedicatoria** al homenajeado con su ocasión y la **nota del autor** con las Licencias declaradas | §4.4 | IMP-17, BE:P-110 |
| REQ-FE-20 | El historial lista las versiones publicadas con su fecha y su puntuación del juez, y para dos cualesquiera enseña qué capítulos cambian | §4.5 | IMP-18 |
| REQ-FE-21 | Desde el historial se abre cualquier versión anterior, que sigue entera y legible | §4.5 | IMP-18 |
| REQ-FE-22 | `print` es un solo documento con portada y dedicatoria, nota del autor, índice, capítulos, ficha de personajes y —si hay predecesora— página de novedades, en ese orden | §4.6 | IMP-22 |
| REQ-FE-23 | La petición envía el fragmento seleccionado, el capítulo y la versión desde los que se pide, y el texto de la petición | §5 | IMP-20 |
| REQ-FE-24 | El frontend **no resuelve nada**: no busca el hecho, no toca el canon y devuelve un acuse, no un resultado | §5 | IMP-21 |
| REQ-FE-25 | No hay espera ni sondeo: la novela cambia cuando aparece una versión nueva en el historial | §5 | IMP-21 |
| REQ-FE-26 | Una selección vacía no habilita el formulario | §5 | IMP-20 |
| REQ-FE-27 | Un `409` se cuenta tal cual y la petición **no se encola** | §5 | IMP-21 |

### 12.3 El modo impresión, `shared/` y la estructura

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-FE-28 | La ruta de impresión **no navega**: todo está en la misma página y el índice enlaza por ancla, no por router | §6 | IMP-24 |
| REQ-FE-29 | Las cuatro regiones que `render_visual` comprueba se marcan con `data-render`, nunca con clases de CSS ni con textos visibles | §6 | IMP-23 |
| REQ-FE-30 | **Ningún módulo fuera de `shared/api` emite una petición de red**, porque lo que no se puede interceptar no se puede juzgar | §6 | IMP-27, IMP-09 |
| REQ-FE-31 | La hoja `@media print` vive en `app/styles`, no repartida por las páginas | §6 | IMP-06 |
| REQ-FE-32 | Cada segmento de `shared/` expone su propia API pública, en lugar de un `shared/index.ts` único | §7 | IMP-02 |
| REQ-FE-33 | `shared/api` no contiene ninguna regla de negocio ni decide qué significa un dato | §7 | IMP-09 |
| REQ-FE-34 | `shared/ui` no contiene nada que sepa qué es un Capítulo | §7 | IMP-11 |
| REQ-FE-35 | Los tipos de transporte **se derivan del OpenAPI** que FastAPI publica; no se escriben a mano | §7 | IMP-05 |
| REQ-FE-36 | El error se traduce una sola vez en `shared/api`, y **ninguna página vuelve a mirar un código HTTP** | §7 | IMP-10 |
| REQ-FE-37 | Un módulo solo importa de capas estrictamente inferiores: `app → pages → shared` | §8 | IMP-02, IMP-04 |
| REQ-FE-38 | Dos slices de la misma capa nunca se importan entre sí | §8 | IMP-08, IMP-04 |
| REQ-FE-39 | `features/` y `entities/` no se crean de entrada, porque ninguna pantalla cumple todavía las tres condiciones de extracción | §8 | IMP-02 |
| REQ-FE-40 | `widgets/` no se usa: lo que en otra organización sería un widget aquí es composición de una página | §8 | IMP-02 |
| REQ-FE-41 | Los assets van junto al código que los usa; no hay carpeta `assets/` de primer nivel | §8 | IMP-06 |
| REQ-FE-42 | Los ficheros se nombran por dominio y no por rol técnico | §8 | IMP-02 |
| REQ-FE-43 | Steiger **informa y no bloquea**: la forma de una carpeta no pone en riesgo lo que G3 y G5 protegen | §8 | IMP-04 |

### 12.4 Errores, comprobación y alcance

| # | Requisito | Apartado | Ítems |
|---|---|---|---|
| REQ-FE-44 | Un `404` lleva a una pantalla de «no existe» con vuelta al listado, **nunca a una página en blanco** | §9 | IMP-10 |
| REQ-FE-45 | Con la API caída se avisa y se ofrece reintento; **la lectura no se cachea para fingir que sigue viva** | §9 | IMP-10 |
| REQ-FE-46 | Una versión sin predecesora no marca capítulos cambiados y omite la página de novedades | §9 | IMP-25 |
| REQ-FE-47 | Una ficha sin capítulos que enlazar se enseña sin enlaces; la entrada **no se oculta** | §9 | IMP-16 |
| REQ-FE-48 | Los enlaces internos del índice y de la ficha se comprueban con un recorrido de **Playwright MCP** | §10 | IMP-29 |
| REQ-FE-49 | El PDF de ejemplo se imprime con `page.pdf()` desde la ruta de impresión de este frontend | §10 | IMP-30, BE:P-94 |
| REQ-FE-50 | La interfaz va en castellano, **sin capa de internacionalización** | §13 | IMP-31 |
| REQ-FE-51 | Los identificadores de este apartado no se repiten ni se reutilizan, y todo ítem citado existe en el plan | §12 | BE:P-139 |

---

## 13. Lo que este documento deja fuera a propósito

- **La forma técnica exacta** —qué componente, qué biblioteca de datos, en qué orden se construye— va en [`plan.md`](plan.md).
- **El backend entero**, incluida la forma interna de los endpoints que aquí se consumen.
- **El diseño visual concreto**: tipografías, paleta y maquetación fina son decisiones de ejecución, no contrato.
- **La internacionalización**: la novela y la interfaz van en castellano, y no hay un segundo idioma que sostener.
- **La autenticación**, que no existe por decisión declarada en U-17.

---

## 14. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-23 | Las cinco costuras de §11 quedan cerradas arriba y §11 pasa a decir dónde: dos endpoints en la spec del backend, y en la arquitectura quién sirve la aplicación, cómo ve el navegador la versión candidata y las dos pantallas que faltaban en §16.3 | Una spec que enumera lo que le falta al de al lado sirve una vez, para pedirlo. Cuando lo pedido se concede, lo que tiene que contar es dónde quedó decidido |
| 2026-09-23 | Versión inicial | Fijar el contrato del frontend: las seis pantallas, el mapa de rutas, la petición de cambio y —sobre todo— las condiciones del modo impresión, que es donde este frontend deja de ser una interfaz y pasa a sostener G5 |
| 2026-09-23 | Entra **§12, los 51 requisitos** `REQ-FE-nn` derivados de los propios apartados de este documento, con el apartado del que nacen y los ítems que los realizan, y los apartados finales se renumeran | Mismo motivo que en la spec del backend: el contrato estaba escrito para leerse y no para comprobarse. Los requisitos salen de lo que este documento ya afirma, de modo que no añaden ninguna decisión |
