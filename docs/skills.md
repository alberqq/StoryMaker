# Skills, subagentes y comandos

Qué capacidades de Claude Code usa este repositorio, de dónde vienen y para qué sirve cada una **en esta pila concreta**. El inventario con la procedencia exacta —repositorio de origen, commit y reparaciones aplicadas— vive en [`.claude/skills/PROCEDENCIA.md`](../.claude/skills/PROCEDENCIA.md); este documento es la vista desde el proyecto, que es lo que hace falta para decidir si una skill sobra o falta.

## El criterio

**Las skills se instalan copiando el directorio desde su fuente, y no se editan a mano** salvo para reparar rutas que solo tienen sentido en el repositorio de origen. Si hace falta cambiar una, se vuelve a copiar desde el origen. La razón es que una skill editada localmente es una bifurcación silenciosa: sigue pareciendo la de upstream, deja de comportarse como ella, y nadie lo nota hasta que upstream cambia.

Cada reparación aplicada queda anotada en `PROCEDENCIA.md` con lo que se tocó y por qué.

## Las trece instaladas

Agrupadas por la parte del sistema a la que sirven.

### El motor de orquestación

| Skill | Sirve a |
|---|---|
| `langgraph-architecture` | Las decisiones de §3, §8 y §9 de la arquitectura: el grafo, las ejecuciones de fase y la máquina de estados |
| `langgraph-implementation` | La escritura de los nodos y las aristas condicionales |
| `langgraph-code-review` | La revisión de lo anterior |

### La persistencia y el contexto

| Skill | Sirve a |
|---|---|
| `sqlite-vec` | Las tablas `vec0` de los índices semánticos (§7 y §16.2). Son la gestión de contexto: deciden qué porción del material entra en cada paquete |

### La superficie web

| Skill | Sirve a |
|---|---|
| `fastapi-code-review` | La API, el webhook de Telegram y la reanudación de gates (§10) |
| `feature-sliced-design` | La organización del frontend en FSD v2.1 (§16.3) |
| `webapp-testing` | La validación visual del lector y la ruta desde la que se imprime el PDF (§16.1) |

### La verificación formal

| Skill | Sirve a |
|---|---|
| `lean-proof` | Los invariantes de la cronología (§11c). Del repositorio **oficial** de Lean |
| `lean4-setup` | El proyecto Lake y las toolchains de `elan` |
| `tlaplus` | La especificación del arnés y las ejecuciones de TLC (§11d) |

### El código Python

| Skill | Sirve a |
|---|---|
| `python-code-review` | Backend Python 3.12 |
| `pytest-code-review` | La técnica 5 del plan de verificación |
| `review-verification-protocol` | No se usa sola: las dos anteriores y `fastapi-code-review` la referencian por ruta relativa, y sin ella quedan rotas |

## La skill propia que falta

§19 de la arquitectura declara `continuity-check` como **la skill reutilizable del proyecto**, y hoy no existe. Es la única prevista como creación propia y no como instalación: expondría a Claude Code la misma validación de continuidad que corre dentro del grafo, para que una persona que edita un capítulo a mano en el disco pueda comprobar que su edición no ha roto los guardrails ni la continuidad antes de commitear o de regenerar el PDF.

El punto importante de su diseño es que **no es una segunda implementación**. §15 lo dice con todas las letras: la validación vive en el Core Domain, y tanto el nodo del grafo como el hook de `.claude/` la invocan. Una skill que reimplementara la comprobación sería la forma más rápida de que la edición manual y la generación empezaran a discrepar.

Queda pendiente del tramo del plan que implemente `commons/validation/`.

## Subagentes y comandos propios

**No hay.** `ls -a .claude/` devuelve solo `skills`: no existen `.claude/agents/` ni `.claude/commands/`.

Es deliberado y conviene decir por qué, porque la ausencia se lee mal. Los nueve roles de este sistema **no son subagentes de Claude Code**: son invocaciones del Claude Agent SDK desde el orquestador, con su modelo, sus herramientas y su techo de turnos fijados por invocación. Definirlos además como subagentes de `.claude/` crearía dos definiciones del mismo rol —una que el arnés usa en producción y otra que solo existe cuando el Autor trabaja en el repositorio— y la segunda derivaría de la primera sin que nada lo detectara.

Si en algún momento se añaden, este apartado deja de estar vacío y pasa a ser su inventario.

## Lo que este documento no cubre

El inventario de skills **deliberadamente no instaladas**, con el motivo de cada descarte, está al final de [`PROCEDENCIA.md`](../.claude/skills/PROCEDENCIA.md). Se mantiene allí y no aquí porque es una decisión sobre el entorno de trabajo, no sobre la arquitectura del producto.
