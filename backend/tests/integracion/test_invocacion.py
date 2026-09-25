"""spec: §2.1, §3.2 · arq: §8, §16.4

Pruebas de la invocación y de la ramificación, sobre SQLite temporal.

Mientras las seis fases no estén escritas, lo que se puede comprobar aquí es justo lo que
importa que esté bien antes de que existan: que el cerrojo se toma y se suelta, que un
nodo que revienta deja la ejecución marcada como fallida y **el checkpoint intacto**, y que
ramificar es copiar el fichero sin tocar el original.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from dobles import guion
from dobles.agente_falso import TransporteFalso
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.agents.techos import Perfil
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela, crear_novela
from storymaker.commons.db.repos import arnes, mundo
from storymaker.commons.errores import NovelaNoEncontrada, NovelaOcupada
from storymaker.commons.graph import cerrojo
from storymaker.commons.graph.branch import ramificar
from storymaker.commons.graph.run import Arranque, invocar
from storymaker.commons.obs.trazas import ObservadorNulo
from storymaker.gates.notifier import NotifierNulo


@pytest.fixture
def ajustes() -> Settings:
    """Con los gates **encendidos**: lo que aquí se comprueba es que la invocación pare.

    El recorrido completo, con los gates apagados, vive en `test_extremo_a_extremo`. Aquí
    interesa lo contrario: que el primer gate corte la invocación y deje el checkpoint en
    disco, que es la mitad del diseño que hace que reiniciar el servidor no mate nada.
    """
    return Settings(_env_file=None, gates_enabled=True)


@pytest.fixture
def dobles() -> dict[str, object]:
    """El transporte falso, el vectorizador determinista y un observador que no emite."""
    transporte = TransporteFalso().preparar(Perfil.ENTREVISTADOR, guion.entrevista(3))
    return {
        "transporte": transporte,
        "vectorizador": VectorizadorFalso(),
        "observador": ObservadorNulo(),
    }


@pytest.fixture
async def novela(tmp_path: Path) -> Path:
    ruta = tmp_path / "proyectos" / "novela-1.db"
    await crear_novela(ruta)
    return ruta


class TestInvocacion:
    async def test_el_recorrido_llega_al_primer_gate(
        self, novela: Path, ajustes: Settings, dobles: dict[str, Any]
    ) -> None:
        """Con los veinticuatro nodos escritos, la invocacion avanza y se detiene donde debe.

        Lo que se comprueba no es que escriba una novela —eso necesita el SDK y una sesion de
        Claude Code—, sino que **el recorrido es real**: el grafo arranca en `Configure`, pasa
        por los nodos y se para en el primer punto que espera a alguien, dejando la ejecucion
        registrada. Entre invocacion e invocacion no queda nada vivo.
        """
        resultado = await invocar(novela, Arranque(n_capitulos=3), settings=ajustes, **dobles)
        assert resultado.nodo_final != "Fail", resultado.error
        assert resultado.error is None

        async with abrir_novela(novela) as db:
            async with db.execute("SELECT * FROM fase_run") as cursor:
                fila = await cursor.fetchone()
        assert fila is not None, "la ejecucion de fase queda registrada"

    async def test_el_gate_se_abre_se_decide_y_no_se_reabre_al_reanudar(
        self, novela: Path, ajustes: Settings, dobles: dict[str, Any]
    ) -> None:
        """El gate queda **pendiente** en la base, y decidirlo no abre otro igual.

        LangGraph vuelve a ejecutar el nodo del gate al reanudar. Sin la marca de
        reanudación, cada decisión abría un gate nuevo y volvía a avisar al Autor.
        """
        from storymaker.commons.graph.run import reanudar
        from storymaker.commons.obs.trazas import ObservadorNulo
        from storymaker.gates.decisiones import aplicar

        primero = await invocar(novela, Arranque(n_capitulos=3), settings=ajustes, **dobles)
        assert primero.gate_abierto is not None, "el primer gate queda pendiente en la base"

        async with abrir_novela(novela) as db:
            await aplicar(db, ObservadorNulo(), "aprobar")
            await db.commit()
        # Lo que venga después del gate no importa aquí: el doble de esta prueba no guioniza
        # la investigación. Lo que se mira es que reanudar no reabra el gate decidido.
        await reanudar(novela, settings=ajustes, decision="aprobar", **dobles)

        async with abrir_novela(novela) as db:
            async with db.execute("SELECT id, estado FROM gate ORDER BY id") as cursor:
                gates = [(int(f["id"]), str(f["estado"])) for f in await cursor.fetchall()]
        assert gates[0] == (primero.gate_abierto, "decidido")
        assert [e for _, e in gates].count("pendiente") <= 1, gates
        assert len(gates) <= 2, "reanudar no reabre el gate decidido"

    async def test_ningun_nodo_queda_sin_implementar(self) -> None:
        """El plan esta completo: los veinticuatro nodos resuelven a codigo real."""
        from storymaker.commons.graph.construccion import nodos_pendientes

        assert nodos_pendientes() == []

    async def test_el_cerrojo_se_suelta_aunque_la_invocacion_falle(
        self, novela: Path, ajustes: Settings
    ) -> None:
        await invocar(novela, Arranque(n_capitulos=3), settings=ajustes)
        assert not cerrojo.esta_tomado(novela), "un cerrojo huerfano por cada fallo seria peor"

    async def test_una_invocacion_que_revienta_avisa_de_la_parada(
        self, novela: Path, ajustes: Settings
    ) -> None:
        """Sin guion, el entrevistador no tiene respuesta y el grafo revienta en `Configure`.

        El aviso sale aunque nadie mire la terminal, y dice dónde reventó.
        """
        nulo = NotifierNulo()
        resultado = await invocar(
            novela,
            Arranque(n_capitulos=3),
            settings=ajustes,
            transporte=TransporteFalso(),
            vectorizador=VectorizadorFalso(),
            observador=ObservadorNulo(),
            notifier=nulo,
        )
        assert resultado.nodo_final == "Fail"
        assert [a.titulo for a in nulo.enviados] == [f"StoryMaker · {novela.stem} · se ha detenido"]
        assert "Nodo: entrevistar" in nulo.enviados[0].cuerpo
        assert "storymaker" not in nulo.enviados[0].cuerpo

    async def test_parar_en_un_gate_no_manda_aviso_de_parada(
        self, novela: Path, ajustes: Settings, dobles: dict[str, Any]
    ) -> None:
        """El gate avisa desde su nodo; `invocar` no duplica el mensaje ni lo llama fallo."""
        nulo = NotifierNulo()
        resultado = await invocar(
            novela, Arranque(n_capitulos=3), settings=ajustes, notifier=nulo, **dobles
        )
        assert resultado.gate_abierto is not None
        assert nulo.enviados == []

    async def test_quien_llega_segundo_es_rechazado(self, novela: Path, ajustes: Settings) -> None:
        """Dos invocaciones a la vez podrian duplicar un capitulo: es `ResumeIsExactlyOnce`."""
        with cerrojo.tomar(novela), pytest.raises(NovelaOcupada):
            await invocar(novela, Arranque(n_capitulos=3), settings=ajustes)

    async def test_una_novela_inexistente_no_se_crea_por_invocarla(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        with pytest.raises(NovelaNoEncontrada):
            await invocar(tmp_path / "no-existe.db", Arranque(n_capitulos=3), settings=ajustes)


class TestRamificacion:
    async def test_ramificar_es_copiar_el_fichero(self, novela: Path) -> None:
        async with abrir_novela(novela) as db:
            ejecucion = await arnes.abrir_fase_run(db, "plotting")
            await mundo.insertar_hecho(
                db,
                fase_run_id=ejecucion,
                enunciado="El roble llegaba de La Habana",
                estado="verificado",
                dimension="cultura_material",
            )
            await db.commit()

        rama = await ramificar(novela, novela.with_name("novela-1b.db"), fase_run_id=ejecucion)

        async with abrir_novela(rama) as db:
            hechos = await mundo.hechos_vigentes(db, ejecucion)
            async with db.execute("SELECT * FROM procedencia") as cursor:
                procedencia = await cursor.fetchone()
        assert len(hechos) == 1, "la rama parte del mismo corpus"
        assert procedencia is not None
        assert procedencia["origen_db"] == "novela-1.db"
        assert procedencia["origen_fase_run_id"] == ejecucion

    async def test_la_rama_hereda_el_checkpoint_en_su_propio_hilo(self, novela: Path) -> None:
        """El hilo se llama como el fichero: sin mudarlo, la rama nacía sin checkpoint."""
        async with abrir_novela(novela) as db:
            await db.execute("CREATE TABLE checkpoints (thread_id TEXT, checkpoint_id TEXT)")
            await db.execute("CREATE TABLE writes (thread_id TEXT, checkpoint_id TEXT)")
            await db.execute("INSERT INTO checkpoints VALUES ('novela-1', 'c1')")
            await db.execute("INSERT INTO writes VALUES ('novela-1', 'c1')")
            await db.commit()

        rama = await ramificar(novela, novela.with_name("novela-1b.db"))

        async with abrir_novela(rama) as db:
            for tabla in ("checkpoints", "writes"):
                async with db.execute(f"SELECT DISTINCT thread_id FROM {tabla}") as cursor:
                    hilos = [str(f[0]) for f in await cursor.fetchall()]
                assert hilos == ["novela-1b"], tabla
        async with abrir_novela(novela) as db:
            async with db.execute("SELECT thread_id FROM checkpoints") as cursor:
                assert [str(f[0]) for f in await cursor.fetchall()] == ["novela-1"]

    async def test_la_novela_original_no_se_toca(self, novela: Path) -> None:
        rama = await ramificar(novela, novela.with_name("novela-1b.db"))
        async with abrir_novela(rama) as db:
            await arnes.abrir_fase_run(db, "writing")
            await db.commit()
        async with abrir_novela(novela) as db:
            async with db.execute("SELECT COUNT(*) AS n FROM fase_run") as cursor:
                fila = await cursor.fetchone()
        assert fila is not None and int(fila["n"]) == 0

    async def test_ramificar_no_sobrescribe(self, novela: Path) -> None:
        """Sobrescribir una novela por equivocarse de nombre seria el borrado mas caro."""
        destino = novela.with_name("novela-1b.db")
        await ramificar(novela, destino)
        with pytest.raises(NovelaOcupada):
            await ramificar(novela, destino)

    async def test_no_se_ramifica_lo_que_no_existe(self, tmp_path: Path) -> None:
        with pytest.raises(NovelaNoEncontrada):
            await ramificar(tmp_path / "no-existe.db", tmp_path / "copia.db")
