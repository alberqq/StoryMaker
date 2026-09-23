"""spec: §3.5 · arq: §16.2

El vectorizador. Corre **en local sobre ONNX**: sin llamada de red, sin credenciales y
sin catálogo externo que pueda cambiar bajo los pies. Con el modelo fijado, el mismo
texto produce siempre el mismo vector, de modo que la búsqueda semántica es determinista
y no erosiona la reproducibilidad que promete §13.

Se expone como **protocolo** y no como clase concreta por una razón práctica: cargar el
modelo cuesta un par de segundos y unos cientos de megas, y la suite necesita poder
sustituirlo por un doble determinista sin tocar nada más. El arnés en producción usa
siempre `FastEmbedVectorizador`, y qué modelo se usó viaja en el manifiesto.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, Protocol, runtime_checkable

from storymaker.commons.config import Defaults

if TYPE_CHECKING:
    from fastembed import TextEmbedding

#: FastEmbed nombra los modelos con su organización delante.
NOMBRE_EN_FASTEMBED: Final = f"sentence-transformers/{Defaults.MODELO_EMBEDDINGS}"


@runtime_checkable
class Vectorizador(Protocol):
    """Lo único que el resto del sistema necesita saber de un modelo de embeddings."""

    @property
    def dimension(self) -> int: ...

    def vectorizar(self, textos: list[str]) -> list[list[float]]: ...


class FastEmbedVectorizador:
    """FastEmbed sobre ONNX, con el modelo de §19 y sus 384 dimensiones.

    El modelo se carga **la primera vez que se vectoriza**, no al construir el objeto: la
    CLI es un proceso por comando y `storymaker estado` no tiene por qué pagar la carga de
    un modelo que no va a usar.
    """

    def __init__(self, nombre: str = NOMBRE_EN_FASTEMBED) -> None:
        self._nombre = nombre
        self._modelo: TextEmbedding | None = None

    @property
    def dimension(self) -> int:
        return Defaults.DIMENSION_EMBEDDINGS

    @property
    def nombre(self) -> str:
        return self._nombre

    def vectorizar(self, textos: list[str]) -> list[list[float]]:
        if self._modelo is None:
            from fastembed import TextEmbedding

            self._modelo = TextEmbedding(model_name=self._nombre)
        return [[float(x) for x in vector] for vector in self._modelo.embed(textos)]
