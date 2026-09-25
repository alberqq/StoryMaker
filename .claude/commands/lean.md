---
description: Compila el proyecto Lean de la cronología (lake build) y ejecuta lake exe verificar, interpretando el código de salida
argument-hint: "(sin argumentos)"
---

# /lean — el validador formal de la historia

Compila `formal/lean/` y ejecuta el verificador sobre el `Cronologia/Generado.lean` versionado, que es un ejemplo construido a mano y **viola tres invariantes a propósito** (I1, I2 e I4; ver `formal/lean/README.md`). El resultado esperado, por tanto, es un rechazo.

**Este comando no reinicia el servidor de la interfaz, no lanza ninguna novela y no edita ningún `.lean`.** Tampoco escribe sobre `Generado.lean`: el arnés trabaja siempre en una copia temporal del proyecto, y el ejemplo versionado sigue siendo el que es. Se rige por `AGENTS.md`.

## Pasos

1. **Localiza `lake`.** Prueba primero `lake --version`. Si no está en el PATH, en esta máquina suele estar en `~/.elan/bin`: usa esa ruta (`~/.elan/bin/lake`, o `lake.exe` en Windows) y **dilo en el resumen**, porque tiene una consecuencia: con `lake` fuera del PATH, el arnés no usa Lean y cae a la evaluación en Python de los mismos invariantes (`commons/formal/cronologia.py::lean_activo`). Si no aparece en ninguno de los dos sitios, para y dilo; no instales elan sin que el Autor lo pida.
2. **Compila** desde `formal/lean/`:

   ```bash
   cd formal/lean && lake build
   ```

   Un fallo de `lake build` es un fallo de compilación del modelo o del toolchain (`lean-toolchain` fija la versión), no un veredicto sobre la historia. Si falla, resume el primer error y para.
3. **Verifica** y captura el código de salida:

   ```bash
   lake exe verificar; echo "codigo de salida: $?"
   ```

4. **Interpreta el código, no la prosa.** El código de salida es el contrato con el arnés:
   - `0`: la cronología es coherente con los cuatro invariantes.
   - `1`: es incoherente; la salida lista los eventos culpables. Con el ejemplo del repositorio es lo esperado.
   - cualquier otro: fallo del ejecutable, no veredicto.

## El resumen

Una línea por invariante (I1 nadie antes de nacer, I2 nadie después de morir, I3 nadie en dos lugares a la vez, I4 ningún objeto antes de existir) con si cae o no y los eventos que cita. Si el resultado sobre el ejemplo no es el que describe `formal/lean/README.md`, señálalo al Autor como hallazgo.
