---
description: "etapa.lanzar - Ejecuta el arnes paso a paso. Sin etapa, corre de corrido desde donde toque; con etapa, la ejecuta aislada."
argument-hint: "<PRY-id> [etapa-1|etapa-2|etapa-3]"
---

# Operación `etapa.lanzar`

Argumentos: `$ARGUMENTS` — el primero es el `proyecto_id`; el segundo, opcional, la etapa.

**Sin etapa** es la ejecución continua: las tres etapas se encadenan sin intervención humana y el arnés solo
se detiene en un punto de control. **Con etapa** es la invocación aislada, para reanudar, reejecutar o probar.
**Es la misma operación**, y por eso no hay dos caminos que mantener.

---

## Actúas como Agente Orquestador

Lee **ahora**, antes de cualquier otra cosa:

1. `arnes/agentes/L1-sistema.md`
2. `arnes/agentes/orquestador.md` — tu instrucción completa. **Síguela al pie de la letra.**
3. `arnes/configuracion.json`, `arnes/etapas.json`, `arnes/registro-agentes.json`, `arnes/severidades.json`

Luego, del Proyecto: `proyectos/<PRY-id>/proyecto.json` y `proyectos/<PRY-id>/estado/estado-ejecucion.json`.

## El bucle

Repites este ciclo, **una unidad de trabajo por vuelta**, hasta que se cumpla una condición de parada:

1. **CMP-001** — calcula la única unidad siguiente desde el cursor del estado. Comprueba guardas de etapa,
   idempotencia y disponibilidad del agente en el registro.
2. **CMP-002 / CMP-033** — ensambla el contexto contra el contrato declarado del modo, rotulando cada bloque
   con `[[bloque: … | id: … | prioridad: Pn]]`. Reduce por prelación si desborda y anota las omisiones.
3. **Invoca al agente** que el registro declara, mediante la herramienta de subagentes, usando el vínculo
   `vinculo_claude_code` de su entrada. Le pasas L1 + L2 + L3 + L4 + L5 en el prompt. **El agente no lee
   ficheros del Proyecto: todo va en el prompt.**
4. **CMP-034** — valida la salida contra su esquema de `arnes/esquemas/`. Una sola reparación dirigida.
5. **CMP-003** — aplica la política de veredicto y decide la transición.
6. **CMP-004 / CMP-035** — escribe la entrada de bitácora con su bloque de traza.
7. **CMP-005** — escribe el estado, en el orden de cuatro pasos declarado.
8. Vuelve a 1.

## Condiciones de parada

Te detienes y lo comunicas cuando ocurra **cualquiera** de estas:

- Se abre un **punto de control**: escribes la solicitud, marcas `bloqueado: true` y terminas. La ejecución
  queda detenida indefinidamente hasta que el autor use `/control-atender`.
- Se alcanza el **estado de cierre** de la etapa pedida, si se pidió una etapa concreta.
- El Proyecto queda **Entregado**.
- Un **error no reintentable**: `ERR-201`, `ERR-202`, `ERR-402`, `ERR-404`, `ERR-501`, `ERR-502`, `ERR-503`,
  `ERR-602`, `ERR-903`.

## Qué informas al autor en cada vuelta

Una línea por unidad, para que el avance sea observable sin leer la bitácora:

```
[e3 · CAP-04/ESC-02 · intento 2] escritor → verificador-linguistica: Rechazado (1 Mayor: falta_encaje)
```

Al detenerte, di **por qué** te detuviste, en qué unidad, y cuál es el paso siguiente que el autor puede dar.

## Recordatorios que cuestan caro olvidar

- **Nunca cuentes intentos de memoria.** Viven en `estado-ejecucion.json`.
- **Nunca encadenes dos unidades sin escribir el estado entre ellas.** Si se corta la sesión, lo escrito
  sobrevive y lo no escrito se recalcula; lo que no se puede recuperar es lo que quedó solo en tu cabeza.
- **Nunca improvises un paso sin agente declarado.** `ERR-202` y te detienes.
- **Nunca escribas sobre un artefacto sellado.** `ERR-501`, error de sistema.
- **Nunca juzgues el contenido.** Si te sorprendes opinando sobre un párrafo, has salido de tu papel.
