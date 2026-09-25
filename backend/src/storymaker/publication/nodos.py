"""spec: §4.5 · arq: §4, §9, §11c

Fase 5 · Publication. Los nodos `Judge` y `PublishVersion`.

**Publication no lleva gate humano**, porque el manuscrito ya se aprobó al cerrar Writing y
lo único que queda entre medias es automático. Eso pone toda la responsabilidad en las dos
puertas que sí hay, y las dos son de las que no admiten excepción: **Lean sobre la
cronología completa** y **`render_visual` antes del `commit`**.

El orden dentro de `PublishVersion` es lo que lo hace una puerta y no un informe: se compone
la versión candidata, se comprueba su cronología, se abre su lectura en un navegador, y
**solo entonces** se escriben las filas de la versión. Si algo falla no hay nada que
deshacer, porque todavía no existe nada.

**El rechazo vuelve al gate de Writing.** Lo que falla se guarda como incidencia citando los
capítulos culpables, y la novela vuelve al Autor por la arista `PublishVersion →
AwaitApproval4`; si rehace, se reescriben esos capítulos y su escritor recibe el motivo en
el encargo. El rechazo comparte contador con el del juez, y agotado va a `Fail`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import aiosqlite
import yaml

from storymaker.commons.agents.invocacion import invocar_rol
from storymaker.commons.agents.techos import Perfil
from storymaker.commons.db.repos import arnes, plan, texto
from storymaker.commons.errores import ErrorDeStoryMaker
from storymaker.commons.formal.cronologia import cronologia_de_la_novela, verificar_cronologia
from storymaker.commons.formal.generador import (
    NovelaLean,
)
from storymaker.commons.graph.dependencias import actuales
from storymaker.commons.graph.estado import EstadoNovela
from storymaker.commons.obs.prompts import RepositorioDePrompts
from storymaker.commons.obs.scores import registrar, registrar_veredicto
from storymaker.commons.obs.trazas import Span, nombre_de_span
from storymaker.commons.validation.modelos import Incidencia
from storymaker.publication import manifiesto, render
from storymaker.publication.candidata import componer
from storymaker.publication.esquemas import UMBRAL_DE_PUBLICACION, Criterio, SalidaJuez


class PublicacionRechazada(ErrorDeStoryMaker):
    """La versión no se publica. **No hay anulación.**

    Se lanza cuando Lean tumba la cronología completa o cuando el render candidato no pasa,
    y lleva las incidencias bloqueantes que lo causaron. `publish` la recoge, las guarda y
    devuelve la novela al gate de Writing: el Autor decide qué se rehace.
    """

    def __init__(self, mensaje: str, incidencias: tuple[Incidencia, ...] = ()) -> None:
        super().__init__(mensaje)
        self.incidencias = incidencias


#: Los validadores de `PublishVersion`. Sus incidencias cuelgan de la novela, no de un
#: capítulo, y citan los capítulos culpables en el texto para que el gate los devuelva.
VALIDADORES_DE_PUBLICACION = ("cronologia_publicacion", "render_visual")


@dataclass(frozen=True)
class VersionPublicada:
    version_id: int
    manifiesto_id: int
    media_del_juez: float


async def juzgar(*, capitulos: list[str]) -> SalidaJuez:
    """El juez lee la novela terminada y aplica la rúbrica de ocho criterios.

    Recibe el texto y devuelve notas. No tiene permiso de escritura sobre el texto y su
    esquema no le da dónde ejercerlo: su única salida es el esquema de puntuaciones, que se
    inyecta como *scores* en la traza.
    """
    deps = actuales()
    novela = "\n\n".join(f"Capitulo {i}\n{t}" for i, t in enumerate(capitulos, start=1))
    prompt = RepositorioDePrompts(deps.settings).para(Perfil.JUEZ)
    resultado = await invocar_rol(
        Perfil.JUEZ,
        _rubrica() + "\n\n# La novela\n\n" + novela,
        SalidaJuez,
        transporte=deps.transporte,
        settings=deps.settings,
        sistema=prompt.texto,
    )
    deps.observador.registrar_span(
        Span(
            nombre=nombre_de_span(capitulo=None, rol="juez"),
            rol="juez",
            consumo=resultado.consumo,
            prompt_version=prompt.version,
        )
    )
    return resultado.valor


@cache
def _rubrica() -> str:
    """Las ocho preguntas de `rubrica.yaml`, el mismo fichero que usa la revisión humana.

    Sin ellas el juez puntuaba ocho criterios de los que solo conocía el nombre.
    """
    ruta = Path(__file__).with_name("rubrica.yaml")
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    preguntas = "\n".join(
        f"- **{c['nombre']}**: {c['pregunta']}" for c in datos.get("criterios", [])
    )
    return (
        "Antes de puntuar, lee la novela entera buscando **contradicciones** y enumeralas en "
        "`contradicciones`, una por entrada y citando los capitulos: lo que un capitulo "
        "afirma y otro desmiente (un objeto que se entrega dos veces, una promesa que luego "
        "se niega, un dato que cambia), y lo que un personaje sabe o cuenta antes de que "
        "ocurra en la fecha narrativa. Si no hay ninguna, deja la lista vacia.\n\n"
        "Despues puntua esta novela del 1 al 10 en cada uno de los ocho criterios de la "
        "rubrica, con una justificacion por criterio.\n\n# Rubrica\n\n" + preguntas
    )


def topar_continuidad(notas: SalidaJuez) -> SalidaJuez:
    """La nota de continuidad no pasa de `10 - 2n` con `n` contradicciones, ni baja de 1.

    El juez cuenta; cuánto pesa cada contradicción no lo decide él. En la cuarta novela real
    puso un 8 en continuidad a una novela con cinco contradicciones que él mismo podía ver.
    """
    techo = max(1, 10 - 2 * len(notas.contradicciones))
    return notas.model_copy(
        update={
            "puntuaciones": [
                p.model_copy(update={"valor": min(p.valor, techo)})
                if p.criterio is Criterio.CONTINUIDAD
                else p
                for p in notas.puntuaciones
            ]
        }
    )


async def cronologia_completa() -> NovelaLean:
    """Toda la cronología de la novela: lo histórico y lo narrativo de lo aprobado.

    Es el tercero de los tres puntos de Lean, y el único cuyo fallo **impide publicar**. Los
    otros dos devuelven el trabajo a alguien; este no tiene a quién devolvérselo. Solo
    cuentan las versiones aprobadas vigentes: los eventos de un intento descartado
    describen algo que ya no está en la novela.
    """
    return await cronologia_de_la_novela(actuales().db)


async def publicar(*, numero: int, gate_id: int | None = None) -> VersionPublicada:
    """Compone la candidata, comprueba cronología y render, y **solo entonces** la escribe.

    El orden es la puerta. Si `render_visual` se ejecutara después de escribir la versión, un
    índice roto sería una versión ya publicada, y G5 existe precisamente para impedir eso.
    Las dos comprobaciones corren siempre, también si la primera falla, para que el Autor
    vea de una vez todo lo que tiene que rehacer; cada una deja su *score*.
    """
    deps = actuales()

    total = await plan.total_de_capitulos(deps.db)
    versiones: list[int] = []
    for n in range(1, total + 1):
        capitulo = await plan.capitulo_por_numero(deps.db, n)
        if capitulo is None:
            continue
        aprobado = await texto.capitulo_aprobado(deps.db, int(capitulo["id"]))
        if aprobado is None:
            raise PublicacionRechazada(
                f"El capitulo {n} no esta aprobado: la version no se puede componer."
            )
        versiones.append(int(aprobado["id"]))

    # G5: la cronología completa y el render, antes de que exista la versión (arq. §11a, §11c).
    cronologia = await verificar_cronologia(
        await cronologia_completa(), bloquea=True, validador="cronologia_publicacion"
    )
    lectura = await render.construir_lectura_candidata(deps.db, versiones)
    visuales = await render.render_visual(lectura)

    por_validador = {"cronologia_publicacion": cronologia, "render_visual": visuales}
    for validador, incidencias in por_validador.items():
        await registrar_veredicto(
            deps.db,
            deps.observador,
            validador=validador,
            incidencias=[i for i in incidencias if i.bloquea],
            objeto_tipo="novela",
            objeto_id=numero,
        )

    bloqueantes = tuple(i for i in (*cronologia, *visuales) if i.bloquea)
    if bloqueantes:
        raise PublicacionRechazada(
            "La version candidata no se publica: " + "; ".join(i.mensaje for i in bloqueantes),
            bloqueantes,
        )

    version_id = await texto.publicar_version(
        deps.db, numero=numero, capitulo_version_ids=versiones, gate_id=gate_id
    )
    datos = await manifiesto.reunir(deps.db, deps.settings)
    manifiesto_id = await manifiesto.escribir(deps.db, version_id, datos)

    return VersionPublicada(version_id=version_id, manifiesto_id=manifiesto_id, media_del_juez=0.0)


_CAPITULO_CITADO_EN_INCIDENCIA = re.compile(r"\bcap(?:itulo)?[\s_-]?(\d+)", re.IGNORECASE)


def capitulos_citados(incidencia: Incidencia) -> list[int]:
    """Los capítulos que una incidencia de la publicación nombra, en orden.

    Las de la cronología citan los eventos por su clave (`cap4-esc10`), y las del render la
    pieza o el capítulo (`cap3`). Es lo que permite al gate de Writing devolver al escritor
    justo esos capítulos y no la novela entera.
    """
    texto_citado = " ".join(
        t for t in (incidencia.ubicacion, incidencia.mensaje, incidencia.propuesta) if t
    )
    return sorted({int(n) for n in _CAPITULO_CITADO_EN_INCIDENCIA.findall(texto_citado)})


async def registrar_rechazo(db: aiosqlite.Connection, incidencias: tuple[Incidencia, ...]) -> None:
    """Guarda el rechazo como incidencias de la novela, sustituyendo las del intento anterior.

    `ubicacion` lleva los capítulos citados (`cap1, cap5`), igual que las contradicciones del
    juez, para que el gate de Writing y el encargo del escritor los lean del mismo modo.
    """
    for validador in VALIDADORES_DE_PUBLICACION:
        await arnes.retirar_incidencias_sin_capitulo(db, validador)
    for incidencia in incidencias:
        citados = capitulos_citados(incidencia)
        await arnes.registrar_incidencia(
            db,
            validador=incidencia.validador,
            severidad="bloqueante",
            mensaje=incidencia.mensaje,
            ubicacion=", ".join(f"cap{n}" for n in citados) or incidencia.ubicacion,
            propuesta=incidencia.propuesta,
        )


# --- Los nodos del grafo -------------------------------------------------------------


async def judge(estado: EstadoNovela) -> EstadoNovela:
    """`Judge`. Umbral superado → publicar; no superado → vuelta al gate de Writing.

    El umbral se calcula **en Python sobre las notas**, no se le pregunta al juez si su
    novela es publicable: eso sería dejarle decidir sobre su propia métrica.
    """
    deps = actuales()
    candidata = await componer(deps.db)
    textos = []
    for version_id in candidata.capitulo_version_ids:
        async with deps.db.execute(
            "SELECT texto FROM capitulo_version WHERE id = ?", (version_id,)
        ) as cursor:
            fila = await cursor.fetchone()
        if fila is not None:
            textos.append(str(fila["texto"]))

    if not textos:
        return {**estado, "pc": "Judge", "hay_bloqueantes": True}

    notas = topar_continuidad(await juzgar(capitulos=textos))
    await registrar(
        deps.db,
        deps.observador,
        validador="juez_rubrica",
        valor=notas.media,
        objeto_tipo="novela",
        objeto_id=1,
        detalle={**notas.por_criterio(), "contradicciones": notas.contradicciones},
    )
    await registrar_contradicciones(deps.db, notas.contradicciones)
    supera = supera_el_umbral(notas)
    if not supera and not estado["gates_enabled"]:
        # En batch nadie puede decidir qué rehacer, y volver a juzgar el mismo texto solo
        # lleva a `Fail` al segundo rechazo. La nota queda registrada; la novela se publica.
        supera = True
    return {
        **estado,
        "pc": "Judge",
        "hay_bloqueantes": not supera,
        "rechazos_juez": estado["rechazos_juez"] + (0 if supera else 1),
    }


async def publish(estado: EstadoNovela) -> EstadoNovela:
    """`PublishVersion`. Publicada → `Idle`; rechazada → al gate de Writing o a `Fail`.

    El rechazo no es una excepción que tumbe la invocación: se guarda, suma un rechazo al
    contador que comparte con el juez y deja `hay_bloqueantes` para que `tras_publish` elija
    la arista. Una versión que no se puede ni componer —un capítulo sin aprobar— sí revienta,
    porque ahí no hay nada que devolver a nadie.
    """
    deps = actuales()
    async with deps.db.execute(
        "SELECT COALESCE(MAX(numero), 0) + 1 AS siguiente FROM version_novela"
    ) as cursor:
        fila = await cursor.fetchone()
    numero = int(fila["siguiente"]) if fila is not None else 1

    try:
        await publicar(numero=numero, gate_id=estado["gate_id"])
    except PublicacionRechazada as rechazo:
        if not rechazo.incidencias:
            raise
        await registrar_rechazo(deps.db, rechazo.incidencias)
        return {
            **estado,
            "pc": "PublishVersion",
            "hay_bloqueantes": True,
            "rechazos_juez": estado["rechazos_juez"] + 1,
        }
    await registrar_rechazo(deps.db, ())
    # El PDF no se imprime aquí: dentro del paso la versión aún no está confirmada, y la ruta
    # de impresión la lee por la API. Lo imprime `invocar` al salir del grafo (spec §4.5).
    return {**estado, "pc": "Idle", "hay_bloqueantes": False}


#: Las contradicciones que lista el juez, una incidencia de aviso cada una.
CONTRADICCION_DEL_JUEZ = "juez_contradiccion"
_CAPITULO_CITADO = re.compile(r"[Cc]ap[ií]tulos?\s+(\d+)")


async def registrar_contradicciones(db: aiosqlite.Connection, contradicciones: list[str]) -> None:
    """Cada contradicción del juez, como aviso sin capítulo con los capítulos que cita.

    Antes solo vivían dentro de la nota: la de `metro` —la edad de la homenajeada, diez años
    distinta entre el capítulo 1 y el 5— no llegó a nadie que pudiera corregirla. Así las
    enseñan el gate de Writing, si el juez devuelve la novela, y el aviso de terminada, si
    no (specs/escritura §6). Cada juicio sustituye al anterior.
    """
    await arnes.retirar_incidencias_sin_capitulo(db, CONTRADICCION_DEL_JUEZ)
    for contradiccion in contradicciones:
        citados = sorted({int(n) for n in _CAPITULO_CITADO.findall(contradiccion)})
        await arnes.registrar_incidencia(
            db,
            validador=CONTRADICCION_DEL_JUEZ,
            severidad="aviso",
            mensaje=contradiccion,
            ubicacion=", ".join(f"cap{n}" for n in citados) or None,
        )


def supera_el_umbral(salida: SalidaJuez, umbral: float = UMBRAL_DE_PUBLICACION) -> bool:
    """El booleano que lee la arista. Calculado en Python sobre las notas, no interpretado."""
    return salida.media >= umbral
