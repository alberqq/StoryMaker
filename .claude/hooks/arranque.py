#!/usr/bin/env python3
"""Hook `arranque` - SessionStart (RF-084, RF-086).

Carga el estado del Proyecto, comprueba el esquema y avisa de los puntos de
control pendientes.

Es lo primero que ve la sesion. Su trabajo es que el Autor no tenga que preguntar
donde se quedo, y que una sesion no arranque sobre un esquema que no se sabe leer:
ADR-06 regla 3 prefiere no arrancar a leer mal.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from storymaker.hooks_comun import (  # noqa: E402
    informar,
    leer_evento,
    proyecto_activo,
    raiz_proyectos,
)


def main() -> int:
    leer_evento()
    identificador = proyecto_activo()

    if identificador is None:
        return informar(
            "StoryMaker: no hay ningun Proyecto activo, o hay varios y "
            "`STORYMAKER_PROYECTO` no esta declarado. Crea uno con `/encargo` o "
            "declara cual con la variable de entorno."
        )

    try:
        from storymaker import SCHEMA_VERSION
        from storymaker.dominio import ejecucion as d_ejecucion
        from storymaker.proyecto import Proyecto

        proyecto = Proyecto(raiz_proyectos(), identificador)
        estado = proyecto.estado
        lineas = [
            f"**StoryMaker** - Proyecto `{estado.id}` ({estado.titulo_provisional})",
            f"- Estado: {estado.estado} | Etapa: {estado.etapa} | Modo: {estado.modo}",
            f"- Canon: {estado.canon_version_vigente or 'sin proponer'} "
            f"({estado.canon_estado or 'sin estado'})",
        ]

        if estado.schema_version != SCHEMA_VERSION:
            lineas.append(
                f"- **Aviso de esquema**: el Proyecto es v{estado.schema_version} y el "
                f"nucleo es v{SCHEMA_VERSION}. Se promovera en lectura y quedara "
                "constancia en el ledger (ADR-06 regla 5)."
            )

        if estado.limitado_a_reservas:
            lineas.append(
                "- **El Proyecto solo puede alcanzar *finalizado con reservas***: "
                + "; ".join(estado.motivo_reservas)
            )

        if estado.ejecucion_activa:
            resumen = d_ejecucion.estado(proyecto)
            recuento = resumen["hallazgos_abiertos_por_severidad"]
            lineas.append(
                f"- Ejecucion `{estado.ejecucion_activa}` | avance {resumen['avance']:.0%} | "
                f"hallazgos abiertos: {recuento['bloqueante']} bloqueantes, "
                f"{recuento['mayor']} mayores, {recuento['menor']} menores"
            )
            lineas.append(
                f"- Remanente: {resumen['remanente']['coste']} de coste, "
                f"{resumen['remanente']['iteraciones']} iteraciones"
            )
            pendientes = resumen["puntos_control_pendientes"]
            if pendientes:
                lineas.append(
                    f"- **{len(pendientes)} puntos de control esperan tu decision**: "
                    + ", ".join(f"{p['id']} ({p['tipo']})" for p in pendientes)
                    + ". Resuelvelos con `/control`."
                )
            if resumen["lineas_descartadas"]:
                lineas.append(
                    f"- **ERR-503**: {len(resumen['lineas_descartadas'])} lineas truncadas "
                    "en los libros de solo anexion. El trabajo posterior a ellas se rehace."
                )
        else:
            lineas.append("- Sin Ejecucion activa. Arranca o reanuda con `/ejecutar`.")

        return informar("\n".join(lineas))
    except Exception as fallo:  # noqa: BLE001
        return informar(
            f"StoryMaker: no se pudo cargar el estado de `{identificador}`: {fallo}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
