"""spec: §4.3 · arq: §4, §10

Detalla `specs/trama-rehacible/spec.md` §2.

Rehacer la Trama: **cuándo se replanifica, qué se borra y qué se le cuenta al arquitecto**.

`Plan` tiene dos aristas de entrada que no significan lo mismo. Desde `FillGap` es una
vuelta dentro de la misma ejecución, y replanificar ahí duplicaría la escaleta a cambio de
nada. Desde el gate de Plotting, tras «rehacer» o «editar», el Autor ha pedido otra trama, y
no replanificar es ignorarle: el gate volvía a abrirse idéntico. Lo que las separa es un dato
de la base y no del estado del grafo —**el gate decidido después de escribir la trama**—,
de modo que reanudar tras un fallo, que no pasa por el gate, no replanifica.

Rehacer **sustituye** la trama en lugar de versionarla. Antes del sello nada la usa todavía
—ni un capítulo escrito ni una cronología extraída—, y llevar `fase_run_id` en las catorce
tablas de canon y escaleta para conservar la anterior costaría más que lo que protege. Lo que
sí se conserva es lo que el Autor tocó: la trama anterior, con sus correcciones del gate,
llega al arquitecto como punto de partida, junto con su comentario y los avisos de la
revisión.
"""

from __future__ import annotations

import aiosqlite

from storymaker.commons.db.repos import canon, plan

#: Las tablas de la trama en orden de borrado: cada una antes de aquellas a las que apunta.
#: `canon_obra` va antes que los personajes porque referencia al homenajeado.
_TABLAS_EN_ORDEN_DE_BORRADO = (
    "plan_hueco",
    "canon_arco_hito",
    "canon_arco",
    "plan_anclaje",
    "plan_beat",
    "plan_escena_personaje",
    "canon_obra",
    "plan_escena",
    "plan_capitulo",
    "canon_relacion",
    "canon_licencia",
    "canon_glosario",
    "canon_prohibida",
    "canon_escenario",
    "canon_personaje",
)


async def hay_que_planificar(db: aiosqlite.Connection) -> bool:
    """Si `Plan` tiene que llamar al arquitecto o solo volver al bucle de huecos.

    Se planifica cuando no hay trama, y cuando hay un gate de Plotting decidido como
    «rehacer» o «editar» en la ejecución que la escribió o en una posterior. Una trama sin
    dueño —escrita antes de que `canon_obra` lo llevara— se rehace si hubo cualquier
    «rehacer» de Plotting, porque la nueva ya nace con dueño y la pregunta no se repite.
    """
    obra = await canon.obra(db)
    if obra is None:
        return True
    dueno = obra["fase_run_id"]
    async with db.execute(
        """
        SELECT 1 FROM gate g JOIN fase_run f ON f.id = g.fase_run_id
         WHERE f.fase = 'plotting' AND g.decision IN ('rehacer', 'editar')
           AND (? IS NULL OR g.fase_run_id >= ?)
         LIMIT 1
        """,
        (dueno, dueno),
    ) as cursor:
        return await cursor.fetchone() is not None


async def hay_trama(db: aiosqlite.Connection) -> bool:
    return await canon.obra(db) is not None or await plan.total_de_capitulos(db) > 0


async def borrar(db: aiosqlite.Connection) -> None:
    """Quita la trama entera, canon incluido, con su índice semántico.

    Solo es posible antes del sello: después, los capítulos escritos apuntan a escenas y a
    personajes, y las claves foráneas abortan el borrado, que es lo que tiene que pasar.
    """
    for tabla in _TABLAS_EN_ORDEN_DE_BORRADO:
        await db.execute(f"DELETE FROM {tabla}")  # noqa: S608 - nombres fijos de este módulo
    await db.execute("DELETE FROM vec_canon")


async def como_texto(db: aiosqlite.Connection) -> str:
    """La trama vigente, resumida para que el arquitecto la tenga delante al rehacerla.

    Va lo que el Autor pudo corregir en el gate —las fichas de personaje— tal como quedó,
    y de la escaleta solo el esqueleto: título y función de cada capítulo y el objetivo de
    cada escena. Con eso el arquitecto sabe qué conservar; la escaleta entera no cabría en
    su techo de contexto junto al corpus.
    """
    lineas: list[str] = []
    obra = await canon.obra(db)
    if obra is not None:
        if obra["titulo"]:
            lineas.append(f"Titulo: {obra['titulo']}")
        lineas.append(f"Premisa: {obra['premisa'] or ''}")
        lineas.append(f"Tema: {obra['tema'] or ''}")

    async with db.execute(
        "SELECT nombre, tipo, estatus, objetivo, miedo, voz FROM canon_personaje ORDER BY id"
    ) as cursor:
        personajes = list(await cursor.fetchall())
    if personajes:
        lineas.append("Personajes:")
        for p in personajes:
            detalle = "; ".join(
                f"{campo}: {p[campo]}"
                for campo in ("estatus", "objetivo", "miedo", "voz")
                if p[campo]
            )
            lineas.append(f"- {p['nombre']} ({p['tipo']}){': ' + detalle if detalle else ''}")

    async with db.execute(
        """
        SELECT c.numero, c.titulo, c.funcion, e.orden, e.objetivo
          FROM plan_capitulo c LEFT JOIN plan_escena e ON e.capitulo_id = c.id
         ORDER BY c.numero, e.orden
        """
    ) as cursor:
        filas = list(await cursor.fetchall())
    if filas:
        lineas.append("Escaleta:")
        actual = None
        for f in filas:
            if f["numero"] != actual:
                actual = f["numero"]
                cabeza = f"Capitulo {f['numero']}"
                if f["titulo"]:
                    cabeza += f". {f['titulo']}"
                if f["funcion"]:
                    cabeza += f" — {f['funcion']}"
                lineas.append(cabeza)
            if f["orden"] is not None:
                lineas.append(f"  escena {f['orden']}: {f['objetivo'] or ''}")
    return "\n".join(lineas)
