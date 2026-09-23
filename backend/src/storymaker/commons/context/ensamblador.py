"""spec: §3.4 · arq: §2, §6

**El corazón del arnés, y conviene que no tenga nada de inteligente.**

El escritor no tiene herramientas de recuperación: recibe un paquete montado por este
módulo, que lee SQLite y los índices semánticos y devuelve siempre la misma estructura de
siete bloques. Si la recuperación la hiciera el agente, cada capítulo recibiría un contexto
distinto y la estabilidad métrica dejaría de ser sostenible.

Que aquí se busque por similitud no rompe el principio del §2, y el matiz importa: **la
recuperación la hace el ensamblador, con una consulta derivada mecánicamente de la
escaleta, no el agente decidiendo sobre la marcha**. FastEmbed corre en local con el modelo
fijado, el corpus está sellado y la búsqueda de `sqlite-vec` es exhaustiva, así que con las
mismas entradas salen los mismos vecinos, siempre.
"""

from __future__ import annotations

import aiosqlite

from storymaker.commons.config import Settings
from storymaker.commons.context import bloques as constructores
from storymaker.commons.context.paquete import Paquete
from storymaker.commons.context.truncado import ajustar_al_total, ajustar_bloque
from storymaker.commons.db.repos import plan
from storymaker.commons.embeddings.modelo import Vectorizador
from storymaker.commons.errores import EscaletaAusente


async def ensamblar(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    capitulo_n: int,
    *,
    settings: Settings,
) -> Paquete:
    """Monta el paquete del capítulo N.

    Un bloque vacío no es un error: el capítulo 1 no tiene memoria de N-1 ni continuidad, y
    el paquete lo refleja. Lo que sí es un error es que falte la escaleta del capítulo
    pedido, que aborta la invocación en lugar de dejar que alguien genere a ciegas.
    """
    if await plan.capitulo_por_numero(db, capitulo_n) is None:
        raise EscaletaAusente(
            f"La escaleta no contempla el capitulo {capitulo_n}: no hay encargo que entregar."
        )

    crudos = [
        await constructores.encargo(db, capitulo_n, settings),
        await constructores.canon_relevante(db, vectorizador, capitulo_n, settings),
        await constructores.continuidad(db, capitulo_n),
        await constructores.memoria(db, vectorizador, capitulo_n, settings),
        await constructores.anclajes(db, vectorizador, capitulo_n, settings),
        await constructores.reglas(db),
        await constructores.personalizacion(db, capitulo_n),
    ]

    # Primero cada bloque contra su propio techo, y solo después el total: así un bloque
    # generoso no se come el sitio de otro antes de que nadie haya mirado el conjunto.
    porsi = [ajustar_bloque(b) for b in crudos]
    return Paquete(capitulo=capitulo_n, bloques=tuple(ajustar_al_total(porsi)))


async def persistir(
    db: aiosqlite.Connection,
    paquete: Paquete,
    *,
    capitulo_version_id: int | None = None,
    intento: int = 1,
    trace_span: str | None = None,
) -> int:
    """Guarda el paquete entero y devuelve su identificador.

    Cuesta casi nada y vale mucho: poder abrir, delante del evaluador, literalmente lo que
    el modelo vio cuando escribió el capítulo 7 es la definición operativa de «interpretable»
    en este sistema. El identificador viaja después al span de Langfuse.
    """
    from storymaker.commons.db.repos import id_insertado

    cursor = await db.execute(
        """
        INSERT INTO paquete_contexto (capitulo_version_id, capitulo_numero, intento, texto,
                                      tokens, trace_span)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            capitulo_version_id,
            paquete.capitulo,
            intento,
            paquete.texto(),
            paquete.tokens(),
            trace_span,
        ),
    )
    return id_insertado(cursor)
