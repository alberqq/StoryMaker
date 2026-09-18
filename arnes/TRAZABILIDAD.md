# Trazabilidad entre el arnés y las especificaciones

Las especificaciones de [`docs/`](../docs/) son el contrato y **están al día**. Este fichero no las sustituye
ni las corrige: solo dice qué pieza del arnés materializa cada decisión, para que quien lea `arnes/` sepa a
qué requisito responde y quien lea `docs/` sepa dónde está implementado.

**Regla.** Si un cambio en `arnes/` contradice lo que dice `docs/`, el trabajo no está terminado hasta que la
especificación se haya actualizado y el cambio conste en su registro —§18.5 de la Funcional, Anexo A.6 de la
Técnica—. Un fichero de desviaciones no es sustituto de propagar: el registro guarda el porqué, que es
justamente lo que un diff no conserva.

---

## Decisiones de v1.1

Las cuatro nacieron durante la implementación y están propagadas a ambos documentos.

| # | Decisión | Afirmación | Funcional | Técnica | Arnés |
|---|---|---|---|---|---|
| 1 | Diecisiete dimensiones de investigación, de esquema historiográfico | E75 | RF-005, §3, §6.1, §7.1, §11.1 | CMP-008 | `dimensiones.json` v2.1.0 |
| 2 | Topes 2/4/52 y 2 búsquedas por dimensión | E76 | RF-014, RF-054, RNF-025, SUP-007 | CMP-037 | `configuracion.json → investigacion` |
| 3 | El Inventario de Prohibidos se juzga en el bucle exterior | E77 | RF-028, RF-030 | ADR-026, CMP-024, CMP-026, CTR-006, CTR-007 | `verificador-linguistica.md`, `verificador-canon-historia.md` |
| 4 | Una invocación realiza toda la investigación; la verificación se agrupa por dimensión | E78 | — (cardinalidad no fijada por ninguna RF) | ADR-025, CMP-015, CMP-016, §12.6 | `investigador.md`, `verificador-investigacion.md`, `orquestador.md` |

| 5 | Las instrucciones de los agentes dejan de versionarse: se editan en su sitio | E79 | RF-050, RNF-007, RNF-021 | ADR-010, CTR-002, CTR-009, CTR-011, §12.3 | `arnes/agentes/*.md` sin sufijo; `registro-agentes.json` v2.0.0 |

## Defecto corregido sin cambio de especificación

| Defecto | Qué pasó | Por qué no cambia la especificación |
|---|---|---|
| Invocaciones en paralelo en la Etapa 1 | El orquestador lanzó varios Investigadores a la vez: treinta y un artefactos en disco sin una sola entrada de bitácora, estado detenido en la invocación 1, procedencia perdida | **ADR-013 ya lo prohibía.** Era un defecto de implementación, no una laguna del diseño. `orquestador.md` incorpora la tabla de cardinalidad por paso y la prohibición explícita de abanicar. Queda registrado en el Anexo A.6 de la Técnica por ser la primera confirmación empírica de por qué el escritor único no es negociable |

## Lo que el arnés añade y la especificación no nombra

Detalles del CÓMO que no amplían alcance y que se documentan en su propio artefacto:

| Elemento | Dónde | Por qué existe |
|---|---|---|
| `clave_severidad` en el hallazgo | `severidades.json`, `hallazgo.schema.json` | El enum `tipo` de CTR-003 es demasiado grueso para distinguir filas de RF-051 con severidades distintas: «error gramatical» (Mayor) y «repetición léxica» (Menor) son ambos `defecto_lexico` |
| `encargo` y `derivados` en el enum del cursor | `estado-ejecucion.schema.json` | Los dieciocho tipos de unidad de §7.2 no cubren la Etapa 0, pero el estado se inicializa al crear el Proyecto y el cursor necesita valor |
| `prioridad_al_repartir` | `dimensiones.json` | Reparte la holgura de afirmaciones hacia la dimensión de la que depende el Inventario de Prohibidos |
