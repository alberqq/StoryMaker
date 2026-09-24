"""spec: §4.4 · arq: §4, §5

Los esquemas del bucle de capítulo: lo que entrega el escritor, lo que **mide** el extractor
y lo que devuelve el editor.

El reparto entre los tres es la decisión central de la fase. **El extractor es independiente
porque mide lo que no puede declarar quien lo hizo**: si el escritor dijera qué hechos ha
usado, el índice hecho→capítulo se construiría sobre la autodeclaración de quien tiene
incentivo en decir que los usó todos; y si dijera qué beats ha ejecutado, la comprobación de
que el capítulo cumple la escaleta sería el escritor dándose el visto bueno.

Por eso la salida del escritor es **solo prosa**. No lleva un campo «hechos usados» ni
«beats cubiertos»: no se le pregunta, se le mide.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from pydantic import BaseModel, Field, ValidationInfo, model_validator


class SalidaEscritor(BaseModel):
    """Prosa, y nada más.

    El capítulo se genera **de una sola vez** y no escena a escena: coser escenas generadas
    por separado es la forma más fiable de producir la prosa mecánica y los saltos que el
    producto prohíbe. La escena queda como unidad de planificación y de traza, no de
    redacción.
    """

    texto: str = Field(min_length=1)


class SalidaEditor(BaseModel):
    """El parche del editor.

    Devuelve el capítulo entero corregido y no un diff, por una razón práctica: aplicar un
    diff de prosa a ciegas es una fuente de corrupción silenciosa, y el capítulo cabe
    holgadamente en su techo. Lo que sí se le pide es que **no reescriba lo que funciona**.
    """

    texto: str = Field(min_length=1)
    cambios: list[str] = Field(default_factory=list)


class UsoDeHecho(BaseModel):
    """Un hecho del corpus que el extractor ha encontrado **de verdad** en el texto."""

    hecho_id: int
    escena: int = Field(ge=1, description="orden de la escena dentro del capitulo")
    tipo_uso: str = "mencion"


class UsoDeElemento(BaseModel):
    """Un elemento de personalización que aparece en el capítulo."""

    dato_id: int
    escena: int = Field(ge=1)


class EstadoDeContinuidad(BaseModel):
    """Dónde queda cada personaje al cerrar el capítulo.

    Es lo que el bloque 3 del paquete entrega al capítulo siguiente, y el último bloque que
    el ensamblador recorta: perder memoria produce un capítulo más pobre, perder continuidad
    produce uno que contradice lo que ya ocurrió.
    """

    personaje_id: int
    escenario_id: int | None = None
    fecha_narrativa: str = ""
    conocimiento: list[str] = Field(default_factory=list)
    posesiones: list[str] = Field(default_factory=list)
    estado: dict[str, str] = Field(default_factory=dict)


class EventoNarrativo(BaseModel):
    """Un evento de la cronología que ocurre **en esta prosa**.

    Las filas con `origen = 'narrativo'` las escribe el extractor al leer el capítulo:
    nadie más sabe qué ocurrió ahí dentro. Por eso Lean corre en su pasada y no en la
    determinista — antes de esta llamada, la cronología del capítulo N sencillamente no
    existe.
    """

    clave: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    momento: str = Field(min_length=1, description="fecha narrativa del evento")
    escena: int = Field(ge=1)
    participantes: list[int] = Field(default_factory=list)


class VeredictoDeEjecucion(BaseModel):
    """Qué del plan ocurrió y qué no.

    **Es el juicio de un modelo sobre si algo narrativo ocurrió, y eso no es una puerta.**
    Un beat que el escritor resolvió de otra manera, o un hito que se insinúa en vez de
    declararse, no son errores; un validador bloqueante los trataría como tales y gastaría
    los dos reintentos del capítulo discutiendo con el editor sobre una lectura.
    """

    beats_ejecutados: list[str] = Field(default_factory=list)
    beats_pendientes: list[str] = Field(default_factory=list)
    hitos_ejecutados: list[int] = Field(default_factory=list)
    hitos_pendientes: list[int] = Field(default_factory=list)


@dataclass(frozen=True)
class Dominio:
    """Los identificadores que el extractor tuvo delante (ER §7.3).

    Viaja como contexto de validación y no como parte del esquema: el esquema es la forma,
    común a toda novela; el dominio es de esta novela y de este capítulo.
    """

    personajes: frozenset[int] = field(default_factory=frozenset)
    escenarios: frozenset[int] = field(default_factory=frozenset)
    hechos: frozenset[int] = field(default_factory=frozenset)
    datos: frozenset[int] = field(default_factory=frozenset)
    hitos: frozenset[int] = field(default_factory=frozenset)


def _fuera(nombre: str, usados: list[int], validos: frozenset[int]) -> str | None:
    ajenos = sorted({u for u in usados if u not in validos})
    if not ajenos:
        return None
    admitidos = ", ".join(str(v) for v in sorted(validos)) or "ninguno"
    return f"{nombre} {ajenos} no estan en el catalogo; admitidos: {admitidos}"


class SalidaExtractorDeCapitulo(BaseModel):
    """Todo lo que el extractor mide en una sola llamada.

    Una sola llamada y no cinco: se invoca una vez por intento que supere la pasada
    determinista, tres veces por capítulo en el peor caso. Es el precio más barato al que se
    puede comprar la comprobación de que el texto ejecutó el plan.
    """

    resumen: str = Field(min_length=1, max_length=1200)
    hechos_usados: list[UsoDeHecho] = Field(default_factory=list)
    elementos_usados: list[UsoDeElemento] = Field(default_factory=list)
    continuidad: list[EstadoDeContinuidad] = Field(default_factory=list)
    eventos: list[EventoNarrativo] = Field(default_factory=list)
    veredicto: VeredictoDeEjecucion = Field(default_factory=VeredictoDeEjecucion)

    @model_validator(mode="after")
    def _en_dominio(self, info: ValidationInfo) -> Self:
        """Ningún identificador fuera del catálogo llega al volcado."""
        dominio = (info.context or {}).get("dominio")
        if not isinstance(dominio, Dominio):
            return self
        continuidad = self.continuidad
        errores = [
            _fuera("personaje_id", [c.personaje_id for c in continuidad], dominio.personajes),
            _fuera(
                "participantes",
                [p for e in self.eventos for p in e.participantes],
                dominio.personajes,
            ),
            _fuera(
                "escenario_id",
                [c.escenario_id for c in continuidad if c.escenario_id is not None],
                dominio.escenarios,
            ),
            _fuera("hecho_id", [h.hecho_id for h in self.hechos_usados], dominio.hechos),
            _fuera("dato_id", [e.dato_id for e in self.elementos_usados], dominio.datos),
            _fuera(
                "hitos",
                [*self.veredicto.hitos_ejecutados, *self.veredicto.hitos_pendientes],
                dominio.hitos,
            ),
        ]
        motivos = [e for e in errores if e is not None]
        if motivos:
            raise ValueError("; ".join(motivos))
        return self
