"""spec: §4.2 · arq: §4, §7

Los esquemas de la Fase 2: lo que el investigador devuelve y lo que el verificador dictamina.

Dos cosas se fijan aquí y las dos son estructurales. La primera es que **cada hecho viaja
con su cita**, acotada a 300 caracteres: ese límite obliga al investigador a señalar el
fragmento que sostiene ese enunciado concreto en lugar de volcar media página, y mantiene
acotado el contexto del verificador. La cita no es adorno — es lo único que hace verificable
el paso 2.

La segunda es que **`estado` y `respaldo` son cosas distintas**. `estado` es una propiedad
del hecho en la historiografía: si la fuente lo da por asentado, si es materia de debate,
si es una inferencia o si sencillamente no se sabe. `respaldo` es una propiedad de la cita:
si el fragmento guardado sostiene o no el enunciado. Un hecho puede estar perfectamente
respaldado y ser `debatido`, y otro afirmarse como `verificado` y resultar `no_respaldado`
porque la cita hable de otra cosa.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from storymaker.commons.config import Defaults


class Dimension(StrEnum):
    """Las seis dimensiones que definen un período histórico.

    La lista es **cerrada**, y por eso el investigador recibe un encargo y no una consigna
    vaga: su trabajo es repartir tres búsquedas entre estas seis y dejarlas todas pobladas.
    Que el reparto lo decida él es un riesgo aceptado, mitigado enseñando el recuento por
    dimensión en el informe del gate.
    """

    CRONOLOGIA = "cronologia"
    LUGAR = "lugar"
    CULTURA_MATERIAL = "cultura_material"
    LENGUAJE = "lenguaje"
    MENTALIDAD = "mentalidad"
    ESTRUCTURA_SOCIAL = "estructura_social"


class EstadoEpistemico(StrEnum):
    """Qué firmeza tiene el hecho en la historiografía. Viaja al bloque 5 del paquete."""

    VERIFICADO = "verificado"
    DEBATIDO = "debatido"
    INFERIDO = "inferido"
    DESCONOCIDO = "desconocido"


class Respaldo(StrEnum):
    """Qué dice la cita. Viaja al informe del gate."""

    PENDIENTE = "pendiente"
    RESPALDADO = "respaldado"
    NO_RESPALDADO = "no_respaldado"
    NO_APLICA = "no_aplica"


class FuenteCitada(BaseModel):
    """Lo que `WebSearch` devuelve —URL y título— se mapea directamente aquí."""

    url: str = Field(min_length=1)
    titulo: str = Field(default="", max_length=300)
    tipo: str = "web"


class HechoPropuesto(BaseModel):
    """Un hecho del corpus, tal como el investigador lo entrega."""

    enunciado: str = Field(min_length=1, max_length=600)
    estado: EstadoEpistemico
    dimension: Dimension
    #: El fragmento de la fuente copiado tal cual. El tope es lo que hace verificable el paso 2.
    cita: str = Field(default="", max_length=Defaults.LONGITUD_MAXIMA_CITA)
    fuentes: list[FuenteCitada] = Field(default_factory=list)
    entidades: list[str] = Field(default_factory=list)


class SalidaInvestigador(BaseModel):
    """Lo que devuelve la sesión única de Investigation."""

    hechos: list[HechoPropuesto] = Field(default_factory=list)

    def por_dimension(self) -> dict[str, int]:
        recuento: dict[str, int] = {}
        for hecho in self.hechos:
            recuento[hecho.dimension.value] = recuento.get(hecho.dimension.value, 0) + 1
        return recuento


class HuecoResuelto(BaseModel):
    """La respuesta a una micro-llamada del arquitecto en Plotting.

    Termina siempre de una de dos formas, y las dos son útiles: o trae el hecho, o dice
    `no_encontrado` y **autoriza al arquitecto a inventarlo**. Un detalle de cultura
    material no puede detener la escaleta.
    """

    encontrado: bool
    hecho: HechoPropuesto | None = None
    motivo: str = ""


class VeredictoDeRespaldo(BaseModel):
    """Lo que el verificador dictamina sobre un hecho, respondiendo una sola pregunta.

    «¿El fragmento dice lo que el hecho afirma, sí o no?». Nada más: no se le pide que
    juzgue si el hecho es cierto —eso es U-2 y ninguna técnica de software lo decide—, sino
    si la cita sostiene el enunciado.
    """

    hecho_id: int
    respaldado: bool
    motivo: str = Field(default="", max_length=300)


class SalidaVerificador(BaseModel):
    """Un lote de veredictos. El troceo evita que el tamaño del corpus reviente la guarda."""

    veredictos: list[VeredictoDeRespaldo] = Field(default_factory=list)
