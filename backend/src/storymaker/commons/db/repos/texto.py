"""spec: §4.4, §4.5 · arq: §7

Consultas sobre capítulos y versiones.

Aquí no hay ninguna operación que reescriba un capítulo, y no es un olvido: una versión
nueva es una fila nueva, y una versión de la novela es el manifiesto que lista qué
`capitulo_version` la componen. Por eso el «qué cambió» es un `JOIN` entre dos
manifiestos y no un diff de texto, y por eso un capítulo no regenerado se comparte entre
versiones sin duplicarse.
"""

from __future__ import annotations

import aiosqlite

from storymaker.commons.db.repos import id_insertado


async def insertar_capitulo_version(
    db: aiosqlite.Connection,
    *,
    capitulo_id: int,
    fase_run_id: int,
    texto: str,
    intento: int = 1,
    resumen: str | None = None,
) -> int:
    """Escribe un intento de capítulo. El recuento de palabras se calcula aquí.

    Se calcula y no se recibe porque `longitud_capitulo` compara contra este número: si lo
    declarase quien escribe, el validador estaría comprobando la aritmética del modelo en
    lugar de la longitud del texto.
    """
    palabras = len(texto.split())
    cursor = await db.execute(
        """
        INSERT INTO capitulo_version (capitulo_id, fase_run_id, intento, texto, palabras, resumen)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (capitulo_id, fase_run_id, intento, texto, palabras, resumen),
    )
    return id_insertado(cursor)


async def aprobar_capitulo(db: aiosqlite.Connection, capitulo_version_id: int) -> None:
    """Marca el estado. Es lo único que cambia de una fila ya escrita."""
    await db.execute(
        "UPDATE capitulo_version SET estado = 'aprobado' WHERE id = ?", (capitulo_version_id,)
    )


async def invalidar_capitulos(db: aiosqlite.Connection, ids: list[int]) -> None:
    """Deja capítulos posteriores a la espera de los validadores de coste cero (Fase 6)."""
    await db.executemany(
        "UPDATE capitulo_version SET estado = 'invalidado' WHERE id = ?", [(i,) for i in ids]
    )


async def capitulo_aprobado(db: aiosqlite.Connection, capitulo_id: int) -> aiosqlite.Row | None:
    async with db.execute(
        """
        SELECT * FROM capitulo_version
         WHERE capitulo_id = ? AND estado = 'aprobado'
         ORDER BY id DESC LIMIT 1
        """,
        (capitulo_id,),
    ) as cursor:
        return await cursor.fetchone()


async def publicar_version(
    db: aiosqlite.Connection,
    *,
    numero: int,
    capitulo_version_ids: list[int],
    gate_id: int | None = None,
) -> int:
    """Escribe la versión y su manifiesto. La anterior sobrevive entera, por construcción."""
    cursor = await db.execute(
        "INSERT INTO version_novela (numero, gate_id) VALUES (?, ?)", (numero, gate_id)
    )
    version_id = id_insertado(cursor)
    await db.executemany(
        "INSERT INTO version_capitulo (version_id, capitulo_version_id) VALUES (?, ?)",
        [(version_id, cv) for cv in capitulo_version_ids],
    )
    return version_id


async def capitulos_de_version(db: aiosqlite.Connection, version_id: int) -> list[aiosqlite.Row]:
    async with db.execute(
        """
        SELECT cv.*
          FROM version_capitulo vc
          JOIN capitulo_version cv ON cv.id = vc.capitulo_version_id
          JOIN plan_capitulo pc ON pc.id = cv.capitulo_id
         WHERE vc.version_id = ?
         ORDER BY pc.numero
        """,
        (version_id,),
    ) as cursor:
        return list(await cursor.fetchall())


async def capitulos_afectados(db: aiosqlite.Connection, hecho_id: int) -> list[int]:
    """Qué capítulos usan un hecho. Es el índice del que cuelga la Fase 6 entera.

    `uso_hecho` registra a granularidad de escena y esta consulta lo agrega a capítulo,
    que es la unidad de reescritura.
    """
    async with db.execute(
        """
        SELECT DISTINCT pc.numero
          FROM uso_hecho uh
          JOIN capitulo_version cv ON cv.id = uh.capitulo_version_id
          JOIN plan_capitulo pc ON pc.id = cv.capitulo_id
         WHERE uh.hecho_id = ? AND cv.estado = 'aprobado'
         ORDER BY pc.numero
        """,
        (hecho_id,),
    ) as cursor:
        return [int(fila["numero"]) for fila in await cursor.fetchall()]


async def diff_de_manifiestos(
    db: aiosqlite.Connection, version_a: int, version_b: int
) -> list[aiosqlite.Row]:
    """Qué capítulos cambian entre dos versiones, con un `JOIN` y sin mirar el texto."""
    async with db.execute(
        """
        SELECT pc.numero,
               a.capitulo_version_id AS antes,
               b.capitulo_version_id AS despues
          FROM version_capitulo a
          JOIN capitulo_version cva ON cva.id = a.capitulo_version_id
          JOIN plan_capitulo pc ON pc.id = cva.capitulo_id
          LEFT JOIN version_capitulo b
            ON b.version_id = ?
           AND b.capitulo_version_id IN (
                 SELECT id FROM capitulo_version WHERE capitulo_id = cva.capitulo_id
               )
         WHERE a.version_id = ?
           AND (b.capitulo_version_id IS NULL OR b.capitulo_version_id <> a.capitulo_version_id)
         ORDER BY pc.numero
        """,
        (version_b, version_a),
    ) as cursor:
        return list(await cursor.fetchall())


async def continuidad_de(db: aiosqlite.Connection, capitulo_version_id: int) -> list[aiosqlite.Row]:
    """El estado de continuidad al cierre de un capitulo, con el nombre de cada personaje.

    Lo escribe el extractor y cuelga del intento que lo produjo, no del capitulo: las filas
    de un intento descartado quedan colgando de una version que ningun manifiesto recoge.
    """
    async with db.execute(
        """
        SELECT c.*, p.nombre AS personaje, e.descripcion AS escenario
          FROM continuidad c
          JOIN canon_personaje p ON p.id = c.personaje_id
          LEFT JOIN canon_escenario e ON e.id = c.escenario_id
         WHERE c.capitulo_version_id = ?
         ORDER BY c.id
        """,
        (capitulo_version_id,),
    ) as cursor:
        return list(await cursor.fetchall())


async def insertar_continuidad(
    db: aiosqlite.Connection,
    *,
    capitulo_version_id: int,
    personaje_id: int,
    escenario_id: int | None = None,
    fecha_narrativa: str | None = None,
    conocimiento_json: str | None = None,
    posesiones_json: str | None = None,
    estado_json: str | None = None,
) -> int:
    cursor = await db.execute(
        """
        INSERT INTO continuidad (capitulo_version_id, personaje_id, escenario_id,
                                 fecha_narrativa, conocimiento_json, posesiones_json, estado_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            capitulo_version_id,
            personaje_id,
            escenario_id,
            fecha_narrativa,
            conocimiento_json,
            posesiones_json,
            estado_json,
        ),
    )
    return id_insertado(cursor)


async def resumen_de(db: aiosqlite.Connection, capitulo_version_id: int) -> str | None:
    async with db.execute(
        "SELECT resumen FROM capitulo_version WHERE id = ?", (capitulo_version_id,)
    ) as cursor:
        fila = await cursor.fetchone()
    if fila is None or fila["resumen"] is None:
        return None
    return str(fila["resumen"])


async def registrar_uso_hecho(
    db: aiosqlite.Connection,
    *,
    capitulo_version_id: int,
    escena_id: int,
    hecho_id: int,
    tipo_uso: str = "anclaje",
) -> None:
    """Lo puebla el extractor independiente, no quien escribio el capitulo."""
    await db.execute(
        """
        INSERT OR REPLACE INTO uso_hecho (capitulo_version_id, escena_id, hecho_id, tipo_uso)
        VALUES (?, ?, ?, ?)
        """,
        (capitulo_version_id, escena_id, hecho_id, tipo_uso),
    )


async def registrar_uso_hito(
    db: aiosqlite.Connection,
    *,
    capitulo_version_id: int,
    escena_id: int,
    hito_id: int,
    ejecutado: bool,
) -> None:
    """El gemelo de uso_hecho para el arco: sin el, mover un hito no invalidaria nada."""
    await db.execute(
        """
        INSERT OR REPLACE INTO uso_hito (capitulo_version_id, escena_id, hito_id, ejecutado)
        VALUES (?, ?, ?, ?)
        """,
        (capitulo_version_id, escena_id, hito_id, int(ejecutado)),
    )
