"""spec: §4.1 · arq: §4, §7

Consultas sobre el encargo del comprador.

**La verdad son las filas, no el JSON del brief.** `intake_brief` guarda el `Brief`
serializado tal como se cerró en el gate y **no se consulta para decidir nada**: es la
fotografía que permite enseñar meses después qué se encargó exactamente. Lo vivo son las
filas de `intake_dato`, que se editan, se cuentan, se anclan y, si se borran, disparan la
invalidación.
"""

from __future__ import annotations

import aiosqlite

from storymaker.commons.db.repos import id_insertado


async def guardar_brief(
    db: aiosqlite.Connection, *, fase_run_id: int, json_brief: str, hash_brief: str
) -> int:
    """La fotografía auditable. No decide nada; sostiene la auditabilidad de §13."""
    cursor = await db.execute(
        "INSERT INTO intake_brief (fase_run_id, json, hash) VALUES (?, ?, ?)",
        (fase_run_id, json_brief, hash_brief),
    )
    return id_insertado(cursor)


async def guardar_texto_crudo(db: aiosqlite.Connection, texto: str) -> int:
    """Mete el texto pegado en la cuarentena. **De aquí no sale.**"""
    cursor = await db.execute("INSERT INTO intake_texto_crudo (texto) VALUES (?)", (texto,))
    return id_insertado(cursor)


async def existe_dato(
    db: aiosqlite.Connection, *, tipo: str, valor_json: str, origen: str
) -> bool:
    """Si el encargo ya tiene ese dato. Repetir la entrevista no lo escribe dos veces."""
    async with db.execute(
        "SELECT 1 FROM intake_dato WHERE tipo = ? AND valor_json = ? AND origen = ? LIMIT 1",
        (tipo, valor_json, origen),
    ) as cursor:
        return await cursor.fetchone() is not None


async def hay_texto_crudo(db: aiosqlite.Connection) -> bool:
    async with db.execute("SELECT 1 FROM intake_texto_crudo LIMIT 1") as cursor:
        return await cursor.fetchone() is not None


async def insertar_dato(
    db: aiosqlite.Connection,
    *,
    tipo: str,
    valor_json: str,
    origen: str,
    obligatorio: bool = False,
    texto_crudo_id: int | None = None,
) -> int:
    """Una fila tipada del encargo.

    Las que vienen de la cuarentena llevan `origen = 'texto_libre_no_confiable'` y su
    `texto_crudo_id`: la defensa contra inyección es estructural, porque una inyección
    tiene que sobrevivir a convertirse en una fila tipada para hacer daño, y no sobrevive.
    """
    cursor = await db.execute(
        """
        INSERT INTO intake_dato (texto_crudo_id, tipo, valor_json, origen, obligatorio)
        VALUES (?, ?, ?, ?, ?)
        """,
        (texto_crudo_id, tipo, valor_json, origen, int(obligatorio)),
    )
    return id_insertado(cursor)


async def datos(db: aiosqlite.Connection) -> list[aiosqlite.Row]:
    async with db.execute("SELECT * FROM intake_dato ORDER BY id") as cursor:
        return list(await cursor.fetchall())


async def obligatorios(db: aiosqlite.Connection) -> list[aiosqlite.Row]:
    """Los elementos que la novela tiene que tocar. Es lo que hace contable la cobertura."""
    async with db.execute(
        "SELECT * FROM intake_dato WHERE obligatorio = 1 ORDER BY id"
    ) as cursor:
        return list(await cursor.fetchall())


async def obligatorios_sin_anclar(db: aiosqlite.Connection) -> list[aiosqlite.Row]:
    """Los que ninguna escena de la escaleta recoge.

    Es `cobertura_anclada`, en el gate de Plotting: cuesta un `SELECT` y convierte un fallo
    de diez capítulos escritos y pagados en un fallo de escaleta.
    """
    async with db.execute(
        """
        SELECT d.*
          FROM intake_dato d
         WHERE d.obligatorio = 1
           AND NOT EXISTS (SELECT 1 FROM plan_anclaje a WHERE a.dato_id = d.id)
         ORDER BY d.id
        """
    ) as cursor:
        return list(await cursor.fetchall())


async def obligatorios_sin_usar(db: aiosqlite.Connection) -> list[aiosqlite.Row]:
    """Los que no aparecieron en ningún capítulo aprobado.

    Es `cobertura_personalizacion`, en el gate de Writing, y se queda como red de seguridad
    porque anclar no es escribir.
    """
    async with db.execute(
        """
        SELECT d.*
          FROM intake_dato d
         WHERE d.obligatorio = 1
           AND NOT EXISTS (
                 SELECT 1
                   FROM intake_uso_dato u
                   JOIN capitulo_version cv ON cv.id = u.capitulo_version_id
                  WHERE u.dato_id = d.id AND cv.estado = 'aprobado'
               )
         ORDER BY d.id
        """
    ) as cursor:
        return list(await cursor.fetchall())


async def datos_de_capitulo(db: aiosqlite.Connection, numero: int) -> list[aiosqlite.Row]:
    """Los elementos de personalización que la escaleta encomendó a este capítulo.

    Es lo que llena el bloque 7 del paquete, y contra lo que `cobertura_capitulo` comprueba
    después si aparecieron de verdad.
    """
    async with db.execute(
        """
        SELECT DISTINCT d.*
          FROM plan_anclaje a
          JOIN plan_escena e ON e.id = a.escena_id
          JOIN plan_capitulo c ON c.id = e.capitulo_id
          JOIN intake_dato d ON d.id = a.dato_id
         WHERE c.numero = ?
         ORDER BY d.id
        """,
        (numero,),
    ) as cursor:
        return list(await cursor.fetchall())


async def registrar_uso(
    db: aiosqlite.Connection,
    *,
    capitulo_version_id: int,
    escena_id: int,
    dato_id: int,
    tipo_uso: str = "mencion",
) -> None:
    """Lo escribe el extractor independiente, no quien redactó el capítulo."""
    await db.execute(
        """
        INSERT OR REPLACE INTO intake_uso_dato (capitulo_version_id, escena_id, dato_id, tipo_uso)
        VALUES (?, ?, ?, ?)
        """,
        (capitulo_version_id, escena_id, dato_id, tipo_uso),
    )
