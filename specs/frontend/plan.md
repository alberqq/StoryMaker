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
| **H1** | `shared/`: el cliente único, los errores y el kit | G1 |
| **H2** | Las seis pantallas leyendo de la API | G1, G2 |
| **H3** | La petición de cambio del lector | G1, G2 |
| **H4** | El modo impresión, el PDF y la condición de G5 | G5 |
| **H5** | Verificación de extremo a extremo y entrega | G2, G5 |

El criterio de corte de cada hito es el mismo que en el backend: **el hito termina cuando su parte de la comprobación está en verde, no cuando el código existe.**

---

## 2. H0 · Andamiaje, capas y rutas

| # | Entregable | Ficheros y símbolos | Criterio de hecho | Arq. | Gate |
|---|---|---|---|---|---|
| **IMP-01** | Proyecto **React + Vite** con TypeScript en `frontend/`, con los scripts `dev`, `build`, `preview`, `tipos` y `estructura` | `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html` | `npm run build` produce `dist/`; `npm run dev` sirve la aplicación con el proxy de `/api` contra FastAPI | §16.1 | G1 |
| **IMP-02** | Árbol **FSD v2.1** con el juego mínimo: `app/`, `pages/`, `shared/` con un `index.ts` **por segmento** de `shared`. Sin `widgets/`, sin `features/` y sin `entities/` | `frontend/src/{app,pages,shared}/…`, `shared/{api,ui,lib,config}/index.ts` | No existe `shared/index.ts` único ni carpeta de capa vacía; Steiger no reporta violación de capa | §16.3 | G1 |
| **IMP-03** | Alias `@/app`, `@/pages`, `@/shared` declarados **con el mismo mapa** en `tsconfig.json` y en `vite.config.ts` | `frontend/tsconfig.json::paths`, `frontend/vite.config.ts::resolve.alias` | Un import por alias compila con `tsc` y resuelve en `dev` y en `build`; los dos mapas coinciden literalmente | §16.3 | G1 |
| **IMP-04** | **Steiger** como script y como trabajo de CI que **informa y no bloquea**, con su salida publicada junto al informe de G1 | `frontend/package.json::scripts.estructura`, `.github/workflows/ci.yml` (trabajo `frontend-estructura`) | El trabajo publica la salida de `npx steiger src` y **termina en verde aunque haya hallazgos** | §16.1, §16.3, verif. §3.2 | G1 |
| **IMP-05** | Generación de los **tipos de transporte desde el OpenAPI** que FastAPI publica; no se escriben a mano | `frontend/scripts/generar-tipos.ts`, `shared/api/transporte.ts` (generado) | Regenerar contra un backend con un endpoint cambiado hace fallar `tsc`; el fichero generado está marcado como tal y no se edita | §16.3, spec §7 | G1 |
| **IMP-06** | `app/styles`: reset, tipografía de lectura, **fuentes locales** y la hoja `@media print` | `app/styles/global.css`, `app/styles/print.css`, `app/styles/fonts/` | Las fuentes se sirven desde el propio origen —sin petición a terceros— y la hoja de impresión oculta la navegación | §16.3 | G1 |
| **IMP-07** | `app/router.tsx` con las **ocho rutas** de §3 de la spec y `app/providers` | `app/router.tsx::rutas`, `app/providers/index.tsx`, `app/main.tsx` | Cada ruta monta su página; una ruta desconocida cae en la pantalla de «no existe»; ninguna ruta de lectura carece de versión | §7, §16.3, spec §3 | G1 |
| **IMP-08** | `shared/config`: **constructores de ruta** (`rutaCapitulo`, `rutaPersonajes`, `rutaPortada`, `rutaImprimir`, `rutaVersiones`) y lectura de `VITE_API_URL` y `VITE_BASE_PATH` | `shared/config/rutas.ts`, `shared/config/entorno.ts` | Ninguna página construye una URL con plantilla propia, y ninguna slice de `pages/` importa de otra | §16.3, spec §3 | G1 |

**Lo que rompe:** nada. H0 no enseña todavía ninguna novela.

---

## 3. H1 · `shared/`: cliente, errores y kit

| # | Entregable | Ficheros y símbolos | Criterio de hecho | Arq. | Gate |
|---|---|---|---|---|---|
| **IMP-09** | **Cliente único** de la API: una instancia, base tomada de `shared/config`, y el **único punto del código que emite red** | `shared/api/cliente.ts::cliente`, `shared/api/novelas.ts`, `shared/api/versiones.ts` | Una prueba de repositorio falla si aparece `fetch(`, `XMLHttpRequest` o una segunda instancia de cliente fuera de `shared/api/` | §16.3, spec §6 | G1, G5 |
| **IMP-10** | **Errores tipados** `NoEncontrado`, `NovelaOcupada` y `SinRespuesta`, traducidos desde el código HTTP **una sola vez** | `shared/api/errores.ts` | Ningún módulo de `pages/` menciona `404`, `409` ni `status` | spec §7, §9 | G1 |
| **IMP-11** | Kit de `shared/ui`: `Pagina`, `Tarjeta`, `Tabla`, `Boton`, `EnlaceCapitulo`, `MarcaCambiado` y los tres estados `EstadoCarga`, `EstadoError`, `EstadoVacio` | `shared/ui/*/index.ts` | Los tres estados existen como componentes y **toda pantalla los usa**: no hay ninguna que se quede en blanco mientras carga | §16.3, spec §4 | G1 |
| **IMP-12** | `shared/lib`: hook de **selección de texto** y formateo de fecha y de puntuación | `shared/lib/seleccion.ts::useSeleccion`, `shared/lib/formato.ts` | El hook devuelve el fragmento seleccionado y el capítulo en el que se seleccionó, y cadena vacía cuando no hay selección | §16.3, spec §5 | G1 |

**Lo que rompe:** nada; no hay pantalla que consuma esto todavía.

---

## 4. H2 · Las seis pantallas

| # | Entregable | Ficheros y símbolos | Criterio de hecho | Arq. | Gate |
|---|---|---|---|---|---|
| **IMP-13** | `pages/library`: listado de novelas del directorio `proyectos/` con título, fase en curso y número de versiones | `pages/library/ui/Biblioteca.tsx`, `pages/library/api/listar.ts`, `pages/library/index.ts` | Una novela **sin versiones publicadas aparece sin enlace de lectura**; un directorio vacío se anuncia como vacío y no como error | §16.4 | G1 |
| **IMP-14** | `pages/reading`, vista de **índice**: capítulos del manifiesto en orden, con su número y su título, y **marca de capítulo cambiado** respecto de la versión anterior | `pages/reading/ui/Indice.tsx`, `pages/reading/api/manifiesto.ts`, `pages/reading/model/cambiados.ts` | La marca sale del endpoint de diff, no de comparar textos en el cliente; sin versión anterior, no hay marcas y no hay petición de diff | §4 F5, §4 F6, §16.3 | G1, G2 |
| **IMP-15** | `pages/reading`, vista de **capítulo**: el texto tal como esa versión lo fija, con anterior, siguiente y vuelta al índice | `pages/reading/ui/Capitulo.tsx`, `pages/reading/api/capitulo.ts` | Un capítulo inexistente muestra la pantalla de «no existe»; el primero no ofrece anterior y el último no ofrece siguiente | §7, §4 F5 | G1 |
| **IMP-16** | `pages/characters`: fichas de personajes y de escenarios, **cada entrada enlazada a los capítulos donde aparece**, leídas de `GET /novelas/{id}/versiones/{n}/personajes` | `pages/characters/ui/Fichas.tsx`, `pages/characters/api/personajes.ts` | El enlace lleva la versión de la ruta; una ficha sin apariciones se muestra sin enlaces y **no se oculta** | §4 F5, §16.3 | G1, G2 |
| **IMP-17** | `pages/cover`: título, **dedicatoria** con la ocasión y **nota del autor** con las Licencias declaradas | `pages/cover/ui/Portada.tsx`, `pages/cover/api/paratexto.ts` | Renderiza con el **bloque de paratexto** que devuelve el endpoint de versión; una novela sin Licencias declaradas enseña la portada y omite la nota, que es un caso legítimo y no un fallo | §4 F5, §16.3 | G1, G2 |
| **IMP-18** | `pages/versions`: historial con fecha y puntuación del juez, apertura de cualquier versión anterior y **diff entre dos** | `pages/versions/ui/Historial.tsx`, `pages/versions/api/diff.ts` | Una versión anterior se abre entera y legible; el diff lista los capítulos que cambian entre los dos manifiestos | §4 F6, §7, §8 | G1 |
| **IMP-19** | Redirección de `/novelas/:id` a la **última versión publicada**, y a la ficha con su fase si todavía no hay ninguna | `app/router.tsx::redireccionVersion` | Ninguna ruta de lectura queda sin número de versión | §7 | G1 |

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
| **IMP-23** | **Anclas estables** `data-render="indice|portada|personajes|novedades"` y un `id` por capítulo | `pages/print/ui/*`, `pages/reading/ui/Indice.tsx` | Los cuatro selectores existen en el DOM renderizado y **no dependen de ninguna clase de CSS ni de ningún rótulo visible** | §11a, spec §6 | G5 |
| **IMP-24** | **Enlaces internos por ancla** en el índice, en la ficha de personajes y en la página de novedades | `pages/print/ui/Indice.tsx`, `pages/print/ui/Novedades.tsx` | En el PDF impreso los enlaces saltan a su destino dentro del documento | §4 F5, §4 F6 | G5 |
| **IMP-25** | **Página de novedades** cuando la versión tiene predecesora, construida desde el endpoint de diff | `pages/print/ui/Novedades.tsx` | Sin predecesora la sección se omite entera y el índice no la enlaza | §4 F6 | G5 |
| **IMP-26** | **FastAPI monta el `dist/` construido** y declara la URL base con la que Playwright abre la lectura. *Ítem compartido con el backend*, donde es `P-136` | `backend/src/storymaker/api/estaticos.py`, `commons/config.py::Settings.frontend_base_url`, `frontend/package.json::scripts.build` | `render_visual` y el PDF abren **la misma URL del mismo origen** que el lector; no hace falta un segundo proceso vivo | §16.1, §16.4 | G5 |
| **IMP-27** | **Contrato de interceptación**: todas las peticiones salen del cliente único, de modo que el navegador de `render_visual` pueda servirlas desde el manifiesto candidato que vive en la transacción abierta. El lado del backend es `P-92` | `shared/api/cliente.ts`, `tests/estructura/cliente-unico.test.ts` | La prueba falla si algún módulo fuera de `shared/api` emite red; `render_visual` renderiza la versión candidata **sin que esté publicada** | §4 F5, §11a | G5 |

**Lo que rompe:** IMP-26 cambia cómo se sirve la aplicación. Mientras no esté, `render_visual` no tiene URL que abrir y el PDF tampoco.

---

## 7. H5 · Verificación y entrega

| # | Entregable | Ficheros y símbolos | Criterio de hecho | Arq. | Gate |
|---|---|---|---|---|---|
| **IMP-28** | Pruebas de componente e integración con **MSW** sobre los contratos de `shared/api`, incluidos los siete casos de error de §9 de la spec | `frontend/tests/**` | Los siete casos de error tienen prueba, y la suite corre en el mismo trabajo de CI que Steiger | verif. §3.5 | G1 |
| **IMP-29** | Recorrido con **Playwright MCP**: índice navegable, enlaces de la ficha y portada con dedicatoria, más la configuración del MCP en el harness | `.claude/mcp.json`, `frontend/tests/recorrido.md` | Se demuestran LEC-02, LEC-04 y LEC-05 sobre una novela real, y el acta queda con el informe de G2 | §19, verif. §2 nº 11 | G2 |
| **IMP-30** | **`ejemplos/novela-ejemplo.pdf`** impreso con `page.pdf()` desde la ruta de impresión de una versión publicada | `ejemplos/novela-ejemplo.pdf`, `backend/src/storymaker/publication/pdf.py` | El PDF tiene los diez capítulos, índice con enlaces que saltan y portada con dedicatoria (ENT-06) | §16.1, §4 F5 | G5 |
| **IMP-31** | **Castellano** en toda la interfaz, sin capa de internacionalización | `frontend/src/**` | No hay fichero de traducciones ni cadena en inglés visible al lector | §19 | G1 |

---

## 8. Dependencias y qué se rompe mientras tanto

- **H2 depende de la API**, no del backend entero: mientras las pantallas se construyen, MSW sirve los contratos y el desarrollo no espera.
- **IMP-16 e IMP-17 dependen de dos endpoints concretos** —la ficha versionada y el bloque de paratexto—, que la spec del backend ya contrata en su §5. Dejaron de necesitar comportamiento degradado el día que esos dos endpoints se declararon.
- **IMP-26 e IMP-27 son la frontera con `publication/`**: sin ellos el frontend funciona para un lector y no funciona para G5.
- **IMP-30 cierra el círculo**: no se puede imprimir hasta que hay una versión publicada, y no hay versión publicada hasta que `render_visual` pasa.

---

## 9. Lo que este plan no cubre

- **El diseño visual concreto**: tipografías, paleta y maquetación fina.
- **El backend**, salvo los dos ítems declarados como compartidos, IMP-26 y su parte de IMP-30.
- **El lado del backend de IMP-26 e IMP-27**, que son `P-136` y `P-92` en su plan. Aquí se planifica lo que toca a `frontend/src`.

---

## 10. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-23 | Cerradas las cinco costuras arriba: IMP-16 lee la ficha **versionada**, IMP-17 deja de declarar render degradado y dibuja la portada con el **bloque de paratexto**, y IMP-26 e IMP-27 nombran a sus contrapartes del backend, `P-136` y `P-92` | Un plan que declara comportamiento degradado para un hueco ya tapado construye el rodeo igualmente, y nadie vuelve a quitarlo |
| 2026-09-23 | Versión inicial: treinta y un ítems en seis hitos, con criterio de hecho por ítem | El frontend no tenía plan, y la matriz de trazabilidad que el Autor pidió necesita ítems con entregable y criterio para poder marcar cubierto algo sin mentir |
