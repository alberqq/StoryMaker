"""spec: §4.3 · arq: §4, §10

Pruebas de `specs/trama-rehacible/spec.md`: rehacer la Trama desde su gate, los huecos
anclados a su escena y la revisión que se guarda, se enseña y vuelve al arquitecto.

Recorren el grafo de verdad, con gates, hasta el de Plotting: lo que se comprueba es lo que
antes fallaba en silencio —el gate que volvía a abrirse idéntico tras «rehacer»—, y eso solo
se ve con la arista, el nodo y la base juntos.
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
from storymaker.commons.graph.run import Arranque, ResultadoInvocacion, invocar, reanudar
from storymaker.commons.obs.trazas import ObservadorNulo
from storymaker.gates.decisiones import aplicar
from storymaker.gates.notifier import NotifierNulo
from storymaker.investigation.esquemas import Dimension, HuecoResuelto
from storymaker.plotting.esquemas import HuecoPropuesto

CAPITULOS = 2
COMENTARIO = "Que el inspector sea el hermano de la maestra"


def _hasta_el_gate_de_la_trama(*arquitecturas: object, micro: int = 5) -> TransporteFalso:
    falso = TransporteFalso()
    falso.preparar(Perfil.ENTREVISTADOR, guion.entrevista(CAPITULOS))
    falso.preparar(Perfil.INVESTIGADOR_INICIAL, guion.investigacion())
    falso.preparar(Perfil.VERIFICADOR, guion.verificacion(), *[guion.verificacion()] * micro)
    falso.preparar(Perfil.ARQUITECTO, *arquitecturas)
    falso.preparar(Perfil.INVESTIGADOR_MICRO, *[guion.hueco_resuelto() for _ in range(micro)])
    return falso


async def _decidir(
    ruta: Path, ajustes: Settings, transporte: TransporteFalso, decision: str, comentario: str = ""
) -> ResultadoInvocacion:
    async with abrir_novela(ruta) as db:
        await aplicar(db, ObservadorNulo(), decision, comentario)
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


async def _llegar(ruta: Path, ajustes: Settings, transporte: TransporteFalso) -> None:
    await crear_novela(ruta)
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
    await _decidir(ruta, ajustes, transporte, "aprobar")


async def _uno(ruta: Path, consulta: str) -> int:
    async with abrir_novela(ruta) as db:
        async with db.execute(consulta) as cursor:
            fila = await cursor.fetchone()
    return int(fila[0]) if fila is not None and fila[0] is not None else 0


@pytest.fixture
def ajustes() -> Settings:
    return Settings(_env_file=None, gates_enabled=True, reintentos_por_capitulo=2)


class TestRehacer:
    async def test_rehacer_llama_otra_vez_al_arquitecto_y_sustituye_la_trama(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        ruta = tmp_path / "proyectos" / "rehacer.db"
        transporte = _hasta_el_gate_de_la_trama(
            guion.arquitectura(CAPITULOS), guion.arquitectura(CAPITULOS)
        )
        await _llegar(ruta, ajustes, transporte)
        assert transporte.veces(Perfil.ARQUITECTO) == 1
        primera = await _uno(ruta, "SELECT fase_run_id FROM canon_obra")

        resultado = await _decidir(ruta, ajustes, transporte, "rehacer", COMENTARIO)

        assert resultado.gate_abierto is not None, "vuelve a esperar en el gate de la Trama"
        assert transporte.veces(Perfil.ARQUITECTO) == 2
        assert await _uno(ruta, "SELECT COUNT(*) FROM plan_capitulo") == CAPITULOS
        assert await _uno(ruta, "SELECT COUNT(*) FROM canon_obra") == 1
        assert await _uno(ruta, "SELECT COUNT(*) FROM canon_personaje") == 2
        assert await _uno(ruta, "SELECT fase_run_id FROM canon_obra") > primera

    async def test_el_arquitecto_recibe_el_comentario_y_la_trama_anterior(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        ruta = tmp_path / "proyectos" / "comentario.db"
        transporte = _hasta_el_gate_de_la_trama(
            guion.arquitectura(CAPITULOS), guion.arquitectura(CAPITULOS)
        )
        await _llegar(ruta, ajustes, transporte)
        await _decidir(ruta, ajustes, transporte, "rehacer", COMENTARIO)

        primero, segundo = transporte.prompts[Perfil.ARQUITECTO]
        assert "--- Rehacer ---" not in primero
        assert "--- Rehacer ---" in segundo
        assert COMENTARIO in segundo
        assert "El reloj de la maestra" in segundo, "la trama anterior va como punto de partida"

    async def test_las_correcciones_del_gate_llegan_al_arquitecto(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        ruta = tmp_path / "proyectos" / "correccion.db"
        transporte = _hasta_el_gate_de_la_trama(
            guion.arquitectura(CAPITULOS), guion.arquitectura(CAPITULOS)
        )
        await _llegar(ruta, ajustes, transporte)
        async with abrir_novela(ruta) as db:
            await db.execute(
                "UPDATE canon_personaje SET objetivo = 'vengar a su padre' "
                "WHERE nombre = 'Don Emeterio'"
            )
            await db.commit()
        await _decidir(ruta, ajustes, transporte, "rehacer", "")

        assert "vengar a su padre" in transporte.prompts[Perfil.ARQUITECTO][1]

    async def test_aprobar_no_replanifica(self, tmp_path: Path, ajustes: Settings) -> None:
        ruta = tmp_path / "proyectos" / "aprobar.db"
        transporte = _hasta_el_gate_de_la_trama(guion.arquitectura(CAPITULOS))
        transporte.preparar(Perfil.ESCRITOR, guion.capitulo(1))
        transporte.preparar(Perfil.EXTRACTOR_CAPITULO, guion.extraccion(1))
        await _llegar(ruta, ajustes, transporte)
        await _decidir(ruta, ajustes, transporte, "aprobar")
        assert transporte.veces(Perfil.ARQUITECTO) == 1


class TestHuecosAnclados:
    async def test_el_hueco_se_ancla_a_la_escena_que_lo_pidio(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        ruta = tmp_path / "proyectos" / "hueco.db"
        hueco = HuecoPropuesto(
            pregunta="Como eran los pupitres",
            escena="c2e1",
            dimension=Dimension.CULTURA_MATERIAL,
            si_no_se_encuentra="Los pupitres eran bancos corridos de pino.",
        )
        transporte = _hasta_el_gate_de_la_trama(
            guion.arquitectura(CAPITULOS, huecos=(hueco,)), micro=1
        )
        await _llegar(ruta, ajustes, transporte)

        async with abrir_novela(ruta) as db:
            async with db.execute(
                """
                SELECT c.numero, a.tipo_vinculo, h.enunciado, u.resultado
                  FROM plan_hueco u
                  JOIN plan_anclaje a ON a.hecho_id = u.hecho_id
                  JOIN plan_escena e ON e.id = a.escena_id
                  JOIN plan_capitulo c ON c.id = e.capitulo_id
                  JOIN mundo_hecho h ON h.id = u.hecho_id
                """
            ) as cursor:
                filas = [tuple(f) for f in await cursor.fetchall()]
        assert filas == [
            (
                2,
                "cubre un hueco de la escaleta",
                "Los pupitres eran de madera con tintero empotrado.",
                "encontrado",
            )
        ]

    async def test_lo_no_encontrado_entra_con_la_propuesta_y_no_con_la_pregunta(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        ruta = tmp_path / "proyectos" / "inventado.db"
        hueco = HuecoPropuesto(
            pregunta="Como se llamaba la calle del mercado",
            escena="c1e1",
            dimension=Dimension.LUGAR,
            si_no_se_encuentra="La calle del mercado se llamaba de la Pescaderia.",
        )
        transporte = _hasta_el_gate_de_la_trama(guion.arquitectura(CAPITULOS, huecos=(hueco,)))
        transporte.respuestas[Perfil.INVESTIGADOR_MICRO] = [
            HuecoResuelto(encontrado=False, motivo="no aparece en las fuentes")
        ]
        await _llegar(ruta, ajustes, transporte)

        async with abrir_novela(ruta) as db:
            async with db.execute(
                "SELECT h.enunciado, h.dimension, h.origen FROM plan_hueco u "
                "JOIN mundo_hecho h ON h.id = u.hecho_id"
            ) as cursor:
                fila = await cursor.fetchone()
        assert fila is not None
        assert tuple(fila) == (
            "La calle del mercado se llamaba de la Pescaderia.",
            "lugar",
            "invencion_autorizada",
        )


class TestRevisionGuardada:
    async def test_la_revision_se_guarda_y_llega_al_arquitecto_al_rehacer(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        """Un personaje en dos escenarios el mismo día: la cronología lo ve sin Lean."""
        ruta = tmp_path / "proyectos" / "revision.db"
        arquitectura = guion.arquitectura(CAPITULOS)
        arquitectura.escenarios.append(
            arquitectura.escenarios[0].model_copy(
                update={"clave": "plaza", "descripcion": "La plaza"}
            )
        )
        segunda = arquitectura.capitulos[1].escenas[0]
        segunda.escenario = "plaza"
        segunda.fecha_narrativa = arquitectura.capitulos[0].escenas[0].fecha_narrativa
        transporte = _hasta_el_gate_de_la_trama(arquitectura, guion.arquitectura(CAPITULOS))
        await _llegar(ruta, ajustes, transporte)

        async with abrir_novela(ruta) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT mensaje FROM incidencia WHERE validador = 'cronologia_escaleta'"
            ) as cursor:
                avisos = [str(f["mensaje"]) for f in await cursor.fetchall()]
        assert avisos and "dos lugares" in avisos[0]

        await _decidir(ruta, ajustes, transporte, "rehacer", "")
        assert "dos lugares" in transporte.prompts[Perfil.ARQUITECTO][1]
