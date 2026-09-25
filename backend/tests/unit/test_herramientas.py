"""spec: §3.3 · arq: §5, §12

Pruebas de las herramientas propias del arnés: el cálculo de fechas del arquitecto.

Lo que se comprueba es que **el esquema manda**: una entrada que no lo cumple no llega a
ejecutarse y vuelve al rol como error, con el campo que falla. Y que la concesión es la que
dice la tabla: solo el arquitecto las tiene, con cuota, y ninguna sale a la red.
"""

from __future__ import annotations

import pytest

from storymaker.commons.agents.herramientas import (
    HERRAMIENTAS_PROPIAS,
    EntradaEdad,
    EntradaSumarDias,
    edad_en_fecha,
    ejecutar,
    es_propia,
    sumar_dias,
)
from storymaker.commons.agents.hooks import CuotaDeHerramientas
from storymaker.commons.agents.techos import (
    TECHOS,
    Perfil,
    herramientas_de,
    propias_de,
    turnos_de,
)

SUMAR = "mcp__storymaker__sumar_dias"
EDAD = "mcp__storymaker__edad_en_fecha"


def _texto(resultado: dict[str, object]) -> str:
    return resultado["content"][0]["text"]  # type: ignore[index]


class TestEsquema:
    @pytest.mark.parametrize(
        ("herramienta", "argumentos", "campo"),
        [
            (SUMAR, {"fecha": "1574", "dias": 3}, "fecha"),
            (SUMAR, {"fecha": "1574-03-01", "dias": 10**6}, "dias"),
            (SUMAR, {"fecha": "1574-03-01"}, "dias"),
            (EDAD, {"nacimiento": "hace mucho", "fecha": "1574"}, "nacimiento"),
            (EDAD, {"nacimiento": "1540", "fecha": "1574", "sobra": 1}, "sobra"),
        ],
    )
    def test_lo_que_no_cumple_no_se_ejecuta_y_dice_que_campo_falla(
        self, herramienta: str, argumentos: dict[str, object], campo: str
    ) -> None:
        resultado = ejecutar(herramienta, argumentos)
        assert resultado.get("is_error") is True
        assert campo in _texto(resultado)

    def test_una_fecha_con_forma_pero_inexistente_se_rechaza(self) -> None:
        resultado = ejecutar(SUMAR, {"fecha": "1574-02-30", "dias": 1})
        assert resultado.get("is_error") is True

    def test_una_herramienta_desconocida_es_un_error_y_no_una_excepcion(self) -> None:
        assert ejecutar("mcp__storymaker__nada", {}).get("is_error") is True

    def test_el_esquema_que_ve_el_modelo_sale_del_mismo_modelo_pydantic(self) -> None:
        for herramienta in HERRAMIENTAS_PROPIAS.values():
            esquema = herramienta.json_schema()
            assert esquema == herramienta.esquema.model_json_schema()
            assert esquema["additionalProperties"] is False


class TestCalculo:
    def test_sumar_dias_da_la_fecha_y_el_dia_de_la_semana(self) -> None:
        assert sumar_dias(EntradaSumarDias(fecha="1805-04-11", dias=10)).startswith(
            "1805-04-21 (domingo)"
        )

    def test_antes_de_1582_avisa_del_calendario(self) -> None:
        assert "juliano" in sumar_dias(EntradaSumarDias(fecha="1574-03-01", dias=40))

    @pytest.mark.parametrize(
        ("nacimiento", "fecha", "esperado"),
        [
            ("1540-06-10", "1574-06-10", "34 anos cumplidos"),
            ("1540-06-10", "1574-06-09", "33 anos cumplidos"),
            ("1540-06", "1574-09", "34 anos cumplidos"),
            ("1540", "1574-06", "Entre 33 y 34"),
            ("1580", "1574", "aun no ha nacido"),
            ("1574-08", "1574-03", "aun no ha nacido"),
        ],
    )
    def test_edad_a_la_precision_que_haya(self, nacimiento: str, fecha: str, esperado: str) -> None:
        assert esperado in edad_en_fecha(EntradaEdad(nacimiento=nacimiento, fecha=fecha))


class TestConcesion:
    def test_solo_el_arquitecto_tiene_herramientas_propias(self) -> None:
        assert {p for p in Perfil if propias_de(p)} == {Perfil.ARQUITECTO}
        assert set(propias_de(Perfil.ARQUITECTO)) == set(HERRAMIENTAS_PROPIAS)

    def test_no_cuentan_como_red(self) -> None:
        assert herramientas_de(Perfil.ARQUITECTO) == ()
        assert all(es_propia(h) for h in propias_de(Perfil.ARQUITECTO))

    def test_cada_herramienta_concedida_tiene_cuota(self) -> None:
        cuotas = dict(TECHOS[Perfil.ARQUITECTO].cuota_de_herramientas)
        assert set(cuotas) == set(propias_de(Perfil.ARQUITECTO))

    def test_la_cuota_se_agota(self) -> None:
        cuota = CuotaDeHerramientas.para(Perfil.ARQUITECTO)
        decisiones = [cuota.decidir(SUMAR)["permissionDecision"] for _ in range(5)]
        assert decisiones == ["allow"] * 4 + ["deny"]

    def test_el_arquitecto_tiene_turnos_para_usarlas(self) -> None:
        assert turnos_de(Perfil.ARQUITECTO) > 1


def test_el_servidor_mcp_se_construye_con_el_sdk() -> None:
    pytest.importorskip("claude_agent_sdk")
    from storymaker.commons.agents.herramientas import servidor_mcp

    servidor = servidor_mcp(tuple(HERRAMIENTAS_PROPIAS))
    assert servidor["type"] == "sdk" and servidor["name"] == "storymaker"
