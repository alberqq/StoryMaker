"""spec: §7.1 nº 20 · arq: §11e

`registro_de_validadores`: **la comprobación que bloquea de la familia de correspondencia.**

Compara tres tablas por pares —el `REGISTRO` del código, la de §11a de la arquitectura y la
de §7.2 de la spec del backend— y exige que coincidan en conjunto, en punto de ejecución y
en condición de bloqueo.

Se comparan tres y no dos porque los mismos validadores están descritos en los dos
documentos y la arquitectura es la fuente de verdad de ambos: confrontar solo el registro
contra la spec dejaría a §11a derivar en silencio.

Y bloquea porque **un validador que deja de bloquear en silencio destruye la confianza en
todos los demás**: la suite seguiría en verde, los capítulos se aprobarían y nadie se
enteraría hasta leer la novela.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storymaker.commons.validation.registro import REGISTRO, Punto

RAIZ = Path(__file__).resolve().parents[3]
ARQUITECTURA = RAIZ / "docs" / "architecture.md"
SPEC = RAIZ / "specs" / "backend" / "spec.md"

#: Cómo se dice cada punto de ejecución en los documentos. La prosa manda en el documento;
#: aquí solo se reconoce, y por eso el emparejamiento va por palabras clave y no por
#: igualdad literal: exigir la cadena exacta convertiría una mejora de redacción en un
#: fallo de CI.
PISTAS: dict[Punto, tuple[str, ...]] = {
    Punto.SALIDA_DE_NODO_AGENTE: ("salida de cada nodo",),
    Punto.POST_WRITE_CHAPTER: ("post `writechapter`", "post writechapter"),
    Punto.POST_EXTRACT: ("post `extract`", "post extract"),
    Punto.GATE_PLOTTING: ("gate de plotting",),
    Punto.GATE_WRITING: ("gate de writing",),
    Punto.PUBLISH_VERSION: ("publishversion",),
}


def _punto_de(texto: str) -> Punto | None:
    minusculas = texto.lower()
    for punto, pistas in PISTAS.items():
        if any(pista in minusculas for pista in pistas):
            return punto
    return None


def _filas_de_tabla(documento: str, titulo: str, siguiente: str) -> list[list[str]]:
    """Las filas de la tabla que hay entre dos encabezados."""
    inicio = documento.index(titulo)
    fin = documento.index(siguiente, inicio)
    filas = []
    for linea in documento[inicio:fin].splitlines():
        if not linea.startswith("|") or set(linea) <= set("|- "):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if celdas and celdas[0].startswith("`"):
            filas.append(celdas)
    return filas


def _nombre(celda: str) -> str:
    return celda.strip("`").strip()


def _tabla_de_la_arquitectura() -> dict[str, Punto | None]:
    documento = ARQUITECTURA.read_text(encoding="utf-8")
    filas = _filas_de_tabla(documento, "### a) Programáticos (deterministas)", "### b) Semánticos")
    return {_nombre(f[0]): _punto_de(f[2]) for f in filas if len(f) >= 3}


def _tabla_de_la_spec() -> dict[str, tuple[Punto | None, bool]]:
    documento = SPEC.read_text(encoding="utf-8")
    filas = _filas_de_tabla(
        documento, "#### a) Programáticos — deterministas, coste cero", "#### b) Semánticos"
    )
    tabla = {}
    for fila in filas:
        if len(fila) < 6:
            continue
        bloquea = fila[5].strip().lower().startswith(("sí", "si"))
        tabla[_nombre(fila[0])] = (_punto_de(fila[2]), bloquea)
    return tabla


class TestTresTablasPorPares:
    def test_el_registro_y_la_arquitectura_tienen_los_mismos_validadores(self) -> None:
        arquitectura = _tabla_de_la_arquitectura()
        assert set(REGISTRO) == set(arquitectura), (
            "El registro y §11a de la arquitectura no describen los mismos validadores. "
            "La arquitectura manda: si el codigo tiene uno de mas, sobra; si le falta uno, "
            "es una decision fijada que nadie implemento."
        )

    def test_la_spec_y_la_arquitectura_tampoco_divergen(self) -> None:
        assert set(_tabla_de_la_spec()) == set(_tabla_de_la_arquitectura())

    @pytest.mark.parametrize("nombre", sorted(REGISTRO))
    def test_cada_validador_corre_donde_dicen_los_documentos(self, nombre: str) -> None:
        arquitectura = _tabla_de_la_arquitectura()
        declarado = arquitectura.get(nombre)
        if declarado is None:
            pytest.skip(f"§11a describe el punto de {nombre} en prosa que no se reconoce")
        assert REGISTRO[nombre].punto is declarado, (
            f"{nombre} corre en {REGISTRO[nombre].punto} y la arquitectura lo situa en "
            f"{declarado}."
        )

    @pytest.mark.parametrize("nombre", sorted(REGISTRO))
    def test_la_condicion_de_bloqueo_coincide_con_la_spec(self, nombre: str) -> None:
        spec = _tabla_de_la_spec()
        if nombre not in spec:
            pytest.skip(f"{nombre} no aparece en §7.2a de la spec")
        _, bloquea = spec[nombre]
        assert REGISTRO[nombre].bloquea is bloquea, (
            f"{nombre} {'bloquea' if REGISTRO[nombre].bloquea else 'no bloquea'} en el codigo "
            f"y la spec dice lo contrario. Un validador que deja de bloquear en silencio "
            f"destruye la confianza en todos los demas."
        )


class TestRutasDelRegistro:
    """Aqui se comprueba la **forma** de la ruta, no que el fichero exista todavia.

    Que el modulo este escrito es cosa del inventario, que informa en dos cubos: mientras
    el plan se ejecuta, la mayoria de los items aun no existen —`render_visual` vive en H6—
    y convertir eso en un fallo de CI dejaria la puerta en rojo durante meses por el estado
    normal del proyecto.
    """

    @pytest.mark.parametrize("nombre", sorted(REGISTRO))
    def test_la_ruta_esta_bien_formada(self, nombre: str) -> None:
        modulo, separador, simbolo = REGISTRO[nombre].ruta.partition(":")
        assert separador == ":", f"{nombre} no declara el simbolo dentro del modulo"
        assert modulo.startswith("storymaker."), f"{nombre} apunta fuera del paquete"
        assert simbolo.isidentifier(), f"{nombre} declara un simbolo que no es un nombre"
