"""spec: §3.6 · arq: §11a, §11e

**El registro es el cableado, no un inventario aparte.**

De aquí saca el grafo qué validadores componen cada pasada, y de aquí saca el hook de
`.claude/` los que puede ejecutar sobre un capítulo editado a mano. Un validador que no
esté registrado sencillamente no corre por ningún camino, de modo que no puede existir un
validador vivo fuera de este diccionario. Eso es lo que convierte `registro_de_validadores`
en una comprobación de clase **A**: no confronta dos listas mantenidas a mano, confronta el
cableado real contra el documento.

**Cada entrada declara la ruta de su implementación como cadena, no como `import`.** Es lo
que permite que el registro cubra los once validadores de §11a —incluidos `schema_guard`,
que vive en `commons/agents/`, y `render_visual`, que conduce un navegador desde
`publication/`— sin que `commons/validation/` importe nada de fuera y sin romper
`core-domain-puro`. Quien resuelve la ruta es quien compone la pasada, no el registro.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class Punto(StrEnum):
    """Dónde corre cada validador. Es lo que el grafo filtra para componer una pasada."""

    SALIDA_DE_NODO_AGENTE = "salida_de_nodo_agente"
    POST_WRITE_CHAPTER = "post_write_chapter"
    POST_EXTRACT = "post_extract"
    GATE_PLOTTING = "gate_plotting"
    GATE_WRITING = "gate_writing"
    PUBLISH_VERSION = "publish_version"


@dataclass(frozen=True)
class EntradaValidador:
    """Las cuatro cosas que el arnés necesita saber de un validador determinista."""

    nombre: str
    punto: Punto
    bloquea: bool
    ruta: str


def _e(nombre: str, punto: Punto, bloquea: bool, ruta: str) -> EntradaValidador:
    return EntradaValidador(nombre, punto, bloquea, ruta)


#: Los once validadores programáticos de §11a. Ni uno más, ni uno menos: la prueba
#: `registro_de_validadores` compara este diccionario, la tabla de §11a de la arquitectura
#: y la de §7.2 de la spec, por pares.
REGISTRO: Final[dict[str, EntradaValidador]] = {
    entrada.nombre: entrada
    for entrada in (
        _e(
            "schema_guard",
            Punto.SALIDA_DE_NODO_AGENTE,
            True,
            "storymaker.commons.agents.schema_guard:validar",
        ),
        _e(
            "nombres_exactos",
            Punto.POST_WRITE_CHAPTER,
            True,
            "storymaker.commons.validation.chapter_validator:nombres_exactos",
        ),
        _e(
            "longitud_capitulo",
            Punto.POST_WRITE_CHAPTER,
            True,
            "storymaker.commons.validation.chapter_validator:longitud_capitulo",
        ),
        _e(
            "guardrail_prohibidas",
            Punto.POST_WRITE_CHAPTER,
            True,
            "storymaker.commons.validation.policy_checker:guardrail_prohibidas",
        ),
        _e(
            "anacronismo_fechado",
            Punto.POST_WRITE_CHAPTER,
            True,
            "storymaker.commons.validation.chapter_validator:anacronismo_fechado",
        ),
        _e(
            "anclaje_valido",
            Punto.POST_WRITE_CHAPTER,
            True,
            "storymaker.commons.validation.chapter_validator:anclaje_valido",
        ),
        _e(
            "cobertura_anclada",
            Punto.GATE_PLOTTING,
            True,
            "storymaker.commons.validation.escaleta:cobertura_anclada",
        ),
        _e(
            "arco_anclado",
            Punto.GATE_PLOTTING,
            True,
            "storymaker.commons.validation.escaleta:arco_anclado",
        ),
        _e(
            "cobertura_capitulo",
            Punto.POST_EXTRACT,
            False,
            "storymaker.commons.validation.chapter_validator:cobertura_capitulo",
        ),
        _e(
            "cobertura_personalizacion",
            Punto.GATE_WRITING,
            True,
            "storymaker.commons.validation.escaleta:cobertura_personalizacion",
        ),
        _e(
            "render_visual",
            Punto.PUBLISH_VERSION,
            True,
            "storymaker.publication.render:render_visual",
        ),
    )
}


def del_punto(punto: Punto) -> tuple[EntradaValidador, ...]:
    """Los validadores de una pasada, en el orden en que se registraron.

    Quien compone una pasada llama aquí en lugar de escribir su propia lista. Si lo hiciera
    por su cuenta, el registro pasaría a ser un inventario paralelo con derecho a derivar y
    la comprobación caería de clase A a clase T.
    """
    return tuple(e for e in REGISTRO.values() if e.punto is punto)


def bloqueantes() -> tuple[str, ...]:
    return tuple(nombre for nombre, e in REGISTRO.items() if e.bloquea)
