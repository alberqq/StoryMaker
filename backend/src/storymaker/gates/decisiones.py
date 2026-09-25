"""spec: §4.7 · arq: §10

Las cuatro decisiones del Autor, y qué hace cada una.

«Rehacer» a secas hace que el agente vuelva a tirar el dado; **el comentario es lo que
convierte el reintento en dirigido**. Por eso el texto libre se inyecta como bloque extra en
el prompt de esa fase, y por eso cuenta contra el límite de reintentos: un reintento
dirigido sigue siendo un reintento.

Todo comentario y toda edición se guardan como fila, se versionan y van al audit log y a
Langfuse. **La intervención del Autor queda trazada igual que la de un agente**, que es lo
que hace de la revisión humana algo auditable en lugar de un recuerdo.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import aiosqlite

from storymaker.commons.db.repos import arnes
from storymaker.commons.errores import ErrorDeStoryMaker
from storymaker.commons.obs.scores import registrar_decision_de_gate
from storymaker.commons.obs.trazas import Observador


class Decision(StrEnum):
    APROBAR = "aprobar"
    REHACER = "rehacer"
    EDITAR = "editar"
    ABORTAR = "abortar"


#: Las cuatro, en el orden en que las enseñan el aviso y la CLI.
DECISIONES = (Decision.APROBAR, Decision.REHACER, Decision.EDITAR, Decision.ABORTAR)


class DecisionInvalida(ErrorDeStoryMaker):
    """Una decisión que no se puede aplicar. No reanuda nada."""


@dataclass(frozen=True)
class DecisionTomada:
    gate_id: int
    decision: Decision
    comentario: str | None = None
    actor: str = "autor"
    #: La fase del gate decidido. La de Regeneración no reanuda: entra en la Fase 6.
    fase: str | None = None

    @property
    def cuenta_como_reintento(self) -> bool:
        """Rehacer y editar consumen intento; aprobar y abortar, no."""
        return self.decision in (Decision.REHACER, Decision.EDITAR)

    def bloque_para_el_prompt(self) -> str:
        """Lo que se inyecta en el prompt de la fase que se rehace.

        Va con su encabezado y en segunda persona porque va a un agente, no a un log: el
        comentario del Autor es una instrucción, y llega como tal.
        """
        if not self.comentario:
            return ""
        return (
            "\n\nEl Autor ha revisado tu entrega anterior y pide que la rehagas con esta "
            f"indicacion:\n{self.comentario}\n"
        )


async def registrar(
    db: aiosqlite.Connection,
    observador: Observador,
    tomada: DecisionTomada,
) -> None:
    """Escribe la decisión en `gate`, en el audit log y en la traza.

    En los tres sitios y no en uno: la fila de `gate` es lo que el grafo lee para reanudar,
    el audit log es lo que permite reconstruir quién decidió qué meses después, y la traza
    es lo que hace que la intervención humana aparezca al lado de la de los agentes.
    """
    await arnes.decidir_gate(
        db,
        tomada.gate_id,
        decision=tomada.decision.value,
        comentario=tomada.comentario,
        decidido_por=tomada.actor,
    )
    await registrar_decision_de_gate(
        db,
        observador,
        gate_id=tomada.gate_id,
        decision=tomada.decision.value,
        actor=tomada.actor,
        comentario=tomada.comentario,
    )


async def _fase_del_gate(db: aiosqlite.Connection, gate_id: int) -> str | None:
    async with db.execute(
        "SELECT f.fase FROM gate g JOIN fase_run f ON f.id = g.fase_run_id WHERE g.id = ?",
        (gate_id,),
    ) as cursor:
        fila = await cursor.fetchone()
    return str(fila["fase"]) if fila is not None else None


async def aplicar(
    db: aiosqlite.Connection,
    observador: Observador,
    decision: str,
    comentario: str | None = None,
) -> DecisionTomada:
    """La decisión del Autor sobre **el gate pendiente** de la novela, tomada en su PC.

    Es lo que ejecuta `storymaker decidir` antes de reanudar. Telegram solo avisa (arq. §10),
    así que esta es la única entrada de una decisión, y rechaza sin tocar nada lo que no
    se puede aplicar: una decisión fuera de las cuatro o una novela sin gate pendiente. Un
    gate ya decidido no está pendiente, de modo que decidir dos veces no reanuda dos veces.
    """
    if decision not in {d.value for d in Decision}:
        validas = ", ".join(d.value for d in DECISIONES)
        raise DecisionInvalida(f"«{decision}» no es una decision. Las validas son: {validas}.")
    pendiente = await arnes.gate_pendiente(db)
    if pendiente is None:
        raise DecisionInvalida("La novela no tiene ningun gate esperando decision.")
    fase = await _fase_del_gate(db, int(pendiente["id"]))
    if decision == Decision.ABORTAR.value and fase != "intake":
        raise DecisionInvalida(
            "Abortar solo cabe en el gate de Intake, que es la unica arista que declara el "
            "modelo TLA+. En los demas gates, no decidir ya deja la novela parada sin coste."
        )
    tomada = DecisionTomada(
        gate_id=int(pendiente["id"]),
        decision=Decision(decision),
        comentario=comentario or None,
        fase=fase,
    )
    await registrar(db, observador, tomada)
    return tomada
