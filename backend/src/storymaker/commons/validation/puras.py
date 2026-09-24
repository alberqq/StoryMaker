"""spec: §3.6, §7.1 · arq: §11a, §15

Las funciones puras críticas del Core Domain. Son las que CrossHair verifica
simbólicamente en G2, y están juntas por eso: lo que se puede garantizar por construcción
no se deja a una prueba, y para que una función sea verificable simbólicamente tiene que
ser pequeña, total y sin estado.

`truncar_por_prioridad`, la quinta de la lista, vive en `commons/context/truncado.py`
porque pertenece al ensamblador; se verifica igual y desde el mismo sitio.
"""

from __future__ import annotations

import re
import unicodedata

#: El guion bajo entra aqui aunque `\w` lo considere palabra: en un texto es
#: puntuacion, y dejarlo haria que «el_reloj» y «el reloj» no casaran.
_NO_ALFANUMERICO = re.compile(r"[^\w\s]|_", re.UNICODE)
_ESPACIOS = re.compile(r"\s+")


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos, sin puntuación y sin plurales simples.

    La detección de términos prohibidos **normaliza antes de comparar**, porque una lista
    de términos que solo casa la forma exacta no detecta nada: basta una mayúscula, una
    tilde o un plural para esquivarla. Lo que esto no cubre es la paráfrasis, que es un
    problema semántico y abierto, y queda declarado como riesgo aceptado U-4.

    post: normalizar(__return__) == __return__
    post: __return__ == __return__.lower()
    post: __return__ == __return__.strip()
    post: "  " not in __return__
    """
    # El orden importa, y lo descubrio una prueba de propiedades: hay caracteres que
    # `lower()` no baja pero que NFKD descompone en una mayuscula corriente —la ene
    # caligrafica, por ejemplo—. Normalizar primero y bajar despues deja siempre
    # minusculas; al reves, no.
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    limpio = _ESPACIOS.sub(" ", _NO_ALFANUMERICO.sub(" ", sin_tildes)).strip().lower()
    return " ".join(_singular(palabra) for palabra in limpio.split())


def _singular(palabra: str) -> str:
    """Plural castellano en su forma simple. No pretende ser un lematizador.

    **Recorta hasta punto fijo**, y eso no es un detalle de implementación: es lo que hace
    que la aguja y el pajar acaben en la misma forma. Un sustantivo que ya es singular y
    termina en ese —«autobús», «país», «análisis»— se recortaba una vez, y su plural dos,
    de modo que «autobús» quedaba en `autobu` y «autobuses» en `autobus`: el guardrail
    cazaba el término prohibido en singular y lo dejaba pasar en plural. Recortando hasta
    que deje de haber sufijo que quitar, los dos caminos terminan en el mismo sitio.

    El precio es recortar de más y juntar alguna palabra que no debería juntarse, y se paga
    a sabiendas: en una lista de términos prohibidos, un falso positivo es una incidencia
    que el Autor ve en el informe y un falso negativo es una palabra vetada impresa en el
    regalo.

    La recursión termina siempre porque cada vuelta acorta la cadena al menos un carácter y
    las guardas de longitud ponen el suelo.
    """
    while True:
        if len(palabra) > 4 and palabra.endswith("es"):
            palabra = palabra[:-2]
            continue
        if len(palabra) > 3 and palabra.endswith("s"):
            palabra = palabra[:-1]
            continue
        return palabra


def anio_de(fecha: str | None) -> int | None:
    """El año de una fecha ISO, o `None` si no hay fecha utilizable.

    Se trabaja con el año y no con la fecha completa porque las fechas del corpus vienen
    con precisión desigual —«1805», «1805-04», «1805-04-11»— y exigir formato completo
    dejaría fuera la mitad del material histórico.

    post: __return__ is None or 0 <= __return__ <= 9999
    """
    if not fecha:
        return None
    cabeza = fecha.strip()[:4]
    # `isdigit()` acepta cosas que `int()` rechaza —el dígito uno entre paréntesis, los
    # subíndices, los dígitos de otros sistemas de escritura—, y con esa comprobación la
    # función dejaba de ser total: una fecha con un carácter raro reventaba dentro del
    # validador en lugar de devolver `None`. Lo encontró CrossHair, que es exactamente la
    # clase de borde que nadie escribe a mano en una prueba. Aquí las fechas son ISO, así
    # que se exige ASCII y se acabó la ambigüedad.
    if len(cabeza) == 4 and cabeza.isascii() and cabeza.isdigit():
        return int(cabeza)
    return None


def es_anacronico(fecha_inicio: str | None, fecha_narrativa: str | None) -> bool:
    """¿Existe ya esa cosa en ese momento de la novela?

    Devuelve `False` cuando falta cualquiera de las dos fechas, y es deliberado: un objeto
    sin fecha de aparición documentada no es un anacronismo, es un dato que no tenemos, y
    convertir la ignorancia en incidencia llenaría el informe de ruido.

    post: not __return__ or (fecha_inicio is not None and fecha_narrativa is not None)
    """
    inicio = anio_de(fecha_inicio)
    narrativa = anio_de(fecha_narrativa)
    if inicio is None or narrativa is None:
        return False
    return inicio > narrativa


def hay_solape_temporal(
    inicio_a: str | None, fin_a: str | None, inicio_b: str | None, fin_b: str | None
) -> bool:
    """¿Coexisten dos periodos?

    Lo usa el detector de presencias imposibles: un personaje histórico solo puede aparecer
    en una escena si sus fechas vitales solapan con la fecha de la escena. Un extremo
    abierto se trata como «sin límite por ese lado», que es lo que significa no saber
    cuándo murió alguien.

    La simetría es el contrato que importa: si el orden de los dos periodos cambiara el
    veredicto, el validador de presencias imposibles daría un resultado distinto según en
    qué orden leyera las filas de la base.

    post: __return__ == hay_solape_temporal(inicio_b, fin_b, inicio_a, fin_a)
    """
    a1, a2 = anio_de(inicio_a), anio_de(fin_a)
    b1, b2 = anio_de(inicio_b), anio_de(fin_b)
    if a1 is not None and b2 is not None and a1 > b2:
        return False
    return not (b1 is not None and a2 is not None and b1 > a2)


def capitulos_afectados(usos: dict[int, tuple[int, ...]], hecho_id: int) -> list[int]:
    """Qué capítulos hay que regenerar si cambia un hecho.

    La versión pura de la consulta de la Fase 6. Devuelve la lista **ordenada** porque el
    orden gobierna en qué secuencia se regenera, y una regeneración que empezara por el
    capítulo 9 y siguiera por el 2 dejaría al 9 escrito contra una continuidad que el 2 va
    a cambiar.

    post: __return__ == sorted(__return__)
    post: set(__return__) == set(usos.get(hecho_id, ()))
    """
    return sorted(usos.get(hecho_id, ()))


#: De más a menos firme. `inventado` no está: no es un grado de lo documentado sino una
#: licencia, y no se compara con los demás.
ORDEN_DE_FIRMEZA = ("documentado", "debatido", "inferido", "desconocido")

#: Lo más que puede valer un hecho cuya cita nadie ha comprobado que lo sostenga.
TECHO_SIN_RESPALDO = "inferido"

#: Cómo se lee cada estado declarado en la escala de firmeza.
_FIRMEZA_DECLARADA = {
    "verificado": "documentado",
    "debatido": "debatido",
    "inferido": "inferido",
    "desconocido": "desconocido",
}


def firmeza(estado: str, respaldo: str, origen: str) -> str:
    """Cuánto puede apoyarse la obra en un hecho (arq. §7).

    No se guarda: se calcula al leer, a partir de lo que declaró quien creó la fila
    (`estado`), de lo que dictó el verificador (`respaldo`) y de dónde salió (`origen`).
    Cada una de esas columnas tiene un solo dueño, y esta función es la única que las junta.

    La regla es un mínimo: lo declarado, recortado por el techo que permite el respaldo. Un
    hecho sin respaldo comprobado —`no_respaldado` o todavía `pendiente`— no pasa de
    `inferido`, de modo que una cita floja **nunca sube a nadie de categoría**: un
    `desconocido` sin respaldo sigue siendo `desconocido`. Una invención autorizada es
    `inventado` sea cual sea lo demás. Es total: un estado que no reconoce cuenta como
    `desconocido`, que es el suelo.

    post: __return__ in ORDEN_DE_FIRMEZA or __return__ == "inventado"
    """
    if origen == "invencion_autorizada":
        return "inventado"
    declarada = _FIRMEZA_DECLARADA.get(estado, "desconocido")
    if respaldo == "respaldado":
        return declarada
    return max(declarada, TECHO_SIN_RESPALDO, key=ORDEN_DE_FIRMEZA.index)


def anadido_vigente(enunciado: str, sin_respaldo: str | None) -> str | None:
    """Lo que el enunciado añade y su cita no dice, **si sigue en el enunciado**.

    Es el añadido del veredicto parcial (arq. §4, Fase 2). El verificador lo copió del
    enunciado tal como era; si después el Autor corrige el hecho y lo quita, ya no hay nada
    que señalar, y reescribir el veredicto no es cosa suya.

    Se compara normalizado y **por palabras significativas**, no por copia literal: el
    verificador a veces lo copia con otras palabras —«para la Exposición de 1888» frente a
    «para la Exposición Universal de 1888»—, y exigir la copia exacta escondía la nota. Son
    significativas las palabras de más de tres letras y los números; si el añadido no tiene
    ninguna, cuentan todas.

    post: __return__ is None or __return__ == sin_respaldo
    """
    if not sin_respaldo:
        return None
    anadido = normalizar(sin_respaldo)
    if not anadido:
        return None
    texto = normalizar(enunciado)
    if anadido in texto:
        return sin_respaldo
    palabras = anadido.split()
    significativas = [p for p in palabras if len(p) > 3 or p.isdigit()] or palabras
    presentes = set(texto.split())
    return sin_respaldo if all(p in presentes for p in significativas) else None
