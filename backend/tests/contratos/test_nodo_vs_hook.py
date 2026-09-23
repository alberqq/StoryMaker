"""spec: §3.6, §7.1 nº 13 · arq: §3, §15

**La prueba de contrato más valiosa del proyecto.**

Ejecuta el mismo capítulo por los dos caminos —como lo ejecutaría el grafo y como lo
ejecuta el hook de `.claude/` cuando una persona edita el fichero a mano— y exige el mismo
veredicto, incidencia por incidencia.

Si divergieran, el producto y el editor humano dejarían de estar de acuerdo sobre qué es
válido: el Autor corregiría a mano un capítulo que su editor da por bueno y el arnés
volvería a rechazarlo, o peor, al revés. Que sea una prueba y no una convención es lo que
convierte «una sola lógica, dos puntos de ejecución» en una propiedad comprobada.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storymaker.commons.validation.chapter_validator import validar_capitulo
from storymaker.commons.validation.entrada_manual import contexto_desde_json, revisar_fichero
from storymaker.commons.validation.modelos import (
    CapituloEnRevision,
    EntidadFechada,
    TerminoProhibido,
)
from storymaker.commons.validation.policy_checker import guardrail_prohibidas

CONTEXTO = {
    "numero": 3,
    "nombres_canonicos": ["Manuel Ferrer"],
    "prohibidas": [{"nivel": "destinatario", "termino": "Beatriz", "normalizado": "beatriz"}],
    "entidades_fechadas": [{"nombre": "telegrafo", "fecha_inicio": "1844"}],
    "fecha_narrativa": "1805-04-11",
    "rango_palabras": [5, 40],
}

LIMPIO = (
    "Manuel Ferrer bajo al muelle antes del amanecer y conto los cascos uno a uno, "
    "como hacia su padre, con la niebla pegada a la jarcia y el catalejo en la mano."
)

SUCIO = (
    "manuel ferrer saco el telegrafo del bolsillo y penso en Beatriz mientras la niebla "
    "subia del agua sin prisa alguna por encima de los cascos varados en la arena."
)


def _por_el_nodo(texto: str) -> list[tuple[str, str]]:
    """Lo que haria el grafo: construir el capitulo y correr la pasada determinista."""
    capitulo = CapituloEnRevision(
        numero=int(CONTEXTO["numero"]),  # type: ignore[arg-type]
        texto=texto,
        palabras=len(texto.split()),
        rango_palabras=(5, 40),
        nombres_canonicos=("Manuel Ferrer",),
        prohibidas=(TerminoProhibido("destinatario", "Beatriz", "beatriz"),),
        entidades_fechadas=(EntidadFechada("telegrafo", "1844"),),
        fecha_narrativa="1805-04-11",
    )
    incidencias = [*validar_capitulo(capitulo), *guardrail_prohibidas(capitulo)]
    return sorted((i.validador, i.mensaje) for i in incidencias)


def _por_el_hook(texto: str, carpeta: Path) -> list[tuple[str, str]]:
    """Lo que hace Claude Code: un fichero en disco y su contexto al lado."""
    capitulo = carpeta / "capitulo_03.md"
    capitulo.write_text(texto, encoding="utf-8")
    capitulo.with_suffix(".contexto.json").write_text(
        json.dumps(CONTEXTO, ensure_ascii=False), encoding="utf-8"
    )
    informe = revisar_fichero(capitulo)
    return sorted((i.validador, i.mensaje) for i in informe.incidencias)


@pytest.mark.parametrize("texto", [LIMPIO, SUCIO], ids=["capitulo_limpio", "capitulo_sucio"])
def test_el_mismo_capitulo_da_el_mismo_veredicto_por_los_dos_caminos(
    texto: str, tmp_path: Path
) -> None:
    assert _por_el_nodo(texto) == _por_el_hook(texto, tmp_path)


def test_el_capitulo_sucio_destapa_las_tres_cosas(tmp_path: Path) -> None:
    """Sin esto, la prueba anterior pasaria tambien con dos caminos que no detectan nada."""
    validadores = {v for v, _ in _por_el_hook(SUCIO, tmp_path)}
    assert validadores == {"nombres_exactos", "anacronismo_fechado", "guardrail_prohibidas"}


def test_el_capitulo_limpio_no_levanta_nada(tmp_path: Path) -> None:
    assert _por_el_hook(LIMPIO, tmp_path) == []


def test_sin_contexto_el_hook_cae_a_los_valores_por_defecto(tmp_path: Path) -> None:
    """Un capitulo suelto sin su JSON no revienta: se valida con lo que no necesita contexto.

    Sin canon ni prohibidas no hay nada contra lo que comparar esos dos, pero el rango de
    palabras si tiene un valor por defecto —el de §19— y se aplica. Es lo razonable: un
    fichero que alguien valida a mano sin declarar nada sigue siendo un capitulo de novela.
    """
    capitulo = tmp_path / "suelto.md"
    capitulo.write_text(SUCIO, encoding="utf-8")
    informe = revisar_fichero(capitulo)
    validadores = {i.validador for i in informe.incidencias}
    assert validadores == {"longitud_capitulo"}


def test_el_contexto_json_se_traduce_a_los_tipos_del_core_domain() -> None:
    contexto = contexto_desde_json(CONTEXTO)
    assert contexto["prohibidas"][0].normalizado == "beatriz"
    assert contexto["entidades_fechadas"][0].fecha_inicio == "1844"
    assert contexto["rango_palabras"] == (5, 40)
