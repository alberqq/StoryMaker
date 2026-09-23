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
from storymaker.commons.obs.scores import registrar_decision_de_gate
from storymaker.commons.obs.trazas import Observador


class Decision(StrEnum):
    APROBAR = "aprobar"
    REHACER = "rehacer"
    EDITAR = "editar"
    ABORTAR = "abortar"


#: Las cuatro, en el orden en que aparecen en los botones inline.
DECISIONES = (Decision.APROBAR, Decision.REHACER, Decision.EDITAR, Decision.ABORTAR)


@dataclass(frozen=True)
class DecisionTomada:
    gate_id: int
    decision: Decision
    comentario: str | None = None
    actor: str = "autor"

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


def desde_callback(dato: str) -> DecisionTomada | None:
    """Traduce el `callback_data` de un botón de Telegram: `<gate_id>:<decision>`.

    Devuelve `None` en lugar de lanzar si el dato no encaja, porque esto lo alimenta una
    petición de fuera: un callback malformado es una petición que se rechaza, no una avería
    del arnés.
    """
    gate, _, decision = dato.partition(":")
    if not gate.isdigit() or decision not in {d.value for d in Decision}:
        return None
    return DecisionTomada(gate_id=int(gate), decision=Decision(decision))
