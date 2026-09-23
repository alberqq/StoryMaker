"""spec: §4.6 · arq: §4, §7

El diff entre dos versiones: **comparar dos manifiestos con un `JOIN`**, no diffear texto.

Sale gratis de la decisión de §7. Una versión de la novela es la lista ordenada de qué
`capitulo_version` la componen, así que «qué cambió» es una consulta sobre esa lista. De ahí
salen a la vez la página de novedades del PDF y el distintivo del índice web, y un capítulo
no regenerado se comparte entre versiones sin duplicarse.

Comparar texto habría sido la alternativa obvia y habría sido peor: un diff de prosa señala
palabras, y lo que el lector quiere saber es **qué capítulos cambiaron**.
"""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite


@dataclass(frozen=True)
class CapituloDelDiff:
    numero: int
    antes: int | None
    despues: int | None

    @property
    def estado(self) -> str:
        if self.antes is None:
            return "nuevo"
        if self.despues is None:
            return "retirado"
        if self.antes == self.despues:
            return "igual"
        return "regenerado"


@dataclass(frozen=True)
class Diff:
    version_a: int
    version_b: int
    capitulos: tuple[CapituloDelDiff, ...]

    @property
    def cambiados(self) -> tuple[CapituloDelDiff, ...]:
        return tuple(c for c in self.capitulos if c.estado != "igual")

    def como_texto(self) -> str:
        if not self.cambiados:
            return f"Las versiones {self.version_a} y {self.version_b} tienen los mismos capitulos."
        lineas = [f"Cambios entre la version {self.version_a} y la {self.version_b}:"]
        for capitulo in self.cambiados:
            lineas.append(f"  - capitulo {capitulo.numero}: {capitulo.estado}")
        iguales = len(self.capitulos) - len(self.cambiados)
        lineas.append(
            f"Los otros {iguales} capitulo(s) son la misma fila en las dos versiones: no se "
            f"han duplicado ni reescrito."
        )
        return "\n".join(lineas)


async def entre(db: aiosqlite.Connection, version_a: int, version_b: int) -> Diff:
    """El diff completo, con un `JOIN` sobre los dos manifiestos."""
    async with db.execute(
        """
        SELECT pc.numero AS numero,
               MAX(CASE WHEN vc.version_id = ? THEN vc.capitulo_version_id END) AS antes,
               MAX(CASE WHEN vc.version_id = ? THEN vc.capitulo_version_id END) AS despues
          FROM version_capitulo vc
          JOIN capitulo_version cv ON cv.id = vc.capitulo_version_id
          JOIN plan_capitulo pc ON pc.id = cv.capitulo_id
         WHERE vc.version_id IN (?, ?)
         GROUP BY pc.numero
         ORDER BY pc.numero
        """,
        (version_a, version_b, version_a, version_b),
    ) as cursor:
        filas = list(await cursor.fetchall())

    return Diff(
        version_a=version_a,
        version_b=version_b,
        capitulos=tuple(
            CapituloDelDiff(
                numero=int(f["numero"]),
                antes=int(f["antes"]) if f["antes"] is not None else None,
                despues=int(f["despues"]) if f["despues"] is not None else None,
            )
            for f in filas
        ),
    )
