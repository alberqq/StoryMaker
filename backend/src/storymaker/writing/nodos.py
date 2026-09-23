"""spec: §4.4 · arq: §4, §9

Fase 4 · Writing. El bucle por capítulo, que es la unidad de generación, validación,
checkpoint y regeneración.

El recorrido es siempre el mismo: el ensamblador monta el paquete, el escritor redacta el
capítulo entero de una vez, `Validate` corre en dos pasadas —determinista primero, extractor
después y solo si la primera queda limpia—, y si hay incidencias bloqueantes el editor
recibe **el informe ya producido** y emite un parche. Dos reintentos, y después `Fail`.

**El editor no decide cuándo validar.** Recibe el informe hecho, y su único trabajo es
emitir el parche. Con eso, las transiciones del grafo dependen de valores calculados en
Python y no de la salida de un modelo — que es exactamente lo que TLC puede verificar.

**El extractor corre antes de aprobar y no después**, y eso es lo que hace que sirva: un
veredicto emitido tras `ApproveChapter` no tendría adónde ir, porque no hay arista de vuelta
desde `Checkpoint` a `Repair`.
"""

from __future__ import annotations

from storymaker.commons.agents.invocacion import invocar_rol
from storymaker.commons.agents.techos import Perfil
from storymaker.commons.context.ensamblador import ensamblar, persistir
from storymaker.commons.db.repos import arnes, texto
from storymaker.commons.embeddings import indice
from storymaker.commons.graph.dependencias import actuales
from storymaker.commons.graph.estado import EstadoNovela
from storymaker.commons.obs.prompts import RepositorioDePrompts
from storymaker.commons.obs.trazas import Span, nombre_de_span
from storymaker.commons.validation.modelos import Incidencia
from storymaker.writing import extraccion, similitud, validacion
from storymaker.writing.esquemas import (
    SalidaEditor,
    SalidaEscritor,
    SalidaExtractorDeCapitulo,
)


async def escribir_capitulo(numero: int, *, fase_run_id: int, intento: int = 1) -> int:
    """Monta el paquete, invoca al escritor y guarda el intento. Devuelve su identificador.

    El paquete se persiste **antes** de invocar y se enlaza al span: poder abrir literalmente
    lo que el modelo vio cuando escribió el capítulo 7 es la definición operativa de
    interpretable en este sistema, y si se guardara después, un fallo de la llamada dejaría
    sin rastro justo el caso que más interesa mirar.
    """
    deps = actuales()
    paquete = await ensamblar(deps.db, deps.vectorizador, numero, settings=deps.settings)
    span = nombre_de_span(capitulo=numero, rol="escritor", intento=intento)
    paquete_id = await persistir(deps.db, paquete, intento=intento, trace_span=span)

    resultado = await invocar_rol(
        Perfil.ESCRITOR,
        paquete.texto(),
        SalidaEscritor,
        transporte=deps.transporte,
        settings=deps.settings,
        sistema=RepositorioDePrompts(deps.settings).para(Perfil.ESCRITOR).texto,
    )
    deps.observador.registrar_span(
        Span(nombre=span, rol="escritor", consumo=resultado.consumo, paquete_id=paquete_id)
    )

    capitulo_id = await validacion.capitulo_id_de(deps.db, numero)
    if capitulo_id is None:
        raise ValueError(f"La escaleta no contempla el capitulo {numero}")

    return await texto.insertar_capitulo_version(
        deps.db,
        capitulo_id=capitulo_id,
        fase_run_id=fase_run_id,
        texto=resultado.valor.texto,
        intento=intento,
    )


async def validar_determinista(
    capitulo_version_id: int, numero: int
) -> list[Incidencia]:
    """La pasada de coste cero. Corre siempre y **antes** de gastar una llamada."""
    deps = actuales()
    async with deps.db.execute(
        "SELECT texto, palabras FROM capitulo_version WHERE id = ?", (capitulo_version_id,)
    ) as cursor:
        fila = await cursor.fetchone()
    if fila is None:
        return []

    revision = await validacion.construir_revision(
        deps.db,
        numero=numero,
        texto_capitulo=str(fila["texto"]),
        palabras=int(fila["palabras"]),
        rango_palabras=await validacion.rango_de_palabras(deps.db),
    )
    incidencias = validacion.pasada_determinista(revision)
    for incidencia in incidencias:
        await arnes.registrar_incidencia(
            deps.db,
            capitulo_version_id=capitulo_version_id,
            validador=incidencia.validador,
            severidad=str(incidencia.severidad),
            mensaje=incidencia.mensaje,
            ubicacion=incidencia.ubicacion,
            propuesta=incidencia.propuesta,
        )
    return incidencias


async def extraer(capitulo_version_id: int, numero: int, *, intento: int = 1) -> list[Incidencia]:
    """La pasada del extractor: una llamada, y solo si la anterior quedó limpia.

    Escribe además las filas narrativas de la cronología, que es lo que permite que Lean
    verifique **este** capítulo y no el anterior.
    """
    deps = actuales()
    async with deps.db.execute(
        "SELECT texto FROM capitulo_version WHERE id = ?", (capitulo_version_id,)
    ) as cursor:
        fila = await cursor.fetchone()
    if fila is None:
        return []

    span = nombre_de_span(capitulo=numero, rol="extractor_capitulo", intento=intento)
    resultado = await invocar_rol(
        Perfil.EXTRACTOR_CAPITULO,
        f"Capitulo {numero}:\n\n{fila['texto']}",
        SalidaExtractorDeCapitulo,
        transporte=deps.transporte,
        settings=deps.settings,
        sistema=RepositorioDePrompts(deps.settings).para(Perfil.EXTRACTOR_CAPITULO).texto,
    )
    deps.observador.registrar_span(
        Span(nombre=span, rol="extractor_capitulo", consumo=resultado.consumo)
    )

    salida = resultado.valor
    await extraccion.volcar(
        deps.db, salida, capitulo_version_id=capitulo_version_id, numero=numero
    )
    await extraccion.guardar_resumen(deps.db, capitulo_version_id, salida.resumen)

    revision = await validacion.construir_revision(
        deps.db,
        numero=numero,
        texto_capitulo=str(fila["texto"]),
        palabras=len(str(fila["texto"]).split()),
        rango_palabras=await validacion.rango_de_palabras(deps.db),
    )
    incidencias = validacion.pasada_del_extractor(revision, salida)

    parecidos = await similitud.buscar_repeticion(
        deps.db, deps.vectorizador, resumen=salida.resumen, capitulo_numero=numero
    )
    incidencias += similitud.como_incidencias(parecidos, numero)

    for incidencia in incidencias:
        await arnes.registrar_incidencia(
            deps.db,
            capitulo_version_id=capitulo_version_id,
            validador=incidencia.validador,
            severidad=str(incidencia.severidad),
            mensaje=incidencia.mensaje,
            ubicacion=incidencia.ubicacion,
        )
    return incidencias


async def reparar(
    capitulo_version_id: int, numero: int, *, fase_run_id: int, intento: int
) -> int:
    """El editor recibe el informe **ya producido** y emite un parche.

    Su único trabajo es corregir: no decide qué validar, no puntúa y no aprueba. Entra como
    `capitulo_version` con `intento+1`, porque nada se sobrescribe.
    """
    deps = actuales()
    async with deps.db.execute(
        "SELECT texto, capitulo_id FROM capitulo_version WHERE id = ?", (capitulo_version_id,)
    ) as cursor:
        fila = await cursor.fetchone()
    if fila is None:
        raise ValueError(f"No existe la version {capitulo_version_id}")

    incidencias = await arnes.incidencias_de(db=deps.db, capitulo_version_id=capitulo_version_id)
    informe = "\n".join(
        f"- [{i['severidad']}] {i['validador']}: {i['mensaje']}" for i in incidencias
    )
    span = nombre_de_span(capitulo=numero, rol="editor", intento=intento)
    resultado = await invocar_rol(
        Perfil.EDITOR,
        f"Capitulo {numero}:\n\n{fila['texto']}\n\nIncidencias a corregir:\n{informe}",
        SalidaEditor,
        transporte=deps.transporte,
        settings=deps.settings,
        sistema=RepositorioDePrompts(deps.settings).para(Perfil.EDITOR).texto,
    )
    deps.observador.registrar_span(Span(nombre=span, rol="editor", consumo=resultado.consumo))

    return await texto.insertar_capitulo_version(
        deps.db,
        capitulo_id=int(fila["capitulo_id"]),
        fase_run_id=fase_run_id,
        texto=resultado.valor.texto,
        intento=intento,
    )


async def aprobar(capitulo_version_id: int, numero: int) -> None:
    """Marca el estado e indexa el resumen como vigente, en la misma operación.

    El `vigente` importa más de lo que parece: sin él, el escritor del capítulo 7 podría
    recibir el resumen de un intento rechazado del 3 — un fallo silencioso, porque el
    capítulo saldría bien escrito recordando algo que ya no está en la novela.
    """
    deps = actuales()
    await texto.aprobar_capitulo(deps.db, capitulo_version_id)

    resumen = await texto.resumen_de(deps.db, capitulo_version_id)
    if resumen:
        await indice.indexar_resumen(
            deps.db,
            deps.vectorizador,
            capitulo_version_id=capitulo_version_id,
            resumen=resumen,
            capitulo_numero=numero,
        )
        await indice.marcar_vigente(
            deps.db, capitulo_version_id=capitulo_version_id, capitulo_numero=numero
        )


# --- Los nodos del grafo -------------------------------------------------------------


async def write(estado: EstadoNovela) -> EstadoNovela:
    """`WriteChapter`. El escritor redacta de una sola vez."""
    version = await escribir_capitulo(
        estado["capitulo"],
        fase_run_id=estado["fase_run_id"],
        intento=estado["intentos"] + 1,
    )
    return {
        **estado,
        "pc": "Validate",
        "capitulo_version_id": version,
        "hay_bloqueantes": False,
    }


async def validate(estado: EstadoNovela) -> EstadoNovela:
    """`Validate`, pasada determinista. Deja el booleano que lee la arista.

    El booleano se calcula aquí, contando incidencias en una lista, y es lo único que la
    arista mira. Ninguna transición de este grafo depende de lo que diga un modelo.
    """
    version = estado["capitulo_version_id"]
    if version is None:
        return {**estado, "pc": "Validate", "hay_bloqueantes": True}

    incidencias = await validar_determinista(version, estado["capitulo"])
    return {
        **estado,
        "pc": "Validate",
        "hay_bloqueantes": validacion.hay_bloqueantes(incidencias),
    }


async def extract(estado: EstadoNovela) -> EstadoNovela:
    """`Extract`. Una llamada por intento que supere la pasada anterior."""
    version = estado["capitulo_version_id"]
    if version is None:
        return {**estado, "pc": "Extract", "hay_bloqueantes": True}

    incidencias = await extraer(version, estado["capitulo"], intento=estado["intentos"] + 1)
    return {
        **estado,
        "pc": "Extract",
        "hay_bloqueantes": validacion.hay_bloqueantes(incidencias),
    }


async def repair(estado: EstadoNovela) -> EstadoNovela:
    """`Repair`. Consume un reintento; el contador es único para sus dos aristas de entrada."""
    version = estado["capitulo_version_id"]
    intento = estado["intentos"] + 2
    nueva = version
    if version is not None:
        nueva = await reparar(
            version, estado["capitulo"], fase_run_id=estado["fase_run_id"], intento=intento
        )
    return {
        **estado,
        "pc": "Validate",
        "intentos": estado["intentos"] + 1,
        "capitulo_version_id": nueva,
    }


async def approve(estado: EstadoNovela) -> EstadoNovela:
    """`ApproveChapter`. Marca el estado del capítulo e indexa su resumen como vigente."""
    version = estado["capitulo_version_id"]
    if version is not None:
        await aprobar(version, estado["capitulo"])
    aprobados = [*estado["aprobados"], estado["capitulo"]]
    validados = [*estado["validados"], estado["capitulo"]]
    return {**estado, "pc": "Checkpoint", "aprobados": aprobados, "validados": validados}


async def checkpoint(estado: EstadoNovela) -> EstadoNovela:
    """`Checkpoint`. Avanza al capítulo siguiente y reinicia el contador de intentos.

    El checkpoint de LangGraph y la escritura de dominio ocurren en la misma transacción, y
    de eso se encarga el envoltorio de invocación: el nodo no hace `commit` por su cuenta.
    """
    siguiente = estado["capitulo"] + 1
    return {
        **estado,
        "pc": "Checkpoint",
        "capitulo": siguiente,
        "intentos": 0,
        "capitulo_version_id": None,
    }
