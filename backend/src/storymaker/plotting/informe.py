"""spec: §4.3 · arq: §4, §10

Lo que enseña lo fija además `specs/trama-rehacible/spec.md` §3.

El informe del gate de Plotting: lo que el Autor tiene delante al decidir sobre la trama.

Su pieza más importante es **el recuento de hechos inventados por dimensión**, y está ahí
por una decisión concreta: la invención autorizada no se topa, se cuenta. Poner límite a lo
que el arquitecto puede inventar solo le dejaría salidas peores —fallar, o declarar otro
origen—, así que lo que hace el arnés es enseñarlo. Cuánta libertad es aceptable ya lo
declara `grado_licencia` en el brief, y quien la juzga es el juez con el criterio de
autenticidad de época.

Lo demás es lo que el Autor necesita para decidir con conocimiento: cada hueco con su
escena y cómo se cubrió, y los avisos de la revisión. **Ninguno cierra el gate**; si rehace,
el arquitecto los recibe.
"""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite

from storymaker.commons.db.repos import mundo, plan
from storymaker.commons.validation.modelos import Incidencia
from storymaker.plotting.gate import PuertaDePlotting


@dataclass(frozen=True)
class HuecoDelInforme:
    pregunta: str
    dimension: str
    #: `encontrado`, `inventado`, o `None` si el tope de huecos no llegó a él.
    resultado: str | None
    enunciado: str | None
    capitulo: int | None
    escena: int | None


@dataclass(frozen=True)
class InformeDePlotting:
    capitulos: int
    escenas: int
    inventados_por_dimension: dict[str, int]
    huecos_gastados: int
    incidencias: tuple[Incidencia, ...] = ()
    #: Hechos que encontró la micro-sesión y el verificador no respaldó: su firmeza no pasa
    #: de `inferido` aunque el investigador los diera por verificados.
    micro_sin_respaldo: int = 0
    #: `(capitulo, orden)` de las escenas que solo se apoyan en hechos inferidos o
    #: desconocidos. Es aviso: el Autor decide si merecen otro ancla (arq. §4, Fase 3).
    escenas_poco_firmes: tuple[tuple[int, int], ...] = ()
    huecos: tuple[HuecoDelInforme, ...] = ()

    @property
    def inventados(self) -> int:
        return sum(self.inventados_por_dimension.values())

    @property
    def puede_avanzar(self) -> bool:
        """Si la revisión está en verde. Informa: el gate se puede aprobar igual."""
        return not any(i.bloquea for i in self.incidencias)

    def como_texto(self) -> str:
        lineas = [
            f"Escaleta: {self.capitulos} capitulos, {self.escenas} escenas.",
            f"Huecos de micro-investigacion gastados: {self.huecos_gastados}.",
        ]
        for h in self.huecos:
            donde = f"cap. {h.capitulo} esc. {h.escena}" if h.capitulo else "sin escena"
            como = {
                "encontrado": "encontrado",
                "inventado": "inventado con permiso",
            }.get(h.resultado or "", "sin cubrir")
            lineas.append(f"  - {h.pregunta} ({donde}): {como}")
        if self.inventados:
            lineas.append(f"\n{self.inventados} hecho(s) inventados con permiso, por dimension:")
            for dimension, cuantos in sorted(self.inventados_por_dimension.items()):
                lineas.append(f"  - {dimension}: {cuantos}")
            lineas.append(
                "No se topan a proposito: topar la invencion solo dejaria al arquitecto "
                "salidas peores. Cuanta libertad es aceptable lo declara el grado de "
                "licencia del encargo, y quien la juzga es el juez."
            )
        else:
            lineas.append("\nNingun hecho inventado: toda la escaleta se apoya en el corpus.")
        if self.micro_sin_respaldo:
            lineas.append(
                f"{self.micro_sin_respaldo} hecho(s) de la micro-investigacion sin respaldo: "
                "su firmeza no pasa de inferido."
            )
        if self.escenas_poco_firmes:
            lineas.append(
                f"{len(self.escenas_poco_firmes)} escena(s) se apoyan solo en hechos inferidos "
                "o desconocidos: "
                + ", ".join(f"cap. {c} esc. {o}" for c, o in self.escenas_poco_firmes)
                + ". No bloquea; si alguna sostiene un giro, merece un ancla documentado."
            )

        if self.incidencias:
            lineas.append("\nLa revision de la escaleta encontro esto:")
            for incidencia in self.incidencias:
                marca = "grave" if incidencia.bloquea else "aviso"
                lineas.append(f"  [{marca}] {incidencia.validador}: {incidencia.mensaje}")
            lineas.append(
                "Corregir esto aqui cuesta un parrafo de escaleta. Descubrirlo con la "
                "novela escrita cuesta diez capitulos. Si rehaces, el arquitecto recibe "
                "estos avisos ademas de tu comentario."
            )
        else:
            lineas.append("\nCobertura, arcos y cronologia en verde: la escaleta puede sellarse.")
        return "\n".join(lineas)

    def como_resumen(self) -> list[str]:
        """Lo mismo, para el móvil: cifras y avisos agrupados, sin una frase por aviso.

        El informe entero se lee en el PC, que es donde se decide (arq. §10). En el móvil
        basta con saber si merece la pena ir a mirar: cuántos huecos se inventaron y qué
        clase de avisos hay, lo grave primero.
        """
        encontrados = sum(1 for h in self.huecos if h.resultado == "encontrado")
        lineas: list[str] = []
        if self.huecos:
            lineas.append(
                f"Huecos: {_cuantos(encontrados, 'encontrado', 'encontrados')}, "
                f"{_cuantos(self.inventados, 'inventado', 'inventados')}"
            )
        elif self.inventados:
            lineas.append(f"Inventados: {self.inventados}")
        if not self.incidencias:
            lineas.append("Revisión en verde")
            return lineas
        graves = sum(1 for i in self.incidencias if i.bloquea)
        cabecera = f"Revisión: {_cuantos(len(self.incidencias), 'aviso', 'avisos')}"
        lineas.append(cabecera + (f", {_cuantos(graves, 'grave', 'graves')}" if graves else ""))
        por_tipo: dict[str, list[Incidencia]] = {}
        for incidencia in self.incidencias:
            por_tipo.setdefault(
                ETIQUETAS.get(incidencia.validador, incidencia.validador), []
            ).append(incidencia)
        orden = sorted(
            por_tipo.items(), key=lambda par: (not any(i.bloquea for i in par[1]), -len(par[1]))
        )
        for etiqueta, lista in orden:
            marca = " (grave)" if any(i.bloquea for i in lista) else ""
            lineas.append(f"  · {etiqueta}: {len(lista)}{marca}")
        return lineas


#: Cómo se nombra cada validador de la revisión fuera del código: las mismas etiquetas que
#: la pantalla del gate, para que el móvil y el PC hablen igual.
ETIQUETAS = {
    "cobertura_anclada": "elemento sin anclar",
    "cobertura_reparada": "anclado por el arnés",
    "arco_anclado": "arco",
    "escenas_por_capitulo": "escenas por capítulo",
    "anclaje_resuelto": "anclaje sin resolver",
    "anclaje_por_parecido": "anclado por parecido",
    "invencion_sobre_historico": "invención sobre un histórico",
    "cronologia_escaleta": "cronología",
    "lean_cronologia": "cronología",
}


def _cuantos(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


async def construir(
    db: aiosqlite.Connection, fase_run_id: int, puerta: PuertaDePlotting, *, huecos_gastados: int
) -> InformeDePlotting:
    """El informe de la trama vigente.

    La invención se cuenta en los huecos **de esta trama** cuando los hay, y en el corpus de
    `fase_run_id` si no: tras rehacer, lo inventado para la trama anterior sigue en el corpus
    pero ya no es obra de la que se está juzgando.
    """
    capitulos = await plan.total_de_capitulos(db)
    async with db.execute("SELECT COUNT(*) AS n FROM plan_escena") as cursor:
        fila = await cursor.fetchone()
    escenas = int(fila["n"]) if fila is not None else 0

    huecos = tuple(
        HuecoDelInforme(
            pregunta=str(h["pregunta"]),
            dimension=str(h["dimension"]),
            resultado=h["resultado"],
            enunciado=h["enunciado"],
            capitulo=h["capitulo"],
            escena=h["escena"],
        )
        for h in await plan.huecos_de_la_trama(db)
    )
    if huecos:
        inventados: dict[str, int] = {}
        for h in huecos:
            if h.resultado == "inventado":
                inventados[h.dimension] = inventados.get(h.dimension, 0) + 1
    else:
        inventados = await mundo.inventados_por_dimension(db, fase_run_id)

    return InformeDePlotting(
        capitulos=capitulos,
        escenas=escenas,
        inventados_por_dimension=inventados,
        huecos_gastados=huecos_gastados or sum(1 for h in huecos if h.resultado),
        incidencias=puerta.incidencias,
        micro_sin_respaldo=await mundo.micro_sin_respaldo(db, fase_run_id),
        escenas_poco_firmes=tuple(await plan.escenas_poco_firmes(db)),
        huecos=huecos,
    )
