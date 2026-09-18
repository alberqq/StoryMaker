---
description: "proyecto.crear - Crea un Proyecto nuevo, por dialogo o desde un fichero de Encargo."
argument-hint: "[titulo] [--encargo <ruta.json>]"
---

# Operación `proyecto.crear`

Argumentos: `$ARGUMENTS`. Actúas como **Agente Orquestador**: lee `arnes/agentes/orquestador.md`.

**Sin `--encargo`, el Proyecto arranca por diálogo**, que es el canal por defecto. El fichero es la
alternativa, no al revés.

0. Si no se ha dado título, **pregunta por un título provisional** antes de nada: hace falta para el
   identificador y para el directorio. Puede cambiar de idea después; es `titulo_provisional` y no ata nada.
1. Genera el identificador `PRY-<aaaammdd>-<slug>`, con el slug derivado del título. Es estable y **nunca se
   reutiliza**.
2. Crea `proyectos/<PRY-id>/` con esta disposición:
   `proyecto.json`, `estado/`, `bitacora/`, `etapa-1/afirmaciones/`, `etapa-2/`,
   `etapa-3/capitulos/`, `puntos-control/`, `archivo/`, `entrega/`.
3. Escribe `proyecto.json` conforme a `arnes/esquemas/proyecto.schema.json`, anotando la **versión del arnés,
   del esquema, de la configuración y del catálogo de clichés** con que corre. El Proyecto queda anclado a
   ellas de por vida: si el arnés avanza, este Proyecto sigue con las suyas (ADR-015).
4. Inicializa `estado/estado-ejecucion.json` conforme a su esquema, con el cursor en la unidad `encargo`,
   contadores a cero, `bloqueado: false`.
5. Inicializa `bitacora/indice.json` y `bitacora/e0.jsonl` con la primera entrada, `tipo_evento: "transicion"`,
   `secuencia: 1`.
6. **Continúa inmediatamente con `encargo.cumplimentar`**, sin pedir otro comando: por fichero si se pasó
   `--encargo`, y **por diálogo si no**. Lee `.claude/commands/encargo-cumplimentar.md` y sigue su guion de
   cinco bloques. El Proyecto recién creado sin Encargo no sirve para nada, así que no te detengas aquí.

Errores posibles: `ERR-101`, `ERR-102`, `ERR-103`.
