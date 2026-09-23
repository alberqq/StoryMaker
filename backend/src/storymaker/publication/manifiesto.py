"""spec: §4.5 · arq: §13, §16.2

El manifiesto: **lo que hace auditable una versión publicada**.

El sistema promete dos cosas y no promete una tercera. Promete **auditabilidad**: cada
versión lleva el hash del brief, el del corpus sellado, la versión de cada prompt, el id
exacto de cada modelo, el modelo de embeddings con su dimensión y la versión del SDK, de
modo que cualquier resultado se puede explicar hacia atrás. Promete **estabilidad métrica**.
Y **no promete el mismo texto**: un modelo generativo no es determinista bit a bit ni a
temperatura cero, así que la evidencia de que el sistema funciona es el PDF commiteado con
su manifiesto, no la capacidad de reconstruirlo carácter a carácter.

El modelo de embeddings viaja aquí y no en el sello, y la razón es concreta: el sello hashea
el contenido de las tablas `mundo_*` y los vectores ya no están ahí, así que reindexar con
otro modelo cambiaría lo que el escritor ve en cada paquete sin alterar el hash. Registrar
el identificador y la dimensión permite detectarlo comparando manifiestos — que además dicen
cuál era el anterior— en vez de con un hash que solo sabría decir que algo cambió.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import aiosqlite

from storymaker.commons.config import Settings
from storymaker.commons.db.repos import id_insertado


@dataclass(frozen=True)
class DatosDelManifiesto:
    brief_hash: str
    sello_corpus_hash: str
    prompts: dict[str, str] = field(default_factory=dict)
    modelos: dict[str, str] = field(default_factory=dict)
    embeddings: dict[str, str | int] = field(default_factory=dict)
    sdk_version: str | None = None
    gates_enabled: bool = True


async def reunir(db: aiosqlite.Connection, settings: Settings) -> DatosDelManifiesto:
    """Junta lo que hay que registrar. Se lee de la base, no de lo que alguien recuerde."""
    async with db.execute("SELECT hash FROM intake_brief ORDER BY id DESC LIMIT 1") as cursor:
        brief = await cursor.fetchone()
    async with db.execute("SELECT hash FROM mundo_sello ORDER BY id DESC LIMIT 1") as cursor:
        sello = await cursor.fetchone()

    return DatosDelManifiesto(
        brief_hash=str(brief["hash"]) if brief is not None else "",
        sello_corpus_hash=str(sello["hash"]) if sello is not None else "",
        modelos={rol.value: modelo for rol, modelo in settings.modelo_por_rol.items()},
        embeddings={
            "modelo": settings.modelo_embeddings,
            "dimension": settings.dimension_embeddings,
        },
        sdk_version=settings.sdk_version,
        gates_enabled=settings.gates_enabled,
    )


async def escribir(
    db: aiosqlite.Connection, version_novela_id: int, datos: DatosDelManifiesto
) -> int:
    """Escribe el manifiesto de una versión. Es inmutable desde que se escribe."""
    cursor = await db.execute(
        """
        INSERT INTO manifiesto
            (version_novela_id, brief_hash, sello_corpus_hash, prompts_json, modelos_json,
             embeddings_json, sdk_version, gates_enabled)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_novela_id,
            datos.brief_hash,
            datos.sello_corpus_hash,
            json.dumps(datos.prompts, ensure_ascii=False, sort_keys=True),
            json.dumps(datos.modelos, ensure_ascii=False, sort_keys=True),
            json.dumps(datos.embeddings, ensure_ascii=False, sort_keys=True),
            datos.sdk_version,
            int(datos.gates_enabled),
        ),
    )
    return id_insertado(cursor)


async def de_version(db: aiosqlite.Connection, version_novela_id: int) -> aiosqlite.Row | None:
    async with db.execute(
        "SELECT * FROM manifiesto WHERE version_novela_id = ?", (version_novela_id,)
    ) as cursor:
        return await cursor.fetchone()


async def comparar(
    db: aiosqlite.Connection, version_a: int, version_b: int
) -> dict[str, tuple[str, str]]:
    """En qué se diferencian dos manifiestos. Es cómo se detecta un reindexado.

    Devuelve solo lo que cambió, y con los dos valores: saber que el modelo de embeddings
    cambió no sirve de nada si no se sabe cuál era el anterior.
    """
    uno = await de_version(db, version_a)
    otro = await de_version(db, version_b)
    if uno is None or otro is None:
        return {}

    diferencias: dict[str, tuple[str, str]] = {}
    for columna in (
        "brief_hash",
        "sello_corpus_hash",
        "prompts_json",
        "modelos_json",
        "embeddings_json",
        "sdk_version",
    ):
        antes, despues = str(uno[columna] or ""), str(otro[columna] or "")
        if antes != despues:
            diferencias[columna] = (antes, despues)
    return diferencias
