"""spec: §3.4 · arq: §6

La forma del paquete de contexto: siete bloques en orden, cada uno con su techo, y 12.000
tokens en total.

El orden no es decorativo. El bloque 1 es el encargo y es el que nunca debería recortarse;
el 3 es la continuidad y es **el último que se toca**, porque es lo que impide que el
escritor contradiga lo que ya ocurrió. Entre medias, lo que se recorta primero es la
memoria, que es el bloque más grande y el que más redundancia admite.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final

from storymaker.commons.agents.presupuesto import estimar_tokens

#: Los techos de §6, por número de bloque.
TECHOS_DE_BLOQUE: Final[dict[int, int]] = {
    1: 800,  # Encargo
    2: 2_500,  # Canon relevante
    3: 1_500,  # Continuidad
    4: 4_000,  # Memoria
    5: 1_500,  # Anclajes
    6: 1_200,  # Reglas
    7: 500,  # Personalización
}

TECHO_TOTAL: Final = 12_000

#: Por dónde se recorta cuando el total se pasa. La continuidad va la última y el encargo
#: el penúltimo: son los dos bloques cuya pérdida produce un capítulo incoherente en vez de
#: uno más pobre.
ORDEN_DE_RECORTE: Final = (4, 2, 5, 7, 6, 1, 3)

NOMBRES: Final[dict[int, str]] = {
    1: "Encargo",
    2: "Canon relevante",
    3: "Continuidad",
    4: "Memoria",
    5: "Anclajes",
    6: "Reglas",
    7: "Personalizacion",
}


@dataclass(frozen=True)
class Bloque:
    """Un bloque del paquete, con sus fragmentos ya ordenados por relevancia.

    `fijos` son los primeros fragmentos que no se recortan nunca. Es lo que implementa la
    regla de que **los anclajes explícitos de la escaleta entran siempre**, antes que
    cualquier vecino semántico: lo que el arquitecto decidió no compite con lo que la
    búsqueda encontró.
    """

    numero: int
    fragmentos: tuple[str, ...] = ()
    fijos: int = 0

    @property
    def nombre(self) -> str:
        return NOMBRES[self.numero]

    @property
    def techo(self) -> int:
        return TECHOS_DE_BLOQUE[self.numero]

    def texto(self) -> str:
        return "\n".join(self.fragmentos)

    def tokens(self) -> int:
        return estimar_tokens(self.texto())

    def sin_el_ultimo(self) -> Bloque:
        """Suelta el fragmento menos relevante. No baja nunca de los fijos."""
        if len(self.fragmentos) <= self.fijos:
            return self
        return replace(self, fragmentos=self.fragmentos[:-1])


@dataclass(frozen=True)
class Paquete:
    """Lo que el escritor ve. Se persiste entero y se enlaza desde su span de Langfuse.

    Poder abrir, delante del evaluador, literalmente lo que el modelo vio cuando escribió el
    capítulo 7 es la definición operativa de «interpretable» en este sistema. Cuesta casi
    nada y vale mucho.
    """

    capitulo: int
    bloques: tuple[Bloque, ...]

    def texto(self) -> str:
        partes = [f"## {b.numero}. {b.nombre}\n{b.texto()}" for b in self.bloques if b.fragmentos]
        return "\n\n".join(partes)

    def tokens(self) -> int:
        return estimar_tokens(self.texto())

    def bloque(self, numero: int) -> Bloque:
        return next(b for b in self.bloques if b.numero == numero)
