"""spec: §5 · arq: §16.1, §16.3

La ruta de lectura: **la misma que el navegador lee y desde la que se imprime el PDF**.

Es la contrapartida de elegir React. Si el PDF se maquetara aparte, web y PDF divergirían,
y la divergencia aparecería el día de la demo. Imprimiendo esta misma ruta con Playwright el
PDF es literalmente lo que se ve, y conserva los enlaces internos que necesitan el índice
navegable y la página de novedades.

Aquí se sirve el HTML que el backend renderiza contra un manifiesto. Cuando el frontend de
React exista, sustituirá a este render y **seguirá siendo la ruta que se imprime**: lo que
no puede haber es una segunda maquetación que mantener.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from storymaker.api import novelas
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela
from storymaker.commons.errores import NovelaNoEncontrada
from storymaker.publication import render

router = APIRouter(prefix="/lectura", tags=["lectura"])


def _settings(peticion: Request) -> Settings:
    return peticion.app.state.settings  # type: ignore[no-any-return]


@router.get("/{nombre}/{numero}", response_class=HTMLResponse)
async def leer(nombre: str, numero: int, peticion: Request) -> Any:
    """La novela entera, renderizada contra el manifiesto de esa versión.

    Se sirve **por versión** y no «la última»: un capítulo regenerado tiene texto distinto en
    cada una, y servir la última sin decirlo haría que un enlace compartido cambiara de
    contenido bajo los pies de quien lo abrió.
    """
    ruta = await novelas.exigir(nombre, _settings(peticion))

    async with abrir_novela(ruta) as db:
        async with db.execute(
            "SELECT id FROM version_novela WHERE numero = ?", (numero,)
        ) as cursor:
            fila = await cursor.fetchone()
        if fila is None:
            raise NovelaNoEncontrada(f"La novela {nombre} no tiene version {numero}")
        lectura = await render.construir_lectura(db, int(fila["id"]))

    return HTMLResponse(content=lectura.como_html())


@router.get("/{nombre}", response_class=HTMLResponse)
async def leer_la_ultima(nombre: str, peticion: Request) -> Any:
    """Atajo a la última versión publicada, con su número visible en la URL final."""
    ruta = await novelas.exigir(nombre, _settings(peticion))
    async with abrir_novela(ruta) as db:
        async with db.execute(
            "SELECT numero FROM version_novela ORDER BY numero DESC LIMIT 1"
        ) as cursor:
            fila = await cursor.fetchone()
    if fila is None:
        raise NovelaNoEncontrada(f"La novela {nombre} no tiene ninguna version publicada")
    return await leer(nombre, int(fila["numero"]), peticion)
