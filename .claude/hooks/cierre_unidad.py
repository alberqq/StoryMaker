#!/usr/bin/env python3
"""Hook `cierre-unidad` - SubagentStop (RF-055).

Cierra la unidad de trabajo, registra el modo de terminacion y libera el cerrojo.

La razon de que esto sea un hook y no una llamada del subagente es que un
subagente puede terminar sin llamar a nada: porque se quedo sin contexto, porque
fallo, o porque el Autor lo interrumpio. Si el cierre dependiera de que el agente
se acordara de cerrarse, una unidad caida dejaria su memoria efimera y su cerrojo
para siempre.

Una unidad que termina sin cierre registrado se cierra aqui como `agotamiento`,
que es lo que de hecho ocurrio, y queda su Deuda.
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

    try:
        from storymaker.ledger import Ledger
        from storymaker.proyecto import Proyecto

        proyecto = Proyecto(raiz_proyectos(), identificador)
        ledger = Ledger(proyecto.almacen, estado["ejecucion_activa"])

        iniciadas = {
            e["carga"]["id_unidad"]: e["carga"]
            for e in ledger.eventos("unidad_iniciada")
            if e.get("carga", {}).get("id_unidad")
        }
        cerradas = {
            e["carga"].get("id_unidad")
            for e in ledger.eventos("unidad_cerrada")
        }
        huerfanas = [u for u in iniciadas if u not in cerradas]

        for id_unidad in huerfanas:
            carga = iniciadas[id_unidad]
            ledger.anexar(
                "unidad_cerrada",
                id_unidad=id_unidad,
                unidad=carga.get("unidad"),
                clave_idempotencia=carga.get("clave_idempotencia"),
                modo_cierre="agotamiento",
                version_vigente=None,
                deuda={
                    "unidad": carga.get("unidad"),
                    "modo_cierre": "agotamiento",
                    "hallazgos": [],
                    "motivo": (
                        "El subagente termino sin registrar cierre. La unidad se cierra "
                        "desde SubagentStop para no dejar la memoria efimera ni el "
                        "cerrojo colgando; su trabajo se rehace desde el manifiesto."
                    ),
                },
                iteraciones_consumidas=1,
                cerrada_por="hook cierre-unidad",
            )
            # La memoria efimera no es autoritativa: se borra sin ceremonia.
            proyecto.almacen.borrar_tmp(id_unidad)

        # El cerrojo se libera aunque el proceso que lo tomo ya no exista.
        cerrojo = proyecto.almacen.raiz / ".cerrojo"
        cerrojo.unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        return permitir()

    return permitir()


if __name__ == "__main__":
    raise SystemExit(main())
