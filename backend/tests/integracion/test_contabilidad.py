"""spec: §3.2 · arq: §8

Pruebas de la contabilidad de la invocación: una `fase_run` por fase y el consumo contado.

Realizan §9.1 y §9.2 de la spec de ejecución real. Lo que se comprueba es lo que la cuarta
novela real enseñó roto: que `storymaker estado` diga la fase en la que está la novela, que
lo que cuesta no sume cero, y que rehacer una fase desde su gate no mezcle el corpus nuevo
con el anterior.
"""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import aiosqlite
import pytest
from dobles import guion
from dobles.agente_falso import TransporteFalso
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.agents.contador import TransporteContado
from storymaker.commons.agents.hooks import CuotaDeHerramientas
from storymaker.commons.agents.techos import Perfil
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela, crear_novela
from storymaker.commons.graph.contabilidad import corpus_de
from storymaker.commons.graph.estado import estado_inicial
from storymaker.commons.graph.nodos import FASE_DE_NODO, GATES, NODOS, TERMINALES
from storymaker.commons.graph.run import Arranque, ResultadoInvocacion, invocar, reanudar
from storymaker.commons.obs.trazas import ObservadorNulo
from storymaker.gates.decisiones import aplicar
from storymaker.gates.notifier import NotifierNulo

CAPITULOS = 2
FASES_DEL_ESQUEMA = {
    "intake",
    "investigation",
    "plotting",
    "writing",
    "publication",
    "regeneration",
}


def _guion(*, investigaciones: int = 1) -> TransporteFalso:
    """El guion de una novela entera, con holgura en los roles del bucle de capítulo."""
    falso = TransporteFalso()
    falso.preparar(Perfil.ENTREVISTADOR, guion.entrevista(CAPITULOS))
    falso.preparar(Perfil.INVESTIGADOR_INICIAL, *[guion.investigacion()] * investigaciones)
    falso.preparar(Perfil.VERIFICADOR, *[guion.verificacion()] * investigaciones)
    falso.preparar(Perfil.ARQUITECTO, guion.arquitectura(CAPITULOS))
    falso.preparar(Perfil.INVESTIGADOR_MICRO, *[guion.hueco_resuelto() for _ in range(5)])
    falso.preparar(Perfil.ESCRITOR, *[guion.capitulo(n) for n in (1, 1, 1, 2, 2, 2)])
    falso.preparar(Perfil.EDITOR, *[guion.capitulo(n) for n in (1, 1, 2, 2)])
    falso.preparar(Perfil.EXTRACTOR_CAPITULO, *[guion.extraccion(n) for n in (1, 1, 1, 2, 2, 2)])
    falso.preparar(Perfil.JUEZ, guion.juicio(), guion.juicio())
    return falso


async def _filas(ruta: Path) -> list[aiosqlite.Row]:
    async with abrir_novela(ruta) as db:
        async with db.execute("SELECT * FROM fase_run ORDER BY id") as cursor:
            return list(await cursor.fetchall())


async def _decidir(
    ruta: Path, ajustes: Settings, transporte: TransporteFalso, decision: str
) -> ResultadoInvocacion:
    async with abrir_novela(ruta) as db:
        await aplicar(db, ObservadorNulo(), decision, "otra vez" if decision == "rehacer" else "")
        await db.commit()
    return await reanudar(
        ruta,
        settings=ajustes,
        decision=decision,
        transporte=transporte,
        vectorizador=VectorizadorFalso(),
        observador=ObservadorNulo(),
        notifier=NotifierNulo(),
    )


class TestTablaDeFases:
    def test_todo_nodo_que_no_es_gate_ni_reposo_tiene_fase(self) -> None:
        """Un nodo sin fase heredaría la fila de otra fase y su consumo iría a parar allí."""
        sin_fase = set(NODOS) - set(GATES) - set(TERMINALES) - {"Idle"}
        assert set(FASE_DE_NODO) == sin_fase

    def test_ninguna_fase_esta_fuera_del_check(self) -> None:
        """El `CHECK` de `fase_run.fase` abortaría la transacción al abrir la fila."""
        assert set(FASE_DE_NODO.values()) <= FASES_DEL_ESQUEMA


class TestTransporteContado:
    async def test_suma_cada_llamada(self) -> None:
        falso = TransporteFalso().preparar(
            Perfil.ENTREVISTADOR, guion.entrevista(), guion.entrevista()
        )
        contado = TransporteContado(falso)
        for _ in range(2):
            await contado.pedir(
                perfil=Perfil.ENTREVISTADOR,
                modelo="haiku",
                prompt="",
                sistema="",
                herramientas=(),
                max_turns=1,
                cuota=CuotaDeHerramientas.para(Perfil.ENTREVISTADOR),
            )
        assert contado.consumo.tokens_in == 20
        assert contado.consumo.tokens_out == 20


class TestCorpusDe:
    def test_sin_corpus_propio_es_la_fila_en_curso(self) -> None:
        """Un checkpoint anterior al cambio: todas las fases compartían una sola fila."""
        estado = estado_inicial(
            novela="n", fase_run_id=7, n_capitulos=2, max_intentos=2, huecos=0, gates_enabled=True
        )
        assert corpus_de(estado) == 7
        legado = {clave: valor for clave, valor in estado.items() if clave != "corpus_run_id"}
        assert corpus_de(legado) == 7  # type: ignore[arg-type]

    def test_con_corpus_propio_es_el_de_investigation(self) -> None:
        estado = estado_inicial(
            novela="n", fase_run_id=9, n_capitulos=2, max_intentos=2, huecos=0, gates_enabled=True
        )
        assert corpus_de({**estado, "corpus_run_id": 4}) == 4


class TestUnaFilaPorFase:
    async def test_en_batch_cada_fase_deja_su_fila_con_consumo(self, tmp_path: Path) -> None:
        """La travesía entera: cinco fases, cinco filas cerradas y un coste que no es cero."""
        ajustes = Settings(_env_file=None, gates_enabled=False, reintentos_por_capitulo=2)
        ruta = tmp_path / "proyectos" / "batch.db"
        await crear_novela(ruta)
        resultado = await invocar(
            ruta,
            Arranque(n_capitulos=CAPITULOS),
            settings=ajustes,
            transporte=_guion(),
            vectorizador=VectorizadorFalso(),
            observador=ObservadorNulo(),
            notifier=NotifierNulo(),
        )
        assert resultado.nodo_final == "Idle", resultado.error

        filas = await _filas(ruta)
        assert [f["fase"] for f in filas] == [
            "intake",
            "investigation",
            "plotting",
            "writing",
            "publication",
        ]
        assert {f["estado"] for f in filas} == {"completada"}
        assert all(f["tokens_in"] > 0 for f in filas)
        assert resultado.consumo.tokens_in == sum(f["tokens_in"] for f in filas)
        for anterior, siguiente in pairwise(filas):
            assert siguiente["input_run_id"] == anterior["id"]

    async def test_el_corpus_se_sella_bajo_la_fila_de_investigation(self, tmp_path: Path) -> None:
        ajustes = Settings(_env_file=None, gates_enabled=False, reintentos_por_capitulo=2)
        ruta = tmp_path / "proyectos" / "sello.db"
        await crear_novela(ruta)
        await invocar(
            ruta,
            Arranque(n_capitulos=CAPITULOS),
            settings=ajustes,
            transporte=_guion(),
            vectorizador=VectorizadorFalso(),
            observador=ObservadorNulo(),
            notifier=NotifierNulo(),
        )
        filas = await _filas(ruta)
        investigacion = next(int(f["id"]) for f in filas if f["fase"] == "investigation")
        async with abrir_novela(ruta) as db:
            async with db.execute("SELECT DISTINCT fase_run_id FROM mundo_hecho") as cursor:
                escritores = {int(f[0]) for f in await cursor.fetchall()}
            async with db.execute("SELECT fase_run_id FROM mundo_sello") as cursor:
                sello = await cursor.fetchone()
        assert escritores == {investigacion}, "los huecos de FillGap entran en el mismo corpus"
        assert sello is not None and int(sello[0]) == investigacion


class TestConGates:
    @pytest.fixture
    def ajustes(self) -> Settings:
        return Settings(_env_file=None, gates_enabled=True, reintentos_por_capitulo=2)

    async def test_la_fila_del_gate_espera_y_la_anterior_se_completa(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        """Lo que `storymaker estado` lee: la fase en la que la novela espera al Autor."""
        ruta = tmp_path / "proyectos" / "gates.db"
        await crear_novela(ruta)
        transporte = _guion()
        primera = await invocar(
            ruta,
            Arranque(n_capitulos=CAPITULOS),
            settings=ajustes,
            transporte=transporte,
            vectorizador=VectorizadorFalso(),
            observador=ObservadorNulo(),
            notifier=NotifierNulo(),
        )
        assert primera.gate_abierto is not None
        assert [(f["fase"], f["estado"]) for f in await _filas(ruta)] == [
            ("intake", "esperando_gate")
        ]

        segunda = await _decidir(ruta, ajustes, transporte, "aprobar")
        assert segunda.gate_abierto is not None
        filas = await _filas(ruta)
        assert [(f["fase"], f["estado"]) for f in filas] == [
            ("intake", "completada"),
            ("investigation", "esperando_gate"),
        ]
        assert filas[1]["tokens_in"] > 0
        assert segunda.consumo.tokens_in == filas[1]["tokens_in"]

    async def test_rehacer_abre_una_fila_nueva_sin_mezclar_el_corpus(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        """Rehacer es una ejecución nueva (arq. §8): los hechos nuevos llevan su propia fila."""
        ruta = tmp_path / "proyectos" / "rehacer.db"
        await crear_novela(ruta)
        transporte = _guion(investigaciones=2)
        await invocar(
            ruta,
            Arranque(n_capitulos=CAPITULOS),
            settings=ajustes,
            transporte=transporte,
            vectorizador=VectorizadorFalso(),
            observador=ObservadorNulo(),
            notifier=NotifierNulo(),
        )
        await _decidir(ruta, ajustes, transporte, "aprobar")
        await _decidir(ruta, ajustes, transporte, "rehacer")

        filas = await _filas(ruta)
        assert [(f["fase"], f["estado"]) for f in filas] == [
            ("intake", "completada"),
            ("investigation", "completada"),
            ("investigation", "esperando_gate"),
        ]
        primera, segunda = int(filas[1]["id"]), int(filas[2]["id"])
        async with abrir_novela(ruta) as db:
            async with db.execute(
                "SELECT fase_run_id, COUNT(*) FROM mundo_hecho GROUP BY fase_run_id"
            ) as cursor:
                por_fila = {int(f[0]): int(f[1]) for f in await cursor.fetchall()}
        assert set(por_fila) == {primera, segunda}
        assert por_fila[primera] == por_fila[segunda]


class TestReintentar:
    """`storymaker reintentar` reabre el capítulo que agotó sus reintentos (arq. §16.5)."""

    @staticmethod
    def _cae_en_el_capitulo_1() -> TransporteFalso:
        """Hasta el sello, bien; el capítulo 1, demasiado corto en los tres intentos."""
        falso = TransporteFalso()
        falso.preparar(Perfil.ENTREVISTADOR, guion.entrevista(CAPITULOS))
        falso.preparar(Perfil.INVESTIGADOR_INICIAL, guion.investigacion())
        falso.preparar(Perfil.VERIFICADOR, guion.verificacion())
        falso.preparar(Perfil.ARQUITECTO, guion.arquitectura(CAPITULOS))
        falso.preparar(Perfil.INVESTIGADOR_MICRO, *[guion.hueco_resuelto() for _ in range(5)])
        falso.preparar(Perfil.ESCRITOR, guion.capitulo(1, palabras=20))
        falso.preparar(
            Perfil.EDITOR, guion.capitulo(1, palabras=20), guion.capitulo(1, palabras=20)
        )
        return falso

    @staticmethod
    def _escribe_bien() -> TransporteFalso:
        falso = TransporteFalso()
        falso.preparar(Perfil.ESCRITOR, *[guion.capitulo(n) for n in (1, 1, 1, 2, 2, 2)])
        falso.preparar(Perfil.EDITOR, *[guion.capitulo(n) for n in (1, 1, 2, 2)])
        falso.preparar(
            Perfil.EXTRACTOR_CAPITULO, *[guion.extraccion(n) for n in (1, 1, 1, 2, 2, 2)]
        )
        falso.preparar(Perfil.JUEZ, guion.juicio(), guion.juicio())
        return falso

    async def test_reabre_el_capitulo_y_la_novela_se_publica(self, tmp_path: Path) -> None:
        from storymaker.commons.graph.run import reintentar

        ajustes = Settings(_env_file=None, gates_enabled=False, reintentos_por_capitulo=2)
        ruta = tmp_path / "proyectos" / "caida.db"
        await crear_novela(ruta)
        caida = await invocar(
            ruta,
            Arranque(n_capitulos=CAPITULOS),
            settings=ajustes,
            transporte=self._cae_en_el_capitulo_1(),
            vectorizador=VectorizadorFalso(),
            observador=ObservadorNulo(),
            notifier=NotifierNulo(),
        )
        assert caida.nodo_final == "Fail"

        resultado = await reintentar(
            ruta,
            settings=ajustes,
            transporte=self._escribe_bien(),
            vectorizador=VectorizadorFalso(),
            observador=ObservadorNulo(),
            notifier=NotifierNulo(),
        )
        assert resultado.nodo_final == "Idle", resultado.error

        async with abrir_novela(ruta) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM capitulo_version WHERE capitulo_id = 1"
            ) as cursor:
                intentos = await cursor.fetchone()
        assert intentos is not None and intentos[0] >= 4, "los intentos fallidos no se borran"
        filas = await _filas(ruta)
        assert [f["fase"] for f in filas][-2:] == ["writing", "publication"]
        assert filas[-3]["estado"] == "fallida"

    async def test_se_niega_si_la_novela_espera_en_un_gate(self, tmp_path: Path) -> None:
        from storymaker.commons.errores import NadaQueReintentar
        from storymaker.commons.graph.run import reintentar

        ajustes = Settings(_env_file=None, gates_enabled=True)
        ruta = tmp_path / "proyectos" / "en-gate.db"
        await crear_novela(ruta)
        await invocar(
            ruta,
            Arranque(n_capitulos=CAPITULOS),
            settings=ajustes,
            transporte=_guion(),
            vectorizador=VectorizadorFalso(),
            observador=ObservadorNulo(),
            notifier=NotifierNulo(),
        )
        antes = await _filas(ruta)
        with pytest.raises(NadaQueReintentar):
            await reintentar(ruta, settings=ajustes, transporte=_guion())
        assert [tuple(f) for f in await _filas(ruta)] == [tuple(f) for f in antes]
