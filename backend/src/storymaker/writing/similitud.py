"""spec: §7.2 · arq: §16.2

El linter de prosa por **auto-similitud**: el cuarto uso de los embeddings.

Compara el capítulo recién escrito con los anteriores y avisa cuando la repetición pasa del
umbral. No es uno de los once validadores de §11a, no gobierna ninguna arista y no bloquea:
es una señal para el informe del gate.

Que no bloquee es deliberado. La repetición en una novela no siempre es un defecto —un
motivo que vuelve, una fórmula que se repite a propósito— y un umbral de distancia coseno no
sabe distinguirlas. Lo que sí puede hacer es señalarle al Autor los dos capítulos que más
se parecen, que es información que él no tiene de otra manera y que a un lector le costaría
media tarde encontrar.
"""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite

from storymaker.commons.embeddings import indice
from storymaker.commons.embeddings.modelo import Vectorizador
from storymaker.commons.validation.modelos import Incidencia, Severidad

#: Distancia coseno por debajo de la cual dos capítulos se parecen demasiado. Con vectores
#: normalizados, 0 es idéntico y 2 es opuesto: 0,15 es «dicen casi lo mismo».
UMBRAL_DE_REPETICION = 0.15


@dataclass(frozen=True)
class Parecido:
    capitulo_version_id: int
    distancia: float


async def buscar_repeticion(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    *,
    resumen: str,
    capitulo_numero: int,
    umbral: float = UMBRAL_DE_REPETICION,
) -> list[Parecido]:
    """Los capítulos anteriores que se parecen demasiado a este.

    Se compara sobre el **resumen** y no sobre el texto entero, y no por ahorrar: dos
    capítulos con la misma estructura narrativa tienen resúmenes casi idénticos aunque su
    prosa sea distinta, y esa es precisamente la repetición que importa detectar.
    """
    vecinos = await indice.buscar_resumenes(
        db, vectorizador, resumen, anteriores_a=capitulo_numero, k=5
    )
    return [Parecido(v.id, v.distancia) for v in vecinos if v.distancia <= umbral]


def como_incidencias(parecidos: list[Parecido], capitulo_numero: int) -> list[Incidencia]:
    """Un aviso por capítulo repetido. Nunca bloqueante."""
    return [
        Incidencia(
            validador="auto_similitud",
            severidad=Severidad.AVISO,
            mensaje=(
                f"El capitulo {capitulo_numero} se parece mucho a un capitulo anterior "
                f"(distancia {parecido.distancia:.3f}). Puede ser un motivo que vuelve o "
                f"puede ser repeticion: lo decide quien lee."
            ),
            ubicacion=f"capitulo_version {parecido.capitulo_version_id}",
        )
        for parecido in parecidos
    ]
