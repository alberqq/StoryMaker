---
description: Lanza storymaker evaluar sobre ejemplos/evals (ejecuciones reales y de pago), previa confirmación explícita del Autor
argument-hint: "[directorio de briefs]  (vacío: ../ejemplos/evals)"
---

# /evaluar — los briefs de evaluación en modo batch

Corre `storymaker evaluar`, que genera en modo batch, con los gates apagados, una novela por cada brief de un directorio (`eval-<brief>` en `backend/proyectos/`). Es lo que alimenta la tabla brief × validador.

> **Aviso: lanza ejecuciones reales, con llamadas al modelo y a internet, que cuestan dinero y tardan.** Una novela de dos capítulos costó 1,72 $ (`docs/iteraciones.md`, It-39); siete briefs de diez capítulos cuestan bastante más.

**Este comando no reinicia el servidor de la interfaz** y se rige por `AGENTS.md`: una ejecución real solo se lanza cuando el Autor la pide.

Argumento recibido: `$ARGUMENTS`. Vacío, el directorio es `../ejemplos/evals` (relativo a `backend/`).

## Pasos

1. **Lista los briefs** del directorio (`*.yaml` y `*.json`) y cuántos son. Hoy `ejemplos/evals/` tiene siete, del `01-jubilacion` al `07-adversarial-temporal`.
2. **Comprueba qué existe ya**: si hay carpetas `backend/proyectos/eval-*`, dilo, porque `evaluar` reutiliza la novela si su carpeta existe en lugar de empezar de cero.
3. **Comprueba si Lean va a ser Lean**: si `lake` no está en el PATH (en esta máquina suele estar solo en `~/.elan/bin`), la cronología se verificará en Python y un fallo del brief 07 no contará como caso real de Lean. Dilo.
4. **Pide confirmación explícita** al Autor, con el número de briefs y el aviso de coste. Sin un «sí» expreso, para aquí.
5. **Lanza con la ruta explícita.** El valor por defecto de `--briefs` apunta a `evals/briefs`, que ya no existe, así que la opción se pasa siempre:

   ```bash
   cd backend && uv run storymaker evaluar --briefs ../ejemplos/evals
   ```

   Es largo: lánzalo en segundo plano y sigue su avance con `/estado-novelas`, sin reiniciar nada.
6. **Resume al terminar**: por brief, la novela creada, si publicó o en qué fase y con qué error se detuvo, y el coste de `storymaker estado eval-<brief>`. La tabla brief × validador sale de la tabla `score` de cada `eval-*.db`; si se construye, se hace aparte, no dentro de este comando.
