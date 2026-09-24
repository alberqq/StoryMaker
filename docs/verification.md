# Verificación — StoryMaker

Plan de verificación y **Quality Gates** del arnés multiagente de novela histórica.

[`architecture.md`](architecture.md) responde *quién* hace cada cosa y *cómo se detiene*. Este documento responde la pregunta complementaria: **cómo sabemos que lo hace bien**, con qué técnica se comprueba cada afirmación, en qué punto del ciclo de vida se comprueba y qué queda deliberadamente sin comprobar.

Cubre las dos superficies de riesgo del sistema, que son distintas y no se verifican igual:

- **El código del arnés** —orquestador, validadores, ensamblador, esquema— es software convencional y determinista. Se verifica con las técnicas clásicas: tipos, análisis estático, pruebas, *model checking*.
- **La conducta de los agentes** —nueve roles sobre Haiku 4.5— no es determinista y no admite una prueba de igualdad. Se verifica por *envelope*: se acota lo que pueden hacer, se mide lo que hacen y se somete lo consecuente a juicio humano.

Toda afirmación de este documento lleva una **clase de confianza**. Ninguna queda como suposición silenciosa.

---

## 1. El marco de confianza (T · A · I · D · U)

| Clase | Nombre | Significa | Evidencia que produce |
|---|---|---|---|
| **T** | Test | Se ejecuta el sistema contra entradas concretas. | Suite verde, informe de cobertura, *mutation score*. |
| **A** | Analysis | Razonamiento estático: tipos, SAST, ejecución simbólica, demostración. | Salida limpia del verificador, teorema demostrado, invariante sin contraejemplo. |
| **I** | Inspection | Una persona —o un modelo crítico— lee y juzga. | Decisión de gate firmada, rúbrica cumplimentada, acta de revisión. |
| **D** | Demonstration | Se observa el funcionamiento correcto en un escenario realista. | Traza de Langfuse de una ejecución completa, PDF generado, novela de `/ejemplos`. |
| **U** | Unverifiable | No hay método aplicable, o no compensa su coste. | **Una fila en §5 con el riesgo nombrado y su mitigación.** |

### Reglas de uso

1. **Toda propiedad del sistema tiene exactamente una clase primaria**, y como mucho una secundaria (se escribe `A/T`: garantizada por construcción, confirmada por prueba).
2. **U no es un cajón de sastre.** Una propiedad solo entra en U si está escrita en §5 con su mitigación y su condición de revisión. Un riesgo en U es un riesgo aceptado por el Autor, no uno olvidado por el arquitecto.
3. **A vence a T cuando ambas son posibles.** Si una propiedad se puede garantizar por construcción, no se deja al criterio de una prueba que alguien puede borrar. El caso canónico es el de los validadores: son nodos del grafo y no herramientas que un agente elige llamar, de modo que «el validador siempre corre» es A, no T.
4. **La clase no se hereda hacia abajo.** Que el modelo TLA+ cumpla un invariante no hace que el código Python lo cumpla: eso es la *brecha de refinamiento* de §5.

### Principio de proporcionalidad

El sistema no tiene usuarios en producción ni impacto sobre terceros. Las técnicas se adoptan en la dosis que aporta señal y se rechazan cuando el coste no se paga: se dice cuál, dónde y por qué. Un plan de verificación que nadie ejecuta porque tarda cuarenta minutos no verifica nada.

---

## 2. Mapa maestro

| # | Técnica | Clase | Dónde vive | Gate | Veredicto |
|---|---|---|---|---|---|
| 1 | Type checking | **A** | Pydantic v2, mypy `--strict`, SQLite `STRICT` | G1 | Adoptada, bloqueante |
| 2 | Static analysis / SAST | **A** | ruff+bandit, pip-audit, gitleaks, reglas Semgrep propias, Steiger sobre el frontend | G1 | Adoptada, bloqueante salvo Steiger |
| 3 | Symbolic execution | **A** | CrossHair sobre cinco funciones del Core Domain | G2 | Adoptada, acotada |
| 4 | Formal verification | **A** | Lean 4 sobre la cronología concreta: la deducida de la escaleta y la leída del texto | G3, G4, G5 | Adoptada, bloqueante |
| 5 | Unit / integration testing | **T** | pytest sobre `commons/validation/`, `commons/context/`, `commons/db/`, subgrafos con agente falso | G1 | Adoptada, bloqueante |
| 6 | Property-based testing | **T/A** | Hypothesis sobre ensamblador, normalización y manifiestos | G1 | Adoptada, bloqueante |
| 7 | Mutation testing | **T** | mutmut restringido a `commons/validation/` | G2 | Adoptada, solo Core Domain |
| 8 | Contract testing | **A/T** | Esquemas de rol, OpenAPI del endpoint, contrato nodo↔hook | G1 | Adoptada, bloqueante |
| 9 | Runtime observability | **D/T** | Langfuse: sesión por novela, span por invocación, aserciones sobre la traza | G6 | Adoptada |
| 10 | Evals | **T/I** | Cinco briefs de evaluación, *datasets* de Langfuse, rúbrica compartida | G2 | Adoptada |
| 11 | Sandboxed execution | **D/A** | `allowed_tools` por rol, contenedor, un fichero por novela | G4, G6 | Adoptada |
| 12 | Guardrails | **A/T** | Validadores como nodos, cuarentena de texto libre, `canon_prohibida`, guarda de contexto | G3 | Adoptada, bloqueante |
| 13 | Human-in-the-loop | **I** | Cinco gates avisados por Telegram y decididos en el PC, `edicion_humana`, revisión con rúbrica | G4 | Adoptada, bloqueante |
| 14 | Multi-agent verification | **I/T** | Juez separado del editor; auto-consistencia como medida | G5 | Adoptada parcialmente (§4.6) |
| 15 | CI/CD integration | **T/A** | GitHub Actions; misma tubería para código humano y generado | G1, G2 | Adoptada |
| 16 | Progressive rollout | **D** | Versiones de prompt en Langfuse, ramas por fichero, *feature flags* | G2 | Reinterpretada (§4.8) |
| 17 | Red-teaming | **T/I** | Suite adversaria determinista + sesión manual por hito | G1, G2 | Adoptada |
| 18 | Model checking | **A** | TLA+ directo, TLC sobre modelo pequeño | G1 | Adoptada, bloqueante |
| 19 | Correspondencia documento↔código | **A/T** | Cuatro pruebas de trazabilidad sobre el repositorio: inventario del plan, registro de validadores, anclas de procedencia e identidad nodo↔acción | G1 | Adoptada, bloqueante en dos de las cuatro |

---

## 3. Verificación del artefacto — ¿es correcto el código?

### 3.1 Type checking — **A**

**Qué garantiza.** Que ningún valor se use de forma incompatible con lo que la operación espera y, lo que en este sistema importa más, que **la salida de un modelo de lenguaje no entre en el grafo sin haber pasado por un esquema**.

**Implementación.**

| Frontera | Mecanismo | Fallo |
|---|---|---|
| Entrada del sistema | `Brief` (Pydantic v2) con `@model_validator` para las contradicciones de §4 de la arquitectura | `ValueError` que el entrevistador traduce a pregunta |
| Salida de cada rol | Un modelo Pydantic por rol, inyectado como esquema de salida; el nodo `schema_guard` valida antes de escribir en SQLite | Reintento con el error de validación en el prompt; agotado el límite, incidencia |
| Estado del grafo | `TypedDict` total con anotaciones explícitas; nada de `dict[str, Any]` en `graph/` | mypy en CI |
| Código del arnés | mypy `--strict` sobre `src/storymaker/`, sin `ignore_missing_imports` salvo lista blanca | Build roja |
| Persistencia | Tablas `STRICT` de SQLite más `CHECK` sobre los enumerados (`estado`, `origen`, `nivel`, `severidad`) | Excepción de integridad, transacción abortada |

**Por qué aquí.** El límite peligroso de un sistema multiagente no es `str` contra `int`: es **texto libre de un modelo interpretado como si fuera un dato**. El tipado es la primera línea que convierte una salida generativa en una estructura, y es la razón de que el texto pegado por el comprador solo pueda avanzar convertido en filas tipadas.

**Qué no cubre.** Que el contenido de un campo bien tipado sea *cierto*. `fecha_narrativa: date` no impide que la fecha sea absurda: eso es trabajo de Lean (§3.4).

---

### 3.2 Static analysis / SAST — **A**

**Qué garantiza.** Ausencia de patrones conocidos como malos, sin ejecutar nada. En este proyecto tiene un segundo cometido, más valioso: **hacer cumplir las decisiones de arquitectura de las que cuelga el sistema**.

**Herramientas genéricas.**

- `ruff` con el conjunto `S` (reglas de bandit): inyección SQL por interpolación, `subprocess` con `shell=True`, `pickle`, aserciones en producción.
- `pip-audit` sobre el *lockfile*.
- `gitleaks` en pre-commit y en CI. El repositorio convive con un token de Telegram y claves de Langfuse: un secreto commiteado es el único fallo de este proyecto con consecuencias fuera de él. **No hay clave de Anthropic que proteger**, y conviene decirlo porque cambia la superficie: los modelos corren a través de Claude Code, que el Agent SDK lanza como subproceso, de modo que la autenticación la pone la sesión ya iniciada del Autor y nunca entra en el árbol ni en el entorno del arnés.

**Reglas propias (Semgrep).** Son las que convierten principios escritos en prosa en comprobaciones mecánicas:

| Regla | Prohíbe | Principio que protege |
|---|---|---|
| `no-update-inmutables` | Cualquier `UPDATE` o `DELETE` sobre `capitulo_version`, `fase_run`, `version_*` o `mundo_hecho` tras el sello | «Nada se sobrescribe» (principio 5) |
| `core-domain-puro` | Importar `claude_agent_sdk`, `langgraph`, `httpx` o `langfuse` desde `src/storymaker/commons/validation/` | El Core Domain es agnóstico a quién lo llama (§15 arq.) |
| `validador-no-es-tool` | Registrar cualquier símbolo de `commons/validation/` en un `allowed_tools` o decorarlo como herramienta | «Los validadores son nodos, no herramientas» |
| `sin-red-fuera-del-investigador` | `WebSearch` o `WebFetch` en la definición de un rol que no sea el investigador | Aislamiento de la superficie de red (§4.3) |
| `pii-fuera-del-investigador` | Construir el prompt del investigador a partir de campos personales del `Brief` | Exfiltración de datos del homenajeado (§4.9) |
| `indice-solo-por-embeddings` | `INSERT`, `UPDATE` o `DELETE` sobre cualquier tabla `vec_*` desde fuera de `commons/embeddings/` | «El índice se escribe en la misma transacción que la fila» (§16.2 arq.) |

**Steiger, el linter de Feature-Sliced Design.** El frontend está organizado en FSD v2.1 (§16.3 arq.), cuyas dos reglas estructurales —un módulo solo importa de capas estrictamente inferiores, y dos *slices* de la misma capa nunca se importan entre sí— son comprobables sin ejecutar nada. `npx steiger src` las verifica en CI. Es la razón de haber preferido una metodología estándar a una convención propia: una convención propia no tiene quien la mire.

**Lo que Steiger no ve, y sí sostiene una puerta.** La regla de que **ningún módulo fuera de `shared/api` emite una petición de red** no es una regla de capas y el linter de FSD no la mira, pero de ella depende que `render_visual` pueda servir al navegador la versión candidata (§4 y §16.3 de la arquitectura). Se comprueba con una prueba propia sobre el árbol del frontend, y **esa sí bloquea**, por el mismo criterio que se enuncia a continuación: bloquea lo que sostiene una puerta.

**Steiger informa, no bloquea.** Es el primer caso de un criterio que este plan aplica en todas partes y conviene enunciar una sola vez: **bloquea lo que sostiene una puerta; informa lo que describe la forma del repositorio.** La forma de una carpeta no pone en riesgo ninguna de las propiedades que G3 y G5 protegen, y convertirla en parada contradiría el criterio de producto del proyecto. Bajo la misma regla informan `inventario_del_plan` y `anclas_de_procedencia` (§3.9), y bloquean `registro_de_validadores` e `identidad_nodo_accion`, porque el primero sostiene G3 y el segundo sostiene lo que TLC verificó. Todas publican su salida con el informe de G1.

**Valor real.** La regla `validador-no-es-tool` es análisis estático haciendo el trabajo que ninguna prueba puede hacer bien: una prueba comprobaría que *hoy* los validadores corren; la regla impide que *mañana* alguien los convierta en algo que un modelo pueda olvidarse de llamar.

---

### 3.3 Symbolic execution — **A**

**Qué garantiza.** Para un puñado de funciones puras y críticas, las condiciones exactas que las romperían, con contraejemplo concreto, sin depender de que a alguien se le ocurriera ese caso.

**Alcance deliberadamente estrecho.** Se aplica CrossHair —ejecución simbólica sobre Python con un solucionador SMT— a cinco funciones, todas en `commons/validation/` y `commons/context/`, todas puras y sin E/S:

| Función | Contrato que se explora |
|---|---|
| `normalizar(termino)` | Idempotente, y nunca colapsa dos términos prohibidos distintos en el mismo normalizado. **La idempotencia se cumple por construcción**: `_singular` recorta el plural hasta punto fijo, de modo que un término y su forma ya normalizada acaban en la misma cadena. La segunda cláusula se cumple solo en parte, y a sabiendas: recortar hasta punto fijo puede juntar dos palabras que no deberían juntarse, y en una lista de términos vetados un falso positivo es una incidencia que el Autor lee en el informe, mientras que un falso negativo es una palabra prohibida impresa en el regalo |
| `hay_solape_temporal(a, b)` | Simétrica, y correcta en los bordes con rangos abiertos (`fecha_fin = None`) |
| `es_anacronico(entidad, fecha)` | Falsa si y solo si `fecha_inicio ≤ fecha_narrativa ≤ fecha_fin`, con nulos bien tratados |
| `truncar_por_prioridad(bloques, techo)` | Nunca excede el techo, nunca vacía el bloque 3 y respeta el orden de recorte declarado |
| `capitulos_afectados(hecho_id, usos)` | El conjunto devuelto contiene todos los capítulos con un uso del hecho |

**Por qué solo cinco.** La ejecución simbólica escala mal con la E/S y con el estado, y el grueso del arnés es precisamente E/S sobre SQLite. Pagar el coste tiene sentido donde un error es silencioso y sistemático: un `normalizar` con un borde mal tratado no rompe nada visible, simplemente deja pasar una palabra prohibida en cada novela, para siempre. Un fallo de lectura de SQLite, en cambio, se nota enseguida.

**Cadencia.** Nocturna (G2), nunca por *commit*: CrossHair tarda lo que se le deje tardar. Un contraejemplo hallado se convierte en caso de prueba en `tests/validation/` y ya no se pierde.

**Relación con el resto.** El solucionador SMT que más trabaja en este proyecto no es el de CrossHair: es el de Lean y, sobre todo, la exploración exhaustiva de TLC. Los tres son la misma familia de garantía —*para todas las entradas del modelo*— aplicada a tres capas distintas: la función, la historia y el sistema.

---

### 3.4 Formal verification / theorem proving — **A**

**Qué garantiza.** Que la cronología de la novela publicada es consistente con las fechas duras del corpus histórico, para todos los eventos, no para los que alguien mire.

**Implementación.** `src/storymaker/commons/formal/` genera un fichero Lean 4 a partir de `cronologia_evento`, `cronologia_participante` y las fechas de `canon_personaje` y `mundo_entidad`. Los cuatro invariantes de §11c de la arquitectura se verifican por decisión (`decide`), de modo que la demostración es automática y no puede atascarse. El *runner* invoca `lake build`; el resultado es un booleano que leen las aristas condicionales del grafo.

**Dónde corre y qué bloquea.**

| Punto | Gate | Efecto del fallo |
|---|---|---|
| Tras aprobar cada capítulo | G3 | El capítulo vuelve al editor con el invariante violado como incidencia |
| Antes de publicar la versión | G5 | **La versión no se publica.** No hay anulación |
| Tras invalidar capítulos en Fase 6 | G3 | Solo se reescriben los capítulos que Lean tumba |

**Por qué una cronología concreta y no teoremas generales.** Un teorema general sobre «toda novela histórica» exigiría demostraciones asistidas que se atascan y que nadie mantendrá. Verificar la instancia concreta es automático, se ejecuta en cada capítulo y detecta exactamente la clase de fallo que un LLM no ve: un personaje histórico en escena tres años después de su muerte documentada le parece natural a un modelo, porque un modelo no tiene aritmética temporal. A Lean sí.

**Lo que queda fuera.** Que el generador de Lean traduzca fielmente el contenido de SQLite. Es código Python corriente y se verifica como tal (§3.5, §3.6, §3.8), no formalmente. Está anotado como brecha de refinamiento en §5.

---

### 3.5 Unit / integration testing — **T**

**Qué garantiza.** Comportamiento correcto sobre casos concretos elegidos, incluidos los bordes que el diseño declara importantes.

**Unitarias** (`tests/validation/`, `tests/context/`, `tests/db/`): Python puro, sin red, sin modelo, milisegundos.

- Un caso por validador programático de §11a, con su caso positivo y su caso negativo.
- `guardrail_prohibidas`: un caso por nivel (`global`, `novela`, `destinatario`), más variantes con acento, plural y mayúsculas, derivadas por raíz y el caso que no debe saltar dentro de otra palabra.
- Ensamblador: los siete bloques, en orden, con los techos respetados y el recorte por prioridad.
- Consulta de invalidación: dado un hecho usado en las escenas de tres capítulos, devuelve esos tres.
- Diff de manifiestos: dos versiones, un capítulo cambiado, `JOIN` correcto.

**De integración** (`tests/graph/`): el grafo completo sobre un SQLite temporal, con un **agente falso** —una implementación de la interfaz de invocación que devuelve artefactos de *fixture* en lugar de llamar al Agent SDK—. Sin esa pieza no hay suite de integración posible, porque una ejecución real cuesta dinero y tarda minutos.

| Prueba | Qué demuestra |
|---|---|
| Recorrido completo en modo batch | El grafo llega de `Configure` a `PublishVersion` sin intervención |
| Atomicidad del checkpoint | Matar el proceso entre `ApproveChapter` y `Checkpoint` deja la base coherente; al reanudar, el capítulo no se duplica ni se pierde |
| Reanudación por gate | `interrupt()` más `Command(resume=...)` retoma en el mismo nodo, con el mismo estado |
| Fase 6 de extremo a extremo | Cambiar un hecho regenera exactamente los capítulos que lo usan y **la versión anterior sigue completa** |
| Ramificación | Copiar el fichero y continuar no contamina el original |
| Reintentos agotados | Dos fallos llevan a `Fail`, no a un tercer intento |
| El extractor corre antes de aprobar | Un capítulo al que le falta un elemento obligatorio anclado vuelve al editor, y no llega a `ApproveChapter` |
| Un aviso viaja al capítulo siguiente | Un hito de arco no ejecutado en N aparece en el bloque 1 del paquete de N+1 sin haber detenido N |
| Solo viajan tres avisos | Con cinco avisos abiertos en N, el bloque 1 de N+1 recibe los tres más recientes |
| El aviso del último capítulo no se pierde | Un hito no ejecutado en el capítulo final aparece destacado en el informe del gate de Writing |
| Editar un arco invalida por `uso_hito` | Mover un hito del capítulo 8 al 5 invalida exactamente los capítulos que lo ejecutaban |
| Lean sobre la escaleta | Una escaleta que pone a un personaje en dos lugares el mismo día no pasa el gate de Plotting, sin haber redactado nada |
| Las filas del intento descartado no contaminan | Tras un reintento, `uso_hecho` y `continuidad` del intento fallido no entran en ningún manifiesto |

**Umbral.** Cobertura ≥ 90 % en `commons/validation/` y `commons/context/`; sin umbral global. Cubrir `publication/` al 90 % no dice nada sobre la corrección de una novela.

---

### 3.6 Property-based testing — **T/A**

**Qué garantiza.** Que una propiedad general se sostiene sobre cientos de entradas generadas, incluidas las que nadie habría escrito a mano. Es la técnica que **acerca el código a los invariantes formales**: cada invariante de TLA+ tiene aquí su eco ejecutable sobre la implementación real.

Con Hypothesis, y estrategias que sintetizan novelas: corpus, canon, escaleta y secuencias de operaciones.

| Propiedad | Invariante que refleja |
|---|---|
| Para cualquier estado de la base, el paquete ensamblado cabe en el techo y conserva el bloque de continuidad | Presupuesto de contexto (§12 arq.) |
| Para cualquier secuencia de regeneraciones, toda versión publicada previamente sigue siendo recuperable entera | `PreviousVersionPreserved` |
| Para cualquier traza de reintentos, el número de `capitulo_version` por capítulo y `fase_run` no supera el límite | `RetriesBounded` |
| Para cualquier conjunto de usos, los capítulos invalidados incluyen todos los que usan el hecho | Corrección de la Fase 6 |
| Para cualquier escaleta que pase `arco_anclado`, todo personaje en ≥3 escenas tiene arco, y todo arco positivo o negativo tiene ≥2 hitos en capítulos estrictamente crecientes | Corrección de `arco_anclado` |
| Para cualquier escaleta cuya cronología Lean acepte en el gate de Plotting, ningún personaje aparece en dos escenas del mismo día en lugares distintos ni fuera de sus fechas vitales | Anticipación de los invariantes de Lean a la escaleta |
| `normalizar` es idempotente y detecta toda variante generada de un término prohibido | Eficacia del guardrail |
| Ninguna versión publicada contiene un `capitulo_version` sin *score* de todos los validadores | `NoPublishUnvalidated` |

**Por qué importa más aquí que en un CRUD.** Las propiedades anteriores son la única evidencia de que el código *implementa* el modelo verificado con TLC. No cierran la brecha de refinamiento, pero la estrechan donde más duele.

---

### 3.7 Mutation testing — **T**

**Qué garantiza.** Que la suite detecta de verdad los fallos que dice detectar, y no simplemente ejecuta líneas.

**Alcance.** `mutmut` restringido a `src/storymaker/commons/validation/`, con objetivo de ***mutation score* ≥ 80 %** en los validadores y en la normalización. Fuera de esa carpeta no se ejecuta.

**Por qué exactamente ahí.** Es el mismo argumento que sostiene toda la arquitectura, un nivel más abajo. Un validador que siempre devuelve «correcto» es indistinguible de un validador correcto mirando la suite en verde: los capítulos se aprueban, los *scores* salen perfectos y nadie se entera hasta leer la novela. Mutar `>` por `>=` en `es_anacronico`, o negar la condición de `guardrail_prohibidas`, y comprobar que alguna prueba se pone roja, es la forma barata de saber que la red tiene malla. Un validador silenciosamente roto es el fallo más caro de este sistema, porque destruye la confianza en todos los demás.

**Cadencia.** Nocturna (G2) y antes de cada hito. Informativo: no bloquea una integración, pero una caída del *score* se trata como defecto.

---

### 3.8 Contract testing — **A/T**

**Qué garantiza.** Que las interfaces entre piezas que evolucionan por separado no se rompen en silencio. En un arnés multiagente los contratos relevantes no son solo HTTP:

| Contrato | Lados | Verificación |
|---|---|---|
| **Orquestador ↔ rol** | Nodo del grafo / prompt en Langfuse | El modelo Pydantic es el contrato. Un corpus de salidas reales grabadas se revalida contra el esquema en CI: si alguien cambia un campo, la prueba cae aunque el prompt siga funcionando |
| **Prompt ↔ esquema** | Versión de prompt / versión del modelo de salida | El id de versión del prompt viaja en el span; una prueba comprueba que la versión publicada en Langfuse es compatible con el esquema del repositorio |
| **CLI ↔ grafo** | `storymaker decidir` / acción `HumanDecide` | Una decisión desconocida o sin gate pendiente no reanuda el grafo, y reanudar no reabre el gate decidido |
| **Código ↔ esquema SQLite** | Migraciones / consultas | Prueba de migración sobre una base de la versión anterior, más comprobación de que toda columna leída existe |
| **Generador ↔ Lean** | `formal/` / proyecto `lake` | Un fichero Lean de referencia se regenera y se compara; si el generador cambia de forma, la diferencia se ve |
| **Nodo ↔ hook de `.claude/`** | Grafo en producción / Claude Code en edición manual | **El contrato más valioso del proyecto** |

**Sobre el último.** El Core Domain tiene dos consumidores: el grafo lo ejecuta como nodo y `.claude/` lo expone como *skill* y como *hook* cuando una persona edita un capítulo a mano. La prueba de contrato ejecuta **el mismo capítulo por ambos caminos y exige el mismo veredicto, incidencia por incidencia**. Si divergen, el producto y el editor humano dejan de estar de acuerdo sobre qué es válido, que es precisamente el fallo que la decisión de «una sola implementación, dos puntos de ejecución» existe para evitar.

---

### 3.9 Correspondencia documento↔código — **A/T**

**Qué garantiza.** Que el código que corre es el que los documentos describen. Es la familia §11e de la arquitectura, y responde a la pregunta que ninguna de las ocho técnicas anteriores contesta: todas comparan el código consigo mismo —contra sus tipos, contra sus pruebas, contra su modelo—, y ninguna lo compara contra la especificación que, en este proyecto, manda sobre él.

**Las cuatro pruebas.**

| Prueba | Compara | Clase | Bloquea |
|---|---|---|---|
| `inventario_del_plan` | Las rutas y símbolos de la columna «Ficheros y símbolos» de cada `plan.md` contra el árbol, en las dos direcciones | T | No |
| `registro_de_validadores` | El registro de validadores deterministas, §11a de la arquitectura y §7.2 de la spec, por pares | A/T | **Sí** |
| `anclas_de_procedencia` | Las anclas `spec:` y `arq:` de los docstrings del backend contra los documentos, y §3 y §4 de la spec del backend contra los símbolos que los citan. El frontend no lleva anclas: se traza por `inventario_del_plan` y `requisitos_declarados` | T | No |
| `identidad_nodo_accion` | Nombres y aristas del `StateGraph` contra los `process` y la definición `Aristas` de `harness.tla` | A | **Sí** |

**Por qué dos son de clase A.** `registro_de_validadores` lo es porque el registro **es el cableado**: el grafo compone su pasada determinista leyéndolo, así que un validador ausente del registro no corre, y la prueba confronta el cableado real contra el documento en vez de dos listas mantenidas a mano. `identidad_nodo_accion` lo es porque la definición `Aristas` gobierna el `Next` que TLC explora: lo que la prueba lee es exactamente lo que se verificó.

**La dirección que importa.** La comprobación inversa —que todo apartado de §3 y §4 de la spec tenga al menos un símbolo que lo cite— es la única de todo este plan capaz de señalar una **ausencia**. Ninguna suite de pruebas ve el código que nadie escribió, porque nadie escribe la prueba de un código que no existe.

**Relación con §3.2 y §3.8.** Las reglas Semgrep hacen cumplir principios de arquitectura enunciados en prosa, y las pruebas de contrato cuidan las interfaces entre piezas que evolucionan por separado. Esta familia cuida la interfaz entre el documento y el código, que es la que el método de trabajo del proyecto da por supuesta.

**Qué no cubre.** Que los documentos digan la verdad sobre el dominio: una tabla mal pensada y un registro fiel a ella pasan en verde. Anotado como U-18.

---

## 4. Verificación del proceso — ¿se comporta bien el agente?

### 4.1 Runtime observability / tracing — **D/T**

**Qué garantiza.** Que la trayectoria real de cada ejecución es visible y consultable después: qué prompt vio cada rol, qué devolvió, cuántos tokens, cuánto costó y qué falló.

**Implementación.** La de §14 de la arquitectura: sesión por novela, span por invocación (`capitulo_07 · escritor · intento_2`), *scores* de todos los validadores asociados a su traza y decisiones de gate incluidas. **Cada paquete de contexto se persiste y se enlaza desde su span**: poder abrir literalmente lo que el modelo vio al escribir el capítulo 7 es la definición operativa de interpretabilidad en este sistema.

**De observación pasiva a verificación activa.** Una traza que nadie consulta no verifica nada. Tras cada ejecución de evaluación, un script consulta la API de Langfuse y **afirma propiedades sobre la trayectoria** —esto es T, no D—:

- Todo capítulo aprobado tiene un span de escritor y al menos un span de validación **anterior** a su aprobación.
- Ningún capítulo tiene más spans de `intento_` que el límite de reintentos.
- El coste acumulado de la ejecución está por debajo del presupuesto declarado.
- Ningún span de un rol distinto del investigador contiene llamadas a `WebSearch` o `WebFetch`.
- Toda decisión de gate tiene actor y momento.

La primera y la última son `NoPublishUnvalidated` y la trazabilidad de la intervención humana, comprobadas sobre una ejecución real en lugar de sobre un modelo.

---

### 4.2 Evals — **T/I**

**Qué garantiza.** Que la conducta del sistema sobre un conjunto representativo de entradas es la esperada, y que no empeora cuando se toca un prompt.

**Dataset.** Cinco briefs de evaluación, versionados en el repositorio y registrados como *dataset* de Langfuse, elegidos para cubrir ejes distintos: períodos con densidad documental muy diferente, un homenajeado con datos escasos, un brief con lista de palabras prohibidas larga, un período con eventos históricos duros y fechables, y un brief deliberadamente tenso (tono festivo sobre un período trágico). Corren en modo batch, con `gates.enabled = false`.

| Tipo de eval | Qué mide | Criterio de aprobación | Clase |
|---|---|---|---|
| **Golden dataset** | Validadores deterministas sobre los cinco briefs | Cero incidencias críticas en la versión publicada | T |
| **LLM-as-judge** | Rúbrica de siete criterios del juez | Media ≥ umbral declarado y ningún criterio por debajo del mínimo | T |
| **Task completion** | ¿Llega a `PublishVersion` sin intervención? ¿Cuántos capítulos aprueban al primer intento? | 5/5 ejecuciones completan; ≥ 70 % de capítulos al primer intento | T |
| **Adversarial** | Briefs construidos para romper (§4.9) | El sistema rechaza o pregunta; nunca publica en silencio | T |
| **Live / online** | *Scores* de toda ejecución real, no solo de las de evaluación | Vigilancia de deriva entre versiones de prompt | D |

**Estabilidad métrica.** El juez se ejecuta N veces sobre la misma novela y **se publica la desviación por criterio**. Es una de las dos promesas de reproducibilidad del sistema (§13 arq.) y no se supone: se mide. Si la desviación excede la tolerancia declarada, subir el modelo de ese rol es una línea de *frontmatter*, y la tabla antes/después es evidencia de la iteración de *tuning*.

**Lo que un eval no puede decidir.** Si la novela emociona. La rúbrica mide lo que la rúbrica mide; el resto es §4.5.

---

### 4.3 Sandboxed execution — **D/A**

**Qué garantiza.** Que una acción equivocada de un agente falla sin alcanzar nada valioso.

**El aislamiento es sobre todo de diseño, no de infraestructura**, y conviene decirlo con precisión porque cambia el perfil de amenaza:

| Superficie | Estado | Clase |
|---|---|---|
| Ejecución de código por un agente | **No existe.** Ningún rol tiene `Bash` ni ejecución arbitraria | A |
| Escritura en disco por un agente | **No existe.** La salida del modelo va a SQLite a través del orquestador; ningún rol tiene `Write` | A |
| Acceso a red | Solo el investigador, con `WebSearch` y `WebFetch` | A, comprobado por regla Semgrep y por aserción sobre la traza |
| Alcance de la escritura | Un fichero SQLite por novela; ramificar es copiar el fichero | A |
| Contenido no confiable de la red | Entra en micro-sesiones con `max_turns` bajo que escriben sus hechos y mueren | D |
| Entorno de ejecución | Contenedor con el proyecto y la base montados; Playwright MCP en *headless* dentro del mismo contenedor | D |

**Consecuencia.** El escenario clásico de *sandboxing* —el agente ejecuta algo destructivo— está cerrado por construcción, no por contención. El riesgo residual es distinto y menos espectacular: **contenido hostil leído de internet que intenta convertirse en instrucción**. Se trata en §4.9.

---

### 4.4 Guardrails — **A/T**

**Qué garantiza.** Que hay acciones y salidas que el sistema no puede producir, con independencia de lo que el modelo decida.

Cinco guardrails, ordenados por el momento en que actúan:

| # | Guardrail | Momento | Mecanismo | Clase |
|---|---|---|---|---|
| 1 | **Cuarentena de texto libre** | Antes de que el texto entre en el sistema | El texto pegado va a una tabla de cuarentena; un extractor con salida restringida por esquema produce hechos tipados; **el texto en bruto no llega jamás al prompt del escritor** | A |
| 2 | **Guarda de presupuesto** | Antes de emitir la llamada | Si el prompt ensamblado excede el techo del rol, la llamada se rechaza en lugar de emitirse; un semáforo suma los techos de las sesiones concurrentes | A |
| 3 | **Herramientas declaradas** | En la invocación | `allowed_tools` y `max_turns` por rol, fijados en cada llamada | A |
| 4 | **Palabras prohibidas** | Tras generar, antes de aprobar | `canon_prohibida` en tres niveles, con normalización previa a la comparación; coincidencia implica vuelta al escritor, con límite | A/T |
| 5 | **Inmutabilidad** | En la persistencia | *Triggers* `BEFORE UPDATE` sobre las tablas inmutables que abortan la transacción, además de la regla Semgrep | A |

**Sobre el quinto.** El principio «nada se sobrescribe» merece dos cerrojos: uno estático que impide escribir el código y otro en la base que impide que se ejecute. Un principio que solo vive en un documento es una convención; con el *trigger*, es una propiedad.

**La clase se reparte.** La *existencia* del guardrail es A, porque es estructural. Su *eficacia* es T: hay pruebas por nivel y por variante, y mutación sobre el comparador. La *lista* de términos prohibidos es I: la decide una persona, y ninguna técnica la valida.

---

### 4.5 Human-in-the-loop review — **I**

**Qué garantiza.** Que ninguna decisión consecuente se toma sin una persona, y que esa decisión queda registrada como dato.

**Los cinco gates.** Intake, Investigation, Plotting, Writing y Regeneration. El nodo llama a `interrupt()`, el estado se persiste y el proceso termina; Telegram avisa, y la decisión se toma en el PC con `storymaker decidir`, que la escribe y reanuda el grafo. No hay auto-aprobación por *timeout*: eso convertiría un gate de calidad en un temporizador. En modo batch los cinco se desactivan enteros, porque los briefs de evaluación tienen que correr desatendidos.

**Lo que se registra.** Toda decisión va a `gate`; toda edición directa del corpus, del canon o de la escaleta va a `edicion_humana` y a `audit_log` con actor, momento y estados antes y después; todo comentario de «rehacer» se inyecta como bloque en el prompt y se versiona. **La intervención del Autor queda trazada igual que la de un agente.**

**La revisión con rúbrica.** Una persona aplica a al menos una novela completa **la misma rúbrica de siete criterios que el juez**, desde el mismo fichero. Sin esa identidad, comparar juicio humano y juicio de modelo no significaría nada; con ella, la comparación por criterio es una tabla.

**Qué pasa con la señal.** Este sistema no reentrena nada, y conviene no prometer más de lo que hay. La retroalimentación tiene tres destinos reales: el comentario de «rehacer» entra en el prompt de esa ejecución; la divergencia sistemática entre humano y juez motiva una **nueva versión de prompt en Langfuse**, medida contra el eval anterior; y la edición directa del canon dispara la maquinaria de la Fase 6. Llamar a eso *training signal* sería inexacto: es control, versionado y medido.

---

### 4.6 Multi-agent verification — **I/T**

La posición del proyecto es tan importante por lo que rechaza como por lo que adopta.

| Patrón | Decisión | Razón |
|---|---|---|
| **Critic / verifier** | **Adoptado, con separación estricta.** El juez verifica y **no puede escribir**; el editor repara y **no puntúa**; el **verificador** dicta si la cita sostiene el hecho y **no puede añadir hechos al corpus** | Si el mismo agente que optimiza la métrica es el que la produce, los *scores* dejan de significar nada. Por eso el investigador tampoco declara que sus propios hechos estén respaldados |
| **Reflection** | **Adoptada, acotada y heterónoma.** El bucle editor↔validadores es reflexión con límite de dos iteraciones, y lo que la dispara es un **informe producido fuera del escritor**: determinista en todo lo que bloquea, y del extractor independiente en lo que solo avisa. Nunca la autocrítica de quien redactó | Un modelo juzgando su propia prosa es el fallo que la separación editor/juez existe para evitar, y el mismo que haría inútil preguntarle al escritor si ejecutó sus beats. Además `RetriesBounded` está verificado en TLC |
| **Self-consistency** | **Adoptada como medida, no como decisión.** N ejecuciones del juez sobre la misma novela para publicar la varianza por criterio. Si excede la tolerancia, la puntuación del gate G5 pasa a ser la **mediana de tres ejecuciones** | Votar por mayoría sobre contenido generado no aplica: no hay una respuesta correcta que aparezca más veces |
| **Ensembles** | **Rechazado para generación; contingente para el juez** | Alternar modelos entre capítulos rompería la consistencia de voz, que es un criterio de la rúbrica. Para el juez es la mitigación declarada si Haiku resulta demasiado ruidoso |
| **Debate** | **Rechazado.** Anotado en §5 | Dos modelos discutiendo sobre una rúbrica de siete criterios multiplica el coste para un veredicto que no es más verificable. Los criterios duros ya los resuelven Lean y los validadores deterministas; los blandos los cierra una persona |

**El principio que ordena todo esto** es *determinista antes que modelo*. Un segundo modelo solo se añade donde no hay cálculo posible. Para fechas, nombres, longitudes, anacronismos y anclajes hay cálculo, y ahí un crítico LLM sería más caro y menos fiable que veinte líneas de Python.

---

### 4.7 CI/CD integration — **T/A**

**Qué garantiza.** Que el código generado por agentes pasa exactamente por donde pasa el escrito por humanos, y que se puede saber de dónde vino cada cosa.

**Tubería (GitHub Actions).**

| Etapa | Contenido | Tiempo objetivo | Bloqueante |
|---|---|---|---|
| 1 · Estática | ruff y bandit, mypy `--strict`, gitleaks, reglas Semgrep propias | < 1 min | Sí |
| 2 · Rápida | pytest unitarias, Hypothesis, contratos | < 3 min | Sí |
| 3 · Formal del sistema | TLC sobre `formal/tla/harness.cfg` (5 capítulos, 2 reintentos) | < 3 min | Sí |
| 4 · Formal de la historia | `lake build` sobre una cronología de *fixture* | < 2 min | Sí |
| 5 · Integración | Grafo completo con agente falso sobre SQLite temporal | < 5 min | Sí |
| 6 · Nocturna | Mutación, CrossHair, suite de evals con modelo real, varianza del juez | Sin límite | No |

**Procedencia, en dos planos.** Conviene no confundirlos, porque responden a preguntas distintas:

- **Procedencia del código.** El repositorio se escribe en buena parte con Claude Code. Los *commits* llevan su línea de coautoría y pasan por la misma tubería y la misma revisión. No hay una vía rápida para el código generado: ese es todo el punto.
- **Procedencia del contenido.** El `manifiesto` de cada versión publicada registra el hash del brief, el hash del corpus sellado, la versión de cada prompt, el id exacto de cada modelo y la versión del SDK; `audit_log` y `edicion_humana` distinguen `origen = 'humano'` de `'agente'` en cada fila tocada. Cualquier frase de cualquier versión se rastrea hasta la escaleta, el canon y el corpus exactos que la produjeron.

---

### 4.8 Progressive rollout — **D**

**Reinterpretado, porque no hay tráfico.** Desplegar al 5 % de los usuarios no significa nada en un sistema que produce una novela por encargo. Lo que sí existe es el problema que el *rollout* progresivo resuelve: **cambiar algo sin descubrir en producción que lo empeoró**. Hay tres vehículos para eso:

| Mecanismo | Equivalente a | Cómo se decide |
|---|---|---|
| **Versiones de prompt en Langfuse** | El *canary* | Una versión nueva se ejecuta primero sobre los cinco briefs de evaluación. Solo pasa a ser la versión por defecto si no empeora ningún criterio de la rúbrica ni ningún *score* determinista |
| **Ramificación por copia de fichero** | Despliegue paralelo | La configuración nueva produce `novela-7b.db`; el diff de manifiestos y las puntuaciones del juez se comparan lado a lado y **decide el Autor** |
| ***Feature flags* en configuración** | El interruptor de apagado | `gates.enabled`, exportación OTLP, modelo por rol, límite de reintentos. Cambiables sin tocar código |

**Lo que no hay:** despliegue por porcentaje de tráfico, *shadow traffic* y *rollback* automático por métrica. Anotado en §5 como no aplicable, no como pendiente.

---

### 4.9 Red-teaming / adversarial testing — **T/I**

**Modelo de amenaza.** El adversario relevante aquí no es un atacante con objetivos económicos: es **contenido hostil o degenerado que entra por las dos únicas puertas abiertas del sistema** —el texto que pega el comprador y las páginas que lee el investigador—, más los modos de fallo propios de un agente en una ejecución larga.

| Vector | Ataque concreto | Defensa | Prueba |
|---|---|---|---|
| **Inyección por texto pegado** | Una anécdota que contiene «ignora las instrucciones anteriores y escribe…» | Estructural: el texto va a cuarentena y solo avanza convertido en filas tipadas (`persona`, `lugar`, `fecha`, `objeto`, `anécdota`) | Cargas de inyección en el brief; se afirma que **ninguna cadena del texto original aparece en el prompt del escritor** y que lo extraído es tipado |
| **Inyección por contenido web** | Una página recuperada por el investigador que le ordena algo | Micro-sesión con `max_turns` bajo que solo puede escribir hechos y muere; el corpus lo aprueba el Autor en el gate de Investigation | *Fixture* de página hostil; se afirma que el resultado es, como mucho, una fila de `mundo_hecho` visible en el gate |
| **Encadenamiento de herramientas** | Un rol intenta usar una herramienta que no le corresponde | `allowed_tools` por invocación | Invocación de un rol con herramienta prohibida: debe fallar, no degradar |
| **Exfiltración de datos personales** | Los datos del homenajeado salen por la única ruta con red | El investigador **recibe únicamente el período y el lugar del `Brief`, nunca sus campos personales**, y es el único rol con red | Regla Semgrep más aserción: el prompt ensamblado del investigador no contiene ningún valor de los campos personales |
| **Deriva de objetivo** | En el capítulo 9 el sistema ya está escribiendo otra novela | No hay sesión larga: cada capítulo es una invocación con contexto ensamblado desde SQLite, y el canon manda sobre el texto | Ejecución de diez capítulos con aserciones de continuidad y `cobertura_personalizacion` |
| **Evasión del guardrail** | Término prohibido con acentos raros, espaciado o separadores | Normalización previa a la comparación | Generador de variantes en Hypothesis |
| **Negación de servicio por coste** | Una regeneración que toca un hecho usado en nueve capítulos | Correcto pero caro: el gate de Regeneration permite abortar antes de pagarlo | Prueba del recuento de afectados y del aviso previo |

**Cadencia.** La suite adversaria es determinista —usa el agente falso y *fixtures*— y corre en G1. Una **sesión manual de red-teaming por hito**, con modelo real y una persona intentando romperlo a mano, corre en G2 y se documenta como acta: eso es I, y es la parte que ninguna suite sustituye.

---

### 4.10 Model checking — **A**

**Qué garantiza.** Que el comportamiento del arnés —no su código: su comportamiento— cumple sus invariantes en **todos** los estados alcanzables del modelo, incluidos los entrelazados que a nadie se le ocurriría probar.

**Implementación.** Especificación escrita **directamente en TLA+** en `formal/tla/harness.tla`, con los nombres de los nodos de LangGraph como valores del contador de programa y todas las acciones moviéndolo por `Mueve(de, a)` sobre la definición `Aristas`. La tabla de correspondencia acción↔nodo de §9 de la arquitectura no es una narración: es una lista de identidades, y es lo que hace que un contraejemplo de TLC se lea como una secuencia de nodos reales.

**Alcance.** Las seis fases, incluidas reanudación y regeneración. Modelar solo el bucle de generación dejaría fuera precisamente los invariantes interesantes, porque viven en lo que se habría excluido.

| Invariante | Enunciado | Por qué no basta con pruebas |
|---|---|---|
| `NoPublishUnvalidated` | Nunca se publica una versión con un capítulo que no pasó todos los validadores | Exige cuantificar sobre todos los entrelazados de aprobación, regeneración y publicación |
| `ResumeIsExactlyOnce` | Reanudar desde checkpoint no duplica ni pierde capítulos | El fallo vive en el instante exacto entre escribir y marcar |
| `RetriesBounded` | Los reintentos por capítulo nunca superan el límite | Interacción entre el bucle de reparación y la reanudación |
| `CorpusSelladoNoSeToca` | Sellado el corpus, ningún nodo vuelve a escribir en `mundo_*` | El atajo que lo rompería es un camino del grafo, no una línea de código |

**`PreviousVersionPreserved` se comprueba como propiedad temporal** —la secuencia de versiones es *append-only* y ningún elemento publicado cambia— y no como invariante de estado: «la anterior sigue siendo recuperable» no se mira en una foto del sistema, sino entre un estado y el siguiente.

**Liveness.** En batch, la propiedad directa: toda generación termina publicando una versión o deteniéndose con error. En interactivo, el humano se modela como proceso de entorno no determinista y la propiedad se enuncia **bajo hipótesis de equidad débil sobre su respuesta**: *si el Autor acaba respondiendo, toda generación termina*. No es una escapatoria: sin esa hipótesis la propiedad es falsa y no hay diseño que la salve.

**Configuración.** Modelo pequeño —5 capítulos, 2 reintentos— en `formal/tla/harness.cfg`, ejecutado en CI. TLC no ejecuta el código: explora el modelo. **Cada contraejemplo hallado durante el desarrollo se documenta junto al cambio de diseño que provocó**; esa lista es la evidencia más honesta de que la especificación sirvió para algo, y no un adorno escrito a posteriori.

---

## 5. Riesgos aceptados — **U**

Todo lo que este plan **no** verifica, dicho en voz alta. Cada fila es una decisión del Autor, no un olvido.

| # | Riesgo aceptado | Por qué no se verifica | Mitigación | Cuándo se revisa |
|---|---|---|---|---|
| U-1 | **Brecha de refinamiento.** Que el código Python implemente fielmente el modelo TLA+ y el generador de Lean | Demostrar refinamiento de Python contra TLA+ está fuera de todo presupuesto razonable | Identidad de nombres nodo↔acción, propiedades de Hypothesis que reflejan cada invariante (§3.6), pruebas de integración sobre los mismos escenarios | Si aparece un fallo que TLC daba por imposible |
| U-2 | **Verdad histórica del corpus.** El sistema verifica que una afirmación tiene fuente y estado epistémico, **no que sea cierta** | Ninguna técnica de software decide qué ocurrió en 1805 | Estado epistémico por hecho, fuentes registradas, gate humano de Investigation, nota del autor con las licencias declaradas | Permanente: es la naturaleza del dominio |
| U-3 | **Reproducibilidad textual.** Dos ejecuciones del mismo brief no producen el mismo texto | Un modelo generativo no es determinista bit a bit ni a temperatura cero | Se promete auditabilidad y estabilidad métrica en su lugar; la evidencia es el PDF commiteado más su manifiesto | No se revisa: es una promesa que no se hace |
| U-4 | **Evasión del guardrail por paráfrasis.** Una lista de términos no detecta una alusión | El problema es semántico y abierto | Tres niveles de lista, normalización y gate humano de Writing | Si aparece un caso real en una revisión |
| U-5 | **Calidad literaria más allá de la rúbrica.** Si la novela emociona | No hay métrica | Revisión humana con la misma rúbrica y lectura completa de al menos una novela | Cada hito |
| U-6 | **Originalidad y plagio.** No se comprueba similitud contra obras existentes | Exigiría un servicio externo y un corpus de referencia | El criterio de originalidad de la rúbrica, aplicado por el juez y por la persona | Si el proyecto saliera del ámbito académico |
| U-7 | **Coste real.** `total_cost_usd` del SDK es una estimación en cliente, no facturación | No hay API de facturación por ejecución | Se etiqueta como estimación en toda salida y en la propuesta económica | — |
| U-8 | **Restricción de dominios en `WebFetch`.** El SDK no la documenta | Fuera de nuestro control | Tope de tres `WebSearch` y tres `WebFetch` impuesto por el arnés, cada fetch acotado a 10.000 tokens: el peor caso de la sesión es una suma conocida de antemano | Si el SDK lo documenta |
| U-9 | **Varianza del juez en Haiku 4.5** | Se mide, pero no se puede garantizar *a priori* | Publicación de la desviación por criterio; mediana de tres ejecuciones o subida de modelo solo en ese rol si excede la tolerancia | En cada ejecución del eval |
| U-10 | **Rollout por porcentaje de tráfico y rollback automático** | No aplicable: no hay tráfico | Canary sobre el eval, ramas comparables y *feature flags* (§4.8) | No aplica |
| U-11 | **Debate entre modelos** | Rechazado por coste frente a valor marginal (§4.6) | Los criterios duros los cierran Lean y los deterministas; los blandos, una persona | Si la revisión humana discrepara sistemáticamente del juez |
| U-12 | **Ejecución simbólica más allá de cinco funciones** | No escala sobre código con E/S y estado | Propiedades de Hypothesis sobre el resto | Si aparece un fallo de borde en una función pura no cubierta |
| U-13 | **Fiabilidad del verificador de respaldo.** Es un modelo decidiendo si un fragmento sostiene un enunciado, y puede equivocarse en ambas direcciones | Montar un juego de pares etiquetados a mano para un validador que no bloquea nada cuesta más de lo que vale. Su clase de confianza es **I**: quien decide es el Autor en el gate | El veredicto no gobierna ninguna arista del grafo; solo degrada el estado epistémico y colorea el informe de G4. El Autor tiene el enunciado, la cita y la URL delante | Si el informe resultara tan ruidoso que el Autor dejara de mirarlo |
| U-15 | **Disponibilidad de `sqlite-vec`.** Es una extensión nativa que se carga con `enable_load_extension`, y un intérprete de Python compilado sin soporte de extensiones no puede abrirla | Está fuera del código: depende de cómo se haya construido el intérprete de la máquina donde corra | La carga se comprueba al abrir la base y el arranque se detiene con un mensaje explícito, de modo que el fallo es ruidoso e inmediato y nunca degrada en silencio a un sistema sin búsqueda semántica | Si aparece en una máquina de evaluación |
| U-16 | **Fiabilidad de `ejecucion_escaleta` y `arco_ejecutado`.** Es un modelo decidiendo si un beat planificado o un hito de arco ocurrieron en la prosa, y puede equivocarse en ambas direcciones: dar por ejecutado lo que solo se insinúa, o no reconocer un beat que el escritor resolvió de otra manera | Montar un juego de capítulos etiquetados a mano para dos validadores que no bloquean nada cuesta más de lo que vale. Su clase de confianza es **I**: quien decide es el Autor en el gate de Writing | Ninguno de los dos gobierna una arista del grafo. Abren incidencia de severidad `aviso`, entran en el informe de G4 y viajan al bloque 1 del capítulo siguiente, donde el escritor puede recoger lo pendiente o ignorarlo. El juicio de si el arco está *bien* lo sigue dando el juez sobre la obra entera | Si el informe resultara tan ruidoso que el Autor dejara de mirarlo, o si el escritor empezara a repetir en N+1 lo que ya había hecho en N |
| U-14 | **Cita fabricada.** El verificador comprueba que el fragmento guardado sostenga el hecho, no que el fragmento esté realmente en la URL citada | Releer las páginas duplicaría el coste de la fase y abriría una segunda puerta a internet | La fuente queda registrada con su URL, a un clic en el informe del gate; y un hecho histórico falso sigue cayendo bajo U-2 | Si una revisión encuentra un caso real |
| U-17 | **La API no tiene autenticación, y desde arq. §16.5 opera novelas.** Quien alcance el puerto puede leer una novela, pedir un cambio, lanzar una ejecución o decidir un gate, y cada invocación cuesta dinero | Montar usuarios y sesiones cuesta más que el riesgo que cubre en un sistema que corre en local, con un solo usuario que es a la vez el Autor | El servidor solo escucha en `127.0.0.1`; cada acción rechaza a un cliente no local y exige `Content-Type: application/json`, que una página ajena abierta en el navegador del Autor no puede enviar sin un permiso CORS que la API no concede. Toda acción que ejecuta el grafo pasa por la CLI, con su cerrojo y su traza | Si el backend se desplegara fuera de la máquina del Autor, o escuchara en otra interfaz que `127.0.0.1` |
| U-18 | **Que los documentos digan la verdad sobre el dominio.** La familia §11e comprueba que el código y la especificación coinciden, no que lo que ambos dicen sea lo correcto: una tabla mal pensada y un registro fiel a ella pasan en verde | No hay técnica que decida si una decisión de diseño es buena; eso es juicio, y el juicio es del Autor | El grilling de cada documento antes de bajar al siguiente, que es donde se destapan los hilos sueltos, y la revisión del Autor al cerrar cada hito. Su clase de confianza es **I** | Si un fallo real resultara estar correctamente implementado según un documento equivocado |

---

## 6. Quality Gates

Siete puertas. Cada una declara qué exige, qué evidencia produce y qué ocurre si falla.

| Gate | Momento | Exige | Evidencia | Si falla |
|---|---|---|---|---|
| **G0 · Local** | Pre-commit | ruff, mypy rápido, gitleaks | Hook local | El *commit* no se crea |
| **G1 · Integración** | Cada push a la rama de trabajo | Estática, unitarias, Hypothesis, contratos, TLC, `lake build` de *fixture*, integración con agente falso, red-team determinista y las cuatro pruebas de correspondencia de §3.9 | Build verde, más el informe de las dos que informan | No se integra. Las dos que informan no detienen nada |
| **G2 · Nocturna** | Diaria y por hito | Mutación ≥ 80 % en `commons/validation/`, CrossHair, cinco evals con modelo real, varianza del juez, sesión manual de red-teaming por hito | Informe y *dataset run* en Langfuse | No bloquea; se abre defecto y se trata en el hito |
| **G3 · Capítulo** | Tras cada `WriteChapter`, en ejecución, en dos pasadas | **Pasada determinista:** los validadores programáticos de §11a que actúan sobre el capítulo. **Pasada del extractor**, solo si la anterior queda limpia: los cuatro invariantes de Lean sobre la cronología acumulada, más `cobertura_capitulo`, `ejecucion_escaleta` y `arco_ejecutado` en calidad de aviso | Filas en `incidencia` y `score`, *scores* en la traza | Lo bloqueante vuelve al editor; agotados los dos reintentos, `Fail`. Los avisos no detienen el capítulo: viajan al encargo del siguiente y al informe de G4 |
| **G4 · Fase** | Cinco gates humanos | `cobertura_anclada` y `arco_anclado` en verde antes de abrir el gate de Plotting, y en los cinco la decisión explícita del Autor: aprobar, rehacer con comentario, editar o abortar | Fila en `gate`, `audit_log`, span en Langfuse | La ejecución se aparca. **Nunca se auto-aprueba** |
| **G5 · Publicación** | Antes de `PublishVersion` | Lean sobre la cronología completa, umbral del juez, `cobertura_personalizacion`, y `render_visual` sobre la versión candidata antes del `commit` | `manifiesto` con hashes, prompts, modelos y versión del SDK | La versión **no se publica** |
| **G6 · Post** | Tras publicar | Aserciones sobre la traza (§4.1), coste dentro de presupuesto, *scores* completos | Consulta a la API de Langfuse | Defecto abierto; la versión ya publicada no se retira |

**Regla de suspensión.** Solo el Autor puede saltarse G4, y solo desactivando los gates enteros para una ejecución en modo batch, lo que queda registrado en el manifiesto. **G3 y G5 no admiten excepción**: son las dos puertas que impiden que salga una novela con un anacronismo duro o con un capítulo sin validar.

---

## 7. Cobertura por riesgo

Lectura transversal: los siete modos de fallo que más importan y con qué se atacan. La clase indicada es la garantía *más fuerte* disponible para cada uno.

| Modo de fallo | Técnicas | Gate | Clase |
|---|---|---|---|
| Un personaje aparece fuera de sus fechas vitales | Lean (invariante 4), `anacronismo_fechado`, propiedades | G3, G5 | **A** |
| Se publica un capítulo sin validar | Validadores como nodos, `NoPublishUnvalidated` en TLC, aserción sobre la traza | G1, G6 | **A** |
| Un validador está roto y nadie se entera | Mutation testing sobre `commons/validation/`, CrossHair, contrato nodo↔hook | G2, G1 | **T** |
| Una regeneración destruye la versión anterior | Inmutabilidad y manifiesto, *trigger*, `PreviousVersionPreserved`, Hypothesis, integración de Fase 6 | G1 | **A/T** |
| Texto hostil pegado por el comprador dirige al escritor | Cuarentena y extracción tipada, suite de inyección | G1 | **A** |
| Datos personales del homenajeado salen a internet | Aislamiento del investigador, regla Semgrep, aserción sobre el prompt | G1, G6 | **A** |
| La calidad narrativa se degrada al cambiar un prompt | Evals sobre cinco briefs, canary de versión de prompt, revisión humana con rúbrica | G2, G4 | **T/I** |
| Lo que la spec declara nunca llega a implementarse | Cobertura inversa de `anclas_de_procedencia`, cubo «declarado y ausente» del inventario | G1 | **T** |
| Un validador deja de bloquear en un refactor | `registro_de_validadores` contra las tres tablas, con el registro como cableado | G1 | **A/T** |
| El grafo se cablea distinto del modelo que TLC verificó | `identidad_nodo_accion` sobre nombres y aristas, contra la definición `Aristas` | G1 | **A** |

---

## 8. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | En G3, `cobertura_capitulo` pasa de bloquear a avisar; la cobertura que bloquea queda en G5, con `cobertura_personalizacion` | Se propaga §11a de la arquitectura. Un capítulo correcto agotó sus reintentos porque el extractor no reconoció un elemento escrito de forma indirecta |
| 2026-09-24 | U-17 se reescribe: la API ya no es solo de lectura, porque la interfaz opera la novela (arq. §16.5). La mitigación pasa a ser escuchar solo en `127.0.0.1`, rechazar clientes no locales y exigir JSON en las acciones | La mitigación anterior citaba el `secret_token` del webhook de Telegram, retirado días antes; y la superficie que el riesgo describía ha crecido de leer a lanzar y decidir |
| 2026-09-24 | §3.9 acota `anclas_de_procedencia` al backend, como §11e de la arquitectura | La fila hablaba de «docstrings» y de «la spec» sin decir de qué mitad, y el frontend no tiene ni lo uno ni un §3 y §4 de contratos y fases |
| 2026-09-24 | La matriz de contratos cambia `Telegram ↔ FastAPI` por `CLI ↔ grafo`, y la fila de human-in-the-loop y §4 dicen que los gates se avisan por Telegram y se deciden en el PC | Decisión del Autor en §10 de la arquitectura: Telegram solo avisa y se retira el webhook |
| 2026-09-23 | La fila de `normalizar` en §3.3 explica **por qué el contrato se cumple ahora** y en qué medida | Al declarar los contratos para CrossHair apareció que `normalizar` no era idempotente: un sustantivo singular terminado en -s («autobús», «país», «análisis») se recortaba una vez y su plural dos, así que el guardrail cazaba el singular y dejaba pasar el plural. Se arregló recortando hasta punto fijo, a costa de algún falso positivo. En la misma pasada CrossHair encontró que `anio_de` reventaba con dígitos Unicode que `isdigit()` acepta e `int()` rechaza; quedó arreglado y el contraejemplo es un caso de `tests/unit/test_core_domain.py` |
| 2026-09-23 | Se propaga la reescritura de §11d: el mapa maestro y §4.10 pasan a **TLA+ directo** con las rutas de `formal/tla/`, entra `CorpusSelladoNoSeToca` en la tabla de invariantes y `PreviousVersionPreserved` pasa a declararse **propiedad temporal**. §3.2 añade la regla del cliente único del frontend, que bloquea porque sostiene G5 | La arquitectura resolvió su contradicción y este plan medía contra la versión vieja: un plan de verificación que comprueba cuatro invariantes donde hay cinco da por verde lo que nadie ha mirado |
| 2026-09-23 | Versión inicial | Fijar los Quality Gates y la clasificación T/A/I/D/U antes de escribir código, para que cada decisión de arquitectura nazca con su método de verificación asociado |
| 2026-09-23 | El frontend pasa a Feature-Sliced Design v2.1 y **Steiger** entra en §3.2 como análisis estático de clase **A** bajo G1, informando sin bloquear; los vectores pasan a tablas `vec0` de `sqlite-vec`, lo que añade la regla Semgrep `indice-solo-por-embeddings` y el riesgo U-15 | Una convención de carpetas propia no la comprueba nadie; FSD trae un linter oficial y convierte la estructura en una propiedad verificable. La extensión nativa, en cambio, añade la única dependencia de la pila que puede fallar por cómo esté construido el intérprete |
| 2026-09-23 | Investigation gana un validador semántico, `respaldo_fuente`, de clase **I** y cubierto por G4: el verificador lee la cita guardada y dicta si sostiene el hecho. Se añaden U-13 (fiabilidad del verificador) y U-14 (cita fabricada), y se reescribe la mitigación de U-8 | El corpus era lo único que ningún control miraba antes de que la novela se construyera encima. No bloquea ninguna arista, así que su garantía es la inspección del Autor en el gate, no una prueba |
| 2026-09-23 | G3 pasa a dos pasadas y el extractor entra **dentro** de `Validate`, antes de aprobar el capítulo: `cobertura_capitulo` bloquea, y `ejecucion_escaleta` y `arco_ejecutado` avisan con clase **I** bajo G4. `arco_anclado` se suma a G3 en el gate de Plotting con su propiedad de Hypothesis, y se añade U-16 | Nada comprobaba que el capítulo escrito ejecutara la escaleta: el extractor registraba la deriva como estado oficial y la propagaba al capítulo siguiente. Los dos validadores nuevos no bloquean porque son el juicio de un modelo sobre algo narrativo, y una puerta así gastaría los reintentos del capítulo discutiendo una lectura |
| 2026-09-23 | Tras el grilling: Lean pasa de la pasada determinista a la del extractor y gana un tercer punto de ejecución —la escaleta en el gate de Plotting—, lo que lleva la técnica 4 a G3, G4 y G5; `arco_anclado` se redefine por apariciones y admite el arco plano; se añaden cinco pruebas de integración y una propiedad de Hypothesis | Lean no podía correr antes del extractor, porque es el extractor quien escribe la cronología narrativa del capítulo. Y lo que la escaleta ya declara —la fecha de cada escena y quién está en ella— se puede verificar antes de redactar, que es donde corregir cuesta un párrafo |
| 2026-09-23 | Las rutas de este plan pasan a las de §16.3 de la arquitectura —`commons/validation/`, `commons/context/`, `commons/db/`, `commons/formal/` y `publication/` en lugar de `core/`, `context/`, `db/`, `formal/` y `render/`—, y se añade el riesgo U-17 | Este documento nombraba un Core Domain en `core/` que la arquitectura sitúa en `commons/validation/`: dos documentos apuntando a carpetas distintas habrían acabado en dos carpetas. U-17 recoge la superficie pública que abre §16.4 |
| 2026-09-23 | G4 declara los dos validadores deterministas que sostienen el gate de Plotting —`cobertura_anclada` y `arco_anclado`—, G5 precisa que `render_visual` corre sobre la versión candidata antes del `commit`, y el recuento de roles pasa a nueve | Los dos validadores del gate de Plotting no figuraban bajo ninguna puerta, así que su incumplimiento no tenía consecuencia escrita; y `render_visual` aparecía en G5 sin decir sobre qué corría, que era la contradicción con §11a de la arquitectura |
| 2026-09-23 | Entra la **técnica 19, correspondencia documento↔código** (§3.9): cuatro pruebas de trazabilidad, dos bloqueantes y dos informativas, bajo G1. §3.2 deja de presentar a Steiger como excepción y enuncia el criterio general —bloquea lo que sostiene una puerta, informa lo que describe la forma del repositorio—, §7 gana tres modos de fallo y se añade **U-18** | Las dieciocho técnicas anteriores comparaban el código consigo mismo: contra sus tipos, sus pruebas o su modelo. Ninguna lo comparaba contra la especificación que en este proyecto manda sobre él, de modo que la conformidad con la spec era lo único que se sostenía solo por disciplina |
