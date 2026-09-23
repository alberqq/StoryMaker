"""spec: §3.2 · arq: §1, §9, §16.4

Pruebas del estado del grafo, de sus aristas condicionales y del cerrojo.

Lo que se comprueba de las aristas no es que enruten «bien» en abstracto, sino que
**deciden sobre booleanos calculados en Python**: se les da un estado y se mira adónde
llevan. Ningún enrutador recibe texto de un modelo, y esa es la propiedad de la que cuelga
que TLC pueda verificar el sistema.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from storymaker.commons.errores import NovelaOcupada
from storymaker.commons.graph import cerrojo
from storymaker.commons.graph.aristas import (
    tras_checkpoint,
    tras_extract,
    tras_gate,
    tras_judge,
    tras_plan,
    tras_validate,
)
from storymaker.commons.graph.construccion import (
    NodoSinImplementar,
    _pendiente,
    nodos_pendientes,
    nodos_resueltos,
    resolver,
)
from storymaker.commons.graph.estado import EstadoNovela, estado_inicial
from storymaker.commons.graph.nodos import NODOS, fail, idle


def estado(**cambios: object) -> EstadoNovela:
    base = estado_inicial(
        novela="proyectos/n.db",
        fase_run_id=1,
        n_capitulos=10,
        max_intentos=2,
        huecos=5,
        gates_enabled=True,
    )
    base.update(cambios)  # type: ignore[typeddict-item]
    return base


class TestEstado:
    def test_arranca_en_configure(self) -> None:
        assert estado()["pc"] == "Configure"

    def test_es_total(self) -> None:
        """Un `TypedDict` total: nadie tiene que comprobar si un campo esta."""
        inicial = estado()
        assert set(EstadoNovela.__annotations__) == set(inicial)

    def test_no_guarda_contenido(self) -> None:
        """El orquestador no acumula: aqui hay punteros, nunca texto."""
        valores = estado().values()
        largos = [v for v in valores if isinstance(v, str) and len(v) > 200]
        assert largos == []


class TestAristasCondicionales:
    def test_validate_limpio_va_al_extractor(self) -> None:
        assert tras_validate(estado(hay_bloqueantes=False)) == "Extract"

    def test_validate_con_incidencias_va_al_editor(self) -> None:
        assert tras_validate(estado(hay_bloqueantes=True, intentos=0)) == "Repair"

    def test_agotados_los_reintentos_va_a_fail(self) -> None:
        """`Fail` es un estado declarado del grafo, no una excepcion."""
        assert tras_validate(estado(hay_bloqueantes=True, intentos=2)) == "Fail"

    def test_el_extractor_comparte_el_contador_con_validate(self) -> None:
        """Las dos aristas de entrada a `Repair`: es por lo que `RetriesBounded` existe."""
        assert tras_extract(estado(hay_bloqueantes=True, intentos=1)) == "Repair"
        assert tras_extract(estado(hay_bloqueantes=True, intentos=2)) == "Fail"
        assert tras_extract(estado(hay_bloqueantes=False)) == "ApproveChapter"

    def test_checkpoint_sigue_o_cierra_writing(self) -> None:
        """`capitulo` es el que **falta**, porque `Checkpoint` ya adelantó el contador.

        Por eso el último valor que manda a escribir es `n_capitulos` y no `n_capitulos - 1`:
        con la comparación estricta la novela se quedaba siempre un capítulo corta y era
        `PublishVersion` quien lo destapaba, mucho más tarde y sin decir por qué.
        """
        assert tras_checkpoint(estado(capitulo=3, n_capitulos=10)) == "WriteChapter"
        assert tras_checkpoint(estado(capitulo=10, n_capitulos=10)) == "WriteChapter"
        assert tras_checkpoint(estado(capitulo=11, n_capitulos=10)) == "AwaitApproval4"

    def test_el_tope_de_huecos_vive_en_el_estado(self) -> None:
        """Si viviera en el prompt del arquitecto seria una sugerencia."""
        assert tras_plan(estado(huecos=3)) == "FillGap"
        assert tras_plan(estado(huecos=0)) == "AwaitApproval3"

    def test_el_corpus_sellado_cierra_la_micro_investigacion(self) -> None:
        assert tras_plan(estado(huecos=3, sellado=True)) == "AwaitApproval3"

    def test_el_juez_tiene_tope_de_rechazos(self) -> None:
        """Sin tope, el juez y el gate se pasan la novela para siempre. Lo vio TLC."""
        assert tras_judge(estado(hay_bloqueantes=False)) == "PublishVersion"
        assert tras_judge(estado(hay_bloqueantes=True, rechazos_juez=0)) == "AwaitApproval4"
        assert tras_judge(estado(hay_bloqueantes=True, rechazos_juez=2)) == "Fail"


class TestDecisionesDeGate:
    @pytest.mark.parametrize(
        ("gate", "avance"),
        [
            ("AwaitApproval", "Research"),
            ("AwaitApproval2", "Plan"),
            ("AwaitApproval3", "SealCorpus"),
            ("AwaitApproval4", "Judge"),
        ],
    )
    def test_aprobar_avanza(self, gate: str, avance: str) -> None:
        assert tras_gate(estado(), gate=gate, decision="aprobar") == avance

    @pytest.mark.parametrize(
        ("gate", "vuelta"),
        [
            ("AwaitApproval", "Configure"),
            ("AwaitApproval2", "Research"),
            ("AwaitApproval3", "Plan"),
            ("AwaitApproval4", "WriteChapter"),
        ],
    )
    def test_rehacer_vuelve_a_quien_produjo_el_artefacto(self, gate: str, vuelta: str) -> None:
        assert tras_gate(estado(), gate=gate, decision="rehacer") == vuelta

    def test_editar_vuelve_por_el_mismo_camino_que_rehacer(self) -> None:
        """La edicion humana dispara la misma maquinaria; no hay un segundo recorrido."""
        assert tras_gate(estado(), gate="AwaitApproval3", decision="editar") == "Plan"

    def test_abortar_en_el_gate_de_intake(self) -> None:
        assert tras_gate(estado(), gate="AwaitApproval", decision="abortar") == "Fail"

    def test_abortar_en_los_otros_gates_es_un_hallazgo_abierto(self) -> None:
        """El modelo no declara esa arista, asi que el codigo no se la inventa.

        §10 ofrece «abortar» en los cinco gates y `Aristas` solo lo declara desde el
        primero. Mientras no se resuelva arriba, esto revienta en vez de mover el `pc` por
        una transicion que TLC nunca exploro.
        """
        with pytest.raises(AssertionError, match="no esta en la relacion"):
            tras_gate(estado(), gate="AwaitApproval4", decision="abortar")


class TestResolucionDeNodos:
    def test_los_veinticuatro_tienen_entrada(self) -> None:
        assert len(nodos_resueltos()) == len(NODOS) == 24

    def test_ya_no_queda_ninguno_pendiente(self) -> None:
        """Los veinticuatro resuelven a codigo real: el plan esta completo."""
        assert nodos_pendientes() == []

    def test_una_ruta_que_no_existe_no_resuelve(self) -> None:
        """El mecanismo sigue en pie para el proximo nodo que alguien declare antes de escribir."""
        assert resolver("storymaker.fase.inexistente:nodo") is None

    async def test_el_sustituto_lanza_al_pisarlo(self) -> None:
        """Un nodo que no hace nada produciria una novela con fases enteras saltadas."""
        pendiente = _pendiente("Inventado", "storymaker.fase.inexistente:nodo")
        with pytest.raises(NodoSinImplementar):
            await pendiente(estado())

    async def test_idle_y_fail_ya_existen_y_no_tocan_el_estado(self) -> None:
        inicial = estado()
        assert await idle(inicial) == inicial
        assert await fail(inicial) == inicial


class TestCerrojo:
    def test_se_toma_y_se_suelta(self, tmp_path: Path) -> None:
        novela = tmp_path / "n.db"
        novela.touch()
        with cerrojo.tomar(novela):
            assert cerrojo.esta_tomado(novela)
        assert not cerrojo.esta_tomado(novela)

    def test_quien_llega_segundo_es_rechazado_no_encolado(self, tmp_path: Path) -> None:
        """Una cola seria ese segundo lugar donde vive el estado que §16.4 descarta."""
        novela = tmp_path / "n.db"
        novela.touch()
        with cerrojo.tomar(novela), pytest.raises(NovelaOcupada):
            with cerrojo.tomar(novela):
                pass

    def test_se_suelta_aunque_reviente(self, tmp_path: Path) -> None:
        novela = tmp_path / "n.db"
        novela.touch()
        with pytest.raises(RuntimeError), cerrojo.tomar(novela):
            raise RuntimeError("el nodo revienta")
        assert not cerrojo.esta_tomado(novela)

    def test_guarda_el_pid_para_que_el_autor_pueda_decidir(self, tmp_path: Path) -> None:
        novela = tmp_path / "n.db"
        novela.touch()
        with cerrojo.tomar(novela) as ruta:
            assert ruta.read_text(encoding="utf-8") == str(os.getpid())

    def test_romper_un_cerrojo_huerfano(self, tmp_path: Path) -> None:
        """La operacion de mantenimiento que el Autor hara una vez cada muchas."""
        novela = tmp_path / "n.db"
        novela.touch()
        cerrojo.ruta_del_cerrojo(novela).write_text("99999", encoding="utf-8")
        assert cerrojo.romper(novela) is True
        assert cerrojo.romper(novela) is False
