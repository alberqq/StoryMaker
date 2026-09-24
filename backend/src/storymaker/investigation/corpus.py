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
from storymaker.investigation.esquemas import EstadoEpistemico, FuenteCitada, HechoPropuesto


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


def _respaldo_inicial(hecho: HechoPropuesto, origen: str) -> str:
    """`no_aplica` para lo que no tiene cita que comprobar; `pendiente` para lo demás.

    Una invención no tiene fuente, y una laguna —`desconocido`— dice que algo no se sabe:
    en ninguna de las dos hay fragmento que el verificador pueda leer (arq. §4, Fase 2).
    """
    if origen == "invencion_autorizada" or hecho.estado is EstadoEpistemico.DESCONOCIDO:
        return "no_aplica"
    return "pendiente"


async def escribir_hecho(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    hecho: HechoPropuesto,
    *,
    fase_run_id: int,
    origen: str = "investigacion_inicial",
) -> int:
    """Escribe el hecho, sus fuentes y su vector. Devuelve el identificador.

    El `respaldo` nace en `pendiente` y lo escribe el verificador después, salvo en lo que no
    tiene cita que comprobar. Nace así y no en `respaldado` porque dar por bueno lo que nadie
    ha mirado es exactamente el fallo que el paso 2 existe para impedir.
    """
    hecho_id = await mundo.insertar_hecho(
        db,
        fase_run_id=fase_run_id,
        enunciado=hecho.enunciado,
        estado=hecho.estado.value,
        dimension=hecho.dimension.value,
        origen=origen,
        cita=hecho.cita or None,
        respaldo=_respaldo_inicial(hecho, origen),
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


async def anotar_veredicto(
    db: aiosqlite.Connection, hecho_id: int, respaldado: bool, sin_respaldo: str = ""
) -> None:
    """Escribe el veredicto. Un `no_respaldado` **baja la firmeza del hecho, no lo borra**.

    Nada de esto detiene la fase ni reescribe lo que declaró el investigador. Un hecho sin
    respaldo aparece destacado en el informe del gate, donde el Autor decide si lo corrige,
    lo borra a mano o lo deja pasar sabiendo lo que es. La bajada tiene consecuencia real
    más adelante, porque el bloque 5 del paquete lleva la firmeza hasta el escritor.
    """
    # El añadido solo cuenta si el dato central está respaldado: es lo que hace parcial
    # al veredicto. En un no respaldado no hay nada que separar.
    await mundo.anotar_respaldo(
        db,
        hecho_id,
        "respaldado" if respaldado else "no_respaldado",
        sin_respaldo if respaldado else None,
    )
