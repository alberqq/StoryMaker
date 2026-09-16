# StoryMaker

Arnés generador de novelas históricas. El tiempo de ejecución es Claude Code: las
etapas son subagentes, y debajo hay un núcleo determinista en Python que es el único
que escribe.

## La regla que gobierna todo lo demás

**El estado autoritativo lo escribe únicamente el núcleo `storymaker`, invocado como
herramienta.** Ningún agente escribe estado por su cuenta.

No es una convención de estilo. Se impone con tres mecanismos concéntricos, y ninguno
depende de que un agente colabore:

1. **Permisos.** `settings.json` deniega toda escritura bajo `proyectos/**`, con la
   única excepción de `proyectos/<prj>/tmp/`.
2. **Hooks `PreToolUse`.** Deniegan antes de que la llamada exista, con un motivo.
3. **El núcleo**, que vuelve a comprobar las invariantes antes de persistir.

La redundancia es deliberada: los dos primeros protegen de un agente descaminado, el
tercero protege de un error en los dos primeros.

Si necesitas escribir algo, **propónlo al núcleo**. Si el núcleo lo rechaza, no
busques otra vía: el rechazo es la respuesta.

## Qué es autoritativo y qué no

| Artefacto | Autoritativo | Dónde vive |
|---|---|---|
| Encargo, Contexto, Canon, Novela, ledger | **Sí** | `proyectos/<prj>/` |
| Borradores y notas de un agente | No | `proyectos/<prj>/tmp/<udt>/`, se borra al cerrar |
| Índices derivados | No | `proyectos/<prj>/indices/`, se reconstruyen |
| Sinopsis de un capítulo cerrado | Sí, y **congelada** | `novela/sinopsis/<cap>.md` |

Los índices sirven para consultar, **nunca para decidir**. Un índice puede estar
obsoleto; una decisión no puede apoyarse en algo que puede estarlo. En particular, el
estado de los hilos se recalcula en el momento de decidir la terminación, no se lee
de `idx_hilos_estado`.

## Lo que no se hace nunca

- **No se redacta sobre un Canon no aprobado.**
- **No se produce en serie antes de que el Autor acepte la escena piloto.**
- **No se reescribe un pasaje protegido sin justificación registrada.** Cada uno
  resolvió un hallazgo bloqueante, y reescribirlo lo trae de vuelta.
- **No se rellenan las lagunas con verosimilitud.** Se declaran.
- **No se inventa un dato histórico.** Se solicita investigación.
- **No se resuelve una contradicción del Encargo en silencio.** Se eleva al Autor.
- **No se aprueba un capítulo rechazado cuyo texto no ha cambiado.**
- **Ninguna credencial aparece en un artefacto persistido.** Se resuelven del entorno
  y se referencian por marcador.

## El vocabulario es del Autor, y es fijo

Encargo, Semilla, Contexto histórico, Restricción de época, Canon, Hilo de trama,
Plan de revelaciones, Guía de estilo, Escena, Capítulo, Novela, Hallazgo, Severidad,
Causa raíz, Anacronismo, Licencia literaria, Licencia de alcance, Escena piloto,
Pasaje protegido, Presupuesto, Punto de control, Deuda de calidad.

Úsalos tal cual, también al hablar con el Autor. No los traduzcas a *issue*,
*pipeline*, *briefing* ni *worldbuilding*.

## A quién se pregunta

Al **Autor**, a través de un punto de control. Nunca se decide por él:

| Qué | Punto |
|---|---|
| Contenido y cierre del Encargo | PC-1, PC-2 |
| Aprobación del Canon | PC-3 |
| Replanificación durante la producción | PC-4 |
| Bloqueo irresoluble | PC-5 |
| Agotamiento con bloqueantes abiertos | PC-6 |
| La escena piloto | PC-8 |

Una Ejecución detenida en un punto de control **no consume presupuesto** mientras
espera.

## El núcleo

```
storymaker --proyecto <prj> <grupo> <accion> [opciones]
```

Todo comando devuelve el mismo sobre: `ok`, comando, y datos o error. El código de
salida es 0 o 1 según `ok`. `storymaker errores listar` da el catálogo completo de
códigos con su acción prescrita.

Los grupos son `proyecto`, `encargo`, `contexto`, `canon`, `escena`, `sinopsis`,
`hallazgo`, `capitulo`, `novela`, `entrega`, `ejecucion`, `etapa`, `unidad`,
`control`, `traza`, `indices`, `informe`, `contratos` y `errores`.

## Documentos de referencia

- `especificaciones_funcionales.md` — el qué. Requisitos RF, RNF, invariantes INV,
  puntos de control PC.
- `especificaciones_tecnicas.md` — el cómo. Decisiones ADR, contratos CT, taxonomía
  de errores ERR.
- `ARQUITECTURA.md` — mapa de qué fichero del código implementa qué parte.

Cuando el código y la especificación discrepen, **gana la especificación**: el código
es la implementación, no la decisión.
