"""spec: §3.6 · arq: §15

El hook de policy de `.claude/`: **impide escribir en un capítulo un término prohibido**.
El contrato está en `specs/final/spec.md` §3.

Es un hook distinto del de validación y corre en otro momento. El de validación es
`PostToolUse`: la edición ya está en disco y comprueba el capítulo entero, con todas las
reglas. Este es `PreToolUse`: mira solo el texto que la edición **introduce** y, si trae un
término vetado, la deniega antes de que llegue al fichero. La diferencia importa por el
nivel `destinatario` de §15: el nombre que no puede aparecer en una novela que se regala no
debería llegar a escribirse ni un instante, aunque la validación de después lo fuera a
detectar.

La regla es la del grafo —`guardrail_prohibidas`, con la misma normalización— y los términos
salen del mismo `<capitulo>.contexto.json` que usa el hook de validación. Sin contexto no hay
lista de prohibidas, y el hook deja pasar la edición.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

from storymaker.commons.validation.cli_hook import (
    BLOQUEA,
    es_capitulo,
    leer_evento,
    ruta_del_evento,
    salida_en_utf8,
)
from storymaker.commons.validation.entrada_manual import contexto_desde_json
from storymaker.commons.validation.modelos import CapituloEnRevision, Incidencia
from storymaker.commons.validation.policy_checker import guardrail_prohibidas


def texto_introducido(evento: dict[str, Any]) -> str:
    """Lo que la herramienta va a escribir: el fichero entero o los fragmentos nuevos."""
    entrada = evento.get("tool_input")
    if not isinstance(entrada, dict):
        return ""
    partes = [entrada.get("content"), entrada.get("new_string")]
    ediciones = entrada.get("edits")
    if isinstance(ediciones, list):
        partes += [e.get("new_string") for e in ediciones if isinstance(e, dict)]
    return "\n".join(p for p in partes if isinstance(p, str))


def revisar_edicion(texto: str, ruta_contexto: Path) -> list[Incidencia]:
    if not texto or not ruta_contexto.exists():
        return []
    contexto = contexto_desde_json(json.loads(ruta_contexto.read_text(encoding="utf-8")))
    capitulo = CapituloEnRevision(
        numero=0,
        texto=texto,
        palabras=len(texto.split()),
        rango_palabras=contexto["rango_palabras"],
        prohibidas=contexto["prohibidas"],
    )
    return guardrail_prohibidas(capitulo)


def main(entrada: TextIO | None = None) -> int:
    salida_en_utf8()
    evento = leer_evento(entrada or sys.stdin)
    ruta = ruta_del_evento(evento)
    if ruta is None or not es_capitulo(ruta):
        return 0

    incidencias = revisar_edicion(texto_introducido(evento), ruta.with_suffix(".contexto.json"))
    if not incidencias:
        return 0
    # En `PreToolUse`, el código 2 deniega la herramienta y `stderr` es el motivo que
    # recibe el agente.
    print("Edicion denegada por la policy de terminos prohibidos:", file=sys.stderr)
    for incidencia in incidencias:
        print(f"  - {incidencia.mensaje}", file=sys.stderr)
    return BLOQUEA


if __name__ == "__main__":
    raise SystemExit(main())
