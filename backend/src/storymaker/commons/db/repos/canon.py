"""spec: §3.4, §4.3 · arq: §6, §7

Consultas sobre la biblia de la obra. Alimentan sobre todo los bloques 2 y 6 del paquete:
las fichas de quien sale en el capítulo, y las reglas con las que se escribe.

El canon es **biblia viva**: se edita en los gates y esas ediciones disparan el
reembedding de lo que se tocó. Por eso aquí no hay ninguna consulta que cachee nada.
"""

from __future__ import annotations

import json
from typing import Any

import aiosqlite


async def obra(db: aiosqlite.Connection) -> aiosqlite.Row | None:
    async with db.execute("SELECT * FROM canon_obra LIMIT 1") as cursor:
        return await cursor.fetchone()


async def estilo(db: aiosqlite.Connection) -> dict[str, Any]:
    """Los diales de la frontera historia-ficción, tal como el arquitecto los volcó.

    `grado_licencia`, `arcaismo` y `contenido_admisible` no los lee ningún validador por sí
    solos, y aun así son obligatorios: son la política contra la que el juez puntúa la
    autenticidad de época. Llegan a quien escribe por aquí, en el bloque 6.
    """
    fila = await obra(db)
    if fila is None or fila["estilo_json"] is None:
        return {}
    cargado: Any = json.loads(str(fila["estilo_json"]))
    return dict(cargado) if isinstance(cargado, dict) else {}


async def personajes(db: aiosqlite.Connection, ids: list[int]) -> list[aiosqlite.Row]:
    if not ids:
        return []
    marcas = ",".join("?" * len(ids))
    async with db.execute(
        f"SELECT * FROM canon_personaje WHERE id IN ({marcas}) ORDER BY id",  # noqa: S608
        ids,
    ) as cursor:
        return list(await cursor.fetchall())


async def escenarios(db: aiosqlite.Connection, ids: list[int]) -> list[aiosqlite.Row]:
    if not ids:
        return []
    marcas = ",".join("?" * len(ids))
    async with db.execute(
        f"SELECT * FROM canon_escenario WHERE id IN ({marcas}) ORDER BY id",  # noqa: S608
        ids,
    ) as cursor:
        return list(await cursor.fetchall())


async def glosario(db: aiosqlite.Connection) -> list[aiosqlite.Row]:
    async with db.execute("SELECT * FROM canon_glosario ORDER BY termino") as cursor:
        return list(await cursor.fetchall())


async def prohibidas(db: aiosqlite.Connection) -> list[aiosqlite.Row]:
    """Los tres niveles: `global`, `novela` y `destinatario`."""
    async with db.execute("SELECT * FROM canon_prohibida ORDER BY nivel, termino") as cursor:
        return list(await cursor.fetchall())


async def licencias(db: aiosqlite.Connection) -> list[aiosqlite.Row]:
    async with db.execute("SELECT * FROM canon_licencia ORDER BY id") as cursor:
        return list(await cursor.fetchall())


async def arcos(db: aiosqlite.Connection) -> list[aiosqlite.Row]:
    async with db.execute(
        """
        SELECT a.*, p.nombre AS personaje
          FROM canon_arco a
          JOIN canon_personaje p ON p.id = a.personaje_id
         ORDER BY a.id
        """
    ) as cursor:
        return list(await cursor.fetchall())


async def hitos_de_arco(db: aiosqlite.Connection, arco_id: int) -> list[aiosqlite.Row]:
    async with db.execute(
        """
        SELECT h.*, e.capitulo_id, c.numero AS capitulo_numero
          FROM canon_arco_hito h
          LEFT JOIN plan_escena e ON e.id = h.escena_id
          LEFT JOIN plan_capitulo c ON c.id = e.capitulo_id
         WHERE h.arco_id = ?
         ORDER BY h.orden
        """,
        (arco_id,),
    ) as cursor:
        return list(await cursor.fetchall())


async def homenajeado(db: aiosqlite.Connection) -> aiosqlite.Row | None:
    """La ficha de la persona a quien se regala la novela.

    Existe como columna y no solo como cadena en el `Brief` porque sin ella ninguna
    consulta sabría **cuál de las fichas es la suya**, y a él se le exige algo distinto que
    a los demás: arco con hitos y cierre en el tercio final.
    """
    async with db.execute(
        """
        SELECT p.*
          FROM canon_obra o
          JOIN canon_personaje p ON p.id = o.homenajeado_id
         LIMIT 1
        """
    ) as cursor:
        return await cursor.fetchone()
