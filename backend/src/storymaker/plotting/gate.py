"""spec: §4.3, §7.2 · arq: §11a, §11c

La puerta del gate de Plotting: **lo que tiene que estar en verde antes de abrirlo**.

Aquí corren los dos validadores más rentables del sistema, y lo son por la misma razón: se
ejecutan cuando todavía no se ha escrito una línea, y arreglarlos cuesta un párrafo de
escaleta en lugar de diez capítulos escritos y pagados.

`cobertura_anclada` comprueba que cada elemento obligatorio del encargo está anclado a
alguna escena. `arco_anclado` comprueba que todo personaje recurrente tiene arco — y admite
el plano, que es lo que evita que la exigencia se convierta en una puerta atascada.

Y corre **Lean sobre la cronología deducida de la escaleta**, que es el más barato de sus
tres puntos de ejecución: la escaleta ya declara qué día ocurre cada escena y quién está en
ella, así que un personaje en dos sitios a la vez es detectable antes de redactar.
"""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite

from storymaker.commons.db.repos import canon, intake, plan
from storymaker.commons.formal.generador import (
    Evento,
    NovelaLean,
    Persona,
    a_momento,
)
from storymaker.commons.validation.escaleta import arco_anclado, cobertura_anclada
from storymaker.commons.validation.modelos import (
    ArcoEnRevision,
    EscaletaEnRevision,
    Incidencia,
)


async def construir_revision(db: aiosqlite.Connection) -> EscaletaEnRevision:
    """Traduce la base a los tipos del Core Domain. El validador no ve SQLite."""
    obra = await canon.obra(db)
    homenajeado = await canon.homenajeado(db)
    homenajeado_id = int(homenajeado["id"]) if homenajeado is not None else None

    apariciones = await plan.apariciones_por_personaje(db)
    nombres: dict[int, str] = {}
    arcos: list[ArcoEnRevision] = []

    for fila in await canon.arcos(db):
        personaje_id = int(fila["personaje_id"])
        nombres[personaje_id] = str(fila["personaje"])
        hitos = await canon.hitos_de_arco(db, int(fila["id"]))
        capitulos = tuple(
            int(h["capitulo_numero"]) for h in hitos if h["capitulo_numero"] is not None
        )
        arcos.append(
            ArcoEnRevision(
                personaje_id=personaje_id,
                personaje=str(fila["personaje"]),
                tipo=str(fila["tipo"]),
                hitos_por_capitulo=capitulos,
                es_homenajeado=personaje_id == homenajeado_id,
            )
        )

    for personaje_id in apariciones:
        if personaje_id not in nombres:
            fichas = await canon.personajes(db, [personaje_id])
            nombres[personaje_id] = str(fichas[0]["nombre"]) if fichas else str(personaje_id)

    obligatorios = await intake.obligatorios(db)
    sin_anclar = {int(f["id"]) for f in await intake.obligatorios_sin_anclar(db)}
    todos = tuple(int(f["id"]) for f in obligatorios)

    return EscaletaEnRevision(
        n_capitulos=(
            int(obra["n_capitulos"]) if obra is not None else await plan.total_de_capitulos(db)
        ),
        apariciones_por_personaje=apariciones,
        nombres_por_personaje=nombres,
        arcos=tuple(arcos),
        obligatorios=todos,
        obligatorios_anclados=frozenset(d for d in todos if d not in sin_anclar),
    )


async def cronologia_de_la_escaleta(db: aiosqlite.Connection) -> NovelaLean:
    """La cronología que se deduce de la escaleta, sin haber redactado nada.

    Cada escena es un evento con su fecha y sus personajes; cada personaje, una persona con
    sus fechas vitales. Con eso, los cuatro invariantes ya tienen material: si el arquitecto
    puso a alguien en una escena posterior a su muerte documentada, cae aquí.
    """
    personas: list[Persona] = []
    async with db.execute(
        "SELECT id, nombre, fecha_nacimiento, fecha_muerte FROM canon_personaje ORDER BY id"
    ) as cursor:
        for fila in await cursor.fetchall():
            personas.append(
                Persona(
                    id=int(fila["id"]),
                    nombre=str(fila["nombre"]),
                    nacimiento=a_momento(fila["fecha_nacimiento"]) or 0,
                    muerte=a_momento(fila["fecha_muerte"]),
                )
            )

    eventos: list[Evento] = []
    async with db.execute(
        """
        SELECT e.id, e.orden, e.fecha_narrativa, e.escenario_id, c.numero
          FROM plan_escena e
          JOIN plan_capitulo c ON c.id = e.capitulo_id
         ORDER BY c.numero, e.orden
        """
    ) as cursor:
        escenas = list(await cursor.fetchall())

    for fila in escenas:
        momento = a_momento(fila["fecha_narrativa"])
        if momento is None:
            # Una escena sin fecha no se puede juzgar temporalmente, y no tenerla no es un
            # error: el arquitecto puede dejarla al aire. Lean no opina sobre lo que no sabe.
            continue
        async with db.execute(
            "SELECT personaje_id FROM plan_escena_personaje WHERE escena_id = ?",
            (fila["id"],),
        ) as cursor2:
            participantes = tuple(int(p["personaje_id"]) for p in await cursor2.fetchall())
        eventos.append(
            Evento(
                id=int(fila["id"]),
                clave=f"cap{fila['numero']}-esc{fila['orden']}",
                momento=momento,
                lugar=int(fila["escenario_id"] or 0),
                participantes=participantes,
                objetos=(),
                origen="narrativo",
            )
        )

    return NovelaLean(personas=tuple(personas), objetos=(), eventos=tuple(eventos))


@dataclass(frozen=True)
class PuertaDePlotting:
    incidencias: tuple[Incidencia, ...]

    @property
    def abierta(self) -> bool:
        return not any(i.bloquea for i in self.incidencias)


async def comprobar(db: aiosqlite.Connection) -> PuertaDePlotting:
    """Los dos validadores del gate. Lean corre aparte, porque necesita el subproceso."""
    revision = await construir_revision(db)
    return PuertaDePlotting(
        tuple([*cobertura_anclada(revision), *arco_anclado(revision)])
    )
