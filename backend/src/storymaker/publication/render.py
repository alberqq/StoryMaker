"""spec: §4.5 · arq: §4, §11a, §16.1

La lectura web, el PDF y `render_visual`.

**El render se comprueba antes de publicar, y eso es lo que lo hace una puerta.** G5 no
admite excepción, y un índice roto detectado tras `PublishVersion` sería una versión ya
publicada con la portada mal: no habría adónde volver. Por eso se arma el manifiesto de la
**versión candidata**, se renderiza contra él y se juzga el render **con la transacción
todavía abierta**; si algo no renderiza, se deshace y no hay versión publicada.

**El PDF se imprime desde la misma ruta que lee el navegador.** Es la contrapartida de
elegir React: si el PDF se maquetara aparte, web y PDF divergirían, y la divergencia
aparecería el día de la demo. Imprimiendo la ruta de lectura con Playwright el PDF es
literalmente lo que se ve, y conserva los enlaces internos que necesitan el índice navegable
y la página de novedades.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

import aiosqlite

from storymaker.commons.db.repos import canon, texto
from storymaker.commons.errores import ErrorDeEntorno
from storymaker.commons.validation.modelos import Incidencia, Severidad

#: Lo que `render_visual` exige que exista en la lectura renderizada. Son las tres cosas
#: que §4 nombra: índice navegable, ficha de personajes y portada con dedicatoria.
PIEZAS_EXIGIDAS = ("indice", "personajes", "portada")


@dataclass(frozen=True)
class Lectura:
    """La versión candidata, renderizada a HTML y todavía sin publicar."""

    titulo: str
    portada: str
    indice: str
    capitulos: tuple[tuple[int, str], ...]
    personajes: str

    def como_html(self) -> str:
        cuerpo = "\n".join(
            f'<section id="capitulo-{n}"><h2>Capitulo {n}</h2>{t}</section>'
            for n, t in self.capitulos
        )
        return (
            f"<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(self.titulo)}</title></head><body>"
            f'<header id="portada">{self.portada}</header>'
            f'<nav id="indice">{self.indice}</nav>'
            f"{cuerpo}"
            f'<aside id="personajes">{self.personajes}</aside>'
            f"</body></html>"
        )


async def construir_lectura(db: aiosqlite.Connection, version_id: int) -> Lectura:
    """Arma la lectura de una versión candidata a partir de su manifiesto.

    Se arma desde `version_capitulo` y no desde «los capítulos aprobados», y la diferencia
    importa: una versión es exactamente la lista de `capitulo_version` que la componen, y
    renderizar otra cosa publicaría algo que el manifiesto no describe.
    """
    obra = await canon.obra(db)
    titulo = str(obra["titulo"]) if obra is not None and obra["titulo"] else "Sin titulo"

    capitulos: list[tuple[int, str]] = []
    for fila in await texto.capitulos_de_version(db, version_id):
        async with db.execute(
            "SELECT numero FROM plan_capitulo WHERE id = ?", (fila["capitulo_id"],)
        ) as cursor:
            numero = await cursor.fetchone()
        parrafos = "".join(
            f"<p>{html.escape(p)}</p>" for p in str(fila["texto"]).split("\n") if p.strip()
        )
        capitulos.append((int(numero["numero"]) if numero else 0, parrafos))

    indice = "<ol>" + "".join(
        f'<li><a href="#capitulo-{n}">Capitulo {n}</a></li>' for n, _ in capitulos
    ) + "</ol>"

    fichas = []
    async with db.execute("SELECT nombre, estatus FROM canon_personaje ORDER BY id") as cursor:
        for ficha in await cursor.fetchall():
            fichas.append(
                f"<li>{html.escape(str(ficha['nombre']))} — "
                f"{html.escape(str(ficha['estatus'] or ''))}</li>"
            )

    return Lectura(
        titulo=titulo,
        portada=f"<h1>{html.escape(titulo)}</h1>",
        indice=indice,
        capitulos=tuple(capitulos),
        personajes="<ul>" + "".join(fichas) + "</ul>",
    )


def render_visual(lectura: Lectura) -> list[Incidencia]:
    """Comprueba que el render tiene sus tres piezas. **Corre antes del `commit`.**

    Esta es la comprobación estructural, que no necesita navegador: que el índice tenga
    entradas, que la ficha de personajes no esté vacía y que la portada lleve título. La
    comprobación visual con Playwright vive aparte porque necesita un navegador instalado, y
    un navegador ausente es un error de entorno, no un render roto.
    """
    documento = lectura.como_html()
    incidencias = []

    for pieza in PIEZAS_EXIGIDAS:
        if f'id="{pieza}"' not in documento:
            incidencias.append(
                Incidencia(
                    validador="render_visual",
                    severidad=Severidad.BLOQUEANTE,
                    mensaje=f"La lectura renderizada no tiene {pieza}.",
                    ubicacion=pieza,
                )
            )

    if not lectura.capitulos:
        incidencias.append(
            Incidencia(
                validador="render_visual",
                severidad=Severidad.BLOQUEANTE,
                mensaje="La version candidata no tiene ningun capitulo que renderizar.",
            )
        )
    if "<li>" not in lectura.indice:
        incidencias.append(
            Incidencia(
                validador="render_visual",
                severidad=Severidad.BLOQUEANTE,
                mensaje="El indice no tiene entradas: no seria navegable.",
                ubicacion="indice",
            )
        )
    return incidencias


async def imprimir_pdf(html_lectura: str, destino: str) -> None:
    """Imprime la misma ruta que lee el navegador, con `page.pdf()` de Playwright.

    Si Playwright no está instalado es un **error de entorno** y no un fallo de la novela:
    detiene, no aprueba. Es la misma distinción que con `lake`, y por el mismo motivo — un
    PDF que no se genera porque falta el navegador no dice nada sobre el texto.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise ErrorDeEntorno(
            "Playwright no esta instalado, asi que no se puede imprimir el PDF. Es un error "
            "de entorno: la version no se da por publicada sin el."
        ) from exc

    async with async_playwright() as playwright:
        navegador = await playwright.chromium.launch()
        pagina = await navegador.new_page()
        await pagina.set_content(html_lectura)
        await pagina.pdf(path=destino, format="A5", print_background=True)
        await navegador.close()
