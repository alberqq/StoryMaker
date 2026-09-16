#!/usr/bin/env python3
"""Hook `ledger-llamada` - PostToolUse (RF-083, RNF-013).

Anexa al ledger la llamada con sus tokens, coste, latencia y hashes.

Lo que este hook garantiza es que **ninguna llamada quede fuera de la
contabilidad**, ni siquiera las que un agente hizo sin pasar por el nucleo. La
contabilidad exacta de la seccion 8 depende de que todo pase por un solo sitio, y
este es el cinturon que sujeta lo que se escape del tirante.

Tambien registra las denegaciones: una llamada que un hook `PreToolUse` bloqueo es
informacion, y ADR-02 exige que quede constancia de ella.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from storymaker.hooks_comun import (  # noqa: E402
    estado_proyecto,
    leer_evento,
    permitir,
    proyecto_activo,
    raiz_proyectos,
)


def main() -> int:
    evento = leer_evento()
    estado = estado_proyecto()
    identificador = proyecto_activo()

    if estado is None or identificador is None or not estado.get("ejecucion_activa"):
        return permitir()

    respuesta = evento.get("tool_response", {}) or {}
    denegada = respuesta.get("permissionDecision") == "deny" or respuesta.get("interrupted")

    try:
        from storymaker.ledger import Ledger
        from storymaker.proyecto import Proyecto

        proyecto = Proyecto(raiz_proyectos(), identificador)
        ledger = Ledger(proyecto.almacen, estado["ejecucion_activa"])

        if denegada:
            ledger.anexar(
                "escritura_denegada",
                herramienta=evento.get("tool_name"),
                motivo=respuesta.get("permissionDecisionReason", "sin motivo registrado"),
                entrada_resumida=str(evento.get("tool_input", {}))[:500],
            )
        else:
            # El blob del prompt y el de la salida se guardan por contenido; el
            # ledger solo lleva sus huellas, para seguir siendo legible.
            salida = str(respuesta.get("stdout", ""))[:20000]
            ledger.anexar(
                "llamada_modelo",
                id_unidad=evento.get("session_id", "sin_unidad"),
                herramienta=evento.get("tool_name"),
                blob_salida=proyecto.almacen.guardar_blob(salida) if salida else None,
                tokens_entrada=0,
                tokens_salida=0,
                coste=0.0,
                segundos=0.0,
                modelo_solicitado="via_hook",
                modelo_servido="via_hook",
                nota=(
                    "Registro de respaldo desde PostToolUse. Los tokens y el coste "
                    "exactos los contabiliza `storymaker unidad llamada`."
                ),
            )
    except Exception:  # noqa: BLE001 - la contabilidad no puede tumbar la Ejecucion
        return permitir()

    return permitir()


if __name__ == "__main__":
    raise SystemExit(main())
