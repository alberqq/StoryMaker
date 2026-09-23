"""spec: §3.1 · arq: §7, §8

Consultas sobre el estado del sistema: ejecuciones de fase, gates, incidencias, scores y
audit log. Nadie fuera de `commons/db` construye SQL contra estas tablas.

Una `fase_run` se abre cuando la fase empieza y se cierra cuando termina, con su consumo
y su hora de fin. Entre medias es inmutable en todo lo demás: qué fase es, de qué
ejecución salió y con qué prompt se hizo no cambian nunca, y el trigger lo impide.
"""

from __future__ import annotations

import json
from typing import Any

import aiosqlite

from storymaker.commons.db.repos import id_insertado


async def abrir_fase_run(
    db: aiosqlite.Connection,
    fase: str,
    *,
    input_run_id: int | None = None,
    prompt_nombre: str | None = None,
    prompt_version: str | None = None,
    modelo: str | None = None,
    trace_id: str | None = None,
) -> int:
    """Registra el comienzo de una fase y devuelve su identificador.

    `input_run_id` es lo que convierte la cadena de fases en un grafo: apunta a la
    ejecución que le sirvió de entrada, y es lo que hace que rehacer, reanudar, ramificar
    y regenerar sean la misma operación con distinto punto de entrada.
    """
    cursor = await db.execute(
        """
        INSERT INTO fase_run (fase, estado, input_run_id, prompt_nombre, prompt_version,
                              modelo, trace_id)
        VALUES (?, 'en_curso', ?, ?, ?, ?, ?)
        """,
        (fase, input_run_id, prompt_nombre, prompt_version, modelo, trace_id),
    )
    return id_insertado(cursor)


async def cerrar_fase_run(
    db: aiosqlite.Connection,
    fase_run_id: int,
    *,
    estado: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    coste_usd: float = 0.0,
    artefacto_hash: str | None = None,
) -> None:
    """Cierra la ejecución con su estado final y su consumo.

    El coste es una estimación en cliente, no facturación (U-7), y se etiqueta como tal
    en todas las salidas que lo enseñan.
    """
    await db.execute(
        """
        UPDATE fase_run
           SET estado = ?, tokens_in = ?, tokens_out = ?, coste_usd = ?,
               artefacto_hash = COALESCE(?, artefacto_hash), fin = datetime('now')
         WHERE id = ?
        """,
        (estado, tokens_in, tokens_out, coste_usd, artefacto_hash, fase_run_id),
    )


async def abrir_gate(db: aiosqlite.Connection, fase_run_id: int) -> int:
    """Deja el gate pendiente. A partir de aquí la máquina duerme en disco."""
    cursor = await db.execute(
        """
        INSERT INTO gate (fase_run_id, estado, notificado_en)
        VALUES (?, 'pendiente', datetime('now'))
        """,
        (fase_run_id,),
    )
    return id_insertado(cursor)


async def decidir_gate(
    db: aiosqlite.Connection,
    gate_id: int,
    *,
    decision: str,
    comentario: str | None = None,
    decidido_por: str = "autor",
) -> None:
    """Anota la decisión del Autor. Queda trazada igual que la de un agente."""
    await db.execute(
        """
        UPDATE gate
           SET estado = 'decidido', decision = ?, comentario = ?, decidido_por = ?,
               decidido_en = datetime('now')
         WHERE id = ?
        """,
        (decision, comentario, decidido_por, gate_id),
    )


async def gate_pendiente(db: aiosqlite.Connection) -> aiosqlite.Row | None:
    async with db.execute(
        "SELECT * FROM gate WHERE estado = 'pendiente' ORDER BY id DESC LIMIT 1"
    ) as cursor:
        return await cursor.fetchone()


async def registrar_incidencia(
    db: aiosqlite.Connection,
    *,
    validador: str,
    severidad: str,
    mensaje: str,
    capitulo_version_id: int | None = None,
    ubicacion: str | None = None,
    propuesta: str | None = None,
) -> int:
    """Un defecto del contenido, que tiene camino de vuelta. No es un error del sistema."""
    cursor = await db.execute(
        """
        INSERT INTO incidencia (capitulo_version_id, validador, severidad, ubicacion,
                                mensaje, propuesta)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (capitulo_version_id, validador, severidad, ubicacion, mensaje, propuesta),
    )
    return id_insertado(cursor)


async def incidencias_de(
    db: aiosqlite.Connection, capitulo_version_id: int, *, solo_bloqueantes: bool = False
) -> list[aiosqlite.Row]:
    consulta = "SELECT * FROM incidencia WHERE capitulo_version_id = ?"
    if solo_bloqueantes:
        consulta += " AND severidad = 'bloqueante'"
    async with db.execute(consulta + " ORDER BY id", (capitulo_version_id,)) as cursor:
        return list(await cursor.fetchall())


async def registrar_score(
    db: aiosqlite.Connection,
    *,
    objeto_tipo: str,
    objeto_id: int,
    validador: str,
    valor: float,
    detalle: dict[str, Any] | None = None,
) -> None:
    await db.execute(
        """
        INSERT INTO score (objeto_tipo, objeto_id, validador, valor, detalle_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (objeto_tipo, objeto_id, validador, valor, json.dumps(detalle) if detalle else None),
    )


async def registrar_audit(
    db: aiosqlite.Connection,
    *,
    actor: str,
    accion: str,
    objeto: str,
    antes: Any = None,
    despues: Any = None,
) -> None:
    """Toda decisión de policy, de gate y toda edición humana pasa por aquí (arq. §15)."""
    await db.execute(
        """
        INSERT INTO audit_log (actor, accion, objeto, antes_json, despues_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            actor,
            accion,
            objeto,
            json.dumps(antes) if antes is not None else None,
            json.dumps(despues) if despues is not None else None,
        ),
    )


async def comentarios_de_rehacer(db: aiosqlite.Connection, fase: str) -> list[str]:
    """Los comentarios de todos los gates de una fase decididos como «rehacer», en orden.

    En Intake son las respuestas del Autor a la entrevista: `Configure` las recibe todas
    en cada vuelta, porque el entrevistador no guarda memoria entre una y otra.
    """
    async with db.execute(
        """
        SELECT g.comentario FROM gate AS g JOIN fase_run AS f ON f.id = g.fase_run_id
        WHERE f.fase = ? AND g.decision = 'rehacer' AND g.comentario IS NOT NULL
        ORDER BY g.id
        """,
        (fase,),
    ) as cursor:
        return [str(fila["comentario"]) for fila in await cursor.fetchall()]


async def retirar_incidencias_sin_capitulo(db: aiosqlite.Connection, validador: str) -> None:
    """Retira las incidencias de un validador que no cuelgan de ningún capítulo.

    Sirve a las preguntas del entrevistador: una vuelta nueva de la entrevista sustituye
    las preguntas de la anterior, que ya están contestadas o reformuladas.
    """
    await db.execute(
        "DELETE FROM incidencia WHERE validador = ? AND capitulo_version_id IS NULL",
        (validador,),
    )


async def incidencias_sin_capitulo(db: aiosqlite.Connection, validador: str) -> list[str]:
    async with db.execute(
        "SELECT mensaje FROM incidencia WHERE validador = ? AND capitulo_version_id IS NULL "
        "ORDER BY id",
        (validador,),
    ) as cursor:
        return [str(fila["mensaje"]) for fila in await cursor.fetchall()]
