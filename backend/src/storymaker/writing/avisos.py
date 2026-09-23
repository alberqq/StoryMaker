"""spec: §4.4, §7.2 · arq: §11b, §19

Qué pasa con los avisos de ejecución: **viajan al capítulo siguiente**.

Ese viaje es lo que los distingue de un simple apunte. Sin él, detectar en el capítulo 4
que un hito no ocurrió solo adelantaría la mala noticia. Con él, la corrección entra por
donde entra todo lo demás en este sistema —el paquete de contexto ensamblado desde SQLite—
y no hace falta ni un gate nuevo ni una arista nueva.

**Viajan los tres más recientes, no todos.** El bloque 1 es el encargo, y es el bloque que
nunca debería recortarse; un capítulo que arrastrase siete avisos se los comería. Además, un
capítulo con siete avisos no tiene un problema de contexto sino de escritura, y volcárselos
enteros al escritor siguiente no lo arregla.

**En el último capítulo el aviso no viaja a ninguna parte, y es justo donde más importa.**
No hay capítulo N+1, y es donde cierra el arco del homenajeado, así que es donde
`arco_ejecutado` tiene más probabilidad de saltar. Ahí el aviso se convierte en entrada
destacada del informe del gate de Writing, con el hito concreto que falta escrito en el
mensaje.
"""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite

from storymaker.commons.config import Defaults
from storymaker.commons.db.repos import arnes, plan, texto


@dataclass(frozen=True)
class AvisoDestacado:
    """Un aviso del último capítulo, que no tiene adónde viajar."""

    capitulo: int
    validador: str
    mensaje: str


async def pendientes_para(db: aiosqlite.Connection, numero: int) -> list[str]:
    """Los tres avisos más recientes del capítulo anterior, para el bloque 1 del paquete."""
    if numero <= 1:
        return []
    anterior = await plan.capitulo_por_numero(db, numero - 1)
    if anterior is None:
        return []
    version = await texto.capitulo_aprobado(db, int(anterior["id"]))
    if version is None:
        return []
    incidencias = await arnes.incidencias_de(db, int(version["id"]))
    avisos = [i for i in incidencias if i["severidad"] == "aviso"]
    return [str(i["mensaje"]) for i in avisos[-Defaults.AVISOS_QUE_VIAJAN_AL_SIGUIENTE :]]


async def del_ultimo_capitulo(db: aiosqlite.Connection) -> list[AvisoDestacado]:
    """Los avisos que no pudieron viajar. Se destacan en el informe del gate de Writing.

    No bloquean —seguiría siendo el juicio de un modelo gastando reintentos en la peor
    esquina para hacerlo—, pero llegan a la única persona que puede decidir si importan, que
    es donde este sistema pone siempre esa clase de decisión.
    """
    total = await plan.total_de_capitulos(db)
    if total == 0:
        return []
    ultimo = await plan.capitulo_por_numero(db, total)
    if ultimo is None:
        return []
    version = await texto.capitulo_aprobado(db, int(ultimo["id"]))
    if version is None:
        return []
    return [
        AvisoDestacado(
            capitulo=total,
            validador=str(i["validador"]),
            mensaje=str(i["mensaje"]),
        )
        for i in await arnes.incidencias_de(db, int(version["id"]))
        if i["severidad"] == "aviso"
    ]


async def todos_los_avisos(db: aiosqlite.Connection) -> list[tuple[int, str]]:
    """Todos los avisos de los capítulos aprobados, para el informe del gate."""
    async with db.execute(
        """
        SELECT pc.numero, i.mensaje
          FROM incidencia i
          JOIN capitulo_version cv ON cv.id = i.capitulo_version_id
          JOIN plan_capitulo pc ON pc.id = cv.capitulo_id
         WHERE i.severidad = 'aviso' AND cv.estado = 'aprobado'
         ORDER BY pc.numero, i.id
        """
    ) as cursor:
        return [(int(f["numero"]), str(f["mensaje"])) for f in await cursor.fetchall()]
