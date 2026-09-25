"""spec: §3.2 · arq: §1, §9

Las transiciones del grafo, declaradas una sola vez, y los enrutadores que las eligen.

**Las aristas condicionales leen booleanos calculados en Python**, nunca la salida de un
modelo. Esa es la decisión de la que cuelga todo el arnés: si el editor decidiera cuándo
validar, un modelo que se olvida de invocar una herramienta produciría un capítulo aprobado
sin comprobar, indistinguible de uno comprobado y correcto. Aquí, `Validate` va a `Repair`
o a `Extract` según un `bool` que salió de contar incidencias en una lista.

`ARISTAS` es la **misma relación** que la definición `Aristas` de `formal/tla/harness.tla`,
y una prueba lo comprueba. Que el conjunto de nombres coincida no basta: un grafo con los
veinticuatro estados bien nombrados y el cableado equivocado pasaría una comparación de
nombres sin parecerse en nada al modelo que TLC verificó, porque lo que TLC explora son
transiciones.
"""

from __future__ import annotations

from typing import Final

from storymaker.commons.graph.estado import EstadoNovela

#: La relación de transición. Cada par es «de este nodo se puede ir a este otro».
ARISTAS: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        # Fase 1 · Intake
        ("Configure", "AwaitApproval"),
        ("AwaitApproval", "Research"),
        ("AwaitApproval", "Configure"),
        ("AwaitApproval", "Fail"),
        # Fase 2 · Investigation
        ("Research", "VerifyCorpus"),
        ("VerifyCorpus", "AwaitApproval2"),
        ("AwaitApproval2", "Plan"),
        ("AwaitApproval2", "Research"),
        # Fase 3 · Plotting
        ("Plan", "FillGap"),
        ("FillGap", "Plan"),
        ("Plan", "AwaitApproval3"),
        ("AwaitApproval3", "SealCorpus"),
        ("AwaitApproval3", "Plan"),
        # Fase 4 · Writing
        ("SealCorpus", "WriteChapter"),
        ("WriteChapter", "Validate"),
        ("Validate", "Repair"),
        ("Validate", "Extract"),
        ("Extract", "Repair"),
        ("Repair", "Validate"),
        ("Validate", "Fail"),
        ("Extract", "Fail"),
        ("Extract", "ApproveChapter"),
        ("ApproveChapter", "Checkpoint"),
        ("Checkpoint", "WriteChapter"),
        ("Checkpoint", "AwaitApproval4"),
        # Fase 5 · Publication
        ("AwaitApproval4", "Judge"),
        ("AwaitApproval4", "WriteChapter"),
        ("Judge", "PublishVersion"),
        ("Judge", "AwaitApproval4"),
        ("Judge", "Fail"),
        ("PublishVersion", "Idle"),
        ("PublishVersion", "AwaitApproval4"),
        ("PublishVersion", "Fail"),
        # Fase 6 · Regeneration
        ("Idle", "RequestChange"),
        ("RequestChange", "Invalidate"),
        ("Invalidate", "RegenerateAffected"),
        ("RegenerateAffected", "Validate"),
        ("Idle", "Branch"),
    }
)


def destinos_de(nodo: str) -> frozenset[str]:
    return frozenset(b for a, b in ARISTAS if a == nodo)


def _comprobada(desde: str, hasta: str) -> str:
    """Devuelve el destino, y revienta si esa arista no existe en la relación.

    Es el equivalente del operador `Mueve(de, a)` del modelo, que obliga a toda acción a
    pasar por `Aristas`. Sin esto, un enrutador podría inventarse una transición que TLC
    nunca exploró y el modelo dejaría de decir nada sobre el código.
    """
    if (desde, hasta) not in ARISTAS:
        raise AssertionError(f"la arista {desde} -> {hasta} no esta en la relacion declarada")
    return hasta


def tras_validate(estado: EstadoNovela) -> str:
    """Determinista limpia → `Extract`; incidencias → `Repair`; sin reintentos → `Fail`.

    Las dos pasadas viven dentro del bucle de reparación, y el orden no es casual: no tiene
    sentido preguntarle a un modelo si los beats ocurrieron en un capítulo al que le faltan
    cuatrocientas palabras. Primero lo que es gratis y seguro.
    """
    if not estado["hay_bloqueantes"]:
        return _comprobada("Validate", "Extract")
    if estado["intentos"] < estado["max_intentos"]:
        return _comprobada("Validate", "Repair")
    return _comprobada("Validate", "Fail")


def tras_extract(estado: EstadoNovela) -> str:
    """Sin incidencias bloqueantes se aprueba; con ellas vuelve al editor.

    `Repair` tiene así **dos aristas de entrada** que comparten un único contador de
    intentos. Es exactamente la clase de interacción por la que `RetriesBounded` existe, y
    la razón de que `Extract` sea una acción propia del modelo y no un detalle interno de
    `Validate`.
    """
    if not estado["hay_bloqueantes"]:
        return _comprobada("Extract", "ApproveChapter")
    if estado["intentos"] < estado["max_intentos"]:
        return _comprobada("Extract", "Repair")
    return _comprobada("Extract", "Fail")


def tras_checkpoint(estado: EstadoNovela) -> str:
    """Quedan capítulos → el siguiente; se acabaron → el gate de Writing.

    La comparación es **`<=` y no `<`** porque `Checkpoint` ya adelantó el contador: cuando
    el nodo entrega el estado, `capitulo` es el que falta por escribir, no el que se acaba
    de aprobar. Con `<` la última novela se quedaba siempre un capítulo corta y `PublishVersion`
    la rechazaba sin decir por qué — que es justo lo que destapó la prueba de extremo a extremo.

    En regeneración el router es el mismo y lo que cambia es el nodo: `Checkpoint` no suma
    uno, sino que saca el siguiente de `a_regenerar`, y con la cola vacía deja `capitulo`
    más allá del último. Así la regeneración no reescribe en cascada lo posterior.
    """
    if estado["capitulo"] <= estado["n_capitulos"]:
        return _comprobada("Checkpoint", "WriteChapter")
    return _comprobada("Checkpoint", "AwaitApproval4")


def tras_idle(estado: EstadoNovela) -> str:
    """Publicada → fin de la invocación; con una petición aprobada → `RequestChange`.

    `Idle` es un reposo y no un final, pero la Fase 6 entra como **invocación nueva**:
    `regenerar` escribe en el checkpoint `pc = RequestChange` como salida de `Idle`, igual
    que `reintentar` lo hace como salida de `SealCorpus`, y este router lo lee. Recién
    publicada, `pc` es `Idle` y la invocación termina.
    """
    from langgraph.graph import END

    if estado["pc"] == "RequestChange":
        return _comprobada("Idle", "RequestChange")
    return str(END)


def tras_plan(estado: EstadoNovela) -> str:
    """Con huecos disponibles se puede micro-investigar; si no, al gate.

    El contador vive en el estado del grafo, que es el único sitio donde un tope se puede
    imponer de verdad: si viviera en el prompt del arquitecto, sería una sugerencia.
    """
    if estado["huecos"] > 0 and not estado["sellado"]:
        return _comprobada("Plan", "FillGap")
    return _comprobada("Plan", "AwaitApproval3")


def tras_judge(estado: EstadoNovela) -> str:
    """Umbral superado → publicar; no superado → al gate, con tope de rechazos.

    El tope lo descubrió TLC: sin él, el juez y el gate se pasan la novela para siempre y
    la propiedad de terminación es falsa. No es una defensa contra un caso raro, es la
    corrección de un contraejemplo real.
    """
    if not estado["hay_bloqueantes"]:
        return _comprobada("Judge", "PublishVersion")
    if estado["rechazos_juez"] < estado["max_rechazos_juez"]:
        return _comprobada("Judge", "AwaitApproval4")
    return _comprobada("Judge", "Fail")


def tras_publish(estado: EstadoNovela) -> str:
    """Publicada → `Idle`; rechazada → al gate de Writing, con el tope del juez; → `Fail`.

    Lean o `render_visual` rechazaron la candidata y no hay versión. El rechazo vuelve al
    Autor como vuelve el del juez, y comparte su contador: un render que falla siempre y un
    Autor que aprueba siempre serían el mismo ciclo que TLC encontró entre `Judge` y el gate.
    """
    if not estado["hay_bloqueantes"]:
        return _comprobada("PublishVersion", "Idle")
    if estado["rechazos_juez"] < estado["max_rechazos_juez"]:
        return _comprobada("PublishVersion", "AwaitApproval4")
    return _comprobada("PublishVersion", "Fail")


def tras_gate(estado: EstadoNovela, *, gate: str, decision: str) -> str:
    """Adónde lleva cada decisión del Autor en cada uno de los cuatro gates.

    «Rehacer» devuelve a la fase que produjo el artefacto; «aprobar» avanza; «abortar»
    termina. No hay auto-aprobación por tiempo: eso convertiría un gate de calidad en un
    temporizador.
    """
    avance = {
        "AwaitApproval": "Research",
        "AwaitApproval2": "Plan",
        "AwaitApproval3": "SealCorpus",
        "AwaitApproval4": "Judge",
    }
    rehacer = {
        "AwaitApproval": "Configure",
        "AwaitApproval2": "Research",
        "AwaitApproval3": "Plan",
        "AwaitApproval4": "WriteChapter",
    }
    if decision == "aprobar":
        return _comprobada(gate, avance[gate])
    if decision in ("rehacer", "editar"):
        return _comprobada(gate, rehacer[gate])
    # Abortar. El modelo solo declara la arista desde el gate de Intake, así que en los
    # otros tres esto revienta a propósito en lugar de inventarse una transición que TLC
    # nunca exploró. Es una discrepancia entre §10 —que ofrece «abortar» en los cinco
    # gates— y `formal/tla/harness.tla`, y se resuelve arriba: o el modelo gana tres
    # aristas y se vuelve a pasar TLC, o §10 dice que abortar solo cabe en el primero.
    return _comprobada(gate, "Fail")


def tras_espera(estado: EstadoNovela) -> str:
    """La salida de un gate. Se limita a leer adónde dijo el nodo que iba.

    El destino lo calcula el propio nodo con `tras_gate`, porque es quien tiene delante la
    decisión del Autor —o la aprobación implícita del modo batch—, y este router solo lo
    transporta. Repetir aquí la tabla de decisiones dejaría dos sitios donde cambiar una
    arista, que es la forma habitual de que el grafo y el modelo dejen de coincidir.
    """
    return estado["pc"]

