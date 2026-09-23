"""spec: §3.1 · arq: §7

Repositorios de dominio: una consulta con nombre por cada cosa que el arnés necesita
saber o escribir. Nadie fuera de este paquete construye SQL contra las tablas.
"""

from __future__ import annotations

import aiosqlite


def id_insertado(cursor: aiosqlite.Cursor) -> int:
    """El identificador de la fila recién escrita.

    SQLite devuelve `lastrowid` como opcional y nosotros lo necesitamos siempre: si
    faltara, el nodo estaría escribiendo filas que luego no puede referenciar, y eso es
    una avería, no una incidencia. Se comprueba con una excepción y no con un `assert`
    porque `python -O` borra los asertos y esta comprobación tiene que sobrevivir.
    """
    if cursor.lastrowid is None:
        raise RuntimeError("la insercion no devolvio identificador de fila")
    return int(cursor.lastrowid)
