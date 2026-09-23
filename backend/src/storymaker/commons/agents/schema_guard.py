"""spec: §3.3 · arq: §11a

`schema_guard`: la salida de cada rol se valida contra su modelo Pydantic **antes de
escribir en SQLite**. Un modelo no escribe nunca en la base sin pasar por aquí.

Es el primero de los once validadores programáticos y el único que corre a la salida de
todos los nodos agente, no en un punto concreto del flujo. Que sea un validador y no un
`try/except` repartido importa: su veredicto se registra como los demás, y su fallo abre
incidencia en vez de propagar una excepción de parseo desde el fondo del sistema.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ValidationError

from storymaker.commons.errores import ErrorDeStoryMaker

_BLOQUE_JSON = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class SalidaInvalida(ErrorDeStoryMaker):
    """La salida del rol no cumple su esquema.

    Lleva el mensaje de error de Pydantic porque ese texto es lo que se le reinyecta al
    modelo en el reintento: decirle «no valida» no le sirve de nada, decirle qué campo
    falta y de qué tipo lo esperábamos sí.
    """

    def __init__(self, mensaje: str, *, bruto: str) -> None:
        super().__init__(mensaje)
        self.bruto = bruto


def _extraer_json(bruto: str) -> str:
    """Saca el objeto JSON de una respuesta que puede venir envuelta en prosa.

    Los modelos tienden a rodear el JSON de explicaciones o de vallas de código. Aceptarlo
    aquí no es indulgencia: es reconocer que el formato de salida no es el contrato —el
    contrato es el esquema— y que fallar por una valla de markdown gastaría un reintento
    en algo que no es un defecto del contenido.
    """
    if (valla := _BLOQUE_JSON.search(bruto)) is not None:
        return valla.group(1).strip()
    inicio = bruto.find("{")
    fin = bruto.rfind("}")
    if inicio != -1 and fin > inicio:
        return bruto[inicio : fin + 1]
    return bruto.strip()


def validar[T: BaseModel](esquema: type[T], bruto: str) -> T:
    """Devuelve la instancia validada, o lanza `SalidaInvalida` con el motivo."""
    texto = _extraer_json(bruto)
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise SalidaInvalida(f"La salida no es JSON valido: {exc}", bruto=bruto) from exc
    try:
        return esquema.model_validate(datos)
    except ValidationError as exc:
        raise SalidaInvalida(
            f"La salida no cumple el esquema {esquema.__name__}:\n{exc}", bruto=bruto
        ) from exc
