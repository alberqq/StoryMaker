---
description: Abre la captura conversacional del Encargo, o ingiere un fichero JSON con los mismos campos.
argument-hint: "[semilla | @fichero.json]"
allowed-tools: Task, Bash, Read, AskUserQuestion
---

Captura del Encargo (E1). Argumento recibido: `$ARGUMENTS`

Decide cual de los dos caminos aplica:

**Si el argumento empieza por `@`**, es un fichero de Encargo (RF-110). Ingierelo:

```
storymaker --proyecto <prj> encargo ingerir --datos @<fichero>
```

Un campo desconocido se rechaza nombrandolo; no lo ignores ni lo corrijas por tu
cuenta. Despues presenta el Encargo al Autor y **espera su confirmacion explicita**:
un fichero no confirma nada por si mismo.

**Si el argumento es texto libre o esta vacio**, es una semilla y arranca el
interrogatorio. Despacha el subagente `sm-entrada`, que lo conduce.

Si no existe todavia un Proyecto, crealo antes:

```
storymaker proyecto crear --titulo "<titulo provisional>" --modo asistido
```

Al terminar, muestra al Autor:

- El Encargo completo tal como quedo registrado.
- **Que campos quedaron marcados como sin preferencia**, y el recordatorio de que eso
  significa que no se evaluaran, no que tengan un valor por defecto.
- Las incompatibilidades detectadas y como se resolvieron.
- La extension por capitulo con su factor de conversion, si vino en lineas.
