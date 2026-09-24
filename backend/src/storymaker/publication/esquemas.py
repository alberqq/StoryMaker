"""spec: §4.5 · arq: §5, §11b

Lo que el juez devuelve: **puntuaciones, y nada más**.

El juez no tiene permiso de escritura sobre el texto, y su esquema lo hace cierto: no hay
ningún campo donde pudiera devolver prosa corregida. Si lo tuviera, el mismo agente que
produce la métrica podría optimizarla, y los *scores* dejarían de significar nada. Esa es
la misma razón por la que el editor y el juez son dos agentes distintos y no uno.

La rúbrica son **siete criterios del 1 al 10 con justificación**, y la justificación no es
adorno: es lo que permite comparar el juicio del modelo con el de una persona, porque
`revision_humana` usa exactamente el mismo fichero de rúbrica.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Criterio(StrEnum):
    """Los siete de §11b. La lista es cerrada: puntuar otra cosa no es esta rúbrica."""

    CONTINUIDAD = "continuidad"
    ARCO = "arco"
    COHERENCIA_DE_PERSONAJES = "coherencia_de_personajes"
    RITMO = "ritmo"
    PROSA = "prosa"
    NATURALIDAD_DE_LA_PERSONALIZACION = "naturalidad_de_la_personalizacion"
    AUTENTICIDAD_DE_EPOCA = "autenticidad_de_epoca"


class Puntuacion(BaseModel):
    """Un criterio, su nota y por qué.

    La justificación tiene mínimo pero no máximo generoso: un juez que escribe «bien» no
    está juzgando, y uno que escribe tres párrafos por criterio se come su propio techo.
    """

    criterio: Criterio
    valor: int = Field(ge=1, le=10)
    justificacion: str = Field(min_length=10, max_length=600)


class SalidaJuez(BaseModel):
    """La rúbrica entera. Sin ningún campo por el que pudiera devolver texto de la novela."""

    puntuaciones: list[Puntuacion] = Field(min_length=1)
    #: Lo que un capitulo afirma y otro desmiente, y lo que un personaje sabe o cuenta antes
    #: de que ocurra. Las enumera el juez antes de puntuar; cuanto pesan lo decide Python.
    contradicciones: list[str] = Field(default_factory=list, max_length=20)

    @property
    def media(self) -> float:
        return sum(p.valor for p in self.puntuaciones) / len(self.puntuaciones)

    @property
    def completa(self) -> bool:
        return {p.criterio for p in self.puntuaciones} == set(Criterio)

    def por_criterio(self) -> dict[str, int]:
        return {p.criterio.value: p.valor for p in self.puntuaciones}

    def peor(self) -> Puntuacion:
        return min(self.puntuaciones, key=lambda p: p.valor)


#: Umbral por debajo del cual la novela vuelve al gate de Writing. No es un número mágico:
#: es la nota media que el Autor declaró aceptable, y se puede mover sin tocar código.
UMBRAL_DE_PUBLICACION = 6.0
