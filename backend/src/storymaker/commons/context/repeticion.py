"""spec: §3.4 · arq: §6

Lo que la novela ya ha gastado: las palabras que más repite y las frases con que cierra.

El escritor solo lee N-1, así que la repetición de una novela escrita capítulo a capítulo
no la puede ver: cada capítulo repite «precisión» unas pocas veces, y la novela entera la
repite sesenta. Aquí se cuenta sobre los capítulos aprobados y se le dice cuál es, que es
lo mismo que haría un editor humano con la novela delante.

Python puro y determinista, como el resto del ensamblador: con los mismos textos salen las
mismas listas.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from itertools import pairwise

#: Palabras vacías del castellano que pasan del mínimo de longitud. Las de menos de cinco
#: letras ya las descarta el mínimo, así que la lista solo recoge las largas.
VACIAS = frozenset(
    {
        "aquel",
        "aquella",
        "aquello",
        "aquellos",
        "aquellas",
        "cuando",
        "donde",
        "entonces",
        "entre",
        "desde",
        "hasta",
        "hacia",
        "sobre",
        "mientras",
        "porque",
        "aunque",
        "tambien",
        "también",
        "siempre",
        "nunca",
        "nadie",
        "nada",
        "todos",
        "todas",
        "otros",
        "otras",
        "mismo",
        "misma",
        "mismos",
        "mismas",
        "cada",
        "tenia",
        "tenía",
        "habia",
        "había",
        "habían",
        "estaba",
        "estaban",
        "era",
        "eran",
        "fueron",
        "sabía",
        "podía",
        "sería",
        "estos",
        "estas",
        "esos",
        "esas",
        "ellos",
        "ellas",
        "después",
        "antes",
        "ahora",
        "todavía",
        "algo",
        "alguien",
        "como",
        "pero",
        "sino",
        "según",
        "dijo",
        "dice",
        "tiene",
        "tienen",
        "puede",
        "pueden",
        "debía",
        "hacer",
        "hubiera",
        "quien",
        "quién",
        "cuál",
        "cual",
        "este",
        "esta",
        "esto",
        "ese",
        "esa",
        "eso",
        "solo",
        "sólo",
        "menos",
        "manera",
        "forma",
        "tanto",
        "tanta",
        "muchos",
    }
)

LONGITUD_MINIMA = 5


def _palabras(texto: str) -> list[str]:
    return [p.lower() for p in re.findall(r"[^\W\d_]+", texto)]


def mas_repetidas(
    textos: Iterable[str],
    *,
    excluir: Iterable[str] = (),
    palabras: int = 8,
    expresiones: int = 4,
    minimo: int = 5,
) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    """Las palabras y las expresiones de dos palabras más frecuentes, con su recuento.

    Quedan fuera las palabras vacías y las de `excluir`, que son los nombres del canon: que
    el nombre de la homenajeada aparezca en cada página no es una repetición, es la novela.
    Solo entra lo que aparece al menos `minimo` veces; una expresión, al menos tres.
    """
    fuera = VACIAS | {p.lower() for nombre in excluir for p in _palabras(nombre)}

    def cuenta(p: str) -> bool:
        return len(p) >= LONGITUD_MINIMA and p not in fuera

    sueltas: Counter[str] = Counter()
    pares: Counter[str] = Counter()
    for texto in textos:
        tokens = _palabras(texto)
        sueltas.update(p for p in tokens if cuenta(p))
        pares.update(
            f"{a} {b}"
            for a, b in pairwise(tokens)
            if cuenta(a) or cuenta(b)
            if a not in fuera and b not in fuera and min(len(a), len(b)) >= 3
        )
    return (
        [(p, n) for p, n in sueltas.most_common(palabras) if n >= minimo],
        [(p, n) for p, n in pares.most_common(expresiones) if n >= 3],
    )


def ultima_frase(texto: str, *, maximo: int = 200) -> str:
    """La frase con la que cierra un capítulo, recortada si es muy larga."""
    frases = [f.strip() for f in re.split(r"(?<=[.!?…»])\s+", texto.strip()) if f.strip()]
    if not frases:
        return ""
    final = frases[-1]
    return final if len(final) <= maximo else final[: maximo - 1].rstrip() + "…"


def como_lista(recuentos: Sequence[tuple[str, int]]) -> str:
    return ", ".join(f"«{p}» ({n})" for p, n in recuentos)
