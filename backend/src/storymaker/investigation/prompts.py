"""spec: §4.2 · arq: §15

Los prompts de la Fase 2, construidos de modo que **los datos personales no puedan salir**.

El investigador es el único rol con acceso a la red, así que es el único por el que la
información del homenajeado podría escapar del fichero de su novela. La defensa tiene dos
mitades: la regla Semgrep `pii-fuera-del-investigador`, que impide escribir el código que
lo haría, y esta función, que construye el prompt **solo con período y lugar** y no recibe
el `Brief` entero.

Que la función tome `periodo` y `lugar` como cadenas y no un `Brief` no es un detalle de
estilo: es lo que hace imposible el error. No se puede filtrar lo que no se tiene.
"""

from __future__ import annotations

from storymaker.commons.config import Defaults
from storymaker.investigation.esquemas import Dimension

DIMENSIONES_EXPLICADAS: dict[Dimension, str] = {
    Dimension.CRONOLOGIA: "cronologia y eventos: que pasa, cuando, en que orden",
    Dimension.LUGAR: (
        "lugar y toponimia de epoca: como se llamaban las calles, los barrios y los accidentes"
    ),
    Dimension.CULTURA_MATERIAL: (
        "cultura material: objetos, oficios, herramientas, ropa, comida, monedas"
    ),
    Dimension.LENGUAJE: (
        "lenguaje de epoca: terminos, tratamientos, giros, lo que no se decia aun"
    ),
    Dimension.MENTALIDAD: (
        "mentalidad: que se daba por supuesto, que escandalizaba, que se temia"
    ),
    Dimension.ESTRUCTURA_SOCIAL: (
        "estructura social: quien manda, quien trabaja, como se asciende"
    ),
}


def prompt_de_investigacion(periodo: str, lugar: str) -> str:
    """El encargo de la sesión única. **Recibe dos cadenas y nada más.**

    El tope de búsquedas se dice aquí para que el investigador pueda repartirlas, pero
    quien lo impone es el arnés: el hook `PreToolUse` deniega la cuarta y esa llamada no
    llega a emitirse. Decirlo en el prompt sin imponerlo sería una sugerencia.
    """
    dimensiones = "\n".join(
        f"  {i}. {DIMENSIONES_EXPLICADAS[d]}" for i, d in enumerate(Dimension, start=1)
    )
    return f"""Investiga este periodo historico y deja pobladas las seis dimensiones.

Periodo: {periodo}
Lugar: {lugar}

Las seis dimensiones:
{dimensiones}

Tienes **{Defaults.WEBSEARCH_INVESTIGACION_INICIAL} busquedas y
{Defaults.WEBFETCH_INVESTIGACION_INICIAL} paginas** en toda la sesion, y el arnes las
impone: la cuarta no se emite. Reparte esas tres paginas entre las seis dimensiones — la
toponimia y la cultura material de un mismo lugar suelen venir de la misma pagina, asi que
aprovecha cada una para varias.

De cada hecho guarda:
  - el enunciado, concreto y comprobable;
  - su estado epistemico: verificado, debatido, inferido o desconocido;
  - la dimension a la que pertenece;
  - **la cita textual de la fuente que lo sostiene**, copiada tal cual y de
    {Defaults.LONGITUD_MAXIMA_CITA} caracteres como mucho. Senala el fragmento que sostiene
    ese enunciado concreto, no media pagina: otro agente va a leer ese fragmento y decidir
    si dice lo que tu afirmas.
"""


#: Lo que cada hecho tiene que llevar, igual en la sesión única y en las dirigidas.
_COMO_SE_GUARDA_UN_HECHO = f"""De cada hecho guarda:
  - el enunciado, concreto y comprobable;
  - su estado epistemico: verificado, debatido, inferido o desconocido;
  - la dimension de la que trata, una de estas seis: {", ".join(d.value for d in Dimension)};
  - **la cita textual de la fuente que lo sostiene**, copiada tal cual y de
    {Defaults.LONGITUD_MAXIMA_CITA} caracteres como mucho. Otro agente va a leer ese
    fragmento y decidir si dice lo que tu afirmas.
"""


def _encargo_dirigido(periodo: str, lugar: str, foco: str, comentarios: str) -> str:
    """El marco común de las sesiones dirigidas: una búsqueda, una página, un foco."""
    extra = (
        f"\nEl Autor pidio al rehacer la investigacion:\n{comentarios}\n" if comentarios else ""
    )
    return f"""Investiga un unico encargo de este periodo historico.

Periodo: {periodo}
Lugar: {lugar}

Encargo: {foco}

Tienes **una busqueda y una pagina**, y el arnes las impone: la segunda no se emite.
Elige la busqueda que mejor sirva a este encargo y extrae de esa pagina todos los hechos
concretos que encuentres sobre el.
{extra}
{_COMO_SE_GUARDA_UN_HECHO}"""


def prompt_de_dimension(periodo: str, lugar: str, dimension: Dimension, comentarios: str) -> str:
    """Una sesión del modo exhaustivo por cada dimensión del período."""
    return _encargo_dirigido(periodo, lugar, DIMENSIONES_EXPLICADAS[dimension], comentarios)


def prompt_de_personajes(
    periodo: str, lugar: str, personajes: list[str], evento: str, comentarios: str
) -> str:
    """La sesión dirigida a las figuras reales y al evento ancla del brief.

    Recibe nombres de figuras históricas y un acontecimiento, **nunca** el del homenajeado:
    la guarda de PII se aplica sobre este prompt antes de emitirlo.
    """
    partes = []
    if personajes:
        partes.append(
            "las figuras historicas " + ", ".join(personajes)
            + ": sus fechas y lo que hicieron en este periodo y lugar"
        )
    if evento:
        partes.append(f"el acontecimiento «{evento}»: cuando fue y que ocurrio exactamente")
    return _encargo_dirigido(periodo, lugar, "; y ".join(partes), comentarios)


def prompt_de_oficio(periodo: str, lugar: str, oficio: str, comentarios: str) -> str:
    """La sesión dirigida al oficio del homenajeado en la época."""
    foco = (
        f"el oficio de «{oficio}» en esta epoca y lugar: como se ejercia, que leyes o "
        "gremios lo regulaban y que riesgos tenia"
    )
    return _encargo_dirigido(periodo, lugar, foco, comentarios)


def prompt_de_verificacion(pares: list[tuple[int, str, str]]) -> str:
    """El lote del verificador: identificador, enunciado y cita.

    No lleva nada más. El verificador **no tiene herramientas y no sale a internet**: todo
    lo que necesita está ya en la base, y eso lo hace barato, acotado y repetible. Lo que
    comprueba es exactamente lo que se puede comprobar sin volver a la página.
    """
    bloques = "\n\n".join(
        f"[{identificador}]\nAfirma: {enunciado}\nCita guardada: {cita or '(sin cita)'}"
        for identificador, enunciado, cita in pares
    )
    return f"""Para cada hecho, responde una sola pregunta: **¿la cita dice lo que el hecho
afirma?**

No juzgues si el hecho es cierto, ni si la fuente es buena, ni si falta contexto. Solo si
ese fragmento sostiene ese enunciado. Si no hay cita, el hecho no esta respaldado.

{bloques}
"""


def prompt_de_hueco(pregunta: str, periodo: str, lugar: str) -> str:
    """La micro-llamada del arquitecto: una sola cosa, una sola búsqueda.

    Y una salida honesta: si no aparece, `no_encontrado` es una respuesta válida y útil,
    porque **autoriza al arquitecto a inventarlo**. Empujar a un modelo a responder algo
    cuando no lo sabe es la manera más segura de llenar el corpus de invenciones que se
    presentan como hechos.
    """
    return f"""Busca este dato concreto para una novela ambientada en {periodo}, en {lugar}:

{pregunta}

Tienes **una sola busqueda**. Si no lo encuentras, responde `no_encontrado`: es una
respuesta valida y util, y el arquitecto podra inventarlo declarandolo como tal.
"""
