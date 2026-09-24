"""spec: §4.2 · arq: §10, §18

El informe del gate de Investigation: **el corpus es lo único que el Autor revisa a mano**.

Ese es el sentido de este informe y explica su forma. Como el veredicto del verificador no
gobierna ninguna arista del grafo —un hecho sin respaldo se degrada, no bloquea—, lo único
que impide que un corpus flojo llegue a la novela es que alguien lo mire. Así que aquí se
enseñan las dos cosas que hacen falta para mirarlo bien:

**El recuento por dimensión**, porque el reparto de las tres búsquedas entre las seis
dimensiones lo decide el modelo y una puede quedar mucho más pobre que las otras. Enseñarlo
es la mitigación declarada de ese riesgo, y «rehacer con comentario» permite dirigir la
segunda pasada a lo que falte.

**Los hechos sin respaldo, destacados y con su fuente a un clic**, que es también la
mitigación de la cita fabricada: el verificador comprueba que el fragmento sostenga el
hecho, no que el fragmento esté realmente en la URL.
"""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite

from storymaker.commons.db.repos import arnes, mundo
from storymaker.investigation.esquemas import Dimension


@dataclass(frozen=True)
class HechoDudoso:
    enunciado: str
    cita: str
    url: str


@dataclass(frozen=True)
class InformeDeInvestigacion:
    total: int
    por_dimension: dict[str, int]
    sin_respaldo: tuple[HechoDudoso, ...] = ()
    #: Una línea por sesión del modo exhaustivo; vacío en el estándar.
    sesiones_dirigidas: tuple[str, ...] = ()

    @property
    def dimensiones_vacias(self) -> tuple[str, ...]:
        return tuple(d.value for d in Dimension if self.por_dimension.get(d.value, 0) == 0)

    def como_texto(self) -> str:
        lineas = [f"Corpus: {self.total} hechos."]
        if self.sesiones_dirigidas:
            lineas.append("Investigacion exhaustiva:")
            lineas.extend(f"  - {linea}" for linea in self.sesiones_dirigidas)
        for dimension in Dimension:
            cuantos = self.por_dimension.get(dimension.value, 0)
            marca = "  " if cuantos else "! "
            lineas.append(f"{marca}{dimension.value}: {cuantos}")
        if self.dimensiones_vacias:
            lineas.append(
                "Hay dimensiones sin un solo hecho. No bloquea, pero «rehacer con "
                "comentario» permite dirigir la segunda pasada a lo que falta."
            )
        if self.sin_respaldo:
            lineas.append(
                f"\n{len(self.sin_respaldo)} hecho(s) sin respaldo, degradados a inferido:"
            )
            for hecho in self.sin_respaldo:
                lineas.append(f"  - {hecho.enunciado}")
                lineas.append(f"    cita: {hecho.cita or '(sin cita)'}")
                lineas.append(f"    fuente: {hecho.url or '(sin fuente)'}")
        else:
            lineas.append("\nTodos los hechos con cita quedaron respaldados.")
        return "\n".join(lineas)


async def construir(db: aiosqlite.Connection, fase_run_id: int) -> InformeDeInvestigacion:
    hechos = await mundo.hechos_vigentes(db, fase_run_id)
    dudosos = await mundo.sin_respaldo(db, fase_run_id)

    detalles = []
    for fila in dudosos:
        async with db.execute(
            """
            SELECT f.url
              FROM mundo_hecho_fuente hf
              JOIN mundo_fuente f ON f.id = hf.fuente_id
             WHERE hf.hecho_id = ?
             LIMIT 1
            """,
            (fila["id"],),
        ) as cursor:
            fuente = await cursor.fetchone()
        detalles.append(
            HechoDudoso(
                enunciado=str(fila["enunciado"]),
                cita=str(fila["cita"] or ""),
                url=str(fuente["url"]) if fuente is not None else "",
            )
        )

    return InformeDeInvestigacion(
        total=len(hechos),
        por_dimension=await mundo.hechos_por_dimension(db, fase_run_id),
        sin_respaldo=tuple(detalles),
        sesiones_dirigidas=tuple(
            await arnes.incidencias_sin_capitulo(db, "investigacion_dirigida")
        ),
    )
