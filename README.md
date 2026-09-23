# StoryMaker

Arnés multiagente que escribe **novelas históricas personalizadas**. Se le da el nombre de una persona, una época y un puñado de recuerdos, y devuelve una novela de diez capítulos en la que esa persona es un personaje de un escenario histórico real y documentado: el padre que se jubila aparece como armador en el Cádiz de 1805; la pareja, como copista en un *scriptorium* del siglo XII.

La personalización es el *qué*. El rigor histórico es el *cómo*, y es lo que distingue el producto de pedirle un cuento a un modelo generalista: hay una fase de investigación con acceso a internet, un corpus que se sella y deja de admitir hechos nuevos, y una familia de validadores deterministas que comprueban que ningún objeto, término o concepto aparezca antes de existir.

> **Estado del proyecto.** En construcción. El andamiaje, las puertas estáticas y la persistencia están implementados; las seis fases todavía no. [`docs/requirements-audit.md`](docs/requirements-audit.md) dice exactamente qué hay y qué falta, con evidencia por línea.

## Por dónde empezar a leer

| Si quieres saber… | Lee |
|---|---|
| Quién hace qué, cómo recibe su contexto y cómo se detiene | [`docs/architecture.md`](docs/architecture.md) — es la fuente de verdad |
| Cómo se demuestra que funciona, y qué queda sin demostrar | [`docs/verification.md`](docs/verification.md) |
| Qué significa cada término del dominio | [`docs/definitions.md`](docs/definitions.md) |
| Cómo se relacionan los conceptos de la novela entre sí | [`docs/domain-knowledge.md`](docs/domain-knowledge.md) |
| Qué contrato expone cada pieza del backend | [`specs/backend/spec.md`](specs/backend/spec.md) |
| Por qué el código está como está, paso a paso | [`docs/iteraciones.md`](docs/iteraciones.md) |

## Puesta en marcha

Requiere **Python 3.12** y [uv](https://docs.astral.sh/uv/). Las dependencias, los extras y los grupos de desarrollo viven en `backend/pyproject.toml`.

```bash
git clone <este-repo> && cd StoryMaker
cp .env.example backend/.env          # y rellena lo que vayas a usar
cd backend
uv sync --group dev
uv run pytest -q
```

Ninguna clave es obligatoria para arrancar ni para correr los tests: los secretos nacen vacíos y quien los exige es el módulo que va a usarlos, en el momento de usarlos. Sin credenciales de Telegram los gates no notifican; sin las de Langfuse no se emiten trazas.

**No hay credencial de modelo, y es deliberado.** La única puerta al modelo es el Claude Agent SDK, que lanza Claude Code como subproceso y hereda la sesión ya iniciada del Autor. El arnés fija por invocación el modelo, las herramientas, los turnos y los techos, pero no autentica.

## El brief de ejemplo

Una novela empieza por un **brief**: quién es el homenajeado, en qué mundo vive y con qué reglas se escribe. El de ejemplo está en [`ejemplos/brief-ejemplo.yaml`](ejemplos/brief-ejemplo.yaml) y es el que genera la novela de muestra:

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
uv run storymaker nueva --brief ../ejemplos/brief-ejemplo.yaml
uv run storymaker correr --novela ramon-iriarte
```

En modo interactivo el arnés se detiene en cinco puntos a esperar tu decisión y avisa por Telegram. Con `--batch` los cinco gates quedan desactivados y la ejecución corre sola, que es como se pasan los briefs de evaluación de [`evals/`](evals/).

## Cómo lee el resultado quien recibe la novela

Se generan **las dos formas, y desde la misma fuente**: la lectura web en React —índice navegable, ficha de personajes y lugares enlazada a los capítulos donde aparecen, portada con dedicatoria— y el PDF, que se imprime con `page.pdf()` de Playwright **sobre esa misma ruta de lectura**. Maquetar el PDF aparte habría hecho que web y PDF divergieran, y la divergencia aparece siempre el día de la demo.

Cuando el lector pide un cambio —«mi abuelo no tenía una txalupa, tenía un bote»— no se regenera la novela entera: la tabla de hechos sabe qué capítulos usaron ese hecho, se invalidan solo esos, y la versión anterior se conserva. El PDF nuevo trae una página de novedades y el índice web marca lo que cambió.

## La correspondencia entre la especificación formal y el código

El comportamiento del arnés está especificado en TLA+/PlusCal en [`formal/tla/harness.tla`](formal/tla/harness.tla), y TLC lo verifica sobre un modelo pequeño. **Los nodos de LangGraph y las acciones de PlusCal se llaman igual**, así que esta tabla no es una narración: es una lista de identidades, y hay una prueba que la comprueba en CI comparando además el conjunto de aristas del `StateGraph` con la definición `Aristas` de la especificación.

| Acción PlusCal | Nodo LangGraph | Efecto en SQLite |
|---|---|---|
| `Configure` | `intake.configure` | Inserta `Brief`, abre `fase_run` |
| `Research` | `investigation.research` | Puebla `mundo_*` con la ejecución vigente |
| `VerifyCorpus` | `investigation.verify` | Escribe `respaldo` y degrada `estado` en `mundo_hecho` |
| `Plan` | `plotting.plan` | Puebla `canon_*` y `plan_*` |
| `FillGap` | `plotting.fill_gap` | Inserta un `mundo_hecho` de micro-investigación; descuenta un hueco |
| `SealCorpus` | `plotting.seal` | Escribe `mundo_sello` |
| `WriteChapter` | `writing.write` | Inserta `capitulo_version` |
| `Validate` | `writing.validate` | Inserta `incidencia` y `score` de la pasada determinista |
| `Extract` | `writing.extract` | Puebla `uso_hecho`, `intake_uso_dato`, `continuidad` y `cronologia_evento` |
| `Repair` | `writing.repair` | Inserta `capitulo_version` con `intento+1` |
| `ApproveChapter` | `writing.approve` | Marca el estado del capítulo |
| `Checkpoint` | `writing.checkpoint` | Checkpoint de LangGraph, misma transacción |
| `AwaitApproval` | `gates.await` | `interrupt()`, inserta `gate` pendiente |
| `HumanDecide` | endpoint FastAPI | Actualiza `gate`, reanuda con `Command(resume=...)` |
| `Judge` | `publication.judge` | Inserta `score` del juez |
| `PublishVersion` | `publication.publish` | Renderiza, corre `render_visual` e inserta `version_novela` y `version_capitulo` |
| `RequestChange` | `regeneration.request` | Modifica el hecho, registra en `audit_log` |
| `Invalidate` | `regeneration.invalidate` | Marca capítulos posteriores |
| `RegenerateAffected` | `regeneration.regenerate` | Nuevas `capitulo_version` |
| `ResumeFromCheckpoint` | `graph.invoke(Command(...))` | Lee checkpoint |
| `Branch` | `branch.fork` | Copia el fichero, inserta `procedencia` |

Los invariantes y la propiedad de liveness que TLC comprueba están en [`formal/tla/README.md`](formal/tla/README.md), junto con los contraejemplos que encontró y qué se cambió por cada uno.

## Las dos decisiones que explican el resto

**Los validadores son nodos del grafo, no herramientas que un agente elige llamar.** Lo que un modelo puede olvidarse de invocar no es una comprobación, es una sugerencia. Las aristas condicionales leen booleanos calculados en Python, así que ningún agente puede saltarse una validación aunque quiera.

**El estado vive en un fichero SQLite por novela, y en ningún otro sitio.** El checkpoint del grafo y el capítulo recién aprobado se escriben en la misma transacción, de modo que no existe el instante en que el grafo cree que el capítulo 6 está hecho y la biblia no lo tenga. Una novela es un fichero: ramificarla es copiarlo y descargarla es copiarlo.

## Estructura del repositorio

```
backend/          FastAPI + LangGraph, package by feature: una fase es una carpeta
frontend/         React + Vite, Feature-Sliced Design v2.1
formal/tla/       Especificación TLA+/PlusCal del arnés, con su modelo para TLC
formal/lean/      Validador formal de la cronología de la historia, en Lean 4
evals/            Los cinco briefs de evaluación y sus resultados
semgrep/          Seis reglas propias que vigilan las invariantes del arnés en CI
docs/             Arquitectura, verificación, ontología, explainers e iteraciones
specs/            Spec y plan por componente
.claude/          Skills instaladas; su procedencia, en docs/skills.md
```

## Licencia y alcance

Ejercicio académico. No hay garantía de nada, y el arnés no está pensado para correr desatendido contra dinero real.
