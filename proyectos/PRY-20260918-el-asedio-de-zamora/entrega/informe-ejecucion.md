# Informe de ejecución — PRY-20260918-el-asedio-de-zamora

*Generado por el Agente Orquestador (CMP-031) al cierre de la Etapa 3, recorriendo la bitácora completa.
Trece bloques; la ausencia de cualquiera sería un defecto.*

---

## 1. Cabecera

| Campo | Valor |
|---|---|
| Proyecto | `PRY-20260918-el-asedio-de-zamora` |
| Título provisional | El asedio de Zamora |
| Creado | 2026-09-18T11:53:24Z |
| Estado del Proyecto | **Entregado** — entrega completa, no parcial. El Proyecto queda en solo lectura |
| Versión del arnés anclada | **1.0.0** |
| Versión de configuración | **1.0.0** |
| Versión del catálogo de clichés | **1.0.0** |
| Versión del esquema de Proyecto | `proyecto@1` |

### Encargo congelado, íntegro

Congelado el 2026-09-18T11:59:06Z por el canal **diálogo**.

| Bloque | Contenido |
|---|---|
| Época — intervalo temporal | 1072 |
| Época — ámbito geográfico | Zamora y su alfoz |
| Tema | La lealtad dividida de un caballero entre Sancho II y doña Urraca durante el cerco de Zamora |
| Personajes de partida | *(ninguno)* |
| Inspiración | ninguna |
| Parámetros | 3 capítulos · 4 párrafos por capítulo · 12 líneas por capítulo · 15 palabras por línea |

### Versiones de instrucción empleadas — **hubo mezcla**

**Sí hubo mezcla de instrucciones dentro de esta ejecución, y debe tenerse en cuenta al comparar este
informe con otro.** El Proyecto quedó anclado a `version_arnes: "1.0.0"` en el momento de crearse (ADR-015).
Entre el cierre de la Etapa 2 y el arranque de la Etapa 3, la definición del arnés en disco avanzó:
`registro-agentes.json` pasó de 1.2.0 a 2.0.0, los ficheros de instrucción perdieron el sufijo `@versión`
del nombre y el campo `version_instruccion` desapareció del registro y del esquema de bitácora.

En consecuencia:

- Las **Etapas 0, 1 y 2** se ejecutaron contra las instrucciones tal como estaban bajo el registro 1.2.0, y
  sus entradas de bitácora anteriores a la secuencia 187 llevan `version_instruccion` con sufijo.
- La **Etapa 3** se ejecutó contra las instrucciones ya editadas en su sitio bajo el registro 2.0.0, y sus
  entradas no llevan ese campo.

Se registró como `ERR-502` en la secuencia 187 y **no se detuvo la ejecución**, porque no es `ERR-202`: todos
los agentes declarados seguían teniendo fichero de instrucción y vínculo invocable. Lo que identifica una
ejecución es la versión del arnés, y aquí esa versión no es una sola a lo largo del Proyecto.

---

## 2. Intentos, rechazos y descartes por etapa

| Etapa | Invocaciones | Veredictos favorables | Rechazos | Descartes |
|---|---|---|---|---|
| etapa-0 · Encargo | 0 | — | — | — |
| etapa-1 · Investigación | 33 | 52 afirmaciones Verificadas | 17 | 9 (`ERR-704`) |
| etapa-2 · Canon | 6 | 1 Aceptado | 2 | 1 canon completo (`ERR-705`) |
| etapa-3 · Redacción | 34 | 13 escenas Aprobadas + 5 Aprobados (3 capítulos, 1 global, 1 cierre) | 2 | 0 |
| **Total** | **73** | | **21** | **10** |

Notas de lectura:

- Los 17 rechazos de la Etapa 1 son la primera vuelta de verificación de respaldo. De ellos, 8 se recuperaron
  en el segundo intento y 9 se descartaron al agotar el límite `verificacion_afirmacion` (2 intentos), con la
  política declarada `descarte_con_registro`. **Un identificador descartado no se reutiliza.**
- El descarte de la Etapa 2 es un canon entero: `ERR-705`, descarte y sustitución, tras agotar los 2 intentos
  de `validacion_elemento_canon`. El canon sustituto se aceptó en su primer ciclo.
- Las 13 escenas aprobadas de la Etapa 3 corresponden a 12 escenas: **CAP-03/ESC-03 consumió tres intentos**
  (el tercero exigido por la validación global), y la contabilidad de veredictos cuenta cada uno.

---

## 3. Hallazgos por severidad y por tipo

**46 hallazgos** emitidos por los verificadores a lo largo de toda la ejecución.

### Por severidad

| Severidad | Cuántos |
|---|---|
| Bloqueante | 9 |
| Mayor | 37 |
| Menor | 0 *(ver la advertencia de abajo)* |

**Advertencia sobre este reparto.** El cero de la fila «Menor» no significa que no hubiera hallazgos leves:
significa que `severidades.json` no contiene fila para varias de las claves que los verificadores emitieron,
y la regla por defecto las resuelve como **Mayor** (`ERR-306`). Dos afirmaciones —AF-0002 y AF-0029— y un
hallazgo de escena fueron calificados **Menor por el verificador** y elevados a Mayor por la tabla. El reparto
real de gravedad es más benigno que el que muestra esta tabla.

### Por tipo

| Tipo de hallazgo | Cuántos |
|---|---|
| `incoherencia` | 22 |
| `no_previsto` | 15 |
| `desvio_canon` | 3 |
| `sostenimiento_indirecto` | 1 |
| `ausencia_de_especificacion` | 1 |
| `afirmacion_no_atomica` | 1 |
| `falta_encaje` | 1 |
| `contradiccion_capitulo` | 1 |
| `repeticion_lexica` | 1 |

Los 15 de tipo `no_previsto` son hallazgos cuya clave de severidad no figura en la tabla. Se enumeran en el
bloque 13.

---

## 4. Hallazgos aceptados con observaciones y sin corregir

**Uno**, y sigue abierto en el manuscrito entregado.

| Campo | Valor |
|---|---|
| Identificador | `H-VER-LNG-001` |
| Verificador | AG-VER-LING, criterio 3 (repetición léxica) |
| Localización | CAP-03/ESC-03, intento 3 |
| Cita literal | «en silencio» |
| Severidad declarada por el verificador | Menor |
| Severidad resuelta por la tabla | Mayor (`ERR-306`, clave `MENOR` no listada) |
| Corrección esperada | La expresión «en silencio» aparece también en el párrafo anterior («Armas observó en silencio»). Variar la expresión |
| Por qué no se corrigió | El veredicto fue **Aceptado**: un hallazgo de esa gravedad no fuerza reescritura, y el resultado del veredicto manda sobre la transición. El orquestador **no reinterpretó** la severidad ni gastó el último intento de la escena en un hallazgo que el propio verificador aceptó |

El hallazgo queda registrado en `etapa-3/capitulos/cap-03/esc-03.i3.json`, campo `hallazgos_abiertos`, con
ambas severidades a la vista.

---

## 5. Decisiones de continuación del autor

**Una.**

| Campo | Valor |
|---|---|
| Punto de control | **PCH-3** · cobertura deficitaria |
| Momento | Al cierre de la Etapa 1, antes de sellar el Contexto Histórico (bitácora, secuencia 159) |
| Opción elegida | `continuar_con_cobertura_incompleta` |
| Motivo registrado | El autor confirma la cobertura Incompleta y autoriza el sellado pese al conflicto `ERR-802` entre las `invariantes_al_sellar` del esquema `contexto-historico@1` y los valores de `configuracion@1` para diecisiete dimensiones |
| Consecuencia | La Etapa 1 cerró en estado **`Cerrada_incompleta`**. Sin esta confirmación la Etapa 2 no habría arrancado. La decisión queda escrita **dentro del artefacto sellado**, no solo en la bitácora |

No hubo ninguna otra intervención del autor: no se concedieron intentos adicionales, no se aportó texto y no
se aceptó nada con observaciones por decisión suya.

---

## 6. Dimensiones con cobertura deficitaria

De las **17 dimensiones** investigadas, **una** quedó por debajo del mínimo declarado en
`configuracion.json` (mínimo 2 afirmaciones verificadas por dimensión):

| Dimensión | Afirmaciones verificadas | Mínimo | Estado |
|---|---|---|---|
| `comunicacion_saber` | **1** (AF-0040) | 2 | **Deficitaria** |

Reparto completo de las 52 afirmaciones que quedaron en el Contexto Histórico sellado:

| Dimensión | n.º | | Dimensión | n.º |
|---|---|---|---|---|
| `economia` | 5 | | `religion` | 3 |
| `estructura_social` | 5 | | `mentalidad` | 3 |
| `poder_politico` | 4 | | `tiempo` | 2 |
| `cultura_material` | 4 | | `demografia` | 2 |
| `vida_cotidiana` | 4 | | `derecho_justicia` | 2 |
| `arte_estetica` | 4 | | `ciencia_tecnica` | 2 |
| `conflicto_disidencia` | 4 | | `relaciones_exteriores` | 2 |
| `espacio` | 3 | | `ausencias` | 2 |
| | | | `comunicacion_saber` | **1** |

El déficit se registró como `ERR-901` (secuencia 156), abrió PCH-3 y lo resolvió el autor según el bloque 5.

---

## 7. Licencias literarias declaradas

**Dos**, ambas declaradas por el Constructor de Canon en el canon congelado.

### LL-01 — Los movimientos previos de Bellido Dolfos

- **Elemento afectado:** Bellido Dolfos y sus movimientos previos al asesinato.
- **Desviación:** se muestra a Armas presenciando reuniones nocturnas y movimientos sospechosos de Bellido
  Dolfos durante las semanas anteriores al 7 de octubre.
- **Justificación:** las fuentes dicen que Bellido fingió ser desertor, pero no detallan cómo fue recibido ni
  qué conversaciones tuvo. La licencia dramatiza el período de espera y prepara el giro sin contradecir lo
  verificado en AF-0002.

### LL-02 — La presencia de Urraca

- **Elemento afectado:** presencia de doña Urraca en relación con el campamento.
- **Desviación:** Urraca figura como conocida de lejos o en negociaciones neutrales con el campamento de
  Sancho.
- **Justificación:** Urraca defendía Zamora, pero ninguna fuente indica contacto directo con el protagonista.
  Son constructos narrativos que representan la conciencia de Armas sobre la otra parte del conflicto,
  respaldados en AF-0021.

**Nota sobre LL-02 en el manuscrito final:** la licencia está declarada, pero **doña Urraca no llega a
aparecer en escena** en ninguno de los doce párrafos. Solo se la menciona una vez, de forma indirecta, en
CAP-01/ESC-04 («un jinete… decía que desertaba de la corte de Urraca»). La licencia se declaró y no se usó.

Clichés deliberados declarados: **ninguno**. Conflictos entre Encargo y Contexto Histórico: **ninguno**.

---

## 8. Capítulos sin respaldo histórico

**Ninguno.** El canon congelado declara `elementos_no_respaldados: []`: los tres capítulos apoyan sus
elementos rastreables en afirmaciones del Contexto Histórico sellado.

Debe leerse con la reserva que el propio arnés declara: el respaldo es un **control declarado, no una
garantía**. Sin código no hay comparación literal; lo que el arnés promete es que un verificador dictaminó con
el Contexto y el Inventario de Prohibidos delante. Además, **las fuentes no se filtran**: una fuente mala con
un fragmento coherente produce una afirmación verificada falsa, y esa afirmación respaldaría un capítulo sin
que nada aquí lo advirtiera.

---

## 9. Hallazgos de la validación global

La validación global se ejecutó **dos veces**: el límite `validacion_global` concede **una** vuelta de
corrección, y se consumió entera.

### Intento 1 — **Rechazado** (2 de 3 criterios)

| Campo | Valor |
|---|---|
| Identificador | `HAL-001` |
| Criterio | 1 · contradicciones entre capítulos distantes |
| Severidad | Bloqueante |
| Localización | CAP-03/ESC-03 |
| Cita literal | «Esa noche, en la tienda, Armas yacía despierto mientras el viento corría entre las filas de hombres dormidos.» |
| Corrección exigida | Fechar la escena o marcar la transición: tras una escena del 28 de septiembre, «Esa noche» contradecía la fecha del canon para esa escena, el 6 de octubre |

El hallazgo **traía localización**, y por eso volvió al bucle interior **una sola escena** y no las cuatro del
capítulo. Un hallazgo de capítulo sin localización habría mandado las cuatro y multiplicado el coste por
cuatro (H-T16).

### Intento 2 — **Aceptado** (3 de 3 criterios), sin hallazgos

| Criterio | Cumple |
|---|---|
| 1 · Contradicciones entre capítulos distantes | Sí |
| 2 · No reproducción literal de fuentes | Sí |
| 3 · Conformidad con el Canon en su conjunto, incluida la resolución del arco | Sí |

El manuscrito alcanzó el estado de cierre **`Validado_globalmente`**.

---

## 10. Extensión obtenida frente a la solicitada — **ESTIMACIÓN**

**Las cifras de palabras de este bloque son estimaciones, no recuentos.** Bajo RES-11 no hay código que cuente
palabras: son aproximaciones declaradas. La única magnitud exacta es el **número de párrafos**, porque es
contar ficheros.

### Párrafos — magnitud exacta

| Capítulo | Solicitados | Obtenidos | Desviación |
|---|---|---|---|
| CAP-01 | 4 | 4 | 0 |
| CAP-02 | 4 | 4 | 0 |
| CAP-03 | 4 | 4 | 0 |
| **Total** | **12** | **12** | **0** |

### Palabras — estimación

Objetivo derivado del Encargo: 12 líneas por capítulo ÷ 4 párrafos = 3 líneas por párrafo × 15 palabras =
**45 palabras por párrafo**, 180 por capítulo, 540 en total. Tolerancias de `configuracion.json`: **±20 % por
párrafo** (36–54) y **±10 % por capítulo** (162–198).

| Capítulo | ESC-01 | ESC-02 | ESC-03 | ESC-04 | Capítulo | Desviación |
|---|---|---|---|---|---|---|
| CAP-01 | 45 | 47 | 52 | 45 | 189 | +5,0 % |
| CAP-02 | 39 | 45 | 50 | 51 | 185 | +2,8 % |
| CAP-03 | 45 | 45 | 43 | 47 | 180 | 0,0 % |
| **Total** | | | | | **554** | **+2,6 %** |

**Los doce párrafos caen dentro de la tolerancia de ±20 %** (el más corto, 39; el más largo, 52) y **los tres
capítulos dentro de la de ±10 %**. Ninguna desviación de longitud quedó fuera de lo tolerado.

---

## 11. Cota de invocaciones frente a consumo real; duración por etapa

La cota se calcula con las fórmulas de §12.6 de la especificación técnica, para C=3 capítulos, P=4 párrafos y
17 dimensiones de investigación. **No hay presupuesto de parada**: ninguna ejecución se aborta por coste. Esto
es contabilidad, no control.

| Etapa | Cota típica | Consumo real | Duración |
|---|---|---|---|
| etapa-0 · Encargo | — | 0 | — |
| etapa-1 · Investigación | ≈ 38 | **33** | 49,2 min |
| etapa-2 · Canon | ≈ 5 | **6** | 16,2 min |
| etapa-3 · Redacción | 34 | **34** | 23,1 min |
| **Total** | **≈ 77** | **73** | **88,5 min** |

Peor caso declarado para esta configuración: **86** invocaciones sin reescritura total de capítulo, **158** con
ella. El consumo real (73) queda por debajo de la cota típica y muy por debajo de ambos peores casos.

El umbral de anomalía por coste es `factor_anomalia_sobre_cota_tipica: 1.5`, es decir **115 invocaciones**.
**No se superó**, así que no procede señalarlo como anomalía en el bloque 13.

Los tiempos son la suma de latencias registradas por invocación; no incluyen el tiempo de decisión del autor
en PCH-3, que no tiene límite y no se contabiliza.

---

## 12. Omisiones de contexto por desbordamiento, agrupadas por prioridad

El presupuesto de entrada declarado es de **40.000 palabras aproximadas** por invocación. **Ninguna invocación
lo desbordó**: la mayor rondó las 2.200 palabras, un 5 % del presupuesto.

Por tanto, **ninguna de las 15 omisiones registradas se debe a desbordamiento**. Todas tienen motivo
`fuera_de_contrato`: el bloque existía y cabía, pero el contrato declarado del modo invocado no lo admite.

| Prioridad | Artefacto omitido | Veces | Motivo |
|---|---|---|---|
| P3 | `contexto-historico@1.fragmentos` | 1 | `fuera_de_contrato` — el modo de construcción de canon recibe las afirmaciones, no los fragmentos literales de fuente |
| P4 | `escenas_aprobadas_del_capitulo` | 14 | `fuera_de_contrato` — el contrato de la escena da el párrafo inmediatamente anterior, no todas las escenas aprobadas |
| P6 | `resumen_acumulado` | 14 | `fuera_de_contrato` — el resumen acumulado entra en la verificación de capítulo, no en la redacción de escena |

**Ninguna omisión de prioridad P0, P1 ni P2.** El bloque P1 —hallazgos del intento anterior— **nunca es
descartable**, y en esta ejecución nunca se descartó: en CAP-03/ESC-03 se ensamblaron los **dos** conjuntos de
hallazgos acumulados y en conflicto, que es precisamente lo que permitió resolverlo.

---

## 13. Anomalías

Este bloque es el que impide que el informe sea autocomplaciente. **No se oculta nada de lo que sigue.**

### 13.0 ¿Ejecución sin rechazos?

**No.** Hubo 21 rechazos y 10 descartes repartidos por las tres etapas. El control de calidad **sí** rechazó,
de modo que no procede la anomalía de RF-039 escenario 2, que marcaría como sospechosa una ejecución en la que
nada se rechazó nunca.

### 13.1 `ERR-502` · La definición del arnés cambió a mitad de Proyecto

Entre el cierre de la Etapa 2 y el arranque de la Etapa 3, `registro-agentes.json` pasó de 1.2.0 a 2.0.0, los
ficheros de instrucción perdieron el sufijo de versión del nombre y `version_instruccion` desapareció del
registro y del esquema de bitácora. El Proyecto sigue anclado a `version_arnes: "1.0.0"` (ADR-015), de manera
que **este Proyecto mezcla instrucciones de dos versiones del arnés**. Se registró en la secuencia 187 y **no
se detuvo la ejecución**, porque no es `ERR-202`: todos los agentes declarados conservaban fichero y vínculo.
Consta también en el bloque 1. Es la anomalía más importante de esta ejecución a efectos de comparación entre
ejecuciones.

### 13.2 `ERR-301`/`ERR-302` · Defecto sistémico de acoplamiento entre el arnés y el entorno

**Doce veces** la salida de un agente no cumplió su contrato. **Once** de ellas fueron la misma falla: el
agente devolvió una **descripción en prosa de lo que había producido** en lugar del artefacto: «Canon construido y emitido conforme a…», en vez del JSON. El contrato pide el artefacto; el
mecanismo de devolución del entorno invita a informar sobre él. La duodécima (secuencia 152) fue distinta: un vallado de código
alrededor de un JSON por lo demás correcto. Cada caso se reparó con la única reparación dirigida que concede
`reparacion_contrato` (`ERR-301`, que **no** consume intento), salvo **tres** que volvieron a fallar en la
reparación y escalaron a `ERR-302`, consumiendo un intento **sin producir nada**:

| Secuencia | Unidad | Coste |
|---|---|---|
| 21 | `verificacion_afirmacion:demografia` | 1 intento perdido |
| 166 | `canon:canon` | 1 intento perdido — contribuyó al descarte del canon |
| 177 | `canon:canon-sustituto` | 1 intento perdido |

Se registró como anomalía de **acoplamiento arnés-entorno** (secuencia 178). **No es un defecto de L1 ni de la
instrucción del agente**, que piden el artefacto con claridad: es la frontera entre el contrato declarado y la
forma en que el entorno devuelve el trabajo de un subagente. Reformular la petición como «**tu informe final
es el artefacto**» en lugar de «devuelve solo el texto» redujo la frecuencia de casi universal a
aproximadamente uno de cada seis, y después de ese cambio **no volvió a producirse ningún `ERR-302`**. Es
el hallazgo más accionable de esta ejecución para el arnés.

### 13.3 `ERR-306` · Tipos de hallazgo no previstos — **15 casos**

`severidades.json` no contiene fila para varias claves que los verificadores emitieron. La regla por defecto
las resuelve como **Mayor**, que es la severidad que fuerza reescritura.

| Clave emitida | Origen | Veces |
|---|---|---|
| `respaldo_insuficiente`, `afirmacion_no_atomica`, `fuera_de_epoca_o_ambito`, `dimension_incorrecta` | AG-VER-INV, modo respaldo | 12 |
| `INCONSISTENCIA_TEMPORAL`, `MENOR`, `mayor` | claves inventadas por los verificadores | 3 |

**Consecuencia real:** AF-0002 y AF-0029 fueron calificadas **Menor** por el verificador, elevadas a Mayor por
la tabla y **descartadas** al agotar sus intentos. Dos afirmaciones que el propio verificador consideraba leves
no llegaron al Contexto Histórico por una fila que falta en una tabla. No se corrigió durante la ejecución,
porque cambiar `severidades.json` sería cambiar el arnés al que este Proyecto está anclado.

### 13.4 `ERR-802` · El esquema y la configuración se contradicen al sellar

`contexto-historico@1` declara en sus `invariantes_al_sellar` entre 3 y 8 afirmaciones por dimensión y un
total máximo de 50 —valores de SUP-007, pensados para **siete** dimensiones—, mientras `configuracion.json`
declara mínimo 2, máximo 4 por dimensión y tope 52 para **diecisiete**. Ningún reparto satisface ambos. El
sellado quedó suspendido (secuencias 157 y 160) y solo se completó por la decisión expresa del autor en PCH-3,
que consta **dentro del artefacto sellado**.

### 13.5 `ERR-802` · Dos verificadores en conflicto directo sobre el mismo pasaje

Sobre la apertura de CAP-03/ESC-03:

1. AG-VER-LING rechazó «Ocho días después» porque, tras un párrafo que abría con «Diez días después», se leía
   como cuenta atrás.
2. El redactor escribió «Esa noche» y AG-VER-LING lo aceptó.
3. AG-VER-CANON-HIST, en validación global, rechazó «Esa noche» y propuso «Ocho días después, aquella
   noche» — **reintroduciendo la forma que el primero había rechazado**.

El orquestador **no arbitró**: aplicó la política declarada, devolvió la escena al bucle interior con **ambos**
conjuntos de hallazgos como bloque P1 indescartable y dejó que el redactor encontrara la salida que cerraba los
dos criterios a la vez, que fue nombrar la fecha del canon: «La noche del 6 de octubre de 1072…». Se resolvió
en el **tercero y último** intento disponible. Un intento más de mala suerte y esto habría bloqueado en PCH-7.

### 13.6 `ERR-501` · Ubicuidad en el primer canon

El primer canon declaró **un solo momento narrativo por capítulo**, compartido por sus cuatro escenas, que
transcurrían en lugares distintos. El resultado era que Sancho II, Bellido Dolfos y el protagonista estaban en
varios sitios a la vez. Lo detectó el orquestador al sellar (CMP-009) y lo dictaminó el verificador de canon
(criterio 2, **3 hallazgos Bloqueantes**). El canon se descartó por `ERR-705` y el sustituto declaró **doce
momentos narrativos fechados y distintos**, que son los que gobiernan la cronología del manuscrito.

### 13.7 Residuo del canon descartado dentro del canon congelado

La sinopsis del canon congelado para **CAP-03/ESC-04 nombra a «Rodrigo»**, protagonista del canon descartado,
donde todo el resto del artefacto dice **Armas**. **El canon es inmutable** (`ERR-501`): corregirlo habría sido
un error de sistema. El orquestador lo **declaró explícitamente en el contexto ensamblado** para el redactor y
para los verificadores, advirtiendo que el protagonista es Armas y que la discrepancia no debía tratarse como
hallazgo. El manuscrito no contiene el nombre Rodrigo en ningún punto. **El defecto sigue en el artefacto
congelado y seguirá ahí**: la única vía de cambio sería `/etapa-repetir`, que archiva y rehace la etapa entera.

### 13.8 `ERR-306` · Divergencia entre el lugar de la escena y el lugar de la presencia

En el canon sustituto, la ficha de presencia de algunos personajes declara un lugar distinto del `lugar` de la
escena en que aparecen. Se registró (secuencia 182) y no se corrigió: el canon ya estaba congelado.

### 13.9 `ERR-902` · Tensión entre atomicidad y tope global

El criterio de atomicidad del Investigador —una afirmación, un hecho— empuja hacia más afirmaciones, mientras
el tope global de 52 las limita. Al reintentar las rechazadas, ambas exigencias se estorbaron (secuencia 97).
Se registró como tensión declarada y se continuó.

### 13.10 Reparto por dimensión fuera de los topes declarados

La primera entrega del Investigador (secuencia 8) repartió las afirmaciones entre dimensiones sin respetar los
topes de `configuracion@1`. Se registró y el reparto final se ajustó en el resellado.

### 13.11 `ERR-405` · La conversión a PDF no se pudo realizar — **dos veces**

La herramienta de hoja **HOJ-002** (Markdown → PDF) no está disponible en este entorno: no hay pandoc,
wkhtmltopdf ni biblioteca de generación de PDF instalada. Falló en el paso `conversion` de la Etapa 3 y volvió
a fallar en `entrega.obtener`. Se aplicó las dos veces el comportamiento declarado en `herramientas.json` y en
RF-053, caso límite: **la entrega en Markdown se considera completa y el fallo se registra**. No se detuvo
nada, no se degradó ningún otro artefacto y **no se buscó una vía alternativa**, porque una herramienta de
hoja transforma y no decide. `entrega/manuscrito.pdf` **no existe**, y el Proyecto pasó a `Entregado` sin él.

### 13.12 Discrepancias entre estado y bitácora

**Ninguna.** El estado se escribió siempre en el orden declarado por CMP-005 —artefacto, bitácora, copia del
estado anterior, estado nuevo—, la secuencia de bitácora es continua y sin huecos ni repeticiones, y
el índice de segmentos concuerda con el contenido de los ficheros. No se detectó ningún veredicto malformado
más allá de los `ERR-301` ya enumerados, ni ningún campo del Encargo ignorado: los cinco bloques y los cuatro
parámetros se usaron.

---

## Advertencia final — lo que este informe **no** demuestra

Consta por exigencia del propio arnés, y debe repetirse en cualquier lectura académica de estos resultados:

- **Cero anacronismos, longitud exacta y no reproducción de fuentes son controles declarados, no garantías.**
  Sin código no hay recuentos ni comparaciones literales. Lo que el arnés promete es que un verificador buscó
  con el inventario delante, no que no haya nada.
- **Esta ejecución no es reproducible.** No hay control de semilla: el campo `semilla` vale `null` en las 276
  entradas de bitácora, y se registra precisamente para que nadie suponga lo contrario. Repetir la ejecución no
  daría este manuscrito.
- **La coherencia a distancia media está degradada por diseño.** Con 3 capítulos el manuscrito entero cupo en
  la validación global, así que aquí la degradación no llegó a manifestarse; en una novela larga sí lo haría.
- **Las fuentes no se filtran.** Se registra el dominio y aparece en el registro de cada afirmación. Una fuente
  mala con un fragmento coherente produce una afirmación verificada falsa.

---

## Artefactos entregados

| Artefacto | Ruta | Estado |
|---|---|---|
| Manuscrito | `entrega/manuscrito.md` | Entregado — 12 párrafos, idéntico al de `etapa-3/manuscrito.md` |
| Manuscrito en PDF | `entrega/manuscrito.pdf` | **No generado** (`ERR-405`, bloque 13.11) |
| Informe de ejecución | `entrega/informe-ejecucion.md` | Este documento. No se exporta a PDF: es material de auditoría, no de lectura |

---

*Informe generado el 2026-09-18. Bitácora recorrida al emitirlo: 276 entradas, secuencias 1 a 276, en 6
segmentos —la única consulta que paga un recorrido total, y solo se paga una vez—. Las siete entradas
posteriores (emisión de este informe, los dos `ERR-405` de conversión, cierre de la Etapa 3, ensamblado de
entrega, entrega del informe y paso del Proyecto a `Entregado`) se incorporaron a los bloques 1, 11 y 13 sin
repetir el recorrido. Bitácora final: 283 entradas, secuencias 1 a 283.*
