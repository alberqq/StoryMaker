"""spec: §3.3 · arq: §12

La guarda de presupuesto: **se cuenta el prompt ensamblado antes de emitir y, si excede el
techo del rol, la llamada no se emite**.

Hay que ser honesto sobre lo que esto es y lo que no. El SDK no expone el tokenizador de
Anthropic para uso local, así que el recuento es una **estimación** y no una medida. Se
estima por lo alto —cuatro caracteres por token es la regla conocida, y aquí se aplica con
un margen— porque los dos errores no cuestan lo mismo: sobreestimar rechaza una llamada
que habría cabido y se nota en el acto; subestimar deja pasar una que revienta la ventana,
que es el fallo que §12 existe para impedir.

Lo que sí es exacto es el resto del método: los topes de herramientas y el truncado de las
respuestas se imponen por construcción, de modo que lo que entra por esa vía tiene un
máximo conocido de antemano y no depende de esta estimación.
"""

from __future__ import annotations

from typing import Final

from storymaker.commons.agents.techos import TECHOS, Perfil
from storymaker.commons.errores import PresupuestoExcedido

#: Caracteres por token en castellano, a la baja para que la estimación quede por lo alto.
CARACTERES_POR_TOKEN: Final = 3.5

#: Margen de seguridad sobre el techo declarado. El 5 % cubre la diferencia entre esta
#: estimación y el tokenizador real sin dejar inservible un techo ya ajustado.
MARGEN: Final = 0.95


def estimar_tokens(texto: str) -> int:
    """Estimación por lo alto del coste en tokens de un texto.

    No es una medida y el nombre lo dice. Quien necesite el número exacto lo tiene después
    en el `ResultMessage` del SDK, que es de donde salen el consumo y el coste reales.
    """
    return int(len(texto) / CARACTERES_POR_TOKEN) + 1


def presupuesto_disponible(perfil: Perfil) -> int:
    """Cuánto puede ocupar el prompt de este perfil, descontada su salida máxima."""
    techo = TECHOS[perfil]
    return int((techo.total - techo.salida_maxima) * MARGEN)


def guarda_techo(perfil: Perfil, prompt: str) -> int:
    """Comprueba antes de emitir. Devuelve la estimación; lanza si no cabe.

    Es una guarda estructural y no un validador: no produce incidencia ni veredicto, sino
    que **impide el acto**. El nodo que la recibe abre incidencia si quiere, pero la
    llamada ya no se ha hecho.
    """
    estimado = estimar_tokens(prompt)
    disponible = presupuesto_disponible(perfil)
    if estimado > disponible:
        raise PresupuestoExcedido(
            f"El prompt de {perfil.value} ocupa unos {estimado} tokens y su techo deja "
            f"{disponible} para la entrada. La llamada no se emite."
        )
    return estimado
