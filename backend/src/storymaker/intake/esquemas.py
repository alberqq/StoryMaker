"""spec: §4.1 · arq: §4

El `Brief`: lo que el comprador encarga, en tres bloques.

El reparto no es cosmético. El primero describe **a quién** se regala la novela, el segundo
**el mundo** en el que va a vivir y el tercero **las reglas** con las que se escribe. Nada
de lo que el arquitecto puede inventar entra aquí: la Premisa, el Tema, la trama, los
conflictos, los arcos y la escaleta son obra suya en la Fase 3, y recogerlos en la entrada
sería pedirle al comprador que escriba la novela.

Los tres diales de la frontera historia-ficcion —`grado_licencia`, `arcaismo` y
`contenido_admisible`— son obligatorios aunque **ningún validador los lea por sí solos**:
son la política contra la que el juez puntúa la autenticidad de época. Sin declararlos, esa
política existiría igualmente pero la pondría el modelo, que es justo lo que este arnés
evita en todo lo demás. Llegan a quien escribe por `canon_obra.estilo_json`, en el bloque 6
del paquete.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from storymaker.commons.config import Defaults


class TipoDeDato(StrEnum):
    """Los cinco tipos a los que se reduce cualquier material del comprador.

    La lista es cerrada a propósito: es lo que convierte el texto libre en algo que se
    puede anclar, contar y comprobar. Una inyección tiene que sobrevivir a convertirse en
    una de estas cinco cosas para hacer daño, y no sobrevive.
    """

    PERSONA = "persona"
    LUGAR = "lugar"
    FECHA = "fecha"
    OBJETO = "objeto"
    ANECDOTA = "anecdota"


class GradoDeLicencia(StrEnum):
    ESTRICTO = "estricto"
    MODERADO = "moderado"
    AMPLIO = "amplio"


class Arcaismo(StrEnum):
    MINIMO = "minimo"
    MODERADO = "moderado"
    MARCADO = "marcado"


class NivelDeProhibicion(StrEnum):
    """`global` lo pone el arnés; los otros dos, el comprador."""

    GLOBAL = "global"
    NOVELA = "novela"
    DESTINATARIO = "destinatario"


class ElementoPersonalizacion(BaseModel):
    """Algo del comprador que la novela tiene que recoger.

    `obligatorio` es lo que hace contable la cobertura, y se comprueba tres veces: al
    anclar la escaleta, al escribir cada capítulo y al cerrar Writing. Un elemento que no
    es obligatorio es una sugerencia, y no se le exige a nadie.
    """

    tipo: TipoDeDato
    valor: str = Field(min_length=1)
    obligatorio: bool = False


class Periodo(BaseModel):
    """El período histórico, con su denominación historiográfica.

    La denominación no es adorno: es lo que el investigador usa para buscar. «1805» da
    resultados distintos que «el Cádiz de las Cortes».
    """

    inicio: int
    fin: int
    denominacion: str = Field(min_length=1)

    @field_validator("fin")
    @classmethod
    def el_fin_no_precede_al_inicio(cls, fin: int, info: object) -> int:
        datos = getattr(info, "data", {})
        inicio = datos.get("inicio")
        if inicio is not None and fin < inicio:
            raise ValueError(f"El periodo termina en {fin} y empieza en {inicio}.")
        return fin


class PersonajeHistorico(BaseModel):
    """Una figura real que debe aparecer o que debe evitarse.

    Las dos cosas son decisiones del comprador y las dos importan: quien encarga una novela
    sobre Cádiz en 1805 puede querer a Gravina dentro y a Napoleón fuera.
    """

    nombre: str = Field(min_length=1)
    debe_aparecer: bool = True
    nota: str | None = None


class TerminoProhibido(BaseModel):
    nivel: NivelDeProhibicion
    termino: str = Field(min_length=1)


class Brief(BaseModel):
    """El encargo completo, ya validado.

    Lo que se guarda en `intake_brief` es este objeto serializado, y **no se consulta para
    decidir nada**: es la fotografía que permite enseñar meses después qué se encargó
    exactamente. Lo vivo son las filas de `intake_dato`.
    """

    # --- Bloque 1 · Homenajeado --------------------------------------------------
    nombre_homenajeado: str = Field(min_length=1)
    fecha_nacimiento: str = Field(min_length=4)
    rol_epoca: str = Field(min_length=1)
    ocasion: str = Field(min_length=1)
    elementos_personalizacion: list[ElementoPersonalizacion] = Field(default_factory=list)

    # --- Bloque 2 · Mundo --------------------------------------------------------
    periodo: Periodo
    lugar: str = Field(min_length=1)
    evento_ancla: str | None = None
    fecha_evento_ancla: str | None = None
    personajes_historicos: list[PersonajeHistorico] = Field(default_factory=list)

    # --- Bloque 3 · Obra y frontera ----------------------------------------------
    genero: str = Field(min_length=1)
    subgenero: str | None = None
    tono: str = Field(min_length=1)
    punto_de_vista: str | None = None
    grado_licencia: GradoDeLicencia = GradoDeLicencia.MODERADO
    arcaismo: Arcaismo = Arcaismo.MODERADO
    contenido_admisible: str = Defaults.CONTENIDO_ADMISIBLE
    palabras_prohibidas: list[TerminoProhibido] = Field(default_factory=list)
    n_capitulos: int = Field(default=Defaults.N_CAPITULOS, ge=1, le=60)
    palabras_por_capitulo: int = Field(default=Defaults.PALABRAS_POR_CAPITULO, ge=300)

    @property
    def obligatorios(self) -> list[ElementoPersonalizacion]:
        return [e for e in self.elementos_personalizacion if e.obligatorio]

    @property
    def elementos_a_cubrir(self) -> list[ElementoPersonalizacion]:
        """Los elementos del encargo más el evento ancla, que entra como obligatorio.

        Así el evento recorre la misma maquinaria que un elemento del comprador: el
        arquitecto lo ve con su `#id`, `cobertura_anclada` exige que alguna escena lo ancle
        y `cobertura_personalizacion` que algún capítulo aprobado lo cuente. Si fuera solo
        prosa del encargo, el arquitecto podría —y lo hizo— dejarlo fuera de la novela.
        """
        if not self.evento_ancla:
            return list(self.elementos_personalizacion)
        evento = ElementoPersonalizacion(
            tipo=TipoDeDato.ANECDOTA,
            valor=f"evento ancla: {self.evento_ancla}",
            obligatorio=True,
        )
        return [*self.elementos_personalizacion, evento]

    @property
    def diales(self) -> dict[str, str]:
        """Lo que el arquitecto copia a `canon_obra.estilo_json` y llega al bloque 6."""
        return {
            "grado_licencia": self.grado_licencia.value,
            "arcaismo": self.arcaismo.value,
            "contenido_admisible": self.contenido_admisible,
            "tono": self.tono,
            "punto_de_vista": self.punto_de_vista or Defaults.PUNTO_DE_VISTA,
        }


class PreguntaAlComprador(BaseModel):
    """Lo que el entrevistador devuelve cuando algo sigue vacío o ambiguo.

    El entrevistador **solo pregunta por lo que falta**, y es lo que impide que la
    conversación sea un formulario disfrazado: si el comprador ya dijo que su padre fue
    armador, nadie se lo vuelve a preguntar.
    """

    campo: str
    pregunta: str
    motivo: str


class RespuestaEntrevistador(BaseModel):
    """La salida del rol: o el brief cerrado, o lo que falta para cerrarlo."""

    brief: Brief | None = None
    preguntas: list[PreguntaAlComprador] = Field(default_factory=list)

    @property
    def completo(self) -> bool:
        return self.brief is not None and not self.preguntas


class DatoExtraido(BaseModel):
    """Una fila tipada salida del texto en cuarentena.

    La salida del extractor está **restringida por esquema a hechos tipados**, y ahí está
    la defensa: el texto en bruto no llega jamás al prompt del escritor, solo llegan estas
    filas, marcadas con su procedencia.
    """

    tipo: TipoDeDato
    valor: str = Field(min_length=1)
    obligatorio: bool = False


class SalidaExtractorDeIntake(BaseModel):
    datos: list[DatoExtraido] = Field(default_factory=list)
