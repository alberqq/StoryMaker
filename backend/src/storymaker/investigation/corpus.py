"""spec: §4.2 · arq: §4, §7, §16.2

Escribe en el corpus lo que el investigador trae, e indexa cada hecho **en la misma
transacción que la fila**.

Dos reglas gobiernan este módulo. La primera es que cada hecho lleva el `fase_run_id` que
lo escribió: **rehacer no contamina**. Si el Autor rehace la fase desde el gate, el
investigador vuelve a correr y escribe hechos nuevos; los de la ejecución anterior no se
borran ni se mezclan, y quedan como historia consultable.

La segunda es que el índice semántico se escribe con la fila. Si se escribieran por
separado, un fallo entre medias dejaría un hecho que el ensamblador nunca encontraría, o un
vector apuntando a una fila que no existe.
"""

from __future__ import annotations

import aiosqlite

from storymaker.commons.db.repos import id_insertado, mundo
from storymaker.commons.embeddings import indice
from storymaker.commons.embeddings.modelo import Vectorizador
from storymaker.investigation.esquemas import FuenteCitada, HechoPropuesto


async def _guardar_fuente(db: aiosqlite.Connection, fuente: FuenteCitada) -> int:
    """Reutiliza la fuente si ya está: una página citada por seis hechos es una fila."""
    async with db.execute("SELECT id FROM mundo_fuente WHERE url = ?", (fuente.url,)) as cursor:
        existente = await cursor.fetchone()
    if existente is not None:
        return int(existente["id"])
    cursor = await db.execute(
        "INSERT INTO mundo_fuente (tipo, url, titulo) VALUES (?, ?, ?)",
        (fuente.tipo, fuente.url, fuente.titulo),
    )
    return id_insertado(cursor)


async def escribir_hecho(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    hecho: HechoPropuesto,
    *,
    fase_run_id: int,
    origen: str = "investigacion_inicial",
) -> int:
    """Escribe el hecho, sus fuentes y su vector. Devuelve el identificador.

    El `respaldo` nace en `pendiente` y lo escribe el verificador después. Nace así y no en
    `respaldado` porque dar por bueno lo que nadie ha mirado es exactamente el fallo que el
    paso 2 existe para impedir.
    """
    hecho_id = await mundo.insertar_hecho(
        db,
        fase_run_id=fase_run_id,
        enunciado=hecho.enunciado,
        estado=hecho.estado.value,
        dimension=hecho.dimension.value,
        origen=origen,
        cita=hecho.cita or None,
        respaldo="no_aplica" if origen == "invencion_autorizada" else "pendiente",
        entidades={"nombres": hecho.entidades} if hecho.entidades else None,
    )

    for fuente in hecho.fuentes:
        fuente_id = await _guardar_fuente(db, fuente)
        await db.execute(
            "INSERT OR IGNORE INTO mundo_hecho_fuente (hecho_id, fuente_id) VALUES (?, ?)",
            (hecho_id, fuente_id),
        )

    await indice.indexar_hecho(
        db,
        vectorizador,
        hecho_id=hecho_id,
        enunciado=hecho.enunciado,
        estado=hecho.estado.value,
        dimension=hecho.dimension.value,
    )
    return hecho_id


async def escribir_lote(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    hechos: list[HechoPropuesto],
    *,
    fase_run_id: int,
    origen: str = "investigacion_inicial",
) -> list[int]:
    return [
        await escribir_hecho(db, vectorizador, hecho, fase_run_id=fase_run_id, origen=origen)
        for hecho in hechos
    ]


async def degradar_sin_respaldo(db: aiosqlite.Connection, hecho_id: int, respaldado: bool) -> None:
    """Escribe el veredicto. Un `no_respaldado` **degrada el hecho, no lo borra**.

    Nada de esto detiene la fase. Un hecho sin respaldo baja de categoría y aparece
    destacado en el informe del gate, donde el Autor decide si lo corrige, lo borra a mano
    o lo deja pasar sabiendo lo que es. La degradación tiene consecuencia real más adelante,
    porque el bloque 5 del paquete lleva el estado epistémico hasta el escritor.
    """
    await mundo.anotar_respaldo(db, hecho_id, "respaldado" if respaldado else "no_respaldado")
