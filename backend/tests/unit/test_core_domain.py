"""spec: §3.6 · arq: §11a, §15

Pruebas del Core Domain: un caso positivo y uno negativo por validador, como exige la
spec, más las propiedades de las funciones puras.

Estas pruebas no abren ninguna base de datos, y eso es parte de lo que comprueban: si un
validador necesitara una conexión para decidir, el hook de `.claude/` no podría ejecutarlo
sobre un capítulo editado a mano y la promesa de «una sola implementación, dos puntos de
ejecución» sería falsa.
"""

from __future__ import annotations

import pytest

from storymaker.commons.validation.chapter_validator import (
    anacronismo_fechado,
    anclaje_valido,
    cobertura_capitulo,
    longitud_capitulo,
    nombres_exactos,
    validar_capitulo,
)
from storymaker.commons.validation.escaleta import (
    arco_anclado,
    cobertura_anclada,
    cobertura_personalizacion,
)
from storymaker.commons.validation.modelos import (
    AnclajeDeEscena,
    ArcoEnRevision,
    CapituloEnRevision,
    EntidadFechada,
    EscaletaEnRevision,
    Severidad,
    TerminoProhibido,
)
from storymaker.commons.validation.policy_checker import (
    guardrail_prohibidas,
    pii_en_prompt_de_investigacion,
    texto_libre_no_filtrado,
)
from storymaker.commons.validation.puras import (
    anio_de,
    capitulos_afectados,
    es_anacronico,
    hay_solape_temporal,
    normalizar,
)
from storymaker.commons.validation.registro import REGISTRO, Punto, bloqueantes, del_punto


def capitulo(**cambios: object) -> CapituloEnRevision:
    base: dict[str, object] = {
        "numero": 2,
        "texto": "Manuel Ferrer conto los cascos del astillero.",
        "palabras": 1200,
        "rango_palabras": (1000, 1500),
    }
    base.update(cambios)
    return CapituloEnRevision(**base)  # type: ignore[arg-type]


class TestFuncionesPuras:
    @pytest.mark.parametrize(
        ("entrada", "esperado"),
        [
            ("Beatriz", "beatriz"),
            ("¡Cádiz!", "cadiz"),
            ("los  toneleros", "los tonelero"),
            ("LAS JARCIAS", "las jarcia"),
        ],
    )
    def test_normalizar_quita_caso_tildes_puntuacion_y_plural(
        self, entrada: str, esperado: str
    ) -> None:
        assert normalizar(entrada) == esperado

    def test_la_singularizacion_es_tosca_a_proposito(self) -> None:
        """No es un lematizador, y no pretende serlo.

        Lo que importa no es la correccion linguistica sino que la aguja y el pajar pasen
        por la **misma** funcion: si los dos lados se normalizan igual, la comparacion es
        consistente aunque la forma resultante no sea una palabra real. Lo que esta
        heuristica no cubre —la parafrasis, la alusion sin nombrar— es el riesgo aceptado
        U-4, y no se arregla alargando esta funcion.
        """
        assert normalizar("BEATRICES") == "beatric"
        assert normalizar("palabras") == normalizar("Palabra")

    def test_anacronico_solo_cuando_hay_las_dos_fechas(self) -> None:
        """Un objeto sin fecha documentada no es un anacronismo: es un dato que no tenemos."""
        assert es_anacronico("1850", "1805") is True
        assert es_anacronico("1790", "1805") is False
        assert es_anacronico(None, "1805") is False
        assert es_anacronico("1850", None) is False

    def test_solape_temporal_con_extremos_abiertos(self) -> None:
        assert hay_solape_temporal("1760", "1820", "1805", "1806") is True
        assert hay_solape_temporal("1760", "1800", "1805", "1806") is False
        assert hay_solape_temporal("1760", None, "1805", None) is True

    #: Los cuatro contraejemplos, escritos por punto de codigo: son justamente caracteres
    #: que se confunden con digitos ASCII a simple vista, y ponerlos literales aqui haria
    #: saltar la regla de caracteres ambiguos de `ruff` sobre el fichero que los estudia.
    DIGITOS_ENGANOSOS = (
        "05" + chr(0x07C0) + chr(0x2474),          # NKO DIGIT ZERO, PARENTHESIZED DIGIT ONE
        "0" + chr(0x07C0) + chr(0x2776) + chr(0x11D50),  # DINGBAT ONE, MASARAM GONDI ZERO
        "099" + chr(0x2080),                        # SUBSCRIPT ZERO
        chr(0xFF11) + chr(0xFF18) + chr(0xFF10) + chr(0xFF10),  # digitos de ancho completo
    )

    @pytest.mark.parametrize("fecha", DIGITOS_ENGANOSOS)
    def test_una_fecha_con_digitos_raros_devuelve_none_y_no_revienta(self, fecha: str) -> None:
        """Contraejemplo de CrossHair, convertido en caso de prueba (verif. §3.3).

        `isdigit()` acepta el uno entre parentesis, los subindices y los digitos de otros
        sistemas de escritura; `int()` rechaza varios de ellos. Con la comprobacion anterior
        la funcion **dejaba de ser total**: una fecha rara reventaba dentro del validador,
        a mitad de capitulo, en lugar de devolver `None` como promete su contrato.
        """
        assert anio_de(fecha) is None
        assert es_anacronico(fecha, "1805") is False
        assert hay_solape_temporal(None, None, fecha, None) is True

    def test_capitulos_afectados_devuelve_orden_creciente(self) -> None:
        """Regenerar del 9 al 2 dejaria al 9 escrito contra una continuidad que el 2 cambia."""
        assert capitulos_afectados({7: (9, 2, 5)}, 7) == [2, 5, 9]
        assert capitulos_afectados({}, 7) == []


class TestValidadoresDeCapitulo:
    def test_nombres_exactos_pasa_con_la_grafia_del_canon(self) -> None:
        incidencias = nombres_exactos(capitulo(nombres_canonicos=("Manuel Ferrer",)))
        assert incidencias == []

    def test_nombres_exactos_salta_con_otra_grafia(self) -> None:
        """La novela es un regalo: un nombre mal escrito la estropea entera."""
        incidencias = nombres_exactos(
            capitulo(texto="manuel ferrer conto los cascos.", nombres_canonicos=("Manuel Ferrer",))
        )
        assert len(incidencias) == 1
        assert incidencias[0].propuesta == "Manuel Ferrer"
        assert incidencias[0].bloquea

    def test_longitud_dentro_del_rango(self) -> None:
        assert longitud_capitulo(capitulo(palabras=1200)) == []

    def test_longitud_fuera_del_rango(self) -> None:
        assert len(longitud_capitulo(capitulo(palabras=600))) == 1
        assert len(longitud_capitulo(capitulo(palabras=2000))) == 1

    def test_anacronismo_con_objeto_posterior(self) -> None:
        incidencias = anacronismo_fechado(
            capitulo(
                texto="Saco el telegrafo del bolsillo.",
                fecha_narrativa="1805-04-11",
                entidades_fechadas=(EntidadFechada("telegrafo", "1844"),),
            )
        )
        assert len(incidencias) == 1
        assert "1844" in incidencias[0].mensaje

    def test_sin_anacronismo_si_ya_existia(self) -> None:
        incidencias = anacronismo_fechado(
            capitulo(
                texto="Saco el catalejo del bolsillo.",
                fecha_narrativa="1805-04-11",
                entidades_fechadas=(EntidadFechada("catalejo", "1608"),),
            )
        )
        assert incidencias == []

    def test_anclaje_a_hecho_sellado(self) -> None:
        incidencias = anclaje_valido(
            capitulo(anclajes=(AnclajeDeEscena(1, hecho_id=7),), hechos_sellados=frozenset({7}))
        )
        assert incidencias == []

    def test_anclaje_a_hecho_inexistente(self) -> None:
        """Un detalle inventado que viviera solo en la cabeza del arquitecto tumba esto."""
        incidencias = anclaje_valido(
            capitulo(anclajes=(AnclajeDeEscena(1, hecho_id=7),), hechos_sellados=frozenset())
        )
        assert len(incidencias) == 1

    def test_anclaje_cubierto_por_una_licencia_declarada(self) -> None:
        incidencias = anclaje_valido(
            capitulo(
                anclajes=(AnclajeDeEscena(1, hecho_id=7),),
                hechos_sellados=frozenset(),
                licencias_declaradas=frozenset({7}),
            )
        )
        assert incidencias == []

    def test_cobertura_del_capitulo(self) -> None:
        completo = capitulo(
            personalizacion_encomendada=(3, 4), personalizacion_usada=frozenset({3, 4})
        )
        incompleto = capitulo(
            personalizacion_encomendada=(3, 4), personalizacion_usada=frozenset({3})
        )
        assert cobertura_capitulo(completo) == []
        assert len(cobertura_capitulo(incompleto)) == 1

    def test_la_pasada_determinista_acumula(self) -> None:
        incidencias = validar_capitulo(
            capitulo(palabras=100, nombres_canonicos=("Manuel Ferrer",), texto="manuel ferrer.")
        )
        validadores = {i.validador for i in incidencias}
        assert validadores == {"longitud_capitulo", "nombres_exactos"}


class TestPolicy:
    def test_prohibida_exacta(self) -> None:
        incidencias = guardrail_prohibidas(
            capitulo(
                texto="Se llamaba Beatriz y no volvio.",
                prohibidas=(TerminoProhibido("destinatario", "Beatriz", "beatriz"),),
            )
        )
        assert len(incidencias) == 1

    @pytest.mark.parametrize("variante", ["BEATRIZ", "beatriz,", "Beátriz"])
    def test_prohibida_con_variantes(self, variante: str) -> None:
        """Una lista que solo casa la forma exacta no detecta nada."""
        incidencias = guardrail_prohibidas(
            capitulo(
                texto=f"Se llamaba {variante} y no volvio.",
                prohibidas=(TerminoProhibido("destinatario", "Beatriz", "beatriz"),),
            )
        )
        assert len(incidencias) == 1

    def test_no_salta_dentro_de_otra_palabra(self) -> None:
        """Buscar la subcadena haria que «asa» saltara dentro de «casa»."""
        incidencias = guardrail_prohibidas(
            capitulo(
                texto="Entro en la casa con la jarra.",
                prohibidas=(TerminoProhibido("global", "asa", "asa"),),
            )
        )
        assert incidencias == []

    def test_texto_en_cuarentena_que_llega_al_prompt(self) -> None:
        crudo = "Mi padre siempre decia que el mar no perdona a los impacientes"
        assert len(texto_libre_no_filtrado(f"Escribe esto: {crudo}", [crudo])) == 1
        assert texto_libre_no_filtrado("Escribe el capitulo 2.", [crudo]) == []

    def test_pii_en_el_prompt_del_investigador(self) -> None:
        """El investigador es el unico rol con red: por ahi no salen datos personales."""
        incidencias = pii_en_prompt_de_investigacion(
            "Investiga Cadiz en 1805 para Manuel Ferrer", ["Manuel Ferrer"]
        )
        assert len(incidencias) == 1
        assert pii_en_prompt_de_investigacion("Investiga Cadiz en 1805", ["Manuel Ferrer"]) == []


class TestEscaleta:
    def test_cobertura_anclada(self) -> None:
        completa = EscaletaEnRevision(
            n_capitulos=10, obligatorios=(1, 2), obligatorios_anclados=frozenset({1, 2})
        )
        incompleta = EscaletaEnRevision(
            n_capitulos=10, obligatorios=(1, 2), obligatorios_anclados=frozenset({1})
        )
        assert cobertura_anclada(completa) == []
        assert len(cobertura_anclada(incompleta)) == 1

    def test_un_personaje_de_dos_escenas_no_necesita_arco(self) -> None:
        """Con tres escenas de minimo se recoge a quien recurre, no a quien cruza una taberna."""
        escaleta = EscaletaEnRevision(
            n_capitulos=10,
            apariciones_por_personaje={5: 2},
            nombres_por_personaje={5: "El aguador"},
        )
        assert arco_anclado(escaleta) == []

    def test_un_personaje_recurrente_sin_arco_salta(self) -> None:
        escaleta = EscaletaEnRevision(
            n_capitulos=10,
            apariciones_por_personaje={5: 4},
            nombres_por_personaje={5: "Tomasa"},
        )
        incidencias = arco_anclado(escaleta)
        assert len(incidencias) == 1
        assert "plano" in incidencias[0].mensaje, "se le ofrece la salida barata"

    def test_el_arco_plano_cuenta(self) -> None:
        """Pedirle transformacion al tabernero seria mala literatura impuesta por un validador."""
        escaleta = EscaletaEnRevision(
            n_capitulos=10,
            apariciones_por_personaje={5: 4},
            nombres_por_personaje={5: "Tomasa"},
            arcos=(ArcoEnRevision(5, "Tomasa", "plano"),),
        )
        assert arco_anclado(escaleta) == []

    def test_un_arco_positivo_necesita_dos_hitos(self) -> None:
        escaleta = EscaletaEnRevision(
            n_capitulos=10,
            apariciones_por_personaje={5: 4},
            nombres_por_personaje={5: "Tomasa"},
            arcos=(ArcoEnRevision(5, "Tomasa", "positivo", hitos_por_capitulo=(3,)),),
        )
        assert len(arco_anclado(escaleta)) == 1

    def test_los_hitos_van_en_capitulos_crecientes(self) -> None:
        escaleta = EscaletaEnRevision(
            n_capitulos=10,
            apariciones_por_personaje={5: 4},
            nombres_por_personaje={5: "Tomasa"},
            arcos=(ArcoEnRevision(5, "Tomasa", "positivo", hitos_por_capitulo=(7, 3)),),
        )
        incidencias = arco_anclado(escaleta)
        assert len(incidencias) == 1
        assert "hacia atras" in incidencias[0].mensaje

    def test_el_homenajeado_no_puede_ser_plano(self) -> None:
        escaleta = EscaletaEnRevision(
            n_capitulos=10,
            apariciones_por_personaje={1: 9},
            nombres_por_personaje={1: "Manuel Ferrer"},
            arcos=(ArcoEnRevision(1, "Manuel Ferrer", "plano", es_homenajeado=True),),
        )
        incidencias = arco_anclado(escaleta)
        assert any("la novela es para el" in i.mensaje for i in incidencias)

    def test_el_homenajeado_cierra_en_el_tercio_final(self) -> None:
        temprano = EscaletaEnRevision(
            n_capitulos=10,
            apariciones_por_personaje={1: 9},
            nombres_por_personaje={1: "Manuel Ferrer"},
            arcos=(
                ArcoEnRevision(
                    1, "Manuel Ferrer", "positivo", hitos_por_capitulo=(2, 5), es_homenajeado=True
                ),
            ),
        )
        a_tiempo = EscaletaEnRevision(
            n_capitulos=10,
            apariciones_por_personaje={1: 9},
            nombres_por_personaje={1: "Manuel Ferrer"},
            arcos=(
                ArcoEnRevision(
                    1, "Manuel Ferrer", "positivo", hitos_por_capitulo=(2, 9), es_homenajeado=True
                ),
            ),
        )
        assert any("tercio final" in i.mensaje for i in arco_anclado(temprano))
        assert arco_anclado(a_tiempo) == []

    def test_cobertura_personalizacion_como_red_de_seguridad(self) -> None:
        """Anclar no es escribir, y escribir el capitulo N no cubre a los demas."""
        assert cobertura_personalizacion((1, 2), frozenset({1, 2})) == []
        assert len(cobertura_personalizacion((1, 2), frozenset({1}))) == 1


class TestRegistro:
    def test_estan_los_once_validadores_de_la_arquitectura(self) -> None:
        assert len(REGISTRO) == 11
        assert set(REGISTRO) == {
            "schema_guard",
            "nombres_exactos",
            "longitud_capitulo",
            "guardrail_prohibidas",
            "anacronismo_fechado",
            "anclaje_valido",
            "cobertura_anclada",
            "arco_anclado",
            "cobertura_capitulo",
            "cobertura_personalizacion",
            "render_visual",
        }

    def test_los_once_bloquean(self) -> None:
        """Los que no bloquean son los semanticos, y esos no tienen fila aqui."""
        assert len(bloqueantes()) == 11

    def test_la_pasada_determinista_sale_del_registro(self) -> None:
        """Nadie compone una pasada con una lista propia: se filtra el cableado."""
        nombres = {e.nombre for e in del_punto(Punto.POST_WRITE_CHAPTER)}
        assert nombres == {
            "nombres_exactos",
            "longitud_capitulo",
            "guardrail_prohibidas",
            "anacronismo_fechado",
            "anclaje_valido",
        }

    def test_el_gate_de_plotting_tiene_sus_dos(self) -> None:
        assert {e.nombre for e in del_punto(Punto.GATE_PLOTTING)} == {
            "cobertura_anclada",
            "arco_anclado",
        }

    def test_la_ruta_es_una_cadena_y_no_un_import(self) -> None:
        """Es lo que permite registrar `render_visual`, que conduce un navegador, sin
        que el Core Domain importe nada de fuera."""
        entrada = REGISTRO["render_visual"]
        assert entrada.ruta == "storymaker.publication.render:render_visual"
        assert entrada.punto is Punto.PUBLISH_VERSION

    def test_ninguna_severidad_se_inventa(self) -> None:
        assert {s for s in Severidad} == {Severidad.BLOQUEANTE, Severidad.AVISO}
