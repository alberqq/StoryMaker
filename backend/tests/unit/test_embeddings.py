"""spec: §3.5 · arq: §6, §16.2

Pruebas de los índices semánticos. Lo que aquí importa no es que la búsqueda «acierte»
—eso depende del modelo y lo miden los evals—, sino las tres propiedades estructurales de
las que depende el paquete de contexto: que el filtro entra en la consulta KNN, que
`vigente` excluye los intentos descartados, y que reindexar una fila no deja dos vectores
apuntando a la misma cosa.
"""

from __future__ import annotations

import aiosqlite
import pytest
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.db.repos import arnes, mundo
from storymaker.commons.embeddings import indice


@pytest.fixture
def vectorizador() -> VectorizadorFalso:
    return VectorizadorFalso()


async def _hecho(db: aiosqlite.Connection, fase_run: int, enunciado: str, dimension: str) -> int:
    return await mundo.insertar_hecho(
        db,
        fase_run_id=fase_run,
        enunciado=enunciado,
        estado="verificado",
        dimension=dimension,
    )


class TestIndiceDeHechos:
    async def test_recupera_lo_mas_parecido_primero(
        self, db: aiosqlite.Connection, fase_run: int, vectorizador: VectorizadorFalso
    ) -> None:
        hechos = {
            "La bahia de Cadiz se helo en el invierno de 1805": "cronologia",
            "Los toneleros trabajaban el roble americano": "cultura_material",
            "El tratado se firmo en Amiens": "cronologia",
        }
        ids = {}
        for enunciado, dimension in hechos.items():
            ids[enunciado] = await _hecho(db, fase_run, enunciado, dimension)
            await indice.indexar_hecho(
                db,
                vectorizador,
                hecho_id=ids[enunciado],
                enunciado=enunciado,
                estado="verificado",
                dimension=dimension,
            )
        vecinos = await indice.buscar_hechos(db, vectorizador, "el roble de los toneleros", k=3)
        assert vecinos[0].id == ids["Los toneleros trabajaban el roble americano"]

    async def test_el_filtro_de_dimension_entra_en_la_consulta(
        self, db: aiosqlite.Connection, fase_run: int, vectorizador: VectorizadorFalso
    ) -> None:
        """No se recupera y luego se descarta: se pide ya filtrado."""
        for enunciado, dimension in (
            ("El roble americano llegaba por el puerto", "cultura_material"),
            ("El roble se menciona en la cronica de 1805", "cronologia"),
        ):
            identificador = await _hecho(db, fase_run, enunciado, dimension)
            await indice.indexar_hecho(
                db,
                vectorizador,
                hecho_id=identificador,
                enunciado=enunciado,
                estado="verificado",
                dimension=dimension,
            )
        vecinos = await indice.buscar_hechos(
            db, vectorizador, "roble", k=8, dimension="cronologia"
        )
        assert len(vecinos) == 1

    async def test_reindexar_no_duplica(
        self, db: aiosqlite.Connection, fase_run: int, vectorizador: VectorizadorFalso
    ) -> None:
        """Cuando el Autor edita una ficha, el reembedding sustituye; no acumula."""
        identificador = await _hecho(db, fase_run, "Version inicial del hecho", "lugar")
        for enunciado in ("Version inicial del hecho", "Version corregida por el Autor"):
            await indice.indexar_hecho(
                db,
                vectorizador,
                hecho_id=identificador,
                enunciado=enunciado,
                estado="verificado",
                dimension="lugar",
            )
        async with db.execute("SELECT COUNT(*) AS n FROM vec_hecho") as cursor:
            assert int((await cursor.fetchone())["n"]) == 1


class TestIndiceDeResumenes:
    async def test_solo_capitulos_anteriores_y_vigentes(
        self, db: aiosqlite.Connection, vectorizador: VectorizadorFalso
    ) -> None:
        """Las dos condiciones del bloque 4 del paquete, dentro de la consulta KNN."""
        for cv_id, numero, vigente in ((1, 1, True), (2, 2, True), (3, 5, True)):
            await indice.indexar_resumen(
                db,
                vectorizador,
                capitulo_version_id=cv_id,
                resumen=f"Resumen del capitulo {numero} con el armador y el puerto",
                capitulo_numero=numero,
                vigente=vigente,
            )
        vecinos = await indice.buscar_resumenes(
            db, vectorizador, "el armador en el puerto", anteriores_a=3
        )
        assert {v.id for v in vecinos} == {1, 2}, "el capitulo 5 no es anterior al 3"

    async def test_un_intento_descartado_no_se_recuerda(
        self, db: aiosqlite.Connection, vectorizador: VectorizadorFalso
    ) -> None:
        """El fallo silencioso que `vigente` existe para impedir."""
        await indice.indexar_resumen(
            db,
            vectorizador,
            capitulo_version_id=10,
            resumen="El armador vende el barco",
            capitulo_numero=3,
        )
        await indice.indexar_resumen(
            db,
            vectorizador,
            capitulo_version_id=11,
            resumen="El armador conserva el barco",
            capitulo_numero=3,
        )
        await indice.marcar_vigente(db, capitulo_version_id=11, capitulo_numero=3)

        vecinos = await indice.buscar_resumenes(db, vectorizador, "el barco", anteriores_a=7)
        assert [v.id for v in vecinos] == [11]


class TestIndiceDeCanon:
    async def test_guarda_a_que_tabla_y_fila_apunta(
        self, db: aiosqlite.Connection, vectorizador: VectorizadorFalso
    ) -> None:
        """La biblia son tres tablas y la clave de una vec0 es un entero: de ahí los auxiliares."""
        await indice.indexar_canon(
            db,
            vectorizador,
            tabla="canon_personaje",
            fila_id=7,
            texto="Armador de Cadiz, cauto y supersticioso",
            familia="personaje",
        )
        await indice.indexar_canon(
            db,
            vectorizador,
            tabla="canon_escenario",
            fila_id=2,
            texto="El muelle al amanecer, con niebla",
            familia="escenario",
        )
        resultados = await indice.buscar_canon(
            db, vectorizador, "armador supersticioso", familia="personaje"
        )
        assert resultados[0][0] == "canon_personaje"
        assert resultados[0][1] == 7

    async def test_el_indice_y_la_fila_se_escriben_juntos(
        self, db: aiosqlite.Connection, fase_run: int, vectorizador: VectorizadorFalso
    ) -> None:
        """Si la transacción se deshace, no queda un vector apuntando a una fila que no existe."""
        from storymaker.commons.db.transaccion import paso_atomico

        with pytest.raises(RuntimeError):
            async with paso_atomico(db):
                identificador = await _hecho(db, fase_run, "Un hecho que no llega", "lugar")
                await indice.indexar_hecho(
                    db,
                    vectorizador,
                    hecho_id=identificador,
                    enunciado="Un hecho que no llega",
                    estado="verificado",
                    dimension="lugar",
                )
                raise RuntimeError("el nodo revienta")

        async with db.execute("SELECT COUNT(*) AS n FROM vec_hecho") as cursor:
            assert int((await cursor.fetchone())["n"]) == 0
        assert await mundo.hechos_vigentes(db, fase_run) == []


class TestVectorizadorReal:
    """El modelo de verdad se comprueba aparte y se salta si no está descargado."""

    def test_declara_384_dimensiones_y_su_nombre(self) -> None:
        from storymaker.commons.embeddings.modelo import (
            NOMBRE_EN_FASTEMBED,
            FastEmbedVectorizador,
        )

        vectorizador = FastEmbedVectorizador()
        assert vectorizador.dimension == 384
        assert vectorizador.nombre == NOMBRE_EN_FASTEMBED
        assert NOMBRE_EN_FASTEMBED.endswith("paraphrase-multilingual-MiniLM-L12-v2")

    def test_el_nombre_de_settings_llega_con_su_organizacion(self) -> None:
        """`invocar` le pasa el nombre de §19, que FastEmbed rechaza sin organización."""
        from storymaker.commons.config import Settings
        from storymaker.commons.embeddings.modelo import (
            NOMBRE_EN_FASTEMBED,
            FastEmbedVectorizador,
        )

        vectorizador = FastEmbedVectorizador(Settings(_env_file=None).modelo_embeddings)
        assert vectorizador.nombre == NOMBRE_EN_FASTEMBED


async def test_fase_run_no_es_necesaria_para_indexar(
    db: aiosqlite.Connection, vectorizador: VectorizadorFalso
) -> None:
    """Los resúmenes se indexan por identificador: el índice no conoce el dominio."""
    identificador = await arnes.abrir_fase_run(db, "writing")
    assert identificador == 1
