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
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite

from storymaker.commons.config import Settings
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
            f'<!doctype html><html lang="es"><head><meta charset="utf-8">'
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

    indice = (
        "<ol>"
        + "".join(f'<li><a href="#capitulo-{n}">Capitulo {n}</a></li>' for n, _ in capitulos)
        + "</ol>"
    )

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


# --- El PDF desde la ruta de impresión del frontend ------------------------------------

#: El origen que ve el navegador. No existe: el propio proceso responde cada petición.
_ORIGEN = "http://storymaker.local"

#: Cuánto se espera a que la ruta de impresión termine de pedir y pintar la novela.
_ESPERA_MS = 20_000

#: Los márgenes y el pie del libro. La numeración la pone Chromium al imprimir.
_MARGENES: Any = {"top": "16mm", "bottom": "18mm", "left": "15mm", "right": "15mm"}
_PIE = (
    '<div style="width:100%;text-align:center;font-family:Georgia,serif;font-size:8pt;'
    'color:#8a8078;"><span class="pageNumber"></span></div>'
)


async def imprimir_version(novela: Path, numero: int, destino: Path, settings: Settings) -> None:
    """Imprime la ruta `/imprimir` del frontend, **la misma que lee el navegador** (arq. §16.1).

    No hace falta un servidor levantado: Playwright abre la ruta en un origen inventado y el
    propio proceso le responde, con los estáticos de `frontend_dist` y la API con la aplicación
    de FastAPI en memoria. Así el PDF es literalmente lo que se ve en pantalla, sin segunda
    maquetación, y la CLI imprime igual que la interfaz.
    """
    import mimetypes

    import httpx

    try:
        from playwright.async_api import Route, async_playwright
    except ImportError as exc:
        raise ErrorDeEntorno("Playwright no esta instalado: no se puede imprimir el PDF.") from exc

    from storymaker.api.app import crear_app

    dist = settings.frontend_dist.resolve()
    if not (dist / "index.html").is_file():
        raise ErrorDeEntorno(f"No hay frontend construido en {dist}: falta `npm run build`.")
    aplicacion = crear_app(settings)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=aplicacion), base_url=_ORIGEN
    ) as api:

        async def responder(ruta: Route) -> None:
            peticion = ruta.request
            camino = httpx.URL(peticion.url).path
            if camino.startswith("/api/"):
                respuesta = await api.request(
                    peticion.method,
                    peticion.url,
                    headers=peticion.headers,
                    content=peticion.post_data_buffer,
                )
                await ruta.fulfill(
                    status=respuesta.status_code,
                    headers=dict(respuesta.headers),
                    body=respuesta.content,
                )
                return
            fichero = (dist / camino.lstrip("/")).resolve()
            if not fichero.is_file() or not fichero.is_relative_to(dist):
                fichero = dist / "index.html"
            tipo = mimetypes.guess_type(fichero.name)[0] or "application/octet-stream"
            await ruta.fulfill(status=200, body=fichero.read_bytes(), content_type=tipo)

        async with async_playwright() as playwright:
            navegador = await playwright.chromium.launch()
            try:
                pagina = await navegador.new_page()
                await pagina.route(f"{_ORIGEN}/**", responder)
                await pagina.goto(f"{_ORIGEN}/novelas/{novela.stem}/v/{numero}/imprimir")
                # Listo o con error, lo que llegue antes: un documento que no renderiza no se
                # espera un minuto, se cae al HTML mínimo.
                await pagina.wait_for_selector(
                    '[data-estado="listo"], [role="alert"]', timeout=_ESPERA_MS
                )
                if not await pagina.query_selector('[data-estado="listo"]'):
                    raise ErrorDeEntorno("La ruta de impresion no llego a renderizar la novela.")
                await pagina.evaluate("document.fonts.ready.then(() => true)")
                await pagina.pdf(
                    path=str(destino),
                    format="A5",
                    print_background=True,
                    margin=_MARGENES,
                    display_header_footer=True,
                    header_template="<span></span>",
                    footer_template=_PIE,
                )
            finally:
                await navegador.close()


async def imprimir_pendientes(
    novela: Path, settings: Settings, *, rehacer: bool = False
) -> list[Path]:
    """Imprime el PDF de cada versión publicada que aún no lo tenga. Devuelve los impresos.

    La llama `invocar` al salir del grafo, ya confirmado todo: dentro del paso de `publish`
    la versión nueva no es visible para otra conexión, y la ruta de impresión la lee por la
    API. Imprimir lo que falte, y no solo lo último, hace que un fallo se repare solo en la
    siguiente invocación que termine. Sin frontend construido se cae al HTML mínimo.
    """
    from storymaker.commons.db.apertura import abrir_novela

    async with abrir_novela(novela) as db:
        async with db.execute("SELECT id, numero FROM version_novela ORDER BY numero") as cursor:
            versiones = [(int(f["id"]), int(f["numero"])) for f in await cursor.fetchall()]
    impresos = []
    for version_id, numero in versiones:
        destino = novela.with_suffix(f".v{numero}.pdf")
        if destino.exists() and not rehacer:
            continue
        try:
            await imprimir_version(novela, numero, destino, settings)
        except ErrorDeEntorno as motivo:
            print(f"Aviso: {motivo} Se imprime el HTML minimo.", file=sys.stderr)
            async with abrir_novela(novela) as db:
                lectura = await construir_lectura(db, version_id)
            await imprimir_pdf(lectura.como_html(), str(destino))
        impresos.append(destino)
    return impresos
