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
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from storymaker.commons.agents.contador import TransporteContado
from storymaker.commons.agents.invocacion import Consumo
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela
from storymaker.commons.db.repos import arnes
from storymaker.commons.errores import NadaQueReintentar
from storymaker.commons.graph import cerrojo
from storymaker.commons.graph.construccion import construir
from storymaker.commons.graph.dependencias import Dependencias, usando
from storymaker.commons.graph.estado import EstadoNovela, estado_inicial
from storymaker.gates.notifier import (
    Notifier,
    avisar_sin_fallar,
    aviso_de_parada,
    aviso_de_terminada,
)
from storymaker.gates.notifier import construir as construir_notifier

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
    notifier: Notifier | None = None,
) -> ResultadoInvocacion:
    """Avanza la novela hasta el siguiente gate o hasta el final.

    Toma el cerrojo antes de nada y lo suelta pase lo que pase. Si un nodo revienta, la
    ejecución de fase queda registrada como fallida y **el último checkpoint queda
    intacto**: reanudar es el camino de siempre, y no hay ningún estado a medias que
    limpiar.

    Las tres dependencias que los nodos no pueden recibir por el estado —transporte,
    vectorizador y observador— se instalan aquí, en el contexto de invocación, y se retiran
    al salir. Son parámetros con valor por defecto para que las pruebas puedan inyectar sus
    dobles sin tocar ningún global. `notifier` sigue la misma regla: sin él, el que diga
    `Settings`; las pruebas pasan un `NotifierNulo` y miran qué se le pidió.
    """
    piezas = _por_defecto(settings, transporte, vectorizador, observador)

    with cerrojo.tomar(novela):
        async with abrir_novela(novela) as db:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            checkpointer = AsyncSqliteSaver(db)
            grafo = construir(checkpointer=checkpointer)
            # El contador ve pasar cada llamada al modelo: de él sale el consumo de la
            # invocación, y el envoltorio de los nodos lo reparte por `fase_run`.
            contador = TransporteContado(piezas[0])
            dependencias = Dependencias(
                db=db,
                settings=settings,
                transporte=contador,
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
                    investigacion=settings.investigacion,
                )
            else:
                from langgraph.types import Command

                estado = Command(resume=entrada.decision or "")

            aviso = notifier or construir_notifier(settings)
            try:
                with usando(dependencias):
                    final: EstadoNovela = await grafo.ainvoke(estado, config=_hilo(novela))
            except Exception as fallo:
                # La fila abierta es la última de la base, también tras reanudar: antes solo
                # se cerraba la de un `Arranque`, y un fallo tras `continuar` no dejaba rastro.
                await arnes.cerrar_abierta(db, "fallida")
                await db.commit()
                if os.environ.get(TRAZA_DE_FALLOS):
                    traceback.print_exception(fallo)
                resultado = ResultadoInvocacion(
                    nodo_final="Fail", error=str(fallo), consumo=contador.consumo
                )
                await _avisar(db, aviso, novela, resultado, nodo=_ultimo_nodo(fallo))
                return resultado

            pendiente = await arnes.gate_pendiente(db)
            # El nodo `Fail` no reescribe `pc`, así que unos reintentos agotados llegan aquí
            # con el `pc` de quien los mandó —`Extract`, `Validate`, `Judge`—. Un grafo que
            # termina sin publicar y sin gate pendiente ha fallado, diga lo que diga `pc`.
            ultimo = str(final.get("pc", "Fail"))
            fallo_declarado = pendiente is None and ultimo != "Idle"
            resultado = ResultadoInvocacion(
                nodo_final="Fail" if fallo_declarado else ultimo,
                error=(
                    f"el grafo termino en Fail desde {ultimo}: reintentos agotados"
                    if fallo_declarado and ultimo != "Fail"
                    else None
                ),
                gate_abierto=int(pendiente["id"]) if pendiente is not None else None,
                # El de esta invocación. El estado acumula el de toda la novela.
                consumo=contador.consumo,
            )
            if pendiente is not None:
                await arnes.cerrar_abierta(db, "esperando_gate")
            else:
                cierre = "completada" if resultado.nodo_final == "Idle" else "fallida"
                await arnes.cerrar_abierta(db, cierre)
            await db.commit()
            if resultado.nodo_final == "Idle":
                await _imprimir_pdf(novela, settings)
            nodo = f"{ultimo}, capitulo {final.get('capitulo', '?')}"
            await _avisar(db, aviso, novela, resultado, nodo=nodo)
            return resultado


async def reintentar(
    novela: Path,
    *,
    settings: Settings,
    transporte: Transporte | None = None,
    vectorizador: Vectorizador | None = None,
    observador: Observador | None = None,
    notifier: Notifier | None = None,
) -> ResultadoInvocacion:
    """Reabre el capítulo que agotó sus reintentos y reanuda (arq. §16.5).

    Un `Fail` de capítulo termina el grafo: el checkpoint se queda sin nodo siguiente y
    `continuar` no tiene nada que retomar. Aquí se escribe en el checkpoint el estado de un
    capítulo recién empezado —intentos a cero, sin versión en curso— **como salida de
    `SealCorpus`**, cuya única arista lleva a `WriteChapter`, y se reanuda por el camino de
    siempre. Lo aprobado no se toca, y los intentos fallidos se quedan como filas.
    """
    with cerrojo.tomar(novela):
        async with abrir_novela(novela) as db:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            grafo = construir(checkpointer=AsyncSqliteSaver(db))
            foto = await grafo.aget_state(_hilo(novela))
            valores = foto.values
            if foto.next or not valores:
                raise NadaQueReintentar(
                    "La novela no ha terminado: usa `storymaker continuar` o decide su gate."
                )
            if await arnes.gate_pendiente(db) is not None:
                raise NadaQueReintentar("La novela espera tu decision en un gate.")
            if valores.get("pc") == "Idle":
                raise NadaQueReintentar("La novela esta publicada: no hay capitulo que reabrir.")
            if not valores.get("sellado") or valores["capitulo"] > valores["n_capitulos"]:
                raise NadaQueReintentar("La novela no se detuvo escribiendo un capitulo.")
            await grafo.aupdate_state(
                _hilo(novela),
                {
                    "pc": "WriteChapter",
                    "intentos": 0,
                    "capitulo_version_id": None,
                    "hay_bloqueantes": False,
                },
                as_node="SealCorpus",
            )
    return await invocar(
        novela,
        Reanudacion(),
        settings=settings,
        transporte=transporte,
        vectorizador=vectorizador,
        observador=observador,
        notifier=notifier,
    )


def _ultimo_nodo(fallo: BaseException) -> str:
    """El nodo del grafo en el que reventó la invocación, leído de la traza.

    Los nodos viven en módulos de fase (`writing.nodos`, `plotting.nodos`...), así que el
    último marco de la traza que caiga en uno de ellos nombra la función del nodo. Si no hay
    ninguno, el fallo ocurrió fuera del grafo y se dice así.
    """
    nodo = "fuera del grafo"
    for marco in traceback.extract_tb(fallo.__traceback__):
        if marco.filename.replace("\\", "/").endswith("/nodos.py"):
            nodo = marco.name
    return nodo


async def _imprimir_pdf(novela: Path, settings: Settings) -> None:
    """El PDF de las versiones que aún no lo tengan, **ya confirmado todo** (spec §4.5).

    Va aquí y no dentro de `publish` porque, dentro del paso, la versión nueva no es visible
    para otra conexión, y la ruta de impresión la lee por la API. Va antes de `_avisar` para
    que el aviso de terminada llegue con el PDF hecho. Y un fallo es un aviso: no cambia el
    resultado de la invocación ni su consumo, porque la versión ya está publicada y validada.
    """
    from storymaker.publication.render import imprimir_pendientes

    try:
        for destino in await imprimir_pendientes(novela, settings):
            print(f"PDF: {destino}", file=sys.stderr)
    except Exception as fallo:
        print(f"Aviso: version publicada, pero el PDF no se genero: {fallo}", file=sys.stderr)


async def _avisar(
    db: Any, notifier: Notifier, novela: Path, resultado: ResultadoInvocacion, *, nodo: str
) -> None:
    """Los avisos que no son de gate: la parada y el final.

    El gate avisa desde su propio nodo, porque es quien sabe qué informe resumir; lo que
    queda para aquí es lo que solo se sabe al salir del grafo. Salen **también en batch**,
    que es cuando nadie mira la terminal.
    """
    nombre = novela.stem
    if resultado.nodo_final == "Fail":
        motivo = resultado.error or "el grafo termino en Fail: reintentos agotados"
        await avisar_sin_fallar(notifier, aviso_de_parada(nombre, nodo=nodo, motivo=motivo))
    elif resultado.nodo_final == "Idle" and not resultado.espera_al_autor:
        async with db.execute("SELECT MAX(numero) AS n FROM version_novela") as cursor:
            fila = await cursor.fetchone()
        version = int(fila["n"]) if fila is not None and fila["n"] is not None else None
        await avisar_sin_fallar(
            notifier,
            aviso_de_terminada(nombre, version=version, coste_usd=resultado.consumo.coste_usd),
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
    notifier: Notifier | None = None,
) -> ResultadoInvocacion:
    """Azúcar sobre `invocar` con una `Reanudacion`. El camino es el mismo."""
    return await invocar(
        novela,
        Reanudacion(decision=decision, comentario=comentario),
        settings=settings,
        transporte=transporte,
        vectorizador=vectorizador,
        observador=observador,
        notifier=notifier,
    )
