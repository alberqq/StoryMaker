#!/usr/bin/env python3
"""Hook `guard-presupuesto` - PreToolUse (RF-072, ERR-404).

Admision previa: deniega la unidad cuya estimacion supera el remanente, **antes de
gastar**.

El control de presupuesto no es un aviso a posteriori. Un sobrecoste que se
descubre cuando ya se gasto no se puede deshacer: el dinero ya salio. Por eso esta
puerta corre antes de que la llamada exista, y por eso deniega en lugar de avisar.
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

# Ordenes que consumen presupuesto de modelo. `unidad admitir` no esta aqui: esa
# orden *es* la puerta de admision, y denegarla dejaria al nucleo sin forma de
# registrar la denegacion en el ledger.
CONSUME = re.compile(r"\bstorymaker\b.*\b(escena\s+(escribir|refinar)|capitulo\s+validar|novela\s+pasada-global)\b")


def main() -> int:
    evento = leer_evento()
    if evento.get("tool_name") != "Bash":
        return permitir()

    orden = orden_del_nucleo(evento.get("tool_input", {}) or {})
    if orden is None or not CONSUME.search(orden):
        return permitir()

    estado = estado_proyecto()
    identificador = proyecto_activo()
    if estado is None or identificador is None or not estado.get("ejecucion_activa"):
        return permitir()

    try:
        from storymaker.dominio.ejecucion import reconstruir_contabilidad
        from storymaker.proyecto import Proyecto

        proyecto = Proyecto(raiz_proyectos(), identificador)
        contabilidad = reconstruir_contabilidad(proyecto, estado["ejecucion_activa"])
    except Exception:  # noqa: BLE001 - un fallo del hook no detiene la Ejecucion
        return permitir()

    remanente = contabilidad.remanente()
    agotados = [
        nombre for nombre in ("coste", "segundos", "iteraciones")
        if remanente[nombre] <= 0
    ]
    if agotados:
        # RF-072: se detiene con el primero que se agota, y se dice cual fue.
        primero = agotados[0]
        codigo = {"coste": "ERR-402", "segundos": "ERR-403", "iteraciones": "ERR-401"}[primero]
        return denegar(
            f"{codigo}: el presupuesto de {primero} de esta Ejecucion esta agotado "
            f"(remanente {remanente[primero]}). Aplica la politica de agotamiento del "
            "bucle o amplia el presupuesto en `/control`."
        )

    return permitir()


if __name__ == "__main__":
    raise SystemExit(main())
