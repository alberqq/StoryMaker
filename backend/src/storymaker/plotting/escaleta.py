"""spec: §4.3 · arq: §4, §7

Vuelca la escaleta: capítulos, escenas, beats, quién está en cada escena y a qué se ancla.

La escena es la **unidad de planificación y de traza**; el capítulo, la de redacción. Esa
separación es la que permite que el escritor redacte el capítulo entero de una vez —coser
escenas generadas por separado es la forma más fiable de producir prosa mecánica— sin
perder la granularidad que necesitan `uso_hecho`, `uso_hito` y la cronología.

Aquí está también lo que hace posible detectar una cronología imposible **antes de redactar
una línea**: cada escena lleva su `fecha_narrativa` y sus personajes, así que un personaje
en dos sitios el mismo día, o vivo tres años después de su muerte documentada, es visible
en el gate de Plotting, donde corregirlo cuesta un párrafo.
"""

from __future__ import annotations

import re

import aiosqlite

from storymaker.commons.db.repos import id_insertado
from storymaker.commons.validation.puras import normalizar
from storymaker.plotting.esquemas import SalidaArquitecto

_CLAVE = re.compile(r"#\s*(\d+)")


def mapa_de_claves(filas: dict[int, str]) -> dict[str, int]:
    """Identificador → texto, convertido en todo lo que el arquitecto puede escribir.

    El contexto le enseña cada hecho y cada elemento como `#id`, y así es como se le pide
    que ancle (ER §7.2). Se acepta también el texto, normalizado, porque un anclaje que
    copia el enunciado en vez de la clave apunta a lo mismo y descartarlo sería castigar la
    forma y no el contenido.
    """
    mapa: dict[str, int] = {}
    for identificador, texto_fila in filas.items():
        mapa[f"#{identificador}"] = identificador
        mapa[str(identificador)] = identificador
        if texto_fila:
            mapa[normalizar(texto_fila)] = identificador
    return mapa


def resolver_clave(mapa: dict[str, int], propuesta: str | None) -> int | None:
    """La clave que escribió el arquitecto, o `None` si no apunta a nada conocido."""
    if not propuesta:
        return None
    if (marca := _CLAVE.search(propuesta)) is not None:
        return mapa.get(f"#{marca.group(1)}")
    limpia = propuesta.strip()
    return mapa.get(limpia) if limpia in mapa else mapa.get(normalizar(limpia))


async def volcar_escaleta(
    db: aiosqlite.Connection,
    salida: SalidaArquitecto,
    *,
    personajes: dict[str, int],
    hechos: dict[str, int] | None = None,
    datos: dict[str, int] | None = None,
    sin_resolver: list[str] | None = None,
) -> dict[str, int]:
    """Escribe la escaleta entera. Devuelve clave de escena → identificador.

    Ese diccionario es lo que después permite anclar los hitos de arco a sus escenas, y por
    eso se devuelve en lugar de quedarse dentro: el arquitecto nombra las escenas con claves
    y la base con identificadores, y alguien tiene que traducir.

    Los anclajes que no apuntan a nada conocido se añaden a `sin_resolver`, para que el
    gate de Plotting los enseñe en lugar de perderlos en silencio.
    """
    hechos = hechos or {}
    datos = datos or {}
    escenas_por_clave: dict[str, int] = {}

    for capitulo in sorted(salida.capitulos, key=lambda c: c.numero):
        cursor = await db.execute(
            "INSERT INTO plan_capitulo (numero, titulo, funcion, gancho) VALUES (?, ?, ?, ?)",
            (capitulo.numero, capitulo.titulo, capitulo.funcion, capitulo.gancho),
        )
        capitulo_id = id_insertado(cursor)

        for escena in sorted(capitulo.escenas, key=lambda e: e.orden):
            cursor = await db.execute(
                """
                INSERT INTO plan_escena
                    (capitulo_id, orden, escenario_id, fecha_narrativa, pdv_personaje_id,
                     objetivo, conflicto, resultado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    capitulo_id,
                    escena.orden,
                    personajes.get(f"escenario:{escena.escenario}"),
                    escena.fecha_narrativa or None,
                    personajes.get(escena.pdv),
                    escena.objetivo,
                    escena.conflicto,
                    escena.resultado,
                ),
            )
            escena_id = id_insertado(cursor)
            escenas_por_clave[escena.clave] = escena_id

            for beat in sorted(escena.beats, key=lambda b: b.orden):
                await db.execute(
                    """
                    INSERT INTO plan_beat (escena_id, orden, accion, cambio_de_valor)
                    VALUES (?, ?, ?, ?)
                    """,
                    (escena_id, beat.orden, beat.accion, beat.cambio_de_valor),
                )

            for nombre in escena.personajes:
                personaje_id = personajes.get(nombre)
                if personaje_id is not None:
                    await db.execute(
                        """
                        INSERT OR IGNORE INTO plan_escena_personaje (escena_id, personaje_id)
                        VALUES (?, ?)
                        """,
                        (escena_id, personaje_id),
                    )

            for anclaje in escena.anclajes:
                hecho_id = resolver_clave(hechos, anclaje.hecho)
                dato_id = None if hecho_id is not None else resolver_clave(datos, anclaje.dato)
                if hecho_id is None and dato_id is None:
                    if sin_resolver is not None and (anclaje.hecho or anclaje.dato):
                        sin_resolver.append(
                            f"escena {escena.clave}: {anclaje.hecho or anclaje.dato}"
                        )
                    # Un anclaje que no apunta a nada no se escribe: el `CHECK` exige
                    # exactamente uno de los tres, y escribirlo abortaría la transacción
                    # entera por un despiste del modelo.
                    continue
                await db.execute(
                    """
                    INSERT INTO plan_anclaje (escena_id, hecho_id, dato_id, tipo_vinculo)
                    VALUES (?, ?, ?, ?)
                    """,
                    (escena_id, hecho_id, dato_id, anclaje.tipo_vinculo),
                )

    return escenas_por_clave
