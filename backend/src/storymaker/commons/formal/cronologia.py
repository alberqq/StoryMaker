"""spec: §3.7 · arq: §11c

La cronología que se comprueba en Writing y al publicar, y **quién la calcula**.

Detalla `specs/escritura/spec.md` §3 y §4.

Lean corre en tres sitios (arq. §11c). En el gate de Plotting avisa; en la pasada del
extractor y en la publicación **bloquea**. En los tres calcula lo mismo, y en los tres, si
no hay `lake` o Lean falla por avería, los cuatro invariantes se evalúan en Python sobre el
mismo `NovelaLean`. Sin ese respaldo, una instalación sin Lean no comprobaba la cronología
de la prosa en ninguna parte: la arquitectura decía que bloqueaba, y nadie lo llamaba.

**Qué cronología.** Los personajes del canon con sus fechas vitales, y los eventos
históricos más los narrativos **de las versiones aprobadas vigentes**, a los que se suma, en
la pasada del extractor, los de la versión que se está validando. Los de un intento
descartado describen algo que ya no está en la novela, y contarlos haría que un error ya
corregido siguiera tumbando el capítulo.
"""

from __future__ import annotations

import os
import shutil

import aiosqlite

from storymaker.commons.formal import evaluacion
from storymaker.commons.formal.generador import (
    Evento,
    NovelaLean,
    Persona,
    a_momento,
    nacimiento_de,
)
from storymaker.commons.validation.modelos import Incidencia, Severidad


async def cronologia_de_la_novela(
    db: aiosqlite.Connection, *, con_version: int | None = None
) -> NovelaLean:
    """La cronología aprobada, más la de `con_version` si se está validando una."""
    personas: list[Persona] = []
    async with db.execute(
        "SELECT id, nombre, fecha_nacimiento, fecha_muerte FROM canon_personaje ORDER BY id"
    ) as cursor:
        for fila in await cursor.fetchall():
            personas.append(
                Persona(
                    id=int(fila["id"]),
                    nombre=str(fila["nombre"]),
                    nacimiento=nacimiento_de(fila["fecha_nacimiento"]),
                    muerte=a_momento(fila["fecha_muerte"]),
                )
            )

    async with db.execute(
        """
        SELECT e.id, e.clave, e.momento, e.origen
          FROM cronologia_evento e
          LEFT JOIN capitulo_version cv ON cv.id = e.capitulo_version_id
         WHERE e.origen = 'historico'
            OR e.capitulo_version_id = ?
            OR cv.id = (SELECT MAX(id) FROM capitulo_version
                         WHERE capitulo_id = cv.capitulo_id AND estado = 'aprobado')
         ORDER BY e.momento, e.id
        """,
        (con_version if con_version is not None else -1,),
    ) as cursor:
        filas = list(await cursor.fetchall())

    eventos: list[Evento] = []
    for fila in filas:
        momento = a_momento(fila["momento"])
        if momento is None:
            continue
        async with db.execute(
            "SELECT personaje_id FROM cronologia_participante WHERE evento_id = ?",
            (fila["id"],),
        ) as cursor:
            participantes = tuple(int(p["personaje_id"]) for p in await cursor.fetchall())
        eventos.append(
            Evento(
                id=int(fila["id"]),
                clave=str(fila["clave"]),
                momento=momento,
                # El extractor no dice dónde ocurre cada evento, y no saberlo no es estar
                # en otro sitio: I3 no cuenta el escenario desconocido.
                lugar=0,
                participantes=participantes,
                objetos=(),
                origen=str(fila["origen"]),
            )
        )
    return NovelaLean(personas=tuple(personas), objetos=(), eventos=tuple(eventos))


def lean_activo() -> bool:
    """Hay `lake` en el PATH y nadie lo ha apagado con `STORYMAKER_LEAN=0`.

    El interruptor existe para la suite: con Lean instalado, cada prueba que cruza una
    cronología arrancaría un proceso de Lean, y las pruebas que lo ejercitan de verdad lo
    vuelven a encender explícitamente.
    """
    if os.environ.get("STORYMAKER_LEAN", "1").strip().lower() in ("0", "no", "false"):
        return False
    return shutil.which("lake") is not None


async def verificar_cronologia(
    novela: NovelaLean, *, bloquea: bool, validador: str | None = None
) -> list[Incidencia]:
    """Lean si hay `lake` y no se avería; si no, los mismos invariantes en Python.

    `bloquea` decide la severidad, no quién calcula: el gate de Plotting avisa y los otros
    dos puntos bloquean, con el mismo cálculo. `validador` renombra las incidencias para el
    sitio que las guarda; sin él conservan el nombre de quien las produjo.

    **Con Lean, Lean decide y Python explica.** Lean dice qué invariante cae y con qué
    eventos, pero no quién ni en qué fecha, que es lo que el editor necesita para corregir.
    Si Lean rechaza y la evaluación en Python ve lo mismo, van sus incidencias, que nombran
    al personaje; si Lean rechaza y Python no ve nada —el caso que solo Lean ve—, van las de
    Lean tal cual. Si Lean aprueba, no hay incidencias.
    """
    if not novela.eventos:
        return []
    veredicto = None
    if lean_activo():
        from storymaker.commons.formal import runner

        try:
            veredicto = await runner.verificar(novela)
        except Exception:  # cualquier avería de Lean cae a la evaluación en Python
            veredicto = None
    explicado = evaluacion.evaluar(novela)
    if veredicto is None or (not veredicto.correcto and explicado.incidencias):
        veredicto = explicado
    severidad = Severidad.BLOQUEANTE if bloquea else Severidad.AVISO
    return [
        Incidencia(
            validador=validador or i.validador,
            severidad=severidad,
            mensaje=i.mensaje,
            ubicacion=i.ubicacion,
            propuesta=i.propuesta,
        )
        for i in veredicto.incidencias
    ]
