---
description: "proyecto.abrir - Muestra el estado de un Proyecto: etapas, puntos de control pendientes y derivados del Encargo."
argument-hint: "<PRY-id>"
---

# Operación `proyecto.abrir`

Argumento: `$ARGUMENTS` — el `proyecto_id`. Si se omite, lista los Proyectos de `proyectos/`.

Actúas como **Agente Orquestador**. Operación de **solo lectura**: no escribe estado ni bitácora.

Lee `proyecto.json`, `estado/estado-ejecucion.json`, `encargo.json` y `puntos-control/` y presenta:

1. **Identificación**: id, título, fechas, versiones del arnés, esquema, configuración y clichés.
2. **Estado de las tres etapas** y estado del Proyecto.
3. **Cursor**: en qué unidad e intento está.
4. **Puntos de control pendientes**, en el orden en que se generaron, con sus opciones.
5. **Derivados del Encargo**: palabras por párrafo y por capítulo, escenas totales, y las dos cotas de
   invocaciones frente al consumo real.
6. **Avance**: capítulos aprobados sobre planificados; afirmaciones verificadas por dimensión.

Si `estado-ejecucion.json` contradice a la bitácora, **prevalece la bitácora** (`ERR-504`): dilo y ofrece
reconstruir el estado recorriéndola. Si falta o está corrupto un artefacto, `ERR-502`: comunícalo en lugar de
continuar sobre estado inconsistente.
