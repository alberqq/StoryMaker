"""spec: §5 · arq: §16.4

La API de FastAPI: **tres superficies con perfiles de riesgo distintos**, y conviene no
mezclarlas.

El **webhook de Telegram** es el único endpoint que reanuda una ejecución, así que es el
único protegido: comprueba el `secret_token` de la cabecera y rechaza la petición que no lo
traiga. El resto es **lectura**, más una **petición de cambio que no toca nada** hasta que
el Autor la aprueba en su gate.

Que la lectura quede abierta es una decisión declarada y no un olvido: montar usuarios y
sesiones cuesta más que el riesgo que cubre en un sistema que corre en local. Queda anotado
como riesgo aceptado U-17.

**La invocación que reanuda un gate se atiende en segundo plano.** El callback de Telegram
tiene que responder en segundos y la invocación que desencadena puede tardar minutos —
Investigation entera, o los diez capítulos de Writing—. Si el servidor cae a mitad no se
pierde nada que no se pierda con un fallo cualquiera: el último checkpoint está en disco y
reanudar es el camino de siempre.
"""

from __future__ import annotations

from typing import Any

from storymaker.api import cambios, estaticos, lectura, webhook
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
    app.include_router(webhook.router)
    app.include_router(lectura.router)
    app.include_router(cambios.router)
    app.include_router(estaticos.router)

    @app.get("/salud", tags=["operacion"])
    async def salud() -> dict[str, str]:
        """Lo mínimo para saber que el servidor está en pie. No abre ninguna novela."""
        return {"estado": "vivo"}

    return app
