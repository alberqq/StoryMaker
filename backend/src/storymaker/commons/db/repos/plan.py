"""spec: §3.4 · arq: §6, §7

Consultas sobre la escaleta. Son casi todas para el ensamblador de paquetes, que deriva de
aquí el encargo del capítulo y la consulta con la que busca por relevancia.

La escena es la unidad de planificación y de traza; el capítulo, la de redacción. Por eso
estas consultas piden siempre por número de capítulo y devuelven sus escenas dentro.
"""

from __future__ import annotations

import aiosqlite

from storymaker.commons.db.repos import id_insertado
from storymaker.commons.validation.puras import firmeza


async def capitulo_por_numero(db: aiosqlite.Connection, numero: int) -> aiosqlite.Row | None:
    async with db.execute("SELECT * FROM plan_capitulo WHERE numero = ?", (numero,)) as cursor:
        return await cursor.fetchone()


async def escenas_de(db: aiosqlite.Connection, numero: int) -> list[aiosqlite.Row]:
    async with db.execute(
        """
        SELECT e.*, c.numero AS capitulo_numero
          FROM plan_escena e
          JOIN plan_capitulo c ON c.id = e.capitulo_id
         WHERE c.numero = ?
         ORDER BY e.orden
        """,
        (numero,),
    ) as cursor:
        return list(await cursor.fetchall())


async def beats_de(db: aiosqlite.Connection, escena_id: int) -> list[aiosqlite.Row]:
    async with db.execute(
        "SELECT * FROM plan_beat WHERE escena_id = ? ORDER BY orden", (escena_id,)
    ) as cursor:
        return list(await cursor.fetchall())


async def personajes_de(db: aiosqlite.Connection, numero: int) -> list[aiosqlite.Row]:
    """Los personajes que la escaleta pone en las escenas de este capítulo."""
    async with db.execute(
        """
        SELECT DISTINCT p.*
          FROM plan_escena_personaje ep
          JOIN plan_escena e ON e.id = ep.escena_id
          JOIN plan_capitulo c ON c.id = e.capitulo_id
          JOIN canon_personaje p ON p.id = ep.personaje_id
         WHERE c.numero = ?
         ORDER BY p.id
        """,
        (numero,),
    ) as cursor:
        return list(await cursor.fetchall())


async def escenarios_de(db: aiosqlite.Connection, numero: int) -> list[aiosqlite.Row]:
    async with db.execute(
        """
        SELECT DISTINCT s.*
          FROM plan_escena e
          JOIN plan_capitulo c ON c.id = e.capitulo_id
          JOIN canon_escenario s ON s.id = e.escenario_id
         WHERE c.numero = ?
         ORDER BY s.id
        """,
        (numero,),
    ) as cursor:
        return list(await cursor.fetchall())


async def anclajes_de(db: aiosqlite.Connection, numero: int) -> list[aiosqlite.Row]:
    """Los anclajes explícitos de las escenas de este capítulo.

    Entran **siempre** en el bloque 5, antes que cualquier vecino semántico: son lo que el
    arquitecto decidió que este capítulo tiene que usar, y la búsqueda solo añade lo que no
    previó.
    """
    async with db.execute(
        """
        SELECT a.*, e.orden AS escena_orden,
               h.enunciado AS hecho_enunciado, h.estado AS hecho_estado,
               h.respaldo AS hecho_respaldo, h.origen AS hecho_origen,
               h.sin_respaldo AS hecho_sin_respaldo,
               h.dimension AS hecho_dimension,
               n.nombre AS entidad_nombre, n.nombre_epoca AS entidad_nombre_epoca,
               d.valor_json AS dato_valor, d.tipo AS dato_tipo, d.obligatorio AS dato_obligatorio
          FROM plan_anclaje a
          JOIN plan_escena e ON e.id = a.escena_id
          JOIN plan_capitulo c ON c.id = e.capitulo_id
          LEFT JOIN mundo_hecho h ON h.id = a.hecho_id
          LEFT JOIN mundo_entidad n ON n.id = a.entidad_id
          LEFT JOIN intake_dato d ON d.id = a.dato_id
         WHERE c.numero = ?
         ORDER BY e.orden, a.id
        """,
        (numero,),
    ) as cursor:
        return list(await cursor.fetchall())


async def hitos_de(db: aiosqlite.Connection, numero: int) -> list[aiosqlite.Row]:
    """Los hitos de arco anclados a escenas de este capítulo.

    Son lo que `arco_ejecutado` pregunta después: si el hito que le tocaba a este capítulo
    ocurrió. Viajan al bloque 1 porque el escritor tiene que saber qué le toca cerrar.
    """
    async with db.execute(
        """
        SELECT h.*, a.tipo AS arco_tipo, p.nombre AS personaje, e.orden AS escena_orden
          FROM canon_arco_hito h
          JOIN canon_arco a ON a.id = h.arco_id
          JOIN canon_personaje p ON p.id = a.personaje_id
          JOIN plan_escena e ON e.id = h.escena_id
          JOIN plan_capitulo c ON c.id = e.capitulo_id
         WHERE c.numero = ?
         ORDER BY e.orden, h.orden
        """,
        (numero,),
    ) as cursor:
        return list(await cursor.fetchall())


async def apariciones_por_personaje(db: aiosqlite.Connection) -> dict[int, int]:
    """En cuántas escenas sale cada personaje.

    Es lo que hace computable `arco_anclado`: «personaje principal» no es algo que el
    modelo de datos sepa responder, pero contar apariciones sí, y dice lo que interesa —de
    todo personaje que vuelve, alguien tuvo que decidir qué le pasa a lo largo de la obra—.
    """
    async with db.execute(
        """
        SELECT personaje_id, COUNT(DISTINCT escena_id) AS n
          FROM plan_escena_personaje
         GROUP BY personaje_id
        """
    ) as cursor:
        return {int(f["personaje_id"]): int(f["n"]) for f in await cursor.fetchall()}


async def capitulo_de_escena(db: aiosqlite.Connection, escena_id: int) -> int | None:
    async with db.execute(
        """
        SELECT c.numero
          FROM plan_escena e
          JOIN plan_capitulo c ON c.id = e.capitulo_id
         WHERE e.id = ?
        """,
        (escena_id,),
    ) as cursor:
        fila = await cursor.fetchone()
    return int(fila["numero"]) if fila is not None else None


async def total_de_capitulos(db: aiosqlite.Connection) -> int:
    async with db.execute("SELECT COUNT(*) AS n FROM plan_capitulo") as cursor:
        fila = await cursor.fetchone()
    return int(fila["n"]) if fila is not None else 0


async def escenas_por_capitulo(db: aiosqlite.Connection) -> list[tuple[int, int]]:
    """`(numero, escenas)` de cada capítulo de la escaleta, incluidos los que no tienen."""
    async with db.execute(
        """
        SELECT c.numero AS numero, COUNT(e.id) AS escenas
        FROM plan_capitulo AS c LEFT JOIN plan_escena AS e ON e.capitulo_id = c.id
        GROUP BY c.id ORDER BY c.numero
        """
    ) as cursor:
        return [(int(f["numero"]), int(f["escenas"])) for f in await cursor.fetchall()]


#: Las firmezas sobre las que una escena no debería apoyarse sola (arq. §4, Fase 3).
_POCO_FIRMES = frozenset({"inferido", "desconocido"})


async def escenas_poco_firmes(db: aiosqlite.Connection) -> list[tuple[int, int]]:
    """`(capitulo, orden)` de cada escena cuyos anclajes a hechos son todos poco firmes.

    Una escena sin anclajes a hechos no cuenta: puede apoyarse en un elemento del encargo o
    en una entidad de época, y eso no es asunto de la firmeza. Lo que se señala es la escena
    que sí se apoya en la historia y solo encuentra inferencias y lagunas debajo.
    """
    async with db.execute(
        """
        SELECT c.numero AS capitulo, e.orden AS orden,
               h.estado AS estado, h.respaldo AS respaldo, h.origen AS origen
          FROM plan_anclaje a
          JOIN plan_escena e ON e.id = a.escena_id
          JOIN plan_capitulo c ON c.id = e.capitulo_id
          JOIN mundo_hecho h ON h.id = a.hecho_id
        """
    ) as cursor:
        filas = list(await cursor.fetchall())
    firmezas: dict[tuple[int, int], set[str]] = {}
    for f in filas:
        clave = (int(f["capitulo"]), int(f["orden"]))
        firmezas.setdefault(clave, set()).add(
            firmeza(str(f["estado"]), str(f["respaldo"]), str(f["origen"]))
        )
    return sorted(clave for clave, vistas in firmezas.items() if vistas <= _POCO_FIRMES)


# --- Los huecos de la escaleta ------------------------------------------------------


async def registrar_hueco(
    db: aiosqlite.Connection,
    *,
    pregunta: str,
    dimension: str,
    escena_id: int | None,
    propuesta: str,
) -> int:
    """Un hueco que `FillGap` cubrirá. El estado del grafo solo lleva su identificador."""
    cursor = await db.execute(
        "INSERT INTO plan_hueco (escena_id, pregunta, dimension, propuesta) VALUES (?, ?, ?, ?)",
        (escena_id, pregunta, dimension, propuesta or None),
    )
    return id_insertado(cursor)


async def hueco(db: aiosqlite.Connection, hueco_id: int) -> aiosqlite.Row | None:
    async with db.execute("SELECT * FROM plan_hueco WHERE id = ?", (hueco_id,)) as cursor:
        return await cursor.fetchone()


async def cerrar_hueco(
    db: aiosqlite.Connection, hueco_id: int, *, hecho_id: int, resultado: str
) -> None:
    """Anota con qué hecho se cubrió y lo ancla a la escena que lo pedía, si la hay."""
    await db.execute(
        "UPDATE plan_hueco SET hecho_id = ?, resultado = ? WHERE id = ?",
        (hecho_id, resultado, hueco_id),
    )
    fila = await hueco(db, hueco_id)
    if fila is not None and fila["escena_id"] is not None:
        await db.execute(
            "INSERT INTO plan_anclaje (escena_id, hecho_id, tipo_vinculo) VALUES (?, ?, ?)",
            (int(fila["escena_id"]), hecho_id, "cubre un hueco de la escaleta"),
        )


async def huecos_de_la_trama(db: aiosqlite.Connection) -> list[aiosqlite.Row]:
    """Los huecos con su escena, su resultado y el enunciado con que quedaron cubiertos."""
    async with db.execute(
        """
        SELECT u.id, u.pregunta, u.dimension, u.resultado, h.enunciado,
               c.numero AS capitulo, e.orden AS escena
          FROM plan_hueco u
          LEFT JOIN plan_escena e ON e.id = u.escena_id
          LEFT JOIN plan_capitulo c ON c.id = e.capitulo_id
          LEFT JOIN mundo_hecho h ON h.id = u.hecho_id
         ORDER BY u.id
        """
    ) as cursor:
        return list(await cursor.fetchall())


async def anclar_dato(db: aiosqlite.Connection, escena_id: int, dato_id: int) -> None:
    await db.execute(
        "INSERT INTO plan_anclaje (escena_id, dato_id, tipo_vinculo) VALUES (?, ?, ?)",
        (escena_id, dato_id, "elemento del encargo, anclado por el arnes"),
    )


async def escenas_con_texto(db: aiosqlite.Connection) -> list[aiosqlite.Row]:
    """Cada escena con lo que dice de sí misma, para buscar la que mejor recibe un elemento."""
    async with db.execute(
        """
        SELECT e.id, c.numero AS capitulo, e.orden, e.fecha_narrativa,
               COALESCE(e.objetivo, '') || ' ' || COALESCE(e.conflicto, '') || ' ' ||
               COALESCE(e.resultado, '') AS texto
          FROM plan_escena e JOIN plan_capitulo c ON c.id = e.capitulo_id
         ORDER BY c.numero, e.orden
        """
    ) as cursor:
        return list(await cursor.fetchall())
