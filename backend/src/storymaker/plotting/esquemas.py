"""spec: §4.3 · arq: §4, §7

Lo que el arquitecto entrega: la Premisa y el Tema **que él inventa**, el canon y la
escaleta jerárquica.

La Premisa y el Tema pertenecen al módulo 2 de la ontología y **no los escribe ni el
cliente ni el entrevistador**. Es la línea que separa esta fase de la primera: el comprador
encarga a quién, dónde y con qué reglas; el arquitecto decide de qué va la novela.

El Arco tiene esquema propio porque **si no, no puede tener validador**. Todos los
validadores deterministas de este sistema comparan el texto contra una fila, y sin fila el
arco solo podía juzgarlo el juez, sobre la novela entera y una sola vez. Que el arco plano
sea un tipo legítimo es lo que hace exigible el arco sin volverlo una carga: declarar que un
personaje no se transforma es una decisión sobre él.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from storymaker.investigation.esquemas import Dimension


class TipoDePersonaje(StrEnum):
    """Procedencia, no peso en la trama.

    La distinción importa porque «personaje principal» no es algo que el modelo de datos
    sepa responder, y por eso `arco_anclado` cuenta apariciones en lugar de importancia.
    """

    INVENTADO = "inventado"
    HISTORICO_FICCIONALIZADO = "historico_ficcionalizado"
    HISTORICO_DE_FONDO = "historico_de_fondo"


class TipoDeArco(StrEnum):
    POSITIVO = "positivo"
    NEGATIVO = "negativo"
    #: Declarar que un personaje no se transforma es justo la decisión que el validador
    #: reclama. Pedirle una transformación al tabernero sería mala literatura impuesta.
    PLANO = "plano"


class PersonajePropuesto(BaseModel):
    nombre: str = Field(min_length=1)
    tipo: TipoDePersonaje
    objetivo: str = ""
    miedo: str = ""
    voz: str = ""
    estatus: str = ""
    fecha_nacimiento: str | None = None
    fecha_muerte: str | None = None
    es_homenajeado: bool = False


class HitoDeArco(BaseModel):
    """Un punto de la transformación, anclado a una escena.

    El anclaje es lo que permite preguntar en el capítulo N si el hito que le tocaba
    ocurrió, y lo que convierte el giro de valor de cada beat en la materia prima de esa
    comprobación.
    """

    orden: int = Field(ge=1)
    descripcion: str = Field(min_length=1)
    escena: str = Field(min_length=1, description="clave de la escena a la que se ancla")


class ArcoPropuesto(BaseModel):
    personaje: str = Field(min_length=1)
    tipo: TipoDeArco
    estado_inicial: str = ""
    estado_final: str = ""
    hitos: list[HitoDeArco] = Field(default_factory=list)


class EscenarioPropuesto(BaseModel):
    clave: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    lugar: str = ""


class TerminoDeGlosario(BaseModel):
    termino: str = Field(min_length=1)
    significado: str = Field(min_length=1)
    registro: str = ""


class AnclajePropuesto(BaseModel):
    """A qué se agarra una escena: un hecho del corpus, una entidad o un dato del comprador.

    Exactamente uno de los tres, y el `CHECK` de la tabla lo impone. Que el anclaje sea una
    fila y no una intención es lo que permite a `anclaje_valido` comprobar en Writing que
    todo lo que el texto usa está en el corpus sellado o declarado como Licencia.
    """

    tipo_vinculo: str = "sostiene la escena"
    hecho: str | None = None
    entidad: str | None = None
    dato: str | None = None


class BeatPropuesto(BaseModel):
    orden: int = Field(ge=1)
    accion: str = Field(min_length=1)
    #: El giro de valor. Se rellenaba y no lo leía nadie hasta que `ejecucion_escaleta`
    #: pasó a preguntarse si ocurrió.
    cambio_de_valor: str = ""


class EscenaPropuesta(BaseModel):
    clave: str = Field(min_length=1)
    orden: int = Field(ge=1)
    escenario: str = ""
    fecha_narrativa: str = ""
    pdv: str = ""
    objetivo: str = ""
    conflicto: str = ""
    resultado: str = ""
    personajes: list[str] = Field(default_factory=list)
    beats: list[BeatPropuesto] = Field(default_factory=list)
    anclajes: list[AnclajePropuesto] = Field(default_factory=list)


class CapituloPropuesto(BaseModel):
    numero: int = Field(ge=1)
    titulo: str = ""
    funcion: str = ""
    gancho: str = ""
    escenas: list[EscenaPropuesta] = Field(default_factory=list)


class HuecoPropuesto(BaseModel):
    """Lo que la escaleta necesita y el corpus no tiene, dicho junto a la escena que lo pide.

    Lleva **la invención ya enunciada** porque el segundo final del hueco —no encontrarlo—
    autoriza a inventar, y lo que se inventa tiene que ser una afirmación. Sin ella, lo único
    que el arnés tenía para escribir en el corpus era la pregunta.
    """

    pregunta: str = Field(min_length=1)
    #: Clave de la escena que se apoya en la respuesta. Al cubrir el hueco, el hecho se
    #: ancla a ella.
    escena: str = ""
    dimension: Dimension = Dimension.CULTURA_MATERIAL
    #: La afirmación que el arquitecto usaría si la investigación no encuentra nada.
    si_no_se_encuentra: str = ""

    @model_validator(mode="before")
    @classmethod
    def _desde_texto(cls, valor: object) -> object:
        """Un hueco escrito como texto suelto es una pregunta sin escena ni propuesta."""
        if isinstance(valor, str):
            return {"pregunta": valor}
        if isinstance(valor, dict) and valor.get("dimension") not in {d.value for d in Dimension}:
            # Una dimensión mal escrita no tumba la escaleta entera: el hueco sigue siendo
            # útil, y la dimensión solo decide en qué pestaña del corpus aparece.
            return {**valor, "dimension": Dimension.CULTURA_MATERIAL.value}
        return valor


class SalidaArquitecto(BaseModel):
    """La entrega completa de la Fase 3."""

    titulo: str = ""
    premisa: str = Field(min_length=1)
    tema: str = Field(min_length=1)
    voz: str = ""
    personajes: list[PersonajePropuesto] = Field(default_factory=list)
    arcos: list[ArcoPropuesto] = Field(default_factory=list)
    escenarios: list[EscenarioPropuesto] = Field(default_factory=list)
    glosario: list[TerminoDeGlosario] = Field(default_factory=list)
    capitulos: list[CapituloPropuesto] = Field(default_factory=list)
    #: Lo que la escaleta destapó y el corpus no tiene. Cada uno cuesta una micro-llamada.
    huecos: list[HuecoPropuesto] = Field(default_factory=list)

    @property
    def homenajeado(self) -> PersonajePropuesto | None:
        return next((p for p in self.personajes if p.es_homenajeado), None)
