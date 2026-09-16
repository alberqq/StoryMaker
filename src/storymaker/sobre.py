"""El sobre comun y la respuesta del nucleo (seccion 6.1 y 6.4).

Todo lo que cruza una frontera -- de agente a nucleo, de etapa a etapa -- viaja
envuelto en una estructura comun. Y todo comando del nucleo devuelve el sobre de
respuesta tipado con `ok`, comando, y datos o error.

Que la respuesta sea siempre la misma forma no es cosmetica: los hooks y los
comandos de barra la parsean sin saber que comando la produjo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from storymaker import SCHEMA_VERSION
from storymaker.errores import ErrorStoryMaker, redactar_secretos

CONTRATOS_VALIDOS = tuple(f"CT-{n}" for n in range(1, 21)) + ("CT-12R", "CT-13R")


def ahora() -> str:
    """Momento en ISO-8601 con zona, que es el unico formato que persistimos."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass
class Sobre:
    """Envoltorio de lo que un agente propone al nucleo o una etapa pasa a otra."""

    contrato: str
    emisor: str
    carga: dict[str, Any]
    proyecto: str | None = None
    ejecucion: str | None = None
    momento: str = field(default_factory=ahora)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.contrato not in CONTRATOS_VALIDOS:
            raise ErrorStoryMaker(
                "ERR-302",
                f"Contrato desconocido: {self.contrato}",
                contrato=self.contrato,
                admitidos=list(CONTRATOS_VALIDOS),
            )

    def como_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contrato": self.contrato,
            "emisor": self.emisor,
            "momento": self.momento,
            "proyecto": self.proyecto,
            "ejecucion": self.ejecucion,
            "carga": self.carga,
        }

    @classmethod
    def desde_dict(cls, dato: dict[str, Any]) -> "Sobre":
        faltan = [c for c in ("contrato", "emisor", "carga") if c not in dato]
        if faltan:
            raise ErrorStoryMaker(
                "ERR-302",
                f"El sobre no lleva {', '.join(faltan)}",
                campos_ausentes=faltan,
            )
        return cls(
            contrato=dato["contrato"],
            emisor=dato["emisor"],
            carga=dato["carga"],
            proyecto=dato.get("proyecto"),
            ejecucion=dato.get("ejecucion"),
            momento=dato.get("momento", ahora()),
            schema_version=dato.get("schema_version", SCHEMA_VERSION),
        )

    @classmethod
    def desde_json(cls, texto: str) -> "Sobre":
        try:
            dato = json.loads(texto)
        except json.JSONDecodeError as fallo:
            raise ErrorStoryMaker("ERR-301", f"El sobre no es JSON parseable: {fallo}") from fallo
        return cls.desde_dict(dato)


@dataclass
class Respuesta:
    """Lo que devuelve todo comando del nucleo."""

    ok: bool
    comando: str
    datos: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None
    avisos: list[str] = field(default_factory=list)

    @classmethod
    def exito(cls, comando: str, **datos: Any) -> "Respuesta":
        avisos = datos.pop("avisos", [])
        return cls(True, comando, datos=redactar_secretos(datos), avisos=list(avisos))

    @classmethod
    def fallo(cls, comando: str, error: ErrorStoryMaker) -> "Respuesta":
        return cls(False, comando, error=error.como_dict())

    def como_dict(self) -> dict[str, Any]:
        salida: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "ok": self.ok,
            "comando": self.comando,
            "momento": ahora(),
        }
        if self.ok:
            salida["datos"] = self.datos
            if self.avisos:
                salida["avisos"] = self.avisos
        else:
            salida["error"] = self.error
        return salida

    def como_json(self) -> str:
        return json.dumps(self.como_dict(), ensure_ascii=False, indent=2, sort_keys=False)
