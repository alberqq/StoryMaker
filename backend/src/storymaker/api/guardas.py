"""spec: §5.3 · arq: §16.5

Las dos guardas de las rutas que operan una novela, que son la mitigación de U-17.

La API no lleva autenticación, y desde que la interfaz opera el arnés un endpoint puede
lanzar una novela o decidir un gate, que cuestan dinero. Lo que la protege es que **solo se
opera desde la propia máquina**: el servidor escucha en `127.0.0.1`, y además cada acción
rechaza a quien no llega desde ahí. Y exigir JSON no es burocracia: una página cualquiera
abierta en el navegador del Autor puede enviar un formulario a `127.0.0.1`, pero no un JSON
sin el permiso CORS que esta API no concede.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

#: Los clientes que cuentan como la propia máquina. `testclient` es el que usa el cliente
#: de pruebas de Starlette, que no abre ningún socket.
CLIENTES_LOCALES = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})


async def solo_local(peticion: Request) -> None:
    """Rechaza con `403` a un cliente remoto y con `415` un cuerpo que no sea JSON."""
    cliente = peticion.client.host if peticion.client is not None else ""
    if cliente not in CLIENTES_LOCALES:
        raise HTTPException(
            status_code=403,
            detail="Las acciones solo se aceptan desde la propia maquina del Autor.",
        )
    tipo = peticion.headers.get("content-type", "")
    if not tipo.split(";")[0].strip().lower() == "application/json":
        raise HTTPException(
            status_code=415,
            detail="Las acciones se envian como JSON.",
        )
