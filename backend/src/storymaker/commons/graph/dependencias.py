"""spec: §3.2 · arq: §16.4

Cómo llegan a un nodo las cosas que no caben en el estado.

LangGraph le pasa a cada nodo **solo el estado**, y el estado es pequeño a propósito: lleva
punteros, no objetos vivos. Pero un nodo necesita la conexión a la novela, el transporte al
modelo, el vectorizador y el observador, y ninguno de los cuatro puede viajar en un
`TypedDict` que se serializa en cada checkpoint.

La solución es un contexto de invocación: `invocar` lo monta una vez, los nodos lo leen y
se deshace al terminar. Es deliberadamente un `ContextVar` y no una variable global: las
pruebas construyen el suyo, y dos novelas que corrieran a la vez en el mismo proceso no se
pisarían.

Lo que **no** se hace aquí es esconder la configuración: `Settings` sigue siendo un objeto
inyectado que alguien construyó arriba, y este módulo solo lo transporta hasta el nodo.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

    from storymaker.commons.agents.invocacion import Transporte
    from storymaker.commons.config import Settings
    from storymaker.commons.embeddings.modelo import Vectorizador
    from storymaker.commons.obs.trazas import Observador


@dataclass(frozen=True)
class Dependencias:
    """Lo que todo nodo necesita y el estado no puede llevar."""

    db: aiosqlite.Connection
    settings: Settings
    transporte: Transporte
    vectorizador: Vectorizador
    observador: Observador


_ACTUAL: ContextVar[Dependencias | None] = ContextVar("dependencias", default=None)


class SinDependencias(RuntimeError):
    """Un nodo se ejecutó fuera de una invocación.

    Es una avería y no una incidencia: significa que alguien llamó al nodo directamente,
    sin el contexto que `invocar` monta, y lo que hiciera a continuación escribiría en una
    base que no es la suya o no escribiría en ninguna.
    """


def actuales() -> Dependencias:
    dependencias = _ACTUAL.get()
    if dependencias is None:
        raise SinDependencias(
            "Este nodo se ejecuto fuera de una invocacion: no hay conexion ni transporte."
        )
    return dependencias


@contextmanager
def usando(dependencias: Dependencias) -> Iterator[Dependencias]:
    """Instala el contexto durante una invocación y lo retira al salir."""
    testigo = _ACTUAL.set(dependencias)
    try:
        yield dependencias
    finally:
        _ACTUAL.reset(testigo)
