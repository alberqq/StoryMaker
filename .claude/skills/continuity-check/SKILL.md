---
name: continuity-check
description: Valida un capitulo de StoryMaker editado a mano con el mismo Core Domain que usa el grafo. Usar cuando se edite un fichero de capitulo, antes de commitear o de regenerar el PDF.
---

# continuity-check

Corre sobre un capitulo los validadores deterministas del arnes: longitud, nombres
exactos del canon, anacronismos fechados, anclajes y terminos prohibidos.

**No es una segunda implementacion.** Ejecuta exactamente los mismos objetos que el grafo
ejecuta como nodos, importados de `storymaker.commons.validation`. Si esta skill y el
grafo dieran veredictos distintos sobre el mismo capitulo, el producto y el editor humano
dejarian de estar de acuerdo sobre que es valido — y hay una prueba de contrato que lo
comprueba capitulo a capitulo, incidencia a incidencia.

## Uso

```bash
cd backend && uv run python -m storymaker.commons.validation.cli_hook <capitulo.md>
```

El contexto —nombres del canon, terminos prohibidos, entidades fechadas, fecha narrativa y
rango de palabras— se lee de un `<capitulo>.contexto.json` al lado del fichero. Si no
existe, se validan solo las reglas que no lo necesitan.

## Que significa cada veredicto

- **BLOQUEA**: el capitulo no puede aprobarse asi. En produccion volveria al editor.
- **aviso**: no detiene nada; en produccion viajaria al encargo del capitulo siguiente.

Lo que esta skill **no** comprueba es lo que necesita la base de datos o un modelo: la
cobertura de personalizacion, la ejecucion de la escaleta y el arco, y los invariantes de
Lean sobre la cronologia acumulada.

## Los dos hooks que la acompanan

`.claude/settings.json` ejecuta estas mismas reglas sin que nadie las pida, solo sobre
ficheros de capitulo (Markdown con su `.contexto.json` al lado, o `capitulo*.md`):

- **Policy, antes de escribir** (`PreToolUse`, `cli_policy`): si el texto que un `Write`,
  `Edit` o `MultiEdit` introduce trae un termino prohibido, la edicion se deniega.
- **Validacion, despues de escribir** (`PostToolUse`, `cli_hook`): el capitulo entero pasa
  por los validadores; si algo bloquea, el informe vuelve al agente para que lo corrija.

Los dos reciben el evento de Claude Code por la entrada estandar. La skill, en cambio, pasa
la ruta como argumento.
