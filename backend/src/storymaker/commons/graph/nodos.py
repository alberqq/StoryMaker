"""spec: §3.2 · arq: §9, §16.3

La tabla de nodos: **un nombre por acción del modelo TLA+, y el mismo nombre**.

La correspondencia de §9 no es una narración, es una lista de identidades, y aquí está
escrita como dato. Una prueba compara este diccionario con los estados de
`formal/tla/harness.tla`: si alguien añade un nodo sin añadir su acción, o al revés, cae.

**La implementación se declara como ruta, no como `import`.** Es el mismo patrón que el
registro de validadores, y por el mismo motivo: el grafo vive en `commons/graph/` y los
nodos en cada feature, así que importarlos aquí arriba ataría el cableado a que las seis
fases existan. Con la ruta como cadena, el grafo se puede construir, comparar con el modelo
y probar mientras las fases se van escribiendo.

Los cuatro `AwaitApproval` comparten implementación y no nombre. Son cuatro estados
distintos en el modelo —el gate de Intake no es el de Writing— pero un solo nodo de
LangGraph parametrizado, porque lo que hacen es idéntico: `interrupt()`, fila en `gate`, y
la invocación termina.
"""

from __future__ import annotations

from typing import Final

from storymaker.commons.graph.estado import EstadoNovela

#: Nombre del nodo → ruta de su implementación. El orden es el del recorrido.
NODOS: Final[dict[str, str]] = {
    # Fase 1 · Intake
    "Configure": "storymaker.intake.nodos:configure",
    "AwaitApproval": "storymaker.gates.nodos:await_approval",
    # Fase 2 · Investigation
    "Research": "storymaker.investigation.nodos:research",
    "VerifyCorpus": "storymaker.investigation.nodos:verify",
    "AwaitApproval2": "storymaker.gates.nodos:await_approval",
    # Fase 3 · Plotting
    "Plan": "storymaker.plotting.nodos:plan",
    "FillGap": "storymaker.plotting.nodos:fill_gap",
    "AwaitApproval3": "storymaker.gates.nodos:await_approval",
    "SealCorpus": "storymaker.plotting.nodos:seal",
    # Fase 4 · Writing
    "WriteChapter": "storymaker.writing.nodos:write",
    "Validate": "storymaker.writing.nodos:validate",
    "Extract": "storymaker.writing.nodos:extract",
    "Repair": "storymaker.writing.nodos:repair",
    "ApproveChapter": "storymaker.writing.nodos:approve",
    "Checkpoint": "storymaker.writing.nodos:checkpoint",
    "AwaitApproval4": "storymaker.gates.nodos:await_approval",
    # Fase 5 · Publication
    "Judge": "storymaker.publication.nodos:judge",
    "PublishVersion": "storymaker.publication.nodos:publish",
    "Idle": "storymaker.commons.graph.nodos:idle",
    # Fase 6 · Regeneration
    "RequestChange": "storymaker.regeneration.nodos:request",
    "Invalidate": "storymaker.regeneration.nodos:invalidate",
    "RegenerateAffected": "storymaker.regeneration.nodos:regenerate",
    # Terminales
    "Branch": "storymaker.commons.graph.branch:fork",
    "Fail": "storymaker.commons.graph.nodos:fail",
}

#: Los dos estados de los que no sale ninguna arista. `Idle` no está aquí: una novela
#: publicada sigue viva y puede recibir una petición de cambio.
TERMINALES: Final = frozenset({"Branch", "Fail"})

#: Los cuatro gates, con la fase a la que pertenece cada uno. El nodo es el mismo; lo que
#: cambia es qué informe se le enseña al Autor.
GATES: Final[dict[str, str]] = {
    "AwaitApproval": "intake",
    "AwaitApproval2": "investigation",
    "AwaitApproval3": "plotting",
    "AwaitApproval4": "writing",
}

#: Cómo se llama cada fase fuera del código: en la interfaz y en los avisos.
NOMBRE_DE_FASE: Final[dict[str, str]] = {
    "intake": "Encargo",
    "investigation": "Investigación",
    "plotting": "Trama",
    "writing": "Escritura",
    "publication": "Publicación",
    "regeneration": "Regeneración",
}

#: La fase de cada nodo, con los valores del `CHECK` de `fase_run.fase`. Es lo que lee el
#: envoltorio de contabilidad para decidir cuándo empieza una `fase_run` nueva. Los cuatro
#: gates y los tres nodos de reposo o término no están: **heredan la fila abierta**. Un
#: gate con fila propia la abriría antes de `interrupt()`, y como LangGraph vuelve a
#: ejecutar el gate al reanudar, dejaría una fila vacía por cada reanudación.
FASE_DE_NODO: Final[dict[str, str]] = {
    "Configure": "intake",
    "Research": "investigation",
    "VerifyCorpus": "investigation",
    "Plan": "plotting",
    "FillGap": "plotting",
    "SealCorpus": "plotting",
    "WriteChapter": "writing",
    "Validate": "writing",
    "Extract": "writing",
    "Repair": "writing",
    "ApproveChapter": "writing",
    "Checkpoint": "writing",
    "Judge": "publication",
    "PublishVersion": "publication",
    "RequestChange": "regeneration",
    "Invalidate": "regeneration",
    "RegenerateAffected": "regeneration",
}


async def idle(estado: EstadoNovela) -> EstadoNovela:
    """La novela está publicada y en reposo.

    No es un final: de aquí salen la petición de cambio del lector y la ramificación. Que
    exista como nodo y no como ausencia de nodo es lo que permite que la Fase 6 sea una
    entrada más al mismo grafo en lugar de un programa aparte.
    """
    return estado


async def fail(estado: EstadoNovela) -> EstadoNovela:
    """Se agotaron los reintentos o el Autor abortó.

    Es **un estado declarado del grafo y no una excepción**, y la diferencia importa: una
    excepción se propaga hacia arriba y se pierde; un estado queda en el checkpoint, con
    todo lo que lo rodea, y se puede mirar meses después para saber qué pasó.
    """
    return estado
