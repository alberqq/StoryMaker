"""spec: §3.2 · arq: §8

Realiza §9.1 y §9.2 de la spec de ejecución real.

La contabilidad de la invocación, **puesta al cablear y no en cada fase**.

`contabilizado` envuelve a los veinticuatro nodos del grafo. Antes de un nodo con fase
decide si empieza una `fase_run` nueva; después suma al estado y a la fila lo que el nodo
gastó en el modelo. Que el envoltorio sea uno es lo que hace que ninguna fase pueda
olvidarse de abrir su fila ni ningún nodo agente de contar su consumo: la cobertura sale de
la construcción, no de la disciplina de quien escribe la fase.

Se abre fila nueva en dos casos. Cuando **la fase cambia**, la anterior se cierra como
`completada`. Cuando **la fila abierta ya no está en curso**, que es lo que deja un gate: si
la decisión fue rehacer, el primer nodo es de la misma fase, y rehacer es una ejecución
nueva (arq. §8), no la continuación de la anterior.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from storymaker.commons.agents.invocacion import Consumo
from storymaker.commons.db.repos import arnes
from storymaker.commons.graph.dependencias import SinDependencias, actuales
from storymaker.commons.graph.estado import EstadoNovela
from storymaker.commons.graph.nodos import FASE_DE_NODO

Nodo = Callable[[EstadoNovela], Awaitable[EstadoNovela]]


def corpus_de(estado: EstadoNovela) -> int:
    """La `fase_run` bajo la que vive el corpus.

    Sin `corpus_run_id` —antes de Investigation, o en un checkpoint anterior a que cada
    fase abriera su fila— es la fila en curso, que en esas novelas era la única.
    """
    return estado.get("corpus_run_id") or estado["fase_run_id"]


async def _entrar(db: Any, estado: EstadoNovela, fase: str) -> EstadoNovela:
    """El estado con el que corre el nodo: el mismo, o apuntando a una fila nueva."""
    abierta = await arnes.fase_run_abierta(db)
    corpus = estado.get("corpus_run_id")
    if "corpus_run_id" not in estado:
        # Checkpoint anterior a este cambio: todas las fases compartían una fila.
        corpus = estado["fase_run_id"]

    if abierta is not None and abierta["fase"] == fase and abierta["estado"] == "en_curso":
        fase_run_id = int(abierta["id"])
    else:
        anterior = int(abierta["id"]) if abierta is not None else None
        if anterior is not None:
            await arnes.cerrar_abierta(db, "completada", desde=("en_curso", "esperando_gate"))
        fase_run_id = await arnes.abrir_fase_run(db, fase, input_run_id=anterior)
        if fase == "investigation":
            corpus = fase_run_id

    return {**estado, "fase_run_id": fase_run_id, "corpus_run_id": corpus}


def _consumo_actual(transporte: Any) -> Consumo:
    """Lo que lleva contado el transporte, o nada si no es un `TransporteContado`."""
    consumo = getattr(transporte, "consumo", None)
    return consumo if isinstance(consumo, Consumo) else Consumo()


def contabilizado(nombre: str, nodo: Nodo) -> Nodo:
    """El mismo nodo, con su fila de `fase_run` y su consumo a cuenta."""
    fase = FASE_DE_NODO.get(nombre)

    async def envuelto(estado: EstadoNovela) -> EstadoNovela:
        try:
            deps = actuales()
        except SinDependencias:
            return await nodo(estado)

        if fase is not None:
            estado = await _entrar(deps.db, estado, fase)
        antes = _consumo_actual(deps.transporte)
        try:
            salida = await nodo(estado)
        finally:
            # En `finally` para que la fila cuente también lo que gastó un nodo que revienta.
            gasto = _consumo_actual(deps.transporte) + Consumo(
                -antes.tokens_in, -antes.tokens_out, -antes.coste_usd
            )
            if gasto.tokens_in or gasto.tokens_out or gasto.coste_usd:
                await arnes.sumar_consumo(
                    deps.db,
                    estado["fase_run_id"],
                    tokens_in=gasto.tokens_in,
                    tokens_out=gasto.tokens_out,
                    coste_usd=gasto.coste_usd,
                )

        return {
            **salida,
            "fase_run_id": estado["fase_run_id"],
            "corpus_run_id": estado.get("corpus_run_id"),
            "tokens_in": salida.get("tokens_in", estado["tokens_in"]) + gasto.tokens_in,
            "tokens_out": salida.get("tokens_out", estado["tokens_out"]) + gasto.tokens_out,
            "coste_usd": salida.get("coste_usd", estado["coste_usd"]) + gasto.coste_usd,
        }

    envuelto.__name__ = getattr(nodo, "__name__", nombre)
    envuelto.__doc__ = nodo.__doc__
    return envuelto
