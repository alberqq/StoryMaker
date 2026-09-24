"""spec: §4.2, §4.3 · arq: §4, §7

Consultas sobre el corpus histórico.

Dos ideas gobiernan este módulo. La primera es que **solo son vigentes los hechos de la
última ejecución de Investigation**: rehacer la fase escribe hechos nuevos y no borra ni
mezcla los anteriores, que quedan como historia consultable. La segunda es que **el sello
cierra la puerta**: calculado sobre el contenido ordenado de las tablas `mundo_*`
vigentes, convierte el corpus en solo lectura para todo lo que venga después.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import aiosqlite

from storymaker.commons.db.repos import id_insertado


async def insertar_hecho(
    db: aiosqlite.Connection,
    *,
    fase_run_id: int,
    enunciado: str,
    estado: str,
    dimension: str,
    origen: str = "investigacion_inicial",
    cita: str | None = None,
    respaldo: str = "pendiente",
    entidades: dict[str, Any] | None = None,
) -> int:
    """Escribe un hecho del corpus.

    La cita va acotada a 300 caracteres por el `CHECK` del esquema, y no es adorno: es lo
    único que hace verificable el paso 2 de Investigation.
    """
    cursor = await db.execute(
        """
        INSERT INTO mundo_hecho (fase_run_id, enunciado, estado, entidades_json, dimension,
                                 origen, cita, respaldo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            fase_run_id,
            enunciado,
            estado,
            json.dumps(entidades) if entidades else None,
            dimension,
            origen,
            cita,
            respaldo,
        ),
    )
    return id_insertado(cursor)


async def hechos_vigentes(db: aiosqlite.Connection, fase_run_id: int) -> list[aiosqlite.Row]:
    """Los de la ejecución indicada, que es la única vigente.

    Los de ejecuciones anteriores siguen en la tabla y se pueden consultar, pero no
    componen el corpus: rehacer una fase no contamina lo que la siguiente lee.
    """
    async with db.execute(
        "SELECT * FROM mundo_hecho WHERE fase_run_id = ? ORDER BY id", (fase_run_id,)
    ) as cursor:
        return list(await cursor.fetchall())


async def hechos_por_dimension(db: aiosqlite.Connection, fase_run_id: int) -> dict[str, int]:
    """El recuento que el informe del gate pone delante del Autor.

    Existe porque el reparto de las tres búsquedas entre las seis dimensiones lo decide el
    modelo, y una dimensión puede quedar mucho más pobre que las otras: enseñarlo es la
    mitigación declarada de ese riesgo.
    """
    async with db.execute(
        "SELECT dimension, COUNT(*) AS n FROM mundo_hecho WHERE fase_run_id = ? GROUP BY dimension",
        (fase_run_id,),
    ) as cursor:
        return {str(fila["dimension"]): int(fila["n"]) for fila in await cursor.fetchall()}


async def pendientes_de_verificar(
    db: aiosqlite.Connection, fase_run_id: int, *, tamano_lote: int
) -> list[list[aiosqlite.Row]]:
    """Los hechos por verificar, ya troceados en lotes.

    El troceo no es cosmético: evita que el tamaño del corpus convierta la comprobación en
    una llamada que la guarda de presupuesto rechaza por pasarse de contexto, que sería el
    peor final posible —el corpus se quedaría sin verificar y nadie se enteraría—.
    """
    async with db.execute(
        "SELECT * FROM mundo_hecho WHERE fase_run_id = ? AND respaldo = 'pendiente' ORDER BY id",
        (fase_run_id,),
    ) as cursor:
        filas = list(await cursor.fetchall())
    return [filas[i : i + tamano_lote] for i in range(0, len(filas), tamano_lote)]


async def anotar_respaldo(
    db: aiosqlite.Connection, hecho_id: int, respaldo: str, sin_respaldo: str | None = None
) -> None:
    """Escribe el veredicto del verificador, **y nada más**.

    `estado` se queda como lo declaró quien creó la fila: cada columna tiene un solo dueño
    (arq. §7). Un hecho no respaldado no se borra ni se reescribe; lo que baja es su
    firmeza, que `puras.firmeza` calcula al leer y que el bloque 5 lleva hasta el escritor.
    `sin_respaldo` es el añadido del veredicto parcial, o nada.
    """
    await db.execute(
        "UPDATE mundo_hecho SET respaldo = ?, sin_respaldo = ? WHERE id = ?",
        (respaldo, sin_respaldo or None, hecho_id),
    )


async def hay_sello(db: aiosqlite.Connection) -> bool:
    async with db.execute("SELECT 1 FROM mundo_sello LIMIT 1") as cursor:
        return await cursor.fetchone() is not None


async def calcular_hash_corpus(db: aiosqlite.Connection, fase_run_id: int) -> str:
    """El hash sobre el contenido **ordenado** de las tablas `mundo_*` vigentes.

    Ordenado porque si dependiera del orden de inserción, dos corpus idénticos darían
    hashes distintos y el manifiesto dejaría de poder responder si dos versiones partieron
    del mismo material. Lleva el `respaldo` y `sin_respaldo` porque la firmeza y lo que no
    dice la cita, que verá el escritor, dependen de ellos: dos corpus con el mismo texto y
    distinto veredicto no son el mismo material.
    """
    resumen = hashlib.sha256()
    async with db.execute(
        """
        SELECT enunciado, estado, dimension, origen, COALESCE(cita, '') AS cita, respaldo,
               COALESCE(sin_respaldo, '') AS sin_respaldo
          FROM mundo_hecho
         WHERE fase_run_id = ?
         ORDER BY enunciado, dimension, origen
        """,
        (fase_run_id,),
    ) as cursor:
        for fila in await cursor.fetchall():
            resumen.update("\x1f".join(str(v) for v in tuple(fila)).encode("utf-8"))
    async with db.execute(
        """
        SELECT tipo, nombre, COALESCE(nombre_epoca, '') AS nombre_epoca,
               COALESCE(fecha_inicio, '') AS fecha_inicio, COALESCE(fecha_fin, '') AS fecha_fin
          FROM mundo_entidad
         ORDER BY tipo, nombre
        """
    ) as cursor:
        for fila in await cursor.fetchall():
            resumen.update("\x1f".join(str(v) for v in tuple(fila)).encode("utf-8"))
    return resumen.hexdigest()


async def sellar_corpus(db: aiosqlite.Connection, fase_run_id: int) -> str:
    """Cierra el corpus. A partir de aquí solo se puede anclar o declarar una Licencia."""
    hash_corpus = await calcular_hash_corpus(db, fase_run_id)
    await db.execute(
        "INSERT INTO mundo_sello (hash, fase_run_id) VALUES (?, ?)", (hash_corpus, fase_run_id)
    )
    return hash_corpus


async def hecho_por_id(db: aiosqlite.Connection, hecho_id: int) -> aiosqlite.Row | None:
    async with db.execute("SELECT * FROM mundo_hecho WHERE id = ?", (hecho_id,)) as cursor:
        return await cursor.fetchone()


async def inventados_por_dimension(db: aiosqlite.Connection, fase_run_id: int) -> dict[str, int]:
    """El recuento que el informe del gate de Plotting pone delante del Autor.

    La invencion autorizada **no se topa: se cuenta**. Poner limite a lo que el arquitecto
    puede inventar solo le dejaria salidas peores —fallar, o declarar otro origen—, asi que
    lo que hace el arnes es ensenarlo.
    """
    async with db.execute(
        """
        SELECT dimension, COUNT(*) AS n
          FROM mundo_hecho
         WHERE fase_run_id = ? AND origen = 'invencion_autorizada'
         GROUP BY dimension
        """,
        (fase_run_id,),
    ) as cursor:
        return {str(f["dimension"]): int(f["n"]) for f in await cursor.fetchall()}


async def micro_sin_respaldo(db: aiosqlite.Connection, fase_run_id: int) -> int:
    """Cuántos hechos de la micro-sesión de Plotting no respaldó el verificador."""
    async with db.execute(
        """
        SELECT COUNT(*) AS n FROM mundo_hecho
         WHERE fase_run_id = ? AND origen = 'micro_arquitecto' AND respaldo = 'no_respaldado'
        """,
        (fase_run_id,),
    ) as cursor:
        fila = await cursor.fetchone()
    return int(fila["n"]) if fila is not None else 0


async def sin_respaldo(db: aiosqlite.Connection, fase_run_id: int) -> list[aiosqlite.Row]:
    """Los hechos que el verificador no respaldó, que el informe del gate destaca."""
    async with db.execute(
        """
        SELECT * FROM mundo_hecho
         WHERE fase_run_id = ? AND respaldo = 'no_respaldado'
         ORDER BY id
        """,
        (fase_run_id,),
    ) as cursor:
        return list(await cursor.fetchall())


#: Lo que ya se apoya en un hecho. Si alguna tiene filas, descartarlo dejaría a la trama o
#: al texto apuntando a nada.
_USOS_DE_UN_HECHO = ("canon_licencia", "plan_anclaje", "uso_hecho")


async def descartar_hecho(db: aiosqlite.Connection, hecho_id: int) -> aiosqlite.Row | None:
    """Borra un hecho del corpus, con sus fuentes y su vector, y lo devuelve como era.

    Es el «lo borra a mano» de arq. §4, Fase 2: el Autor quita en el gate de Investigation un
    hecho que no quiere en la novela. Solo cabe antes del sello —los disparadores de
    inmutabilidad lo impiden después— y solo si nada lo usa todavía. `None` si no existe;
    `ValueError` si algo lo usa.
    """
    async with db.execute("SELECT * FROM mundo_hecho WHERE id = ?", (hecho_id,)) as cursor:
        fila = await cursor.fetchone()
    if fila is None:
        return None
    for tabla in _USOS_DE_UN_HECHO:
        async with db.execute(
            f"SELECT 1 FROM {tabla} WHERE hecho_id = ? LIMIT 1",  # noqa: S608 — lista cerrada
            (hecho_id,),
        ) as cursor:
            if await cursor.fetchone() is not None:
                raise ValueError(f"El hecho {hecho_id} ya lo usa {tabla}.")
    await db.execute("DELETE FROM mundo_hecho_fuente WHERE hecho_id = ?", (hecho_id,))
    await db.execute("DELETE FROM vec_hecho WHERE hecho_id = ?", (hecho_id,))
    await db.execute("DELETE FROM mundo_hecho WHERE id = ?", (hecho_id,))
    return fila
