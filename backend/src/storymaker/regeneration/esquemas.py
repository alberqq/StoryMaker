"""spec: §4.6 · arq: §4, §16.2

Lo que entra por la Fase 6: una petición en lenguaje natural, o una edición humana directa.

**Las dos entran por la misma puerta y disparan la misma maquinaria.** Si se borra un hecho
que tres capítulos estaban usando, esos tres se invalidan solos por `uso_hecho` — no hace
falta código nuevo, es el motor de la Fase 6 entrando por otra puerta.

«El perro se llama Nala, no Toby» no dice qué fila tocar. La búsqueda semántica sobre canon
y corpus devuelve los candidatos y **el Autor confirma en el gate**; sin eso, la fase
exigiría que el lector conociera los identificadores internos, que es tanto como no tenerla.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field


class ObjetoDelCambio(StrEnum):
    """Qué se toca. **Nunca el texto**: el canon manda sobre la prosa."""

    HECHO = "hecho"
    PERSONAJE = "personaje"
    ESCENARIO = "escenario"
    GLOSARIO = "glosario"


class PeticionDeCambio(BaseModel):
    """Lo que el lector pide, tal como lo escribe."""

    texto: str = Field(min_length=1)
    origen: str = "lector"


@dataclass(frozen=True)
class Candidato:
    """Una fila que podría ser la que hay que cambiar, con su distancia.

    Se devuelven varios y ordenados porque quien decide es el Autor: presentarle uno solo
    sería convertir una búsqueda por similitud en una certeza que no tiene.
    """

    objeto: ObjetoDelCambio
    fila_id: int
    descripcion: str
    distancia: float


@dataclass(frozen=True)
class CambioResuelto:
    """El cambio ya confirmado, listo para aplicarse."""

    objeto: ObjetoDelCambio
    fila_id: int
    campo: str
    antes: str
    despues: str
    motivo: str = ""


@dataclass(frozen=True)
class Alcance:
    """A cuántos capítulos llega el cambio. Es lo que el gate enseña **antes** de pagarlo.

    Una regeneración que toque un hecho usado en nueve capítulos es correcta pero cara, y el
    Autor tiene que poder abortar viéndolo. La distinción entre regenerados e invalidados es
    la política entera de la fase: **invalidación barata, regeneración cara**.
    """

    a_regenerar: tuple[int, ...] = ()
    a_invalidar: tuple[int, ...] = ()

    @property
    def total(self) -> int:
        return len(self.a_regenerar) + len(self.a_invalidar)

    def como_texto(self) -> str:
        lineas = []
        if self.a_regenerar:
            lineas.append(
                f"Se regeneran {len(self.a_regenerar)} capitulo(s): "
                f"{', '.join(str(c) for c in self.a_regenerar)}. Cada uno cuesta una "
                f"escritura completa."
            )
        else:
            lineas.append("Ningun capitulo usa lo que se cambia: no hay nada que regenerar.")
        if self.a_invalidar:
            lineas.append(
                f"Se revisan {len(self.a_invalidar)} capitulo(s) posteriores con los "
                f"validadores de coste cero: {', '.join(str(c) for c in self.a_invalidar)}. "
                f"Solo se paga la reescritura de los que Lean tumbe."
            )
        return "\n".join(lineas)
