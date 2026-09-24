"""spec: §4.4 · arq: §4, §11a, §11c

Las dos pasadas de `Validate`, y **por qué son dos y no una**.

La primera es **determinista y de coste cero**: los validadores programáticos que actúan
sobre el capítulo, solo texto contra filas ya escritas. La segunda es **la del extractor**,
una sola llamada y solo si la anterior no dejó incidencias.

Preguntar cuesta y contar no. No tiene sentido preguntarle a un modelo si los beats
ocurrieron en un capítulo al que le faltan cuatrocientas palabras o que escribe mal el
nombre del homenajeado: primero lo que es gratis y seguro; la llamada, solo cuando el
capítulo ya es defendible.

**Lean va en la segunda pasada**, porque depende del extractor: las filas de
`cronologia_evento` con `origen = 'narrativo'` las escribe él al leer el texto. Ponerlo en
la determinista lo dejaría verificando una cronología que llega hasta N-1, es decir,
detectando un capítulo tarde justo el fallo que mejor detecta.
"""

from __future__ import annotations

import aiosqlite

from storymaker.commons.db.repos import canon, intake, plan, texto
from storymaker.commons.validation.chapter_validator import (
    cobertura_capitulo,
    validar_capitulo,
)
from storymaker.commons.validation.modelos import (
    AnclajeDeEscena,
    CapituloEnRevision,
    EntidadFechada,
    Incidencia,
    Severidad,
    TerminoProhibido,
)
from storymaker.commons.validation.policy_checker import guardrail_prohibidas
from storymaker.writing.esquemas import SalidaExtractorDeCapitulo


async def construir_revision(
    db: aiosqlite.Connection,
    *,
    numero: int,
    texto_capitulo: str,
    palabras: int,
    rango_palabras: tuple[int, int],
) -> CapituloEnRevision:
    """Traduce la base a los tipos del Core Domain. **El validador no ve SQLite.**

    Es lo que permite que la misma función juzgue un capítulo recién generado y uno que una
    persona acaba de editar a mano en el disco.
    """
    nombres = tuple(str(p["nombre"]) for p in await plan.personajes_de(db, numero))
    prohibidas = tuple(
        TerminoProhibido(str(p["nivel"]), str(p["termino"]), str(p["normalizado"]))
        for p in await canon.prohibidas(db)
    )

    entidades: list[EntidadFechada] = []
    async with db.execute(
        "SELECT nombre, nombre_epoca, fecha_inicio, fecha_fin FROM mundo_entidad"
    ) as cursor:
        for fila in await cursor.fetchall():
            entidades.append(
                EntidadFechada(
                    nombre=str(fila["nombre"]),
                    fecha_inicio=fila["fecha_inicio"],
                    fecha_fin=fila["fecha_fin"],
                )
            )
            if fila["nombre_epoca"]:
                entidades.append(
                    EntidadFechada(
                        nombre=str(fila["nombre_epoca"]),
                        fecha_inicio=fila["fecha_inicio"],
                        fecha_fin=fila["fecha_fin"],
                    )
                )

    anclajes = tuple(
        AnclajeDeEscena(
            escena_id=int(a["escena_id"]),
            hecho_id=a["hecho_id"],
            entidad_id=a["entidad_id"],
            dato_id=a["dato_id"],
        )
        for a in await plan.anclajes_de(db, numero)
    )

    async with db.execute("SELECT id FROM mundo_hecho") as cursor:
        sellados = frozenset(int(f["id"]) for f in await cursor.fetchall())
    async with db.execute("SELECT hecho_id FROM canon_licencia WHERE declarada = 1") as cursor:
        licencias = frozenset(
            int(f["hecho_id"]) for f in await cursor.fetchall() if f["hecho_id"] is not None
        )

    escenas = await plan.escenas_de(db, numero)
    fecha = (
        str(escenas[0]["fecha_narrativa"])
        if escenas and escenas[0]["fecha_narrativa"]
        else None
    )

    datos = await intake.datos_de_capitulo(db, numero)
    encomendados = tuple(int(d["id"]) for d in datos)
    textos = tuple((int(d["id"]), intake.texto_de_dato(d["valor_json"])) for d in datos)

    return CapituloEnRevision(
        numero=numero,
        texto=texto_capitulo,
        palabras=palabras,
        rango_palabras=rango_palabras,
        nombres_canonicos=nombres,
        prohibidas=prohibidas,
        entidades_fechadas=tuple(entidades),
        fecha_narrativa=fecha,
        anclajes=anclajes,
        hechos_sellados=sellados,
        licencias_declaradas=licencias,
        personalizacion_encomendada=encomendados,
        personalizacion_textos=textos,
    )


def pasada_determinista(capitulo: CapituloEnRevision) -> list[Incidencia]:
    """Coste cero: solo texto contra filas ya escritas. Es la que corre siempre."""
    return [*validar_capitulo(capitulo), *guardrail_prohibidas(capitulo)]


def pasada_del_extractor(
    capitulo: CapituloEnRevision, salida: SalidaExtractorDeCapitulo
) -> list[Incidencia]:
    """Lo que se juzga sobre lo que el extractor midió.

    Los tres **avisan**. `ejecucion_escaleta` y `arco_ejecutado`, porque son el juicio de
    un modelo sobre si algo narrativo ocurrió, y eso no es una puerta; `cobertura_capitulo`,
    porque mide lo que el extractor reconoció y no el texto, y la cobertura que bloquea es
    la de la novela entera, antes de publicar. Abren incidencia de
    severidad `aviso`, entran en el informe del gate y viajan al bloque 1 del capítulo
    siguiente, donde el escritor lee qué quedó pendiente y puede recogerlo.
    """
    usados = frozenset(u.dato_id for u in salida.elementos_usados)
    incidencias = list(cobertura_capitulo(
        CapituloEnRevision(
            numero=capitulo.numero,
            texto=capitulo.texto,
            palabras=capitulo.palabras,
            rango_palabras=capitulo.rango_palabras,
            personalizacion_encomendada=capitulo.personalizacion_encomendada,
            personalizacion_usada=usados,
            personalizacion_textos=capitulo.personalizacion_textos,
        )
    ))

    for beat in salida.veredicto.beats_pendientes:
        incidencias.append(
            Incidencia(
                validador="ejecucion_escaleta",
                severidad=Severidad.AVISO,
                mensaje=f"El beat planificado no llego a ocurrir: {beat}",
                ubicacion=f"capitulo {capitulo.numero}",
            )
        )
    for hito in salida.veredicto.hitos_pendientes:
        incidencias.append(
            Incidencia(
                validador="arco_ejecutado",
                severidad=Severidad.AVISO,
                mensaje=f"El hito de arco #{hito} anclado a este capitulo no ocurrio.",
                ubicacion=f"capitulo {capitulo.numero}",
            )
        )
    return incidencias


def hay_bloqueantes(incidencias: list[Incidencia]) -> bool:
    """El booleano que lee la arista condicional. Calculado en Python, nunca por un modelo."""
    return any(i.bloquea for i in incidencias)


async def rango_de_palabras(db: aiosqlite.Connection) -> tuple[int, int]:
    """El rango del brief, con el margen de §19 alrededor del objetivo."""
    obra = await canon.obra(db)
    objetivo = int(obra["palabras_por_capitulo"]) if obra is not None else 1200
    return int(objetivo * 0.83), int(objetivo * 1.25)


async def capitulo_id_de(db: aiosqlite.Connection, numero: int) -> int | None:
    fila = await plan.capitulo_por_numero(db, numero)
    return int(fila["id"]) if fila is not None else None


async def ultimo_intento(db: aiosqlite.Connection, capitulo_id: int) -> int:
    async with db.execute(
        "SELECT COALESCE(MAX(intento), 0) AS n FROM capitulo_version WHERE capitulo_id = ?",
        (capitulo_id,),
    ) as cursor:
        fila = await cursor.fetchone()
    return int(fila["n"]) if fila is not None else 0


async def texto_de(db: aiosqlite.Connection, capitulo_version_id: int) -> str:
    fila = await texto.resumen_de(db, capitulo_version_id)
    return fila or ""
