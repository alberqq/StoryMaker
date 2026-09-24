# Plan — Contabilidad de la invocación: `fase_run` por fase y consumo contado

**Qué fija este documento.** La forma técnica exacta con la que se realiza [§9.1 y §9.2 de la spec de ejecución real](spec.md#9-contabilidad-de-la-invocación): qué ficheros cambian, qué funciones nacen y en qué orden se hace el trabajo. No decide nada que no esté decidido arriba. Si algo de aquí contradice a la spec o a [`architecture.md`](../../docs/architecture.md) —en particular §8, el grafo de `fase_run` inmutables—, gana la arquitectura y hay que parar a preguntar.

**Cómo se relaciona con el plan del backend.** Los dos ítems de este plan, **P-141** y **P-142**, se declaran en el [plan del backend](../backend/plan.md), que es donde vive la numeración `P-nn` y contra el que se trazan las matrices. Aquí se desarrollan. Los requisitos que realizan son REQ-ER-25, REQ-ER-26 y REQ-ER-36.

---

## 1. Punto de partida

Una novela real llega al gate de Plotting con **una sola** fila de `fase_run`: la que `invocar` abre para un `Arranque`, con `fase = 'intake'`. Nada la cierra si todo va bien, y ninguna otra fase abre la suya. De ahí salen los tres síntomas que la spec recoge:

- `storymaker estado` lee la fase de la última fila y dice «intake» durante toda la novela.
- El consumo que devuelve cada llamada al modelo solo llega a los *spans* del observador. Nadie lo suma a `tokens_in`, `tokens_out` ni `coste_usd` del estado, y `cerrar_fase_run` solo se llama en el `except`, así que la fila tampoco lo recibe.
- Todos los hechos del corpus llevan el `fase_run_id` de Intake. Rehacer Investigation escribiría hechos nuevos bajo el mismo identificador y los mezclaría con los anteriores.

---

## 2. Los dos ítems

| # | Entregable | Ficheros y símbolos |
|---|---|---|
| **P-141** | La `fase_run` de cada fase la abre un envoltorio puesto al cablear el grafo, que conoce la fase de cada nodo. La abre cuando la fase del nodo es otra o cuando la fila abierta ya no está `en_curso`, y cierra la anterior como `completada`. `invocar` cierra la fila abierta al salir, según cómo terminó. El estado lleva `corpus_run_id`, que fija el envoltorio al abrir Investigation, y los caminos que filtran el corpus por ejecución lo leen de ahí | `commons/graph/nodos.py::FASE_DE_NODO`, `commons/graph/contabilidad.py::contabilizado`, `commons/graph/contabilidad.py::corpus_de`, `commons/graph/construccion.py::nodos_resueltos`, `commons/graph/estado.py::EstadoNovela`, `commons/graph/run.py::invocar`, `commons/db/repos/arnes.py::fase_run_abierta`, `commons/db/repos/arnes.py::sumar_consumo`, `investigation/nodos.py`, `plotting/nodos.py` |
| **P-142** | El consumo lo cuenta un contador que envuelve al transporte. El envoltorio de P-141 toma la diferencia entre antes y después de cada nodo y la suma al estado y a la fila abierta | `commons/agents/contador.py::TransporteContado`, `commons/graph/dependencias.py::Dependencias`, `commons/graph/run.py::invocar` |

---

## 3. Forma técnica

### 3.1 La fase de cada nodo

`FASE_DE_NODO` vive en `commons/graph/nodos.py`, junto a `NODOS` y `GATES`, porque es la misma clase de dato: una tabla de identidades que se lee al cablear. Asigna a cada nodo una de las seis fases del `CHECK` de `fase_run.fase`. Los cuatro `AwaitApproval`, `Idle`, `Fail` y `Branch` no aparecen en ella: heredan la fase de la fila abierta.

Que los gates hereden no es comodidad. `Judge` puede devolver la novela a `AwaitApproval4`, que pertenece a Writing, y si el gate abriera fila propia lo haría **antes** de `interrupt()`. Como LangGraph vuelve a ejecutar el nodo del gate al reanudar, se abriría una segunda fila vacía en cada reanudación.

### 3.2 El envoltorio

`contabilizado(nombre, nodo)` devuelve un nodo con la misma firma. Lo aplica `nodos_resueltos` a todos los nodos, después de `_bautizado` en el caso de los gates. Hace cuatro cosas, en este orden:

1. **Decide si abre fila.** Solo si el nodo tiene fase. La fila abierta es **la última de la base**, que devuelve `arnes.fase_run_abierta(db)`, y no la que apunta el estado. Una novela solo admite una invocación a la vez, así que la última fila es siempre la de la invocación en curso. Además, la Fase 6 abre su fila desde la API, en `api/cambios.py`, antes de que corra ningún nodo, y el envoltorio la reutiliza en lugar de abrir otra. Abre una nueva cuando la fase es distinta o cuando el estado de la fila no es `en_curso`. Si la fila anterior seguía `en_curso` o `esperando_gate`, la cierra como `completada` con `cerrar_fase_run`, conservando el consumo que ya tuviera. La nueva lleva `input_run_id` apuntando a la anterior.
2. **Fija el corpus.** Si la fase nueva es `investigation`, `corpus_run_id` pasa a ser el identificador de la fila recién abierta. Si el estado no trae `corpus_run_id`, porque el checkpoint es anterior a este cambio, se toma el `fase_run_id` que el estado tenía antes de abrir la fila: en esas novelas todas las fases compartían una sola, y esa es la del corpus.
3. **Ejecuta el nodo** con el estado actualizado, midiendo el contador del transporte antes y después.
4. **Suma el consumo** al estado que devuelve el nodo y a la fila abierta, con `arnes.sumar_consumo`, y fuerza en la salida `fase_run_id` y `corpus_run_id`. Un nodo que devuelva un estado parcial no puede perderlos.

Si el nodo lanza una excepción —incluida la de `interrupt()` de un gate—, el envoltorio no la atrapa. La fila recién abierta ya está escrita en la base, y la cierra `invocar`.

`corpus_de(estado)` devuelve `estado.get("corpus_run_id") or estado["fase_run_id"]`. Es lo que usan los nodos que leen o escriben el corpus: `research` y `verify` en Investigation, y `fill_gap` y `seal` en Plotting. `research` y `verify` ya escriben con el identificador correcto, porque en su fase coinciden los dos, pero se cambian igualmente para que haya una sola regla.

### 3.3 El cierre al salir de la invocación

`invocar` deja de depender de la `fase_run_id` local, que valía 0 al reanudar. Tras `ainvoke`, cierra la última fila de la base, si sigue `en_curso`, con `arnes.cerrar_abierta(db, estado)` según el final:

- gate pendiente → `esperando_gate`
- `Idle` → `completada`
- `Fail` → `fallida`

En el `except` se cierra la misma fila como `fallida`. `cerrar_fase_run` sobrescribe el consumo, así que el cierre por estado usa una variante que **solo** toca `estado` y `fin`, y conserva lo que `sumar_consumo` fue acumulando.

El *trigger* `inmutable_fase_run_update` ya admite este cambio: protege `fase`, `input_run_id`, `prompt_*`, `modelo` e `inicio`, no el estado, el consumo ni el fin.

### 3.4 El contador del transporte

`TransporteContado` envuelve a cualquier `Transporte` y acumula en `self.consumo` el `Consumo` de cada respuesta de `pedir`. `invocar` lo pone alrededor de `piezas[0]` al montar `Dependencias`, de modo que lo recibe tanto el transporte del SDK como el agente falso de la suite. Los nodos no cambian: siguen llamando a `deps.transporte` como antes.

### 3.5 Lo que ya enseña bien `storymaker estado`

Nada cambia en `cli/comandos.py::estado` ni en `api/novelas.py::ficha`. Leen la fase de la última fila y la suma de las filas, y con este plan las dos cosas dicen la verdad.

---

## 4. Orden de trabajo

1. `FASE_DE_NODO` y su prueba: todo nodo de `NODOS` que no sea gate ni terminal tiene fase, y ninguna fase está fuera del `CHECK`.
2. `TransporteContado`, con prueba unitaria.
3. `arnes.fase_run_abierta`, `arnes.sumar_consumo` y `arnes.cerrar_abierta`.
4. `contabilidad.contabilizado` y `corpus_de`, y el cableado en `nodos_resueltos`. Desde aquí la suite ya abre una fila por fase.
5. `corpus_run_id` en `EstadoNovela` y `estado_inicial`, y los cuatro nodos del corpus pasan a `corpus_de`.
6. El cierre en `invocar`, en los dos caminos.
7. Prueba de integración con el agente falso: una novela interactiva deja una fila por fase, la del gate en `esperando_gate` y las anteriores `completada`, con tokens mayores que cero; rehacer Investigation desde su gate abre una fila nueva y el corpus sellado no mezcla hechos de la anterior.

---

## 5. Qué se rompe mientras tanto

- **Pruebas que cuentan filas de `fase_run`.** Las que esperan una sola fila por novela dejan de cumplirse en el paso 4. Se ajustan a una fila por fase, que es lo que la arquitectura siempre pidió.
- **Novelas a medias.** Una novela que ya estaba corriendo con el código anterior retoma con su checkpoint, sin `corpus_run_id` y con su única fila todavía `en_curso`. El paso 2 del envoltorio la cubre: la primera fase nueva cierra esa fila como `completada` y el corpus sigue siendo el suyo. **No hace falta migrar nada ni reiniciar ninguna ejecución.**
- **El modelo TLA+.** No cambia. `fase_run` no es una variable del modelo, y el envoltorio no añade ni quita aristas. La prueba de identidad nodo↔acción sigue comparando los mismos nombres.

---

## 6. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | Primera versión: P-141 y P-142, con el envoltorio común, el contador del transporte, `corpus_run_id` y el cierre al salir de la invocación | Realiza §9.1 y §9.2 de la spec de ejecución real (REQ-ER-25, REQ-ER-26 y REQ-ER-36) |
