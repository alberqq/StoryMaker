"""spec: §3.3 · arq: §12, verif. §3.6

La propiedad de la que cuelga el presupuesto de contexto: **el grafo es secuencial, así que
el peor caso es un solo agente abierto**.

Esa frase es lo que permite garantizar los 100.000 tokens concurrentes con una suma en lugar
de con una medición. Y como el Agent SDK no ofrece forma documentada de consultar cuánto
contexto lleva consumido una sesión mientras corre, la suma es lo único que hay — de modo
que si la premisa dejara de ser cierta, el método entero dejaría de serlo sin que nada se
quejara.

Aquí se comprueban las dos mitades: que **ningún techo declarado supera el límite del
sistema**, y que **la suma de cualquier conjunto de sesiones que pudieran solaparse cabe**.
Hoy no se solapa ninguna; el día que las micro-sesiones del arquitecto se paralelicen, esta
prueba es la que dirá cuántas caben.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from storymaker.commons.agents.techos import PEOR_CASO_DEL_SISTEMA, TECHOS, Perfil
from storymaker.commons.config import Defaults

perfiles = st.sampled_from(list(Perfil))


class TestTechoDelSistema:
    def test_ningun_rol_supera_por_si_solo_el_limite(self) -> None:
        """Un rol cuyo techo pasara de 100.000 haria imposible el metodo entero."""
        for perfil, techo in TECHOS.items():
            assert techo.total <= Defaults.TOKENS_CONCURRENTES_MAXIMOS, perfil

    def test_el_peor_caso_es_el_investigador_inicial(self) -> None:
        """Es el unico rol que mete paginas enteras en su ventana, y tres veces."""
        assert PEOR_CASO_DEL_SISTEMA == TECHOS[Perfil.INVESTIGADOR_INICIAL].total
        assert PEOR_CASO_DEL_SISTEMA == max(t.total for t in TECHOS.values())

    def test_en_serie_siempre_cabe(self) -> None:
        """El grafo es secuencial: el peor caso es un agente abierto, y cabe con holgura."""
        assert PEOR_CASO_DEL_SISTEMA < Defaults.TOKENS_CONCURRENTES_MAXIMOS

    @given(perfil=perfiles)
    def test_la_salida_cabe_dentro_del_techo(self, perfil: Perfil) -> None:
        """Un rol cuya salida maxima no cupiera en su propio techo no podria responder."""
        techo = TECHOS[perfil]
        assert techo.salida_maxima < techo.total


class TestSiAlgunDiaSeParalelizan:
    """El semáforo que §12 describe **para el día que haga falta**, comprobado por adelantado.

    Hoy las micro-sesiones del arquitecto corren en serie y el semáforo no existe. Lo que sí
    se puede fijar ya es la aritmética que lo gobernaría, de modo que el día que alguien las
    paralelice tenga el número delante en lugar de tener que deducirlo.
    """

    def test_caben_siete_micro_sesiones_y_no_ocho(self) -> None:
        """Con techo de 14.000, el limite de 100.000 admite siete concurrentes."""
        micro = TECHOS[Perfil.INVESTIGADOR_MICRO].total
        caben = Defaults.TOKENS_CONCURRENTES_MAXIMOS // micro
        assert caben == 7
        assert micro * 8 > Defaults.TOKENS_CONCURRENTES_MAXIMOS

    @given(
        cuantas=st.integers(min_value=1, max_value=20),
    )
    def test_el_semaforo_rechazaria_a_partir_de_la_octava(self, cuantas: int) -> None:
        micro = TECHOS[Perfil.INVESTIGADOR_MICRO].total
        admitida = micro * cuantas <= Defaults.TOKENS_CONCURRENTES_MAXIMOS
        assert admitida == (cuantas <= 7)

    def test_el_investigador_inicial_no_se_paraleliza_consigo_mismo(self) -> None:
        """Dos sesiones iniciales a la vez pasarian de 90.000 y dejarian sin sitio al resto."""
        inicial = TECHOS[Perfil.INVESTIGADOR_INICIAL].total
        assert inicial * 2 < Defaults.TOKENS_CONCURRENTES_MAXIMOS
        assert inicial * 2 + TECHOS[Perfil.ESCRITOR].total > (
            Defaults.TOKENS_CONCURRENTES_MAXIMOS
        )
