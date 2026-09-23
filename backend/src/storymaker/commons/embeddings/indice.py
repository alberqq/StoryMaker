"""spec: §3.5 · arq: §7, §16.2

Los tres índices semánticos y las dos operaciones que el sistema hace con ellos: indexar
una fila y buscar los `k` vecinos.

**Este es el único módulo autorizado a escribir en las tablas `vec_*`**, y la regla
Semgrep `indice-solo-por-embeddings` lo impone. El motivo es que el índice se escribe en
la misma transacción que la fila: quien inserta un hecho, una ficha de canon o un resumen
lo indexa en el mismo `commit`. Si cada feature lo hiciera por su cuenta, el canon —que es
biblia viva— y su índice divergirían en cuanto el Autor editara una ficha en un gate, y la
búsqueda seguiría devolviendo el texto anterior a la corrección.

**El filtro ocurre dentro de la consulta KNN**, no después en Python. Eso importa sobre
todo en el bloque 4 del paquete: pedir los resúmenes más parecidos *entre los capítulos
anteriores a N* es una condición de la consulta, no una lista de vecinos que haya que
descartar luego sin saber cuántos quedarán.
"""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite
import sqlite_vec

from storymaker.commons.config import Defaults
from storymaker.commons.embeddings.modelo import Vectorizador


@dataclass(frozen=True)
class Vecino:
    """Una fila recuperada, con su distancia. La distancia viaja porque el ensamblador
    trunca por relevancia y necesita saber qué es lo menos parecido de lo que trae."""

    id: int
    distancia: float


def _serializar(vector: list[float]) -> bytes:
    """El formato que `vec0` espera: 384 flotantes de 32 bits, sin cabecera."""
    return bytes(sqlite_vec.serialize_float32(vector))


async def indexar_hecho(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    *,
    hecho_id: int,
    enunciado: str,
    estado: str,
    dimension: str,
) -> None:
    """Indexa un hecho del corpus con su estado epistémico y su dimensión como metadatos."""
    (vector,) = vectorizador.vectorizar([enunciado])
    await db.execute("DELETE FROM vec_hecho WHERE hecho_id = ?", (hecho_id,))
    await db.execute(
        "INSERT INTO vec_hecho (hecho_id, embedding, estado, dimension) VALUES (?, ?, ?, ?)",
        (hecho_id, _serializar(vector), estado, dimension),
    )


async def indexar_canon(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    *,
    tabla: str,
    fila_id: int,
    texto: str,
    familia: str,
) -> None:
    """Indexa una ficha de la biblia.

    `vec_canon` lleva identificador propio porque la biblia son tres tablas y la clave
    primaria de una tabla `vec0` es un único entero: a qué tabla y a qué fila apunta se
    guarda en columnas auxiliares, que se almacenan sin indexar porque nunca se filtra por
    ellas — solo se leen al resolver el resultado.
    """
    (vector,) = vectorizador.vectorizar([texto])
    await db.execute("DELETE FROM vec_canon WHERE tabla = ? AND fila_id = ?", (tabla, fila_id))
    async with db.execute("SELECT COALESCE(MAX(id), 0) + 1 AS siguiente FROM vec_canon") as cursor:
        fila = await cursor.fetchone()
    siguiente = int(fila["siguiente"]) if fila is not None else 1
    await db.execute(
        """
        INSERT INTO vec_canon (id, embedding, familia, tabla, fila_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (siguiente, _serializar(vector), familia, tabla, fila_id),
    )


async def indexar_resumen(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    *,
    capitulo_version_id: int,
    resumen: str,
    capitulo_numero: int,
    vigente: bool = True,
) -> None:
    (vector,) = vectorizador.vectorizar([resumen])
    await db.execute(
        "DELETE FROM vec_resumen WHERE capitulo_version_id = ?", (capitulo_version_id,)
    )
    await db.execute(
        """
        INSERT INTO vec_resumen (capitulo_version_id, embedding, capitulo_numero, vigente)
        VALUES (?, ?, ?, ?)
        """,
        (capitulo_version_id, _serializar(vector), capitulo_numero, int(vigente)),
    )


async def marcar_vigente(
    db: aiosqlite.Connection, *, capitulo_version_id: int, capitulo_numero: int
) -> None:
    """Pone a 1 el resumen de la versión aprobada y a 0 el de la que sustituye.

    Sin este filtro, el escritor del capítulo 7 podría recibir el resumen de un intento
    rechazado del 3: un fallo silencioso, porque el capítulo saldría bien escrito
    recordando algo que ya no está en la novela.
    """
    await db.execute(
        "UPDATE vec_resumen SET vigente = 0 WHERE capitulo_numero = ?", (capitulo_numero,)
    )
    await db.execute(
        "UPDATE vec_resumen SET vigente = 1 WHERE capitulo_version_id = ?", (capitulo_version_id,)
    )


async def buscar_hechos(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    consulta: str,
    *,
    k: int = Defaults.K_VECINOS,
    dimension: str | None = None,
) -> list[Vecino]:
    """Los `k` hechos más próximos, con el filtro de dimensión dentro de la consulta."""
    (vector,) = vectorizador.vectorizar([consulta])
    sql = "SELECT hecho_id AS id, distance FROM vec_hecho WHERE embedding MATCH ? AND k = ?"
    parametros: list[object] = [_serializar(vector), k]
    if dimension is not None:
        sql += " AND dimension = ?"
        parametros.append(dimension)
    async with db.execute(sql + " ORDER BY distance", parametros) as cursor:
        return [Vecino(int(f["id"]), float(f["distance"])) for f in await cursor.fetchall()]


async def buscar_canon(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    consulta: str,
    *,
    k: int = Defaults.K_VECINOS,
    familia: str | None = None,
) -> list[tuple[str, int, float]]:
    """Devuelve (tabla, fila_id, distancia): el índice guarda a quién describe."""
    (vector,) = vectorizador.vectorizar([consulta])
    sql = (
        "SELECT tabla, fila_id, distance FROM vec_canon WHERE embedding MATCH ? AND k = ?"
    )
    parametros: list[object] = [_serializar(vector), k]
    if familia is not None:
        sql += " AND familia = ?"
        parametros.append(familia)
    async with db.execute(sql + " ORDER BY distance", parametros) as cursor:
        return [
            (str(f["tabla"]), int(f["fila_id"]), float(f["distance"]))
            for f in await cursor.fetchall()
        ]


async def buscar_resumenes(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    consulta: str,
    *,
    anteriores_a: int,
    k: int = Defaults.K_VECINOS,
) -> list[Vecino]:
    """Los resúmenes vigentes de capítulos anteriores a N, por relevancia.

    Es lo que hace que el sistema escale a novelas largas: en el capítulo 10 no hacen falta
    los nueve resúmenes anteriores con el mismo peso, hacen falta los tres que importan.
    """
    (vector,) = vectorizador.vectorizar([consulta])
    async with db.execute(
        """
        SELECT capitulo_version_id AS id, distance
          FROM vec_resumen
         WHERE embedding MATCH ? AND k = ?
           AND capitulo_numero < ? AND vigente = 1
         ORDER BY distance
        """,
        (_serializar(vector), k, anteriores_a),
    ) as cursor:
        return [Vecino(int(f["id"]), float(f["distance"])) for f in await cursor.fetchall()]
