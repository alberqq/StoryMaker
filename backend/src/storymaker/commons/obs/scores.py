"""spec: §3.8 · arq: §13, §14

El envío de *scores* a la traza y su escritura en la base, que ocurren juntos.

**Todos** los validadores puntúan: los programáticos, los semánticos y los de Lean. Y las
decisiones de gate también, porque **la intervención del Autor queda trazada igual que la
de un agente** — sin eso, la traza contaría la mitad de la historia y la revisión humana
que exige el enunciado no tendría dónde verse.

Un *score* que solo viviera en Langfuse sería un dato que la novela no puede explicar por
sí sola, y uno que solo viviera en SQLite no aparecería en la sesión. Por eso este módulo
escribe en los dos sitios y es el único que lo hace.
"""

from __future__ import annotations

from typing import Any

import aiosqlite

from storymaker.commons.db.repos import arnes
from storymaker.commons.obs.trazas import Observador
from storymaker.commons.validation.modelos import Incidencia


async def registrar(
    db: aiosqlite.Connection,
    observador: Observador,
    *,
    validador: str,
    valor: float,
    objeto_tipo: str,
    objeto_id: int,
    detalle: dict[str, Any] | None = None,
) -> None:
    """Un *score* en la base y en la traza, con el mismo nombre en los dos sitios."""
    await arnes.registrar_score(
        db,
        objeto_tipo=objeto_tipo,
        objeto_id=objeto_id,
        validador=validador,
        valor=valor,
        detalle=detalle,
    )
    observador.registrar_score(
        nombre=validador,
        valor=valor,
        objeto=f"{objeto_tipo}:{objeto_id}",
        detalle=detalle,
    )


async def registrar_veredicto(
    db: aiosqlite.Connection,
    observador: Observador,
    *,
    validador: str,
    incidencias: list[Incidencia],
    objeto_tipo: str,
    objeto_id: int,
) -> None:
    """Puntúa un validador binario: 1 si pasó, 0 si abrió incidencias.

    Se puntúa también cuando pasa, y es deliberado: una traza en la que solo aparecen los
    fallos no permite distinguir un validador que fue correcto de uno que no llegó a
    correr, que es justo la diferencia que `registro_de_validadores` y las aserciones de G6
    existen para vigilar.
    """
    await registrar(
        db,
        observador,
        validador=validador,
        valor=0.0 if incidencias else 1.0,
        objeto_tipo=objeto_tipo,
        objeto_id=objeto_id,
        detalle={"incidencias": [i.mensaje for i in incidencias]} if incidencias else None,
    )


async def registrar_decision_de_gate(
    db: aiosqlite.Connection,
    observador: Observador,
    *,
    gate_id: int,
    decision: str,
    actor: str,
    comentario: str | None = None,
) -> None:
    """La decisión del Autor, en la traza y en el audit log.

    Todo comentario y toda edición se guardan como fila, se versionan y van al audit log y
    a Langfuse: es lo que hace que la revisión humana sea auditable y no un recuerdo.
    """
    await arnes.registrar_audit(
        db,
        actor=actor,
        accion=f"gate:{decision}",
        objeto=f"gate:{gate_id}",
        despues={"decision": decision, "comentario": comentario},
    )
    observador.registrar_score(
        nombre="decision_de_gate",
        valor=1.0 if decision == "aprobar" else 0.0,
        objeto=f"gate:{gate_id}",
        detalle={"decision": decision, "actor": actor, "comentario": comentario},
    )
