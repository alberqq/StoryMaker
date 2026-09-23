"""spec: §3.1 · arq: §1, §7

La regla que sostiene el §7 entero: **el checkpoint de LangGraph y la escritura de
dominio ocurren en la misma transacción.** El nodo no hace `commit` por su cuenta; lo
hace este envoltorio al cerrar el paso.

De ahí que no pueda existir un instante en que el grafo crea que el capítulo 6 está
hecho y la biblia no lo tenga — que es justo el fallo que TLC encontraría, y la razón de
que una novela sea un fichero y no tres.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiosqlite


@asynccontextmanager
async def paso_atomico(db: aiosqlite.Connection) -> AsyncIterator[aiosqlite.Connection]:
    """Todo lo que ocurra dentro se confirma junto o no ocurre.

    Se abre con `BEGIN IMMEDIATE` y no con el `BEGIN` perezoso: la escritura se reclama al
    entrar, de modo que dos invocaciones que se solaparan chocarían aquí y no a mitad del
    paso, con parte del trabajo ya hecho. El cerrojo de fichero de §16.4 es la primera
    defensa; esta es la segunda, dentro del propio SQLite.
    """
    await db.execute("BEGIN IMMEDIATE")
    try:
        yield db
    except BaseException:
        await db.rollback()
        raise
    else:
        await db.commit()
