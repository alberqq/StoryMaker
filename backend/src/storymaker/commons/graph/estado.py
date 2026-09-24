"""spec: §3.2 · arq: §9, §16.3

El estado compartido del grafo: un `TypedDict` **total y explícito**.

Nada de `dict[str, Any]` aquí, y `mypy --strict` lo comprueba. No es una preferencia de
estilo: es lo que permite que el contador de huecos de Plotting o el de reintentos de
Writing tengan un dueño declarado, en lugar de acabar definidos dentro de la fase que
primero los necesitó y leídos a ciegas por las demás.

Las variables son **las mismas que las del modelo TLA+**, con los mismos nombres. Es la
otra mitad de la correspondencia que §9 exige: si un contraejemplo de TLC dice que
`intentos` llegó a tres, aquí hay un campo que se llama igual y significa lo mismo.
"""

from __future__ import annotations

from typing import TypedDict


class EstadoNovela(TypedDict):
    """Lo que viaja de nodo en nodo. Todo lo demás vive en SQLite.

    El orquestador no acumula: este diccionario es pequeño a propósito y contiene punteros
    —números de capítulo, identificadores, contadores—, nunca contenido. El texto de un
    capítulo, el corpus y el canon se leen de la base cuando hacen falta, de modo que matar
    el proceso en cualquier punto y reanudar no pierde nada.
    """

    #: Ruta del fichero de la novela. Una novela es un fichero.
    novela: str

    #: La premisa inicial libre que escribio el comprador. Es materia prima, no la Premisa
    #: narrativa del modulo 2: esa la inventa el arquitecto en la Fase 3.
    premisa: str

    #: Texto pegado por el comprador, si lo hubo. Entra en cuarentena y solo avanza
    #: convertido en filas tipadas.
    texto_pegado: str

    #: El nodo en el que está la invocación. Se llama igual que en el modelo.
    pc: str

    #: La ejecución de fase en curso. Todo lo que se escriba lleva este identificador.
    fase_run_id: int

    #: La ejecución de Investigation, que es la que identifica el corpus. Se lleva aparte
    #: porque cada fase abre su `fase_run`, y el corpus se verifica, se completa en
    #: Plotting y se sella bajo el identificador que lo escribió, no bajo el de la fase en
    #: curso. `None` hasta que Investigation empieza.
    corpus_run_id: int | None

    #: El capítulo que se está escribiendo, de 1 a `n_capitulos`.
    capitulo: int
    n_capitulos: int

    #: Reintentos consumidos por el capítulo en curso. Lo comparte `Repair`, que tiene dos
    #: aristas de entrada —desde `Validate` y desde `Extract`—, y esa es exactamente la
    #: interacción por la que `RetriesBounded` existe.
    intentos: int
    max_intentos: int

    #: Capítulos aprobados y capítulos que pasaron todos los validadores. Se llevan aparte
    #: porque `NoPublishUnvalidated` habla del segundo, no del primero.
    aprobados: list[int]
    validados: list[int]

    #: Huecos de micro-investigación que le quedan al arquitecto en esta ejecución.
    huecos: int

    #: Las preguntas que la escaleta destapó y el corpus no contesta, en el orden en que el
    #: arquitecto las planteó. `FillGap` consume una por vuelta: sin esta lista el contador
    #: sabría *cuántas* quedan pero no *cuáles*, y el bucle giraría en vacío.
    huecos_pendientes: list[str]

    #: El corpus quedó sellado al cerrar Plotting. A partir de ahí es de solo lectura.
    sellado: bool

    #: Se están rehaciendo capítulos por una petición del lector o una edición humana.
    regenerando: bool

    #: El alcance de la regeneración en curso, calculado en `RequestChange` y consumido por
    #: los dos nodos siguientes. Son números de capítulo, no texto: el estado sigue siendo
    #: punteros. La política entera de la Fase 6 vive en la distinción entre estas dos
    #: listas — regeneración cara arriba, invalidación barata abajo.
    a_regenerar: list[int]
    a_invalidar: list[int]

    #: Veces que el juez ha devuelto la novela al gate. Sin tope, el juez y el gate se la
    #: pasan para siempre — lo descubrió TLC, no una revisión.
    rechazos_juez: int
    max_rechazos_juez: int

    #: Gate abierto a la espera del Autor, si lo hay.
    gate_id: int | None

    #: El intento de capitulo en curso. Es el dueno de las filas que escribe el extractor,
    #: y lo que permite que las de un intento descartado queden fuera por construccion.
    capitulo_version_id: int | None

    #: Los gates están activos. En modo batch se apagan enteros.
    gates_enabled: bool

    #: El modo de la investigación: `estandar` o `exhaustiva`. Viaja aquí y no en
    #: `Settings` por la misma razón que `gates_enabled`: la novela se retoma, se rehace
    #: y se ramifica en el modo con que nació.
    investigacion: str

    #: Incidencias bloqueantes del intento en curso. Es el booleano que leen las aristas
    #: condicionales: la transición depende de un valor calculado en Python, nunca de la
    #: salida de un modelo.
    hay_bloqueantes: bool

    #: Consumo acumulado de la invocación, para el informe del gate y la traza.
    tokens_in: int
    tokens_out: int
    coste_usd: float


def estado_inicial(
    *,
    novela: str,
    fase_run_id: int,
    premisa: str = "",
    texto_pegado: str = "",
    n_capitulos: int,
    max_intentos: int,
    huecos: int,
    gates_enabled: bool,
    max_rechazos_juez: int = 2,
    investigacion: str = "estandar",
) -> EstadoNovela:
    """El estado con el que arranca una novela nueva.

    Arranca en `Configure` porque el grafo empieza por Intake, y con `capitulo` en 1
    aunque falten cuatro fases para que alguien escriba: el campo existe desde el
    principio para que el `TypedDict` sea total y nadie tenga que comprobar si está.
    """
    return EstadoNovela(
        novela=novela,
        premisa=premisa,
        texto_pegado=texto_pegado,
        pc="Configure",
        fase_run_id=fase_run_id,
        corpus_run_id=None,
        capitulo=1,
        n_capitulos=n_capitulos,
        intentos=0,
        max_intentos=max_intentos,
        aprobados=[],
        validados=[],
        huecos=huecos,
        huecos_pendientes=[],
        sellado=False,
        regenerando=False,
        a_regenerar=[],
        a_invalidar=[],
        rechazos_juez=0,
        max_rechazos_juez=max_rechazos_juez,
        gate_id=None,
        capitulo_version_id=None,
        gates_enabled=gates_enabled,
        investigacion=investigacion,
        hay_bloqueantes=False,
        tokens_in=0,
        tokens_out=0,
        coste_usd=0.0,
    )
