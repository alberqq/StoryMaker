#!/usr/bin/env python3
"""Hook `guard-canon` - PreToolUse (INV-1, INV-9).

Deniega redactar si el Canon no esta aprobado.

Esta comprobacion tambien la hace el nucleo antes de persistir. La redundancia es
deliberada y esta declarada en ADR-02: el hook protege de un agente descaminado, y
la del nucleo protege de un error en el hook. Que las dos digan lo mismo no es
duplicacion inutil: es que cada una cubre un fallo distinto.

La ventaja de tenerla aqui es que deniega **antes de que la llamada exista**, y
por tanto antes de gastar.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from storymaker.hooks_comun import (  # noqa: E402
    denegar,
    estado_proyecto,
    leer_evento,
    orden_del_nucleo,
    permitir,
)

# Ordenes del nucleo que producen prosa de la Novela.
REDACTA = re.compile(r"\bstorymaker\b.*\bescena\s+(escribir|refinar)\b")


def main() -> int:
    evento = leer_evento()
    if evento.get("tool_name") != "Bash":
        return permitir()

    orden = orden_del_nucleo(evento.get("tool_input", {}) or {})
    if orden is None or not REDACTA.search(orden):
        return permitir()

    estado = estado_proyecto()
    if estado is None:
        # Sin poder identificar el Proyecto no se adivina: el nucleo comprobara.
        return permitir()

    if estado.get("canon_estado") != "aprobado":
        return denegar(
            "INV-1: no se redacta una sola escena sobre un Canon que no esta aprobado. "
            f"El Canon esta en estado '{estado.get('canon_estado')}'. Pasa antes por "
            "PC-3 con `storymaker canon aprobar`."
        )

    return permitir()


if __name__ == "__main__":
    raise SystemExit(main())
