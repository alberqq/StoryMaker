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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from storymaker.commons.agents.invocacion import invocar_rol
from storymaker.commons.agents.schema_guard import SalidaInvalida
from storymaker.commons.agents.techos import Perfil
from storymaker.commons.config import Defaults
from storymaker.commons.db.repos import arnes, mundo
from storymaker.commons.errores import ErrorDeEntorno, PresupuestoExcedido
from storymaker.commons.graph.contabilidad import corpus_de
from storymaker.commons.graph.dependencias import actuales
from storymaker.commons.graph.estado import EstadoNovela
from storymaker.commons.obs.prompts import RepositorioDePrompts
from storymaker.commons.obs.trazas import Span, nombre_de_span
from storymaker.commons.validation.policy_checker import pii_en_prompt_de_investigacion
from storymaker.investigation import corpus, prompts

if TYPE_CHECKING:
    import aiosqlite

from storymaker.investigation.esquemas import (
    Dimension,
    HuecoResuelto,
    SalidaInvestigador,
    SalidaVerificador,
)


async def investigar(
    periodo: str, lugar: str, *, fase_run_id: int, comentarios: str = ""
) -> list[int]:
    """Una sesión, tres búsquedas, seis dimensiones. Devuelve los hechos escritos.

    Que sea una sesión y no seis tiene una contrapartida que conviene decir en voz alta. A
    favor: el investigador ve a la vez lo que lleva encontrado para cada dimensión y puede
    cruzarlo. En contra: arrastra en su ventana el material de las tres páginas a la vez, y
    por eso su techo es el más alto del sistema y gobierna el peor caso de todo el arnés.
    """
    deps = actuales()
    prompt = prompts.prompt_de_investigacion(periodo, lugar)
    if comentarios:
        prompt += f"\nEl Autor pidio al rehacer la investigacion:\n{comentarios}\n"
    if pii_en_prompt_de_investigacion(prompt, await datos_personales(deps.db)):
        # La guarda de PII: un dato personal no sale por la puerta a internet. Sin sesión
        # queda el corpus vacío, que el gate enseña; es peor filtrar que investigar menos.
        await arnes.registrar_incidencia(
            deps.db,
            validador="investigacion_dirigida",
            severidad="aviso",
            mensaje="sesion unica: saltada, su prompt contenia un dato personal",
        )
        return []
    try:
        resultado = await invocar_rol(
            Perfil.INVESTIGADOR_INICIAL,
            prompt,
            SalidaInvestigador,
            transporte=deps.transporte,
            settings=deps.settings,
            sistema=RepositorioDePrompts(deps.settings).para(Perfil.INVESTIGADOR_INICIAL).texto,
        )
    except SalidaInvalida as fallo:
        # Una investigación sin resultado no detiene la novela: se sigue con el corpus
        # vacío y el aviso delante del Autor en el gate, igual que una sesión dirigida.
        await arnes.registrar_incidencia(
            deps.db,
            validador="investigacion_dirigida",
            severidad="aviso",
            mensaje=f"sesion unica: sin resultado, {fallo}",
        )
        return []
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
    """La micro-sesión que Plotting dispara. Una llamada, una búsqueda, dos finales posibles.

    **Un hueco no detiene la escaleta** (arq. §4). Si la micro-sesión se queda sin turnos o
    su salida no valida, el hueco se da por `no_encontrado` y el arquitecto inventa, que es
    el segundo final que la arquitectura ya declara válido. El presupuesto excedido sí
    sigue siendo un error: esa guarda existe para no emitir.
    """
    deps = actuales()
    prompt = prompts.prompt_de_hueco(pregunta, periodo, lugar)
    if pii_en_prompt_de_investigacion(prompt, await datos_personales(deps.db)):
        return HuecoResuelto(encontrado=False, motivo="la pregunta contenia un dato personal")
    try:
        resultado = await invocar_rol(
            Perfil.INVESTIGADOR_MICRO,
            prompt,
            HuecoResuelto,
            transporte=deps.transporte,
            settings=deps.settings,
            sistema=RepositorioDePrompts(deps.settings).para(Perfil.INVESTIGADOR_MICRO).texto,
        )
    except PresupuestoExcedido:
        raise
    except Exception as fallo:
        return HuecoResuelto(encontrado=False, motivo=f"micro-sesion sin respuesta: {fallo}")
    deps.observador.registrar_span(
        Span(
            nombre=nombre_de_span(capitulo=None, rol="investigador_micro"),
            rol="investigador",
            consumo=resultado.consumo,
        )
    )
    return resultado.valor


@dataclass(frozen=True)
class EncargoDirigido:
    """Una sesión del modo exhaustivo: qué se busca y con qué prompt."""

    nombre: str
    prompt: str


async def _datos_del_brief(db: aiosqlite.Connection) -> dict[str, Any]:
    import json

    async with db.execute("SELECT json FROM intake_brief ORDER BY id DESC LIMIT 1") as cursor:
        fila = await cursor.fetchone()
    return dict(json.loads(str(fila["json"]))) if fila is not None else {}


async def datos_personales(db: aiosqlite.Connection) -> list[str]:
    """Lo que no puede salir por la puerta a internet: el homenajeado y su encargo.

    Es la lista contra la que la guarda de PII mira cada prompt del investigador antes de
    emitirlo. El rol de época no está: describe la época, no a la persona (arq. §15).
    """
    datos = await _datos_del_brief(db)
    elementos = [str(e.get("valor", "")) for e in datos.get("elementos_personalizacion", [])]
    return [
        str(datos.get("nombre_homenajeado", "")),
        str(datos.get("fecha_nacimiento", "")),
        *elementos,
    ]


async def encargos_dirigidos(
    db: aiosqlite.Connection, periodo: str, lugar: str, comentarios: str
) -> list[EncargoDirigido]:
    """Las sesiones del modo exhaustivo, en el orden en que corren (arq. §4).

    Seis por dimensión y dos dirigidas por el brief: personajes históricos con el evento
    ancla, y el oficio. Las dos últimas se omiten si el brief no trae de qué.
    """
    encargos = [
        EncargoDirigido(
            nombre=f"dimension {d.value}",
            prompt=prompts.prompt_de_dimension(periodo, lugar, d, comentarios),
        )
        for d in Dimension
    ]
    datos = await _datos_del_brief(db)
    personajes = [
        str(p.get("nombre", ""))
        for p in datos.get("personajes_historicos", [])
        if p.get("debe_aparecer", True) and p.get("nombre")
    ]
    evento = str(datos.get("evento_ancla") or "")
    if personajes or evento:
        encargos.append(
            EncargoDirigido(
                nombre="personajes y evento ancla",
                prompt=prompts.prompt_de_personajes(
                    periodo, lugar, personajes, evento, comentarios
                ),
            )
        )
    oficio = str(datos.get("rol_epoca") or "")
    if oficio:
        encargos.append(
            EncargoDirigido(
                nombre="oficio",
                prompt=prompts.prompt_de_oficio(periodo, lugar, oficio, comentarios),
            )
        )
    return encargos


async def _avisar_sesion(db: aiosqlite.Connection, mensaje: str) -> None:
    await arnes.registrar_incidencia(
        db, validador="investigacion_dirigida", severidad="aviso", mensaje=mensaje
    )


async def investigar_exhaustiva(
    periodo: str, lugar: str, *, fase_run_id: int, comentarios: str = ""
) -> list[int]:
    """El modo exhaustivo: una sesión dirigida detrás de otra. Devuelve los hechos escritos.

    **Una sesión que falla no tumba a las demás.** Si su prompt lleva un dato personal, o
    su salida no valida tras los reintentos, se salta con un aviso en el informe del gate.
    Un error de entorno o el presupuesto excedido sí suben: no son un mal resultado de
    búsqueda, son una avería.
    """
    deps = actuales()
    personales = await datos_personales(deps.db)
    await arnes.retirar_incidencias_sin_capitulo(deps.db, "investigacion_dirigida")
    escritos: list[int] = []

    for numero, encargo in enumerate(
        await encargos_dirigidos(deps.db, periodo, lugar, comentarios), start=1
    ):
        if pii_en_prompt_de_investigacion(encargo.prompt, personales):
            await _avisar_sesion(
                deps.db, f"{encargo.nombre}: saltada, su prompt contenia un dato personal"
            )
            continue
        try:
            resultado = await invocar_rol(
                Perfil.INVESTIGADOR_DIRIGIDO,
                encargo.prompt,
                SalidaInvestigador,
                transporte=deps.transporte,
                settings=deps.settings,
                sistema=RepositorioDePrompts(deps.settings)
                .para(Perfil.INVESTIGADOR_DIRIGIDO)
                .texto,
            )
        except (PresupuestoExcedido, ErrorDeEntorno):
            raise
        except SalidaInvalida as fallo:
            await _avisar_sesion(deps.db, f"{encargo.nombre}: saltada, {fallo}")
            continue
        deps.observador.registrar_span(
            Span(
                nombre=nombre_de_span(capitulo=None, rol="investigador", intento=numero),
                rol="investigador",
                consumo=resultado.consumo,
            )
        )
        nuevos = await corpus.escribir_lote(
            deps.db, deps.vectorizador, resultado.valor.hechos, fase_run_id=fase_run_id
        )
        escritos += nuevos
        await _avisar_sesion(deps.db, f"{encargo.nombre}: {len(nuevos)} hecho(s)")

    return escritos


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
        comentarios = "\n".join(
            f"- {c}" for c in await arnes.comentarios_de_rehacer(deps.db, "investigation")
        )
        if estado.get("investigacion", "estandar") == "exhaustiva":
            await investigar_exhaustiva(
                periodo, lugar, fase_run_id=corpus_de(estado), comentarios=comentarios
            )
        else:
            await investigar(
                periodo, lugar, fase_run_id=corpus_de(estado), comentarios=comentarios
            )
    return {**estado, "pc": "VerifyCorpus"}


async def verify(estado: EstadoNovela) -> EstadoNovela:
    """El nodo del verificador. **No degrada nunca hasta el punto de detener la fase.**

    Una novela de regalo no se para porque una fecha del contexto venga mal citada: por eso
    ninguna arista del grafo depende de este veredicto, y el corpus es lo único que el Autor
    revisa con el informe delante.
    """
    await verificar_respaldo(corpus_de(estado))
    return {**estado, "pc": "AwaitApproval2"}
