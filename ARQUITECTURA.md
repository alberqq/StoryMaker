# Arquitectura de la implementación

Mapa entre la Especificación Técnica 2.0 y el código. Si buscas dónde vive una
decisión, empieza aquí.

Cuando el código y la especificación discrepen, gana la especificación: el código es
la implementación, no la decisión.

---

## Las tres capas

```
Piel          .claude/commands/        ocho comandos de barra
              CLAUDE.md                lo que siempre está en contexto

Agentes       .claude/agents/          nueve subagentes, contexto aislado
              .claude/skills/          seis procedimientos a demanda
              src/storymaker_mcp/      dos servidores de recuperación

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
| E2 · Refutación | `sm-refutador` | `dominio/contexto.py` (`refutar`) |
| E3 · Diseño narrativo | `sm-diseno` | `dominio/canon.py` |
| E4 · Validación del Canon | `sm-validador-canon` | `dominio/canon.py` (`aprobar`) |
| E5 · Redacción | `sm-redactor` | `dominio/novela.py` |
| E6 · Refinamiento | `sm-refinador` | `dominio/novela.py` (`refinar`) |
| E7 · Validación | `sm-validador` | `dominio/validacion.py` |
| E8 · Pasada global | `sm-global` | `dominio/global_.py` |

---

## Las nueve invariantes, y quién las sostiene

Cada una se comprueba en al menos dos sitios. La redundancia es ADR‑02: el hook
protege de un agente descaminado, el núcleo protege de un error en el hook.

| INV | Enunciado | Hook | Núcleo |
|---|---|---|---|
| INV‑1 | No se redacta sobre un Canon no aprobado | `guard_canon.py` | `proyecto.exigir_canon_aprobado` |
| INV‑2 | Ninguna escena revela antes de tiempo | — | `invariantes._revelaciones_posteriores` · `validacion.comprobar_revelaciones_anticipadas` |
| INV‑3 | Toda afirmación histórica, respaldada o con licencia | — | `validacion.comprobar_licencia_de_figura` |
| INV‑4 | La Novela contiene la mejor versión, no la última | — | `novela.conservar_mejor` · `bucles.mejor_version` |
| INV‑5 | Ningún bloqueante convive con una unidad cerrada | — | `validacion.cerrar_capitulo` · `invariantes.comprobar_terminacion` |
| INV‑6 | Toda modificación del Canon genera versión | — | `canon.aprobar` · `canon.replanificar` |
| INV‑7 | Ninguna Ejecución supera su presupuesto | `guard_presupuesto.py` | `presupuesto.Contabilidad.admitir` |
| INV‑8 | Ninguna Restricción de afirmación no verificada | — | `invariantes.comprobar_derivacion_restriccion` |
| INV‑9 | Nada en serie antes del piloto aceptado | `guard_canon.py` | `novela.escribir` |

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

## Dependencias

**Ninguna en tiempo de ejecución.** El almacén son ficheros, la validación de
contratos es un subconjunto de JSON Schema implementado en `esquemas.py`, y los
servidores MCP hablan JSON‑RPC sobre entrada y salida estándar sin biblioteca.

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
| `test_contratos.py` | Contrato | Los veinte contratos, con casos que deben rechazarse |
| `test_almacen_y_recuperacion.py` | Recuperación | Corte simulado en cada paso del orden canónico |
| `test_presupuesto_y_bucles.py` | Unitario determinista | Los dos tramos de reserva y los cinco modos de terminación |
| `test_integracion.py` | Integración | La novela mínima de dos capítulos y cuatro escenas |
| `test_hooks_y_cli.py` | Integración | Los hooks como procesos reales, con su protocolo |
| `test_mcp.py` | Contrato | Que ningún resultado salga sin localizador y fecha |

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
| Índice vectorial del corpus | `storymaker_mcp/rag.py` recupera por términos. El índice vectorial sigue pendiente de prueba de concepto |
| Puerta de calidad sobre la rúbrica | T‑02: la maquinaria está, falta el umbral. Hoy las puntuaciones sólo comparan una versión consigo misma |
