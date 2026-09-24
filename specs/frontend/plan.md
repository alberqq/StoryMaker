# Plan de implementación — Frontend de StoryMaker

**Solo la forma técnica exacta**: qué fichero, qué símbolo, en qué orden y contra qué puerta se comprueba. El *qué hace* está en [`spec.md`](spec.md) y el *por qué* en [`architecture.md`](../../docs/architecture.md), que es la fuente de verdad. **Si algo de este plan contradice la arquitectura, hay que parar y preguntar al Autor.**

La correspondencia ítem a ítem entre este plan y la arquitectura vive en [`trace-matrix.md`](trace-matrix.md), y es la que garantiza que no queda ni una decisión fijada sin código que la realice ni un ítem de trabajo que nadie pidió.

---

## 1. Cómo se lee este plan

Cada ítem lleva un identificador `IMP-nn` que no se reutiliza jamás, el entregable, los ficheros y símbolos que lo materializan, **el criterio de hecho** —qué tiene que ser cierto para darlo por terminado, que no es «existe el fichero»—, el apartado de la arquitectura del que nace y el Quality Gate que lo cubre.

Los identificadores son `IMP-nn` y no `P-nn` porque el plan del backend ya ocupa ese espacio y ningún identificador se reutiliza entre planes: la matriz de trazabilidad tiene que poder nombrar a los dos a la vez sin ambigüedad.

| Hito | Qué deja en pie | Gate |
|---|---|---|
| **H0** | Andamiaje, capas vacías, rutas y puertas estáticas | G1 |
| **H1** | `shared/`: el cliente único, los errores, el kit y la ausencia de copia local | G1 |
| **H2** | Las seis pantallas leyendo de la API | G1, G2 |
| **H3** | La petición de cambio del lector | G1, G2 |
| **H4** | El modo impresión, el PDF y la condición de G5 | G5 |
| **H5** | Verificación de extremo a extremo, trazabilidad en CI y entrega | G1, G2, G5 |
| **H6** | La interfaz opera el arnés: tablero, encargo, panel, gate, salidas y diseño | G1, G4 |

El criterio de corte de cada hito es el mismo que en el backend: **el hito termina cuando su parte de la comprobación está en verde, no cuando el código existe.**

---

## 2. H0 · Andamiaje, capas y rutas

| # | Entregable | Ficheros y símbolos | Criterio de hecho | Arq. | Gate |
|---|---|---|---|---|---|
| **IMP-01** | Proyecto **React + Vite** con TypeScript en `frontend/`, con los scripts `dev`, `build`, `preview`, `tipos` y `estructura` | `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html` | `npm run build` produce `dist/`; `npm run dev` sirve la aplicación con el proxy de `/api` contra FastAPI, que monta la API **bajo ese mismo prefijo** en todos los escenarios | §16.1 | G1 |
| **IMP-02** | Árbol **FSD v2.1** con el juego mínimo: `app/`, `pages/`, `shared/`, con un `index.ts` **por segmento** de `shared` y **una API pública por slice** de `pages/`. Sin `widgets/`, sin `features/` y sin `entities/` | `frontend/src/{app,pages,shared}/…`, `shared/{api,ui,lib,config}/index.ts`, `pages/{library,reading,characters,cover,versions,print}/index.ts` | No existe `shared/index.ts` único; **no existen `widgets/`, `features/` ni `entities/`**, ni vacías ni llenas; cada slice de `pages/` expone su `index.ts` y **ningún módulo de fuera importa el interior de una slice**, empezando por `app/router.tsx`; Steiger no reporta violación de capa | §16.3 | G1 |
| **IMP-03** | Alias `@/app`, `@/pages`, `@/shared` declarados **con el mismo mapa** en `tsconfig.json` y en `vite.config.ts` | `frontend/tsconfig.json::paths`, `frontend/vite.config.ts::resolve.alias` | Un import por alias compila con `tsc` y resuelve en `dev` y en `build`; los dos mapas coinciden literalmente | §16.3 | G1 |
| **IMP-04** | **Steiger** como script y como trabajo de CI que **informa y no bloquea**, con su salida publicada junto al informe de G1 | `frontend/package.json::scripts.estructura`, `.github/workflows/ci.yml` (trabajo `frontend-estructura`) | El trabajo publica la salida de `npx steiger src` y **termina en verde aunque haya hallazgos** | §16.1, §16.3, verif. §3.2 | G1 |
| **IMP-05** | Generación de los **tipos de transporte desde el OpenAPI** que FastAPI publica; no se escriben a mano | `frontend/scripts/generar-tipos.ts`, `shared/api/transporte.ts` (generado) | Regenerar contra un backend con un endpoint cambiado hace fallar `tsc`; el fichero generado está marcado como tal y no se edita | §16.3, spec §7 | G1 |
| **IMP-06** | `app/styles`: reset, tipografía de lectura, **fuentes locales** y la hoja `@media print` | `app/styles/global.css`, `app/styles/print.css`, `app/styles/fonts/` | Las fuentes se sirven desde el propio origen —sin petición a terceros— y la hoja de impresión oculta la navegación; **no hay carpeta `assets/` de primer nivel** ni en `frontend/src` ni en `shared/`, y cada imagen vive en la slice que la importa | §16.3, §15 | G1 |
| **IMP-07** | `app/router.tsx` con las **ocho rutas** de §3 de la spec y `app/providers` | `app/router.tsx::rutas`, `app/providers/index.tsx`, `app/main.tsx` | Cada ruta monta su página; una ruta desconocida cae en la pantalla de «no existe»; ninguna ruta de lectura carece de versión | §7, §16.3, spec §3 | G1 |
| **IMP-08** | `shared/config`: **constructores de ruta** (`rutaCapitulo`, `rutaPersonajes`, `rutaPortada`, `rutaImprimir`, `rutaVersiones`) y lectura de `VITE_API_URL` y `VITE_BASE_PATH` | `shared/config/rutas.ts`, `shared/config/entorno.ts` | Ninguna página construye una URL con plantilla propia, y ninguna slice de `pages/` importa de otra; **solo se leen `VITE_API_URL` y `VITE_BASE_PATH`, y ninguna es un secreto** | §16.3, §16.4, spec §2.2, §3 | G1 |

**Lo que rompe:** nada. H0 no enseña todavía ninguna novela.

---

## 3. H1 · `shared/`: cliente, errores y kit

| # | Entregable | Ficheros y símbolos | Criterio de hecho | Arq. | Gate |
|---|---|---|---|---|---|
| **IMP-09** | **Cliente único** de la API: una instancia, base tomada de `shared/config`, y el **único punto del código que emite red** | `shared/api/cliente.ts::cliente`, `shared/api/novelas.ts`, `shared/api/versiones.ts` | Una prueba de repositorio falla si aparece `fetch(`, `XMLHttpRequest` o una segunda instancia de cliente fuera de `shared/api/`; **el cliente no envía cabecera de autenticación ni guarda credenciales**, y sus funciones devuelven los tipos de transporte **tal cual**: ninguna calcula, filtra ni reordena datos de dominio | §16.3, §16.4, spec §6 | G1, G5 |
| **IMP-10** | **Errores tipados** `NoEncontrado`, `NovelaOcupada` y `SinRespuesta`, traducidos desde el código HTTP **una sola vez** | `shared/api/errores.ts` | Ningún módulo de `pages/` menciona `404`, `409` ni `status` | §16.3, spec §7, §9 | G1 |
| **IMP-11** | Kit de `shared/ui`: `Pagina`, `Tarjeta`, `Tabla`, `Boton`, `EnlaceCapitulo`, `MarcaCambiado` y los tres estados `EstadoCarga`, `EstadoError`, `EstadoVacio` | `shared/ui/{Pagina,Tarjeta,Tabla,Boton,EnlaceCapitulo,MarcaCambiado,Estados}.tsx`, `shared/ui/ui.css` | Los tres estados existen como componentes —más `NoExiste`, la pantalla de «no existe» con vuelta al listado— y **toda pantalla los usa**: no hay ninguna que se quede en blanco mientras carga. Ningún componente recibe un tipo de dominio: `EnlaceCapitulo` y `MarcaCambiado` reciben un destino y un texto | §16.3, spec §4 | G1 |
| **IMP-12** | `shared/lib`: hook de **selección de texto** y formateo de fecha y de puntuación | `shared/lib/seleccion.ts::useSeleccion`, `shared/lib/formato.ts`, `shared/lib/carga.ts::useCarga` | El hook devuelve el fragmento seleccionado y el `data-origen` del contenedor en que se seleccionó —la página pone ahí el capítulo—, y cadena vacía cuando no hay selección. `useCarga` da a cada pantalla sus tres estados sin caché y sin emitir red: recibe la función de `shared/api` que la emite | §16.3, spec §5 | G1 |
| **IMP-32** | **Sin copia local de la novela**: ni almacenamiento del navegador, ni caché persistente de respuestas, ni *service worker*. Lo que el lector ve se pide a la API cada vez que se monta la pantalla | `frontend/tests/estructura/sin-copia-local.test.ts` | Una prueba de repositorio falla si aparece `localStorage`, `sessionStorage`, `indexedDB`, `caches.` o el registro de un *service worker* en `frontend/src`; tras una recarga la pantalla vuelve a pedir sus datos, y con la API caída enseña el aviso de §9 de la spec y **no la última lectura** | §2, §15, §16.4, spec §1, §9 | G1 |

**Lo que rompe:** nada; no hay pantalla que consuma esto todavía.

---

## 4. H2 · Las seis pantallas

| # | Entregable | Ficheros y símbolos | Criterio de hecho | Arq. | Gate |
|---|---|---|---|---|---|
| **IMP-13** | *Retirado el 2026-09-24.* El listado de novelas pasa a ser el tablero de IMP-39 | — | — | §16.4 | — |
| **IMP-14** | `pages/reading`, vista de **índice**: capítulos del manifiesto en orden, con su número y su título, y **marca de capítulo cambiado** respecto de la versión anterior | `pages/reading/ui/Indice.tsx`, `pages/reading/api/manifiesto.ts`, `pages/reading/model/cambiados.ts` | La marca sale del endpoint de diff, no de comparar textos en el cliente; sin versión anterior, no hay marcas y no hay petición de diff | §4 F5, §4 F6, §16.3 | G1, G2 |
| **IMP-15** | `pages/reading`, vista de **capítulo**: el texto tal como esa versión lo fija, con anterior, siguiente y vuelta al índice | `pages/reading/ui/Capitulo.tsx`, `pages/reading/api/capitulo.ts` | Un capítulo inexistente muestra la pantalla de «no existe»; el primero no ofrece anterior y el último no ofrece siguiente | §7, §4 F5 | G1 |
| **IMP-16** | `pages/characters`: fichas de personajes y de escenarios, **cada entrada enlazada a los capítulos donde aparece**, leídas de `GET /novelas/{id}/versiones/{n}/personajes` | `pages/characters/ui/Fichas.tsx`, `pages/characters/api/personajes.ts` | El enlace lleva la versión de la ruta; una ficha sin apariciones se muestra sin enlaces y **no se oculta** | §4 F5, §16.3 | G1, G2 |
| **IMP-17** | `pages/cover`: título, **dedicatoria** con la ocasión y **nota del autor** con las Licencias declaradas | `pages/cover/ui/Portada.tsx`, `pages/cover/api/paratexto.ts` | Renderiza con el **bloque de paratexto** que devuelve el endpoint de versión; una novela sin Licencias declaradas enseña la portada y omite la nota, que es un caso legítimo y no un fallo | §4 F5, §16.3 | G1, G2 |
| **IMP-18** | `pages/versions`: historial con fecha y puntuación del juez, apertura de cualquier versión anterior y **diff entre dos** | `pages/versions/ui/Historial.tsx`, `pages/versions/api/historial.ts`, `pages/versions/api/diff.ts` | Una versión anterior se abre entera y legible; el diff lista los capítulos que cambian entre los dos manifiestos | §4 F6, §7, §8 | G1 |
| **IMP-19** | *Retirado el 2026-09-24.* `/novelas/:id` ya no redirige a la lectura: es el panel de IMP-41 | — | — | §7 | — |

**Lo que rompe:** nada del backend. A partir de aquí el frontend depende de que la API responda.

---

## 5. H3 · La petición de cambio del lector

| # | Entregable | Ficheros y símbolos | Criterio de hecho | Arq. | Gate |
|---|---|---|---|---|---|
| **IMP-20** | **Selección de fragmento y formulario de petición** dentro del lector, con `POST /novelas/{id}/cambios` llevando fragmento, capítulo, versión y texto | `pages/reading/ui/PeticionCambio.tsx`, `pages/reading/api/pedir-cambio.ts` | Sin selección el botón **no se habilita**; la petición viaja con los cuatro campos; el componente vive en `pages/reading` y no en una slice propia | §4 F6, §16.3 | G1, G2 |
| **IMP-21** | **Acuse y rechazo**: respuesta correcta → «queda registrada, el Autor la revisará»; `409` → aviso de ejecución en curso | `pages/reading/ui/PeticionCambio.tsx`, `shared/api/errores.ts` | Ante un `409` **no hay reintento automático ni cola**; el frontend no sondea el gate en ningún caso | §16.4, spec §5 | G1 |

**Lo que rompe:** nada. La petición no toca la novela: abre la Fase 6, que se detiene en su gate.

---

## 6. H4 · El modo impresión y la condición de G5

| # | Entregable | Ficheros y símbolos | Criterio de hecho | Arq. | Gate |
|---|---|---|---|---|---|
| **IMP-22** | `pages/print`: **un solo documento** con portada y dedicatoria, nota del autor, índice, capítulos, ficha de personajes y novedades, en ese orden | `pages/print/ui/Documento.tsx`, `pages/print/api/todo.ts` | Una sola navegación lo trae entero; dentro no hay router ni paginación | §16.1, §4 F5 | G5 |
| **IMP-23** | **Anclas estables** `data-render` con los valores `indice`, `portada`, `personajes` y `novedades`, y un `id` por capítulo | `pages/print/ui/*`, `pages/reading/ui/Indice.tsx` | Los cuatro selectores existen en el DOM renderizado y **no dependen de ninguna clase de CSS ni de ningún rótulo visible** | §11a, spec §6 | G5 |
| **IMP-24** | **Enlaces internos por ancla** en el índice, en la ficha de personajes y en la página de novedades | `pages/print/ui/Indice.tsx`, `pages/print/ui/Novedades.tsx` | En el PDF impreso los enlaces saltan a su destino dentro del documento | §4 F5, §4 F6 | G5 |
| **IMP-25** | **Página de novedades** cuando la versión tiene predecesora, construida desde el endpoint de diff | `pages/print/ui/Novedades.tsx` | Sin predecesora la sección se omite entera y el índice no la enlaza | §4 F6 | G5 |
| **IMP-26** | **FastAPI monta el `dist/` construido** y declara la URL base con la que Playwright abre la lectura. *Ítem compartido con el backend*, donde es `P-136` | `backend/src/storymaker/api/estaticos.py::montar_frontend`, `commons/config.py::Settings.frontend_dist`, `commons/config.py::Settings.frontend_base_url`, `frontend/package.json::scripts.build` | `render_visual` y el PDF abren **la misma URL del mismo origen** que el lector; no hace falta un segundo proceso vivo | §16.1, §16.4 | G5 |
| **IMP-27** | **Contrato de interceptación**: todas las peticiones salen del cliente único, de modo que el navegador de `render_visual` pueda servirlas desde el manifiesto candidato que vive en la transacción abierta. El lado del backend es `P-92` | `shared/api/cliente.ts`, `frontend/tests/estructura/cliente-unico.test.ts` | La prueba falla si algún módulo fuera de `shared/api` emite red; `render_visual` renderiza la versión candidata **sin que esté publicada** | §4 F5, §11a | G5 |

**Lo que rompe:** IMP-26 cambia cómo se sirve la aplicación. Mientras no esté, `render_visual` no tiene URL que abrir y el PDF tampoco.

---

## 7. H5 · Verificación y entrega

| # | Entregable | Ficheros y símbolos | Criterio de hecho | Arq. | Gate |
|---|---|---|---|---|---|
| **IMP-28** | Pruebas de componente e integración con **MSW** sobre los contratos de `shared/api`, incluidos los siete casos de error de §9 de la spec | `frontend/tests/**` | Los siete casos de error tienen prueba, y la suite corre en el mismo trabajo de CI que Steiger | verif. §3.5 | G1 |
| **IMP-29** | Recorrido con **Playwright MCP**: índice navegable, enlaces de la ficha y portada con dedicatoria, más la configuración del MCP en el harness | `.mcp.json`, `frontend/tests/recorrido.md` | Se demuestran LEC-02, LEC-04 y LEC-05 sobre una novela real, y el acta queda con el informe de G2 | §19, verif. §2 nº 11 | G2 |
| **IMP-30** | **`ejemplos/novela-ejemplo.pdf`** impreso con `page.pdf()` desde la ruta de impresión de una versión publicada | `ejemplos/novela-ejemplo.pdf`, `backend/src/storymaker/publication/render.py::imprimir_pdf` | El PDF tiene los diez capítulos, índice con enlaces que saltan y portada con dedicatoria (ENT-06) | §16.1, §4 F5 | G5 |
| **IMP-31** | **Castellano** en toda la interfaz, sin capa de internacionalización | `frontend/src/**` | No hay fichero de traducciones ni cadena en inglés visible al lector | §19 | G1 |
| **IMP-33** | **Trazabilidad del frontend en CI**: `inventario_del_plan` lee también las filas `IMP-nn` de este plan y coteja sus rutas contra `frontend/` en las dos direcciones, y `requisitos_declarados` recorre §12 de la spec contra este plan. *Ítem compartido con el backend*, donde son `P-129` y `P-139` | `backend/tests/correspondencia/test_inventario.py`, `backend/tests/correspondencia/test_requisitos.py` | Una ruta nombrada en un ítem `IMP-nn` que no existe cae en el cubo «declarado y ausente»; un módulo de `frontend/src` que ningún ítem nombra cae en «presente y no declarado»; un `REQ-FE-nn` que cita un `IMP-nn` inexistente se informa. **Ninguno de los tres bloquea** | §1, §11e | G1 |

---

## 8. H6 · La interfaz opera el arnés

La operación de arq. §16.5 y spec §4.1 a §4.5, §5 y §8: el tablero, el encargo, el panel, el gate, la salida de cada fase, el seguimiento y el diseño visual en dos registros. Depende de P-160 a P-166 del plan del backend.

| # | Entregable | Ficheros y símbolos | Criterio de hecho | Arq. | Gate |
|---|---|---|---|---|---|
| **IMP-34** | `entities/novela`: los estados de spec §5.2 con su nombre y su color, las seis fases con su nombre castellano y su segmento de URL, la **insignia de estado** y la **línea de fases** | `entities/novela/index.ts`, `entities/novela/model/estado.ts`, `entities/novela/model/fases.ts`, `entities/novela/ui/InsigniaEstado.tsx`, `entities/novela/ui/LineaDeFases.tsx` | La slice no importa de `shared/api` nada que no sea un tipo y no emite red; la insignia siempre lleva texto además del color; la línea marca las fases deducidas | §16.3 | G1 |
| **IMP-35** | `shared/api` de seguimiento y operación: listado, panel, gate, salida de fase, intento, registro, ejemplos, validar encargo, encargar, continuar, decidir, reintentar, desbloquear y editar; el error `Rechazada` para el `422`, `403` y `415` | `shared/api/seguimiento.ts`, `shared/api/operacion.ts`, `shared/api/fases.ts`, `shared/api/errores.ts::Rechazada` | Todas pasan por el cliente único; las acciones envían JSON; ninguna página mira un código HTTP; un `202` resuelve con el nombre del registro | §16.5 | G1 |
| **IMP-36** | `useSondeo`: vuelve a pedir cada tres segundos con la pestaña visible, se detiene al ocultarla, **conserva los datos anteriores mientras refresca** y no apila avisos si la API cae; y formateo de dinero, tokens y duración | `shared/lib/sondeo.ts::useSondeo`, `shared/lib/formato.ts` | Una prueba con temporizadores falsos ve la segunda petición a los tres segundos y ninguna con `document.hidden`; un refresco no desmonta el contenido | §16.5 | G1 |
| **IMP-37** | Kit ampliado de `shared/ui`: marco de la aplicación con barra de navegación, insignia, pestañas, diálogo, campo de formulario, métrica, barra de progreso y sección plegable | `shared/ui/{Marco,Insignia,Pestanas,Dialogo,Campo,Metrica,Progreso,Seccion}.tsx`, `shared/ui/logo.png` | Ningún componente recibe un tipo de dominio; el diálogo atrapa el foco y se cierra con Escape | §16.3 | G1 |
| **IMP-38** | **Tokens de diseño** para los dos modos, la tipografía del panel servida desde el origen, y la separación entre el registro de panel y el de libro | `app/styles/tokens.css`, `app/styles/global.css`, `app/styles/libro.css`, `app/styles/fonts/` | Los tokens del panel usan la marca —naranja `#ff7932` y blanco roto `#f5f5f5`—; una prueba falla si un `.tsx` o un `.css` fuera de `tokens.css` escribe un color literal; el modo oscuro solo redefine tokens; nada se desborda a 360 px | spec §8 | G1, G4 |
| **IMP-39** | **El tablero**: seis columnas, una tarjeta por novela, arrastre nativo con las reglas de spec §4.1, diálogo de confirmación con el resumen del gate y casilla de comentario para rehacer, botones equivalentes en la tarjeta y llamada a encargar | `pages/library/ui/Tablero.tsx`, `pages/library/ui/TarjetaNovela.tsx`, `pages/library/ui/ConfirmarGate.tsx`, `pages/library/model/columnas.ts`, `pages/library/api/listar.ts`, `pages/library/api/decidir.ts`, `pages/library/index.ts` | Solo es arrastrable una tarjeta con gate pendiente que no sea de Regeneración; soltar fuera de las dos columnas válidas no hace nada; **ninguna decisión sale sin pulsar confirmar**; el sondeo no mueve la tarjeta mientras se arrastra | §16.5 | G1 |
| **IMP-40** | **El encargo**: formulario por bloques del `Brief`, precarga desde `ejemplos/`, validación en el backend con errores junto a su campo, nombre, con gates o en batch, y lanzar | `pages/commission/ui/Encargo.tsx`, `pages/commission/ui/Bloques.tsx`, `pages/commission/model/brief.ts`, `pages/commission/api/encargo.ts`, `pages/commission/index.ts` | Un brief inválido no se lanza y cada error aparece bajo su campo; lanzar navega al panel de la novela | §16.5 | G1 |
| **IMP-41** | **El panel**: cabecera con estado y acciones de spec §5.3, línea de fases, actividad, rejilla de capítulos, consumo, registro plegado y versiones | `pages/novel/ui/Panel.tsx`, `pages/novel/ui/Acciones.tsx`, `pages/novel/ui/Actividad.tsx`, `pages/novel/ui/Capitulos.tsx`, `pages/novel/ui/Registro.tsx`, `pages/novel/model/acciones.ts`, `pages/novel/api/panel.ts`, `pages/novel/index.ts` | Cada estado ofrece exactamente sus acciones de la tabla; abortar y desbloquear piden confirmación; tras una acción se lee «lanzado» | §16.5 | G1 |
| **IMP-42** | **El gate**: qué fase espera, resumen, preguntas de Intake como casillas, decisión —aprobar, rehacer con comentario y abortar solo en Intake—, editor de filas y la variante de Regeneración con petición y candidatos | `pages/gate/ui/Gate.tsx`, `pages/gate/ui/Preguntas.tsx`, `pages/gate/ui/Decision.tsx`, `pages/gate/ui/Editor.tsx`, `pages/gate/ui/Regeneracion.tsx`, `pages/gate/api/gate.ts`, `pages/gate/index.ts` | Contestar las preguntas envía `rehacer` con las respuestas numeradas como comentario; la pantalla nunca envía `editar`; un hecho de corpus sellado sale sin control de edición | §10, §16.5 | G1 |
| **IMP-43** | **La salida de cada fase**: pestañas por fase con sus ejecuciones y decisiones y la vista propia de cada una | `pages/phase/ui/Fase.tsx`, `pages/phase/ui/Ejecuciones.tsx`, `pages/phase/ui/SalidaEncargo.tsx`, `pages/phase/ui/SalidaInvestigacion.tsx`, `pages/phase/ui/SalidaTrama.tsx`, `pages/phase/ui/SalidaEscritura.tsx`, `pages/phase/ui/SalidaPublicacion.tsx`, `pages/phase/ui/SalidaRegeneracion.tsx`, `pages/phase/api/fase.ts`, `pages/phase/index.ts` | Cada vista enseña lo que su fila de spec §4.5 enumera; una fase sin salida lo dice sin error | §16.5 | G1 |
| **IMP-44** | Las rutas nuevas y sus constructores: taller, encargo, panel, gate y fase | `app/router.tsx`, `shared/config/rutas.ts::rutaEncargo`, `shared/config/rutas.ts::rutaPanel`, `shared/config/rutas.ts::rutaGate`, `shared/config/rutas.ts::rutaFase` | `/novelas/:id` monta el panel; ninguna página construye esas URL a mano | §16.3 | G1 |
| **IMP-45** | Las pantallas de lectura pasan al **registro de libro** de spec §8 dentro del marco nuevo, sin tocar sus contratos | `pages/reading/ui/*`, `pages/characters/ui/*`, `pages/cover/ui/*`, `pages/versions/ui/*`, `pages/print/ui/*` | Las pruebas de lectura e impresión de H2 y H4 siguen en verde sin cambiar sus aserciones | spec §8 | G1 |
| **IMP-46** | Pruebas con MSW de las pantallas de operación y de las reglas del tablero, y la prueba de tokens | `frontend/tests/pantallas/taller.test.tsx`, `frontend/tests/pantallas/encargo.test.tsx`, `frontend/tests/pantallas/panel.test.tsx`, `frontend/tests/pantallas/gate.test.tsx`, `frontend/tests/pantallas/fases.test.tsx`, `frontend/tests/estructura/tokens.test.ts` | Cubren arrastrar y confirmar, arrastre inválido, acciones por estado, preguntas de Intake, editor, abortar solo en Intake y un `409` al decidir | verif. §3.5 | G1 |
| **IMP-47** | **El encargo por conversación**: modo por defecto con el nombre del homenajeado y la descripción libre, siempre con gates, que lleva al gate; el formulario completo pasa a segundo modo | `pages/commission/ui/Encargo.tsx`, `pages/commission/ui/Conversacion.tsx`, `pages/commission/model/brief.ts` | La descripción viaja como `descripcion`; lanzar en este modo nunca envía `batch`; los dos modos validan en el backend | §4 F1 | G1 |
| **IMP-48** | **El gate de Intake como conversación**: descripción, rondas anteriores, preguntas nuevas con su casilla, estado «pensando» tras enviar y brief cerrado con la propuesta de aprobar | `pages/gate/ui/Entrevista.tsx`, `pages/gate/api/gate.ts`, `pages/gate/ui/Gate.tsx` | Tras contestar no se navega; sin gate y con la novela trabajando se dice que el entrevistador piensa; sin preguntas se enseña el brief | §4 F1, §16.5 | G1 |
| **IMP-49** | Pruebas del encargo por conversación y de la entrevista en el gate | `frontend/tests/pantallas/entrevista.test.tsx` | Cubren el lanzamiento con `descripcion`, las rondas, el estado «pensando» y el brief cerrado | verif. §3.5 | G1 |
| **IMP-50** | La **casilla de investigación exhaustiva** en los dos modos del encargo | `pages/commission/ui/CasillaExhaustiva.tsx`, `pages/commission/ui/Encargo.tsx`, `pages/commission/ui/Conversacion.tsx`, `pages/commission/api/encargo.ts` | Marcada, el encargo viaja con `investigacion: 'exhaustiva'`; sin marcar, con `estandar` | §4 F2 | G1 |
| **IMP-51** | Los lugares **titulados con su nombre corto** en la ficha, la impresión y la salida de la Trama, con la descripción debajo | `pages/characters/ui/Fichas.tsx`, `pages/print/ui/Personajes.tsx`, `pages/phase/ui/SalidaTrama.tsx` | Ningún título de lugar es la descripción entera | §16.3 | G1 |
| **IMP-52** | **Descargar el PDF** de cada versión publicada desde el panel, el índice de lectura y la salida de la Publicación | `shared/api/versiones.ts::urlDelPdf`, `pages/novel/ui/Panel.tsx`, `pages/reading/ui/Indice.tsx`, `pages/phase/ui/SalidaPublicacion.tsx` | La URL sale de `shared/api`; el enlace descarga el fichero | §4 F5 | G1 |

**Lo que rompe:** `/novelas/:id` deja de redirigir a la lectura y pasa a ser el panel; `pages/library` cambia su lista por el tablero. Las rutas de lectura no cambian.

---

## 9. Dependencias y qué se rompe mientras tanto

- **H2 depende de la API**, no del backend entero: mientras las pantallas se construyen, MSW sirve los contratos y el desarrollo no espera.
- **IMP-16 e IMP-17 dependen de dos endpoints concretos** —la ficha versionada y el bloque de paratexto—, que la spec del backend ya contrata en su §5. Dejaron de necesitar comportamiento degradado el día que esos dos endpoints se declararon.
- **IMP-26 e IMP-27 son la frontera con `publication/`**: sin ellos el frontend funciona para un lector y no funciona para G5.
- **IMP-30 cierra el círculo**: no se puede imprimir hasta que hay una versión publicada, y no hay versión publicada hasta que `render_visual` pasa.
- **H6 depende de P-160 a P-166 del plan del backend.** Mientras no estén, MSW sirve sus contratos; el orden de trabajo es el backend de seguimiento primero, porque el tablero y el panel no enseñan nada sin él, luego la operación, y el diseño a la vez que las pantallas y no después.
- **IMP-33 puede ir en cualquier momento, y cuanto antes mejor.** Informa y no bloquea, así que no rompe nada; mientras no esté, este plan se puede quedar atrás respecto de `frontend/src` sin que nadie lo vea, que es la deriva que §11e existe para señalar.

---

## 10. Lo que este plan no cubre

- **El diseño visual concreto**: tipografías, paleta y maquetación fina.
- **El backend**, salvo los tres ítems declarados como compartidos: IMP-26, IMP-33 y la parte de IMP-30 que imprime.
- **El lado del backend de IMP-26, IMP-27 e IMP-33**, que son `P-136`, `P-92`, `P-129` y `P-139` en su plan. Aquí se planifica lo que toca a `frontend/`.

---

## 11. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | Entra **IMP-52**: descargar el PDF | Baja de §4.3 de la spec |
| 2026-09-24 | Entra **IMP-51**: los lugares con nombre corto | Baja de §4.7 de la spec |
| 2026-09-24 | Entra **IMP-50**: la casilla de investigación exhaustiva | Baja de §4.2 de la spec |
| 2026-09-24 | Entran **IMP-47** (encargo por conversación), **IMP-48** (el gate de Intake como conversación) e **IMP-49** (sus pruebas) | Baja de §4.2 y §4.4 de la spec |
| 2026-09-24 | IMP-37 añade el logo de la empresa del Autor (`shared/ui/logo.png`), que usa el marco y el icono de la pestaña, e IMP-38 fija los tokens de la marca | Baja de §8 de la spec |
| 2026-09-24 | Entra **H6, la interfaz opera el arnés**, con IMP-34 a IMP-46: `entities/novela`, `shared/api` de seguimiento y operación, `useSondeo`, el kit ampliado, los tokens de diseño, el tablero tipo Jira, el encargo, el panel, el gate, la salida de cada fase, las rutas nuevas, el registro de libro en la lectura y sus pruebas. Se retiran IMP-13 (el listado es ahora el tablero) e IMP-19 (la redirección es ahora el panel) | Baja de arq. §16.5 y de la spec reescrita. Un ítem retirado deja su fila, porque su número no se reutiliza |
| 2026-09-24 | Al implementar: IMP-11 nombra los siete ficheros reales del kit (un fichero por componente, no una carpeta con su `index.ts`) y el estado `NoExiste`; IMP-12 recoge `useCarga`, IMP-13 `etiquetaDeFase` e IMP-18 `api/historial.ts`; IMP-01 fija que la API vive bajo `/api` también cuando FastAPI sirve el `dist/` | El inventario de P-129 señaló los diez módulos como «presente y no declarado». El prefijo no es gusto: la aplicación y la API comparten origen y las dos tienen rutas que empiezan por `/novelas`, así que sin él recargar la página de una novela devolvería su ficha en JSON |
| 2026-09-24 | IMP-29 nombra **`.mcp.json`** en la raíz, como declara ya §16.3 de la arquitectura; las contrapartes de IMP-26 e IMP-33 —`P-136` y `P-129`— recogen en el plan del backend la URL base y la lectura de las filas `IMP-nn` | La arquitectura resolvió dónde vive la configuración MCP y el plan del backend cerró lo que a este le faltaba de sus ítems compartidos: los tres hallazgos que la tercera pasada elevó al Autor |
| 2026-09-24 | Tras la tercera pasada de trazabilidad contra la arquitectura: entran **IMP-32** (sin copia local de la novela, §2, §15 y §16.4) e **IMP-33** (trazabilidad del frontend en CI, §1 y §11e, compartido con `P-129` y `P-139`); IMP-02 gana la **API pública por slice** de `pages/` y nombra las tres capas ausentes en su criterio; IMP-06, IMP-08 e IMP-09 ganan en su criterio los assets junto al código, las dos variables sin secreto, la ausencia de credenciales y el cliente sin reglas de negocio; IMP-10 cita su apartado de la arquitectura; IMP-23 deja de partir su fila con barras sin escapar; IMP-26 e IMP-30 nombran los símbolos de sus contrapartes (`montar_frontend`, `Settings.frontend_dist`, `render.py::imprimir_pdf`), e IMP-27 sitúa su prueba bajo `frontend/tests/` | Cinco decisiones de la arquitectura no tenían ítem, y cuatro filas de la matriz estaban en `CUBIERTO` con un criterio de hecho que no comprobaba lo que la fila afirmaba. Un ítem compartido que nombra ficheros distintos de los de su contraparte no es compartido: son dos planes que discrepan sin saberlo |
| 2026-09-23 | Cerradas las cinco costuras arriba: IMP-16 lee la ficha **versionada**, IMP-17 deja de declarar render degradado y dibuja la portada con el **bloque de paratexto**, y IMP-26 e IMP-27 nombran a sus contrapartes del backend, `P-136` y `P-92` | Un plan que declara comportamiento degradado para un hueco ya tapado construye el rodeo igualmente, y nadie vuelve a quitarlo |
| 2026-09-23 | Versión inicial: treinta y un ítems en seis hitos, con criterio de hecho por ítem | El frontend no tenía plan, y la matriz de trazabilidad que el Autor pidió necesita ítems con entregable y criterio para poder marcar cubierto algo sin mentir |
