"""spec: §4.7 · arq: §9, §10

Los cinco gates. El nodo llama a `interrupt()`, **el checkpointer persiste y la invocación
termina**.

Tres consecuencias encadenadas, y las tres importan: no hay un proceso vivo doce horas
esperando; reiniciar el servidor no mata nada porque el estado está en disco y no en
memoria; y **la reanudación por gate usa exactamente el mismo mecanismo que la reanudación
por fallo** — un solo camino de código.

Los cuatro estados de gate del modelo comparten esta implementación porque lo que hacen es
idéntico. Lo único que cambia es qué informe se le enseña al Autor, y eso lo decide la fase,
no el nodo.

**En modo batch los gates se desactivan enteros.** Es imprescindible y no un lujo: los cinco
briefs de evaluación tienen que correr desatendidos, y si cada uno pidiera cinco
aprobaciones la tabla de resultados no se terminaría nunca.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from storymaker.commons.db.repos import arnes
from storymaker.commons.graph.aristas import tras_gate
from storymaker.commons.graph.dependencias import actuales
from storymaker.commons.graph.estado import EstadoNovela
from storymaker.commons.graph.nodos import GATES, NOMBRE_DE_FASE
from storymaker.gates.decisiones import DECISIONES
from storymaker.gates.notifier import Aviso, avisar_sin_fallar, aviso_de_aparcada, construir


async def abrir(estado: EstadoNovela, *, titulo: str, informe: str, movil: str = "") -> int:
    """Escribe el gate pendiente y notifica. Devuelve su identificador.

    Van dos textos y no uno: el informe entero sale por la salida del proceso, que es donde
    se decide y se lee; al móvil va `movil`, el resumen de cifras, porque un informe de
    treinta líneas en Telegram no se lee y tapa lo único que el aviso tiene que decir.
    """
    deps = actuales()
    gate_id = await arnes.abrir_gate(deps.db, estado["fase_run_id"])
    print(f"\n{titulo}\n{informe}\n", file=sys.stderr)
    notifier = construir(deps.settings)
    await notifier.enviar(
        Aviso(
            titulo=titulo,
            cuerpo=movil or informe,
            gate_id=gate_id,
            decisiones=tuple(d.value for d in DECISIONES),
            novela=Path(estado["novela"]).stem,
        )
    )
    return gate_id


def nombre_del_gate(estado: EstadoNovela, gate: str = "") -> str:
    """Cuál de los cuatro gates se está ejecutando.

    Los cuatro comparten función, así que la función tiene que saber quién es. El nombre lo
    inyecta `construir` al cablear el grafo, y **no se deduce de `pc`**: `pc` lo escribe el
    nodo anterior, y no todos nombran a su sucesor —`Checkpoint` se nombra a sí mismo y es
    una arista condicional la que decide si lo siguiente es el gate de Writing—.
    """
    if gate in GATES:
        return gate
    actual = estado["pc"]
    return actual if actual in GATES else "AwaitApproval"


async def await_approval(estado: EstadoNovela, gate: str = "") -> EstadoNovela:
    """El nodo de los cuatro gates.

    En modo batch no interrumpe: resuelve por «aprobar» y la invocación sigue. En
    interactivo llama a `interrupt()`, y lo que ocurre después no es cosa de este nodo —
    el proceso termina y la decisión entra por `Command(resume=...)`.
    """
    gate = nombre_del_gate(estado, gate)

    if not estado["gates_enabled"]:
        if gate == "AwaitApproval4":
            from storymaker.writing import gate as manuscrito

            await manuscrito.revisar(actuales().db, actuales().observador)
        return {
            **estado,
            "gate_id": None,
            "pc": tras_gate(estado, gate=gate, decision="aprobar"),
        }

    from langgraph.types import interrupt

    gate_id = estado.get("gate_id")
    if not actuales().consumir_reanudacion():
        # Primera pasada por este gate: se escribe pendiente y se avisa. Al reanudar, el
        # nodo vuelve a correr desde aquí y la marca evita abrirlo y avisar dos veces.
        if gate == "AwaitApproval4":
            from storymaker.writing import gate as manuscrito

            await manuscrito.revisar(actuales().db, actuales().observador)
        fase = GATES.get(gate, gate)
        nombre = NOMBRE_DE_FASE.get(fase, fase)
        titulo = f"StoryMaker · {Path(estado['novela']).stem} · {nombre}: espera tu decisión"
        gate_id = await abrir(
            estado,
            titulo=titulo,
            informe=await _resumen(gate, estado),
            movil=await resumen_movil(gate, estado),
        )
    decision: Any = interrupt(
        {
            "gate": gate,
            "fase": GATES.get(gate, "desconocida"),
            "capitulo": estado["capitulo"],
        }
    )
    elegida = str(decision) or "aprobar"
    base = await _rehacer_writing(estado) if _rehace_writing(gate, elegida) else estado
    return {
        **base,
        "gate_id": gate_id,
        "hay_bloqueantes": elegida != "aprobar",
        "pc": tras_gate(estado, gate=gate, decision=elegida),
    }


def _rehace_writing(gate: str, decision: str) -> bool:
    return gate == "AwaitApproval4" and decision in ("rehacer", "editar")


async def _rehacer_writing(estado: EstadoNovela) -> EstadoNovela:
    """Rehacer en el gate de Writing entra en modo regeneración sobre los capítulos citados.

    Los citan las contradicciones del juez y los rechazos de la publicación; sin citas, el
    último. Es lo que el modelo llama `RehacerWriting`: la misma operación que regenerar,
    con otro punto de entrada, de modo que `Checkpoint` saca los siguientes de `a_regenerar`
    y con la cola vacía vuelve a este gate.
    """
    from storymaker.writing import gate as manuscrito

    pendientes = await manuscrito.capitulos_a_rehacer(actuales().db, estado["n_capitulos"])
    return {
        **estado,
        "regenerando": True,
        "capitulo": pendientes[0],
        "a_regenerar": pendientes[1:],
        "intentos": 0,
        "capitulo_version_id": None,
    }


#: Qué se cuenta en el aviso de cada gate. Es un resumen para el móvil; el informe entero
#: se lee en el PC, que es donde se decide.
_RESUMENES: dict[str, tuple[tuple[str, str], ...]] = {
    "AwaitApproval": (
        ("datos del encargo", "SELECT COUNT(*) FROM intake_dato"),
        ("avisos del brief", "SELECT COUNT(*) FROM incidencia WHERE capitulo_version_id IS NULL"),
    ),
    "AwaitApproval2": (
        ("hechos en el corpus", "SELECT COUNT(*) FROM mundo_hecho"),
        ("fuentes", "SELECT COUNT(*) FROM mundo_fuente"),
    ),
    "AwaitApproval3": (
        ("capitulos en la escaleta", "SELECT COUNT(*) FROM plan_capitulo"),
        ("escenas", "SELECT COUNT(*) FROM plan_escena"),
        ("personajes", "SELECT COUNT(*) FROM canon_personaje"),
    ),
    "AwaitApproval4": (
        (
            "capitulos aprobados",
            "SELECT COUNT(*) FROM capitulo_version WHERE estado = 'aprobado'",
        ),
        (
            "incidencias abiertas",
            "SELECT COUNT(*) FROM incidencia WHERE capitulo_version_id IS NOT NULL",
        ),
    ),
}


async def _resumen(gate: str, estado: EstadoNovela | None = None) -> str:
    deps = actuales()
    lineas = []
    for etiqueta, consulta in _RESUMENES.get(gate, ()):
        async with deps.db.execute(consulta) as cursor:
            fila = await cursor.fetchone()
        lineas.append(f"- {etiqueta}: {fila[0] if fila is not None else 0}")
    if gate == "AwaitApproval":
        preguntas = await arnes.incidencias_sin_capitulo(deps.db, "pregunta_del_entrevistador")
        if preguntas:
            lineas += ["", "El entrevistador pregunta:"]
            lineas += [f"  {i}. {p}" for i, p in enumerate(preguntas, start=1)]
            lineas += ["", 'Contesta con: rehacer --comentario "tus respuestas"']
    if gate == "AwaitApproval4":
        from storymaker.writing import gate as manuscrito

        lineas += ["", (await manuscrito.construir(deps.db)).como_texto()]
    if gate == "AwaitApproval3":
        # El informe de la trama entero: los huecos, lo inventado y lo que encontró la
        # revisión. Es lo que el Autor tiene que leer para decidir si rehace.
        from storymaker.commons.graph.contabilidad import corpus_de
        from storymaker.plotting import gate as revision
        from storymaker.plotting import informe

        puerta = revision.PuertaDePlotting(tuple(await revision.incidencias_guardadas(deps.db)))
        corpus = corpus_de(estado) if estado is not None else 0
        resumen = await informe.construir(deps.db, corpus, puerta, huecos_gastados=0)
        lineas += ["", resumen.como_texto()]
    lineas.append("")
    lineas.append("La invocacion se ha detenido y espera tu decision.")
    return "\n".join(lineas)


#: Lo que se cuenta en el aviso del móvil de cada gate: una línea de cifras.
_CIFRAS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "AwaitApproval": (
        ("dato del encargo", "datos del encargo", "SELECT COUNT(*) FROM intake_dato"),
    ),
    "AwaitApproval2": (
        ("hecho", "hechos", "SELECT COUNT(*) FROM mundo_hecho"),
        ("fuente", "fuentes", "SELECT COUNT(*) FROM mundo_fuente"),
    ),
    "AwaitApproval3": (
        ("capítulo", "capítulos", "SELECT COUNT(*) FROM plan_capitulo"),
        ("escena", "escenas", "SELECT COUNT(*) FROM plan_escena"),
        ("personaje", "personajes", "SELECT COUNT(*) FROM canon_personaje"),
    ),
    "AwaitApproval4": (
        (
            "capítulo aprobado",
            "capítulos aprobados",
            "SELECT COUNT(*) FROM capitulo_version WHERE estado = 'aprobado'",
        ),
        (
            "incidencia",
            "incidencias",
            "SELECT COUNT(*) FROM incidencia WHERE capitulo_version_id IS NOT NULL",
        ),
    ),
}


async def resumen_movil(gate: str, estado: EstadoNovela | None = None) -> str:
    """El cuerpo del aviso de Telegram: cifras, lo que pide respuesta y nada más.

    Las preguntas del entrevistador sí van enteras, porque son lo que hay que contestar; de
    la Trama van los huecos y los avisos agrupados por tipo. «Decide en el PC» lo añade el
    notificador.
    """
    deps = actuales()
    cifras: list[str] = []
    for singular, plural, consulta in _CIFRAS.get(gate, ()):
        async with deps.db.execute(consulta) as cursor:
            fila = await cursor.fetchone()
        n = int(fila[0]) if fila is not None else 0
        cifras.append(f"{n} {singular if n == 1 else plural}")
    lineas = [" · ".join(cifras)] if cifras else []
    if gate == "AwaitApproval":
        preguntas = await arnes.incidencias_sin_capitulo(deps.db, "pregunta_del_entrevistador")
        if preguntas:
            lineas += ["", "El entrevistador pregunta:"]
            lineas += [f"{i}. {p}" for i, p in enumerate(preguntas, start=1)]
        else:
            avisos = await arnes.incidencias_sin_capitulo(deps.db, "contradiccion_del_brief")
            lineas += [f"Aviso: {a}" for a in avisos]
    if gate == "AwaitApproval3":
        from storymaker.commons.graph.contabilidad import corpus_de
        from storymaker.plotting import gate as revision
        from storymaker.plotting import informe

        puerta = revision.PuertaDePlotting(tuple(await revision.incidencias_guardadas(deps.db)))
        corpus = corpus_de(estado) if estado is not None else 0
        resumen = await informe.construir(deps.db, corpus, puerta, huecos_gastados=0)
        lineas += resumen.como_resumen()
    if gate == "AwaitApproval4":
        contradicciones = await arnes.incidencias_sin_capitulo(deps.db, "juez_contradiccion")
        if contradicciones:
            lineas.append(f"El juez encontró {len(contradicciones)} contradicción(es)")
    return "\n".join(lineas)


async def aparcar(estado: EstadoNovela, gate_id: int) -> EstadoNovela:
    """El *timeout*: la ejecución se **aparca**, con estado propio.

    **No hay auto-aprobación**, porque eso convertiría un gate de calidad en un
    temporizador. Una ejecución aparcada sigue viva y esperando: lo único que ha pasado es
    que el arnés ha dejado de esperar despierto.
    """
    deps = actuales()
    await deps.db.execute("UPDATE gate SET estado = 'aparcado' WHERE id = ?", (gate_id,))
    await arnes.cerrar_fase_run(deps.db, estado["fase_run_id"], estado="aparcada")
    # Aparcar sin avisar dejaria al Autor creyendo que la novela sigue esperando despierta.
    gate = GATES.get(nombre_del_gate(estado), "desconocido")
    await avisar_sin_fallar(
        construir(deps.settings), aviso_de_aparcada(Path(estado["novela"]).stem, gate=gate)
    )
    return {**estado, "gate_id": gate_id}
