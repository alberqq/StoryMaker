"""spec: §8 · arq: §16.4

La traducción de la taxonomía de errores a códigos HTTP, **en un solo sitio**.

Que viva aquí y no repartida por los endpoints es lo que hace cierta la tabla de §8: si cada
ruta decidiera su propio código, `NovelaOcupada` sería un `409` en un sitio y un `500` en
otro, y la API dejaría de tener un contrato.

La distinción que se conserva es la de siempre: **una incidencia es un defecto del contenido
y tiene camino de vuelta; un error es una avería y detiene la invocación.** Ninguna
incidencia llega hasta aquí — viven como filas en `incidencia` y las lee el gate.
"""

from __future__ import annotations

from typing import Any

from storymaker.commons.errores import (
    ErrorDeEntorno,
    ErrorDeStoryMaker,
    EscaletaAusente,
    EsquemaDelFuturo,
    NovelaNoEncontrada,
    NovelaOcupada,
    PresupuestoExcedido,
    SqliteVecNoDisponible,
)

#: Cada error con su código y con el motivo por el que es ese y no otro.
CODIGOS: dict[type[Exception], tuple[int, str]] = {
    NovelaNoEncontrada: (404, "No hay ninguna novela con ese nombre."),
    NovelaOcupada: (
        409,
        "Ya hay una invocacion en curso sobre esa novela. Quien llega segundo es rechazado, "
        "no encolado: la decision ya esta escrita y reanudar es el camino de siempre.",
    ),
    EscaletaAusente: (422, "La escaleta no contempla ese capitulo."),
    PresupuestoExcedido: (
        503,
        "El prompt excede el techo del rol y la llamada no se emite.",
    ),
    EsquemaDelFuturo: (500, "El fichero tiene un esquema posterior al que este codigo conoce."),
    SqliteVecNoDisponible: (500, "La extension sqlite-vec no carga en este interprete."),
    ErrorDeEntorno: (503, "Falta una herramienta externa. No es un fallo de la novela."),
}


def codigo_de(error: Exception) -> tuple[int, str]:
    """El código y el mensaje de un error. `500` para lo que no está en la tabla.

    Lo desconocido es `500` a propósito: un error que nadie previó no se disfraza de error
    del cliente, porque eso haría que un fallo del arnés pareciera culpa de quien llamó.
    """
    for tipo, (codigo, mensaje) in CODIGOS.items():
        if isinstance(error, tipo):
            return codigo, mensaje
    if isinstance(error, ErrorDeStoryMaker):
        return 500, str(error)
    return 500, "Error interno."


def cuerpo_de(error: Exception) -> dict[str, Any]:
    """El JSON que devuelve la API. Lleva el detalle, porque el cliente es el Autor."""
    codigo, mensaje = codigo_de(error)
    return {
        "error": type(error).__name__,
        "mensaje": mensaje,
        "detalle": str(error),
        "codigo": codigo,
    }


def registrar_en(app: Any) -> None:
    """Instala el manejador en la aplicación de FastAPI."""
    from fastapi import Request
    from fastapi.responses import JSONResponse

    async def manejar(_: Request, error: Exception) -> JSONResponse:
        codigo, _mensaje = codigo_de(error)
        return JSONResponse(status_code=codigo, content=cuerpo_de(error))

    app.add_exception_handler(ErrorDeStoryMaker, manejar)
