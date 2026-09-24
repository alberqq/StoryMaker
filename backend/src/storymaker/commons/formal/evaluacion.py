"""spec: §3.7 · arq: §11c

Detalla `specs/trama-rehacible/spec.md` §3.3.

Los invariantes de `Cronologia.Basico` evaluados en Python, **para cuando Lean no está**.

En el gate de Plotting la cronología se comprueba antes de haber escrito nada, y es la
comprobación más barata de las tres. Pero exige `lake`, y en una instalación sin él la
comprobación no corría en absoluto. Esta evaluación la sustituye allí, y solo allí: es un
aviso para el Autor, no la puerta G5 de publicar, que sigue siendo Lean y sigue sin admitir
excepción.

Se evalúa sobre el mismo `NovelaLean` que el generador vuelca, con las mismas definiciones
—igualdad exacta de día en I3, `None` como ausencia de restricción—, de modo que las dos
evaluaciones no pueden discrepar sobre qué datos miran, solo sobre quién calcula.
"""

from __future__ import annotations

from datetime import timedelta

from storymaker.commons.formal.generador import EPOCA, INVARIANTES, Evento, NovelaLean
from storymaker.commons.formal.runner import Veredicto
from storymaker.commons.validation.modelos import Incidencia, Severidad

VALIDADOR = "cronologia_escaleta"


def _fecha(momento: int) -> str:
    return (EPOCA + timedelta(days=momento)).isoformat()


def evaluar(novela: NovelaLean) -> Veredicto:
    """I1 a I4, con un aviso por evento culpable que dice quién, dónde y cuándo."""
    personas = {p.id: p for p in novela.personas}
    objetos = {o.id: o for o in novela.objetos}
    incidencias: list[Incidencia] = []

    def aviso(etiqueta: str, evento: Evento, detalle: str) -> None:
        incidencias.append(
            Incidencia(
                validador=VALIDADOR,
                severidad=Severidad.AVISO,
                mensaje=f"{INVARIANTES[etiqueta]} {detalle}",
                ubicacion=evento.clave,
            )
        )

    for e in novela.eventos:
        for pid in e.participantes:
            p = personas.get(pid)
            if p is None:
                continue
            if e.momento < p.nacimiento:
                aviso(
                    "I1",
                    e,
                    f"«{p.nombre}» esta en {e.clave} ({_fecha(e.momento)}) y nace el "
                    f"{_fecha(p.nacimiento)}.",
                )
            if p.muerte is not None and e.momento > p.muerte:
                aviso(
                    "I2",
                    e,
                    f"«{p.nombre}» esta en {e.clave} ({_fecha(e.momento)}) y muere el "
                    f"{_fecha(p.muerte)}.",
                )
        for oid in e.objetos:
            o = objetos.get(oid)
            if o is None:
                continue
            if e.momento < o.aparece or (o.desaparece is not None and e.momento > o.desaparece):
                aviso("I4", e, f"«{o.nombre}» aparece en {e.clave} ({_fecha(e.momento)}).")

    vistos: set[tuple[int, int]] = set()
    for e in novela.eventos:
        for f in novela.eventos:
            if e.id >= f.id or e.momento != f.momento or e.lugar == f.lugar:
                continue
            if not e.lugar or not f.lugar:
                # Lugar 0 es «sin escenario»: no se sabe dónde ocurre, y no saberlo no es
                # estar en otro sitio.
                continue
            for pid in set(e.participantes) & set(f.participantes):
                if (pid, e.momento) in vistos:
                    continue
                vistos.add((pid, e.momento))
                nombre = personas[pid].nombre if pid in personas else str(pid)
                aviso(
                    "I3",
                    e,
                    f"«{nombre}» esta el {_fecha(e.momento)} en {e.clave} y en {f.clave}, "
                    "que ocurren en escenarios distintos.",
                )

    return Veredicto(correcto=not incidencias, incidencias=tuple(incidencias))
