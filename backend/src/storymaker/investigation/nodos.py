"""spec: §4.2 · arq: §4, §9

Fase 2 · Investigation. Los nodos `Research` y `VerifyCorpus`.

La fase tiene **dos pasos y dos agentes distintos**: uno rellena el corpus y otro comprueba
que lo que dice está donde dice que está. Es la misma separación que rige al editor y al
juez —quien escribe no aprueba—, aplicada aquí a los hechos históricos. Si el propio
investigador declarase que sus hechos están respaldados, el respaldo mediría la seguridad
en sí mismo de quien tiene incentivo en haber terminado.

`VerifyCorpus` es **un nodo y no una herramienta** que el investigador decida invocar, por
la razón de §1: lo que un agente puede olvidarse de llamar no es una comprobación.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from storymaker.commons.agents.invocacion import invocar_rol
from storymaker.commons.agents.techos import Perfil
from storymaker.commons.config import Defaults
from storymaker.commons.db.repos import mundo
from storymaker.commons.graph.dependencias import actuales
from storymaker.commons.graph.estado import EstadoNovela
from storymaker.commons.obs.prompts import RepositorioDePrompts
from storymaker.commons.obs.trazas import Span, nombre_de_span
from storymaker.investigation import corpus, prompts

if TYPE_CHECKING:
    import aiosqlite

from storymaker.investigation.esquemas import (
    HuecoResuelto,
    SalidaInvestigador,
    SalidaVerificador,
)


async def investigar(periodo: str, lugar: str, *, fase_run_id: int) -> list[int]:
    """Una sesión, tres búsquedas, seis dimensiones. Devuelve los hechos escritos.

    Que sea una sesión y no seis tiene una contrapartida que conviene decir en voz alta. A
    favor: el investigador ve a la vez lo que lleva encontrado para cada dimensión y puede
    cruzarlo. En contra: arrastra en su ventana el material de las tres páginas a la vez, y
    por eso su techo es el más alto del sistema y gobierna el peor caso de todo el arnés.
    """
    deps = actuales()
    resultado = await invocar_rol(
        Perfil.INVESTIGADOR_INICIAL,
        prompts.prompt_de_investigacion(periodo, lugar),
        SalidaInvestigador,
        transporte=deps.transporte,
        settings=deps.settings,
        sistema=RepositorioDePrompts(deps.settings).para(Perfil.INVESTIGADOR_INICIAL).texto,
    )
    deps.observador.registrar_span(
        Span(
            nombre=nombre_de_span(capitulo=None, rol="investigador"),
            rol="investigador",
            consumo=resultado.consumo,
        )
    )
    return await corpus.escribir_lote(
        deps.db, deps.vectorizador, resultado.valor.hechos, fase_run_id=fase_run_id
    )


async def verificar_respaldo(fase_run_id: int) -> tuple[int, int]:
    """Lee los pares enunciado-cita **por lotes de veinte**. Devuelve (respaldados, sin respaldo).

    El troceo no es cosmético: evita que el tamaño del corpus convierta la comprobación en
    una llamada que la guarda de presupuesto rechaza por pasarse de contexto, que sería el
    peor final posible — el corpus se quedaría sin verificar y nadie se enteraría.
    """
    deps = actuales()
    lotes = await mundo.pendientes_de_verificar(
        deps.db, fase_run_id, tamano_lote=Defaults.HECHOS_POR_LOTE_VERIFICADOR
    )
    respaldados = 0
    sin_respaldo = 0

    for numero, lote in enumerate(lotes, start=1):
        pares = [
            (int(fila["id"]), str(fila["enunciado"]), str(fila["cita"] or "")) for fila in lote
        ]
        resultado = await invocar_rol(
            Perfil.VERIFICADOR,
            prompts.prompt_de_verificacion(pares),
            SalidaVerificador,
            transporte=deps.transporte,
            settings=deps.settings,
            sistema=RepositorioDePrompts(deps.settings).para(Perfil.VERIFICADOR).texto,
        )
        deps.observador.registrar_span(
            Span(
                nombre=nombre_de_span(capitulo=None, rol="verificador", intento=numero),
                rol="verificador",
                consumo=resultado.consumo,
            )
        )
        for veredicto in resultado.valor.veredictos:
            await corpus.degradar_sin_respaldo(deps.db, veredicto.hecho_id, veredicto.respaldado)
            if veredicto.respaldado:
                respaldados += 1
            else:
                sin_respaldo += 1

    return respaldados, sin_respaldo


async def resolver_hueco(pregunta: str, periodo: str, lugar: str) -> HuecoResuelto:
    """La micro-sesión que Plotting dispara. Una llamada, una búsqueda, dos finales posibles."""
    deps = actuales()
    resultado = await invocar_rol(
        Perfil.INVESTIGADOR_MICRO,
        prompts.prompt_de_hueco(pregunta, periodo, lugar),
        HuecoResuelto,
        transporte=deps.transporte,
        settings=deps.settings,
        sistema=RepositorioDePrompts(deps.settings).para(Perfil.INVESTIGADOR_MICRO).texto,
    )
    deps.observador.registrar_span(
        Span(
            nombre=nombre_de_span(capitulo=None, rol="investigador_micro"),
            rol="investigador",
            consumo=resultado.consumo,
        )
    )
    return resultado.valor


async def periodo_y_lugar(db: aiosqlite.Connection) -> tuple[str, str]:
    """Lee del brief **solo** lo que el investigador puede recibir.

    Dos cadenas, y nada mas. No se le pasa el `Brief`: no se puede filtrar lo que no se
    tiene, y este rol es el unico con acceso a la red.
    """
    import json

    async with db.execute("SELECT json FROM intake_brief ORDER BY id DESC LIMIT 1") as cursor:
        fila = await cursor.fetchone()
    if fila is None:
        return "", ""
    datos = json.loads(str(fila["json"]))
    periodo = datos.get("periodo", {})
    denominacion = periodo.get("denominacion", "")
    rango = f"{periodo.get('inicio', '')}-{periodo.get('fin', '')}".strip("-")
    return f"{denominacion} ({rango})".strip(), str(datos.get("lugar", ""))


async def research(estado: EstadoNovela) -> EstadoNovela:
    """El nodo. La única puerta a internet de todo el sistema."""
    deps = actuales()
    periodo, lugar = await periodo_y_lugar(deps.db)
    if periodo or lugar:
        await investigar(periodo, lugar, fase_run_id=estado["fase_run_id"])
    return {**estado, "pc": "VerifyCorpus"}


async def verify(estado: EstadoNovela) -> EstadoNovela:
    """El nodo del verificador. **No degrada nunca hasta el punto de detener la fase.**

    Una novela de regalo no se para porque una fecha del contexto venga mal citada: por eso
    ninguna arista del grafo depende de este veredicto, y el corpus es lo único que el Autor
    revisa con el informe delante.
    """
    await verificar_respaldo(estado["fase_run_id"])
    return {**estado, "pc": "AwaitApproval2"}
