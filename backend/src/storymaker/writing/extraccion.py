"""spec: §4.4 · arq: §4, §7

Vuelca lo que el extractor midió: los índices, la continuidad y la cronología narrativa.

**Todas estas filas cuelgan del intento, no del capítulo.** `uso_hecho`, `uso_hito`,
`intake_uso_dato` y `continuidad` se escriben con el `capitulo_version_id` del intento que
las produjo, así que las de un intento descartado quedan colgando de una versión que nunca
se aprueba y que ningún manifiesto recoge. No hace falta marcarlas ni borrarlas: la
inmutabilidad ya las deja fuera.

`uso_hecho` registra a granularidad de **escena**; la consulta de regeneración lo agrega a
capítulo, que es la unidad de reescritura. `uso_hito` es su gemelo para el arco, y existe
por la misma razón: sin él, mover un hito del capítulo 8 al 5 no invalidaría nada.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import aiosqlite

from storymaker.commons.config import Settings
from storymaker.commons.context.bloques import consulta_semantica
from storymaker.commons.db.repos import id_insertado, intake, mundo, plan, texto
from storymaker.commons.embeddings import indice
from storymaker.commons.embeddings.modelo import Vectorizador
from storymaker.writing.esquemas import Dominio, SalidaExtractorDeCapitulo

#: Lo que ocupa como mucho la etiqueta de cada entrada del catálogo. El catálogo es para
#: reconocer, no para leer: el texto completo de un hecho ya lo tuvo el escritor.
_ETIQUETA = 140


@dataclass(frozen=True)
class Catalogo:
    """La escaleta del capítulo y los identificadores que el extractor puede devolver."""

    texto: str
    dominio: Dominio


def _corta(valor: object) -> str:
    texto_plano = " ".join(str(valor or "").split())
    return texto_plano if len(texto_plano) <= _ETIQUETA else texto_plano[: _ETIQUETA - 1] + "…"


async def catalogo(
    db: aiosqlite.Connection, vectorizador: Vectorizador, numero: int, settings: Settings
) -> Catalogo:
    """Lo que el extractor tiene que tener delante para medir sin adivinar (ER §7.3).

    Los hechos son **los que el escritor vio**: los anclados más los vecinos del bloque 5,
    con la misma consulta. Personajes, escenarios y elementos del encargo van enteros, porque
    son pocos y porque la continuidad y la cobertura no se limitan a lo que la escena nombra.
    """
    lineas = [f"Escaleta del capitulo {numero}:"]
    for escena in await plan.escenas_de(db, numero):
        lineas.append(
            f"Escena {escena['orden']}: {_corta(escena['objetivo'])}"
            f" | conflicto: {_corta(escena['conflicto'])}"
        )
        for beat in await plan.beats_de(db, int(escena["id"])):
            lineas.append(f"  - beat: {_corta(beat['accion'])}")

    async with db.execute("SELECT id, nombre FROM canon_personaje ORDER BY id") as cursor:
        personajes = {int(f["id"]): str(f["nombre"]) for f in await cursor.fetchall()}
    async with db.execute("SELECT id, descripcion FROM canon_escenario ORDER BY id") as cursor:
        escenarios = {int(f["id"]): _corta(f["descripcion"]) for f in await cursor.fetchall()}

    hechos: dict[int, str] = {}
    for anclaje in await plan.anclajes_de(db, numero):
        if anclaje["hecho_id"] is not None:
            hechos[int(anclaje["hecho_id"])] = _corta(anclaje["hecho_enunciado"])
    consulta = await consulta_semantica(db, numero)
    if consulta:
        for vecino in await indice.buscar_hechos(db, vectorizador, consulta, k=settings.k_vecinos):
            if vecino.id in hechos:
                continue
            fila = await mundo.hecho_por_id(db, vecino.id)
            if fila is not None:
                hechos[vecino.id] = _corta(fila["enunciado"])

    datos = {int(d["id"]): _corta(d["valor_json"]) for d in await intake.datos(db)}
    hitos = {
        int(h["id"]): f"{_corta(h['descripcion'])} (escena {h['escena_orden']})"
        for h in await plan.hitos_de(db, numero)
    }

    lineas.append("")
    lineas.append(
        "Catalogo de identificadores. Usa SOLO estos numeros en los campos *_id, "
        "participantes e hitos; si algo no esta aqui, no lo declares."
    )
    # Sin esta regla, el extractor contaba como participante a quien solo se recuerda, y
    # un abuelo muerto en 1790 «participaba» en 1805: la cronología bloqueaba un capítulo
    # correcto y ningún parche podía arreglarlo sin quitar un elemento obligatorio.
    lineas.append(
        "En `participantes` van solo los personajes presentes en el evento, en ese momento. "
        "Quien solo se recuerda, se nombra, se sueña o ya ha muerto no participa: no lo "
        "pongas."
    )
    for titulo, entradas in (
        ("Personajes (personaje_id, participantes)", personajes),
        ("Escenarios (escenario_id)", escenarios),
        ("Hechos del corpus que el escritor tuvo delante (hecho_id)", hechos),
        ("Elementos del encargo (dato_id)", datos),
        ("Hitos de arco de este capitulo (hitos_ejecutados, hitos_pendientes)", hitos),
    ):
        lineas.append(f"{titulo}:")
        lineas.extend(f"  #{clave} {etiqueta}" for clave, etiqueta in entradas.items())
        if not entradas:
            lineas.append("  (ninguno)")

    return Catalogo(
        texto="\n".join(lineas),
        dominio=Dominio(
            personajes=frozenset(personajes),
            escenarios=frozenset(escenarios),
            hechos=frozenset(hechos),
            datos=frozenset(datos),
            hitos=frozenset(hitos),
        ),
    )


async def _escenas_por_orden(db: aiosqlite.Connection, numero: int) -> dict[int, int]:
    """Orden dentro del capítulo → identificador. El extractor habla de escenas por orden."""
    return {int(e["orden"]): int(e["id"]) for e in await plan.escenas_de(db, numero)}


async def volcar(
    db: aiosqlite.Connection,
    salida: SalidaExtractorDeCapitulo,
    *,
    capitulo_version_id: int,
    numero: int,
) -> None:
    """Escribe todo lo que el extractor midió, con el intento como dueño."""
    escenas = await _escenas_por_orden(db, numero)

    for uso in salida.hechos_usados:
        escena_id = escenas.get(uso.escena)
        if escena_id is None:
            continue
        await texto.registrar_uso_hecho(
            db,
            capitulo_version_id=capitulo_version_id,
            escena_id=escena_id,
            hecho_id=uso.hecho_id,
            tipo_uso=uso.tipo_uso,
        )

    for elemento in salida.elementos_usados:
        escena_id = escenas.get(elemento.escena)
        if escena_id is None:
            continue
        await intake.registrar_uso(
            db,
            capitulo_version_id=capitulo_version_id,
            escena_id=escena_id,
            dato_id=elemento.dato_id,
        )

    for hito in salida.veredicto.hitos_ejecutados:
        escena_id = await _escena_del_hito(db, hito)
        if escena_id is not None:
            await texto.registrar_uso_hito(
                db,
                capitulo_version_id=capitulo_version_id,
                escena_id=escena_id,
                hito_id=hito,
                ejecutado=True,
            )
    for hito in salida.veredicto.hitos_pendientes:
        escena_id = await _escena_del_hito(db, hito)
        if escena_id is not None:
            await texto.registrar_uso_hito(
                db,
                capitulo_version_id=capitulo_version_id,
                escena_id=escena_id,
                hito_id=hito,
                ejecutado=False,
            )

    for estado in salida.continuidad:
        await texto.insertar_continuidad(
            db,
            capitulo_version_id=capitulo_version_id,
            personaje_id=estado.personaje_id,
            escenario_id=estado.escenario_id,
            fecha_narrativa=estado.fecha_narrativa or None,
            conocimiento_json=json.dumps(estado.conocimiento, ensure_ascii=False),
            posesiones_json=json.dumps(estado.posesiones, ensure_ascii=False),
            estado_json=json.dumps(estado.estado, ensure_ascii=False),
        )

    await volcar_cronologia(db, salida, capitulo_version_id=capitulo_version_id, numero=numero)


async def _escena_del_hito(db: aiosqlite.Connection, hito_id: int) -> int | None:
    async with db.execute(
        "SELECT escena_id FROM canon_arco_hito WHERE id = ?", (hito_id,)
    ) as cursor:
        fila = await cursor.fetchone()
    return int(fila["escena_id"]) if fila is not None and fila["escena_id"] is not None else None


async def volcar_cronologia(
    db: aiosqlite.Connection,
    salida: SalidaExtractorDeCapitulo,
    *,
    capitulo_version_id: int,
    numero: int,
) -> list[int]:
    """Las filas `narrativo` de la cronología. **Nadie más sabe qué ocurrió en esa prosa.**

    Es la razón entera de que Lean corra en la pasada del extractor: antes de esta escritura,
    la cronología del capítulo N no existe, y verificarla sería verificar hasta N-1.
    """
    escenas = await _escenas_por_orden(db, numero)
    identificadores = []

    for evento in salida.eventos:
        cursor = await db.execute(
            """
            INSERT OR IGNORE INTO cronologia_evento
                (clave, descripcion, momento, origen, capitulo_version_id)
            VALUES (?, ?, ?, 'narrativo', ?)
            """,
            (
                f"cap{numero}-v{capitulo_version_id}-{evento.clave}",
                evento.descripcion,
                evento.momento,
                capitulo_version_id,
            ),
        )
        # La clave lleva la versión: cada intento escribe sus eventos, y un evento que el
        # editor corrigió no se queda con la fila del intento anterior. Si aun así el
        # INSERT se ignora —el extractor repitió una clave—, `lastrowid` no vuelve a
        # cero: conserva el último id insertado en la conexión, sea de la tabla que sea,
        # y los participantes colgarían de un evento que no existe. Lo que dice si hubo
        # fila es `rowcount`.
        if cursor.rowcount == 0 or not cursor.lastrowid:
            continue
        evento_id = cursor.lastrowid
        identificadores.append(int(evento_id))
        for personaje_id in evento.participantes:
            await db.execute(
                """
                INSERT OR IGNORE INTO cronologia_participante (evento_id, personaje_id)
                VALUES (?, ?)
                """,
                (evento_id, personaje_id),
            )
        # La escena queda implícita en la clave; no se guarda columna propia porque el
        # modelo de §7 no la tiene y añadirla por comodidad sería cambiar el esquema desde
        # abajo, que es justo lo que este proyecto no hace.
        _ = escenas
    return identificadores


async def guardar_resumen(
    db: aiosqlite.Connection, capitulo_version_id: int, resumen: str
) -> None:
    """El resumen es lo único del extractor que se escribe **en la fila del capítulo**.

    Y es el único `UPDATE` que el *trigger* de inmutabilidad permite sobre columnas que no
    son el estado, porque el resumen no es contenido generado por el escritor: lo mide otro
    agente después, y sin él el bloque 4 del paquete no tendría qué indexar.
    """
    await db.execute(
        "UPDATE capitulo_version SET resumen = ? WHERE id = ?", (resumen, capitulo_version_id)
    )


async def contar_filas_del_intento(db: aiosqlite.Connection, capitulo_version_id: int) -> int:
    """Cuántas filas dejó un intento. Sirve para comprobar que las descartadas quedan fuera."""
    total = 0
    for tabla in ("uso_hecho", "uso_hito", "intake_uso_dato", "continuidad"):
        async with db.execute(
            f"SELECT COUNT(*) AS n FROM {tabla} WHERE capitulo_version_id = ?",  # noqa: S608
            (capitulo_version_id,),
        ) as cursor:
            fila = await cursor.fetchone()
        total += int(fila["n"]) if fila is not None else 0
    return total


async def id_insertado_de(cursor: aiosqlite.Cursor) -> int:
    return id_insertado(cursor)
