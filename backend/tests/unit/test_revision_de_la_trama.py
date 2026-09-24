"""spec: §4.3 · arq: §4, §11c

Pruebas unitarias de `specs/trama-rehacible/spec.md`: la cronología de la escaleta sin
Lean, la cobertura que se repara sola y la revisión tal como la sirve el gate.
"""

from __future__ import annotations

import sqlite3

import aiosqlite
import pytest
from dobles.fabrica import NovelaDePrueba, poblar
from dobles.vectorizador import VectorizadorFalso

from storymaker.api.seguimiento import revision_de_la_trama
from storymaker.commons.db.repos import intake as repo_intake
from storymaker.commons.formal.evaluacion import evaluar
from storymaker.commons.formal.generador import Evento, NovelaLean, Persona, a_momento
from storymaker.plotting import gate, trama
from storymaker.plotting.esquemas import HuecoPropuesto


@pytest.fixture
async def novela(db: aiosqlite.Connection) -> NovelaDePrueba:
    return await poblar(db)


def _momento(fecha: str) -> int:
    momento = a_momento(fecha)
    assert momento is not None
    return momento


class TestCronologiaSinLean:
    def test_nadie_despues_de_morir(self) -> None:
        novela = NovelaLean(
            personas=(Persona(1, "Fray Luis", _momento("1527-01-01"), _momento("1591-08-23")),),
            eventos=(Evento(1, "cap3-esc1", _momento("1595-01-01"), 1, (1,)),),
        )
        veredicto = evaluar(novela)
        assert not veredicto.correcto
        assert veredicto.incidencias[0].ubicacion == "cap3-esc1"
        assert "1591-08-23" in veredicto.incidencias[0].mensaje

    def test_un_escenario_desconocido_no_es_estar_en_otro_sitio(self) -> None:
        dia = _momento("1572-05-01")
        novela = NovelaLean(
            personas=(Persona(1, "Ana", _momento("1550-01-01")),),
            eventos=(Evento(1, "a", dia, 0, (1,)), Evento(2, "b", dia, 3, (1,))),
        )
        assert evaluar(novela).correcto

    async def test_sin_fecha_de_nacimiento_no_nace_en_1800(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Con `0` como nacimiento, toda escena anterior a 1800 salía como imposible."""
        await db.execute("UPDATE plan_escena SET fecha_narrativa = '1572-05-01'")
        cronologia = await gate.cronologia_de_la_escaleta(db)
        tomasa = next(p for p in cronologia.personas if p.nombre == "Tomasa")
        assert tomasa.nacimiento == gate.NACIMIENTO_DESCONOCIDO
        assert not [i for i in evaluar(cronologia).incidencias if "Tomasa" in i.mensaje]


class TestCoberturaReparada:
    async def test_el_obligatorio_suelto_se_ancla_y_se_dice_donde(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        dato = await repo_intake.insertar_dato(
            db,
            tipo="objeto",
            valor_json='{"valor": "la brujula del abuelo"}',
            origen="entrevista",
            obligatorio=True,
        )
        puerta = await gate.revisar(db, VectorizadorFalso())

        assert not await repo_intake.obligatorios_sin_anclar(db)
        assert not any(i.validador == "cobertura_anclada" for i in puerta.incidencias)
        reparada = next(i for i in puerta.incidencias if i.validador == "cobertura_reparada")
        assert "la brujula del abuelo" in reparada.mensaje
        async with db.execute("SELECT COUNT(*) FROM plan_anclaje WHERE dato_id = ?", (dato,)) as c:
            fila = await c.fetchone()
        assert fila is not None and int(fila[0]) == 1


class TestRevisionEnElGate:
    async def test_el_gate_sirve_lo_que_la_revision_guardo(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """El arco plano del homenajeado es grave; la cobertura reparada, un aviso."""
        await db.execute("UPDATE canon_arco SET tipo = 'plano'")
        # Una tercera escena con el homenajeado: con tres ya es recurrente y se le exige arco.
        cursor = await db.execute(
            "INSERT INTO plan_escena (capitulo_id, orden, objetivo) "
            "SELECT id, 2, 'volver al muelle' FROM plan_capitulo WHERE numero = 1"
        )
        await db.execute(
            "INSERT INTO plan_escena_personaje (escena_id, personaje_id) "
            "SELECT ?, homenajeado_id FROM canon_obra",
            (cursor.lastrowid,),
        )
        await repo_intake.insertar_dato(
            db,
            tipo="objeto",
            valor_json='{"valor": "un farol"}',
            origen="entrevista",
            obligatorio=True,
        )
        await gate.revisar(db, VectorizadorFalso())
        revision = await revision_de_la_trama(db)
        validadores = [a.validador for a in revision.avisos]
        assert validadores[0] == "arco_anclado"
        assert revision.avisos[0].grave, "lo grave va primero"
        assert "cobertura_reparada" in validadores

    async def test_los_huecos_salen_con_su_escena(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        from storymaker.commons.db.repos import plan
        from storymaker.plotting.nodos import registrar_hueco

        async with db.execute(
            "SELECT e.id FROM plan_escena e JOIN plan_capitulo c ON c.id = e.capitulo_id "
            "WHERE c.numero = 1"
        ) as cursor:
            fila = await cursor.fetchone()
        assert fila is not None
        await registrar_hueco(
            db, HuecoPropuesto(pregunta="Que se comia", escena="x"), {"x": fila[0]}
        )
        revision = await revision_de_la_trama(db)
        assert [(h.pregunta, h.capitulo, h.resultado) for h in revision.huecos] == [
            ("Que se comia", 1, None)
        ]
        assert await plan.huecos_de_la_trama(db)


class TestCuandoSePlanifica:
    async def test_sin_gate_de_rehacer_la_trama_se_queda(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Volver de un hueco o reanudar tras un fallo no pasan por el gate: no replanifican."""
        assert not await trama.hay_que_planificar(db)

    async def test_con_un_capitulo_escrito_la_trama_no_se_borra(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Las claves foráneas son el cerrojo: rehacer solo cabe antes de escribir."""
        with pytest.raises(sqlite3.IntegrityError):
            await trama.borrar(db)
