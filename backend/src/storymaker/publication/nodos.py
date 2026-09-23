"""spec: §4.5 · arq: §4, §9, §11c

Fase 5 · Publication. Los nodos `Judge` y `PublishVersion`.

**Publication no lleva gate humano**, porque el manuscrito ya se aprobó al cerrar Writing y
lo único que queda entre medias es automático. Eso pone toda la responsabilidad en las dos
puertas que sí hay, y las dos son de las que no admiten excepción: **Lean sobre la
cronología completa** y **`render_visual` antes del `commit`**.

El orden dentro de `PublishVersion` es lo que lo hace una puerta y no un informe: se arma el
manifiesto de la versión candidata, se renderiza contra él, se juzga el render, y **solo
entonces** se confirma la transacción. Si algo no renderiza, se deshace y no hay versión
publicada. No hace falta nodo nuevo ni arista nueva, porque la comprobación cabe dentro del
propio nodo mientras la transacción sigue abierta.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

from storymaker.commons.agents.invocacion import invocar_rol
from storymaker.commons.agents.techos import Perfil
from storymaker.commons.db.repos import plan, texto
from storymaker.commons.errores import ErrorDeStoryMaker
from storymaker.commons.formal.generador import Evento, NovelaLean, Persona, a_momento
from storymaker.commons.graph.dependencias import actuales
from storymaker.commons.graph.estado import EstadoNovela
from storymaker.commons.obs.prompts import RepositorioDePrompts
from storymaker.commons.obs.scores import registrar
from storymaker.commons.obs.trazas import Span, nombre_de_span
from storymaker.commons.validation.modelos import Incidencia
from storymaker.publication import manifiesto, render
from storymaker.publication.candidata import componer
from storymaker.publication.esquemas import UMBRAL_DE_PUBLICACION, SalidaJuez


class PublicacionRechazada(ErrorDeStoryMaker):
    """La versión no se publica. **No hay anulación.**

    Se lanza cuando Lean tumba la cronología completa o cuando el render candidato no pasa.
    Es una excepción y no una incidencia porque no hay a quién devolverle el capítulo: lo
    que falla aquí es la novela entera, y la decisión de qué hacer es del Autor.
    """


@dataclass(frozen=True)
class VersionPublicada:
    version_id: int
    manifiesto_id: int
    media_del_juez: float


async def juzgar(*, capitulos: list[str]) -> SalidaJuez:
    """El juez lee la novela terminada y aplica la rúbrica de siete criterios.

    Recibe el texto y devuelve notas. No tiene permiso de escritura sobre el texto y su
    esquema no le da dónde ejercerlo: su única salida es el esquema de puntuaciones, que se
    inyecta como *scores* en la traza.
    """
    deps = actuales()
    novela = "\n\n".join(f"Capitulo {i}\n{t}" for i, t in enumerate(capitulos, start=1))
    resultado = await invocar_rol(
        Perfil.JUEZ,
        _rubrica() + "\n\n# La novela\n\n" + novela,
        SalidaJuez,
        transporte=deps.transporte,
        settings=deps.settings,
        sistema=RepositorioDePrompts(deps.settings).para(Perfil.JUEZ).texto,
    )
    deps.observador.registrar_span(
        Span(
            nombre=nombre_de_span(capitulo=None, rol="juez"),
            rol="juez",
            consumo=resultado.consumo,
        )
    )
    return resultado.valor


@cache
def _rubrica() -> str:
    """Las siete preguntas de `rubrica.yaml`, el mismo fichero que usa la revisión humana.

    Sin ellas el juez puntuaba siete criterios de los que solo conocía el nombre.
    """
    ruta = Path(__file__).with_name("rubrica.yaml")
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    preguntas = "\n".join(
        f"- **{c['nombre']}**: {c['pregunta']}" for c in datos.get("criterios", [])
    )
    return (
        "Puntua esta novela del 1 al 10 en cada uno de los siete criterios de la rubrica, "
        "con una justificacion por criterio.\n\n# Rubrica\n\n" + preguntas
    )


async def cronologia_completa() -> NovelaLean:
    """Toda la cronología de la novela: lo histórico y lo narrativo que el extractor escribió.

    Es el tercero de los tres puntos de Lean, y el único cuyo fallo **impide publicar**. Los
    otros dos devuelven el trabajo a alguien; este no tiene a quién devolvérselo.
    """
    deps = actuales()
    personas: list[Persona] = []
    async with deps.db.execute(
        "SELECT id, nombre, fecha_nacimiento, fecha_muerte FROM canon_personaje ORDER BY id"
    ) as cursor:
        for fila in await cursor.fetchall():
            personas.append(
                Persona(
                    id=int(fila["id"]),
                    nombre=str(fila["nombre"]),
                    nacimiento=a_momento(fila["fecha_nacimiento"]) or 0,
                    muerte=a_momento(fila["fecha_muerte"]),
                )
            )

    eventos: list[Evento] = []
    async with deps.db.execute(
        "SELECT id, clave, momento, origen FROM cronologia_evento ORDER BY momento, id"
    ) as cursor:
        filas = list(await cursor.fetchall())

    for fila in filas:
        momento = a_momento(fila["momento"])
        if momento is None:
            continue
        async with deps.db.execute(
            "SELECT personaje_id FROM cronologia_participante WHERE evento_id = ?",
            (fila["id"],),
        ) as cursor:
            participantes = tuple(int(p["personaje_id"]) for p in await cursor.fetchall())
        eventos.append(
            Evento(
                id=int(fila["id"]),
                clave=str(fila["clave"]),
                momento=momento,
                lugar=0,
                participantes=participantes,
                objetos=(),
                origen=str(fila["origen"]),
            )
        )

    return NovelaLean(personas=tuple(personas), objetos=(), eventos=tuple(eventos))


async def publicar(*, numero: int, gate_id: int | None = None) -> VersionPublicada:
    """Arma la versión candidata, comprueba el render y **solo entonces** confirma.

    El orden es la puerta. Si `render_visual` se ejecutara después del `commit`, un índice
    roto sería una versión ya publicada, y G5 existe precisamente para impedir eso.
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

    version_id = await texto.publicar_version(
        deps.db, numero=numero, capitulo_version_ids=versiones, gate_id=gate_id
    )

    lectura = await render.construir_lectura(deps.db, version_id)
    incidencias: list[Incidencia] = render.render_visual(lectura)
    if incidencias:
        # La transacción sigue abierta: quien nos llamó la deshará, y no habrá versión.
        raise PublicacionRechazada(
            "El render de la version candidata no pasa: "
            + "; ".join(i.mensaje for i in incidencias)
        )

    datos = await manifiesto.reunir(deps.db, deps.settings)
    manifiesto_id = await manifiesto.escribir(deps.db, version_id, datos)

    return VersionPublicada(version_id=version_id, manifiesto_id=manifiesto_id, media_del_juez=0.0)


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

    notas = await juzgar(capitulos=textos)
    await registrar(
        deps.db,
        deps.observador,
        validador="juez_rubrica",
        valor=notas.media,
        objeto_tipo="novela",
        objeto_id=1,
        detalle=notas.por_criterio(),
    )
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
    """`PublishVersion`. Render comprobado antes del `commit`, manifiesto escrito después."""
    deps = actuales()
    async with deps.db.execute(
        "SELECT COALESCE(MAX(numero), 0) + 1 AS siguiente FROM version_novela"
    ) as cursor:
        fila = await cursor.fetchone()
    numero = int(fila["siguiente"]) if fila is not None else 1

    publicada = await publicar(numero=numero, gate_id=estado["gate_id"])
    await _imprimir(publicada.version_id, Path(estado["novela"]).with_suffix(f".v{numero}.pdf"))
    return {**estado, "pc": "Idle"}


async def _imprimir(version_id: int, destino: Path) -> None:
    """El PDF de la versión ya publicada, junto al fichero de la novela.

    Va **después** de publicar y su fallo es un aviso: la versión ya está validada y el PDF
    se deriva de ella, así que un navegador ausente no puede deshacer una publicación.
    """
    deps = actuales()
    try:
        lectura = await render.construir_lectura(deps.db, version_id)
        await render.imprimir_pdf(lectura.como_html(), str(destino))
    except Exception as fallo:
        print(f"Aviso: version publicada, pero el PDF no se genero: {fallo}", file=sys.stderr)
        return
    print(f"PDF: {destino}", file=sys.stderr)


def supera_el_umbral(salida: SalidaJuez, umbral: float = UMBRAL_DE_PUBLICACION) -> bool:
    """El booleano que lee la arista. Calculado en Python sobre las notas, no interpretado."""
    return salida.media >= umbral
