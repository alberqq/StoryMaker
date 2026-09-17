---
description: Devuelve el origen completo de un pasaje o el respaldo documental de una afirmacion historica.
argument-hint: "<esv_xxx | texto de la afirmacion>"
allowed-tools: Bash, Read
---

Trazabilidad (RF-081, RF-082). Argumento recibido: `$ARGUMENTS`

**Si el argumento empieza por `esv_`**, es una version de escena. Devuelve su cadena
de origen:

```
storymaker --proyecto <prj> traza pasaje --version-escena $ARGUMENTS
```

Presenta: la escena planificada de la que procede, la version de Canon bajo la que se
redacto, la Ejecucion y la iteracion que lo produjeron, y **los hallazgos que lo
modificaron**. Si la cadena esta incompleta, dilo: RNF-007 exige que este completa
en el cien por cien de los pasajes, y un hueco es un defecto, no una rareza.

**En cualquier otro caso**, es una afirmacion historica. Puede ser su identificador o
un fragmento del texto, que es lo que tiene delante quien revisa una novela:

```
storymaker --proyecto <prj> traza afirmacion --consulta "$ARGUMENTS"
```

Presenta: la afirmacion del Contexto que la sostiene, su estado --- vigente o
descartada ---, las Restricciones que derivan de ella, y sus fuentes **con el
contenido conservado**.

El contenido conservado es lo que hace que esto siga funcionando meses despues: un
localizador puede haber muerto, y la trazabilidad no puede depender de que una
pagina siga en pie.

Si no hay respaldo, **dilo claramente**: una afirmacion historica sin respaldo en el
Contexto y sin Licencia literaria registrada incumple INV-3, y eso es un hallazgo
bloqueante, no una curiosidad.
