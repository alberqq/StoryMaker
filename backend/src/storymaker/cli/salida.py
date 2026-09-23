"""spec: §6, §8 · arq: §16.4

Cómo habla la CLI.

Vive aparte de los comandos por la misma razón que la traducción a HTTP vive en un solo
sitio: para que el mismo error se cuente igual lo pida quien lo pida. Y por una segunda,
más del producto — **la salida de la CLI es lo que el Autor lee cuando algo va mal**, así
que dice qué ha pasado y qué puede hacer, no vuelca una traza.

El coste va siempre etiquetado como **estimación en cliente**. No es un matiz legal: es que
`total_cost_usd` del SDK no es facturación, y presentarlo como si lo fuera sería afirmar
algo que el SDK no dice (U-7).
"""

from __future__ import annotations

from typing import Any

import typer


def aviso(texto: str) -> None:
    typer.echo(texto)


def error(texto: str) -> None:
    typer.secho(texto, fg=typer.colors.RED, err=True)


def resultado(invocacion: Any) -> None:
    """Qué pasó con la invocación: dónde se detuvo y qué espera."""
    if getattr(invocacion, "error", None):
        error(f"La invocacion se detuvo: {invocacion.error}")
        aviso("El ultimo checkpoint queda intacto. `storymaker continuar` retoma por ahi.")
        return

    gate = getattr(invocacion, "gate_abierto", None)
    if gate is not None:
        aviso(f"La invocacion termino en un gate (#{gate}) y espera tu decision.")
        aviso("Decide con: storymaker decidir <novela> aprobar|rehacer|editar|abortar")
        aviso("Nada queda corriendo: el estado esta en disco y el proceso ha terminado.")
    else:
        aviso(f"La invocacion termino en {getattr(invocacion, 'nodo_final', '?')}.")

    consumo = getattr(invocacion, "consumo", None)
    if consumo is not None:
        aviso(
            f"Consumo: {consumo.tokens_in} tokens de entrada, {consumo.tokens_out} de salida, "
            f"{consumo.coste_usd:.4f} $ (estimacion en cliente, no facturacion)."
        )


def estado(datos: dict[str, Any]) -> None:
    aviso(f"{datos['titulo']}")
    aviso(f"  Fase: {datos['fase']}")
    aviso(f"  Capitulos aprobados: {datos['aprobados']}")
    if datos["gate"] is not None:
        aviso(f"  Gate abierto: #{datos['gate']} — espera tu decision")
    if datos["ocupada"]:
        aviso("  Hay una invocacion en curso sobre esta novela.")
    aviso(
        f"  Consumo: {datos['tokens_in']} + {datos['tokens_out']} tokens, "
        f"{datos['coste']:.4f} $ (estimacion en cliente, no facturacion)."
    )


def candidatos(propuestas: list[Any]) -> None:
    """Los candidatos de una petición de cambio, con lo que cuesta cada uno."""
    if not propuestas:
        aviso("No se ha encontrado nada que encaje con esa peticion.")
        return
    aviso("Candidatos, del mas parecido al menos:")
    for candidato in propuestas[:5]:
        aviso(
            f"  [{candidato.objeto.value} #{candidato.fila_id}] {candidato.descripcion} "
            f"(distancia {candidato.distancia:.3f})"
        )
    aviso("\nNada se ha cambiado. La eleccion y el coste se ven en el gate de Regeneration.")
