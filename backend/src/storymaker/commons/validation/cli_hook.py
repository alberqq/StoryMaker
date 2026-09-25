"""spec: §3.6 · arq: §3, §15

El ejecutable que la skill y el hook de validación de `.claude/` invocan. No tiene lógica
propia: lee el fichero, llama al Core Domain e imprime el informe. Toda la decisión vive en
`entrada_manual`, que es el mismo código que ejecuta el grafo. El contrato de la entrada
por `stdin` está en `specs/final/spec.md` §2.

Tiene dos entradas. La skill lo llama con la ruta como argumento. El hook no: Claude Code
entrega el evento como JSON por la entrada estándar, con la ruta en `tool_input.file_path`,
y el hook salta con **cualquier** `Write` o `Edit`, así que lo primero es descartar lo que
no es un capítulo.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

from storymaker.commons.validation.entrada_manual import revisar_fichero

#: El código con el que Claude Code lee «no sigas». En `PostToolUse` la edición ya está
#: hecha, y lo que recibe el agente es el informe por `stderr` para que la corrija.
BLOQUEA = 2


def leer_evento(entrada: TextIO) -> dict[str, Any]:
    """El evento del hook, o vacío si no llega nada legible."""
    try:
        datos = json.loads(entrada.read() or "{}")
    except json.JSONDecodeError:
        return {}
    return datos if isinstance(datos, dict) else {}


def ruta_del_evento(evento: dict[str, Any]) -> Path | None:
    entrada = evento.get("tool_input")
    ruta = entrada.get("file_path") if isinstance(entrada, dict) else None
    return Path(ruta) if isinstance(ruta, str) and ruta else None


def es_capitulo(ruta: Path) -> bool:
    """Un capítulo exportado para edición manual: Markdown con su contexto al lado.

    Se admite también el nombre `capitulo*.md` sin contexto, que la skill valida con las
    reglas que no lo necesitan. Cualquier otro Markdown —los documentos de `docs/`, las
    specs— no es un capítulo y el hook lo deja pasar sin mirarlo.
    """
    if ruta.suffix.lower() != ".md":
        return False
    return ruta.with_suffix(".contexto.json").exists() or ruta.stem.lower().startswith("capitulo")


def salida_en_utf8() -> None:
    """Claude Code lee el informe en UTF-8, y en Windows la consola no lo es por defecto."""
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")


def main(argumentos: list[str] | None = None, entrada: TextIO | None = None) -> int:
    salida_en_utf8()
    argv = sys.argv[1:] if argumentos is None else argumentos
    if argv:
        ruta = Path(argv[0])
        if not ruta.exists():
            print(f"No existe el fichero {ruta}", file=sys.stderr)
            return BLOQUEA
    else:
        # Invocado como hook: solo se mira lo que es un capítulo, y lo demás pasa.
        ruta_evento = ruta_del_evento(leer_evento(entrada or sys.stdin))
        if ruta_evento is None or not ruta_evento.exists() or not es_capitulo(ruta_evento):
            return 0
        ruta = ruta_evento

    informe = revisar_fichero(ruta)
    if informe.bloquea:
        print(informe.como_texto(), file=sys.stderr)
        return BLOQUEA
    print(informe.como_texto())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
