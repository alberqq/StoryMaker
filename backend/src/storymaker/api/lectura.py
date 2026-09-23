"""spec: §5 · arq: §16.4

Los endpoints de lectura: la superficie que el frontend consume.

Todos son `GET`, ninguno escribe y ninguno lleva autenticación. **Es una decisión declarada
y no un olvido**: el webhook —el único que reanuda una ejecución— sí comprueba su secreto,
de modo que lo que queda abierto es leer, y leer una novela que corre en la máquina del
Autor no justifica montar usuarios y sesiones. Queda como riesgo aceptado U-17.

Lo que devuelven sale del **manifiesto** y no de «los capítulos aprobados»: una versión es
exactamente la lista de `capitulo_version` que la componen, y servir otra cosa enseñaría una
novela que ningún manifiesto describe.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from storymaker.api import novelas
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela
from storymaker.commons.db.repos import texto
from storymaker.commons.errores import NovelaNoEncontrada
from storymaker.publication import manifiesto
from storymaker.regeneration import diff

router = APIRouter(prefix="/novelas", tags=["lectura"])


def _settings(peticion: Request) -> Settings:
    return peticion.app.state.settings  # type: ignore[no-any-return]


@router.get("")
async def listar(peticion: Request) -> list[dict[str, Any]]:
    """Lista el directorio y abre cada fichero. No hay registro global de novelas."""
    fichas = await novelas.listar(_settings(peticion))
    return [
        {
            "nombre": f.nombre,
            "titulo": f.titulo,
            "fase": f.fase,
            "versiones": f.versiones,
            "gate_abierto": f.gate_abierto,
            "ocupada": f.ocupada,
        }
        for f in fichas
    ]


@router.get("/{nombre}")
async def ficha(nombre: str, peticion: Request) -> dict[str, Any]:
    """Fase, gate abierto si lo hay, versiones publicadas."""
    ruta = await novelas.exigir(nombre, _settings(peticion))
    f = await novelas.ficha(ruta)
    return {
        "nombre": f.nombre,
        "titulo": f.titulo,
        "fase": f.fase,
        "versiones": f.versiones,
        "gate_abierto": f.gate_abierto,
        "ocupada": f.ocupada,
    }


@router.get("/{nombre}/versiones/{numero}")
async def version(nombre: str, numero: int, peticion: Request) -> dict[str, Any]:
    """El manifiesto de una versión y sus capítulos en orden."""
    ruta = await novelas.exigir(nombre, _settings(peticion))
    async with abrir_novela(ruta) as db:
        async with db.execute(
            "SELECT id FROM version_novela WHERE numero = ?", (numero,)
        ) as cursor:
            fila = await cursor.fetchone()
        if fila is None:
            raise NovelaNoEncontrada(f"La novela {nombre} no tiene version {numero}")
        version_id = int(fila["id"])
        capitulos = await texto.capitulos_de_version(db, version_id)
        registro = await manifiesto.de_version(db, version_id)

    return {
        "numero": numero,
        "capitulos": [
            {"id": int(c["id"]), "palabras": int(c["palabras"]), "resumen": c["resumen"]}
            for c in capitulos
        ],
        "manifiesto": {
            "brief_hash": str(registro["brief_hash"]) if registro else None,
            "sello_corpus_hash": str(registro["sello_corpus_hash"]) if registro else None,
            "embeddings": str(registro["embeddings_json"]) if registro else None,
        },
    }


@router.get("/{nombre}/versiones/{numero}/capitulos/{orden}")
async def capitulo(nombre: str, numero: int, orden: int, peticion: Request) -> dict[str, Any]:
    """El texto del capítulo **tal como esa versión lo fija**.

    Se pide por versión y no «el último»: un capítulo no regenerado se comparte entre
    versiones, y uno regenerado tiene texto distinto en cada una.
    """
    ruta = await novelas.exigir(nombre, _settings(peticion))
    async with abrir_novela(ruta) as db:
        async with db.execute(
            "SELECT id FROM version_novela WHERE numero = ?", (numero,)
        ) as cursor:
            fila = await cursor.fetchone()
        if fila is None:
            raise NovelaNoEncontrada(f"La novela {nombre} no tiene version {numero}")
        capitulos = await texto.capitulos_de_version(db, int(fila["id"]))

    if orden < 1 or orden > len(capitulos):
        raise NovelaNoEncontrada(f"La version {numero} no tiene capitulo {orden}")
    elegido = capitulos[orden - 1]
    return {
        "orden": orden,
        "texto": str(elegido["texto"]),
        "palabras": int(elegido["palabras"]),
    }


@router.get("/{nombre}/personajes")
async def personajes(nombre: str, peticion: Request) -> list[dict[str, Any]]:
    """Fichas de personajes y lugares, con los capítulos en que aparecen."""
    ruta = await novelas.exigir(nombre, _settings(peticion))
    async with abrir_novela(ruta) as db:
        async with db.execute(
            """
            SELECT p.id, p.nombre, p.tipo, p.estatus,
                   GROUP_CONCAT(DISTINCT c.numero) AS capitulos
              FROM canon_personaje p
              LEFT JOIN plan_escena_personaje ep ON ep.personaje_id = p.id
              LEFT JOIN plan_escena e ON e.id = ep.escena_id
              LEFT JOIN plan_capitulo c ON c.id = e.capitulo_id
             GROUP BY p.id
             ORDER BY p.id
            """
        ) as cursor:
            filas = list(await cursor.fetchall())

    return [
        {
            "id": int(f["id"]),
            "nombre": str(f["nombre"]),
            "tipo": str(f["tipo"]),
            "estatus": str(f["estatus"] or ""),
            "capitulos": [int(n) for n in str(f["capitulos"] or "").split(",") if n],
        }
        for f in filas
    ]


@router.get("/{nombre}/versiones/{a}/diff/{b}")
async def diferencias(nombre: str, a: int, b: int, peticion: Request) -> dict[str, Any]:
    """Qué capítulos cambian entre dos versiones. Un `JOIN`, no un diff de texto."""
    ruta = await novelas.exigir(nombre, _settings(peticion))
    async with abrir_novela(ruta) as db:
        ids = {}
        for numero in (a, b):
            async with db.execute(
                "SELECT id FROM version_novela WHERE numero = ?", (numero,)
            ) as cursor:
                fila = await cursor.fetchone()
            if fila is None:
                raise NovelaNoEncontrada(f"La novela {nombre} no tiene version {numero}")
            ids[numero] = int(fila["id"])
        resultado = await diff.entre(db, ids[a], ids[b])

    return {
        "version_a": a,
        "version_b": b,
        "cambios": [
            {"capitulo": c.numero, "estado": c.estado} for c in resultado.cambiados
        ],
        "resumen": resultado.como_texto(),
    }
