"""spec: §3.2 · arq: §9, §16.3

Construye el `StateGraph` cableando los nodos que cada feature exporta.

**El grafo vive en `commons/` y los nodos en cada fase**, porque es justo lo que `commons/`
alberga: algo que todas las fases usan y ninguna posee. La dirección de las importaciones
queda así en su sitio —el grafo importa los nodos de cada fase, y ninguna fase importa de
otra—, y el estado compartido, como el contador de huecos de Plotting, tiene un dueño
declarado en lugar de acabar definido dentro de la fase que primero lo necesitó.

Los nodos se resuelven **por su ruta y en el momento de construir**, no con `import` arriba.
Eso permite construir el grafo, compararlo con el modelo y probarlo mientras las seis fases
se van escribiendo: un nodo que aún no existe se sustituye por uno que revienta si alguien
lo pisa, que es exactamente lo que debe pasar mientras el hito que lo trae no esté cerrado.
"""

from __future__ import annotations

import importlib
from collections.abc import Awaitable, Callable
from typing import Any

from storymaker.commons.graph.aristas import (
    tras_checkpoint,
    tras_espera,
    tras_extract,
    tras_judge,
    tras_plan,
    tras_validate,
)
from storymaker.commons.graph.estado import EstadoNovela
from storymaker.commons.graph.nodos import GATES, NODOS, TERMINALES

Nodo = Callable[[EstadoNovela], Awaitable[EstadoNovela]]


class NodoSinImplementar(NotImplementedError):
    """El hito que trae este nodo todavía no está cerrado.

    Es una excepción y no un nodo que devuelve el estado intacto, y la diferencia importa:
    un nodo que no hace nada y deja seguir produciría una novela con fases enteras saltadas
    y sin que nada se quejara.
    """


def resolver(ruta: str) -> Nodo | None:
    """Importa `modulo:simbolo`, o devuelve `None` si aún no existe."""
    modulo, _, simbolo = ruta.partition(":")
    try:
        cargado = importlib.import_module(modulo)
    except ModuleNotFoundError:
        return None
    funcion = getattr(cargado, simbolo, None)
    return funcion if callable(funcion) else None


def _pendiente(nombre: str, ruta: str) -> Nodo:
    async def nodo(_: EstadoNovela) -> EstadoNovela:
        raise NodoSinImplementar(
            f"El nodo {nombre} no esta implementado todavia: {ruta} no existe."
        )

    return nodo


def _bautizado(nodo: Nodo, gate: str) -> Nodo:
    """Fija el nombre del gate en el nodo que los cuatro comparten.

    Los cuatro `AwaitApproval` son el mismo código registrado con cuatro nombres, y el nodo
    necesita saber cuál de ellos está corriendo para decidir adónde lleva «aprobar». Se le
    dice aquí, al cablear, en lugar de dejar que lo deduzca del estado: es el único punto
    del sistema donde el nombre del nodo es un dato de verdad y no una inferencia.
    """

    async def envuelto(estado: EstadoNovela) -> EstadoNovela:
        return await nodo(estado, gate=gate)  # type: ignore[call-arg]

    return envuelto


def nodos_resueltos() -> dict[str, Nodo]:
    """Los veinticuatro nodos, con un sustituto ruidoso para los que faltan."""
    resueltos = {
        nombre: resolver(ruta) or _pendiente(nombre, ruta) for nombre, ruta in NODOS.items()
    }
    for gate in GATES:
        if resolver(NODOS[gate]) is not None:
            resueltos[gate] = _bautizado(resueltos[gate], gate)
    return resueltos


def nodos_pendientes() -> list[str]:
    """Qué nodos siguen sin implementación. Es el informe de avance del plan."""
    return sorted(nombre for nombre, ruta in NODOS.items() if resolver(ruta) is None)


def construir(checkpointer: Any = None) -> Any:
    """Cablea el grafo entero y lo compila.

    Las aristas condicionales leen **booleanos calculados en Python**: `Validate` va a
    `Repair` o a `Extract` según un `bool` que salió de contar incidencias en una lista,
    nunca según lo que diga un modelo. Eso es lo que TLC puede verificar, y lo que hace que
    ningún agente pueda saltarse una validación.
    """
    from langgraph.graph import END, StateGraph

    grafo: Any = StateGraph(EstadoNovela)
    for nombre, nodo in nodos_resueltos().items():
        grafo.add_node(nombre, nodo)

    grafo.set_entry_point("Configure")

    # Tramos sin decisión: una sola salida.
    for desde, hasta in (
        ("Configure", "AwaitApproval"),
        ("Research", "VerifyCorpus"),
        ("VerifyCorpus", "AwaitApproval2"),
        ("FillGap", "Plan"),
        ("SealCorpus", "WriteChapter"),
        ("WriteChapter", "Validate"),
        ("Repair", "Validate"),
        ("ApproveChapter", "Checkpoint"),
        ("PublishVersion", "Idle"),
        ("RequestChange", "Invalidate"),
        ("Invalidate", "RegenerateAffected"),
        ("RegenerateAffected", "Validate"),
    ):
        grafo.add_edge(desde, hasta)

    # Los cuatro gates terminan la invocación: `interrupt()` persiste y el proceso vuelve.
    # La decisión entra despues por `Command(resume=...)`, que es el mismo mecanismo con el
    # que se reanuda tras un fallo — un solo camino de código.
    grafo.add_conditional_edges("Plan", tras_plan, ["FillGap", "AwaitApproval3"])
    grafo.add_conditional_edges("Validate", tras_validate, ["Repair", "Extract", "Fail"])
    grafo.add_conditional_edges(
        "Extract", tras_extract, ["Repair", "ApproveChapter", "Fail"]
    )
    grafo.add_conditional_edges(
        "Checkpoint", tras_checkpoint, ["WriteChapter", "AwaitApproval4"]
    )
    grafo.add_conditional_edges("Judge", tras_judge, ["PublishVersion", "AwaitApproval4", "Fail"])

    # Los cuatro gates. En interactivo la invocación no llega aquí: `interrupt()` la corta
    # antes y el proceso vuelve. En modo batch el nodo resuelve por «aprobar» y la arista se
    # recorre igual que cualquier otra, que es lo que permite que los cinco briefs de
    # evaluación crucen el sistema desatendidos.
    for gate, destinos in (
        ("AwaitApproval", ["Research", "Configure", "Fail"]),
        ("AwaitApproval2", ["Plan", "Research"]),
        ("AwaitApproval3", ["SealCorpus", "Plan"]),
        ("AwaitApproval4", ["Judge", "WriteChapter"]),
    ):
        grafo.add_conditional_edges(gate, tras_espera, destinos)

    # `Idle` no es un final sino un reposo: de ahí salen la petición de cambio y la
    # ramificación, y las dos entran como **invocación nueva**, no como arista.
    for terminal in (*TERMINALES, "Idle"):
        grafo.add_edge(terminal, END)

    return grafo.compile(checkpointer=checkpointer)
