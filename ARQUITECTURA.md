# Arquitectura de la implementación

Mapa entre la Especificación Técnica 2.0 y el código. Si buscas dónde vive una
decisión, empieza aquí.

Cuando el código y la especificación discrepen, gana la especificación: el código es
la implementación, no la decisión.

---

## Las tres capas

```
Piel          .claude/commands/        siete comandos de barra
              gui/                     interfaz y orquestador
              CLAUDE.md                lo que siempre está en contexto

Agentes       .claude/agents/          siete subagentes, contexto aislado
              .claude/skills/          cinco procedimientos a demanda

Núcleo        src/storymaker/          propietario único del estado
              .claude/hooks/           siete puertas deterministas
              proyectos/<prj>/          ficheros: Canon, Contexto, Novela, ledger
```

La regla que las separa es ADR‑01: **los agentes proponen, el núcleo escribe.**

---

## Dónde vive cada decisión

| Sección de la Técnica | Fichero |
|---|---|
| ADR‑01 · propiedad del estado | `src/storymaker/cli.py` (única puerta de escritura) |
| ADR‑02 · la frontera se impone | `.claude/settings.json` · `.claude/hooks/` · `src/storymaker/hooks_comun.py` |
| ADR‑03 · disposición del almacén | `src/storymaker/almacen.py` |
| ADR‑04 · escribir sin transacciones | `src/storymaker/almacen.py` (`CerrojoProyecto`, `ORDEN_CANONICO`) |
| ADR‑05 · versionado de la Novela | `src/storymaker/dominio/novela.py` (`ramas.json`) |
| ADR‑06 · versionado de esquema | `src/storymaker/version_esquema.py` |
| §3 · gestión de contexto | `src/storymaker/manifiesto.py` |
| §4.2 · identificadores | `src/storymaker/ids.py` |
| §4.4 · índices derivados | `src/storymaker/indices.py` |
| §5.5 · Run Ledger | `src/storymaker/ledger.py` |
| §6.1‑6.2 · contratos | `src/storymaker/esquemas.py` · `contracts/` |
| §6.3 · invariantes no expresables en esquema | `src/storymaker/invariantes.py` |
| §6.4 · superficie del núcleo | `src/storymaker/cli.py` |
| §7 · orquestación | `src/storymaker/dominio/ejecucion.py` |
| §7.3 · terminación de bucles | `src/storymaker/bucles.py` |
| §8 · presupuestos | `src/storymaker/presupuesto.py` |
| §9 · evaluación y severidad | `src/storymaker/hallazgos.py` · `src/storymaker/bucles.py` |
| §10 · taxonomía de errores | `src/storymaker/errores.py` |
| §11 · observabilidad | `src/storymaker/dominio/traza.py` · `ejecucion.estado` |
| §12 · estrategia de pruebas | `tests/` |

## Dónde vive cada etapa

| Etapa | Subagente | Mitad determinista |
|---|---|---|
| E1 · Captura del encargo | `sm-entrada` | `dominio/encargo.py` |
| E2 · Investigación | `sm-investigacion` | `dominio/contexto.py` |
| E3 · Diseño narrativo | `sm-diseno` | `dominio/canon.py` |
| E4 · Crítica del Canon | — la escribe E3 al final de su tramo | `dominio/canon.py` (`aprobar`) |
| E5 · Redacción | `sm-redactor` | `dominio/novela.py` |
| E6 · Refinamiento | `sm-refinador` | `dominio/novela.py` (`refinar`) |
| E7 · Validación | `sm-validador` | `dominio/validacion.py` |
| E8 · Pasada global | `sm-global` | `dominio/global_.py` |

---

## Las invariantes, y quién las sostiene

Cada una se comprueba en al menos dos sitios. La redundancia es ADR‑02: el hook
protege de un agente descaminado, el núcleo protege de un error en el hook.

| INV | Enunciado | Hook | Núcleo |
|---|---|---|---|
| INV‑1 | No se redacta sobre un Canon no aprobado | `guard_canon.py` | `proyecto.exigir_canon_aprobado` |
| INV‑2 | Ninguna escena revela antes de tiempo | — | `invariantes._revelaciones_posteriores` · `validacion.comprobar_revelaciones_anticipadas` |
| INV‑3 | Toda afirmación histórica, respaldada o con licencia | — | `validacion.comprobar_licencia_de_figura` |
| INV‑4 | La Novela contiene la mejor versión, no la última | — | `novela.conservar_mejor` · `bucles.mejor_version` |
| INV‑5 | Ningún bloqueante convive con una unidad cerrada | — | `validacion.cerrar_capitulo` · `invariantes.comprobar_terminacion` · `global_._declarar_deuda_al_cerrar` barre los no bloqueantes a Deuda |
| INV‑6 | Toda modificación del Canon genera versión | — | `canon.aprobar` · `canon.replanificar` |
| INV‑7 | Ninguna Ejecución supera su presupuesto | `guard_presupuesto.py` | `presupuesto.Contabilidad.admitir` |
| INV‑8 | Toda Restricción es trazable a una afirmación vigente, y ninguna cuelga de una descartada o refutada | — | `invariantes.comprobar_derivacion_restriccion` |

---

## Las tres memorias

| Memoria | Dónde | Cuánto dura |
|---|---|---|
| Larga | `proyectos/<prj>/` | Toda la vida del Proyecto |
| De trabajo | El manifiesto que `manifiesto.construir` inyecta | Una unidad |
| Efímera | `proyectos/<prj>/tmp/<udt>/` | Se borra al cerrar la unidad |

El manifiesto de cada etapa está declarado como dato en `manifiesto.PRELACION`, y lo
que ninguna prelación puede recortar, en `manifiesto.NO_RECORTABLES`. Dar a un agente
un bloque que su etapa no declara se rechaza con ERR‑105: sin eso se perdería la
promesa de poder reconstruir con qué información se tomó cada decisión.

---

## La interfaz gráfica

| Fichero | Qué hace |
|---|---|
| `gui/servidor.py` | Servidor HTTP de biblioteca estándar. Lee los ficheros del Proyecto para pintar el panel, invoca el núcleo por lista de argumentos para todo lo demás, y expone el orquestador. `/api/flujo/<prj>` reconstruye del Run Ledger qué etapa trabajó sobre qué y cómo cerró, emparejando `unidad_iniciada` con `unidad_cerrada` |
| `gui/proceso.py` | Orquesta la Ejecución en **tres tramos** con dos paradas del Autor. Cada tramo es una sesión de `claude`, cuya salida se traduce a lenguaje legible y llega a la interfaz según se produce. De esa salida se extrae además **quién despacha a quién**: cada subagente con su tarea y su duración, y cada llamada al núcleo |
| `gui/langfuse.py` | Exporta la traza de la Ejecución por **OpenTelemetry** (`/api/public/otel/v1/traces`), en OTLP sobre JSON y con biblioteca estándar: span raíz por Ejecución, uno por tramo, uno de tipo `agent` por cada despacho de subagente y una `generation` por modelo. Las credenciales se resuelven del entorno; sin ellas, se declara que no hay traza y se sigue |
| `gui/comprobar_pagina.py` | Comprobación estática del JavaScript de la página: detecta las formas de romperla que ya conocemos |
| `src/storymaker_mcp/navegador.py` | Servidor MCP de desarrollo, sobre Playwright. Abre la página en un Chromium real y dice qué pestaña revienta. **No es parte del arnés** |
| `gui/index.html` | Página única. React y Babel por CDN, sin compilación y sin `node_modules` |

Tres decisiones la gobiernan, y son consecuencia de la regla de que sólo el núcleo
escribe. La primera es que **el servidor no escribe un solo byte bajo `proyectos/`**:
cuando la interfaz quiere cambiar algo invoca al núcleo y devuelve su sobre tal cual,
error incluido. La segunda es la **lista blanca** de `COMANDOS_PERMITIDOS`: la
superficie de la interfaz es deliberadamente más estrecha que la del CLI, y deja
fuera `escena escribir` y `unidad admitir`, que producen prosa o consumen presupuesto
y son trabajo de una etapa, no de un botón. La tercera es que **sólo escucha en
`127.0.0.1`**, porque esto expone el núcleo por HTTP y abrirlo a la red sería dar a
cualquiera la capacidad de escribir en el Proyecto.

La interfaz tiene siete vistas —componer el Encargo, proceso, estado, Contexto,
Canon, hallazgos y novela— y **ninguna despacha etapas sueltas**: la Ejecución son
tres tramos y se conduce desde *Proceso*.

Las vistas de agentes son **dos, y complementarias**: el panel en vivo de cada tramo
sale de la salida de la sesión y vive en memoria, así que enseña quién trabaja ahora
pero se pierde al reiniciar; *El flujo de agentes* sale del ledger, así que está en
disco y existe para las Ejecuciones de antes, pero sólo enseña las unidades ya cerradas.

**Ninguna etapa tiene reloj.** Lo tuvo: media hora, y el tramo de la novela murió
justo en el tope dos veces, tirando lo que llevaba escrito. Un límite que no
distingue una etapa colgada de una etapa larga corta más trabajo bueno del que
salva. En su lugar, *Proceso* enseña quién está despachado y desde cuándo —que es
lo que de verdad contesta a «esto sigue vivo»— y el botón de **parar mata la etapa
en curso**. Lo que el núcleo haya persistido sobrevive, así que una Ejecución
cortada se relanza y **continúa por donde iba**: los tramos ya superados aparecen
marcados como hechos en una tirada anterior en lugar de desaparecer de la lista.

Se arranca con `python gui/servidor.py` y responde en el puerto 8765, configurable
con `STORYMAKER_GUI_PUERTO`.

---

## Dependencias

**Ninguna en tiempo de ejecución.** El almacén son ficheros, la validación de
contratos es un subconjunto de JSON Schema implementado en `esquemas.py`, y la
interfaz gráfica trae React por CDN en lugar de un árbol de dependencias.

Para las pruebas hace falta `pytest`. El PDF de la entrega usa `pandoc` si está en el
entorno, y si no, se entrega sólo Markdown y se declara (ERR‑902).

---

## Cómo se prueba

```bash
python -m pytest tests/ -q
```

| Fichero | Nivel de §12 | Qué cubre |
|---|---|---|
| `test_invariantes.py` | Unitario determinista | Las invariantes de §6.3, **cada una con su caso que falla** |
| `test_contratos.py` | Contrato | Los quince esquemas de contrato, con casos que deben rechazarse |
| `test_almacen_y_recuperacion.py` | Recuperación | Corte simulado en cada paso del orden canónico |
| `test_presupuesto_y_bucles.py` | Unitario determinista | Los dos tramos de reserva y los cinco modos de terminación |
| `test_integracion.py` | Integración | La novela mínima de dos capítulos y cuatro escenas |
| `test_hooks_y_cli.py` | Integración | Los hooks como procesos reales, con su protocolo |

El quinto nivel de §12 —regresión de arnés sobre el conjunto de encargos de
referencia— **no está implementado**, y no lo está porque necesita un proveedor de
modelos real y un conjunto de encargos que todavía no existe. Es la única forma de
saber si un cambio en un prompt mejora o empeora el sistema; sin él, cada ajuste de
los ficheros de `.claude/agents/` es una apuesta.

---

## Lo que esta implementación no decide

Lo mismo que §13.2 deja fuera, más lo que se ha descubierto al construir:

| Asunto | Estado |
|---|---|
| Catálogo de modelos y su enrutado | Se declara en la configuración de la Ejecución, no en el código |
| Texto de los prompts y de las rúbricas | Los prompts viven en `.claude/agents/`; las rúbricas, en la skill `evaluar-con-rubrica` |
| Deriva de voz y repetición a larga distancia | `global_.indicadores_de_estilo` mide tres cosas simples. Exige calibración empírica sobre el castellano (T‑03) |
| Contradicción entre hechos en lenguaje natural | `canon._detectar_contradiccion` cubre sólo el caso comprobable —mismo sujeto, mismo atributo único, valor distinto—. El resto es comprobación por modelo con rúbrica, y así está declarado (T‑03) |
| Puerta de calidad sobre la rúbrica | T‑02: la maquinaria está, falta el umbral. Hoy las puntuaciones sólo comparan una versión consigo misma |
