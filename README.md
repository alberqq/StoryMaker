# StoryMaker

Arnés multiagente que escribe **novelas históricas personalizadas**. Se le da el nombre de una persona, una época y un puñado de recuerdos, y devuelve una novela de diez capítulos en la que esa persona es un personaje de un escenario histórico real y documentado: el padre que se jubila aparece como armador en el Cádiz de 1805; la pareja, como copista en un *scriptorium* del siglo XII.

La personalización es el *qué*. El rigor histórico es el *cómo*, y es lo que distingue el producto de pedirle un cuento a un modelo generalista: hay una fase de investigación con acceso a internet, un corpus que se sella y deja de admitir hechos nuevos, y una familia de validadores deterministas que comprueban que ningún objeto, término o concepto aparezca antes de existir.

> **Estado del proyecto.** Las seis fases están cableadas y el arnés recorre una novela entera, del encargo a la versión publicada, contra el modelo de verdad: las dos primeras novelas reales, las de [`ejemplos/brief-salamanca.yaml`](ejemplos/brief-salamanca.yaml) y [`ejemplos/brief-sevilla.yaml`](ejemplos/brief-sevilla.yaml), se publicaron y se leen desde la interfaz. La interfaz no solo lee: encarga, sigue y decide los gates. Lo que queda por demostrar, y con qué, está en [`docs/verification.md`](docs/verification.md).

## Por dónde empezar a leer

| Si quieres saber… | Lee |
|---|---|
| Quién hace qué, cómo recibe su contexto y cómo se detiene | [`docs/architecture.md`](docs/architecture.md) — es la fuente de verdad |
| La **spec inicial**: qué se decidió construir, y por qué, antes de escribir código | [`docs/architecture.md`](docs/architecture.md) §0-§1 («El producto en una frase» y «Decisiones fijadas») y las `specs/*/spec.md`. `architecture.md` nace en `e14b6a9` (2026-09-21) y `specs/backend/spec.md` en `89cf09a` (2026-09-23, 14:59), los dos antes del primer código de `backend/src`, que llega en `6928e7c` (2026-09-23, 18:07). Desde entonces ambos se han reescrito: la versión inicial es la de esos commits |
| Cómo se demuestra que funciona, y qué queda sin demostrar | [`docs/verification.md`](docs/verification.md) |
| Qué significa cada término del dominio | [`docs/definitions.md`](docs/definitions.md) |
| Cómo se relacionan los conceptos de la novela entre sí | [`docs/domain-knowledge.md`](docs/domain-knowledge.md) |
| Qué contrato expone cada pieza del backend | [`specs/backend/spec.md`](specs/backend/spec.md) |
| Qué pantallas tiene la interfaz y qué pide a la API | [`specs/frontend/spec.md`](specs/frontend/spec.md) |
| Cómo se concreta una capacidad concreta —el gate de Investigación, la Trama rehacible, la ejecución real— | su carpeta en [`specs/`](specs/), con spec y plan |
| Por qué el código está como está, paso a paso | [`docs/iteraciones.md`](docs/iteraciones.md) |
| Cómo se trabaja en este repositorio | [`AGENTS.md`](AGENTS.md) |

## Puesta en marcha

Requiere **Python 3.12** con [uv](https://docs.astral.sh/uv/) para el backend y **Node** con npm para la interfaz. Las dependencias, los extras y los grupos de desarrollo del backend viven en `backend/pyproject.toml`; las de la interfaz, en `frontend/package.json`.

```bash
git clone <este-repo> && cd StoryMaker
cp .env.example backend/.env          # y rellena lo que vayas a usar

cd backend
uv sync --group dev                   # lo justo para los tests
uv run pytest -q

cd ../frontend
npm install
npm test
```

Para generar novelas hacen falta además los extras del backend: `uv sync --group dev --extra agentes --extra embeddings --extra render`. El primero trae el Claude Agent SDK, el segundo FastEmbed, y el tercero Playwright, que imprime el PDF.

Ninguna clave es obligatoria para arrancar ni para correr los tests: los secretos nacen vacíos y quien los exige es el módulo que va a usarlos, en el momento de usarlos. Sin credenciales de Telegram los gates no notifican; sin las de Langfuse no se emiten trazas.

**No hay credencial de modelo, y es deliberado.** La única puerta al modelo es el Claude Agent SDK, que lanza Claude Code como subproceso y hereda la sesión ya iniciada del Autor. El arnés fija por invocación el modelo, las herramientas, los turnos y los techos, pero no autentica.

### Langfuse

1. Crea un proyecto en [cloud.langfuse.com](https://cloud.langfuse.com) y, en **Settings → API Keys**, un par de claves.
2. Ponlas en `backend/.env`: `STORYMAKER_LANGFUSE_PUBLIC_KEY`, `STORYMAKER_LANGFUSE_SECRET_KEY` y `STORYMAKER_LANGFUSE_HOST`, que es `https://cloud.langfuse.com` en la región europea y `https://us.cloud.langfuse.com` en la americana.
3. Siembra los prompts de rol una vez: `cd backend && uv run python -m storymaker.commons.obs.prompts subir`. Crea con la etiqueta `production` los que falten y no toca los que ya existan; a partir de ahí se editan en Langfuse, y cada edición es una versión nueva.

Lo que se ve después (arq. §14): una **sesión por novela**; dentro, una **traza por generación** —la de la versión 1, y otra por cada regeneración—; en cada traza, un span por capítulo con sus invocaciones de rol como `generation`, con tokens, coste estimado, latencia y la versión de prompt enlazada, y debajo cada llamada a herramienta. Los *scores* de todos los validadores, las decisiones de gate y las coincidencias del guardrail cuelgan de la traza de su generación.

## El brief de ejemplo

Una novela empieza por un **brief**: quién es el homenajeado, en qué mundo vive y con qué reglas se escribe. El de ejemplo está en [`ejemplos/brief-ejemplo.yaml`](ejemplos/brief-ejemplo.yaml), y junto a él hay otros tres —Salamanca, Sevilla y el de la exposición— que la pantalla de encargo ofrece como punto de partida:

```yaml
homenajeado:
  nombre_homenajeado: Ramón Iriarte Sologaray
  fecha_nacimiento: 1958-03-14
  rol_epoca: armador de navío mercante
  ocasion: jubilación tras cuarenta años en el puerto
  elementos_personalizacion:
    - { texto: "aprendió a navegar con su abuelo en una txalupa", obligatorio: true }
    - { texto: "le perdió el miedo al mar a los once años", obligatorio: true }
    - { texto: "colecciona cartas náuticas antiguas", obligatorio: false }

mundo:
  periodo: { inicio: 1803, fin: 1806, denominacion: Guerras Napoleónicas }
  lugar: Cádiz
  evento_ancla: la batalla de Trafalgar
  personajes_historicos:
    aparecen: [Federico Gravina]
    se_evitan: [Napoleón Bonaparte]

obra:
  genero: { principal: histórica, subgenero: marítima }
  tono: elegíaco con final luminoso
  grado_licencia: moderado
  arcaismo: moderado
  contenido_admisible: sin violencia explícita
  palabras_prohibidas:
    novela: [pirata, tesoro]
    destinatario: [naufragio]
  n_capitulos: 10
  palabras_por_capitulo: 1200
```

Para reproducirlo:

```bash
cd backend
uv run storymaker nueva ../ejemplos/brief-ejemplo.yaml --nombre ejemplo
```

`nueva` crea el fichero de la novela en `proyectos/` y **arranca la ejecución en el mismo paso**: no hay un segundo comando para lanzarla. Sin `--nombre`, el fichero toma el nombre del homenajeado. `--investigacion exhaustiva` cambia la sesión única de investigación por ocho sesiones dirigidas, más caras y más completas.

En modo interactivo el arnés se detiene en cinco gates a esperar tu decisión, y avisa por Telegram si está configurado. Telegram solo avisa: el gate se decide en el PC, y la decisión reanuda la ejecución en el mismo proceso.

```bash
uv run storymaker decidir ejemplo aprobar
uv run storymaker decidir ejemplo rehacer --comentario "lo que hay que cambiar"
```

Las decisiones son `aprobar`, `rehacer`, `editar` y `abortar`, y **abortar solo procede en el gate de Intake**, que es la única arista de un gate a `Fail` que declara el modelo TLA+. En los demás gates, no decidir deja la novela parada sin coste. Con `--batch` los cinco gates quedan desactivados y la ejecución corre sola.

Para seguir una novela, recuperarla tras un fallo o cambiarla después de publicada:

```bash
uv run storymaker estado ejemplo        # fase, gate abierto, capítulos aprobados y consumo
uv run storymaker continuar ejemplo     # reanuda desde el último checkpoint
uv run storymaker reintentar ejemplo    # reabre el capítulo que agotó sus reintentos
uv run storymaker desbloquear ejemplo   # rompe el cerrojo que deja un proceso muerto
uv run storymaker cambiar ejemplo "la petición"   # entra en la Fase 6; nada cambia hasta el gate
uv run storymaker ramificar ejemplo copia        # copia el fichero y anota su procedencia
```

Para revisar una novela publicada con la misma rúbrica que el juez, y comparar las dos notas:

```bash
uv run storymaker revision hoja ejemplo                  # la hoja en blanco, sin las notas del juez
uv run storymaker revision registrar ejemplo hoja.yaml --acta acta.md   # score y acta comparada
```

La cronología se verifica con **Lean 4** si `lake` está en el PATH, y con la misma evaluación en Python si no. Para instalarlo basta [elan](https://github.com/leanprover/elan) y un `lake build` en `formal/lean/`, que descarga el toolchain que fija `lean-toolchain`. `STORYMAKER_LEAN=0` lo apaga aunque esté instalado.

### Otro brief: diez años en Compostela

El de Cádiz es el caso cómodo: un período lleno de fechas duras en el que sobran fuentes. Para ver el arnés trabajar con poco, está [`ejemplos/evals/03-pareja.yaml`](ejemplos/evals/03-pareja.yaml), un regalo por diez años de pareja. La homenajeada es cerera y abastece de velas a la catedral de Santiago mientras el maestro Mateo termina el Pórtico de la Gloria, entre 1180 y 1188. Es justo la pareja del *scriptorium* del siglo XII con que empieza este README, llevada a un taller de cera.

```yaml
homenajeado:
  rol_epoca: cerera que abastece de velas a la catedral
  ocasion: diez años con su pareja
  elementos_personalizacion:
    - { texto: "conoció a su pareja haciendo el Camino de Santiago bajo la lluvia", obligatorio: true }
    - { texto: "canta en voz baja cuando está nerviosa", obligatorio: true }
    - { texto: "le encanta el olor a cera y a incienso", obligatorio: false }
mundo:
  periodo: { inicio: 1180, fin: 1188, denominacion: reino de León, siglo XII }
  lugar: Santiago de Compostela
  evento_ancla: la colocación de los dinteles del Pórtico de la Gloria en 1188
  personajes_historicos: { aparecen: [Maestro Mateo], se_evitan: [Fernando II de León] }
obra:
  genero: { principal: histórica, subgenero: romántica }
  tono: tierno y romántico, con humor suave
  palabras_prohibidas: { novela: [milagro], destinatario: [ruptura] }
  n_capitulos: 10
  palabras_por_capitulo: 1200
```

Lo que lo hace interesante es lo que le falta al mundo. Del siglo XII compostelano hay pocas páginas en la red, así que el corpus sale corto. El arquitecto tiene que cubrir huecos con micro-investigación o declarar invenciones autorizadas, y el juez tiene que decidir si la autenticidad de época aguanta igual. En su primera ejecución, en batch, **publicó los diez capítulos al primer o segundo intento, con un 7,0 del juez y 2,31 $** de consumo. El fichero anida el encargo bajo `brief:` y declara al lado qué se esperaba de él (`espera:`).

```bash
cd backend
uv run storymaker nueva ../ejemplos/evals/03-pareja.yaml --nombre compostela --batch
```

### Las novelas generadas, en otra máquina

`backend/proyectos/` no se versiona: cada novela es un fichero SQLite vivo. Una copia coherente de todas las generadas hasta la entrega —las siete evals, las novelas de referencia, las ramas de la demo y las paradas en cada fase— va en [`proyectos.zip`](proyectos.zip), hecha con la API de backup de SQLite. Para recuperarlas, se descomprime en la raíz del repositorio:

```bash
unzip proyectos.zip        # deja backend/proyectos/<novela>/<novela>.db, sus PDF y sus registros
```

## La interfaz

La interfaz la sirve la propia API de FastAPI desde `frontend/dist`, así que primero se construye y después se levanta el servidor:

```bash
cd frontend && npm run build
cd ../backend && uv run uvicorn storymaker.api.app:crear_app --factory --port 8765
```

Desde `http://127.0.0.1:8765` se opera la novela entera sin tocar la CLI: el **taller** reparte las novelas en un tablero por fases, y arrastrar una tarjeta que espera en un gate a la columna siguiente lo aprueba tras una confirmación; el **encargo** empieza por una conversación con el entrevistador; el **panel** de cada novela enseña sus fases, sus capítulos y su actividad, que se refresca sola; el **gate** enseña lo que hay que decidir, con el corpus o la revisión de la escaleta a la vista, y deja corregir filas antes de aprobar o rehacer. Cada acción lanza la CLI como proceso aparte: el servidor no guarda nada en memoria, y solo acepta acciones desde `127.0.0.1`.

En desarrollo, `npm run dev` en `frontend/` levanta Vite con un proxy de `/api` a FastAPI en el puerto 8000.

## Cómo lee el resultado quien recibe la novela

Se generan **las dos formas, y desde la misma fuente**: la lectura web en React —índice navegable, ficha de personajes y lugares enlazada a los capítulos donde aparecen, portada con dedicatoria— y el PDF, que se imprime con `page.pdf()` de Playwright **sobre esa misma ruta de lectura**. Maquetar el PDF aparte habría hecho que web y PDF divergieran, y la divergencia aparece siempre el día de la demo.

Cuando el lector pide un cambio —«mi abuelo no tenía una txalupa, tenía un bote»— no se regenera la novela entera: la tabla de hechos sabe qué capítulos usaron ese hecho, se invalidan solo esos, y la versión anterior se conserva. El PDF nuevo trae una página de novedades y el índice web marca lo que cambió.

## La correspondencia entre la especificación formal y el código

El comportamiento del arnés está especificado en TLA+ en [`formal/tla/harness.tla`](formal/tla/harness.tla), y TLC lo verifica sobre un modelo pequeño: 5 capítulos, 2 reintentos, una caída del proceso, un reintento manual y un cambio del lector. **Los nodos de LangGraph y los estados del modelo se llaman igual**, así que esta tabla no es una narración: es una lista de identidades. Una prueba la comprueba en G1 (`backend/tests/contratos/test_identidad_nodos.py`) comparando además la relación `ARISTAS` de `commons/graph/aristas.py` —por la que tiene que pasar todo enrutador, que revienta si elige una arista que no está— con la definición `Aristas` de la especificación, que es la que gobierna el `Next` que TLC explora.

Las acciones de la primera parte mueven el `pc` por una arista de `Aristas`. Las de la segunda son el entorno —el Autor, el proceso que cae, el lector— o escrituras en el checkpoint que no pasan por una arista.

| Acción TLA+ | Estado o transición del código | Efecto en SQLite |
|---|---|---|
| `Configure` | nodo `intake.configure` | Inserta `Brief`, abre `fase_run` |
| `Research` | nodo `investigation.research` | Puebla `mundo_*` con la ejecución vigente |
| `VerifyCorpus` | nodo `investigation.verify` | Escribe `respaldo` en `mundo_hecho`, sin tocar su `estado`, y el motivo del veredicto en `audit_log` |
| `Plan` | nodo `plotting.plan`, arista `tras_plan` | Puebla `canon_*` y `plan_*` |
| `FillGap` | nodo `plotting.fill_gap` | Inserta un `mundo_hecho` de micro-investigación; descuenta un hueco |
| `SealCorpus` | nodo `plotting.seal` | Escribe `mundo_sello` |
| `WriteChapter` | nodo `writing.write` | Inserta `capitulo_version` |
| `Validate` | nodo `writing.validate`, arista `tras_validate` | Inserta `incidencia` y `score` de la pasada determinista |
| `Extract` | nodo `writing.extract`, arista `tras_extract` | Puebla `uso_hecho`, `uso_hito`, `intake_uso_dato`, `continuidad` y `cronologia_evento`; `score` de la cronología del capítulo |
| `Repair` | nodo `writing.repair` | Inserta `capitulo_version` con `intento+1` |
| `ApproveChapter` | nodo `writing.approve` | Marca el estado del capítulo |
| `Checkpoint` | nodo `writing.checkpoint`, arista `tras_checkpoint` | Checkpoint de LangGraph, misma transacción; en regeneración saca el siguiente de `a_regenerar` |
| `Judge` | nodo `publication.judge`, arista `tras_judge` | Inserta `score` del juez |
| `PublishVersion` | nodo `publication.publish`, arista `tras_publish` | Corre la cronología completa y `render_visual` en Chromium sobre la candidata; si pasan inserta `version_novela` y `version_capitulo`, y si no, la `incidencia` del rechazo citando capítulos. Las dos dejan `score` |
| `RequestChange` | nodo `regeneration.request` | Modifica el hecho, registra en `audit_log` |
| `Invalidate` | nodo `regeneration.invalidate` | Marca capítulos posteriores |
| `RegenerateAffected` | nodo `regeneration.regenerate` | Nuevas `capitulo_version` |
| `Branch` | nodo `Branch` → `commons.graph.branch:fork`, que existe y solo termina la invocación. El `StateGraph` no cablea `Idle → Branch` (el router `tras_idle` va a `RequestChange` o a `END`): la ramificación real la hace `storymaker ramificar`, que llama a `commons.graph.branch:ramificar` fuera del grafo | Copia el fichero con el cerrojo del origen tomado, inserta `procedencia` |
| `AwaitApproval` … `AwaitApproval4` (estados; los mueven las acciones `Gate*` de abajo) | un solo nodo, `gates.await_approval`, compartido por los cuatro, con `interrupt()` | Inserta `gate` pendiente; en `AwaitApproval4`, la `incidencia` y el `score` de `cobertura_personalizacion` |
| `Aprobar` (dentro de `GateIntake` … `GateWriting`), `Rehacer` (de `GateIntake` a `GatePlotting`) y `Abortar` (solo en `GateIntake`) | `storymaker decidir`, o la pantalla del gate que lo lanza, y la arista `tras_espera` | Actualiza `gate`, reanuda con `Command(resume=...)` |
| `RehacerWriting` (dentro de `GateWriting`) | Lo mismo, en `AwaitApproval4` | Pone `regenerando` y la cola `a_regenerar` con los capítulos que citan las incidencias de la novela |
| `IdleRequest` | `storymaker decidir` en el gate de Regeneración, que llama a `commons.graph.run:regenerar`; el nodo `Idle` (`commons.graph.nodos:idle`) y su router `tras_idle` la llevan a `RequestChange` | Escribe `pc = RequestChange` como salida de `Idle`; pone a cero los rechazos |
| `Caida` | El proceso muere | Nada: lo que el nodo no confirmó no existe |
| `ResumeFromCheckpoint` | `storymaker continuar`, con `Command(resume=...)` | Nada: se vuelve a ejecutar el nodo pendiente |
| `Reintentar` | `storymaker reintentar`, con `aupdate_state(..., as_node="SealCorpus")` | Reabre el capítulo con los intentos a cero; lo aprobado no se toca |
| `Terminado` | los nodos terminales `Fail` (`commons.graph.nodos:fail`) y `Branch`, con arista a `END` | Nada: la invocación termina y el estado queda en el checkpoint |

Los invariantes y las propiedades temporales que TLC comprueba están en [`formal/tla/README.md`](formal/tla/README.md), junto con el resultado de cada configuración, los contraejemplos que encontró y qué se cambió por cada uno.

## Las dos decisiones que explican el resto

**Los validadores son nodos del grafo, no herramientas que un agente elige llamar.** Lo que un modelo puede olvidarse de invocar no es una comprobación, es una sugerencia. Las aristas condicionales leen booleanos calculados en Python, así que ningún agente puede saltarse una validación aunque quiera.

**El estado vive en un fichero SQLite por novela, y en ningún otro sitio.** El checkpoint del grafo y el capítulo recién aprobado se escriben en la misma transacción, de modo que no existe el instante en que el grafo cree que el capítulo 6 está hecho y la biblia no lo tenga. Una novela es un fichero: ramificarla es copiarlo y descargarla es copiarlo.

## Estructura del repositorio

```
backend/          FastAPI + LangGraph, package by feature: una fase es una carpeta
frontend/         React + Vite, Feature-Sliced Design v2.1
formal/tla/       Especificación TLA+/PlusCal del arnés, con su modelo para TLC
formal/lean/      Validador formal de la cronología de la historia, en Lean 4
ejemplos/         Los briefs de ejemplo, en YAML
semgrep/          Seis reglas propias que vigilan las invariantes del arnés en G1
docs/             Arquitectura, verificación, ontología, explainers e iteraciones
specs/            Spec y plan por componente y por capacidad
.claude/          Skills instaladas, con su procedencia en docs/skills.md, y el hook que
                  valida la continuidad de cada capítulo editado a mano
```

## Licencia y alcance

Ejercicio académico. No hay garantía de nada, y el arnés no está pensado para correr desatendido contra dinero real.
