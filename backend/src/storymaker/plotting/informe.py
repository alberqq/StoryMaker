"""spec: §4.3 · arq: §4, §10

El informe del gate de Plotting.

Su pieza más importante es **el recuento de hechos inventados por dimensión**, y está ahí
por una decisión concreta: la invención autorizada no se topa, se cuenta. Poner límite a lo
que el arquitecto puede inventar solo le dejaría salidas peores —fallar, o declarar otro
origen—, así que lo que hace el arnés es enseñarlo. Cuánta libertad es aceptable ya lo
declara `grado_licencia` en el brief, y quien la juzga es el juez con el criterio de
autenticidad de época.

Lo demás que se enseña aquí es lo que el Autor necesita para decidir con conocimiento: qué
validadores han pasado, cuántos huecos se gastaron y qué queda sin anclar.
"""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite

from storymaker.commons.db.repos import mundo, plan
from storymaker.commons.validation.modelos import Incidencia
from storymaker.plotting.gate import PuertaDePlotting


@dataclass(frozen=True)
class InformeDePlotting:
    capitulos: int
    escenas: int
    inventados_por_dimension: dict[str, int]
    huecos_gastados: int
    incidencias: tuple[Incidencia, ...] = ()

    @property
    def inventados(self) -> int:
        return sum(self.inventados_por_dimension.values())

    @property
    def puede_avanzar(self) -> bool:
        return not any(i.bloquea for i in self.incidencias)

    def como_texto(self) -> str:
        lineas = [
            f"Escaleta: {self.capitulos} capitulos, {self.escenas} escenas.",
            f"Huecos de micro-investigacion gastados: {self.huecos_gastados}.",
        ]
        if self.inventados:
            lineas.append(
                f"\n{self.inventados} hecho(s) inventados con permiso, por dimension:"
            )
            for dimension, cuantos in sorted(self.inventados_por_dimension.items()):
                lineas.append(f"  - {dimension}: {cuantos}")
            lineas.append(
                "No se topan a proposito: topar la invencion solo dejaria al arquitecto "
                "salidas peores. Cuanta libertad es aceptable lo declara el grado de "
                "licencia del encargo, y quien la juzga es el juez."
            )
        else:
            lineas.append("\nNingun hecho inventado: toda la escaleta se apoya en el corpus.")

        if self.incidencias:
            lineas.append("\nLa puerta del gate no esta en verde:")
            for incidencia in self.incidencias:
                marca = "BLOQUEA" if incidencia.bloquea else "aviso  "
                lineas.append(f"  [{marca}] {incidencia.validador}: {incidencia.mensaje}")
            lineas.append(
                "Corregir esto aqui cuesta un parrafo de escaleta. Descubrirlo con la "
                "novela escrita cuesta diez capitulos."
            )
        else:
            lineas.append("\nCobertura y arcos en verde: la escaleta puede sellarse.")
        return "\n".join(lineas)


async def construir(
    db: aiosqlite.Connection, fase_run_id: int, puerta: PuertaDePlotting, *, huecos_gastados: int
) -> InformeDePlotting:
    capitulos = await plan.total_de_capitulos(db)
    async with db.execute("SELECT COUNT(*) AS n FROM plan_escena") as cursor:
        fila = await cursor.fetchone()
    escenas = int(fila["n"]) if fila is not None else 0

    return InformeDePlotting(
        capitulos=capitulos,
        escenas=escenas,
        inventados_por_dimension=await mundo.inventados_por_dimension(db, fase_run_id),
        huecos_gastados=huecos_gastados,
        incidencias=puerta.incidencias,
    )
