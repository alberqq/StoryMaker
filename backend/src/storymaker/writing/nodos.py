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
from storymaker.commons.formal.cronologia import cronologia_de_la_novela, verificar_cronologia
from storymaker.commons.graph.dependencias import actuales
from storymaker.commons.graph.estado import EstadoNovela
from storymaker.commons.obs import scores
from storymaker.commons.obs.prompts import RepositorioDePrompts
from storymaker.commons.obs.trazas import Span, nombre_de_span
from storymaker.commons.validation.modelos import Incidencia
from storymaker.commons.validation.registro import Punto, del_punto
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

    de_rol = RepositorioDePrompts(deps.settings).para(Perfil.ESCRITOR)
    resultado = await invocar_rol(
        Perfil.ESCRITOR,
        paquete.texto(),
        SalidaEscritor,
        transporte=deps.transporte,
        settings=deps.settings,
        sistema=de_rol.texto,
    )
    deps.observador.registrar_span(
        Span(
            nombre=span,
            rol="escritor",
            consumo=resultado.consumo,
            prompt_version=de_rol.version,
            prompt_nombre=de_rol.nombre,
            paquete_id=paquete_id,
        )
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
    capitulo_version_id: int, numero: int, *, retirados: list[list[str]] | None = None
) -> list[Incidencia]:
    """La pasada de coste cero. Corre siempre y **antes** de gastar una llamada.

    Con `retirados` —los pares de un cambio de nombre en regeneración— suma como bloqueante
    cada nombre viejo que el capítulo conserve.
    """
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
    if retirados:
        from storymaker.regeneration import retirados as valor_retirado

        incidencias += valor_retirado.incidencias(
            str(fila["texto"]), [(p[0], p[1]) for p in retirados]
        )
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
        if incidencia.validador == "guardrail_prohibidas":
            # Una decisión del policy engine: además de incidencia, fila de auditoría.
            await arnes.registrar_audit(
                deps.db,
                actor="policy",
                accion="guardrail:prohibida",
                objeto=f"capitulo_version:{capitulo_version_id}",
                despues={
                    "capitulo": numero,
                    "termino": incidencia.ubicacion,
                    "mensaje": incidencia.mensaje,
                },
            )
    # Cada validador de la pasada puntúa, también cuando pasa (ver `registrar_veredicto`).
    for entrada in del_punto(Punto.POST_WRITE_CHAPTER):
        await scores.registrar_veredicto(
            deps.db,
            deps.observador,
            validador=entrada.nombre,
            incidencias=[i for i in incidencias if i.validador == entrada.nombre],
            objeto_tipo="capitulo_version",
            objeto_id=capitulo_version_id,
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

    # Sin catálogo, el extractor adivinaba los identificadores y el volcado moría en una
    # clave foránea con el capítulo ya validado (ER §7.3).
    escaleta = await extraccion.catalogo(deps.db, deps.vectorizador, numero, deps.settings)
    span = nombre_de_span(capitulo=numero, rol="extractor_capitulo", intento=intento)
    de_rol = RepositorioDePrompts(deps.settings).para(Perfil.EXTRACTOR_CAPITULO)
    resultado = await invocar_rol(
        Perfil.EXTRACTOR_CAPITULO,
        f"Capitulo {numero}:\n\n{fila['texto']}\n\n{escaleta.texto}",
        SalidaExtractorDeCapitulo,
        transporte=deps.transporte,
        settings=deps.settings,
        sistema=de_rol.texto,
        contexto={"dominio": escaleta.dominio},
    )
    deps.observador.registrar_span(
        Span(
            nombre=span,
            rol="extractor_capitulo",
            consumo=resultado.consumo,
            prompt_version=de_rol.version,
            prompt_nombre=de_rol.nombre,
        )
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

    # La cronología acumulada, con los eventos que el extractor acaba de escribir. Solo
    # cuenta lo que toca a esta versión: lo aprobado antes ya pasó, y devolver al editor un
    # choque entre dos capítulos aprobados le pediría arreglar lo que no puede tocar.
    marca = f"cap{numero}-v{capitulo_version_id}-"
    novela = await cronologia_de_la_novela(deps.db, con_version=capitulo_version_id)
    cronologia = [
        i
        for i in await verificar_cronologia(
            novela, bloquea=True, validador=CRONOLOGIA_DEL_CAPITULO
        )
        if marca in f"{i.ubicacion or ''} {i.mensaje}{i.propuesta or ''}"
    ]
    await scores.registrar_veredicto(
        deps.db,
        deps.observador,
        validador=CRONOLOGIA_DEL_CAPITULO,
        incidencias=cronologia,
        objeto_tipo="capitulo_version",
        objeto_id=capitulo_version_id,
    )
    incidencias += cronologia

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
) -> int | None:
    """El editor recibe el informe **ya producido** y emite un parche.

    Su único trabajo es corregir: no decide qué validar, no puntúa y no aprueba. Entra como
    `capitulo_version` con `intento+1`, porque nada se sobrescribe.

    **Un parche que no cambia el texto no es un intento.** Devuelve `None`, no escribe
    versión y deja la incidencia `reparacion_sin_cambios` en la que había: validar otra vez
    el mismo texto daría las mismas incidencias, y en la primera novela con gates eso gastó
    los tres intentos de un capítulo en copias idénticas (specs/escritura §2.2).
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
    de_rol = RepositorioDePrompts(deps.settings).para(Perfil.EDITOR)
    resultado = await invocar_rol(
        Perfil.EDITOR,
        f"Capitulo {numero}:\n\n{fila['texto']}\n\nIncidencias a corregir:\n{informe}",
        SalidaEditor,
        transporte=deps.transporte,
        settings=deps.settings,
        sistema=de_rol.texto,
    )
    deps.observador.registrar_span(
        Span(
            nombre=span,
            rol="editor",
            consumo=resultado.consumo,
            prompt_version=de_rol.version,
            prompt_nombre=de_rol.nombre,
        )
    )

    if resultado.valor.texto.strip() == str(fila["texto"]).strip():
        await arnes.registrar_incidencia(
            deps.db,
            capitulo_version_id=capitulo_version_id,
            validador=SIN_CAMBIOS,
            severidad="bloqueante",
            mensaje=(
                "El editor devolvio el capitulo sin cambios: no quedan reintentos que "
                "sirvan. Mira las incidencias de esta version; si el texto ya es correcto, "
                "el que falla es el validador."
            ),
        )
        return None

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


#: La incidencia del parche que devolvió el mismo texto.
SIN_CAMBIOS = "reparacion_sin_cambios"

#: Las incidencias de cronología de la pasada del extractor.
CRONOLOGIA_DEL_CAPITULO = "cronologia_capitulo"


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

    incidencias = await validar_determinista(
        version, estado["capitulo"], retirados=estado.get("retirados")
    )
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
    if nueva is None and version is not None:
        # Sin cambios: se agotan los reintentos y `Validate` lleva a `Fail`, como pide G3,
        # sin pagar más parches sobre el mismo texto. La arista no cambia.
        return {
            **estado,
            "pc": "Validate",
            "intentos": estado["max_intentos"],
            "capitulo_version_id": version,
        }
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

    **En regeneración no se avanza al siguiente, sino al siguiente pendiente.** El que toca
    sale de `a_regenerar`; con la cola vacía se revisan los invalidados con los validadores
    de coste cero, y los que fallan vuelven a la cola. Solo cuando no queda nada se sale
    del modo y `capitulo` queda más allá del último, que es lo que lleva al gate de Writing.
    La revisión va aquí y no en `Invalidate` porque Lean mira la cronología entera, y antes
    de regenerar los afectados la comprobaría contra capítulos a punto de cambiar.
    """
    base: EstadoNovela = {
        **estado,
        "pc": "Checkpoint",
        "intentos": 0,
        "capitulo_version_id": None,
    }
    if not estado.get("regenerando", False):
        return {**base, "capitulo": estado["capitulo"] + 1}

    pendientes = list(estado.get("a_regenerar", []))
    if not pendientes and estado.get("a_invalidar"):
        from storymaker.regeneration.revision import revisar_invalidados

        pendientes = await revisar_invalidados(
            estado["a_invalidar"], retirados=estado.get("retirados")
        )
        base = {**base, "a_invalidar": []}
    if pendientes:
        return {**base, "capitulo": pendientes[0], "a_regenerar": pendientes[1:]}
    return {
        **base,
        "capitulo": estado["n_capitulos"] + 1,
        "a_regenerar": [],
        "regenerando": False,
        "retirados": [],
    }
