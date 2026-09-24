"""spec: §4.3 · arq: §4, §7, §16.2

Vuelca a la base lo que el arquitecto entrega: el canon y la escaleta.

Dos cosas que este módulo hace y conviene señalar. La primera es que **copia los diales de
la frontera a `canon_obra.estilo_json`**: `grado_licencia`, `arcaismo` y
`contenido_admisible` no los lee ningún validador por sí solos, y aun así son obligatorios
porque son la política contra la que el juez puntúa. Este volcado es cómo llegan al bloque
6 del paquete y, por tanto, a quien escribe.

La segunda es que **indexa lo que escribe**. El canon es biblia viva: si el índice no se
escribiera con la fila, la búsqueda semántica seguiría devolviendo el texto anterior en
cuanto el Autor corrigiera una ficha en un gate.
"""

from __future__ import annotations

import json

import aiosqlite

from storymaker.commons.db.repos import id_insertado
from storymaker.commons.embeddings import indice
from storymaker.commons.embeddings.modelo import Vectorizador
from storymaker.intake.esquemas import Brief
from storymaker.plotting.esquemas import SalidaArquitecto


async def volcar_canon(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    salida: SalidaArquitecto,
    brief: Brief,
    *,
    fase_run_id: int | None = None,
) -> dict[str, int]:
    """Escribe personajes, arcos, escenarios y glosario. Devuelve nombre → identificador.

    `fase_run_id` es la ejecución que escribe la trama, y queda en `canon_obra`: es lo que
    permite a `Plan` distinguir una vuelta de un hueco de un «rehacer» del Autor.
    """
    por_nombre: dict[str, int] = {}

    for personaje in salida.personajes:
        # El nombre del homenajeado lo fija el encargo, no el arquitecto (arq. §3): si lo
        # abrevia, `nombres_exactos` compararía contra la abreviatura y el nombre completo
        # no se exigiría nunca. Su clave en la escaleta sigue siendo la del arquitecto.
        nombre = brief.nombre_homenajeado if personaje.es_homenajeado else personaje.nombre
        cursor = await db.execute(
            """
            INSERT INTO canon_personaje
                (nombre, tipo, objetivo, miedo, voz, estatus, fecha_nacimiento, fecha_muerte)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nombre,
                personaje.tipo.value,
                personaje.objetivo,
                personaje.miedo,
                personaje.voz,
                personaje.estatus,
                personaje.fecha_nacimiento,
                personaje.fecha_muerte,
            ),
        )
        identificador = id_insertado(cursor)
        por_nombre[personaje.nombre] = identificador
        await indice.indexar_canon(
            db,
            vectorizador,
            tabla="canon_personaje",
            fila_id=identificador,
            texto=f"{nombre} {personaje.estatus} {personaje.objetivo} {personaje.voz}",
            familia="personaje",
        )

    escenarios: dict[str, int] = {}
    for escenario in salida.escenarios:
        cursor = await db.execute(
            "INSERT INTO canon_escenario (descripcion) VALUES (?)", (escenario.descripcion,)
        )
        identificador = id_insertado(cursor)
        escenarios[escenario.clave] = identificador
        await indice.indexar_canon(
            db,
            vectorizador,
            tabla="canon_escenario",
            fila_id=identificador,
            texto=escenario.descripcion,
            familia="escenario",
        )

    for termino in salida.glosario:
        cursor = await db.execute(
            "INSERT INTO canon_glosario (termino, significado, registro) VALUES (?, ?, ?)",
            (termino.termino, termino.significado, termino.registro),
        )
        await indice.indexar_canon(
            db,
            vectorizador,
            tabla="canon_glosario",
            fila_id=id_insertado(cursor),
            texto=f"{termino.termino}: {termino.significado}",
            familia="glosario",
        )

    homenajeado = salida.homenajeado
    await db.execute(
        """
        INSERT INTO canon_obra
            (titulo, premisa, tema, genero, n_capitulos, palabras_por_capitulo, voz,
             estilo_json, homenajeado_id, fase_run_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            salida.titulo or None,
            salida.premisa,
            salida.tema,
            brief.genero,
            brief.n_capitulos,
            brief.palabras_por_capitulo,
            salida.voz or None,
            json.dumps(brief.diales, ensure_ascii=False),
            por_nombre.get(homenajeado.nombre) if homenajeado else None,
            fase_run_id,
        ),
    )

    await volcar_prohibidas(db, brief)
    return {**por_nombre, **{f"escenario:{k}": v for k, v in escenarios.items()}}


async def volcar_prohibidas(db: aiosqlite.Connection, brief: Brief) -> None:
    """Los términos vetados, ya normalizados para que el guardrail compare rápido."""
    from storymaker.commons.validation.puras import normalizar

    for prohibida in brief.palabras_prohibidas:
        await db.execute(
            "INSERT INTO canon_prohibida (nivel, termino, normalizado) VALUES (?, ?, ?)",
            (prohibida.nivel.value, prohibida.termino, normalizar(prohibida.termino)),
        )


async def volcar_arcos(
    db: aiosqlite.Connection, salida: SalidaArquitecto, personajes: dict[str, int],
    escenas: dict[str, int],
) -> None:
    """Escribe los arcos con sus hitos anclados a escenas.

    Un hito sin escena se escribe igualmente, con `escena_id` nulo: `arco_anclado` lo
    detectará en el gate, que es donde tiene arreglo barato. Rechazarlo aquí convertiría un
    despiste del arquitecto en una excepción a mitad de volcado.
    """
    for arco in salida.arcos:
        personaje_id = personajes.get(arco.personaje)
        if personaje_id is None:
            continue
        cursor = await db.execute(
            """
            INSERT INTO canon_arco (personaje_id, tipo, estado_inicial, estado_final)
            VALUES (?, ?, ?, ?)
            """,
            (personaje_id, arco.tipo.value, arco.estado_inicial, arco.estado_final),
        )
        arco_id = id_insertado(cursor)
        for hito in arco.hitos:
            await db.execute(
                """
                INSERT INTO canon_arco_hito (arco_id, orden, descripcion, escena_id)
                VALUES (?, ?, ?, ?)
                """,
                (arco_id, hito.orden, hito.descripcion, escenas.get(hito.escena)),
            )
