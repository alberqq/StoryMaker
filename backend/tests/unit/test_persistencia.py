"""spec: §3.1, §2.3 · arq: §7, §2 principio 5

Pruebas del esquema y del acceso a la base. Lo que se comprueba aquí no es que las
consultas funcionen —eso es lo fácil—, sino que **el fichero se defiende solo**: que un
enumerado fuera de rango aborta la transacción, que un capítulo no se puede reescribir
aunque alguien lo intente, y que el corpus queda de solo lectura en cuanto se sella.

Son las propiedades de clase A del hito: no dependen de que nadie recuerde respetarlas.
"""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from storymaker.commons.db.apertura import (
    VERSION_ESQUEMA,
    abrir_novela,
    crear_novela,
)
from storymaker.commons.db.repos import arnes, mundo, texto
from storymaker.commons.db.transaccion import paso_atomico
from storymaker.commons.errores import EsquemaDelFuturo, NovelaNoEncontrada


async def _capitulo(db: aiosqlite.Connection, numero: int = 1) -> int:
    cursor = await db.execute("INSERT INTO plan_capitulo (numero) VALUES (?)", (numero,))
    assert cursor.lastrowid is not None
    return cursor.lastrowid


class TestArranque:
    async def test_crear_novela_aplica_el_esquema_entero(self, tmp_path: Path) -> None:
        ruta = tmp_path / "novela.db"
        await crear_novela(ruta)
        async with abrir_novela(ruta) as db:
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
            ) as cursor:
                tablas = {str(fila["name"]) for fila in await cursor.fetchall()}
        # Una tabla de cada familia de §7, más las tres virtuales de sqlite-vec.
        assert {"intake_dato", "mundo_hecho", "canon_arco", "plan_escena"} <= tablas
        assert {"capitulo_version", "cronologia_evento", "fase_run", "manifiesto"} <= tablas
        assert {"vec_hecho", "vec_canon", "vec_resumen"} <= tablas

    async def test_los_pragmas_quedan_activos(self, db: aiosqlite.Connection) -> None:
        async with db.execute("PRAGMA journal_mode") as cursor:
            assert str((await cursor.fetchone())[0]).lower() == "wal"
        async with db.execute("PRAGMA foreign_keys") as cursor:
            assert int((await cursor.fetchone())[0]) == 1

    async def test_sqlite_vec_esta_cargado(self, db: aiosqlite.Connection) -> None:
        """Si no lo estuviera, el arranque se habría detenido en vez de llegar aquí."""
        async with db.execute("SELECT vec_version()") as cursor:
            assert (await cursor.fetchone())[0].startswith("v")

    async def test_abrir_una_novela_inexistente_no_la_crea(self, tmp_path: Path) -> None:
        """Equivocarse de nombre no puede tener como consecuencia una novela nueva."""
        with pytest.raises(NovelaNoEncontrada):
            async with abrir_novela(tmp_path / "no-existe.db"):
                pass
        assert not (tmp_path / "no-existe.db").exists()

    async def test_no_se_abre_un_esquema_del_futuro(self, tmp_path: Path) -> None:
        ruta = tmp_path / "novela.db"
        await crear_novela(ruta)
        async with abrir_novela(ruta) as db:
            await db.execute(f"PRAGMA user_version={VERSION_ESQUEMA + 7}")
            await db.commit()
        with pytest.raises(EsquemaDelFuturo):
            async with abrir_novela(ruta):
                pass

    async def test_reabrir_no_reaplica_el_esquema(self, tmp_path: Path) -> None:
        """La migración es idempotente: abrir dos veces no duplica ni rompe nada."""
        ruta = tmp_path / "novela.db"
        await crear_novela(ruta)
        async with abrir_novela(ruta) as db:
            identificador = await arnes.abrir_fase_run(db, "intake")
            await db.commit()
        async with abrir_novela(ruta) as db:
            async with db.execute("SELECT COUNT(*) AS n FROM fase_run") as cursor:
                assert int((await cursor.fetchone())["n"]) == 1
            assert identificador == 1


class TestEnumerados:
    """Un valor fuera del enumerado aborta la transacción; no se normaliza ni se corrige."""

    async def test_estado_epistemico_invalido(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        with pytest.raises(aiosqlite.IntegrityError):
            await mundo.insertar_hecho(
                db,
                fase_run_id=fase_run,
                enunciado="Cadiz era un puerto",
                estado="bastante_probable",
                dimension="lugar",
            )

    async def test_dimension_fuera_de_las_seis(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        with pytest.raises(aiosqlite.IntegrityError):
            await mundo.insertar_hecho(
                db,
                fase_run_id=fase_run,
                enunciado="Algo",
                estado="verificado",
                dimension="gastronomia",
            )

    async def test_severidad_invalida(self, db: aiosqlite.Connection) -> None:
        with pytest.raises(aiosqlite.IntegrityError):
            await arnes.registrar_incidencia(
                db, validador="longitud_capitulo", severidad="grave", mensaje="x"
            )

    async def test_la_cita_no_pasa_de_300_caracteres(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        """El tope obliga a señalar el fragmento, no a volcar media página."""
        with pytest.raises(aiosqlite.IntegrityError):
            await mundo.insertar_hecho(
                db,
                fase_run_id=fase_run,
                enunciado="Algo",
                estado="verificado",
                dimension="lugar",
                cita="x" * 301,
            )

    async def test_lo_inventado_no_puede_decir_que_esta_respaldado(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        """Un dato inventado con permiso no tiene cita, así que no hay nada que comprobar."""
        with pytest.raises(aiosqlite.IntegrityError):
            await mundo.insertar_hecho(
                db,
                fase_run_id=fase_run,
                enunciado="La calle se llamaba de los Toneleros",
                estado="inferido",
                dimension="lugar",
                origen="invencion_autorizada",
                respaldo="respaldado",
            )

    async def test_un_anclaje_apunta_a_una_sola_cosa(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        """Hecho, entidad o dato del comprador: exactamente uno de los tres."""
        capitulo = await _capitulo(db)
        cursor = await db.execute(
            "INSERT INTO plan_escena (capitulo_id, orden) VALUES (?, 1)", (capitulo,)
        )
        escena = cursor.lastrowid
        with pytest.raises(aiosqlite.IntegrityError):
            await db.execute(
                "INSERT INTO plan_anclaje (escena_id, tipo_vinculo) VALUES (?, 'ambienta')",
                (escena,),
            )


class TestInmutabilidad:
    async def test_el_texto_de_un_capitulo_no_se_reescribe(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        capitulo = await _capitulo(db)
        version = await texto.insertar_capitulo_version(
            db, capitulo_id=capitulo, fase_run_id=fase_run, texto="El armador miro al mar."
        )
        with pytest.raises(aiosqlite.IntegrityError):
            await db.execute(
                "UPDATE capitulo_version SET texto = ? WHERE id = ?", ("otro texto", version)
            )

    async def test_pero_su_estado_si_cambia(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        """`ApproveChapter` marca el estado: lo inmutable es lo generado, no la fila entera."""
        capitulo = await _capitulo(db)
        version = await texto.insertar_capitulo_version(
            db, capitulo_id=capitulo, fase_run_id=fase_run, texto="El armador miro al mar."
        )
        await texto.aprobar_capitulo(db, version)
        fila = await texto.capitulo_aprobado(db, capitulo)
        assert fila is not None
        assert fila["estado"] == "aprobado"
        assert fila["palabras"] == 5

    async def test_un_capitulo_no_se_borra(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        capitulo = await _capitulo(db)
        version = await texto.insertar_capitulo_version(
            db, capitulo_id=capitulo, fase_run_id=fase_run, texto="Texto."
        )
        with pytest.raises(aiosqlite.IntegrityError):
            await db.execute("DELETE FROM capitulo_version WHERE id = ?", (version,))

    async def test_una_version_publicada_no_se_toca(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        """Es la promesa de `PreviousVersionPreserved`, sostenida por el fichero."""
        capitulo = await _capitulo(db)
        version = await texto.insertar_capitulo_version(
            db, capitulo_id=capitulo, fase_run_id=fase_run, texto="Texto."
        )
        publicada = await texto.publicar_version(db, numero=1, capitulo_version_ids=[version])
        with pytest.raises(aiosqlite.IntegrityError):
            await db.execute("UPDATE version_novela SET numero = 99 WHERE id = ?", (publicada,))
        with pytest.raises(aiosqlite.IntegrityError):
            await db.execute("DELETE FROM version_capitulo WHERE version_id = ?", (publicada,))

    async def test_la_identidad_de_una_ejecucion_no_cambia(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        with pytest.raises(aiosqlite.IntegrityError):
            await db.execute("UPDATE fase_run SET fase = 'writing' WHERE id = ?", (fase_run,))

    async def test_pero_una_ejecucion_si_se_cierra(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        await arnes.cerrar_fase_run(
            db, fase_run, estado="completada", tokens_in=1200, tokens_out=800, coste_usd=0.03
        )
        async with db.execute("SELECT * FROM fase_run WHERE id = ?", (fase_run,)) as cursor:
            fila = await cursor.fetchone()
        assert fila is not None
        assert fila["estado"] == "completada"
        assert fila["fin"] is not None


class TestSelloDelCorpus:
    async def test_antes_del_sello_el_verificador_puede_degradar(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        hecho = await mundo.insertar_hecho(
            db,
            fase_run_id=fase_run,
            enunciado="La bahia se helo en 1805",
            estado="verificado",
            dimension="cronologia",
            cita="fragmento",
        )
        await mundo.anotar_respaldo(db, hecho, "no_respaldado")
        filas = await mundo.hechos_vigentes(db, fase_run)
        assert filas[0]["respaldo"] == "no_respaldado"
        assert filas[0]["estado"] == "inferido", "un hecho sin respaldo se degrada, no se borra"

    async def test_tras_el_sello_el_corpus_es_de_solo_lectura(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        hecho = await mundo.insertar_hecho(
            db,
            fase_run_id=fase_run,
            enunciado="Cadiz tenia astilleros",
            estado="verificado",
            dimension="estructura_social",
        )
        await mundo.sellar_corpus(db, fase_run)
        with pytest.raises(aiosqlite.IntegrityError):
            await mundo.anotar_respaldo(db, hecho, "respaldado")
        with pytest.raises(aiosqlite.IntegrityError):
            await mundo.insertar_hecho(
                db,
                fase_run_id=fase_run,
                enunciado="Un hecho tardio",
                estado="inferido",
                dimension="lugar",
            )
        with pytest.raises(aiosqlite.IntegrityError):
            await db.execute("DELETE FROM mundo_hecho WHERE id = ?", (hecho,))

    async def test_el_hash_no_depende_del_orden_de_insercion(self, tmp_path: Path) -> None:
        """Dos corpus idénticos dan el mismo sello aunque se escribieran en otro orden."""
        hashes = []
        for orden in ([0, 1, 2], [2, 0, 1]):
            ruta = tmp_path / f"n{orden[0]}{orden[1]}{orden[2]}.db"
            enunciados = ["alfa", "beta", "gamma"]
            async with abrir_novela(ruta, crear=True) as db:
                ejecucion = await arnes.abrir_fase_run(db, "investigation")
                for i in orden:
                    await mundo.insertar_hecho(
                        db,
                        fase_run_id=ejecucion,
                        enunciado=enunciados[i],
                        estado="verificado",
                        dimension="lugar",
                    )
                hashes.append(await mundo.calcular_hash_corpus(db, ejecucion))
        assert hashes[0] == hashes[1]


class TestVigenciaPorEjecucion:
    async def test_rehacer_no_contamina_el_corpus(self, db: aiosqlite.Connection) -> None:
        """Los hechos de la ejecución anterior quedan como historia, no como corpus."""
        primera = await arnes.abrir_fase_run(db, "investigation")
        await mundo.insertar_hecho(
            db,
            fase_run_id=primera,
            enunciado="Dato de la primera pasada",
            estado="verificado",
            dimension="lugar",
        )
        segunda = await arnes.abrir_fase_run(db, "investigation", input_run_id=primera)
        await mundo.insertar_hecho(
            db,
            fase_run_id=segunda,
            enunciado="Dato de la segunda pasada",
            estado="verificado",
            dimension="lugar",
        )
        vigentes = await mundo.hechos_vigentes(db, segunda)
        assert [f["enunciado"] for f in vigentes] == ["Dato de la segunda pasada"]
        assert len(await mundo.hechos_vigentes(db, primera)) == 1, "lo anterior sigue consultable"

    async def test_recuento_por_dimension_para_el_informe_del_gate(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        for dimension in ("lugar", "lugar", "mentalidad"):
            await mundo.insertar_hecho(
                db,
                fase_run_id=fase_run,
                enunciado=f"hecho de {dimension}",
                estado="verificado",
                dimension=dimension,
            )
        assert await mundo.hechos_por_dimension(db, fase_run) == {"lugar": 2, "mentalidad": 1}

    async def test_el_verificador_recibe_lotes_de_veinte(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        """El troceo evita que el tamaño del corpus reviente la guarda de presupuesto."""
        for i in range(45):
            await mundo.insertar_hecho(
                db,
                fase_run_id=fase_run,
                enunciado=f"hecho {i}",
                estado="verificado",
                dimension="lugar",
                cita="fragmento",
            )
        lotes = await mundo.pendientes_de_verificar(db, fase_run, tamano_lote=20)
        assert [len(lote) for lote in lotes] == [20, 20, 5]


class TestTransaccion:
    async def test_lo_que_falla_a_mitad_no_deja_rastro(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        """Es lo que impide que el grafo crea que el capítulo 6 está hecho sin estarlo."""
        capitulo = await _capitulo(db)
        with pytest.raises(RuntimeError):
            async with paso_atomico(db):
                await texto.insertar_capitulo_version(
                    db, capitulo_id=capitulo, fase_run_id=fase_run, texto="A medias."
                )
                raise RuntimeError("el nodo revienta despues de escribir")
        async with db.execute("SELECT COUNT(*) AS n FROM capitulo_version") as cursor:
            assert int((await cursor.fetchone())["n"]) == 0

    async def test_lo_que_termina_se_confirma_junto(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        capitulo = await _capitulo(db)
        async with paso_atomico(db):
            version = await texto.insertar_capitulo_version(
                db, capitulo_id=capitulo, fase_run_id=fase_run, texto="Un capitulo entero."
            )
            await texto.aprobar_capitulo(db, version)
        fila = await texto.capitulo_aprobado(db, capitulo)
        assert fila is not None and fila["estado"] == "aprobado"
