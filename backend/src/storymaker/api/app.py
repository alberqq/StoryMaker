"""spec: §5 · arq: §16.4, §16.5

La API de FastAPI, con tres superficies: **lectura**, **seguimiento** y **operación**.

La operación no ejecuta el grafo: lanza la CLI como proceso aparte (arq. §16.5), de modo que
una novela operada desde la interfaz recorre exactamente el mismo código que una tecleada en
la terminal. Telegram solo avisa: no hay webhook, y nada fuera de la máquina del Autor puede
mover una novela, porque las acciones solo se aceptan desde `127.0.0.1`.

Que la API no lleve autenticación es una decisión declarada y no un olvido: montar usuarios y
sesiones cuesta más que el riesgo que cubre en un sistema que corre en local, con un solo
usuario. Queda anotado como riesgo aceptado U-17.
"""

from __future__ import annotations

from typing import Any

from storymaker.api import cambios, estaticos, fases, lectura, operacion, seguimiento
from storymaker.commons.config import Settings

#: El prefijo de la API. El proxy de Vite reenvía exactamente este camino en desarrollo.
PREFIJO_API = "/api"


def crear_app(settings: Settings | None = None) -> Any:
    """Monta la aplicación. Recibe `Settings` inyectado, como todo lo demás."""
    from fastapi import FastAPI

    from storymaker.api import manejadores

    ajustes = settings or Settings()
    app = FastAPI(
        title="StoryMaker",
        summary="Arnes multiagente para novelas historicas personalizadas",
        version="0.1.0",
    )
    app.state.settings = ajustes

    manejadores.registrar_en(app)
    # La API va bajo `/api` porque comparte origen con la aplicación de React, y las dos
    # tienen rutas que empiezan por `/novelas`: sin prefijo, recargar la página de una
    # novela devolvería su ficha en JSON en lugar de la aplicación.
    app.include_router(seguimiento.router, prefix=PREFIJO_API)
    app.include_router(fases.router, prefix=PREFIJO_API)
    app.include_router(lectura.router, prefix=PREFIJO_API)
    app.include_router(operacion.router, prefix=PREFIJO_API)
    app.include_router(operacion.ejemplos_router, prefix=PREFIJO_API)
    app.include_router(cambios.router, prefix=PREFIJO_API)
    estaticos.montar_frontend(app, ajustes)

    @app.get("/salud", tags=["operacion"])
    async def salud() -> dict[str, str]:
        """Lo mínimo para saber que el servidor está en pie. No abre ninguna novela."""
        return {"estado": "vivo"}

    return app
