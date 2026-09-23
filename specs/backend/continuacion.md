# Continuación — dónde se quedó el backend y qué sigue

Documento de traspaso. Está escrito para **una sesión de Claude Code que empieza de cero en otra máquina**, sin nada del contexto de la sesión que dejó el trabajo aquí. Todo lo que hace falta para seguir está en este fichero o enlazado desde él.

Lee primero [`AGENTS.md`](../../AGENTS.md) de la raíz: fija la rama de trabajo, el flujo *spec-driven* y el criterio de producto, y **manda sobre este documento**. Lo de aquí es el estado y la cola de trabajo, no las reglas.

---

## 1. Estado, con números comprobados

| Qué | Estado |
|---|---|
| Ítems del plan del backend | **139**, todos con código |
| Nodos del grafo resueltos | **24 de 24**; `nodos_pendientes()` devuelve `[]` |
| Suite | **661 pasan, 1 se salta** |
| `ruff` y `mypy --strict` | limpios sobre 111 ficheros |
| `inventario_del_plan` | 0 declarados-y-ausentes · 0 presentes-y-no-declarados *(ver §2, se rompió al añadir `encargo.py`)* |
| Matriz de trazabilidad de la raíz | 0 huecos |
| Requisitos | 131 `REQ-BE-nn` + 51 `REQ-FE-nn`, sin fantasmas ni repetidos |
| Frontend | **0 de 31 ítems**; `frontend/` está vacío |

Las seis fases están cableadas y **el sistema recorre una novela entera de `Configure` a `PublishVersion`** con un transporte falso: lo comprueba [`tests/integracion/test_extremo_a_extremo.py`](../../backend/tests/integracion/test_extremo_a_extremo.py). Lo que no se ha hecho nunca es recorrerla **con un modelo de verdad**, y eso es el paso B.

Para reproducir estos números:

```bash
cd backend
uv run pytest -q
uv run ruff check src/ tests/ ../evals/
uv run mypy
uv run python -c "from storymaker.commons.graph.construccion import nodos_pendientes; print(nodos_pendientes())"
uv run python -c "import sys; sys.path.insert(0,'tests'); from correspondencia.test_inventario import cubos; print(cubos())"
```

> `remaining.md` de la raíz **está desfasado**: describe H6 y H7 como «sin empezar» y habla de 503 pruebas. Es de antes de la implementación. No lo uses como estado; o se reescribe o se borra.

---

## 2. Paso A — cerrar la propagación documental

Trabajo mecánico, media hora, sin decisiones. Es lo primero porque **deja el repositorio consistente consigo mismo**, y los validadores de correspondencia lo comprueban.

### A.1 Declarar en el plan lo que se implementó al final

[`specs/backend/plan.md`](plan.md) no nombra tres cosas que ya existen. Mientras no lo haga, `inventario_del_plan` las señalará como «presente y no declarado», que es exactamente la deriva que ese validador busca.

| Fichero que existe | Ítem que debe declararlo | Por qué existe |
|---|---|---|
| `backend/src/storymaker/intake/encargo.py` | **P-113** (la CLI) y **P-120** (los evals) | Lee el fichero de encargo y lo convierte en la premisa con la que arranca la Fase 1 |
| `.github/workflows/nocturna.yml` | **P-119**, cuya celda de ficheros dice hoy solo «CI nocturna» | Es la puerta G2: `mutmut` y CrossHair, ninguno bloqueante |
| `[tool.mutmut]` en `backend/pyproject.toml` | **P-119** | El alcance de la mutación, para que local y CI midan lo mismo |

Y añadir una fila al registro de cambios de §12 del plan explicando las tres.

### A.2 Corregir lo que los documentos afirman y ya no es cierto

| Documento | Qué dice | Qué hacer |
|---|---|---|
| [`docs/verification.md`](../../docs/verification.md) §3.3 | La fila de `normalizar` describe el contrato explorado por CrossHair | Ese contrato **ahora sí se cumple**, porque `_singular` recorta hasta punto fijo. Conviene que la celda diga por qué, y que el registro de cambios recoja el hallazgo (ver §5.1) |
| [`ejemplos/brief-ejemplo.yaml`](../../ejemplos/brief-ejemplo.yaml) | El bloque «Reproducir» invoca `storymaker correr --novela ramon-iriarte` | **Ese comando no existe.** Los comandos reales son los de §3.2 de este documento |
| [`remaining.md`](../../remaining.md) | Estado del repositorio anterior a la implementación | Reescribirlo contra el estado real, o borrarlo. Un documento de estado que miente es peor que ninguno |

### A.3 Comprobar

```bash
cd backend && uv run pytest tests/correspondencia -q -s
```

Los cuatro informes tienen que salir en cero, y los dos cubos del inventario vacíos.

---

## 3. Paso B — la primera novela real

**Esto es lo que de verdad falta.** No es código: el sistema está entero y probado con dobles. Lo que no ha ocurrido nunca es una ejecución contra el modelo.

### 3.1 Requisitos de la máquina

- **Python ≥ 3.12** y [`uv`](https://docs.astral.sh/uv/) instalados.
- **El CLI `claude` en el `PATH`, con sesión iniciada.** Esto no es opcional y no se sustituye con una clave: la única puerta al modelo es el Claude Agent SDK, que **lanza Claude Code como subproceso y hereda la sesión ya autenticada**. En este repositorio no hay ninguna credencial de Anthropic y no debe haberla — así lo declara [`.env.example`](../../.env.example) y lo comprueba `gitleaks` en G0 y G1.
- Conexión a internet: el investigador es el único rol con `WebSearch` y `WebFetch`.

Comprueba la sesión antes de gastar nada:

```bash
claude --version
```

### 3.2 Instalar y arrancar

```bash
cd backend
uv sync --extra agentes --extra embeddings --extra render
uv run playwright install chromium     # solo si vas a generar el PDF
```

Los tres extras existen por separado a propósito: `agentes` trae el SDK, `embeddings` arrastra `onnxruntime` (pesa), y `render` trae Playwright. La suite de G1 no necesita ninguno.

**La primera ejecución, en modo batch** —sin gates, sin detenerse a preguntar—, que es lo que quieres para ver si el recorrido completo funciona:

```bash
cd backend
uv run storymaker nueva ../ejemplos/brief-ejemplo.yaml --batch
```

Y para verla avanzar o retomarla:

```bash
uv run storymaker estado ramon-iriarte-sologaray
uv run storymaker continuar ramon-iriarte-sologaray
```

Los siete comandos que existen, tal como los declara [`cli/comandos.py`](../../backend/src/storymaker/cli/comandos.py):

| Comando | Qué hace |
|---|---|
| `nueva <brief> [--nombre N] [--batch]` | Crea la novela en `proyectos/` y arranca la invocación |
| `continuar <nombre>` | Reanuda desde el último checkpoint, **tras un fallo o tras un gate, por el mismo camino** |
| `estado <nombre>` | Fase, gate abierto, capítulos aprobados y consumo |
| `ramificar <nombre> <destino>` | Copia el fichero y escribe la fila de `procedencia` |
| `cambiar <nombre> <peticion>` | Entra en la Fase 6. **No cambia nada hasta el gate** |
| `desbloquear <nombre>` | Rompe un cerrojo huérfano de un proceso muerto |
| `evaluar [--briefs D]` | Corre los cinco briefs en modo batch |

### 3.3 Qué mirar cuando falle

Fallará: es la primera vez. Para ver la traza completa en lugar del mensaje reducido:

```bash
STORYMAKER_TRAZA_FALLOS=1 uv run storymaker nueva ../ejemplos/brief-ejemplo.yaml --batch
```

Dos cosas que conviene saber de antemano:

- **Una novela es un fichero.** Todo lo escrito está en `proyectos/<nombre>.db`, incluidos los checkpoints de LangGraph. Si algo se tuerce, ese fichero es el estado entero y `continuar` retoma desde el último checkpoint: no hay nada a medias que limpiar.
- **El cerrojo.** Si una invocación muere de golpe deja `proyectos/<nombre>.lock`. `desbloquear` lo rompe. Antes de romperlo, comprueba que no hay ningún proceso vivo.

Y el criterio de producto de `AGENTS.md` aplica aquí más que en ningún sitio: **ante una puerta que bloquea, ablandarla**. Si un validador para la ejecución por algo cosmético, bájale la severidad y sigue; el hallazgo se le cuenta al Autor, no se convierte en una parada.

---

## 4. Paso C — lo que solo se cierra con esa ejecución

Cuatro ítems del plan tienen el código escrito y **les falta haber corrido**. Ninguno se puede cerrar sin el paso B.

| Ítem | Qué falta | Con qué |
|---|---|---|
| **P-120** | Los cinco briefs de evaluación: cero incidencias críticas, 5/5 completan, ≥ 70 % de capítulos al primer intento | `uv run storymaker evaluar --briefs ../evals/briefs` o `python evals/correr.py` |
| **P-121** | Varianza del juez: N ejecuciones sobre la misma novela, desviación por criterio | `python evals/varianza_juez.py` |
| **P-122** | La primera revisión humana con rúbrica | El protocolo está en [`docs/revision-humana.md`](../../docs/revision-humana.md); el acta se añade a su §5 |
| **P-123** | Aserciones de G6 contra la traza real de Langfuse | `tests/traza/test_g6.py`, con `STORYMAKER_LANGFUSE_*` rellenos |
| **P-124** | `ejemplos/novela-ejemplo.pdf` commiteado con su manifiesto | Sale de la primera novela publicada |

**No corren en CI y no deben.** La nocturna [`nocturna.yml`](../../.github/workflows/nocturna.yml) tiene `mutmut` y CrossHair, que sí pueden correr en un *runner*; los cinco briefs no, porque un *runner* de GitHub no tiene sesión de Claude Code. Se lanzan a mano desde una máquina autenticada.

---

## 5. Hallazgos abiertos — decisiones del Autor

Ninguno se ha resuelto por cuenta propia, que es lo que manda `AGENTS.md` cuando algo toca una decisión fijada.

### 5.1 La normalización recorta de más (resuelto, pero conviene saberlo)

Al declarar los contratos para CrossHair salió que `normalizar` **no era idempotente**, y la consecuencia no era teórica: «autobús» normalizaba a `autobu` y «autobuses» a `autobus`, de modo que **el guardrail de palabras prohibidas cazaba el singular y dejaba pasar el plural** en todo sustantivo terminado en -s (país, análisis, mes, crisis).

Se arregló haciendo que `_singular` recorte hasta punto fijo. El precio es recortar de más y juntar alguna palabra que no debería juntarse, y se paga a sabiendas: en una lista de términos vetados, un falso positivo es una incidencia que el Autor ve en el informe y un falso negativo es una palabra prohibida impresa en el regalo. **Si el Autor prefiere el otro lado del trade-off, hay que decirlo en `verification.md` §3.3 y revertirlo.**

CrossHair encontró además que `anio_de` reventaba con dígitos Unicode que `isdigit()` acepta e `int()` rechaza —la función dejaba de ser total y el error salía dentro de un validador, a mitad de capítulo—. Arreglado, y el contraejemplo está como caso de prueba en `tests/unit/test_core_domain.py`.

### 5.2 Las aristas de aborto, sin resolver

**El modelo TLA+ declara la arista a `Fail` solo desde el gate de Intake**, mientras que §10 de la arquitectura ofrece «abortar» en los cinco gates. `tras_gate`, en [`commons/graph/aristas.py`](../../backend/src/storymaker/commons/graph/aristas.py), revienta a propósito en los otros tres en lugar de inventarse una transición que TLC nunca exploró, y hay una prueba que fija la limitación.

Dos resoluciones posibles, y la elección es del Autor:

1. **Añadir las tres aristas** a la definición `Aristas` de `formal/tla/harness.tla` y **volver a correr TLC**. Es lo que exige la correspondencia nodo↔acción.
2. **Estrechar §10** de la arquitectura para que «abortar» se ofrezca solo en el gate de Intake.

Lo que no vale es dejarlo: la discrepancia es entre la arquitectura y el modelo formal, y los dos se declaran fuente de verdad de cosas distintas.

