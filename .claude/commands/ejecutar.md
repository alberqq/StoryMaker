---
description: Arranca una Ejecucion nueva o reanuda la que quedo a medias, sin rehacer trabajo valido.
argument-hint: "[--reanudar | --coste N --iteraciones N]"
allowed-tools: Task, Bash, Read
---

Arranque o reanudacion de una Ejecucion. Argumento recibido: `$ARGUMENTS`

## Primero, mira donde esta el Proyecto

```
storymaker --proyecto <prj> ejecucion estado
```

## Si hay una Ejecucion activa

Reanuda. **No arranques una nueva**: eso perderia el consumo ya gastado y volveria a
pagar trabajo que ya esta hecho.

```
storymaker --proyecto <prj> ejecucion reanudar
```

Reanudar lee el ultimo estado consistente y continua desde la siguiente unidad. Las
unidades ya cerradas no se rehacen: su clave de idempotencia esta en el ledger y el
nucleo devuelve su resultado sin gastar.

Antes de seguir, **comprueba si hay puntos de control pendientes**. Una Ejecucion
detenida en un punto de control no avanza hasta que el Autor decida, y no consume
presupuesto mientras espera. Si los hay, remite a `/control` y para.

## Si no hay Ejecucion activa

Arranca una, con sus presupuestos:

```
storymaker --proyecto <prj> ejecucion iniciar --coste <N> --iteraciones <N> --modo-ejecucion revision_del_autor
```

Los valores por defecto de los presupuestos son suposiciones sin base empirica y
deben recalibrarse tras la primera novela completa. El informe de calibracion que
emite `/calibracion` al cerrar es la unica via por la que dejaran de serlo.

## Despues, despacha la etapa que toque

**Hay dos etapas que no se despachan nunca, porque el juicio lo hace el Autor**: la
revision del Contexto historico y la del Canon. No busques un subagente para ellas.
La Ejecucion **se detiene** ahi y no sigue hasta que el Autor decide:

| Momento | Lo que hace el Autor |
|---|---|
| Contexto historico compuesto | Descarta lo que no da por bueno con `contexto descartar`, y firma con `contexto firmar --quien "<nombre>"` |
| Canon propuesto (PC-3) | Aprueba con `canon aprobar --modo-aprobacion humano --quien "<nombre>"` |

Segun la etapa en que este el Proyecto:

| Etapa | Subagente |
|---|---|
| `Encargo` | `sm-entrada` |
| `Investigacion` | `sm-investigacion` |
| `Diseno` | `sm-diseno`, que ademas escribe la **critica breve** del Canon que el Autor leera |
| `ValidacionCanon` | Ninguno. Es la parada en que el Autor aprueba |
| `Produccion` | `sm-redactor`, luego `sm-refinador` |
| `Produccion` (capitulo completo) | `sm-validador` |
| `PasadaGlobal` | `sm-global` |

Cada unidad pasa antes por la puerta de admision:

```
storymaker --proyecto <prj> unidad admitir --etapa <agente> --unidad <esc|cap> \
  --contenidos @manifiesto.json --coste-estimado <N>
```

Si la admision deniega, **no despaches**: aplica la politica de agotamiento del
bucle correspondiente y dilo. Gastar y descubrirlo despues no se puede deshacer.
