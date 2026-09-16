#!/usr/bin/env python3
"""Hook `guard-escritura` - PreToolUse (ADR-02, mecanismo 2).

Deniega cualquier escritura de estado que no venga del nucleo.

Los permisos de `settings.json` ya deniegan `Write` y `Edit` bajo `proyectos/**`.
Este hook cubre lo que los permisos no ven: un `Bash` con `echo ... > fichero`, un
`python -c` que abre un fichero en modo escritura, un `cp` sobre el Canon. Un
agente al que se le ocurra escribir directamente una escena recibe una denegacion,
no un fallo silencioso, y la denegacion queda en el ledger.

Protocolo de hooks: se lee el evento por la entrada estandar y se responde por la
salida estandar con `permissionDecision` a `deny` o `allow`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from storymaker.hooks_comun import (  # noqa: E402
    ES_ESCRITURA_SHELL,
    denegar,
    leer_evento,
    permitir,
    ruta_de_estado,
)

# La unica excepcion de ADR-02: el borrador de trabajo de una unidad. Es donde un
# agente necesita un sitio donde pensar, y ese sitio no puede ser el estado del
# Proyecto.
TMP = re.compile(r"proyectos[/\\][^/\\]+[/\\]tmp[/\\]")

# Invocaciones del nucleo. El nucleo si escribe: es el unico que puede.
NUCLEO = re.compile(r"\b(storymaker|python\s+-m\s+storymaker)\b")


def main() -> int:
    evento = leer_evento()
    herramienta = evento.get("tool_name", "")
    entrada = evento.get("tool_input", {}) or {}

    if herramienta in ("Write", "Edit", "NotebookEdit"):
        destino = str(entrada.get("file_path", ""))
        if ruta_de_estado(destino) and not TMP.search(destino):
            return denegar(
                f"ADR-02: `{destino}` es estado del Proyecto y solo lo escribe el nucleo. "
                "Propon el resultado con `storymaker ...`, o escribe tu borrador bajo "
                "`proyectos/<prj>/tmp/<udt>/`."
            )
        return permitir()

    if herramienta == "Bash":
        orden = str(entrada.get("command", ""))
        if NUCLEO.search(orden):
            return permitir()
        for fragmento in ES_ESCRITURA_SHELL.findall(orden):
            if ruta_de_estado(fragmento) and not TMP.search(fragmento):
                return denegar(
                    f"ADR-02: la orden escribiria sobre estado del Proyecto (`{fragmento}`). "
                    "Toda escritura pasa por el nucleo `storymaker`, que valida las "
                    "invariantes antes de persistir."
                )
        return permitir()

    return permitir()


if __name__ == "__main__":
    raise SystemExit(main())
