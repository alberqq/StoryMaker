"""Servidor MCP minimo sobre entrada y salida estandar, sin dependencias.

El protocolo es JSON-RPC 2.0. De el solo hace falta lo que usan los dos servidores
de recuperacion: `initialize`, `tools/list` y `tools/call`. Arrastrar una libreria
para eso contradiria la decision de que el arnes no tenga dependencias de
almacenamiento ni de transporte.

El contrato que este modulo impone a todo resultado, y que es la razon de que los
dos servidores compartan base:

    contenido + localizador + fecha de consulta

Un resultado al que le falte cualquiera de las tres cosas **no sale**. Se registra
como descartado y se dice por que. Es preferible una laguna declarada a una
afirmacion que nadie podra rastrear dentro de seis meses.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

VERSION_PROTOCOLO = "2024-11-05"


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass
class Resultado:
    """Lo unico que un servidor de recuperacion puede devolver.

    Las tres piezas son obligatorias por construccion: no hay forma de construir un
    Resultado sin localizador ni sin contenido, porque `valido` lo comprueba y el
    servidor descarta los que no lo son antes de responder.
    """

    contenido: str
    localizador: str
    consultado_en: str = field(default_factory=ahora)
    titulo: str = ""
    fragmento: str = ""
    fiabilidad: str = "sin_declarar"

    @property
    def valido(self) -> bool:
        return bool(self.contenido.strip()) and bool(self.localizador.strip())

    def como_dict(self) -> dict[str, Any]:
        return {
            "contenido": self.contenido,
            "localizador": self.localizador,
            "consultado_en": self.consultado_en,
            "titulo": self.titulo,
            "fragmento": self.fragmento,
            "fiabilidad": self.fiabilidad,
        }


@dataclass
class Herramienta:
    nombre: str
    descripcion: str
    esquema_entrada: dict[str, Any]
    funcion: Callable[[dict[str, Any]], dict[str, Any]]

    def declaracion(self) -> dict[str, Any]:
        return {
            "name": self.nombre,
            "description": self.descripcion,
            "inputSchema": self.esquema_entrada,
        }


class Servidor:
    """Bucle JSON-RPC sobre entrada y salida estandar."""

    def __init__(self, nombre: str, version: str = "2.0.0"):
        self.nombre = nombre
        self.version = version
        self.herramientas: dict[str, Herramienta] = {}

    def herramienta(self, nombre: str, descripcion: str, esquema: dict[str, Any]):
        def envoltorio(funcion):
            self.herramientas[nombre] = Herramienta(nombre, descripcion, esquema, funcion)
            return funcion

        return envoltorio

    # -- protocolo ---------------------------------------------------------

    def _responder(self, identificador: Any, resultado: Any) -> None:
        sys.stdout.write(
            json.dumps({"jsonrpc": "2.0", "id": identificador, "result": resultado},
                       ensure_ascii=False) + "\n"
        )
        sys.stdout.flush()

    def _error(self, identificador: Any, codigo: int, mensaje: str) -> None:
        sys.stdout.write(
            json.dumps({"jsonrpc": "2.0", "id": identificador,
                        "error": {"code": codigo, "message": mensaje}},
                       ensure_ascii=False) + "\n"
        )
        sys.stdout.flush()

    def _despachar(self, peticion: dict[str, Any]) -> None:
        metodo = peticion.get("method")
        identificador = peticion.get("id")
        parametros = peticion.get("params", {}) or {}

        if metodo == "initialize":
            self._responder(identificador, {
                "protocolVersion": VERSION_PROTOCOLO,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": self.nombre, "version": self.version},
            })
            return

        if metodo in ("notifications/initialized", "initialized"):
            return  # una notificacion no lleva respuesta

        if metodo == "tools/list":
            self._responder(identificador, {
                "tools": [h.declaracion() for h in self.herramientas.values()]
            })
            return

        if metodo == "tools/call":
            nombre = parametros.get("name")
            herramienta = self.herramientas.get(nombre)
            if herramienta is None:
                self._error(identificador, -32601, f"Herramienta desconocida: {nombre}")
                return
            try:
                salida = herramienta.funcion(parametros.get("arguments", {}) or {})
            except Exception as fallo:  # noqa: BLE001 - se devuelve como error de herramienta
                self._responder(identificador, {
                    "content": [{"type": "text", "text": json.dumps(
                        {"ok": False, "error": str(fallo)}, ensure_ascii=False)}],
                    "isError": True,
                })
                return
            self._responder(identificador, {
                "content": [{"type": "text", "text": json.dumps(salida, ensure_ascii=False, indent=2)}],
                "isError": not salida.get("ok", True),
            })
            return

        if identificador is not None:
            self._error(identificador, -32601, f"Metodo no implementado: {metodo}")

    def ejecutar(self) -> int:
        for linea in sys.stdin:
            texto = linea.strip()
            if not texto:
                continue
            try:
                peticion = json.loads(texto)
            except json.JSONDecodeError:
                continue
            self._despachar(peticion)
        return 0


def filtrar_validos(resultados: list[Resultado]) -> tuple[list[dict[str, Any]], list[str]]:
    """Separa lo entregable de lo que hay que descartar, y dice por que.

    Un resultado sin localizador o sin contenido no se entrega. Devolverlo seria
    darle al investigador material sobre el que afirmar sin poder conservarlo, y la
    afirmacion que saliera de ahi no se podria rastrear.
    """
    validos = [r.como_dict() for r in resultados if r.valido]
    descartados = [
        f"{r.localizador or '(sin localizador)'}: "
        + ("sin contenido recuperable" if not r.contenido.strip() else "sin localizador")
        for r in resultados
        if not r.valido
    ]
    return validos, descartados
