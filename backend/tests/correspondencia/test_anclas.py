"""spec: §7.1 nº 22 · arq: §11e

`anclas_de_procedencia`: cada módulo dice de qué apartado nace, y cada apartado tiene quien
lo implemente.

La convención es una línea, la primera del docstring del módulo: `spec: §3.6 · arq: §11a`.
Cuesta nada escribirla y permite dos comprobaciones que ninguna otra cosa hace.

**Las dos direcciones importan, y la segunda es la que no suele escribirse.** Comprobar que
cada símbolo apunta a un apartado existente detecta el documento que se quedó atrás.
Comprobar que cada apartado tiene quien lo implemente detecta lo contrario: lo que se
especificó, se dio por hecho y nunca se escribió. Es la única comprobación del proyecto
capaz de señalar una **ausencia**, y una ausencia es justamente lo que ninguna suite puede
ver, porque nadie escribe la prueba de un código que no existe.

El alcance de esa segunda dirección se declara para que no sea una exigencia difusa: **§3 y
§4 de la spec**, que son sus contratos y sus fases. El resto del documento es prosa de
justificación y no se le pide implementación.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
FUENTE = RAIZ / "backend" / "src" / "storymaker"
SPEC = RAIZ / "specs" / "backend" / "spec.md"
ARQUITECTURA = RAIZ / "docs" / "architecture.md"

_ANCLA = re.compile(r"^spec:\s*(§[\w.]+(?:,\s*§[\w.]+)*)\s*·\s*arq:\s*(§[\w.]+(?:,\s*§[\w.]+)*)")
_APARTADO_SPEC = re.compile(r"^###\s+(\d+\.\d+)\s", re.MULTILINE)


def _modulos() -> list[Path]:
    return sorted(p for p in FUENTE.rglob("*.py") if p.name != "__init__.py")


def _ancla_de(ruta: Path) -> re.Match[str] | None:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    documentacion = ast.get_docstring(arbol)
    if not documentacion:
        return None
    return _ANCLA.match(documentacion.strip().splitlines()[0].strip())


def _existe(apartado: str, documento: str) -> bool:
    """¿Está ese apartado en el documento?

    Acepta tres formas porque los documentos usan tres: el encabezado (`## 11`), la
    referencia en prosa (`§11a`) y la subsección con letra, que en el documento es un
    encabezado propio —`### b) Semánticos`— y no lleva el número delante. Exigir la forma
    literal convertiría una mejora de redacción en un fallo de CI, que es justo lo que esta
    familia de comprobaciones no debe hacer.
    """
    if f"## {apartado}" in documento or f"§{apartado}" in documento:
        return True
    if apartado and apartado[-1].isalpha():
        numero, letra = apartado[:-1], apartado[-1]
        return f"## {numero}" in documento and f"### {letra})" in documento
    return False


@pytest.mark.parametrize("modulo", _modulos(), ids=lambda p: p.stem)
def test_todo_modulo_declara_de_donde_nace(modulo: Path) -> None:
    """Esta direccion si se exige: escribir la linea cuesta nada y sin ella no hay cotejo."""
    ancla = _ancla_de(modulo)
    assert ancla is not None, (
        f"{modulo.name} no declara su procedencia. La primera linea de su docstring tiene "
        f"que ser del estilo `spec: §3.6 · arq: §11a`."
    )


@pytest.mark.parametrize("modulo", _modulos(), ids=lambda p: p.stem)
def test_los_apartados_citados_existen(modulo: Path) -> None:
    """Un ancla a un apartado que ya no esta es un documento que se quedo atras."""
    ancla = _ancla_de(modulo)
    assert ancla is not None
    spec = SPEC.read_text(encoding="utf-8")
    arquitectura = ARQUITECTURA.read_text(encoding="utf-8")
    for apartado in re.findall(r"§([\w.]+)", ancla.group(1)):
        assert _existe(apartado, spec), (
            f"{modulo.name} cita spec §{apartado}, que no aparece en la spec."
        )
    for apartado in re.findall(r"§([\w.]+)", ancla.group(2)):
        assert _existe(apartado, arquitectura), (
            f"{modulo.name} cita arq §{apartado}, que no aparece en la arquitectura."
        )


def test_cobertura_inversa_de_los_apartados_de_contrato() -> None:
    """Informa: qué apartados de §3 y §4 de la spec no tienen todavía quien los cite.

    No bloquea, por el mismo motivo que el inventario: mientras queden hitos por cerrar, lo
    normal es que falten. Lo que este informe permite es mirarlo **al cerrar cada hito**, que
    es cuando un apartado sin implementar deja de ser trabajo pendiente y pasa a ser un
    olvido.
    """
    apartados = {
        numero
        for numero in _APARTADO_SPEC.findall(SPEC.read_text(encoding="utf-8"))
        if numero.startswith(("3.", "4."))
    }
    citados: set[str] = set()
    for modulo in _modulos():
        ancla = _ancla_de(modulo)
        if ancla is not None:
            citados.update(re.findall(r"§([\w.]+)", ancla.group(1)))

    huerfanos = sorted(apartados - citados)
    print(f"\n[anclas] apartados de contrato sin modulo que los cite: {len(huerfanos)}")
    for apartado in huerfanos:
        print(f"  - spec §{apartado}")
    assert apartados, "no se reconocio ningun apartado de §3 o §4 en la spec"
