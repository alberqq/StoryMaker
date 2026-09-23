"""spec: §3.5 · arq: §16.2

Vectorizador determinista para la suite.

No carga ningún modelo: reparte el peso de cada palabra en las 384 dimensiones con un
hash estable, de modo que dos textos que comparten vocabulario quedan próximos y dos que
no lo comparten quedan lejos. Es suficiente para comprobar lo que aquí se comprueba —que
el filtro entra en la consulta KNN, que `vigente` excluye lo descartado, que el índice se
escribe con la fila—, y evita que la suite dependa de descargar trescientos megas.

Lo que **no** sustituye es la calidad semántica del modelo real: eso no lo verifica una
prueba unitaria, sino los evals de G2 con el sistema entero corriendo.
"""

from __future__ import annotations

import hashlib
import math
import re

from storymaker.commons.config import Defaults

_PALABRA = re.compile(r"\w+", re.UNICODE)


class VectorizadorFalso:
    """Bolsa de palabras proyectada por hash. Determinista y sin red."""

    def __init__(self, dimension: int = Defaults.DIMENSION_EMBEDDINGS) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def vectorizar(self, textos: list[str]) -> list[list[float]]:
        return [self._uno(texto) for texto in textos]

    def _uno(self, texto: str) -> list[float]:
        vector = [0.0] * self._dimension
        for palabra in _PALABRA.findall(texto.lower()):
            digest = hashlib.sha256(palabra.encode("utf-8")).digest()
            posicion = int.from_bytes(digest[:4], "big") % self._dimension
            signo = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[posicion] += signo
        norma = math.sqrt(sum(x * x for x in vector))
        if norma == 0.0:
            # Un texto sin palabras no puede ser el vector cero: la distancia coseno no
            # está definida contra él y sqlite-vec devolvería NaN.
            vector[0] = 1.0
            return vector
        return [x / norma for x in vector]
