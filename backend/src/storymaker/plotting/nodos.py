"""spec: §4.3 · arq: §4, §9

Fase 3 · Plotting. Los nodos `Plan`, `FillGap` y `SealCorpus`.

**El hueco del arquitecto.** La investigación inicial se hizo sin saber todavía qué iba a
necesitar la trama, así que la escaleta destapa huecos: un detalle de cultura material, el
nombre de época de una calle, cómo se llamaba un oficio. Cada hueco dispara **una única
llamada** al investigador, que termina siempre de una de dos formas: lo encuentra, o
devuelve `no_encontrado` y **autoriza al arquitecto a inventarlo**.

**El número de huecos está topado en cinco por ejecución**, y el contador vive en el estado
del grafo, que es el único sitio donde un tope se puede imponer de verdad. Alcanzado el
tope el arquitecto no se queda bloqueado: le queda la invención autorizada, que no cuesta
nada y produce exactamente la misma fila.

**La invención, en cambio, no se topa: se cuenta.** Poner límite a lo que el arquitecto
puede inventar solo le dejaría salidas peores —fallar, o declarar otro origen—, así que lo
que hace el arnés es enseñarlo en el informe del gate.
"""

from __future__ import annotations

import json

import aiosqlite

from storymaker.commons.agents.invocacion import invocar_rol
from storymaker.commons.agents.techos import Perfil
from storymaker.commons.config import Defaults
from storymaker.commons.db.repos import arnes, intake, mundo
from storymaker.commons.db.repos import plan as repo_plan
from storymaker.commons.graph.contabilidad import corpus_de
from storymaker.commons.graph.dependencias import actuales
from storymaker.commons.graph.estado import EstadoNovela
from storymaker.commons.obs.prompts import RepositorioDePrompts
from storymaker.commons.obs.trazas import Span, nombre_de_span
from storymaker.intake.esquemas import Brief
from storymaker.investigation.corpus import escribir_hecho
from storymaker.investigation.esquemas import (
    Dimension,
    EstadoEpistemico,
    HechoPropuesto,
)
from storymaker.investigation.nodos import periodo_y_lugar, resolver_hueco
from storymaker.plotting import canon, contexto, escaleta
from storymaker.plotting.esquemas import SalidaArquitecto

ORIGEN_MICRO = "micro_arquitecto"
ORIGEN_INVENTADO = "invencion_autorizada"


async def cubrir_hueco(
    pregunta: str, *, periodo: str, lugar: str, fase_run_id: int, dimension: Dimension
) -> tuple[int, str]:
    """Resuelve un hueco. Devuelve (identificador del hecho, origen con el que entró).

    Los dos finales escriben **una fila del corpus**, y eso no es burocracia: `anclaje_valido`
    exige en Writing que todo anclaje apunte a un hecho del corpus sellado o a una Licencia
    declarada. Un detalle inventado que viviera solo en la cabeza del arquitecto tumbaría ese
    validador en cuanto el escritor lo usara.
    """
    deps = actuales()
    resuelto = await resolver_hueco(pregunta, periodo, lugar)

    if resuelto.encontrado and resuelto.hecho is not None:
        hecho_id = await escribir_hecho(
            deps.db, deps.vectorizador, resuelto.hecho, fase_run_id=fase_run_id, origen=ORIGEN_MICRO
        )
        return hecho_id, ORIGEN_MICRO

    inventado = HechoPropuesto(
        enunciado=pregunta,
        estado=EstadoEpistemico.INFERIDO,
        dimension=dimension,
        cita="",
        fuentes=[],
    )
    hecho_id = await escribir_hecho(
        deps.db, deps.vectorizador, inventado, fase_run_id=fase_run_id, origen=ORIGEN_INVENTADO
    )
    return hecho_id, ORIGEN_INVENTADO


async def brief_vigente(db: aiosqlite.Connection) -> Brief | None:
    """El `Brief` tal como se cerró en Intake. Al arquitecto sí se le entrega entero.

    A diferencia del investigador —que recibe dos cadenas y nada más porque es el único rol
    con salida a la red—, el arquitecto necesita el encargo completo: los elementos de
    personalización obligatorios son suyos, y sin ellos no puede repartirlos por la escaleta.
    """
    async with db.execute("SELECT json FROM intake_brief ORDER BY id DESC LIMIT 1") as cursor:
        fila = await cursor.fetchone()
    if fila is None:
        return None
    return Brief.model_validate(json.loads(str(fila["json"])))


def forma_de_la_escaleta(brief: Brief) -> str:
    """Capítulos, escenas por capítulo y extensión (arq. §19), dichos al arquitecto.

    Sin esto la primera escaleta con gates salió con una escena por capítulo: el rango de
    §19 existía en la configuración y no lo usaba nada.
    """
    minimo, maximo = Defaults.RANGO_ESCENAS_POR_CAPITULO
    return (
        f"Exactamente {brief.n_capitulos} capitulos, cada uno con entre {minimo} y {maximo} "
        f"escenas, y unas {brief.palabras_por_capitulo} palabras por capitulo repartidas "
        "entre sus escenas."
    )


async def planificar(brief: Brief, *, fase_run_id: int) -> SalidaArquitecto:
    """Una llamada al arquitecto, con el corpus repartido por dimensiones delante.

    Lo que se le entrega no es el corpus entero sino la selección de `contexto`: el techo de
    25.000 tokens de §12 se respeta por construcción eligiendo qué entra, no recortando
    después lo que no cupo.
    """
    deps = actuales()
    hechos = await contexto.hechos_relevantes(
        deps.db, deps.vectorizador, brief, settings=deps.settings
    )
    prompt = (
        "Este es el encargo del comprador y el contexto histórico investigado. Inventa la "
        "Premisa y el Tema, construye el canon y desglosa la escaleta capítulo a capítulo. "
        "Lo que necesites y no esté en el contexto, decláralo como hueco.\n\n"
        f"--- Encargo ---\n{brief.model_dump_json(indent=2)}\n\n"
        f"--- Contexto histórico ---\n{contexto.como_texto(hechos)}\n\n"
        f"--- Elementos del encargo ---\n{await elementos_con_clave(deps.db)}\n\n"
        f"--- Forma de la escaleta ---\n{forma_de_la_escaleta(brief)}\n\n"
        "Ancla cada escena a los hechos y elementos que la sostienen escribiendo su "
        "clave #id tal como aparece arriba.\n"
    )
    resultado = await invocar_rol(
        Perfil.ARQUITECTO,
        prompt,
        SalidaArquitecto,
        transporte=deps.transporte,
        settings=deps.settings,
        sistema=RepositorioDePrompts(deps.settings).para(Perfil.ARQUITECTO).texto,
    )
    deps.observador.registrar_span(
        Span(
            nombre=nombre_de_span(capitulo=None, rol="arquitecto"),
            rol="arquitecto",
            consumo=resultado.consumo,
        )
    )
    _ = fase_run_id
    return resultado.valor


async def volcar(salida: SalidaArquitecto, brief: Brief) -> None:
    """Canon, palabras prohibidas, escaleta y arcos, **en ese orden**.

    El orden no es cosmético: los arcos anclan sus hitos a escenas, y las escenas no tienen
    identificador hasta que la escaleta está escrita. Volcarlos antes dejaría todos los hitos
    con `escena_id` nulo y `arco_anclado` en rojo en el gate.
    """
    deps = actuales()
    personajes = await canon.volcar_canon(deps.db, deps.vectorizador, salida, brief)
    await canon.volcar_prohibidas(deps.db, brief)
    async with deps.db.execute("SELECT id, enunciado FROM mundo_hecho") as cursor:
        hechos = {int(f["id"]): str(f["enunciado"]) for f in await cursor.fetchall()}
    datos = {int(d["id"]): _valor_de_dato(d["valor_json"]) for d in await intake.datos(deps.db)}
    sin_resolver: list[str] = []
    escenas = await escaleta.volcar_escaleta(
        deps.db,
        salida,
        personajes=personajes,
        hechos=escaleta.mapa_de_claves(hechos),
        datos=escaleta.mapa_de_claves(datos),
        sin_resolver=sin_resolver,
    )
    await canon.volcar_arcos(deps.db, salida, personajes, escenas)
    # Lo que no se pudo anclar no se pierde en silencio: lo enseña el gate (ER §7.2).
    await arnes.retirar_incidencias_sin_capitulo(deps.db, VALIDADOR_DE_ANCLAJES)
    for anclaje in sin_resolver:
        await arnes.registrar_incidencia(
            deps.db,
            validador=VALIDADOR_DE_ANCLAJES,
            severidad="aviso",
            mensaje=f"El anclaje no apunta a ningun hecho ni elemento conocido: {anclaje}",
        )


#: Los anclajes de la escaleta que no se pudieron resolver a un hecho o a un elemento.
VALIDADOR_DE_ANCLAJES = "anclaje_resuelto"


def _valor_de_dato(valor_json: object) -> str:
    """El texto de un elemento del encargo, que en la base vive dentro de un JSON."""
    try:
        cargado = json.loads(str(valor_json))
    except json.JSONDecodeError:
        return str(valor_json)
    if isinstance(cargado, dict):
        return str(cargado.get("valor", "")) or json.dumps(cargado, ensure_ascii=False)
    return str(cargado)


async def elementos_con_clave(db: aiosqlite.Connection) -> str:
    """Los elementos de personalización con la clave con la que se anclan."""
    lineas = [
        f"(#{d['id']}) [{'OBLIGATORIO' if int(d['obligatorio']) else 'opcional'}] "
        f"{_valor_de_dato(d['valor_json'])}"
        for d in await intake.datos(db)
    ]
    return "\n".join(lineas) or "(ninguno)"


async def plan(estado: EstadoNovela) -> EstadoNovela:
    """El arquitecto inventa la Premisa y el Tema, y construye canon y escaleta.

    **Planifica una sola vez.** El nodo tiene dos aristas de entrada —la primera desde
    `VerifyCorpus` y las siguientes desde `FillGap`—, y al volver de un hueco no rehace la
    escaleta: el hueco resuelto entró en el corpus, que es lo que `anclaje_valido` mira en
    Writing. Replanificar en cada vuelta duplicaría personajes y capítulos, y costaría cinco
    llamadas de arquitecto para no cambiar nada que el escritor vaya a leer.

    El tope de huecos se recorta además a los que el arquitecto declaró de verdad: el
    presupuesto de cinco es un máximo, no una cuota que haya que gastar.
    """
    deps = actuales()
    if await repo_plan.total_de_capitulos(deps.db) > 0:
        return {**estado, "pc": "AwaitApproval3"}

    brief = await brief_vigente(deps.db)
    if brief is None:
        return {**estado, "pc": "AwaitApproval3", "huecos": 0}

    salida = await planificar(brief, fase_run_id=estado["fase_run_id"])
    await volcar(salida, brief)

    pendientes = salida.huecos[: estado["huecos"]]
    return {
        **estado,
        "pc": "AwaitApproval3",
        "huecos": len(pendientes),
        "huecos_pendientes": list(pendientes),
    }


async def fill_gap(estado: EstadoNovela) -> EstadoNovela:
    """Resuelve un hueco, lo descuenta y vuelve a `Plan`.

    El contador vive aquí y no en el prompt: un tope que el arquitecto pudiera leer sería una
    sugerencia. Los dos finales de `cubrir_hueco` —encontrado o inventado— escriben fila, así
    que la vuelta a `Plan` es idéntica en ambos casos y el bucle siempre avanza.
    """
    pendientes = list(estado["huecos_pendientes"])
    if pendientes:
        deps = actuales()
        periodo, lugar = await periodo_y_lugar(deps.db)
        await cubrir_hueco(
            pendientes.pop(0),
            periodo=periodo,
            lugar=lugar,
            fase_run_id=corpus_de(estado),
            dimension=Dimension.CULTURA_MATERIAL,
        )
    return {
        **estado,
        "pc": "Plan",
        "huecos": max(0, estado["huecos"] - 1),
        "huecos_pendientes": pendientes,
    }


async def seal(estado: EstadoNovela) -> EstadoNovela:
    """**Sella el corpus.** A partir de este instante es de solo lectura.

    El sello se coloca al cerrar Plotting y no al cerrar Investigation por dos razones:
    permite las micro-sesiones del arquitecto, y garantiza que cualquier rama posterior
    parta del mismo corpus — sin lo cual las ramas no serían comparables.

    Se calcula sobre el contenido **ordenado** de las tablas `mundo_*` vigentes, de modo que
    dos corpus idénticos den el mismo hash aunque se escribieran en otro orden.
    """
    deps = actuales()
    await mundo.sellar_corpus(deps.db, corpus_de(estado))
    return {**estado, "pc": "WriteChapter", "sellado": True}
