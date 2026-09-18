---
description: "entrega.obtener - Ensambla el manuscrito, genera el informe de ejecucion y entrega en Markdown y PDF."
argument-hint: "<PRY-id> [--parcial]"
---

# Operación `entrega.obtener`

Argumentos: `$ARGUMENTS`. Actúas como **Agente Orquestador** (CMP-030, CMP-031, CMP-032).

## Precondición

Todos los capítulos `Aprobado` o `Aceptado_con_observaciones`, **y** la validación global sin hallazgos
Bloqueantes abiertos sin decisión expresa del autor. Si no se cumple → `ERR-601`.

Con `--parcial` se entrega igualmente, **marcado explícitamente como parcial** y sin estado de Manuscrito
Completo.

## Pasos

1. **CMP-030** — ensambla `entrega/manuscrito.md` desde las escenas aprobadas, en orden. Es un derivado
   regenerable. Estructura: título; por capítulo, encabezado de nivel 2 con su orden y título; **cada escena,
   un párrafo**. **Sin metadatos incrustados**: los pasajes del autor y los hallazgos abiertos van al informe,
   no al manuscrito.
2. **CMP-032** — convierte a `entrega/manuscrito.pdf` **a partir del Markdown**, nunca de otra fuente, con
   contenido idéntico. Es una herramienta de hoja: **transforma, no decide**.

   ```
   python arnes/herramientas/md-a-pdf.py <ruta>/entrega/manuscrito.md <ruta>/entrega/manuscrito.pdf
   ```

   Devuelve una línea JSON en `stdout` con `resultado`, `paginas`, `parrafos` y `bytes`: regístrala tal cual
   en la bitácora, sin reinterpretarla. Código de salida 0 si convirtió, 1 si falló.

   Si falla —código 1, o `fpdf2` no instalado— → `ERR-405`: la entrega en Markdown **se considera completa**
   y el fallo se registra. El manuscrito ya está terminado; el PDF es una presentación de lo mismo.
3. **CMP-031** — escribe `entrega/informe-ejecucion.md` con sus **trece bloques**, recorriendo la bitácora
   entera. Es la única consulta que paga un recorrido total, y solo se paga una vez.

El informe y la bitácora **no se exportan a PDF**: son material de auditoría, no de lectura.

## El bloque 13 no se suaviza

Anomalías: ejecución **sin ningún rechazo**, veredictos malformados, tipos de hallazgo no previstos, campos
ignorados del Encargo, discrepancias entre estado y bitácora.

Una ejecución en la que nada se rechazó **se destaca como anomalía a revisar**, porque un control de calidad
que nunca rechaza no está demostrado. No la presentes como un éxito.

Al terminar: `estado_proyecto: "Entregado"` y las rutas de los tres ficheros.
