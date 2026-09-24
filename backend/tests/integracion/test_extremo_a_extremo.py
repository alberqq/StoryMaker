"""spec: §2.1, §4 · arq: §4, §9, §16.4 · verif. G4

**Una novela entera, de `Configure` a `PublishVersion`, sin tocar la red.**

Es la prueba que cierra el arnés. Todas las demás miran una pieza: esta comprueba lo único
que ninguna de ellas puede comprobar por separado —que las seis fases encajan—. El
transporte es un doble, así que no hay modelo ni sesión de Claude Code; todo lo demás es
real: el esquema, los validadores, el índice semántico, el checkpointer, los gates y el
render.

Lo que se mira al final no es que «haya salido bien», sino **lo que quedó escrito**: la
escaleta, los capítulos aprobados, sus resúmenes indexados, la versión publicada y su
manifiesto. Si el cableado de un nodo estuviera puesto pero no llamara a nada, el recorrido
terminaría igual de limpio y la base estaría vacía — por eso las aserciones van contra la
base y no contra el estado devuelto.

Corre **en modo batch**, con los gates apagados, que es exactamente el modo en el que los
cinco briefs de evaluación tienen que recorrer el sistema desatendidos.
"""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest
from dobles import guion
from dobles.agente_falso import TransporteFalso
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.agents.techos import Perfil
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela, crear_novela
from storymaker.commons.graph.run import Arranque, invocar
from storymaker.commons.obs.trazas import ObservadorNulo

CAPITULOS = 2


@pytest.fixture
def ajustes(tmp_path: Path) -> Settings:
    """Modo batch: sin gates, sin Langfuse y sin Telegram."""
    return Settings(
        _env_file=None,
        directorio_proyectos=tmp_path / "proyectos",
        gates_enabled=False,
        reintentos_por_capitulo=2,
    )


@pytest.fixture
def transporte() -> TransporteFalso:
    """El guion completo, en el orden en que el grafo va a pedirlo.

    Las colas se dimensionan con holgura en los roles del bucle de capítulo porque el
    número de llamadas depende de si algún validador tumba un intento: si el escritor se
    quedara sin respuestas la prueba fallaría por el motivo equivocado.
    """
    falso = TransporteFalso()
    falso.preparar(Perfil.ENTREVISTADOR, guion.entrevista(CAPITULOS))
    falso.preparar(Perfil.INVESTIGADOR_INICIAL, guion.investigacion())
    falso.preparar(Perfil.VERIFICADOR, guion.verificacion())
    falso.preparar(Perfil.ARQUITECTO, guion.arquitectura(CAPITULOS))
    falso.preparar(Perfil.INVESTIGADOR_MICRO, *[guion.hueco_resuelto() for _ in range(5)])
    falso.preparar(Perfil.ESCRITOR, *[guion.capitulo(n) for n in (1, 1, 1, 2, 2, 2)])
    falso.preparar(Perfil.EDITOR, *[guion.capitulo(n) for n in (1, 1, 2, 2)])
    falso.preparar(Perfil.EXTRACTOR_CAPITULO, *[guion.extraccion(n) for n in (1, 1, 1, 2, 2, 2)])
    falso.preparar(Perfil.JUEZ, guion.juicio(), guion.juicio())
    return falso


async def _recorrer(
    ruta: Path, ajustes: Settings, transporte: TransporteFalso
) -> tuple[str, str | None]:
    await crear_novela(ruta)
    resultado = await invocar(
        ruta,
        Arranque(n_capitulos=CAPITULOS),
        settings=ajustes,
        transporte=transporte,
        vectorizador=VectorizadorFalso(),
        observador=ObservadorNulo(),
    )
    return resultado.nodo_final, resultado.error


async def _contar(db: aiosqlite.Connection, consulta: str) -> int:
    async with db.execute(consulta) as cursor:
        fila = await cursor.fetchone()
    return int(fila[0]) if fila is not None else 0


class TestNovelaCompleta:
    async def test_el_recorrido_llega_hasta_el_final(
        self, tmp_path: Path, ajustes: Settings, transporte: TransporteFalso
    ) -> None:
        """De `Configure` a `Idle` sin pasar por `Fail`. Es la travesía entera."""
        ruta = tmp_path / "proyectos" / "completa.db"
        nodo, error = await _recorrer(ruta, ajustes, transporte)
        assert error is None, error
        assert nodo != "Fail"

    async def test_al_terminar_avisa_de_la_version_publicada(
        self, tmp_path: Path, ajustes: Settings, transporte: TransporteFalso
    ) -> None:
        """En batch no hay gates, así que el final es el único aviso que llega."""
        from storymaker.gates.notifier import NotifierNulo

        ruta = tmp_path / "proyectos" / "avisada.db"
        await crear_novela(ruta)
        nulo = NotifierNulo()
        resultado = await invocar(
            ruta,
            Arranque(n_capitulos=CAPITULOS),
            settings=ajustes,
            transporte=transporte,
            vectorizador=VectorizadorFalso(),
            observador=ObservadorNulo(),
            notifier=nulo,
        )
        assert resultado.nodo_final == "Idle", resultado.error
        assert [a.titulo for a in nulo.enviados] == ["StoryMaker · avisada · terminada"]
        assert "Version 1 publicada" in nulo.enviados[0].cuerpo

    async def test_las_seis_fases_dejan_su_rastro(
        self, tmp_path: Path, ajustes: Settings, transporte: TransporteFalso
    ) -> None:
        """Cada fase escribió lo suyo. Un nodo cableado y hueco fallaría aquí y no antes."""
        ruta = tmp_path / "proyectos" / "rastro.db"
        _, error = await _recorrer(ruta, ajustes, transporte)
        assert error is None, error

        async with abrir_novela(ruta) as db:
            assert await _contar(db, "SELECT COUNT(*) FROM intake_brief") == 1, "Intake"
            assert await _contar(db, "SELECT COUNT(*) FROM mundo_hecho") >= 6, "Investigation"
            assert await _contar(db, "SELECT COUNT(*) FROM canon_personaje") == 2, "Plotting"
            assert await _contar(db, "SELECT COUNT(*) FROM plan_capitulo") == CAPITULOS
            assert await _contar(db, "SELECT COUNT(*) FROM plan_escena") == CAPITULOS
            aprobados = await _contar(
                db, "SELECT COUNT(*) FROM capitulo_version WHERE estado = 'aprobado'"
            )
            assert aprobados == CAPITULOS, "Writing aprueba todos los capitulos"
            assert await _contar(db, "SELECT COUNT(*) FROM version_novela") == 1, "Publication"
            assert await _contar(db, "SELECT COUNT(*) FROM manifiesto") == 1

    async def test_el_corpus_queda_sellado_antes_de_escribir(
        self, tmp_path: Path, ajustes: Settings, transporte: TransporteFalso
    ) -> None:
        """El sello se pone al cerrar Plotting, y es lo que hace comparables las ramas."""
        ruta = tmp_path / "proyectos" / "sello.db"
        _, error = await _recorrer(ruta, ajustes, transporte)
        assert error is None, error

        async with abrir_novela(ruta) as db:
            async with db.execute("SELECT hash FROM mundo_sello LIMIT 1") as cursor:
                fila = await cursor.fetchone()
        assert fila is not None and str(fila["hash"])

    async def test_cada_capitulo_aprobado_tiene_resumen_indexado(
        self, tmp_path: Path, ajustes: Settings, transporte: TransporteFalso
    ) -> None:
        """Sin resumen no hay bloque 3 del paquete, y sin bloque 3 no hay continuidad."""
        ruta = tmp_path / "proyectos" / "resumenes.db"
        _, error = await _recorrer(ruta, ajustes, transporte)
        assert error is None, error

        async with abrir_novela(ruta) as db:
            resumenes = await _contar(
                db,
                "SELECT COUNT(*) FROM capitulo_version "
                "WHERE estado = 'aprobado' AND resumen IS NOT NULL AND resumen <> ''",
            )
        assert resumenes >= CAPITULOS

    async def test_la_cronologia_se_escribe_capitulo_a_capitulo(
        self, tmp_path: Path, ajustes: Settings, transporte: TransporteFalso
    ) -> None:
        """Es lo que permite que Lean verifique un capítulo sin releer su prosa."""
        ruta = tmp_path / "proyectos" / "cronologia.db"
        _, error = await _recorrer(ruta, ajustes, transporte)
        assert error is None, error

        async with abrir_novela(ruta) as db:
            eventos = await _contar(db, "SELECT COUNT(*) FROM cronologia_evento")
        assert eventos >= CAPITULOS

    async def test_ningun_rol_se_invoca_de_mas(
        self, tmp_path: Path, ajustes: Settings, transporte: TransporteFalso
    ) -> None:
        """El arquitecto planifica **una vez**, no una por hueco.

        Es la consecuencia concreta de que `Plan` no replanifique al volver de `FillGap`, y
        la que más cuesta si se pierde: cinco llamadas de arquitecto por novela para no
        cambiar nada que el escritor vaya a leer.
        """
        ruta = tmp_path / "proyectos" / "llamadas.db"
        _, error = await _recorrer(ruta, ajustes, transporte)
        assert error is None, error

        assert transporte.veces(Perfil.ARQUITECTO) == 1
        assert transporte.veces(Perfil.ENTREVISTADOR) == 1
        assert transporte.veces(Perfil.ESCRITOR) == CAPITULOS
