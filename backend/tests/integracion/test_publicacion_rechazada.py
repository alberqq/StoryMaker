"""spec: §4.5 · arq: §9, §11a, §11c · verif. G4, G5

**Una publicación rechazada vuelve al gate de Writing, y no deja versión.**

El recorrido es el de la prueba de extremo a extremo, en batch, con una diferencia: el
navegador de `render_visual` encuentra un fallo. Lo que se comprueba es lo que la arista
`PublishVersion → AwaitApproval4` promete —que el rechazo no publica nada, que queda
escrito citando el capítulo, que la novela vuelve a pasar por el gate y el juez, y que el
rechazo comparte tope con el del juez—, mirando la base y no el estado devuelto.
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
from storymaker.commons.validation.modelos import Incidencia, Severidad
from storymaker.publication import render

CAPITULOS = 2


@pytest.fixture
def ajustes(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        directorio_proyectos=tmp_path / "proyectos",
        gates_enabled=False,
        reintentos_por_capitulo=2,
    )


@pytest.fixture
def transporte() -> TransporteFalso:
    falso = TransporteFalso()
    falso.preparar(Perfil.ENTREVISTADOR, guion.entrevista(CAPITULOS))
    falso.preparar(Perfil.INVESTIGADOR_INICIAL, guion.investigacion())
    falso.preparar(Perfil.VERIFICADOR, guion.verificacion())
    falso.preparar(Perfil.ARQUITECTO, guion.arquitectura(CAPITULOS))
    falso.preparar(Perfil.INVESTIGADOR_MICRO, *[guion.hueco_resuelto() for _ in range(5)])
    falso.preparar(Perfil.ESCRITOR, *[guion.capitulo(n) for n in (1, 1, 1, 2, 2, 2)])
    falso.preparar(Perfil.EDITOR, *[guion.capitulo(n) for n in (1, 1, 2, 2)])
    falso.preparar(Perfil.EXTRACTOR_CAPITULO, *[guion.extraccion(n) for n in (1, 1, 1, 2, 2, 2)])
    falso.preparar(Perfil.JUEZ, guion.juicio(), guion.juicio(), guion.juicio())
    return falso


def navegador_que_falla(veces: int) -> tuple[list[int], object]:
    """Un `en_navegador` que ve el capítulo 2 vacío las primeras `veces` y después nada."""
    llamadas: list[int] = []

    async def falso(lectura: render.Lectura) -> list[Incidencia]:
        llamadas.append(1)
        if len(llamadas) <= veces:
            return [
                Incidencia(
                    validador="render_visual",
                    severidad=Severidad.BLOQUEANTE,
                    mensaje="El capitulo 2 se pinta sin texto.",
                    ubicacion="cap2",
                )
            ]
        return []

    return llamadas, falso


async def _recorrer(ruta: Path, ajustes: Settings, transporte: TransporteFalso) -> str:
    await crear_novela(ruta)
    resultado = await invocar(
        ruta,
        Arranque(n_capitulos=CAPITULOS),
        settings=ajustes,
        transporte=transporte,
        vectorizador=VectorizadorFalso(),
        observador=ObservadorNulo(),
    )
    return resultado.nodo_final


async def _uno(db: aiosqlite.Connection, consulta: str) -> list[aiosqlite.Row]:
    async with db.execute(consulta) as cursor:
        return list(await cursor.fetchall())


class TestRechazoQueSeCorrige:
    async def test_vuelve_al_gate_y_publica_a_la_segunda(
        self,
        tmp_path: Path,
        ajustes: Settings,
        transporte: TransporteFalso,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        llamadas, falso = navegador_que_falla(veces=1)
        monkeypatch.setattr(render, "en_navegador", falso)
        ruta = tmp_path / "proyectos" / "rechazada.db"

        assert await _recorrer(ruta, ajustes, transporte) == "Idle"
        assert len(llamadas) == 2, "el render se juzga en cada paso por PublishVersion"

        async with abrir_novela(ruta) as db:
            versiones = await _uno(db, "SELECT numero FROM version_novela")
            assert [int(v["numero"]) for v in versiones] == [1], "el rechazo no dejo version"
            notas = await _uno(
                db, "SELECT valor FROM score WHERE validador = 'render_visual' ORDER BY id"
            )
            assert [float(n["valor"]) for n in notas] == [0.0, 1.0]
            pendientes = await _uno(
                db,
                "SELECT 1 FROM incidencia WHERE validador = 'render_visual' "
                "AND capitulo_version_id IS NULL",
            )
            assert pendientes == [], "publicada, el rechazo anterior ya no esta abierto"
            juicios = await _uno(db, "SELECT 1 FROM score WHERE validador = 'juez_rubrica'")
            assert len(juicios) == 2, "tras el rechazo la novela vuelve a pasar por el juez"


class TestRechazoQueNoSeCorrige:
    async def test_agota_el_tope_y_para_sin_publicar(
        self,
        tmp_path: Path,
        ajustes: Settings,
        transporte: TransporteFalso,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _, falso = navegador_que_falla(veces=99)
        monkeypatch.setattr(render, "en_navegador", falso)
        ruta = tmp_path / "proyectos" / "irrecuperable.db"

        assert await _recorrer(ruta, ajustes, transporte) == "Fail"

        async with abrir_novela(ruta) as db:
            assert await _uno(db, "SELECT 1 FROM version_novela") == []
            rechazo = await _uno(
                db,
                "SELECT mensaje, ubicacion FROM incidencia WHERE validador = 'render_visual' "
                "AND capitulo_version_id IS NULL",
            )
            assert [(r["mensaje"], r["ubicacion"]) for r in rechazo] == [
                ("El capitulo 2 se pinta sin texto.", "cap2")
            ]
