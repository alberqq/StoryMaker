"""spec: §2.1, §3.2 · arq: §8, §10, §16.4

**La única función que invoca el grafo.** La CLI y la API llaman aquí; ninguna de las dos
tiene un camino propio. Si lo tuvieran, habría dos implementaciones de la reanudación y
solo una estaría cubierta por las pruebas de integración.

Lo que termina en cada gate es **la invocación, no el servidor**: `invocar` avanza de nodo
en nodo hasta encontrar un `interrupt()` o hasta llegar al final, y entonces devuelve el
control. Entre una invocación y la siguiente no queda nada vivo —ni un hilo esperando, ni
una cola, ni una sesión de agente abierta—, y el servidor de FastAPI sigue en pie solo
porque atiende otras peticiones: de la novela no guarda nada, porque todo lo que sabía está
en su fichero.

**Arrancar y reanudar son el mismo camino de código.** `ResumeFromCheckpoint` no es un
estado del grafo sino una arista de entrada a cualquier nodo desde el checkpoint
persistido, y el mismo mecanismo sirve para reanudar tras un fallo, tras un gate y tras una
ramificación.
"""

from __future__ import annotations

import os
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from storymaker.commons.agents.invocacion import Consumo
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela
from storymaker.commons.db.repos import arnes
from storymaker.commons.graph import cerrojo
from storymaker.commons.graph.construccion import construir
from storymaker.commons.graph.dependencias import Dependencias, usando
from storymaker.commons.graph.estado import EstadoNovela, estado_inicial

if TYPE_CHECKING:
    from storymaker.commons.agents.invocacion import Transporte
    from storymaker.commons.embeddings.modelo import Vectorizador
    from storymaker.commons.obs.trazas import Observador


#: Con esta variable de entorno a uno, un nodo que revienta imprime su traza completa antes
#: de que `invocar` la reduzca a una cadena. El resultado no cambia —sigue siendo `Fail` y
#: el mensaje—, porque lo que la API y la CLI reciben no debe depender de una variable
#: suelta; lo único que cambia es que el rastro se ve. Sin esto, depurar un fallo a mitad de
#: una travesía de seis fases obliga a reconstruirlo desde una sola línea.
TRAZA_DE_FALLOS = "STORYMAKER_TRAZA_FALLOS"


@dataclass(frozen=True)
class Arranque:
    """Empezar una novela desde el principio.

    Lleva el encargo porque el grafo tiene que recibirlo por algún sitio: `Configure` lo
    primero que hace es entrevistar sobre la premisa, y una premisa vacía convierte la
    Fase 1 en un interrogatorio desde cero. Viaja aquí y no en `Settings` porque es de esta
    novela y no de esta instalación.
    """

    n_capitulos: int
    premisa: str = ""
    texto_pegado: str = ""
    fase: str = "intake"


@dataclass(frozen=True)
class Reanudacion:
    """Seguir donde se quedó.

    `decision` viene rellena cuando lo que reanuda es la respuesta del Autor a un gate;
    vacía cuando lo que se reanuda es un fallo. El grafo no distingue: recibe un
    `Command(resume=...)` en los dos casos.
    """

    decision: str | None = None
    comentario: str | None = None


@dataclass(frozen=True)
class ResultadoInvocacion:
    """Qué ocurrió: dónde se detuvo, qué gate quedó abierto y cuánto costó."""

    nodo_final: str
    gate_abierto: int | None = None
    consumo: Consumo = field(default_factory=Consumo)
    error: str | None = None

    @property
    def espera_al_autor(self) -> bool:
        return self.gate_abierto is not None


def _hilo(novela: Path) -> dict[str, Any]:
    """La configuración de hilo de LangGraph. Una novela, un hilo, siempre el mismo.

    Es lo que hace que el checkpoint de una novela no se mezcle con el de otra aunque las
    dos corran en el mismo proceso.
    """
    return {"configurable": {"thread_id": novela.stem}}


def _por_defecto(
    settings: Settings,
    transporte: Transporte | None,
    vectorizador: Vectorizador | None,
    observador: Observador | None,
) -> tuple[Transporte, Vectorizador, Observador]:
    """Las tres piezas caras, construidas solo si nadie las inyectó.

    Se construyen aquí dentro y no en el módulo porque cargar FastEmbed baja un modelo ONNX
    y abrir el transporte arranca un subproceso de Claude Code: importar este fichero no
    puede costar eso. Las pruebas inyectan sus dobles y no pagan ninguna de las dos cosas.
    """
    from storymaker.commons.obs import trazas

    if transporte is None:
        from storymaker.commons.agents.transporte_sdk import TransporteAgentSDK

        transporte = TransporteAgentSDK(techo_webfetch=settings.techo_webfetch_tokens)
    if vectorizador is None:
        from storymaker.commons.embeddings.modelo import FastEmbedVectorizador

        vectorizador = FastEmbedVectorizador(settings.modelo_embeddings)

    return transporte, vectorizador, observador or trazas.construir(settings)


async def invocar(
    novela: Path,
    entrada: Arranque | Reanudacion,
    *,
    settings: Settings,
    transporte: Transporte | None = None,
    vectorizador: Vectorizador | None = None,
    observador: Observador | None = None,
) -> ResultadoInvocacion:
    """Avanza la novela hasta el siguiente gate o hasta el final.

    Toma el cerrojo antes de nada y lo suelta pase lo que pase. Si un nodo revienta, la
    ejecución de fase queda registrada como fallida y **el último checkpoint queda
    intacto**: reanudar es el camino de siempre, y no hay ningún estado a medias que
    limpiar.

    Las tres dependencias que los nodos no pueden recibir por el estado —transporte,
    vectorizador y observador— se instalan aquí, en el contexto de invocación, y se retiran
    al salir. Son parámetros con valor por defecto para que las pruebas puedan inyectar sus
    dobles sin tocar ningún global.
    """
    piezas = _por_defecto(settings, transporte, vectorizador, observador)

    with cerrojo.tomar(novela):
        async with abrir_novela(novela) as db:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            checkpointer = AsyncSqliteSaver(db)
            grafo = construir(checkpointer=checkpointer)
            dependencias = Dependencias(
                db=db,
                settings=settings,
                transporte=piezas[0],
                vectorizador=piezas[1],
                observador=piezas[2],
                reanudando_gate=(
                    [True] if isinstance(entrada, Reanudacion) and entrada.decision else []
                ),
            )

            if isinstance(entrada, Arranque):
                fase_run_id = await arnes.abrir_fase_run(db, entrada.fase)
                estado: Any = estado_inicial(
                    novela=str(novela),
                    fase_run_id=fase_run_id,
                    premisa=entrada.premisa,
                    texto_pegado=entrada.texto_pegado,
                    n_capitulos=entrada.n_capitulos,
                    max_intentos=settings.reintentos_por_capitulo,
                    huecos=settings.huecos_por_plotting,
                    gates_enabled=settings.gates_enabled,
                )
            else:
                from langgraph.types import Command

                fase_run_id = 0
                estado = Command(resume=entrada.decision or "")

            try:
                with usando(dependencias):
                    final: EstadoNovela = await grafo.ainvoke(estado, config=_hilo(novela))
            except Exception as fallo:
                if fase_run_id:
                    await arnes.cerrar_fase_run(db, fase_run_id, estado="fallida")
                    await db.commit()
                if os.environ.get(TRAZA_DE_FALLOS):
                    traceback.print_exception(fallo)
                return ResultadoInvocacion(nodo_final="Fail", error=str(fallo))

            pendiente = await arnes.gate_pendiente(db)
            return ResultadoInvocacion(
                nodo_final=str(final.get("pc", "Fail")),
                gate_abierto=int(pendiente["id"]) if pendiente is not None else None,
                consumo=Consumo(
                    tokens_in=int(final.get("tokens_in", 0)),
                    tokens_out=int(final.get("tokens_out", 0)),
                    coste_usd=float(final.get("coste_usd", 0.0)),
                ),
            )


async def reanudar(
    novela: Path,
    *,
    settings: Settings,
    decision: str | None = None,
    comentario: str | None = None,
    transporte: Transporte | None = None,
    vectorizador: Vectorizador | None = None,
    observador: Observador | None = None,
) -> ResultadoInvocacion:
    """Azúcar sobre `invocar` con una `Reanudacion`. El camino es el mismo."""
    return await invocar(
        novela,
        Reanudacion(decision=decision, comentario=comentario),
        settings=settings,
        transporte=transporte,
        vectorizador=vectorizador,
        observador=observador,
    )
