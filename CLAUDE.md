# StoryMaker — arnés generador de novelas históricas

Este repositorio **no contiene un programa**. Contiene un arnés (*harness*) hecho de instrucciones de agente,
artefactos declarativos y contratos. Esa es la restricción que más forma le da (RES-11): **ninguna decisión
del flujo la toma un programa**. Si alguna vez te ves escribiendo un script que orquesta etapas, valida
esquemas o cuenta intentos, has salido del diseño.

Las especificaciones mandan y están en [docs/](docs/): la funcional define el QUÉ, la técnica el CÓMO.

## Cómo se usa

| Operación | Comando |
|---|---|
| Crear un Proyecto | `/proyecto-crear` |
| Ver su estado | `/proyecto-abrir` |
| Completar y congelar el Encargo | `/encargo-cumplimentar` |
| **Ejecutar el arnés** | `/etapa-lanzar` |
| Resolver un punto de control | `/control-atender` |
| Repetir una etapa (archiva, no borra) | `/etapa-repetir` |
| Consultar un artefacto | `/artefacto-consultar` |
| Entregar | `/entrega-obtener` |

`/etapa-lanzar` sin etapa corre de corrido; con etapa, la ejecuta aislada. Es la misma operación.

## La arquitectura en un párrafo

Máquina de estados dirigida por artefactos con **orquestador amnésico**. En cada activación el orquestador
lee el estado y la bitácora, calcula **una sola** unidad de trabajo, ensambla su contexto contra un contrato
declarado, invoca al agente que el registro declara, valida la salida, escribe bitácora y estado, y termina.
El bucle no vive en la conversación: vive en el sistema de ficheros. Una ejecución completa encadena entre
300 y 1.100 invocaciones, y ninguna conversación sostiene eso.

## Las seis reglas que no se negocian

1. **Nada se sobrescribe.** Cada intento es un fichero nuevo con el intento en el nombre
   (`esc-02.i1.md`, `esc-02.i2.md`). La bitácora es de solo añadido: no existe operación de modificación ni de
   borrado.
2. **Lo sellado es inmutable.** Escribir sobre un Contexto sellado o un Canon congelado es `ERR-501`, error de
   sistema. La única vía de cambio es `/etapa-repetir`, que **archiva**.
3. **El orquestador no juzga; los verificadores no escriben.** El orquestador aplica políticas declaradas y
   los verificadores dictaminan. Un verificador que devuelve el texto corregido ve su reescritura descartada.
4. **El orquestador es el único escritor** del almacén. Ningún agente lee ni escribe ficheros del Proyecto:
   recibe su contexto en el prompt y devuelve su contenido. Sin esa frontera, la trazabilidad del contexto es
   indemostrable.
5. **Todo bucle tiene límite** y comportamiento definido al agotarlo. Son seis, y sus límites viven en
   `arnes/configuracion.json`, no en la cabeza de nadie.
6. **Las instrucciones se editan en su sitio.** No llevan version en el nombre: si se cambia una, se ha
   cambiado. El historico lo guarda el repositorio, y lo que identifica una ejecucion es la version del
   arnes (`registro-agentes.json`), anclada en `proyecto.json` al crear el Proyecto.

## Dónde está cada cosa

```
arnes/                        ← la definición del arnés, versionada aparte de los Proyectos
├── registro-agentes.json     ← quién atiende cada paso, con qué modo y qué versión. La pieza de OBJ-7
├── configuracion.json        ← límites, topes, tolerancias, presupuesto de contexto. UN solo lugar
├── etapas.json               ← orden de etapas y pasos. El orquestador no lo lleva escrito
├── dimensiones.json          ← las dimensiones de investigación, editables
├── cliches.json              ← catálogo FIJO CL-01..CL-27
├── severidades.json          ← tabla tipo de hallazgo → severidad
├── herramientas.json         ← las dos únicas herramientas de hoja
├── esquemas/                 ← 18 contratos en JSON Schema
└── agentes/                  ← L1 + las ocho instrucciones, una por agente

.claude/agents/               ← vínculos que hacen invocables a los siete agentes de dominio
.claude/commands/             ← las ocho operaciones declaradas
proyectos/                    ← un directorio autocontenido y portátil por novela
proyectos-prueba/             ← el banco de pruebas NUNCA escribe en proyectos/
```

## Ampliar el arnés

**Un verificador nuevo:** un fichero en `arnes/agentes/`, una entrada en `registro-agentes.json` y un vínculo
en `.claude/agents/`. **Cero modificaciones de agentes existentes.** Si tuviste que tocar uno, el diseño se
rompió.

**Una dimensión nueva:** un elemento en `dimensiones.json`. **Una etapa nueva:** una entrada en `etapas.json`.
Ninguna instrucción de agente enumera etapas ni dimensiones, y por eso esto funciona.

## Lo que este arnés NO promete

Conviene tenerlo presente al leer un informe, y debe constar en la memoria académica:

- **Cero anacronismos, longitud exacta y no reproducción de fuentes son controles declarados, no garantías.**
  Sin código no hay recuentos ni comparaciones literales: el arnés promete que un verificador buscó con el
  inventario delante, no que no haya nada. Las palabras son **estimación**; el número de párrafos de un
  capítulo es la única magnitud de longitud exacta, porque es contar ficheros.
- **No es reproducible**, es auditable y comparable. No hay control de semilla: el campo `semilla` es siempre
  `null`, y se registra precisamente para que nadie suponga lo contrario. Repetir una ejecución no da el
  mismo manuscrito.
- **La coherencia a distancia media está degradada por diseño.** Entre el capítulo n−4 y el n solo se compara
  lo que el resumen y las fichas de continuidad conservaron. Se admite ≤ 1 contradicción cada 10 capítulos.
- **Las fuentes no se filtran.** Se registra el dominio y aparece en el informe. Una fuente mala con un
  fragmento coherente produce una afirmación verificada falsa.

## Convenciones

- **Todo en español**, incluidos artefactos, motivos y hallazgos.
- **JSON** para lo que tiene contrato y se comprueba campo a campo; **Markdown** para la prosa que alguien va
  a leer.
- Identificadores estables: `PRY-…`, `AF-nnnn`, `LI-nnn`, `IP-nnn`, `PC-nnn`, `CL-nn`, `CAP-nn/ESC-nn`,
  `ERR-nnn`, `PCH-n`. **Un identificador eliminado no se reutiliza.**
- Ningún artefacto, instrucción ni entrada de bitácora contiene credenciales. Donde haga falta referenciar
  una, se escribe `TU_CLAVE_AQUI`.
