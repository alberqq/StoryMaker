"""spec: §5 · arq: §16.4

La API de FastAPI: **lectura**, más una **petición de cambio que no toca nada** hasta que el
Autor la aprueba en su gate.

**Ningún endpoint reanuda una ejecución.** Los gates se deciden en el PC del Autor con
`storymaker decidir`, y Telegram solo avisa (arq. §10): no hay webhook ni superficie pública
que pueda mover una novela.

Que la lectura quede abierta es una decisión declarada y no un olvido: montar usuarios y
sesiones cuesta más que el riesgo que cubre en un sistema que corre en local. Queda anotado
como riesgo aceptado U-17.
"""

from __future__ import annotations

from typing import Any

from storymaker.api import cambios, estaticos, lectura
from storymaker.commons.config import Settings


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
    app.include_router(lectura.router)
    app.include_router(cambios.router)
    app.include_router(estaticos.router)

    @app.get("/salud", tags=["operacion"])
    async def salud() -> dict[str, str]:
        """Lo mínimo para saber que el servidor está en pie. No abre ninguna novela."""
        return {"estado": "vivo"}

    return app
