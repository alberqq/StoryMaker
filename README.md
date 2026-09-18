# StoryMaker

Arnés generador de novelas históricas. Dado un encargo —época, tema, personajes de partida, inspiración y
cuatro parámetros de longitud—, produce un manuscrito completo en Markdown y PDF, acompañado de un contexto
histórico verificado con sus fuentes, un canon congelado, una bitácora de todo lo ocurrido y un informe de
ejecución.

Es un prototipo académico. Está construido sobre Claude Code y **no contiene código**: el arnés son
instrucciones de agente, artefactos declarativos y contratos.

## Puesta en marcha

Requiere Claude Code con acceso a búsqueda web y, para la entrega en PDF, a una herramienta de conversión.
No hay instalación, ni build, ni dependencias: la unidad de despliegue es este directorio.

```
/proyecto-crear
```

Sin más. Te preguntará por un título provisional y luego irá recogiendo el Encargo **por bloques**: época
—acotada en tiempo y lugar—, tema, personajes de partida, inspiración y los cuatro parámetros de longitud.
Repregunta solo por lo que falte o no valga, y no rellena nada por su cuenta. Antes de congelar te enseña los
derivados y **dos cotas de invocaciones**, típica y peor caso, para que decidas con el número delante.

Si prefieres traerlo ya escrito, `/proyecto-crear --encargo <ruta.json>` aplica exactamente las mismas
validaciones: el mismo Encargo por ambos canales debe producir artefactos idénticos.

Con el Encargo congelado:

```
/etapa-lanzar PRY-20260918-la-sombra-del-gremio
```

Corre de principio a fin y solo se detiene si algo lo exige. Cuando se detenga, dirá por qué:

```
/control-atender PRY-20260918-la-sombra-del-gremio PCH-7 continuar_aceptando_con_observaciones
/etapa-lanzar PRY-20260918-la-sombra-del-gremio
/entrega-obtener PRY-20260918-la-sombra-del-gremio
```

Hay un encargo de ejemplo en [arnes/ejemplos/encargo-ejemplo.json](arnes/ejemplos/encargo-ejemplo.json):

```
/proyecto-crear --encargo arnes/ejemplos/encargo-ejemplo.json
```

## Qué hace, etapa por etapa

**Etapa 0 · El Encargo.** Se recogen época (acotada en tiempo **y** lugar), tema, personajes, inspiración y
los cuatro parámetros. Antes de arrancar se muestran los derivados —palabras por párrafo, extensión total— y
**dos cotas de invocaciones**, típica y peor caso, para que una configuración desproporcionada se vea antes de
gastar nada. El Encargo se congela y no se vuelve a tocar.

**Etapa 1 · El periodo histórico.** El Investigador planifica por las dimensiones declaradas —dieciséis, de
Tiempo y Espacio a Conflicto y disidencia—, busca en la web y produce afirmaciones atómicas.
Cada una arrastra su URL, su título, su dominio, su fecha de consulta y **un fragmento copiado literalmente**.
El Verificador de Investigación dictamina **solo sobre ese fragmento**: no reabre la fuente ni consulta su
propio conocimiento. Lo verificado se sella junto al **Inventario de Prohibidos**, la lista de lo que no
existía, que es lo que después permite cazar anacronismos.

**Etapa 2 · El canon.** Del Encargo y del Contexto sale el canon completo: personajes, trama, capítulos y
escenas, con el número exacto que fijan los parámetros. El Verificador de Canon lo juzga contra cuatro
criterios: conformidad histórica, coherencia interna, preparación de los giros y un catálogo **fijo** de 27
clichés. Una desviación sobre una figura real exige **Licencia Literaria declarada**. El canon se congela.

**Etapa 3 · La novela.** Dos bucles anidados. El **interior**: el Escritor redacta **un párrafo** por escena y
el Verificador de Lingüística lo juzga contra siete criterios de forma, incluido el encaje con el párrafo
anterior. El **exterior**: ensamblado el capítulo, el Verificador de Canon e Historia lo juzga contra el canon,
el contexto y lo ya narrado, con los tres capítulos previos íntegros delante. Al final, una **validación
global** busca las contradicciones entre capítulos distantes que nadie más puede ver.

## Las decisiones que lo explican

**El orquestador es amnésico.** No mantiene el bucle en una conversación: lee el estado, hace **una** unidad
de trabajo, escribe y termina. Una ejecución son entre 300 y 1.100 invocaciones encadenadas; ninguna
conversación sostiene eso, y una que lo intente no falla: **se degrada en silencio**, que es peor. Como
consecuencia, reanudar no es un modo especial: es lo que el arnés hace siempre.

**Nada se sobrescribe.** Cada intento es un fichero propio. La versión rechazada, sus hallazgos y la versión
corregida siguen ahí, y la diferencia entre dos intentos es la resta de dos ficheros de texto plano.

**Añadir un verificador no toca a ninguno de los existentes.** Todos hablan el mismo contrato de veredicto y
el orquestador consulta un registro en lugar de conocerlos. Un verificador nuevo es un fichero de instrucción
y una entrada en un JSON. Esa extensibilidad está deliberadamente por encima de la calidad literaria.

**Todo bucle termina.** Seis bucles, seis límites, y un comportamiento definido al agotarlos: la ejecución se
bloquea y espera al autor, que puede aceptar con observaciones, conceder intentos, aportar el texto o abortar.
Un solo párrafo irreductible detiene la ejecución en lugar de reintentarse para siempre.

## Lo que no promete

Sin código no hay recuentos exactos ni comparaciones literales. **Cero anacronismos, la longitud exacta y la
no reproducción de fuentes son controles declarados, no garantías**: el arnés promete que un verificador miró
con el inventario delante, no que no haya nada. Las palabras son estimación.

No es reproducible: no hay control de semilla y el campo se registra siempre vacío, precisamente para que
nadie suponga lo contrario. Es **auditable y comparable**, que es otra cosa: se puede saber exactamente en qué
difieren dos ejecuciones, no predecir qué producirá la siguiente.

Y las fuentes no se filtran. Se registra el dominio y se enseña en el informe.

## Estructura

| Directorio | Contenido |
|---|---|
| [docs/](docs/) | Las dos especificaciones. Mandan sobre cualquier otra cosa |
| [arnes/](arnes/) | La definición del arnés: registro, configuración, catálogos, 18 contratos y 9 instrucciones |
| [.claude/](.claude/) | Vínculos de los siete agentes y las ocho operaciones |
| `proyectos/` | Un directorio autocontenido y portátil por novela |
| `proyectos-prueba/` | Banco de pruebas. Nunca escribe en `proyectos/` |

Un Proyecto se lleva entero copiando su directorio: artefactos, bitácora y auditoría incluidos. Todo en texto
legible sin herramienta.
