"""spec: §4.5, §4.6 · arq: §4, §11a, §13

Pruebas de las fases 5 y 6.

Lo que se comprueba de Publication es **el orden**: que el render se juzga sobre la versión
candidata y antes de confirmar, porque un índice roto detectado después sería una versión ya
publicada sin adónde volver. Y de Regeneration, que la política de invalidación barata
funciona: qué se regenera, qué solo se revisa, y que la versión anterior sobrevive entera.
"""

from __future__ import annotations

import aiosqlite
import pytest
from dobles.fabrica import NovelaDePrueba, poblar
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.config import Settings
from storymaker.commons.db.repos import texto
from storymaker.commons.embeddings import indice
from storymaker.publication import manifiesto, render
from storymaker.publication.esquemas import (
    UMBRAL_DE_PUBLICACION,
    Criterio,
    Puntuacion,
    SalidaJuez,
)
from storymaker.publication.nodos import supera_el_umbral
from storymaker.regeneration import cambio, diff, nodos
from storymaker.regeneration.esquemas import CambioResuelto, ObjetoDelCambio


@pytest.fixture
def vectorizador() -> VectorizadorFalso:
    return VectorizadorFalso()


@pytest.fixture
def ajustes() -> Settings:
    return Settings(_env_file=None)


@pytest.fixture
async def novela(db: aiosqlite.Connection) -> NovelaDePrueba:
    return await poblar(db)


def rubrica(valor: int = 8) -> SalidaJuez:
    return SalidaJuez(
        puntuaciones=[
            Puntuacion(criterio=c, valor=valor, justificacion="una justificacion suficiente")
            for c in Criterio
        ]
    )


class TestJuez:
    def test_la_rubrica_son_siete_criterios(self) -> None:
        assert len(Criterio) == 7
        assert rubrica().completa

    def test_no_tiene_donde_devolver_texto(self) -> None:
        """Si pudiera editar, el mismo agente optimizaria la metrica que produce."""
        campos = set(SalidaJuez.model_fields)
        assert campos == {"puntuaciones"}
        assert not (campos & {"texto", "correcciones", "parche"})

    def test_cada_criterio_exige_justificacion(self) -> None:
        """Es lo que hace comparable el juicio del modelo con el de una persona."""
        with pytest.raises(ValueError, match="justificacion"):
            Puntuacion(criterio=Criterio.PROSA, valor=7, justificacion="bien")

    def test_el_umbral_se_calcula_en_python(self) -> None:
        assert supera_el_umbral(rubrica(8)) is True
        assert supera_el_umbral(rubrica(4)) is False
        assert UMBRAL_DE_PUBLICACION == 6.0

    def test_senala_el_peor_criterio(self) -> None:
        salida = SalidaJuez(
            puntuaciones=[
                Puntuacion(criterio=Criterio.PROSA, valor=9, justificacion="se lee muy bien"),
                Puntuacion(criterio=Criterio.RITMO, valor=3, justificacion="se detiene mucho"),
            ]
        )
        assert salida.peor().criterio is Criterio.RITMO


class TestRenderVisual:
    async def test_una_lectura_completa_pasa(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        version = await texto.publicar_version(
            db, numero=1, capitulo_version_ids=[novela.version_capitulo_1]
        )
        lectura = await render.construir_lectura(db, version)
        assert render.render_visual(lectura) == []

    async def test_una_version_sin_capitulos_no_se_publica(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """G5 no admite excepcion: el render se juzga antes de confirmar."""
        version = await texto.publicar_version(db, numero=1, capitulo_version_ids=[])
        lectura = await render.construir_lectura(db, version)
        incidencias = render.render_visual(lectura)
        assert incidencias
        assert all(i.bloquea for i in incidencias)

    async def test_el_indice_tiene_que_ser_navegable(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        version = await texto.publicar_version(
            db, numero=1, capitulo_version_ids=[novela.version_capitulo_1]
        )
        lectura = await render.construir_lectura(db, version)
        roto = render.Lectura(
            titulo=lectura.titulo,
            portada=lectura.portada,
            indice="<ol></ol>",
            capitulos=lectura.capitulos,
            personajes=lectura.personajes,
        )
        assert any("navegable" in i.mensaje for i in render.render_visual(roto))

    async def test_la_lectura_sale_del_manifiesto_y_no_de_los_aprobados(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Renderizar otra cosa publicaria algo que el manifiesto no describe."""
        version = await texto.publicar_version(db, numero=1, capitulo_version_ids=[])
        lectura = await render.construir_lectura(db, version)
        assert lectura.capitulos == ()


class TestManifiesto:
    async def test_registra_el_modelo_de_embeddings(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba, ajustes: Settings
    ) -> None:
        """El sello no cubre los vectores: reindexar se detecta comparando manifiestos."""
        version = await texto.publicar_version(
            db, numero=1, capitulo_version_ids=[novela.version_capitulo_1]
        )
        datos = await manifiesto.reunir(db, ajustes)
        await manifiesto.escribir(db, version, datos)
        fila = await manifiesto.de_version(db, version)
        assert fila is not None
        assert "paraphrase-multilingual" in str(fila["embeddings_json"])
        assert "384" in str(fila["embeddings_json"])

    async def test_comparar_dice_que_cambio_y_cual_era_el_anterior(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba, ajustes: Settings
    ) -> None:
        primera = await texto.publicar_version(
            db, numero=1, capitulo_version_ids=[novela.version_capitulo_1]
        )
        await manifiesto.escribir(db, primera, await manifiesto.reunir(db, ajustes))

        otros = Settings(_env_file=None, modelo_embeddings="otro-modelo")
        segunda = await texto.publicar_version(
            db, numero=2, capitulo_version_ids=[novela.version_capitulo_1]
        )
        await manifiesto.escribir(db, segunda, await manifiesto.reunir(db, otros))

        diferencias = await manifiesto.comparar(db, primera, segunda)
        assert "embeddings_json" in diferencias
        antes, despues = diferencias["embeddings_json"]
        assert "paraphrase" in antes and "otro-modelo" in despues


class TestRegeneracion:
    async def test_el_alcance_separa_lo_caro_de_lo_barato(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Invalidacion barata, regeneracion cara: es la politica entera de la fase."""
        await texto.registrar_uso_hecho(
            db,
            capitulo_version_id=novela.version_capitulo_1,
            escena_id=novela.escena_1,
            hecho_id=novela.hecho_anclado,
        )
        alcance = await nodos.calcular_alcance(
            db, objeto=ObjetoDelCambio.HECHO, fila_id=novela.hecho_anclado
        )
        assert alcance.a_regenerar == (1,)
        assert alcance.a_invalidar == (2,)
        assert "Cada uno cuesta una escritura completa" in alcance.como_texto()

    async def test_si_nadie_lo_usa_no_hay_nada_que_regenerar(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        alcance = await nodos.calcular_alcance(
            db, objeto=ObjetoDelCambio.HECHO, fila_id=novela.hecho_suelto
        )
        assert alcance.total == 0
        assert "no hay nada que regenerar" in alcance.como_texto()

    async def test_se_modifica_la_fila_y_no_el_texto(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba, vectorizador: VectorizadorFalso
    ) -> None:
        """Un buscar-y-reemplazar sobre la prosa deja mintiendo a la biblia."""
        antes = await texto.capitulo_aprobado(db, novela.capitulo_1)
        assert antes is not None
        await cambio.aplicar(
            db,
            vectorizador,
            CambioResuelto(
                objeto=ObjetoDelCambio.PERSONAJE,
                fila_id=novela.homenajeado,
                campo="nombre",
                antes="Manuel Ferrer",
                despues="Manuel Ferrero",
            ),
        )
        despues = await texto.capitulo_aprobado(db, novela.capitulo_1)
        assert despues is not None
        assert despues["texto"] == antes["texto"], "el texto no se toca: se regenera despues"

    async def test_el_cambio_queda_en_el_audit_log_y_en_edicion_humana(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba, vectorizador: VectorizadorFalso
    ) -> None:
        """La intervencion del Autor se traza igual que la de un agente."""
        await cambio.aplicar(
            db,
            vectorizador,
            CambioResuelto(
                objeto=ObjetoDelCambio.PERSONAJE,
                fila_id=novela.homenajeado,
                campo="nombre",
                antes="Manuel Ferrer",
                despues="Manuel Ferrero",
                motivo="el comprador corrige el apellido",
            ),
        )
        async with db.execute("SELECT * FROM audit_log") as cursor:
            assert len(list(await cursor.fetchall())) == 1
        async with db.execute("SELECT * FROM edicion_humana") as cursor:
            fila = await cursor.fetchone()
        assert fila is not None
        assert fila["campo"] == "nombre"
        assert fila["motivo"] == "el comprador corrige el apellido"

    async def test_el_reembedding_acompana_al_cambio(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba, vectorizador: VectorizadorFalso
    ) -> None:
        """Sin el, la busqueda seguiria devolviendo el texto anterior a la correccion."""
        await indice.indexar_canon(
            db,
            vectorizador,
            tabla="canon_personaje",
            fila_id=novela.homenajeado,
            texto="Manuel Ferrer armador",
            familia="personaje",
        )
        await cambio.aplicar(
            db,
            vectorizador,
            CambioResuelto(
                objeto=ObjetoDelCambio.PERSONAJE,
                fila_id=novela.homenajeado,
                campo="nombre",
                antes="Manuel Ferrer",
                despues="Nicolas Ferrer",
            ),
        )
        resultados = await indice.buscar_canon(db, vectorizador, "Nicolas Ferrer")
        assert resultados and resultados[0][1] == novela.homenajeado

    async def test_la_busqueda_encuentra_la_fila_a_tocar(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba, vectorizador: VectorizadorFalso
    ) -> None:
        """Sin esto, la Fase 6 exigiria que el lector conociera los identificadores internos."""
        await indice.indexar_hecho(
            db,
            vectorizador,
            hecho_id=novela.hecho_anclado,
            enunciado="El roble americano llegaba a Cadiz desde La Habana",
            estado="verificado",
            dimension="cultura_material",
        )
        candidatos = await cambio.buscar_candidatos(db, vectorizador, "el roble venia de La Habana")
        assert candidatos
        assert candidatos[0].fila_id == novela.hecho_anclado


class TestDiff:
    async def test_un_capitulo_no_regenerado_se_comparte(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Sale gratis de que una version sea una lista de filas y no una copia."""
        primera = await texto.publicar_version(
            db, numero=1, capitulo_version_ids=[novela.version_capitulo_1]
        )
        segunda = await texto.publicar_version(
            db, numero=2, capitulo_version_ids=[novela.version_capitulo_1]
        )
        resultado = await diff.entre(db, primera, segunda)
        assert resultado.cambiados == ()
        assert "tienen los mismos capitulos" in resultado.como_texto()

    async def test_un_capitulo_regenerado_se_ve(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        nueva_version = await texto.insertar_capitulo_version(
            db,
            capitulo_id=novela.capitulo_1,
            fase_run_id=novela.fase_run,
            texto="La niebla volvio a subir, esta vez con otro nombre.",
            intento=2,
        )
        primera = await texto.publicar_version(
            db, numero=1, capitulo_version_ids=[novela.version_capitulo_1]
        )
        segunda = await texto.publicar_version(db, numero=2, capitulo_version_ids=[nueva_version])
        resultado = await diff.entre(db, primera, segunda)
        assert len(resultado.cambiados) == 1
        assert resultado.cambiados[0].estado == "regenerado"

    async def test_la_version_anterior_sobrevive_entera(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Es `PreviousVersionPreserved`, sostenida por el fichero y no por disciplina."""
        primera = await texto.publicar_version(
            db, numero=1, capitulo_version_ids=[novela.version_capitulo_1]
        )
        nueva = await texto.insertar_capitulo_version(
            db, capitulo_id=novela.capitulo_1, fase_run_id=novela.fase_run, texto="otra cosa",
            intento=2,
        )
        await texto.publicar_version(db, numero=2, capitulo_version_ids=[nueva])
        capitulos = await texto.capitulos_de_version(db, primera)
        assert [c["id"] for c in capitulos] == [novela.version_capitulo_1]
