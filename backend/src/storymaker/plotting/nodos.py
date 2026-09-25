"""spec: §4.3 · arq: §4, §9, §10

La forma de rehacer y de los huecos la fija `specs/trama-rehacible/spec.md` §2 y §4.

Fase 3 · Plotting. Los nodos `Plan`, `FillGap` y `SealCorpus`.

**El hueco del arquitecto.** La investigación inicial se hizo sin saber todavía qué iba a
necesitar la trama, así que la escaleta destapa huecos: un detalle de cultura material, el
nombre de época de una calle, cómo se llamaba un oficio. El arquitecto declara cada hueco
**junto a la escena que lo necesita y con la invención que usaría**, y cada uno dispara
**una única llamada** al investigador, que termina siempre de una de dos formas: lo
encuentra, o devuelve `no_encontrado` y la invención propuesta entra en el corpus como
invención autorizada. En los dos casos el hecho **se ancla a su escena**, que es lo que
hace que el escritor lo reciba.

**El número de huecos está topado en cinco por ejecución**, y el contador vive en el estado
del grafo, que es el único sitio donde un tope se puede imponer de verdad. Alcanzado el
tope el arquitecto no se queda bloqueado: le queda la invención autorizada, que no cuesta
nada y produce exactamente la misma fila.

**La invención, en cambio, no se topa: se cuenta.** Poner límite a lo que el arquitecto
puede inventar solo le dejaría salidas peores —fallar, o declarar otro origen—, así que lo
que hace el arnés es enseñarlo en el informe del gate.

**Rehacer replanifica.** Tras «rehacer» o «editar» en el gate, `Plan` sustituye la trama y
el arquitecto recibe la anterior, el comentario del Autor y los avisos de la revisión
(`plotting.trama`). Al volver de un hueco, no.
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
from storymaker.intake.contradicciones import EDAD_MINIMA_RAZONABLE
from storymaker.intake.esquemas import Brief
from storymaker.investigation.corpus import escribir_hecho
from storymaker.investigation.esquemas import (
    Dimension,
    EstadoEpistemico,
    HechoPropuesto,
)
from storymaker.investigation.nodos import periodo_y_lugar, resolver_hueco, verificar_hecho
from storymaker.plotting import canon, contexto, escaleta, trama
from storymaker.plotting import gate as revision
from storymaker.plotting.esquemas import HuecoPropuesto, SalidaArquitecto, con_claves

ORIGEN_MICRO = "micro_arquitecto"
ORIGEN_INVENTADO = "invencion_autorizada"

#: Qué hacer con cada firmeza al construir la trama (arq. §4, Fase 3). El arquitecto es
#: quien decide dónde se apoya la novela, así que es a él a quien más le importa.
USO_DE_LA_FIRMEZA_EN_LA_TRAMA = (
    "Cada hecho del contexto lleva su firmeza delante.\n"
    "- documentado: apoya aqui el evento ancla y los giros de la trama.\n"
    "- debatido: puede sostener una escena si la duda forma parte de ella.\n"
    "- inferido: usalo como ambiente, no como apoyo de un giro.\n"
    "- desconocido: hueco libre; puedes inventar ahi.\n"
    "- inventado: ya es licencia; usalo dentro del grado de licencia del encargo.\n"
    "Lo marcado como «no lo dice la cita» no es parte del hecho."
)


async def cubrir_hueco(
    pregunta: str,
    *,
    periodo: str,
    lugar: str,
    fase_run_id: int,
    dimension: Dimension,
    propuesta: str = "",
) -> tuple[int, str]:
    """Resuelve un hueco. Devuelve (identificador del hecho, origen con el que entró).

    Los dos finales escriben **una fila del corpus**, y eso no es burocracia: `anclaje_valido`
    exige en Writing que todo anclaje apunte a un hecho del corpus sellado o a una Licencia
    declarada. Un detalle inventado que viviera solo en la cabeza del arquitecto tumbaría ese
    validador en cuanto el escritor lo usara.

    **El hecho encontrado pasa en el acto por el verificador**; el inventado no, porque no
    tiene cita que comprobar (arq. §4, Fase 3). Si el verificador falla, el hecho se queda
    `pendiente`, su firmeza no pasa de `inferido` y la escaleta sigue.

    Lo inventado es **la propuesta del arquitecto**, que es una afirmación. Solo si no la
    dio se escribe la pregunta, que es lo único que queda.
    """
    deps = actuales()
    resuelto = await resolver_hueco(pregunta, periodo, lugar)

    if resuelto.encontrado and resuelto.hecho is not None:
        hecho_id = await escribir_hecho(
            deps.db, deps.vectorizador, resuelto.hecho, fase_run_id=fase_run_id, origen=ORIGEN_MICRO
        )
        await verificar_hecho(hecho_id)
        return hecho_id, ORIGEN_MICRO

    inventado = HechoPropuesto(
        enunciado=propuesta.strip() or pregunta,
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
        "entre sus escenas. La fecha_narrativa de cada escena va en ISO —AAAA, AAAA-MM o "
        "AAAA-MM-DD, tan precisa como la sepas—; la hora del dia o «dias despues» van en el "
        "objetivo de la escena, no en la fecha."
    )


def regla_de_los_arcos() -> str:
    """Lo que `arco_anclado` va a exigir, dicho antes y no después (trama-rehacible §3.6).

    Sin esto el arquitecto se enteraba de la regla al rehacer, con la primera trama ya
    pagada: la segunda novela con gates llegó al gate con cuatro secundarios sin arco.
    """
    return (
        f"Todo personaje que aparezca en {Defaults.ESCENAS_PARA_EXIGIR_ARCO} escenas o mas "
        "necesita un arco. Si no cambia, declaralo con tipo plano, sin hitos: es una "
        "decision valida. Un arco positivo o negativo lleva al menos "
        f"{Defaults.HITOS_MINIMOS_ARCO_CON_TRANSFORMACION} hitos, anclados a escenas de "
        "capitulos que no retroceden. El del homenajeado no puede ser plano y su ultimo "
        "hito cae en el tercio final de la novela."
    )


#: Cómo se le pide al arquitecto que declare un hueco. Sin escena ni propuesta, el hueco
#: entraba en el corpus sin que nada de la trama se apoyara en él.
FORMA_DE_LOS_HUECOS = (
    "Declara cada hueco con: la pregunta concreta; la clave de la escena que lo necesita; "
    "su dimension (cronologia, lugar, cultura_material, lenguaje, mentalidad o "
    "estructura_social), y en si_no_se_encuentra la afirmacion que usarias si la "
    "investigacion no lo encuentra, escrita como un hecho y no como una pregunta. "
    "En si_no_se_encuentra no atribuyas cargos, oficios, lugares ni actos a personajes "
    "historicos reales: lo que se inventa es el ambiente, no la biografia de nadie."
)

#: La fecha de nacimiento del homenajeado en el canon es la de su personaje en la época
#: (arq. §4, Fase 3). El encargo puede traer la real, y copiarla dejaba al protagonista sin
#: nacer en todas sus escenas, que es justo lo que el Lean de la publicación no deja pasar.
NACIMIENTO_DEL_HOMENAJEADO = (
    "La fecha_nacimiento del homenajeado en su ficha es la de su personaje en la epoca, no "
    "la de su vida real: si la del encargo cae despues del periodo o le da menos de "
    "{edad} anos en el, elige una coherente con su rol en la epoca."
)


def rehacer_como_texto(anterior: str, comentarios: list[str], avisos: list[str]) -> str:
    """El bloque que convierte «rehacer» en un reintento dirigido.

    Va la trama anterior porque es lo que el Autor ha visto y quizá corregido; los avisos,
    porque son lo que la revisión encontró, y rehacer sin arreglarlos repetiría el fallo; y
    el comentario, que es lo que manda.
    """
    if not anterior and not comentarios and not avisos:
        return ""
    partes = ["--- Rehacer ---", "El Autor ha pedido rehacer la trama."]
    if comentarios:
        partes.append("Lo que pide, por orden (lo ultimo manda):")
        partes += [f"- {c}" for c in comentarios]
    if avisos:
        partes.append("La revision de la trama anterior encontro esto; corrigelo:")
        partes += [f"- {a}" for a in avisos]
    if anterior:
        partes.append(
            "Esta es la trama anterior, con las correcciones del Autor. Conserva lo que el "
            "comentario no pida cambiar:"
        )
        partes.append(anterior)
    return "\n".join(partes) + "\n\n"


async def planificar(brief: Brief, *, fase_run_id: int, rehacer: str = "") -> SalidaArquitecto:
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
        f"--- Firmeza de los hechos ---\n{USO_DE_LA_FIRMEZA_EN_LA_TRAMA}\n\n"
        f"--- Huecos ---\n{FORMA_DE_LOS_HUECOS}\n\n"
        f"--- Arcos ---\n{regla_de_los_arcos()}\n\n"
        f"--- Homenajeado ---\n"
        f"{NACIMIENTO_DEL_HOMENAJEADO.format(edad=EDAD_MINIMA_RAZONABLE)}\n\n"
        f"{rehacer}"
        "Ancla cada escena a los hechos y elementos que la sostienen escribiendo su "
        "clave #id tal como aparece arriba: en `hecho` las de los hechos del contexto y en "
        "`dato` las de los elementos del encargo.\n"
    )
    # Las claves a las que puede anclar, enumeradas en su contrato de salida: los hechos que
    # ve en el contexto y los elementos del encargo (trama-rehacible §3.5).
    esquema = con_claves(
        [int(h["id"]) for h in hechos], [int(d["id"]) for d in await intake.datos(deps.db)]
    )
    de_rol = RepositorioDePrompts(deps.settings).para(Perfil.ARQUITECTO)
    resultado = await invocar_rol(
        Perfil.ARQUITECTO,
        prompt,
        esquema,
        transporte=deps.transporte,
        settings=deps.settings,
        sistema=de_rol.texto,
    )
    deps.observador.registrar_span(
        Span(
            nombre=nombre_de_span(capitulo=None, rol="arquitecto"),
            rol="arquitecto",
            consumo=resultado.consumo,
            prompt_version=de_rol.version,
            prompt_nombre=de_rol.nombre,
        )
    )
    _ = fase_run_id
    return resultado.valor


async def volcar(
    salida: SalidaArquitecto, brief: Brief, *, fase_run_id: int | None = None
) -> dict[str, int]:
    """Canon, palabras prohibidas, escaleta y arcos, **en ese orden**.

    El orden no es cosmético: los arcos anclan sus hitos a escenas, y las escenas no tienen
    identificador hasta que la escaleta está escrita. Volcarlos antes dejaría todos los hitos
    con `escena_id` nulo y `arco_anclado` en rojo en el gate.

    Devuelve clave de escena → identificador, que es lo que ancla cada hueco a su escena.
    """
    deps = actuales()
    personajes = await canon.volcar_canon(
        deps.db, deps.vectorizador, salida, brief, fase_run_id=fase_run_id
    )
    async with deps.db.execute("SELECT id, enunciado FROM mundo_hecho") as cursor:
        hechos = {int(f["id"]): str(f["enunciado"]) for f in await cursor.fetchall()}
    datos = {int(d["id"]): _valor_de_dato(d["valor_json"]) for d in await intake.datos(deps.db)}
    sin_resolver: list[str] = []
    por_parecido: list[str] = []
    escenas = await escaleta.volcar_escaleta(
        deps.db,
        salida,
        personajes=personajes,
        hechos=escaleta.mapa_de_claves(hechos),
        datos=escaleta.mapa_de_claves(datos),
        textos_de_hecho=hechos,
        textos_de_dato=datos,
        sin_resolver=sin_resolver,
        resueltos_por_parecido=por_parecido,
    )
    await canon.volcar_arcos(deps.db, salida, personajes, escenas)
    # Lo que no se pudo anclar no se pierde en silencio, y lo que se ancló por parecido se
    # dice: los dos los enseña el gate (ER §7.2, trama-rehacible §3.5).
    for validador in (VALIDADOR_DE_ANCLAJES, VALIDADOR_DE_PARECIDO):
        await arnes.retirar_incidencias_sin_capitulo(deps.db, validador)
    for anclaje in sin_resolver:
        await arnes.registrar_incidencia(
            deps.db,
            validador=VALIDADOR_DE_ANCLAJES,
            severidad="aviso",
            mensaje=f"El anclaje no apunta a ningun hecho ni elemento conocido: {anclaje}",
        )
    for anclaje in por_parecido:
        await arnes.registrar_incidencia(
            deps.db,
            validador=VALIDADOR_DE_PARECIDO,
            severidad="aviso",
            mensaje=f"Anclaje escrito como frase, resuelto por parecido: {anclaje}",
        )
    return escenas


#: Los anclajes de la escaleta que no se pudieron resolver a un hecho o a un elemento.
VALIDADOR_DE_ANCLAJES = "anclaje_resuelto"
#: Los que no traían clave y se resolvieron por parecido léxico.
VALIDADOR_DE_PARECIDO = "anclaje_por_parecido"


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

    **Planifica cuando no hay trama o cuando el Autor pidió otra**, y en ningún otro caso
    (`trama.hay_que_planificar`). El nodo tiene dos aristas de entrada —desde `VerifyCorpus`
    o el gate, y desde `FillGap`—, y al volver de un hueco no rehace la escaleta: el hueco
    resuelto ya entró en el corpus y se ancló a su escena. Replanificar en cada vuelta
    duplicaría personajes y capítulos, y costaría cinco llamadas de arquitecto para nada.

    Tras planificar, la revisión corre y guarda lo que encuentra, y los huecos se registran
    con su escena. El tope de huecos se recorta a los que el arquitecto declaró de verdad:
    el presupuesto es un máximo, no una cuota que haya que gastar.
    """
    deps = actuales()
    if not await trama.hay_que_planificar(deps.db):
        return {**estado, "pc": "AwaitApproval3"}

    brief = await brief_vigente(deps.db)
    if brief is None:
        return {**estado, "pc": "AwaitApproval3", "huecos": 0, "huecos_pendientes": []}

    rehacer = ""
    if await trama.hay_trama(deps.db):
        avisos = [i.mensaje for i in await revision.incidencias_guardadas(deps.db)]
        rehacer = rehacer_como_texto(
            await trama.como_texto(deps.db),
            await arnes.comentarios_de_rehacer(deps.db, "plotting"),
            avisos,
        )
        await trama.borrar(deps.db)
        await revision.retirar_incidencias(deps.db)

    salida = await planificar(brief, fase_run_id=estado["fase_run_id"], rehacer=rehacer)
    escenas = await volcar(salida, brief, fase_run_id=estado["fase_run_id"])
    await revision.revisar(deps.db, deps.vectorizador)

    tope = deps.settings.huecos_por_plotting
    pendientes = [await registrar_hueco(deps.db, hueco, escenas) for hueco in salida.huecos[:tope]]
    return {
        **estado,
        "pc": "AwaitApproval3",
        "huecos": len(pendientes),
        "huecos_pendientes": [str(h) for h in pendientes],
    }


async def registrar_hueco(
    db: aiosqlite.Connection, hueco: HuecoPropuesto, escenas: dict[str, int]
) -> int:
    return await repo_plan.registrar_hueco(
        db,
        pregunta=hueco.pregunta,
        dimension=hueco.dimension.value,
        escena_id=escenas.get(hueco.escena),
        propuesta=hueco.si_no_se_encuentra,
    )


async def fill_gap(estado: EstadoNovela) -> EstadoNovela:
    """Resuelve un hueco, lo ancla a su escena, lo descuenta y vuelve a `Plan`.

    El contador vive aquí y no en el prompt: un tope que el arquitecto pudiera leer sería una
    sugerencia. Los dos finales de `cubrir_hueco` —encontrado o inventado— escriben fila, así
    que la vuelta a `Plan` es idéntica en ambos casos y el bucle siempre avanza.

    El estado lleva el identificador del hueco y no su contenido, que vive en `plan_hueco`.
    Un pendiente que no es un número —un checkpoint anterior, con la pregunta en claro— se
    cubre igual, sin escena.
    """
    pendientes = list(estado["huecos_pendientes"])
    if pendientes:
        deps = actuales()
        periodo, lugar = await periodo_y_lugar(deps.db)
        siguiente = pendientes.pop(0)
        fila = await repo_plan.hueco(deps.db, int(siguiente)) if siguiente.isdigit() else None
        hecho_id, origen = await cubrir_hueco(
            str(fila["pregunta"]) if fila is not None else siguiente,
            periodo=periodo,
            lugar=lugar,
            fase_run_id=corpus_de(estado),
            dimension=(
                Dimension(str(fila["dimension"]))
                if fila is not None
                else Dimension.CULTURA_MATERIAL
            ),
            propuesta=str(fila["propuesta"] or "") if fila is not None else "",
        )
        if origen == ORIGEN_INVENTADO:
            # La revisión corrió antes de los huecos: lo inventado ahora se mira aquí.
            for aviso in await revision.invenciones_sobre_historicos(deps.db, [hecho_id]):
                await arnes.registrar_incidencia(
                    deps.db,
                    validador=aviso.validador,
                    severidad=aviso.severidad.value,
                    mensaje=aviso.mensaje,
                    ubicacion=aviso.ubicacion,
                )
        if fila is not None:
            await repo_plan.cerrar_hueco(
                deps.db,
                int(fila["id"]),
                hecho_id=hecho_id,
                resultado="encontrado" if origen == ORIGEN_MICRO else "inventado",
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
