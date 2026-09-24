"""spec: §3.6 · arq: §7

`firmeza(estado, respaldo, origen)`, por **enumeración exhaustiva**.

El dominio es finito —cuatro estados, cuatro respaldos, tres orígenes—, así que recorrerlo
entero no es una muestra: es la demostración de que la función hace lo que la tabla de §7
de la arquitectura dice, para toda entrada posible. Lo esperado se escribe aquí a mano,
fila a fila de esa tabla, y no se deriva de la propia función, que sería comprobarla
contra sí misma.
"""

from __future__ import annotations

import itertools

import pytest

from storymaker.commons.validation.puras import ORDEN_DE_FIRMEZA, anadido_vigente, firmeza

ESTADOS = ("verificado", "debatido", "inferido", "desconocido")
RESPALDOS = ("pendiente", "respaldado", "no_respaldado", "no_aplica")
ORIGENES = ("investigacion_inicial", "micro_arquitecto", "invencion_autorizada")

#: La tabla de arq. §7 para lo que no es invención: estado declarado → respaldo → firmeza.
TABLA = {
    "verificado": {
        "respaldado": "documentado",
        "pendiente": "inferido",
        "no_respaldado": "inferido",
        "no_aplica": "inferido",
    },
    "debatido": {
        "respaldado": "debatido",
        "pendiente": "inferido",
        "no_respaldado": "inferido",
        "no_aplica": "inferido",
    },
    "inferido": {r: "inferido" for r in RESPALDOS},
    "desconocido": {r: "desconocido" for r in RESPALDOS},
}


@pytest.mark.parametrize(
    ("estado", "respaldo", "origen"), list(itertools.product(ESTADOS, RESPALDOS, ORIGENES))
)
def test_las_cuarenta_y_ocho_combinaciones(estado: str, respaldo: str, origen: str) -> None:
    esperada = "inventado" if origen == "invencion_autorizada" else TABLA[estado][respaldo]
    assert firmeza(estado, respaldo, origen) == esperada


@pytest.mark.parametrize(("respaldo", "origen"), list(itertools.product(RESPALDOS, ORIGENES)))
def test_una_cita_floja_nunca_sube_de_categoria(respaldo: str, origen: str) -> None:
    """La degradación anterior convertía un `desconocido` sin respaldo en `inferido`."""
    for estado in ESTADOS:
        obtenida = firmeza(estado, respaldo, origen)
        if obtenida == "inventado":
            continue
        declarada = TABLA[estado]["respaldado"]
        assert ORDEN_DE_FIRMEZA.index(obtenida) >= ORDEN_DE_FIRMEZA.index(declarada)


def test_un_estado_que_no_reconoce_cuenta_como_desconocido() -> None:
    assert firmeza("dudoso", "respaldado", "investigacion_inicial") == "desconocido"


class TestAnadidoVigente:
    """Lo que no dice la cita se enseña mientras siga en el enunciado."""

    def test_sigue_en_el_enunciado(self) -> None:
        enunciado = "El Congreso se celebró en 1888, donde se fundó la UGT"
        assert anadido_vigente(enunciado, "donde se fundó la UGT") == "donde se fundó la UGT"

    def test_una_tilde_o_una_mayuscula_no_lo_dan_por_desaparecido(self) -> None:
        enunciado = "El Congreso se celebró en 1888, donde se fundó la UGT"
        assert anadido_vigente(enunciado, "Donde se fundo la ugt") == "Donde se fundo la ugt"

    def test_si_el_autor_lo_quito_ya_no_se_ensena(self) -> None:
        assert anadido_vigente("El Congreso se celebró en 1888", "donde se fundó la UGT") is None

    @pytest.mark.parametrize("vacio", [None, "", "  ", "¡!"])
    def test_sin_anadido_no_hay_nada(self, vacio: str | None) -> None:
        assert anadido_vigente("cualquier cosa", vacio) is None

    @pytest.mark.parametrize(
        ("enunciado", "anadido"),
        [
            # Los cuatro parciales de la primera novela exhaustiva que no enseñaban su nota.
            (
                "El Parque de la Ciudadela fue completamente urbanizado para la Exposición "
                "Universal de 1888.",
                "para la Exposición de 1888",
            ),
            ("Se construyó un Monumento a Colón en Barcelona durante 1887-1888.", "en 1887-1888"),
            ("Nuevos lugares de ocio surgieron en Barcelona durante 1887-1888.", "en 1887-1888"),
        ],
    )
    def test_copiado_con_otras_palabras_sigue_contando(self, enunciado: str, anadido: str) -> None:
        assert anadido_vigente(enunciado, anadido) == anadido

    def test_una_palabra_significativa_que_falta_lo_da_por_quitado(self) -> None:
        enunciado = "El Parque de la Ciudadela fue urbanizado para la Exposición"
        assert anadido_vigente(enunciado, "para la Exposición de 1888") is None
