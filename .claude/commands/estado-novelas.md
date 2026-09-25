---
description: Resume el estado de las novelas (fase, gate, capítulos, coste, versiones) sin lanzar ni reanudar nada
argument-hint: "[nombre-de-novela]  (vacío: todas)"
---

# /estado-novelas — qué está pasando, sin tocar nada

Resume el estado de las novelas de `backend/proyectos/`. **Solo lee.** Este comando no lanza, reanuda, decide ni reintenta ninguna Ejecución, **no reinicia el servidor de la interfaz** y no escribe en ninguna base. Se rige por `AGENTS.md`, Operación.

Argumento recibido: `$ARGUMENTS`. Si trae un nombre, se resume esa novela; vacío, todas.

## Pasos

1. **Pregunta primero a la interfaz**, si está levantada:

   ```bash
   curl -s -m 5 http://127.0.0.1:8765/api/novelas
   ```

   Devuelve una tarjeta por carpeta de `proyectos/`, con `nombre`, `titulo`, `fase`, `estado`, `gate`, `capitulos_aprobados`, `capitulos_total`, `coste_usd`, `versiones` y `actualizada`. Para una sola novela, `curl -s -m 5 http://127.0.0.1:8765/api/novelas/<nombre>/panel` añade fases, capítulos, actividad, incidencias recientes, consumo y proceso.
2. **Si el servidor no responde, no lo levantes.** Usa la CLI, que lee la base directamente:

   ```bash
   cd backend && uv run storymaker estado <nombre>
   ```

   Da fase, gate abierto, capítulos aprobados y consumo acumulado (coste y tokens). Sin nombre, lista antes las carpetas de `backend/proyectos/` y pásalas una a una.
3. **Resume en una tabla**: novela, fase, estado, gate abierto, capítulos aprobados / total, versiones publicadas y coste en dólares. Debajo, en prosa breve, lo que pide atención: novelas `esperando_autor` (con el gate en que esperan), `fallida` o `detenida`, y las que están `en_marcha` o `arrancando`.

## Lo que no se hace

Si alguna novela está `en_marcha`, `arrancando` o `esperando_autor`, **dilo expresamente**: con Ejecuciones vivas no se reinicia el servidor. Proponer una decisión de gate está bien; tomarla, no, porque es del Autor.
