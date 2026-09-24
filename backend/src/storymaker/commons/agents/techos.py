"""spec: §3.3 · arq: §12

La tabla de techos de §12, como dato y no como literal disperso por el código.

El límite del sistema son **100.000 tokens concurrentes**, y el Agent SDK no ofrece forma
documentada de consultar cuánto contexto lleva consumido una sesión mientras corre. Así
que el límite **no se vigila: se garantiza por construcción**, y el método es sumar techos
declarados. Un agente sin fila en esta tabla sería un hueco en esa suma, que es
exactamente por lo que los dos extractores son roles y no funciones del arnés.

El investigador aparece dos veces porque tiene dos perfiles con techos muy distintos: la
sesión inicial, que mete tres páginas enteras en su ventana y gobierna el peor caso del
sistema, y la micro-sesión de Plotting, que abre una sola.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from storymaker.commons.config import Rol


class Perfil(StrEnum):
    """Un rol en un punto concreto del flujo. Es la clave de la tabla de techos."""

    ENTREVISTADOR = "entrevistador"
    EXTRACTOR_INTAKE = "extractor_intake"
    INVESTIGADOR_INICIAL = "investigador_inicial"
    INVESTIGADOR_MICRO = "investigador_micro"
    INVESTIGADOR_DIRIGIDO = "investigador_dirigido"
    VERIFICADOR = "verificador"
    ARQUITECTO = "arquitecto"
    ESCRITOR = "escritor"
    EDITOR = "editor"
    EXTRACTOR_CAPITULO = "extractor_capitulo"
    JUEZ = "juez"


@dataclass(frozen=True)
class Techo:
    """Lo que un perfil puede llegar a tener abierto a la vez.

    `total` no es la suma aritmética de los otros tres: es el techo declarado en §12, que
    ya contempla el peor caso de ese perfil —tres `WebFetch` acotados en el caso del
    investigador inicial— y es el número con el que se hace la suma del sistema.
    """

    rol: Rol
    prompt_y_skills: int
    contexto: int
    salida_maxima: int
    total: int
    #: Cuántas veces puede llamar a cada herramienta en toda la sesión.
    cuota_de_herramientas: tuple[tuple[str, int], ...] = ()


TECHOS: Final[dict[Perfil, Techo]] = {
    Perfil.ENTREVISTADOR: Techo(Rol.ENTREVISTADOR, 2_000, 4_000, 2_000, 8_000),
    Perfil.EXTRACTOR_INTAKE: Techo(Rol.EXTRACTOR_INTAKE, 1_500, 3_000, 1_500, 6_000),
    Perfil.INVESTIGADOR_INICIAL: Techo(
        Rol.INVESTIGADOR,
        2_000,
        31_000,
        6_000,
        45_000,
        cuota_de_herramientas=(("WebSearch", 3), ("WebFetch", 3)),
    ),
    Perfil.INVESTIGADOR_MICRO: Techo(
        Rol.INVESTIGADOR,
        2_000,
        11_000,
        1_000,
        14_000,
        cuota_de_herramientas=(("WebSearch", 1), ("WebFetch", 1)),
    ),
    Perfil.INVESTIGADOR_DIRIGIDO: Techo(
        Rol.INVESTIGADOR,
        2_000,
        11_000,
        2_000,
        15_000,
        cuota_de_herramientas=(("WebSearch", 1), ("WebFetch", 1)),
    ),
    Perfil.VERIFICADOR: Techo(Rol.VERIFICADOR, 2_000, 8_000, 2_000, 12_000),
    Perfil.ARQUITECTO: Techo(Rol.ARQUITECTO, 2_000, 15_000, 8_000, 25_000),
    Perfil.ESCRITOR: Techo(Rol.ESCRITOR, 5_000, 12_000, 3_000, 20_000),
    Perfil.EDITOR: Techo(Rol.EDITOR, 5_000, 12_000, 3_000, 20_000),
    Perfil.EXTRACTOR_CAPITULO: Techo(Rol.EXTRACTOR_CAPITULO, 2_000, 8_000, 2_000, 12_000),
    Perfil.JUEZ: Techo(Rol.JUEZ, 3_500, 26_000, 3_000, 32_500),
}

#: Las herramientas que cada perfil tiene concedidas. **Solo el investigador sale a la
#: red**; el resto trabaja exclusivamente sobre lo que el arnés le entrega, y la regla
#: Semgrep `sin-red-fuera-del-investigador` impide que eso cambie por descuido.
HERRAMIENTAS: Final[dict[Perfil, tuple[str, ...]]] = {
    Perfil.INVESTIGADOR_INICIAL: ("WebSearch", "WebFetch"),
    Perfil.INVESTIGADOR_MICRO: ("WebSearch", "WebFetch"),
    Perfil.INVESTIGADOR_DIRIGIDO: ("WebSearch", "WebFetch"),
}

#: `max_turns` por perfil. La micro-sesión del arquitecto es de uno o dos turnos: busca
#: una cosa concreta y vuelve.
TURNOS: Final[dict[Perfil, int]] = {
    Perfil.INVESTIGADOR_INICIAL: 20,
    Perfil.INVESTIGADOR_MICRO: 2,
    Perfil.INVESTIGADOR_DIRIGIDO: 4,
}

#: El techo del sistema entero, del que se derivan todos los demás.
PEOR_CASO_DEL_SISTEMA: Final = max(techo.total for techo in TECHOS.values())


def herramientas_de(perfil: Perfil) -> tuple[str, ...]:
    return HERRAMIENTAS.get(perfil, ())


def turnos_de(perfil: Perfil) -> int:
    """Uno por defecto: casi todos los roles reciben su contexto y responden una vez."""
    return TURNOS.get(perfil, 1)
