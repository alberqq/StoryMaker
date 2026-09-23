"""spec: §4.3 · arq: §16.2

Cómo llega el corpus al arquitecto: **por búsqueda semántica, no volcándoselo entero**.

Es el tercero de los cuatro usos que la arquitectura da a los embeddings, y el que menos se
nota hasta que falta. Una novela tiene unos cientos de hechos; meterlos todos en la ventana
del arquitecto se come su techo de 25.000 tokens y deja sin sitio a lo que de verdad tiene
que producir, que es la escaleta.

Como en el ensamblador, **quien recupera es el código y no el agente**: la consulta se
deriva de lo que se está planificando —el período, el lugar, el rol de época del
homenajeado— y no de lo que al modelo se le ocurra preguntar. Esa es la línea que separa una
gestión de contexto reproducible de un RAG cuyo resultado depende del humor del modelo.
"""

from __future__ import annotations

import aiosqlite

from storymaker.commons.config import Settings
from storymaker.commons.db.repos import mundo
from storymaker.commons.embeddings import indice
from storymaker.commons.embeddings.modelo import Vectorizador
from storymaker.intake.esquemas import Brief
from storymaker.investigation.esquemas import Dimension


def consulta_para(brief: Brief) -> str:
    """La consulta, derivada mecánicamente del encargo. Nadie la elige sobre la marcha."""
    partes = [
        brief.periodo.denominacion,
        brief.lugar,
        brief.rol_epoca,
        brief.evento_ancla or "",
        " ".join(e.valor for e in brief.elementos_personalizacion),
    ]
    return " ".join(p for p in partes if p)


async def hechos_relevantes(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    brief: Brief,
    *,
    settings: Settings,
    por_dimension: int = 4,
) -> list[aiosqlite.Row]:
    """Los hechos que el arquitecto necesita, repartidos por dimensión.

    Se pide **por dimensión y no en bloque** a propósito. Una consulta global devolvería los
    ocho hechos más parecidos a la consulta, que probablemente serían ocho de cultura
    material: quien planifica necesita algo de las seis, no mucho de una.
    """
    consulta = consulta_para(brief)
    encontrados: dict[int, aiosqlite.Row] = {}

    for dimension in Dimension:
        vecinos = await indice.buscar_hechos(
            db, vectorizador, consulta, k=por_dimension, dimension=dimension.value
        )
        for vecino in vecinos:
            if vecino.id in encontrados:
                continue
            fila = await mundo.hecho_por_id(db, vecino.id)
            if fila is not None:
                encontrados[vecino.id] = fila

    return list(encontrados.values())


def como_texto(hechos: list[aiosqlite.Row]) -> str:
    """El corpus tal como lo ve el arquitecto, con el estado epistémico delante.

    El estado va delante y no al final porque es lo que decide cómo usar el hecho: sobre un
    `verificado` se puede anclar una escena entera; sobre un `desconocido`, conviene no
    apoyar la trama.
    """
    return "\n".join(
        f"[{fila['estado']}·{fila['dimension']}] (#{fila['id']}) {fila['enunciado']}"
        for fila in hechos
    )
