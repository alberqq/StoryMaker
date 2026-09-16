#!/usr/bin/env python3
"""Hook `guard-proteccion` - PreToolUse (RF-054).

Deniega reescribir un pasaje protegido sin justificacion registrada.

Un pasaje protegido resolvio en su dia un hallazgo bloqueante. Sin esta puerta
ocurre la oscilacion que el mecanismo existe para evitar: el validador senala un
anacronismo, el redactor lo corrige, el refinador reescribe el parrafo por razones
de estilo, y el anacronismo vuelve en la iteracion siguiente. El bucle no converge
y nadie entiende por que.
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
    proyecto_activo,
    raiz_proyectos,
)

REFINA = re.compile(r"\bstorymaker\b.*\bescena\s+refinar\b")
ESCENA = re.compile(r"--escena[=\s]+(\S+)")
JUSTIFICA = re.compile(r"--justificaciones\b")


def main() -> int:
    evento = leer_evento()
    if evento.get("tool_name") != "Bash":
        return permitir()

    orden = orden_del_nucleo(evento.get("tool_input", {}) or {})
    if orden is None or not REFINA.search(orden):
        return permitir()
    if JUSTIFICA.search(orden):
        # Trae justificacion: el nucleo decidira si vale y la somete al validador.
        return permitir()

    coincidencia = ESCENA.search(orden)
    identificador = proyecto_activo()
    estado = estado_proyecto()
    if coincidencia is None or identificador is None or estado is None:
        return permitir()

    id_escena = coincidencia.group(1)
    try:
        from storymaker.dominio.novela import version_vigente
        from storymaker.proyecto import Proyecto

        proyecto = Proyecto(raiz_proyectos(), identificador)
        vigente = version_vigente(proyecto, id_escena)
        if vigente is None:
            return permitir()
        meta = proyecto.almacen.leer_json(
            proyecto.almacen.meta_escena(id_escena, vigente), {}
        ) or {}
    except Exception:  # noqa: BLE001 - un fallo del hook no detiene la Ejecucion
        return permitir()

    protegidos = [p for p in meta.get("pasajes_protegidos", []) if p.get("vigente", True)]
    if not protegidos:
        return permitir()

    return denegar(
        f"RF-054: `{id_escena}` tiene {len(protegidos)} pasajes protegidos, cada uno de "
        "los cuales resolvio un hallazgo bloqueante. Refinala sin tocarlos, o pasa "
        "`--justificaciones` con el motivo de cada reescritura, que se somete al "
        "validador. Pasajes: " + ", ".join(p["id"] for p in protegidos)
    )


if __name__ == "__main__":
    raise SystemExit(main())
