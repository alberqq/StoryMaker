"""spec: §4.4 · arq: §4, §7

Vuelca lo que el extractor midió: los índices, la continuidad y la cronología narrativa.

**Todas estas filas cuelgan del intento, no del capítulo.** `uso_hecho`, `uso_hito`,
`intake_uso_dato` y `continuidad` se escriben con el `capitulo_version_id` del intento que
las produjo, así que las de un intento descartado quedan colgando de una versión que nunca
se aprueba y que ningún manifiesto recoge. No hace falta marcarlas ni borrarlas: la
inmutabilidad ya las deja fuera.

`uso_hecho` registra a granularidad de **escena**; la consulta de regeneración lo agrega a
capítulo, que es la unidad de reescritura. `uso_hito` es su gemelo para el arco, y existe
por la misma razón: sin él, mover un hito del capítulo 8 al 5 no invalidaría nada.
"""

from __future__ import annotations

import json

import aiosqlite

from storymaker.commons.db.repos import id_insertado, intake, plan, texto
from storymaker.writing.esquemas import SalidaExtractorDeCapitulo


async def _escenas_por_orden(db: aiosqlite.Connection, numero: int) -> dict[int, int]:
    """Orden dentro del capítulo → identificador. El extractor habla de escenas por orden."""
    return {int(e["orden"]): int(e["id"]) for e in await plan.escenas_de(db, numero)}


async def volcar(
    db: aiosqlite.Connection,
    salida: SalidaExtractorDeCapitulo,
    *,
    capitulo_version_id: int,
    numero: int,
) -> None:
    """Escribe todo lo que el extractor midió, con el intento como dueño."""
    escenas = await _escenas_por_orden(db, numero)

    for uso in salida.hechos_usados:
        escena_id = escenas.get(uso.escena)
        if escena_id is None:
            continue
        await texto.registrar_uso_hecho(
            db,
            capitulo_version_id=capitulo_version_id,
            escena_id=escena_id,
            hecho_id=uso.hecho_id,
            tipo_uso=uso.tipo_uso,
        )

    for elemento in salida.elementos_usados:
        escena_id = escenas.get(elemento.escena)
        if escena_id is None:
            continue
        await intake.registrar_uso(
            db,
            capitulo_version_id=capitulo_version_id,
            escena_id=escena_id,
            dato_id=elemento.dato_id,
        )

    for hito in salida.veredicto.hitos_ejecutados:
        escena_id = await _escena_del_hito(db, hito)
        if escena_id is not None:
            await texto.registrar_uso_hito(
                db,
                capitulo_version_id=capitulo_version_id,
                escena_id=escena_id,
                hito_id=hito,
                ejecutado=True,
            )
    for hito in salida.veredicto.hitos_pendientes:
        escena_id = await _escena_del_hito(db, hito)
        if escena_id is not None:
            await texto.registrar_uso_hito(
                db,
                capitulo_version_id=capitulo_version_id,
                escena_id=escena_id,
                hito_id=hito,
                ejecutado=False,
            )

    for estado in salida.continuidad:
        await texto.insertar_continuidad(
            db,
            capitulo_version_id=capitulo_version_id,
            personaje_id=estado.personaje_id,
            escenario_id=estado.escenario_id,
            fecha_narrativa=estado.fecha_narrativa or None,
            conocimiento_json=json.dumps(estado.conocimiento, ensure_ascii=False),
            posesiones_json=json.dumps(estado.posesiones, ensure_ascii=False),
            estado_json=json.dumps(estado.estado, ensure_ascii=False),
        )

    await volcar_cronologia(db, salida, capitulo_version_id=capitulo_version_id, numero=numero)


async def _escena_del_hito(db: aiosqlite.Connection, hito_id: int) -> int | None:
    async with db.execute(
        "SELECT escena_id FROM canon_arco_hito WHERE id = ?", (hito_id,)
    ) as cursor:
        fila = await cursor.fetchone()
    return int(fila["escena_id"]) if fila is not None and fila["escena_id"] is not None else None


async def volcar_cronologia(
    db: aiosqlite.Connection,
    salida: SalidaExtractorDeCapitulo,
    *,
    capitulo_version_id: int,
    numero: int,
) -> list[int]:
    """Las filas `narrativo` de la cronología. **Nadie más sabe qué ocurrió en esa prosa.**

    Es la razón entera de que Lean corra en la pasada del extractor: antes de esta escritura,
    la cronología del capítulo N no existe, y verificarla sería verificar hasta N-1.
    """
    escenas = await _escenas_por_orden(db, numero)
    identificadores = []

    for evento in salida.eventos:
        cursor = await db.execute(
            """
            INSERT OR IGNORE INTO cronologia_evento
                (clave, descripcion, momento, origen, capitulo_version_id)
            VALUES (?, ?, ?, 'narrativo', ?)
            """,
            (
                f"cap{numero}-{evento.clave}",
                evento.descripcion,
                evento.momento,
                capitulo_version_id,
            ),
        )
        evento_id = cursor.lastrowid
        if not evento_id:
            continue
        identificadores.append(int(evento_id))
        for personaje_id in evento.participantes:
            await db.execute(
                """
                INSERT OR IGNORE INTO cronologia_participante (evento_id, personaje_id)
                VALUES (?, ?)
                """,
                (evento_id, personaje_id),
            )
        # La escena queda implícita en la clave; no se guarda columna propia porque el
        # modelo de §7 no la tiene y añadirla por comodidad sería cambiar el esquema desde
        # abajo, que es justo lo que este proyecto no hace.
        _ = escenas
    return identificadores


async def guardar_resumen(
    db: aiosqlite.Connection, capitulo_version_id: int, resumen: str
) -> None:
    """El resumen es lo único del extractor que se escribe **en la fila del capítulo**.

    Y es el único `UPDATE` que el *trigger* de inmutabilidad permite sobre columnas que no
    son el estado, porque el resumen no es contenido generado por el escritor: lo mide otro
    agente después, y sin él el bloque 4 del paquete no tendría qué indexar.
    """
    await db.execute(
        "UPDATE capitulo_version SET resumen = ? WHERE id = ?", (resumen, capitulo_version_id)
    )


async def contar_filas_del_intento(db: aiosqlite.Connection, capitulo_version_id: int) -> int:
    """Cuántas filas dejó un intento. Sirve para comprobar que las descartadas quedan fuera."""
    total = 0
    for tabla in ("uso_hecho", "uso_hito", "intake_uso_dato", "continuidad"):
        async with db.execute(
            f"SELECT COUNT(*) AS n FROM {tabla} WHERE capitulo_version_id = ?",  # noqa: S608
            (capitulo_version_id,),
        ) as cursor:
            fila = await cursor.fetchone()
        total += int(fila["n"]) if fila is not None else 0
    return total


async def id_insertado_de(cursor: aiosqlite.Cursor) -> int:
    return id_insertado(cursor)
