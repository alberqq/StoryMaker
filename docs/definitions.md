# Definiciones — Ontología de generación de novelas históricas

Este documento es el glosario de la ontología. Define cada concepto del dominio, sus atributos principales y el módulo al que pertenece. Los diagramas y la explicación de cómo se relacionan los conceptos están en `domain-knowledge.md`.

La ontología se organiza en cinco módulos:

| Módulo | Propósito |
|---|---|
| **1. Mundo histórico** | La realidad documentada de la que se parte. |
| **2. Anatomía narrativa** | La obra que se construye. |
| **3. Frontera historia–ficción** | El punto donde historia y ficción se unen y se declaran. |
| **4. Calidad** | Los criterios con los que se juzga el resultado. |
| **5. Proceso de generación** | Cómo produce la novela la solución. |

**Principio rector:** todo elemento narrativo debe poder rastrearse hasta una de tres cosas: un hecho documentado, una inferencia plausible o una licencia declarada.

---

## 1. Mundo histórico

| Concepto | Definición | Atributos principales |
|---|---|---|
| **Período** | Intervalo temporal acotado que rige la validez de todo lo demás. | inicio, fin, granularidad (siglo, década, año, día), denominación historiográfica |
| **Lugar** | Espacio geográfico tal como era en el período. No equivale al lugar actual. | toponimia de época, toponimia actual, fronteras, urbanismo, clima, paisaje |
| **Evento histórico** | Hecho documentado con consecuencias. Puede ser puntual (una batalla) o un proceso (una epidemia). | fecha o rango, lugar, participantes, causas, consecuencias, tipo |
| **Personaje histórico** | Persona real documentada. Combina hechos biográficos verificables con zonas de silencio documental donde la ficción puede operar. | nombre, fechas vitales, cargos, relaciones documentadas, rasgos atestiguados, lagunas |
| **Estructura social** | Instituciones, jerarquías y normas que condicionan lo que un personaje puede hacer. | instituciones, leyes, economía, religión, roles de género, roles de clase |
| **Cultura material** | Todo lo tangible disponible en el período. | objetos, vestimenta, alimentación, tecnología, moneda, armas, transporte, fecha de aparición |
| **Mentalidad** | Cosmovisión de la época: lo que se creía, se temía, se valoraba y se sabía del mundo. | creencias, valores, tabúes, conocimiento científico, supersticiones |
| **Lenguaje de época** | Léxico, registros y usos propios del período y del grupo social. | léxico, fórmulas de tratamiento, registros, expresiones, fecha de primera documentación |
| **Dimensión del período** | Cada uno de los seis ángulos desde los que se documenta un período: cronología y eventos, lugar y toponimia, cultura material, lenguaje de época, mentalidad y estructura social. Son las seis entradas de esta tabla que un corpus debe dejar pobladas. | nombre, hechos recogidos |
| **Fuente** | Documento que respalda un hecho. | tipo (primaria o secundaria), autor, fecha, fiabilidad, referencia |
| **Fuente primaria** | Documento contemporáneo a los hechos, como una crónica, una carta o un registro. | — |
| **Fuente secundaria** | Elaboración posterior sobre los hechos, como la historiografía o los estudios académicos. | — |
| **Hecho** | Afirmación sobre el mundo acompañada de su estado epistémico. | enunciado, estado, fuentes, cita, entidades implicadas |
| **Cita** | Fragmento textual de la Fuente, copiado tal cual, en el que se apoya un Hecho concreto. Es lo que hace comprobable el Hecho sin volver a la Fuente. | texto, fuente de la que procede |
| **Respaldo** | Propiedad de la Cita, no del Hecho: si el fragmento guardado sostiene o no lo que el Hecho enuncia. No debe confundirse con el estado epistémico, que es una propiedad del Hecho en la historiografía. | respaldado, no respaldado, no aplica |
| **Hecho verificado** | Hecho respaldado por fuentes fiables y concordantes. | — |
| **Hecho debatido** | Hecho sobre el que las fuentes o los historiadores discrepan. | — |
| **Hecho inferido** | Hecho no documentado, pero razonablemente deducible del contexto. | — |
| **Hecho desconocido** | Laguna documental. Es un espacio legítimo para la ficción. | — |

---

## 2. Anatomía narrativa

### 2.1 Obra y concepto

| Concepto | Definición | Atributos principales |
|---|---|---|
| **Obra** | La novela completa. | título, género, subgénero, extensión, público objetivo, período, lugar principal |
| **Premisa** | Planteamiento central en una o dos frases: quién quiere qué, en qué contexto histórico y qué se lo impide. | protagonista, deseo, obstáculo, contexto |
| **Tema** | Idea o pregunta de fondo que la obra explora y que da unidad al conjunto. | enunciado, pregunta temática |
| **Género / Subgénero** | Convenciones que el lector espera encontrar. | bélica, intriga, romántica, biográfica, aventuras, costumbrista… |

### 2.2 Trama y estructura

| Concepto | Definición | Atributos principales |
|---|---|---|
| **Trama** | Secuencia causal de acontecimientos. | tipo (principal o subtrama), personajes implicados, eventos históricos entrelazados |
| **Trama principal** | Línea argumental que sostiene la obra. | — |
| **Subtrama** | Línea secundaria que complementa, refleja o contrasta con la principal. | — |
| **Conflicto** | Oposición que genera tensión. | tipo, partes, apuesta, resolución |
| **Conflicto interno** | El personaje contra sí mismo. | — |
| **Conflicto interpersonal** | El personaje contra otros personajes. | — |
| **Conflicto social-histórico** | El personaje contra su época: sus normas, su poder o sus acontecimientos. | — |
| **Estructura** | Organización macro de la trama. | modelo (tres actos, viaje del héroe, coral…), puntos de giro |
| **Acto** | Gran bloque estructural con una función dramática: planteamiento, nudo o desenlace. | función, puntos de giro |
| **Capítulo** | Unidad de lectura que agrupa escenas y suele cerrar con un gancho o un cambio de estado. | número, título, escenas, gancho final |
| **Escena** | Unidad dramática mínima. Es la pieza clave para generar y evaluar. | escenario, tiempo histórico, personajes presentes, punto de vista, objetivo, conflicto, resultado, anclajes |
| **Beat** | Micro-acción o cambio emocional dentro de una escena. | acción, cambio de valor |

### 2.3 Personajes

| Concepto | Definición | Atributos principales |
|---|---|---|
| **Personaje** | Entidad que actúa en la historia. | nombre, tipo, rasgos, objetivo, necesidad, miedo, secretos, voz, estatus social |
| **Personaje ficticio** | Personaje inventado, pero coherente con la Estructura social y la Mentalidad de su época. | — |
| **Personaje histórico ficcionalizado** | Personaje que representa a un Personaje histórico con pensamientos, diálogos o actos inventados. | referencia al Personaje histórico |
| **Personaje histórico de fondo** | Figura real que aparece o se menciona sin protagonismo. | — |
| **Arco de personaje** | Transformación del personaje a lo largo de la obra. | tipo (positivo, negativo, plano), estado inicial, estado final, hitos |
| **Relación** | Vínculo entre dos personajes que evoluciona con la trama. | tipo (familiar, afectiva, jerárquica, rival…), intensidad, evolución |

### 2.4 Discurso

| Concepto | Definición | Atributos principales |
|---|---|---|
| **Narrador / Punto de vista** | Quién cuenta y desde dónde. Determina qué información está disponible en cada escena. | persona, focalización, fiabilidad |
| **Tiempo narrativo** | Orden y ritmo del relato. Es distinto del tiempo histórico. | orden (cronológico, analepsis, prolepsis), elipsis, duración |
| **Escenario** | Instancia concreta de un Lugar en un momento dado, tal como se describe en la escena. | lugar, fecha, hora, clima, detalles sensoriales |
| **Diálogo** | Habla de los personajes. Equilibra la verosimilitud de época con la legibilidad actual. | hablantes, registro, subtexto |
| **Voz y estilo** | Rasgos de la prosa. | tono, sintaxis, densidad descriptiva, registro, arcaísmo permitido |
| **Motivo / Símbolo** | Elemento recurrente cargado de significado que refuerza el tema. | elemento, significado, apariciones |

---

## 3. Frontera historia–ficción

| Concepto | Definición | Atributos principales |
|---|---|---|
| **Anclaje histórico** | Vínculo explícito entre un elemento narrativo (escena, personaje, conflicto) y un Hecho o Evento. | elemento narrativo, hecho o evento, tipo de vínculo |
| **Licencia histórica** | Alteración consciente de un hecho por razones narrativas, como comprimir el tiempo, fusionar personajes o desplazar un lugar. | hecho original, alteración, justificación, declarada (sí/no) |
| **Anacronismo** | Elemento impropio del período. | tipo, clase, ubicación |
| **Anacronismo involuntario** | Error: algo que no podía existir, decirse o pensarse en la época. | — |
| **Anacronismo deliberado** | Licencia consciente, por ejemplo para acercar el lenguaje al lector actual. | — |
| **Clases de anacronismo** | Según qué elemento resulta impropio del período. | **material** (objetos), **léxico** (palabras), **conceptual** (ideas o conocimientos), **de mentalidad** (valores o juicios actuales) |
| **Plausibilidad** | Grado en que un elemento inventado podría haber ocurrido dado el contexto. Se aplica sobre todo en las zonas de silencio documental. | nivel, justificación |
| **Nota del autor** | Paratexto que declara qué es histórico, qué es ficción y qué licencias se tomaron. | licencias declaradas, fuentes principales |

---

## 4. Características de calidad

Las características se agrupan en cuatro familias.

### 4.1 Fidelidad histórica

| Característica | Definición | Cómo se verifica |
|---|---|---|
| **Rigor histórico** | Los hechos anclados coinciden con las fuentes. | Contraste de afirmaciones con la base de conocimiento; tasa de hechos no respaldados. |
| **Coherencia temporal** | Nada aparece antes de existir: objetos, ideas, palabras, personas vivas o muertas. | Validación de fechas por entidad; detector de anacronismos. |
| **Autenticidad de mentalidad** | Los personajes piensan como en su época y evitan el *presentismo* (proyectar valores actuales). | Revisión de motivaciones y juicios morales frente a la Mentalidad del período. |
| **Autenticidad lingüística** | Registro y léxico adecuados sin sacrificar la legibilidad. | Listas de términos anacrónicos; análisis de fórmulas de tratamiento. |

### 4.2 Calidad narrativa

| Característica | Definición | Cómo se verifica |
|---|---|---|
| **Calidad de trama** | Causalidad, tensión creciente, giros motivados y desenlace satisfactorio. | Comprobación de que cada escena cambia un estado; curva de tensión. |
| **Calidad de personaje** | Motivación clara, agencia, contradicciones y arco completo. | Seguimiento de objetivos y cambios por personaje. |
| **Ritmo** | Alternancia adecuada entre acción, reflexión, diálogo y descripción. | Proporciones por capítulo; longitud de escenas. |
| **Inmersión** | El lector "está" en la época gracias a detalle sensorial y cultura material integrada, no expositiva. | Densidad y distribución del detalle de época; ausencia de "infodumps". |

### 4.3 Calidad textual

| Característica | Definición | Cómo se verifica |
|---|---|---|
| **Calidad de prosa** | Voz consistente, variedad sintáctica y ausencia de clichés o repeticiones. | Métricas de repetición y clichés; consistencia de estilo. |
| **Coherencia interna (continuidad)** | Nombres, edades, heridas, relaciones, conocimiento y geografía se mantienen consistentes. | Comparación con el Estado de continuidad y la Biblia de la obra. |
| **Originalidad** | La obra no reproduce tramas ni textos existentes y aporta una mirada propia. | Detección de similitud; revisión de la premisa. |

### 4.4 Responsabilidad

| Característica | Definición | Cómo se verifica |
|---|---|---|
| **Sensibilidad y ética** | Representación responsable de grupos y conflictos, sin estereotipos gratuitos y con tratamiento cuidadoso de la violencia. | Revisión de sensibilidad por grupo representado. |
| **Transparencia** | Las licencias y ficcionalizaciones de personas reales quedan declaradas. | Registro de licencias completo; existencia de la Nota del autor. |

---

## 5. Proceso de generación

| Concepto | Definición | Atributos principales |
|---|---|---|
| **Especificación (brief)** | Petición de entrada que define la obra deseada. | período, lugar, género, extensión, tono, público, restricciones |
| **Restricción** | Regla que la generación debe respetar. | tipo (contenido, estilo, histórica), severidad |
| **Base de conocimiento histórico** | Repositorio estructurado de Hechos, Entidades y Fuentes del módulo 1. Es la "verdad" contra la que se valida. | hechos, entidades, fuentes, cobertura |
| **Biblia de la obra** | Documento vivo que actúa como canon de la novela. | personajes, relaciones, escenarios, reglas de estilo, glosario de época, licencias |
| **Plan (outline)** | Estructura jerárquica prevista de la obra. | actos, capítulos, escenas, anclajes previstos |
| **Estado de continuidad** | Memoria dinámica del mundo narrativo en cada punto de la obra. | ubicación de personajes, conocimiento de cada personaje, objetos, heridas, relaciones, fecha narrativa |
| **Borrador** | Texto generado de una unidad (escena o capítulo) en una versión concreta. | unidad, versión, texto, estado |
| **Evaluación** | Aplicación de las características de calidad a un borrador. | borrador, características evaluadas, puntuaciones |
| **Incidencia** | Defecto detectado en un borrador. | tipo, severidad, ubicación, característica afectada, propuesta de corrección |
| **Revisión** | Nueva versión de un borrador que resuelve incidencias. | incidencias resueltas, versión resultante |
| **Verificación de respaldo** | Comprobación de que la Cita guardada junto a cada Hecho sostiene su enunciado. La ejecuta un agente distinto del que reunió los Hechos, y un Hecho sin respaldo no se borra: pasa a Hecho inferido. | hechos revisados, veredicto por hecho |
| **Invención autorizada** | Dato que la obra necesita, que la investigación no encuentra y que se inventa con permiso explícito. Entra en la Base de conocimiento como Hecho inferido y sin Fuente, para que la Trazabilidad siga siendo completa. | enunciado, hueco que lo motivó |
| **Trazabilidad** | Enlace de cada afirmación histórica del texto con su Fuente o con su Licencia. | fragmento de texto, hecho, fuente o licencia |
