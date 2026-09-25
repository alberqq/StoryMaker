"""spec: §4.6 · arq: §4, §11c

Detalla `specs/escritura/spec.md` §9.

La revisión de coste cero de los capítulos que la Fase 6 dejó en `Invalidado`.

Es la mitad barata de la política: a los posteriores que no usan lo que cambió se les corren
**solo** los validadores que no cuestan un token —la pasada determinista y la cronología, que
calcula Lean o, sin `lake`, Python— sobre las filas que ya tienen escritas desde que se
aprobaron. Ni el escritor ni el extractor intervienen. El que pasa vuelve a `aprobado`; el
que no, se devuelve para que la regeneración lo reescriba por el camino de siempre.

Se revisan **en orden y de uno en uno**, y el que vuelve a `aprobado` entra en la cronología
con la que se revisa el siguiente: es la misma acumulación que hace la pasada del extractor.
"""

from __future__ import annotations

from storymaker.commons.db.repos import plan, texto
from storymaker.commons.formal.cronologia import cronologia_de_la_novela, verificar_cronologia
from storymaker.commons.graph.dependencias import actuales
from storymaker.writing import validacion
from storymaker.writing.nodos import CRONOLOGIA_DEL_CAPITULO, validar_determinista


async def version_invalidada(numero: int) -> int | None:
    """La última versión en `Invalidado` del capítulo, si la hay."""
    deps = actuales()
    capitulo = await plan.capitulo_por_numero(deps.db, numero)
    if capitulo is None:
        return None
    async with deps.db.execute(
        """
        SELECT id FROM capitulo_version
         WHERE capitulo_id = ? AND estado = 'invalidado'
         ORDER BY id DESC LIMIT 1
        """,
        (int(capitulo["id"]),),
    ) as cursor:
        fila = await cursor.fetchone()
    return int(fila["id"]) if fila is not None else None


async def pasa_coste_cero(
    version: int, numero: int, *, retirados: list[list[str]] | None = None
) -> bool:
    """Pasada determinista y cronología del capítulo, sin invocar a nadie.

    La determinista lleva los nombres retirados: un invalidado que todavía los dice no pasa,
    aunque ninguna tabla de uso lo hubiera metido en el alcance.
    """
    deps = actuales()
    incidencias = await validar_determinista(version, numero, retirados=retirados)
    if validacion.hay_bloqueantes(incidencias):
        return False
    marca = f"cap{numero}-v{version}-"
    novela = await cronologia_de_la_novela(deps.db, con_version=version)
    cronologia = [
        i
        for i in await verificar_cronologia(
            novela, bloquea=True, validador=CRONOLOGIA_DEL_CAPITULO
        )
        if marca in f"{i.ubicacion or ''} {i.mensaje}"
    ]
    return not cronologia


async def revisar_invalidados(
    numeros: list[int], *, retirados: list[list[str]] | None = None
) -> list[int]:
    """Devuelve a `aprobado` los que pasan. Devuelve, en orden, los que hay que reescribir.

    Un capítulo sin versión invalidada —porque la regeneración ya lo reescribió, o porque
    nunca llegó a aprobarse— no se revisa ni se devuelve: no hay nada que restaurar.
    """
    deps = actuales()
    a_reescribir: list[int] = []
    for numero in sorted(numeros):
        version = await version_invalidada(numero)
        if version is None:
            continue
        if await pasa_coste_cero(version, numero, retirados=retirados):
            await texto.aprobar_capitulo(deps.db, version)
        else:
            a_reescribir.append(numero)
    return a_reescribir
