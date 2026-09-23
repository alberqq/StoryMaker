"""spec: §4.7 · arq: §9, §10

Los cinco gates. El nodo llama a `interrupt()`, **el checkpointer persiste y la invocación
termina**.

Tres consecuencias encadenadas, y las tres importan: no hay un proceso vivo doce horas
esperando; reiniciar el servidor no mata nada porque el estado está en disco y no en
memoria; y **la reanudación por gate usa exactamente el mismo mecanismo que la reanudación
por fallo** — un solo camino de código.

Los cuatro estados de gate del modelo comparten esta implementación porque lo que hacen es
idéntico. Lo único que cambia es qué informe se le enseña al Autor, y eso lo decide la fase,
no el nodo.

**En modo batch los gates se desactivan enteros.** Es imprescindible y no un lujo: los cinco
briefs de evaluación tienen que correr desatendidos, y si cada uno pidiera cinco
aprobaciones la tabla de resultados no se terminaría nunca.
"""

from __future__ import annotations

from typing import Any

from storymaker.commons.db.repos import arnes
from storymaker.commons.graph.aristas import tras_gate
from storymaker.commons.graph.dependencias import actuales
from storymaker.commons.graph.estado import EstadoNovela
from storymaker.commons.graph.nodos import GATES
from storymaker.gates.decisiones import DECISIONES
from storymaker.gates.notifier import Aviso, construir


async def abrir(estado: EstadoNovela, *, titulo: str, informe: str) -> int:
    """Escribe el gate pendiente y notifica. Devuelve su identificador."""
    deps = actuales()
    gate_id = await arnes.abrir_gate(deps.db, estado["fase_run_id"])
    notifier = construir(deps.settings)
    await notifier.enviar(
        Aviso(
            titulo=titulo,
            cuerpo=informe,
            gate_id=gate_id,
            decisiones=tuple(d.value for d in DECISIONES),
        )
    )
    return gate_id


def nombre_del_gate(estado: EstadoNovela, gate: str = "") -> str:
    """Cuál de los cuatro gates se está ejecutando.

    Los cuatro comparten función, así que la función tiene que saber quién es. El nombre lo
    inyecta `construir` al cablear el grafo, y **no se deduce de `pc`**: `pc` lo escribe el
    nodo anterior, y no todos nombran a su sucesor —`Checkpoint` se nombra a sí mismo y es
    una arista condicional la que decide si lo siguiente es el gate de Writing—.
    """
    if gate in GATES:
        return gate
    actual = estado["pc"]
    return actual if actual in GATES else "AwaitApproval"


async def await_approval(estado: EstadoNovela, gate: str = "") -> EstadoNovela:
    """El nodo de los cuatro gates.

    En modo batch no interrumpe: resuelve por «aprobar» y la invocación sigue. En
    interactivo llama a `interrupt()`, y lo que ocurre después no es cosa de este nodo —
    el proceso termina y la decisión entra por `Command(resume=...)`.
    """
    gate = nombre_del_gate(estado, gate)

    if not estado["gates_enabled"]:
        return {
            **estado,
            "gate_id": None,
            "pc": tras_gate(estado, gate=gate, decision="aprobar"),
        }

    from langgraph.types import interrupt

    gate_id = estado.get("gate_id")
    decision: Any = interrupt(
        {
            "gate": gate,
            "fase": GATES.get(gate, "desconocida"),
            "capitulo": estado["capitulo"],
        }
    )
    elegida = str(decision) or "aprobar"
    return {
        **estado,
        "gate_id": gate_id,
        "hay_bloqueantes": elegida != "aprobar",
        "pc": tras_gate(estado, gate=gate, decision=elegida),
    }


async def aparcar(estado: EstadoNovela, gate_id: int) -> EstadoNovela:
    """El *timeout*: la ejecución se **aparca**, con estado propio.

    **No hay auto-aprobación**, porque eso convertiría un gate de calidad en un
    temporizador. Una ejecución aparcada sigue viva y esperando: lo único que ha pasado es
    que el arnés ha dejado de esperar despierto.
    """
    deps = actuales()
    await deps.db.execute(
        "UPDATE gate SET estado = 'aparcado' WHERE id = ?", (gate_id,)
    )
    await arnes.cerrar_fase_run(deps.db, estado["fase_run_id"], estado="aparcada")
    return {**estado, "gate_id": gate_id}
