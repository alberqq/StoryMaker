---
description: "artefacto.consultar - Muestra en solo lectura cualquier artefacto del Proyecto."
argument-hint: "<PRY-id> <artefacto> [segmento]"
---

# Operación `artefacto.consultar`

Argumentos: `$ARGUMENTS`. **Solo lectura**: no escribe estado ni bitácora.

| `artefacto` | Qué muestra |
|---|---|
| `encargo` | El Encargo congelado y sus derivados |
| `plan` | El plan de investigación por dimensiones |
| `afirmaciones` | Las afirmaciones; `segmento` filtra por dimensión o por estado |
| `contexto` | El Contexto Histórico sellado |
| `inventario` | El Inventario de Prohibidos |
| `canon` | El Canon congelado |
| `capitulo` | Un capítulo ensamblado; `segmento` es su número |
| `escena` | Una escena y **todos sus intentos**; `segmento` es `CAP-nn/ESC-nn` |
| `manuscrito` | El manuscrito completo |
| `resumen` | El resumen acumulado |
| `continuidad` | Las fichas de continuidad |
| `bitacora` | La bitácora; `segmento` es `e0`, `e1`, `e2` o `e3-cap-nn` |
| `estado` | El estado de ejecución |
| `informe` | El informe de ejecución |
| `archivo` | Lo archivado por repeticiones de etapa |

Artefacto ausente o corrupto → `ERR-502`: comunícalo, no lo reconstruyas por tu cuenta.

Al mostrar una **escena**, muestra sus intentos en orden con sus veredictos: la diferencia entre
`esc-02.i1.md` y `esc-02.i2.md` es la resta de dos ficheros de texto plano, y es lo que hace demostrable que
el histórico conserva la versión rechazada y la corregida.
