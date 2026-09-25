"""spec: §4.4 · arq: §4, §11a, §11c

Pruebas unitarias de `specs/escritura/spec.md`: los nombres descriptivos, la cronología que
se comprueba en Writing y al publicar, y su bloqueo en la pasada del extractor.
"""

from __future__ import annotations

import aiosqlite
import pytest
from dobles.agente_falso import TransporteFalso
from dobles.fabrica import NovelaDePrueba, poblar
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.agents.techos import Perfil
from storymaker.commons.config import Settings
from storymaker.commons.db.repos import texto
from storymaker.commons.formal.cronologia import cronologia_de_la_novela, verificar_cronologia
from storymaker.commons.graph.dependencias import Dependencias, usando
from storymaker.commons.obs.trazas import ObservadorNulo
from storymaker.commons.validation.chapter_validator import nombres_exactos
from storymaker.commons.validation.modelos import CapituloEnRevision, Severidad
from storymaker.writing import extraccion
from storymaker.writing.esquemas import (
    EventoNarrativo,
    SalidaExtractorDeCapitulo,
    VeredictoDeEjecucion,
)


@pytest.fixture
async def novela(db: aiosqlite.Connection) -> NovelaDePrueba:
    return await poblar(db)


def _capitulo(texto_: str, *nombres: str) -> CapituloEnRevision:
    return CapituloEnRevision(
        numero=1,
        texto=texto_,
        palabras=len(texto_.split()),
        rango_palabras=(1, 100),
        nombres_canonicos=nombres,
    )


def _salida(momento: str, participantes: list[int], clave: str = "e1") -> SalidaExtractorDeCapitulo:
    return SalidaExtractorDeCapitulo(
        resumen="resumen",
        eventos=[
            EventoNarrativo(
                clave=clave,
                descripcion="algo ocurre",
                momento=momento,
                escena=1,
                participantes=participantes,
            )
        ],
        veredicto=VeredictoDeEjecucion(),
    )


class TestNombresDescriptivos:
    def test_el_nombre_descriptivo_en_minuscula_no_es_otra_grafia(self) -> None:
        """En `metro`, «el padre de Julia» tumbó el capítulo 1 tres veces."""
        texto_ = "Cuando el padre de Julia llego, la cocina olia a caldo."
        assert nombres_exactos(_capitulo(texto_, "Padre de Julia")) == []

    def test_un_apellido_en_minuscula_sigue_siendo_otra_grafia(self) -> None:
        texto_ = "Manuel ferrer bajo al muelle."
        (incidencia,) = nombres_exactos(_capitulo(texto_, "Manuel Ferrer"))
        assert incidencia.bloquea

    def test_un_nombre_de_una_palabra_no_se_escribe_en_minuscula(self) -> None:
        (incidencia,) = nombres_exactos(_capitulo("Llego tomasa con el pan.", "Tomasa"))
        assert incidencia.bloquea


class TestCronologiaDeLaNovela:
    async def test_solo_cuenta_lo_aprobado_y_el_intento_en_curso(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Un intento descartado describe algo que ya no está en la novela."""
        descartado = await texto.insertar_capitulo_version(
            db, capitulo_id=novela.capitulo_2, fase_run_id=novela.fase_run, texto="a", intento=1
        )
        en_curso = await texto.insertar_capitulo_version(
            db, capitulo_id=novela.capitulo_2, fase_run_id=novela.fase_run, texto="b", intento=2
        )
        await extraccion.volcar_cronologia(
            db,
            _salida("1750-01-01", [novela.homenajeado]),
            capitulo_version_id=descartado,
            numero=2,
        )
        await extraccion.volcar_cronologia(
            db,
            _salida("1805-04-11", [novela.homenajeado]),
            capitulo_version_id=en_curso,
            numero=2,
        )
        claves = {e.clave for e in (await cronologia_de_la_novela(db)).eventos}
        assert not any(c.startswith("cap2-") for c in claves), "nada aprobado todavía"
        con = await cronologia_de_la_novela(db, con_version=en_curso)
        assert {e.clave for e in con.eventos if e.clave.startswith("cap2-")} == {
            f"cap2-v{en_curso}-e1"
        }

    async def test_cada_intento_escribe_sus_eventos(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Con la clave sin versión, el intento 2 heredaba la fila errónea del 1."""
        uno = await texto.insertar_capitulo_version(
            db, capitulo_id=novela.capitulo_2, fase_run_id=novela.fase_run, texto="a", intento=1
        )
        dos = await texto.insertar_capitulo_version(
            db, capitulo_id=novela.capitulo_2, fase_run_id=novela.fase_run, texto="b", intento=2
        )
        for version, momento in ((uno, "1750-01-01"), (dos, "1805-04-11")):
            await extraccion.volcar_cronologia(
                db,
                _salida(momento, [novela.homenajeado]),
                capitulo_version_id=version,
                numero=2,
            )
        async with db.execute(
            "SELECT momento FROM cronologia_evento WHERE capitulo_version_id = ?", (dos,)
        ) as cursor:
            assert [f["momento"] for f in await cursor.fetchall()] == ["1805-04-11"]

    async def test_antes_de_nacer_bloquea_y_se_calcula_sin_lean(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        version = await texto.insertar_capitulo_version(
            db, capitulo_id=novela.capitulo_2, fase_run_id=novela.fase_run, texto="a"
        )
        await extraccion.volcar_cronologia(
            db,
            _salida("1750-01-01", [novela.homenajeado]),
            capitulo_version_id=version,
            numero=2,
        )
        incidencias = await verificar_cronologia(
            await cronologia_de_la_novela(db, con_version=version),
            bloquea=True,
            validador="cronologia_capitulo",
        )
        (incidencia,) = incidencias
        assert incidencia.severidad is Severidad.BLOQUEANTE
        assert incidencia.validador == "cronologia_capitulo"
        assert "Manuel Ferrer" in incidencia.mensaje


class TestCronologiaEnElExtractor:
    async def test_el_capitulo_que_pone_a_alguien_antes_de_nacer_vuelve_al_editor(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        from storymaker.writing.nodos import CRONOLOGIA_DEL_CAPITULO, extraer

        version = await texto.insertar_capitulo_version(
            db,
            capitulo_id=novela.capitulo_2,
            fase_run_id=novela.fase_run,
            texto="Manuel Ferrer ya discutia en el muelle.",
        )
        falso = TransporteFalso().preparar(
            Perfil.EXTRACTOR_CAPITULO, _salida("1750-01-01", [novela.homenajeado])
        )
        with usando(
            Dependencias(
                db=db,
                settings=Settings(_env_file=None),
                transporte=falso,
                vectorizador=VectorizadorFalso(),
                observador=ObservadorNulo(),
            )
        ):
            incidencias = await extraer(version, 2)
        bloqueantes = [i for i in incidencias if i.bloquea]
        assert [i.validador for i in bloqueantes] == [CRONOLOGIA_DEL_CAPITULO]


class TestContradiccionesDelJuez:
    async def test_se_guardan_con_sus_capitulos_y_llegan_al_gate(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """En `metro` la edad de la homenajeada cambió del capítulo 1 al 5 y nadie lo vio."""
        from storymaker.commons.db.repos import arnes
        from storymaker.publication.nodos import registrar_contradicciones
        from storymaker.writing import gate as gate_de_escritura

        await registrar_contradicciones(
            db, ["Capítulo 1 le da 7 años en 1900 y el capítulo 5, 75 en 1979."]
        )
        await registrar_contradicciones(db, ["El Capítulo 2 contradice al 4."])
        async with db.execute(
            "SELECT ubicacion FROM incidencia WHERE validador = 'juez_contradiccion'"
        ) as cursor:
            assert [f["ubicacion"] for f in await cursor.fetchall()] == ["cap2"], (
                "cada juicio sustituye al anterior"
            )
        informe = await gate_de_escritura.construir(db)
        assert "El juez encontro 1 contradiccion(es)" in informe.como_texto()
        assert await arnes.incidencias_sin_capitulo(db, "juez_contradiccion")

    def test_el_aviso_de_terminada_las_cuenta(self) -> None:
        from storymaker.gates.notifier import aviso_de_terminada, texto_de

        texto_ = texto_de(aviso_de_terminada("x", version=1, coste_usd=0.1, contradicciones=2))
        assert "2 contradiccion(es)" in texto_
        assert "contradic" not in texto_de(aviso_de_terminada("x", version=1, coste_usd=0.1))
