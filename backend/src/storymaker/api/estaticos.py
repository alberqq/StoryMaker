"""spec: §5 · arq: §16.1, §16.4

**FastAPI sirve el frontend construido**, y por eso hay un solo origen.

La URL que abre `render_visual`, la que imprime el PDF y la que teclea el lector son la
misma. La alternativa —dejar el servidor de Vite levantado al lado— ataría la publicación a
un segundo proceso vivo y obligaría al navegador que conduce `render_visual` a conocer dos
orígenes.

La aplicación es de una sola página: `/novelas/x/v/2/capitulos/3` no es un fichero, es una
ruta que resuelve el router de React. Por eso el *fallback* a `index.html` va en el manejador
de `404` y no en una ruta comodín: una ruta `GET` que lo capturara todo convertiría un `POST`
a una dirección inexistente en un `405`, y la API dejaría de decir «eso no existe». La API
vive bajo `/api` y nunca cae en el *fallback*: un endpoint que no existe es un `404` en JSON,
no la portada de la aplicación.

**Sin `dist/` el servidor levanta igual.** El `build` del frontend es requisito de la
publicación, no del arranque: la API responde y solo la ruta de la aplicación falla.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from storymaker.commons.config import Settings

#: Prefijos que nunca son rutas de la aplicación: lo que no exista ahí es un 404 de verdad.
PREFIJOS_DE_SERVIDOR = ("/api/", "/salud", "/docs", "/redoc", "/openapi.json")


def _fichero_dentro(dist: Path, ruta: str) -> Path | None:
    """El fichero estático que pide la URL, sin salirse de `dist/`."""
    candidato = (dist / ruta.lstrip("/")).resolve()
    if candidato.is_file() and candidato.is_relative_to(dist.resolve()):
        return candidato
    return None


def montar_frontend(app: Any, settings: Settings) -> None:
    """Instala el *fallback* de la aplicación de una sola página sobre el `404`."""
    from fastapi import Request
    from fastapi.exception_handlers import http_exception_handler
    from fastapi.responses import FileResponse
    from starlette.exceptions import HTTPException

    dist = settings.frontend_dist

    async def servir_o_404(peticion: Request, error: HTTPException) -> Any:
        ruta = peticion.url.path
        es_de_la_aplicacion = (
            error.status_code == 404
            and peticion.method in ("GET", "HEAD")
            and not ruta.startswith(PREFIJOS_DE_SERVIDOR)
            and (dist / "index.html").is_file()
        )
        if not es_de_la_aplicacion:
            return await http_exception_handler(peticion, error)
        fichero = _fichero_dentro(dist, ruta) if ruta != "/" else None
        return FileResponse(fichero or dist / "index.html")

    app.add_exception_handler(HTTPException, servir_o_404)
