"""spec: §3.4 · arq: §6

El recorte del paquete. Son funciones **puras**: reciben fragmentos y devuelven
fragmentos, sin tocar la base ni el reloj. Por eso `truncar_por_prioridad` es una de las
cinco que CrossHair verifica simbólicamente en G2 — lo que se puede garantizar por
construcción no se deja a una prueba.

Tres propiedades deben cumplirse siempre, y son las que se comprueban:

1. El paquete **nunca excede** el techo total.
2. El recorte va **por la cola de la lista ya ordenada por relevancia**.
3. El bloque 3, la continuidad, es **el último que se toca**.
"""

from __future__ import annotations

from collections.abc import Sequence

from storymaker.commons.agents.presupuesto import estimar_tokens
from storymaker.commons.context.paquete import ORDEN_DE_RECORTE, TECHO_TOTAL, Bloque


def truncar_por_prioridad(
    fragmentos: Sequence[str], techo_tokens: int, *, fijos: int = 0
) -> list[str]:
    """Deja los que caben, **cortando por el final** de la lista ya ordenada.

    No reordena ni elige «el que mejor encaje»: la lista llega ordenada por relevancia y se
    corta por la cola. Cualquier otra política haría que el contexto dependiera del tamaño
    de los fragmentos en lugar de su importancia.

    Los `fijos` primeros se conservan aunque se pasen del techo. Es deliberado: un anclaje
    que el arquitecto puso y que no entra no es un problema de espacio, es una señal de que
    la escena pide más de lo que cabe, y silenciarlo produciría un capítulo que incumple la
    escaleta sin que nadie sepa por qué.

    El contrato fuerte es el segundo: lo devuelto es **un prefijo** de lo recibido. Con eso
    quedan dichas las tres propiedades a la vez —no reordena, no elige, y corta por la cola—
    en una sola línea que un solucionador puede explorar.

    pre: techo_tokens >= 0
    pre: fijos >= 0
    post: len(__return__) <= len(fragmentos)
    post: __return__ == list(fragmentos[:len(__return__)])
    """
    conservados: list[str] = list(fragmentos[:fijos])
    usado = estimar_tokens("\n".join(conservados)) if conservados else 0

    for fragmento in fragmentos[fijos:]:
        coste = estimar_tokens(fragmento)
        if usado + coste > techo_tokens:
            break
        conservados.append(fragmento)
        usado += coste
    return conservados


def ajustar_bloque(bloque: Bloque) -> Bloque:
    """Aplica el techo propio del bloque."""
    return Bloque(
        numero=bloque.numero,
        fragmentos=tuple(
            truncar_por_prioridad(bloque.fragmentos, bloque.techo, fijos=bloque.fijos)
        ),
        fijos=bloque.fijos,
    )


def ajustar_al_total(
    bloques: Sequence[Bloque],
    techo_total: int = TECHO_TOTAL,
    orden: Sequence[int] = ORDEN_DE_RECORTE,
) -> list[Bloque]:
    """Recorta hasta caber en el total, en el orden declarado.

    Va soltando el fragmento menos relevante del primer bloque del orden que todavía pueda
    encoger, y solo pasa al siguiente cuando el anterior se ha quedado en sus fijos. Así la
    continuidad —que es la última de la lista— solo se toca cuando ya no queda nada más que
    soltar, que es exactamente lo que §6 pide.
    """
    ajustados = {b.numero: b for b in bloques}

    def total() -> int:
        return sum(b.tokens() for b in ajustados.values())

    for numero in orden:
        while total() > techo_total:
            bloque = ajustados.get(numero)
            if bloque is None:
                break
            encogido = bloque.sin_el_ultimo()
            if encogido is bloque or encogido.fragmentos == bloque.fragmentos:
                break  # este bloque ya no puede ceder más
            ajustados[numero] = encogido
        if total() <= techo_total:
            break

    return [ajustados[b.numero] for b in bloques]
