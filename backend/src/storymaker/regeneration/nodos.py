"""spec: §4.6 · arq: §4, §9, §11c

Fase 6 · Regeneration. Los nodos `RequestChange`, `Invalidate` y `RegenerateAffected`.

La política es **invalidación barata, regeneración cara**, y existe porque las alternativas
son malas: regenerar solo los que usan el hecho deja incoherencias, y regenerar en cascada
todo lo posterior convierte un cambio de nombre en reescribir media novela.

Los capítulos que **usan** lo que cambió se regeneran. Los **posteriores** pasan a
`Invalidado` y se les corren solo los validadores de coste cero —Python y Lean—; si ninguno
falla, se quedan como están y no cuestan un token. Solo se paga la reescritura de los que
Lean tumbe.

Que Lean viva en la pasada del extractor no rompe esto: un capítulo ya aprobado **tiene sus
filas de `cronologia_evento` escritas desde que se aprobó**, así que verificarlo es generar
el fichero y correr el ejecutable, sin invocar a nadie. El extractor solo hace falta cuando
hay prosa nueva que leer.

**Esta fase es la prueba de fuego del resto del sistema.** Solo funciona si el índice
hecho→capítulo se pobló bien, si los capítulos son inmutables, si el canon es la fuente de
verdad y si Lean puede juzgar la continuidad sin reescribir nada. Si cualquiera de esas
cuatro piezas falla, la regeneración lo destapa.
"""

from __future__ import annotations

import aiosqlite

from storymaker.commons.db.repos import arnes, plan, texto
from storymaker.commons.graph.dependencias import actuales
from storymaker.commons.graph.estado import EstadoNovela
from storymaker.regeneration import cambio
from storymaker.regeneration.esquemas import Alcance, ObjetoDelCambio
from storymaker.writing.nodos import escribir_capitulo


async def calcular_alcance(
    db: aiosqlite.Connection, *, objeto: ObjetoDelCambio, fila_id: int
) -> Alcance:
    """Qué capítulos se regeneran y cuáles solo se revisan.

    Los que usan el hecho salen de `uso_hecho`, que registra a granularidad de escena y se
    agrega a capítulo. Si lo que cambió es un arco, salen de `uso_hito`, su gemelo — sin él,
    mover un hito del capítulo 8 al 5 no invalidaría nada y los avisos de ejecución quedarían
    calculados contra un arco que ya no existe.
    """
    if objeto is ObjetoDelCambio.HECHO:
        afectados = await texto.capitulos_afectados(db, fila_id)
    else:
        afectados = await _capitulos_por_canon(db, objeto, fila_id)

    total = await plan.total_de_capitulos(db)
    if not afectados:
        return Alcance()

    primero = min(afectados)
    posteriores = tuple(
        n for n in range(primero + 1, total + 1) if n not in afectados
    )
    return Alcance(a_regenerar=tuple(sorted(afectados)), a_invalidar=posteriores)


async def _capitulos_por_canon(
    db: aiosqlite.Connection, objeto: ObjetoDelCambio, fila_id: int
) -> list[int]:
    """Qué capítulos tocan una ficha del canon: los que la **usan**, según las tablas.

    Un personaje se usa en todo capítulo donde aparece, no solo donde ejecuta un hito de su
    arco: cambiarle el nombre y regenerar solo los de sus hitos dejaba el nombre viejo en el
    resto. Aparecer lo dicen dos tablas —`continuidad`, que escribe el extractor del texto
    aprobado, y `plan_escena_personaje`, la escaleta— más `uso_hito` para el arco.
    """
    if objeto is not ObjetoDelCambio.PERSONAJE:
        return []
    async with db.execute(
        """
        SELECT pc.numero
          FROM continuidad c
          JOIN capitulo_version cv ON cv.id = c.capitulo_version_id
          JOIN plan_capitulo pc ON pc.id = cv.capitulo_id
         WHERE c.personaje_id = ? AND cv.estado = 'aprobado'
        UNION
        SELECT pc.numero
          FROM plan_escena_personaje ep
          JOIN plan_escena e ON e.id = ep.escena_id
          JOIN plan_capitulo pc ON pc.id = e.capitulo_id
         WHERE ep.personaje_id = ?
        UNION
        SELECT pc.numero
          FROM uso_hito uh
          JOIN canon_arco_hito h ON h.id = uh.hito_id
          JOIN canon_arco a ON a.id = h.arco_id
          JOIN capitulo_version cv ON cv.id = uh.capitulo_version_id
          JOIN plan_capitulo pc ON pc.id = cv.capitulo_id
         WHERE a.personaje_id = ? AND cv.estado = 'aprobado'
         ORDER BY 1
        """,
        (fila_id, fila_id, fila_id),
    ) as cursor:
        return [int(f[0]) for f in await cursor.fetchall()]


async def invalidar(db: aiosqlite.Connection, capitulos: tuple[int, ...]) -> list[int]:
    """Marca los posteriores como `Invalidado`. Devuelve las versiones tocadas.

    No los reescribe: los deja a la espera de los validadores de coste cero. Si ninguno
    falla, vuelven a su sitio sin haber costado un token.
    """
    versiones = []
    for numero in capitulos:
        capitulo = await plan.capitulo_por_numero(db, numero)
        if capitulo is None:
            continue
        aprobado = await texto.capitulo_aprobado(db, int(capitulo["id"]))
        if aprobado is not None:
            versiones.append(int(aprobado["id"]))
    await texto.invalidar_capitulos(db, versiones)
    return versiones


# --- Los nodos del grafo -------------------------------------------------------------


async def peticion_aprobada(db: aiosqlite.Connection) -> str:
    """La petición tal como el Autor la dejó al cerrar el gate de la Fase 6.

    El comentario del gate es el canal: el endpoint solo deja la petición pendiente y los
    candidatos a la vista, y nada se toca hasta que el Autor aprueba. Leerla aquí y no
    llevarla en el estado es deliberado — el estado del grafo es de punteros, y el texto de
    la petición ya tiene su fila.
    """
    async with db.execute(
        """
        SELECT g.comentario
          FROM gate g
          JOIN fase_run f ON f.id = g.fase_run_id
         WHERE f.fase = 'regeneration' AND g.comentario IS NOT NULL
         ORDER BY g.id DESC LIMIT 1
        """
    ) as cursor:
        fila = await cursor.fetchone()
    return str(fila["comentario"]) if fila is not None else ""


async def request(estado: EstadoNovela) -> EstadoNovela:
    """`RequestChange`. Resuelve la petición y **modifica la fila, no el texto**.

    Aquí se decide el coste de toda la fase: `calcular_alcance` parte los capítulos en los
    que se regeneran y los que solo se revisan, y ese reparto viaja en el estado porque los
    dos nodos siguientes lo consumen. Una petición que no se resuelve a ninguna fila deja el
    alcance vacío y la fase pasa de largo sin escribir nada.
    """
    deps = actuales()
    peticion = await peticion_aprobada(deps.db)
    resuelto = await cambio.resolver(deps.db, deps.vectorizador, peticion) if peticion else None

    if resuelto is None:
        return {
            **estado,
            "pc": "Invalidate",
            "regenerando": True,
            "a_regenerar": [],
            "a_invalidar": [],
        }

    await cambio.aplicar(
        deps.db, deps.vectorizador, resuelto, actor="autor", fase_run_id=estado["fase_run_id"]
    )
    alcance = await calcular_alcance(deps.db, objeto=resuelto.objeto, fila_id=resuelto.fila_id)
    return {
        **estado,
        "pc": "Invalidate",
        "regenerando": True,
        "a_regenerar": list(alcance.a_regenerar),
        "a_invalidar": list(alcance.a_invalidar),
    }


async def invalidate(estado: EstadoNovela) -> EstadoNovela:
    """`Invalidate`. Marca los posteriores; el coste cero decide si se reescriben.

    No cuesta un token: los capítulos afectados quedan en `Invalidado` a la espera de los
    validadores de Python y de Lean, que pueden juzgarlos sin releer la prosa porque sus
    filas de `cronologia_evento` están escritas desde que se aprobaron.
    """
    deps = actuales()
    versiones = await invalidar(deps.db, tuple(estado["a_invalidar"]))
    if versiones:
        await arnes.registrar_audit(
            deps.db,
            actor="arnes",
            accion="invalidar",
            objeto=f"capitulos:{','.join(str(n) for n in estado['a_invalidar'])}",
            antes={"estado": "aprobado"},
            despues={"estado": "invalidado"},
        )
    return {**estado, "pc": "RegenerateAffected"}


async def regenerate(estado: EstadoNovela) -> EstadoNovela:
    """`RegenerateAffected`. Vuelve a `Validate` por el mismo camino que un capítulo nuevo.

    Que la arista lleve a `Validate` y no a un bucle propio es lo que hace que la Fase 6 no
    tenga su propia maquinaria de validación: un capítulo regenerado pasa exactamente por
    donde pasó el original, con el mismo tope de reintentos y el mismo extractor.

    Se reescribe **de uno en uno**, dejando el resto en la lista: el capítulo vuelve al bucle
    de Writing y, cuando lo aprueben, `Checkpoint` encontrará aquí los que falten.
    """
    pendientes = list(estado["a_regenerar"])
    if not pendientes:
        return {**estado, "pc": "Validate", "intentos": 0}

    numero = pendientes.pop(0)
    version = await escribir_capitulo(numero, fase_run_id=estado["fase_run_id"], intento=1)
    return {
        **estado,
        "pc": "Validate",
        "capitulo": numero,
        "capitulo_version_id": version,
        "intentos": 0,
        "a_regenerar": pendientes,
    }
