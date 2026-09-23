"""spec: §3.2, §7.1 nº 18 · arq: §9, §11d, §11e

`identidad_nodo_accion`: **el grafo y el modelo son la misma máquina, o la prueba cae.**

La correspondencia de §9 es una lista de identidades, no una narración, y esta prueba es lo
que la sostiene. Compara dos cosas, y la segunda es la que de verdad importa:

1. **Los nombres.** El conjunto de nodos del grafo y el de estados de `harness.tla`.
2. **Las aristas.** Un grafo con los veinticuatro estados bien nombrados y el cableado
   equivocado pasaría una comparación de nombres sin parecerse en nada al modelo que TLC
   verificó, porque lo que TLC explora son transiciones.

La relación no se extrae parseando las guardas de cada acción, que estarían desparramadas
por el modelo: la especificación la declara en la definición `Aristas`, **que gobierna el
`Next`**. Leerla desde aquí es entonces trivial y no puede divergir de lo verificado.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from storymaker.commons.graph.aristas import ARISTAS, destinos_de
from storymaker.commons.graph.nodos import GATES, NODOS, TERMINALES

MODELO = Path(__file__).resolve().parents[3] / "formal" / "tla" / "harness.tla"

_PAR = re.compile(r'<<"(\w+)",\s*"(\w+)">>')


def _texto_entre(documento: str, desde: str, hasta: str) -> str:
    inicio = documento.index(desde)
    return documento[inicio : documento.index(hasta, inicio)]


def aristas_del_modelo() -> frozenset[tuple[str, str]]:
    documento = MODELO.read_text(encoding="utf-8")
    bloque = _texto_entre(documento, "Aristas ==", "Estados ==")
    return frozenset(_PAR.findall(bloque))


def estados_del_modelo() -> frozenset[str]:
    documento = MODELO.read_text(encoding="utf-8")
    bloque = _texto_entre(documento, "Estados ==", "Terminales ==")
    return frozenset(re.findall(r'"(\w+)"', bloque))


def terminales_del_modelo() -> frozenset[str]:
    documento = MODELO.read_text(encoding="utf-8")
    bloque = _texto_entre(documento, "Terminales ==", "(****")
    return frozenset(re.findall(r'"(\w+)"', bloque))


class TestNombres:
    def test_el_modelo_existe_y_se_puede_leer(self) -> None:
        """Un parser roto compararia dos conjuntos vacios y pareceria una buena noticia."""
        assert MODELO.exists(), f"no hay especificacion en {MODELO}"
        assert len(estados_del_modelo()) > 20

    def test_los_nodos_del_grafo_son_los_estados_del_modelo(self) -> None:
        assert set(NODOS) == estados_del_modelo(), (
            "El grafo y el modelo no tienen los mismos nodos. Si alguien anadio un nodo sin "
            "anadir su accion, un contraejemplo de TLC dejaria de leerse como una secuencia "
            "de nodos reales."
        )

    def test_los_terminales_coinciden(self) -> None:
        assert TERMINALES == terminales_del_modelo()

    def test_cada_nodo_declara_donde_vive_su_implementacion(self) -> None:
        for nombre, ruta in NODOS.items():
            modulo, separador, simbolo = ruta.partition(":")
            assert separador == ":", f"{nombre} no declara el simbolo"
            assert modulo.startswith("storymaker."), f"{nombre} apunta fuera del paquete"
            assert simbolo.isidentifier(), f"{nombre} declara un simbolo que no es un nombre"

    def test_los_cuatro_gates_comparten_implementacion(self) -> None:
        """Cuatro estados distintos del modelo, un solo nodo: lo que hacen es identico."""
        rutas = {NODOS[gate] for gate in GATES}
        assert len(rutas) == 1
        assert set(GATES) <= set(NODOS)


class TestAristas:
    def test_la_relacion_de_transicion_es_la_misma(self) -> None:
        """Lo que TLC explora son transiciones, no nombres."""
        del_modelo = aristas_del_modelo()
        assert ARISTAS == del_modelo, (
            "El cableado del grafo no coincide con la definicion `Aristas` que gobierna el "
            f"`Next`. Sobran en el codigo: {sorted(ARISTAS - del_modelo)}. "
            f"Faltan: {sorted(del_modelo - ARISTAS)}."
        )

    def test_repair_tiene_dos_aristas_de_entrada(self) -> None:
        """Es la razon de que `Extract` sea accion propia y de que `RetriesBounded` exista."""
        entradas = {a for a, b in ARISTAS if b == "Repair"}
        assert entradas == {"Validate", "Extract"}

    def test_no_hay_vuelta_desde_checkpoint_a_repair(self) -> None:
        """Por eso el extractor corre **antes** de aprobar: despues no tendria adonde ir."""
        assert "Repair" not in destinos_de("Checkpoint")
        assert "Repair" not in destinos_de("ApproveChapter")

    def test_de_los_terminales_no_sale_nada(self) -> None:
        for terminal in TERMINALES:
            assert destinos_de(terminal) == frozenset()

    def test_idle_no_es_terminal(self) -> None:
        """Una novela publicada sigue viva: de ahi salen la Fase 6 y la ramificacion."""
        assert destinos_de("Idle") == {"RequestChange", "Branch"}

    def test_toda_arista_une_dos_nodos_declarados(self) -> None:
        for desde, hasta in ARISTAS:
            assert desde in NODOS, f"{desde} no es un nodo"
            assert hasta in NODOS, f"{hasta} no es un nodo"

    def test_todo_nodo_es_alcanzable_desde_configure(self) -> None:
        """Un nodo inalcanzable es una accion que TLC nunca explora: peor que no tenerla."""
        alcanzados = {"Configure"}
        frontera = ["Configure"]
        while frontera:
            actual = frontera.pop()
            for destino in destinos_de(actual):
                if destino not in alcanzados:
                    alcanzados.add(destino)
                    frontera.append(destino)
        assert alcanzados == set(NODOS), f"inalcanzables: {sorted(set(NODOS) - alcanzados)}"


class TestDiscrepanciaConocida:
    def test_abortar_solo_esta_declarado_en_el_gate_de_intake(self) -> None:
        """Hallazgo abierto, fijado aqui para que no se olvide.

        §10 de la arquitectura ofrece «abortar» como una de las cuatro decisiones de los
        cinco gates, y el modelo solo declara la arista desde `AwaitApproval`. Mientras eso
        no se resuelva arriba, el codigo no se inventa la transicion: revienta.

        Se resuelve de una de dos maneras, y las dos son del Autor: o `Aristas` gana tres
        pares y se vuelve a pasar TLC, o §10 dice que abortar solo cabe en el primer gate.
        """
        con_salida_a_fail = {a for a, b in ARISTAS if b == "Fail"}
        assert "AwaitApproval" in con_salida_a_fail
        assert not ({"AwaitApproval2", "AwaitApproval3", "AwaitApproval4"} & con_salida_a_fail)


@pytest.mark.parametrize("nodo", sorted(NODOS))
def test_todo_nodo_o_tiene_salida_o_es_terminal(nodo: str) -> None:
    assert destinos_de(nodo) or nodo in TERMINALES
