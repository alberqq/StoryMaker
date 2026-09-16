# StoryMaker

Generador de novelas históricas. Un autor aporta una chispa —un personaje, una
época, una idea, una imagen— y el arnés la convierte en una novela completa,
internamente coherente y libre de anacronismos, sin que el autor tenga que sostener
en la cabeza la continuidad de cien mil palabras.

El tiempo de ejecución es Claude Code: las ocho etapas son subagentes. Debajo hay un
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
```

Para el PDF de la entrega hace falta `pandoc` en el entorno. Si no está, se entrega
sólo Markdown y se declara.

## Uso

En una sesión de Claude Code sobre este repositorio:

| Comando | Qué hace |
|---|---|
| `/encargo` | Abre la captura del Encargo, o ingiere un fichero JSON |
| `/ejecutar` | Arranca o reanuda una Ejecución |
| `/estado` | Etapa, unidad, hallazgos, consumo y proyección |
| `/control` | Puntos de control pendientes y su decisión |
| `/piloto` | La escena piloto, con su ficha y los parámetros aplicados |
| `/traza` | El origen de un pasaje, o el respaldo de una afirmación |
| `/entrega` | Markdown, PDF y paquete de trazabilidad |
| `/calibracion` | Consumo real frente a presupuestado |

El núcleo también se usa directamente. Todo comando devuelve el mismo sobre, con
`ok`, comando, y datos o error:

```bash
storymaker proyecto crear --titulo "El cartógrafo"
storymaker --proyecto <prj> ejecucion estado
storymaker errores listar          # el catálogo completo de códigos
```

## Qué garantiza, y qué no

Garantiza, con comprobación en código y no con instrucciones en un prompt:

- No se redacta una sola escena sobre un Canon no aprobado.
- Nada se produce en serie antes de que el Autor acepte la escena piloto.
- Ninguna Restricción de época deriva de una afirmación que su fuente no sostiene o
  que la refutación ha desmentido.
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

## Documentación

| Documento | Qué contiene |
|---|---|
| [`especificaciones_funcionales.md`](especificaciones_funcionales.md) | El qué: requisitos, invariantes, puntos de control |
| [`especificaciones_tecnicas.md`](especificaciones_tecnicas.md) | El cómo: decisiones de arquitectura, contratos, errores |
| [`ARQUITECTURA.md`](ARQUITECTURA.md) | Qué fichero del código implementa qué parte |
| [`CLAUDE.md`](CLAUDE.md) | Las reglas que siempre están en contexto |

## Pruebas

```bash
python -m pytest tests/ -q
```

Cubre los cuatro niveles que no exigen modelos reales: unitario determinista,
contrato, recuperación ante cortes e integración sobre una novela mínima. Cada
invariante tiene su caso que pasa **y su caso que falla**: una invariante probada
sólo con datos válidos no ha demostrado que rechace nada.
