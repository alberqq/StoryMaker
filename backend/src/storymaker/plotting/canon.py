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
from storymaker.commons.validation.puras import anio_de
from storymaker.intake.contradicciones import EDAD_MINIMA_RAZONABLE
from storymaker.intake.esquemas import Brief
from storymaker.plotting.esquemas import SalidaArquitecto


def nacimiento_de_epoca(propuesta: str | None, brief: Brief) -> str | None:
    """La fecha de nacimiento del homenajeado **dentro de la novela** (arq. §4, Fase 3).

    El encargo puede traer la fecha real de la persona, y los briefs de ejemplo la traen: un
    homenajeado de 1958 en el Cádiz de 1805. Copiada al canon, dejaba al protagonista sin
    nacer en todas sus escenas, y la cronología de la publicación —que sí bloquea— no habría
    dejado publicar. Vale la del arquitecto si le da edad en el periodo; si no, la del
    encargo si se la da; y si ninguna, ninguna: sin fecha no hay restricción, que es mejor
    que una restricción falsa.
    """
    for candidata in (propuesta, brief.fecha_nacimiento):
        anio = anio_de(candidata)
        if anio is not None and brief.periodo.fin - anio >= EDAD_MINIMA_RAZONABLE:
            return candidata
    return None


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
                (
                    nacimiento_de_epoca(personaje.fecha_nacimiento, brief)
                    if personaje.es_homenajeado
                    else personaje.fecha_nacimiento
                ),
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
    """Los términos vetados, ya normalizados para que el guardrail compare rápido.

    A los del brief se suma la lista global del arnés, salvo los términos que el brief ya
    trae: una fila repetida daría dos incidencias por la misma palabra.
    """
    from storymaker.commons.validation.policy_checker import PROHIBIDAS_GLOBALES
    from storymaker.commons.validation.puras import normalizar

    filas = [(p.nivel.value, p.termino, normalizar(p.termino)) for p in brief.palabras_prohibidas]
    vistos = {normalizado for _, _, normalizado in filas}
    for termino in PROHIBIDAS_GLOBALES:
        normalizado = normalizar(termino)
        if normalizado not in vistos:
            vistos.add(normalizado)
            filas.append(("global", termino, normalizado))

    for fila in filas:
        await db.execute(
            "INSERT INTO canon_prohibida (nivel, termino, normalizado) VALUES (?, ?, ?)", fila
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
