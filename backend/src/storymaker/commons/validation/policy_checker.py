"""spec: §3.6 · arq: §15

La policy del arnés: palabras prohibidas y datos personales.

`guardrail_prohibidas` es el más literal de los validadores y el que más claro deja por qué
el Core Domain es puro: la misma función decide si un capítulo generado por el escritor y
uno editado a mano por una persona cumplen la misma regla.

**La detección normaliza antes de comparar.** Mayúsculas, acentos, plurales y variantes
simples se reducen a una forma común, porque una lista que solo casa la forma exacta no
detecta nada. Lo que no cubre es la paráfrasis —una alusión sin nombrar—, que es un
problema semántico y abierto y queda declarado como riesgo aceptado U-4.
"""

from __future__ import annotations

from collections.abc import Sequence

from storymaker.commons.validation.modelos import (
    CapituloEnRevision,
    Incidencia,
    Severidad,
    TerminoProhibido,
)
from storymaker.commons.validation.puras import normalizar

#: Los tres niveles de §15, del más general al más personal.
NIVELES = ("global", "novela", "destinatario")

#: El nivel `global`, el único que pone el arnés y no el comprador. Se vuelca en
#: `canon_prohibida` junto a los de la novela al escribir el canon.
#:
#: Solo insultos y términos ofensivos sin otra acepción corriente. Una palabra con un
#: sentido inocente —«zorra», «capullo», «retrasado»— bloquearía capítulos limpios de una
#: novela histórica, y la comparación por raíz lo agrava: por eso no están.
PROHIBIDAS_GLOBALES: tuple[str, ...] = (
    "gilipollas",
    "hijo de puta",
    "hijoputa",
    "cabrón",
    "maricón",
    "subnormal",
    "sudaca",
    "negrata",
)


def guardrail_prohibidas(capitulo: CapituloEnRevision) -> list[Incidencia]:
    """Términos vetados en los tres niveles, normalizando antes de comparar.

    Cada coincidencia es bloqueante sin matices. El nivel `destinatario` —por ejemplo el
    nombre de una expareja— es el que justifica esa dureza: no hay grado de gravedad que
    discutir en una novela que se regala.
    """
    incidencias = []
    normalizado = normalizar(capitulo.texto)
    for prohibida in capitulo.prohibidas:
        if _aparece(prohibida, normalizado):
            incidencias.append(
                Incidencia(
                    validador="guardrail_prohibidas",
                    severidad=Severidad.BLOQUEANTE,
                    mensaje=(
                        f"Aparece el termino prohibido «{prohibida.termino}» "
                        f"(nivel {prohibida.nivel}). No puede figurar bajo ninguna forma."
                    ),
                    ubicacion=prohibida.termino,
                )
            )
    return incidencias


def _aparece(prohibida: TerminoProhibido, texto_normalizado: str) -> bool:
    """Compara por palabras completas, no por subcadena.

    Buscar la subcadena haría que «asa» saltara dentro de «casa». La comparación va sobre
    la secuencia de palabras ya normalizadas, que además es lo que permite que un término
    de varias palabras se detecte entero.
    """
    aguja = prohibida.normalizado or normalizar(prohibida.termino)
    if not aguja:
        return False
    palabras = texto_normalizado.split()
    agujas = aguja.split()
    n = len(agujas)
    if any(palabras[i : i + n] == agujas for i in range(len(palabras) - n + 1)):
        return True
    raiz = _raiz(aguja) if n == 1 else ""
    return bool(raiz) and any(raiz in palabra for palabra in palabras)


#: Por debajo de esta longitud la raíz ya no identifica la palabra: «asa» está en «casa».
_RAIZ_MINIMA = 4


def _raiz(palabra: str) -> str:
    """La palabra sin su vocal final, para cazar derivadas: «ruina» → «ruin».

    Con ella, «arruinada» cae por «ruina» y «herejía» por «hereje», que la comparación por
    palabra completa dejaba pasar. Solo se aplica a términos de una palabra y con raíz de
    al menos cuatro letras; por debajo, la comparación sigue siendo por palabra completa.
    """
    raiz = palabra[:-1] if len(palabra) > _RAIZ_MINIMA and palabra[-1] in "aeo" else palabra
    return raiz if len(raiz) >= _RAIZ_MINIMA else ""


def texto_libre_no_filtrado(prompt: str, textos_en_cuarentena: Sequence[str]) -> list[Incidencia]:
    """Ninguna cadena del texto pegado llega en bruto a un prompt.

    La defensa contra *prompt injection* de este sistema es **estructural**: el texto del
    comprador vive en cuarentena y solo avanza convertido en filas tipadas, de modo que una
    inyección tendría que sobrevivir a convertirse en una fila `persona`, `lugar`, `fecha`,
    `objeto` o `anecdota` para hacer daño. Esta comprobación es el cinturón sobre esa
    estructura: si alguna vez alguien concatenara el crudo, salta aquí.
    """
    incidencias = []
    for crudo in textos_en_cuarentena:
        muestra = crudo.strip()[:80]
        if muestra and muestra in prompt:
            incidencias.append(
                Incidencia(
                    validador="cuarentena_de_texto_libre",
                    severidad=Severidad.BLOQUEANTE,
                    mensaje=(
                        "Un fragmento del texto pegado por el comprador ha llegado en bruto "
                        "al prompt. Solo pueden viajar las filas tipadas que extrajo el rol "
                        "de intake."
                    ),
                    ubicacion=muestra,
                )
            )
    return incidencias


def pii_en_prompt_de_investigacion(
    prompt: str, datos_personales: Sequence[str]
) -> list[Incidencia]:
    """Los datos del homenajeado no salen por la única puerta a internet.

    El investigador es el único rol con red. Que su prompt se construya solo con periodo y
    lugar es una regla de Semgrep en el código; esto es la comprobación en ejecución sobre
    el prompt ya ensamblado, que es lo que la suite adversaria ejercita.
    """
    normalizado = normalizar(prompt)
    incidencias = []
    for dato in datos_personales:
        if dato and normalizar(dato) in normalizado:
            incidencias.append(
                Incidencia(
                    validador="pii_fuera_del_investigador",
                    severidad=Severidad.BLOQUEANTE,
                    mensaje=(
                        f"El prompt del investigador contiene un dato personal («{dato}»). "
                        f"Ese rol recibe periodo y lugar, y nada mas."
                    ),
                    ubicacion=dato,
                )
            )
    return incidencias
