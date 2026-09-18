# StoryMaker

Generador de novelas históricas. Un autor aporta una chispa —un personaje, una
época, una idea, una imagen— y el arnés la convierte en una novela completa,
internamente coherente y libre de anacronismos, sin que el autor tenga que sostener
en la cabeza la continuidad de cien mil palabras.

El tiempo de ejecución es Claude Code: las etapas son subagentes. Debajo hay un
núcleo determinista en Python que es el único que escribe.

## La idea

Un modelo que ha consumido ochenta mil palabras de contexto y lleva tres iteraciones
discutiendo una escena no es un guardián fiable de una invariante. Y el problema no
es la obediencia: es que **una garantía cuyo cumplimiento no se puede comprobar
desde fuera no es una garantía, es una esperanza**.

De ahí la decisión que gobierna todo lo demás: el estado —Encargo, Contexto
histórico, Canon, Novela, presupuestos— lo escribe únicamente el núcleo, invocado
como herramienta. Los agentes leen lo que necesitan y **proponen**; el núcleo valida,
versiona, contabiliza y persiste.

No es una convención de estilo. Se impone con permisos del sistema de ficheros y con
hooks que deniegan antes de que la llamada exista.

## Instalación

```bash
pip install -e .          # el núcleo. Sin dependencias en tiempo de ejecución
pip install pytest        # sólo para las pruebas

# Sólo si vas a tocar la interfaz: abre la página en un navegador de verdad
# para comprobar que pinta. Es una herramienta de desarrollo, no del arnés.
pip install playwright && python -m playwright install chromium
```

Para el PDF de la entrega hace falta `pandoc` en el entorno. Si no está, se entrega
sólo Markdown y se declara.

Para ver la traza de las Ejecuciones hacen falta `LANGFUSE_PUBLIC_KEY`,
`LANGFUSE_SECRET_KEY` y `LANGFUSE_HOST` en el entorno o en un `.env` en la raíz. Sin
ellas todo funciona igual y la falta de traza se declara.

## Cómo se usa

Hay dos superficies sobre el mismo núcleo, y la Ejecución se conduce igual desde
cualquiera de las dos: **tres tramos y dos paradas**, en las que el Autor firma el
Contexto histórico y aprueba el Canon.

### La interfaz gráfica

```bash
python gui/servidor.py     # responde en http://127.0.0.1:8765
```

Compone el Encargo en un formulario, arranca la Ejecución, enseña qué subagente está
trabajando en cada momento y recoge las dos decisiones del Autor. Es la forma más
corta de recorrer una novela entera.

### La sesión de Claude Code

| Comando | Qué hace |
|---|---|
| `/encargo` | Abre la captura del Encargo, o ingiere un fichero JSON |
| `/ejecutar` | Arranca o reanuda una Ejecución |
| `/estado` | Etapa, unidad, hallazgos, consumo y proyección |
| `/control` | Puntos de control pendientes y su decisión |
| `/traza` | El origen de un pasaje, o el respaldo de una afirmación |
| `/entrega` | Markdown, PDF y paquete de trazabilidad |
| `/calibracion` | Consumo real frente a presupuestado |

### El núcleo, directamente

Todo comando devuelve el mismo sobre, con `ok`, comando, y datos o error. El código
de salida es 0 o 1 según `ok`.

```bash
storymaker proyecto crear --titulo "El cartógrafo"
storymaker --proyecto <prj> ejecucion estado
storymaker errores listar          # el catálogo completo de códigos
```

## Qué garantiza, y qué no

Garantiza, con comprobación en código y no con instrucciones en un prompt:

- No se redacta una sola escena sobre un Canon no aprobado.
- Ninguna Restricción de época cuelga de una afirmación descartada o refutada.
- Ningún capítulo rechazado se aprueba sin que su texto haya cambiado.
- La Novela conserva la mejor versión evaluada de cada escena, no la última.
- Ninguna Ejecución supera su presupuesto, y el tramo final de la reserva sólo lo
  libera el último tercio de la novela.
- Toda modificación del Canon genera versión, y las anteriores no se destruyen.
- Ninguna credencial aparece en un artefacto persistido.

**No garantiza que la prosa sea buena.** Las puntuaciones de rúbrica se calculan y se
persisten, pero sólo sirven para comparar una versión consigo misma: ningún mínimo
las convierte en puerta. Es una carencia conocida y declarada, no un olvido. Los
objetivos del arnés ponen la coherencia y la verosimilitud por delante de la calidad
de la prosa, y subordinan esta última explícitamente.

**Tampoco garantiza que el Contexto histórico sea cierto.** Lo comprobado por código
es la trazabilidad —de dónde sale cada Restricción— y no la veracidad de lo afirmado.
La verificación de fidelidad y la pasada de refutación se retiraron en la versión 1.7
porque costaban más de lo que corregían, y el único control sobre el contenido es que
el Autor lo lea y lo firme. Está declarado en §18.2 de la Funcional como lo que es:
una pérdida de garantía aceptada a cambio de que la Ejecución corra entera.

## Documentación

| Documento | Qué contiene |
|---|---|
| [`DEFENSA.md`](DEFENSA.md) | El recorrido completo de una novela: qué hace cada pieza, qué genera y dónde se guarda |
| [`docs/especificaciones_funcionales.md`](docs/especificaciones_funcionales.md) | El qué: requisitos, invariantes, puntos de control |
| [`docs/especificaciones_tecnicas.md`](docs/especificaciones_tecnicas.md) | El cómo: decisiones de arquitectura, contratos, errores |
| [`docs/especificaciones_mejoras.md`](docs/especificaciones_mejoras.md) | Sólo mejoras: qué optimizar, con la medida que lo justifica |
| [`ARQUITECTURA.md`](ARQUITECTURA.md) | Qué fichero del código implementa qué parte |
| [`CLAUDE.md`](CLAUDE.md) | Las reglas que siempre están en contexto |

Cuando el código y la especificación discrepen, gana la especificación: el código es
la implementación, no la decisión.

## Pruebas

```bash
python -m pytest tests/ -q
```

Cubre los cuatro niveles que no exigen modelos reales: unitario determinista,
contrato, recuperación ante cortes e integración sobre una novela mínima. Cada
invariante tiene su caso que pasa **y su caso que falla**: una invariante probada
sólo con datos válidos no ha demostrado que rechace nada.
