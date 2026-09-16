"""Lo que comparten los siete hooks (seccion 2.4).

Los hooks son la segunda de las tres capas concentricas de ADR-02. Son
deterministas, se ejecutan fuera del modelo y pueden denegar antes de que la
llamada exista. Ninguno depende de que un agente colabore.

Este modulo vive en el paquete y no en `.claude/hooks/` porque los hooks tambien
son codigo del nucleo: se prueban con el resto, y su logica no puede estar
duplicada en siete ficheros sueltos.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# Rutas que son estado autoritativo del Proyecto. `tmp/` no esta aqui: es la
# memoria efimera, y los permisos la dejan abierta a proposito.
_RUTA_ESTADO = re.compile(
    r"proyectos[/\\][^/\\]+[/\\]"
    r"(proyecto\.json|encargo|contexto|canon|novela|hallazgos|licencias|deudas"
    r"|ejecuciones|fuentes|blobs|indices|entrega)"
)

# Redirecciones y ordenes de shell que escriben. No pretende ser exhaustivo
# frente a alguien que quiera evadirlo -- para eso estan los permisos y el hecho
# de que el nucleo vuelva a comprobar -- sino atrapar al agente descaminado.
ES_ESCRITURA_SHELL = re.compile(
    r"(?:>>?|(?:^|\s)(?:cp|mv|rm|tee|install|touch|truncate|sed\s+-i)\s+)\s*([^\s;|&]+)"
)

CODIGO_CONTINUAR = 0


def leer_evento() -> dict[str, Any]:
    """Lee el evento del hook de la entrada estandar.

    Un evento ilegible no bloquea el trabajo: se devuelve vacio y el hook permite.
    Un hook que muere por un JSON raro convierte un fallo de fontaneria en una
    parada de la Ejecucion, y eso es peor que no comprobar.
    """
    try:
        bruto = sys.stdin.read()
        return json.loads(bruto) if bruto.strip() else {}
    except (json.JSONDecodeError, OSError):
        return {}


def responder(carga: dict[str, Any]) -> int:
    print(json.dumps(carga, ensure_ascii=False))
    return CODIGO_CONTINUAR


def permitir(motivo: str = "") -> int:
    salida: dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }
    if motivo:
        salida["hookSpecificOutput"]["permissionDecisionReason"] = motivo
    return responder(salida)


def denegar(motivo: str) -> int:
    """Deniega la llamada con un motivo.

    El motivo importa: un agente que recibe "denegado" sin mas reintenta lo mismo.
    Uno que recibe "esto lo escribe el nucleo, propon con `storymaker ...`" corrige.
    """
    return responder({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": motivo,
        }
    })


def informar(contexto: str) -> int:
    """Devuelve contexto adicional sin decidir nada (SessionStart, PostToolUse)."""
    return responder({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": contexto,
        }
    })


def ruta_de_estado(ruta: str) -> bool:
    return bool(_RUTA_ESTADO.search(ruta.replace("\\", "/")))


def raiz_proyectos() -> Path:
    return Path(os.environ.get("STORYMAKER_RAIZ", "proyectos"))


def proyecto_activo() -> str | None:
    """El Proyecto sobre el que se esta trabajando.

    Se toma de `STORYMAKER_PROYECTO` si esta declarado; si no, del unico Proyecto
    que haya. Con varios y sin variable, se devuelve None y el hook que dependa de
    ello permite en lugar de adivinar: adivinar el Proyecto equivocado seria peor
    que no comprobar.
    """
    declarado = os.environ.get("STORYMAKER_PROYECTO")
    if declarado:
        return declarado
    raiz = raiz_proyectos()
    if not raiz.exists():
        return None
    candidatos = [d.name for d in raiz.iterdir() if d.is_dir() and (d / "proyecto.json").exists()]
    return candidatos[0] if len(candidatos) == 1 else None


def estado_proyecto() -> dict[str, Any] | None:
    identificador = proyecto_activo()
    if identificador is None:
        return None
    fichero = raiz_proyectos() / identificador / "proyecto.json"
    if not fichero.exists():
        return None
    try:
        return json.loads(fichero.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def orden_del_nucleo(entrada: dict[str, Any]) -> str | None:
    """Devuelve la orden si la llamada es una invocacion del nucleo."""
    orden = str(entrada.get("command", ""))
    if re.search(r"\bstorymaker\b", orden):
        return orden
    return None
