"""spec: §4.5 · arq: §4, §11a

La **versión candidata**: la que se arma, se renderiza y se juzga antes de existir como
versión publicada.

Vive aparte del nodo porque es una idea con nombre propio y no un paso de un procedimiento.
Una versión candidata es una lista de `capitulo_version` que todavía no tiene manifiesto: ya
se puede renderizar contra ella, ya se puede comprobar, y **si algo falla no hay nada que
retirar** porque nunca llegó a publicarse.

Esa es la diferencia que hace de G5 una puerta. Un índice roto detectado tras
`PublishVersion` sería una versión ya publicada con la portada mal: no habría adónde volver,
igual que le pasaba al extractor antes de meterlo dentro de `Validate`.
"""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite

from storymaker.commons.db.repos import plan, texto
from storymaker.commons.validation.modelos import Incidencia


@dataclass(frozen=True)
class Candidata:
    """Los capítulos que compondrían la versión, en orden, y qué falta si falta algo."""

    capitulo_version_ids: tuple[int, ...]
    faltan: tuple[int, ...] = ()

    @property
    def completa(self) -> bool:
        return not self.faltan

    def como_texto(self) -> str:
        if self.completa:
            return f"Version candidata con {len(self.capitulo_version_ids)} capitulos aprobados."
        return (
            f"No se puede componer la version: faltan por aprobar los capitulos "
            f"{', '.join(str(n) for n in self.faltan)}."
        )


async def componer(db: aiosqlite.Connection) -> Candidata:
    """Reúne los capítulos aprobados en orden. No escribe nada.

    Que no escriba es lo que permite mirarla antes de decidir: el informe del gate de
    Writing la usa para decir si la novela está lista, y el nodo de publicación la usa para
    saber qué va a publicar, sin que ninguno de los dos deje rastro.
    """
    total = await plan.total_de_capitulos(db)
    versiones: list[int] = []
    faltan: list[int] = []

    for numero in range(1, total + 1):
        capitulo = await plan.capitulo_por_numero(db, numero)
        if capitulo is None:
            faltan.append(numero)
            continue
        aprobado = await texto.capitulo_aprobado(db, int(capitulo["id"]))
        if aprobado is None:
            faltan.append(numero)
        else:
            versiones.append(int(aprobado["id"]))

    return Candidata(capitulo_version_ids=tuple(versiones), faltan=tuple(faltan))


def incidencias_de(candidata: Candidata) -> list[Incidencia]:
    """Lo que impide publicar, en el formato que el resto del sistema entiende."""
    from storymaker.commons.validation.modelos import Severidad

    if candidata.completa:
        return []
    return [
        Incidencia(
            validador="version_candidata",
            severidad=Severidad.BLOQUEANTE,
            mensaje=candidata.como_texto(),
        )
    ]
