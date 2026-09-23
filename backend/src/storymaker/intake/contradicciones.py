"""spec: §4.1 · arq: §4

Las contradicciones del encargo, detectadas por **código y no por un modelo**.

Es el principio de §2 aplicado a la entrada: lo que se puede calcular, se calcula. Que el
homenajeado tuviera tres años durante el período elegido, o que la fecha del evento ancla
sea anterior a su nacimiento, es aritmética. Pedirle a un modelo que lo note sería dejar a
la suerte algo que una resta resuelve.

El agente captura el `ValueError`, lo traduce a pregunta y obliga a resolverlo antes de
cerrar el brief. Por eso estas funciones devuelven **mensajes en castellano y en segunda
persona**: no son trazas para un programador, son lo que el comprador va a leer.
"""

from __future__ import annotations

from storymaker.commons.validation.puras import anio_de, normalizar
from storymaker.intake.esquemas import Brief

#: Palabras que hacen de un tono algo incompatible con un período de duelo o catástrofe.
TONOS_FESTIVOS = ("festivo", "alegre", "humoristico", "comico", "luminoso", "celebracion")
PERIODOS_DE_DUELO = ("peste", "hambruna", "guerra", "asedio", "epidemia", "duelo", "matanza")

#: Edad por debajo de la cual el homenajeado no puede ser el protagonista adulto que el
#: producto promete. No es una regla literaria: es que un armador de seis años no existe.
EDAD_MINIMA_RAZONABLE = 12


def edad_en(brief: Brief, anio: int) -> int | None:
    nacimiento = anio_de(brief.fecha_nacimiento)
    return None if nacimiento is None else anio - nacimiento


def revisar(brief: Brief) -> list[str]:
    """Todas las contradicciones del brief, en el orden en que conviene preguntarlas.

    Devuelve una lista y no la primera que encuentra: preguntar de una en una convertiría
    el cierre del brief en una conversación de cuatro rondas, y el comprador no está aquí
    para eso.
    """
    problemas: list[str] = []
    problemas += _edad_contra_periodo(brief)
    problemas += _nacimiento_contra_evento_ancla(brief)
    problemas += _tono_contra_periodo(brief)
    problemas += _datos_contra_prohibidas(brief)
    return problemas


def _edad_contra_periodo(brief: Brief) -> list[str]:
    """La edad del homenajeado durante el período tiene que dar un personaje posible."""
    nacimiento = anio_de(brief.fecha_nacimiento)
    if nacimiento is None:
        return [
            f"No se entiende la fecha de nacimiento «{brief.fecha_nacimiento}». "
            f"Hace falta al menos el ano."
        ]
    if nacimiento > brief.periodo.fin:
        return [
            f"{brief.nombre_homenajeado} nace en {nacimiento} y el periodo termina en "
            f"{brief.periodo.fin}: no puede ser personaje de esa epoca. Hay que mover el "
            f"periodo o la fecha de nacimiento."
        ]
    edad_al_final = brief.periodo.fin - nacimiento
    if edad_al_final < EDAD_MINIMA_RAZONABLE:
        return [
            f"{brief.nombre_homenajeado} tendria {edad_al_final} anos al final del periodo, "
            f"y el encargo lo situa como {brief.rol_epoca}. Conviene revisar la fecha de "
            f"nacimiento o el periodo."
        ]
    return []


def _nacimiento_contra_evento_ancla(brief: Brief) -> list[str]:
    """El evento ancla es opcional; si viene, tiene que ser posterior al nacimiento.

    La comprobación vive aquí y en una sola fase, en lugar de repetirse en el gate de
    Plotting sobre un dato aparecido más tarde.
    """
    if not brief.evento_ancla or not brief.fecha_evento_ancla:
        return []
    fecha = anio_de(brief.fecha_evento_ancla)
    nacimiento = anio_de(brief.fecha_nacimiento)
    if fecha is None or nacimiento is None:
        return []
    if fecha < nacimiento:
        return [
            f"El evento ancla «{brief.evento_ancla}» ocurre en {fecha} y "
            f"{brief.nombre_homenajeado} nace en {nacimiento}: no puede vivirlo."
        ]
    return []


def _tono_contra_periodo(brief: Brief) -> list[str]:
    """Un tono festivo sobre un período de duelo no es imposible, pero hay que quererlo."""
    tono = normalizar(brief.tono)
    denominacion = normalizar(brief.periodo.denominacion)
    festivo = any(normalizar(p) in tono for p in TONOS_FESTIVOS)
    duelo = any(normalizar(p) in denominacion for p in PERIODOS_DE_DUELO)
    if festivo and duelo:
        return [
            f"El tono pedido es «{brief.tono}» y el periodo es «{brief.periodo.denominacion}». "
            f"Se puede escribir, pero conviene confirmarlo: no es lo que se espera de un "
            f"regalo."
        ]
    return []


def _datos_contra_prohibidas(brief: Brief) -> list[str]:
    """Un elemento de personalización que coincide con una palabra prohibida.

    Es la contradicción más incómoda y la que más falta hace detectar aquí: el comprador ha
    pedido a la vez que algo aparezca y que no aparezca, y descubrirlo con la novela escrita
    significa que el guardrail rechazará capítulos que hacían exactamente lo que se pidió.
    """
    problemas = []
    prohibidas = {normalizar(p.termino): p.termino for p in brief.palabras_prohibidas}
    for elemento in brief.elementos_personalizacion:
        normalizado = normalizar(elemento.valor)
        for aguja, original in prohibidas.items():
            if aguja and aguja in normalizado:
                problemas.append(
                    f"El elemento «{elemento.valor}» contiene el termino prohibido "
                    f"«{original}». Hay que quitar uno de los dos: tal como esta, el arnes "
                    f"rechazaria los capitulos que lo recojan."
                )
    return problemas
