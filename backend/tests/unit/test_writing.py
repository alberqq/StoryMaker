"""spec: §4.4 · arq: §4, §11a, §11b

Pruebas del bucle de capítulo.

Lo que se comprueba aquí es el reparto de responsabilidades que sostiene la fase: que la
salida del escritor **es solo prosa** —no se le pregunta qué usó, se le mide—, que la
pasada del extractor separa lo que bloquea de lo que avisa, que las filas de un intento
descartado **quedan fuera por construcción**, y que los avisos viajan al capítulo siguiente
salvo en el último, donde se destacan en el informe del gate.
"""

from __future__ import annotations

import aiosqlite
import pytest
from dobles.fabrica import NovelaDePrueba, poblar
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.agents.schema_guard import SalidaInvalida, validar
from storymaker.commons.config import Settings
from storymaker.commons.db.repos import arnes, intake, texto
from storymaker.commons.embeddings import indice
from storymaker.commons.validation.modelos import CapituloEnRevision, Severidad
from storymaker.writing import avisos, extraccion, gate, similitud, validacion
from storymaker.writing.esquemas import (
    Dominio,
    EstadoDeContinuidad,
    EventoNarrativo,
    SalidaEscritor,
    SalidaExtractorDeCapitulo,
    UsoDeElemento,
    UsoDeHecho,
    VeredictoDeEjecucion,
)


@pytest.fixture
def vectorizador() -> VectorizadorFalso:
    return VectorizadorFalso()


@pytest.fixture
async def novela(db: aiosqlite.Connection) -> NovelaDePrueba:
    return await poblar(db)


class TestSalidaDelEscritor:
    def test_es_solo_prosa(self) -> None:
        """No se le pregunta que hechos uso: se le mide. Por eso no hay donde declararlo."""
        campos = set(SalidaEscritor.model_fields)
        assert campos == {"texto"}
        assert not (campos & {"hechos_usados", "beats_cubiertos", "elementos"})

    def test_el_extractor_si_mide_todo_eso(self) -> None:
        campos = set(SalidaExtractorDeCapitulo.model_fields)
        medidos = {"hechos_usados", "elementos_usados", "continuidad", "eventos", "veredicto"}
        assert medidos <= campos


class TestPasadaDelExtractor:
    def test_la_cobertura_y_la_ejecucion_avisan(self) -> None:
        """Ninguna de las dos detiene el capitulo: la cobertura que bloquea es la de G5.

        La cobertura mide lo que el extractor reconocio, no el texto. Cuando bloqueaba, un
        capitulo que ya cumplia agotaba sus reintentos sin que el editor tuviera que corregir.
        """
        revision = CapituloEnRevision(
            numero=2,
            texto="texto",
            palabras=1200,
            rango_palabras=(1000, 1500),
            personalizacion_encomendada=(7,),
            personalizacion_textos=((7, "colecciona cartas nauticas antiguas"),),
        )
        salida = SalidaExtractorDeCapitulo(
            resumen="un resumen",
            veredicto=VeredictoDeEjecucion(beats_pendientes=["el armador no discute"]),
        )
        incidencias = validacion.pasada_del_extractor(revision, salida)
        por_validador = {i.validador: i.severidad for i in incidencias}
        assert por_validador["cobertura_capitulo"] is Severidad.AVISO
        assert por_validador["ejecucion_escaleta"] is Severidad.AVISO
        cobertura = next(i for i in incidencias if i.validador == "cobertura_capitulo")
        assert "colecciona cartas nauticas antiguas" in cobertura.mensaje

    def test_un_hito_pendiente_avisa_y_no_detiene(self) -> None:
        revision = CapituloEnRevision(
            numero=2, texto="t", palabras=1200, rango_palabras=(1000, 1500)
        )
        salida = SalidaExtractorDeCapitulo(
            resumen="r", veredicto=VeredictoDeEjecucion(hitos_pendientes=[3])
        )
        incidencias = validacion.pasada_del_extractor(revision, salida)
        assert [i.validador for i in incidencias] == ["arco_ejecutado"]
        assert not validacion.hay_bloqueantes(incidencias)

    def test_todo_cubierto_no_levanta_nada(self) -> None:
        revision = CapituloEnRevision(
            numero=2,
            texto="t",
            palabras=1200,
            rango_palabras=(1000, 1500),
            personalizacion_encomendada=(7,),
        )
        salida = SalidaExtractorDeCapitulo(
            resumen="r", elementos_usados=[UsoDeElemento(dato_id=7, escena=1)]
        )
        assert validacion.pasada_del_extractor(revision, salida) == []


class TestCatalogoDelExtractor:
    """ER §7.3: el extractor mide con los identificadores delante, y no puede salirse de ellos."""

    async def test_lleva_la_escaleta_y_los_identificadores(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba, vectorizador: VectorizadorFalso
    ) -> None:
        escaleta = await extraccion.catalogo(db, vectorizador, 2, Settings(_env_file=None))

        assert "Escaleta del capitulo 2" in escaleta.texto
        assert f"#{novela.homenajeado} Manuel Ferrer" in escaleta.texto
        assert novela.homenajeado in escaleta.dominio.personajes
        assert novela.hecho_anclado in escaleta.dominio.hechos
        assert novela.dato_obligatorio in escaleta.dominio.datos
        assert novela.hito in escaleta.dominio.hitos

    async def test_dice_que_quien_solo_se_recuerda_no_participa(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba, vectorizador: VectorizadorFalso
    ) -> None:
        """Un muerto recordado como participante tumbaba por cronología un capítulo correcto."""
        escaleta = await extraccion.catalogo(db, vectorizador, 2, Settings(_env_file=None))
        assert "solo los personajes presentes en el evento" in escaleta.texto
        descripcion = SalidaExtractorDeCapitulo.model_json_schema()["$defs"]["EventoNarrativo"][
            "properties"
        ]["participantes"]["description"]
        assert "ya ha muerto no participa" in descripcion

    def test_un_identificador_fuera_de_dominio_invalida_la_salida(self) -> None:
        """Falla en schema_guard, donde se reintenta, y no en una clave foranea."""
        dominio = Dominio(personajes=frozenset({1, 2}), hechos=frozenset({7}))
        bruto = (
            '{"resumen": "r", "continuidad": [{"personaje_id": 9}],'
            ' "hechos_usados": [{"hecho_id": 7, "escena": 1}]}'
        )
        with pytest.raises(SalidaInvalida) as fallo:
            validar(SalidaExtractorDeCapitulo, bruto, {"dominio": dominio})

        assert "personaje_id [9]" in str(fallo.value)
        assert "admitidos: 1, 2" in str(fallo.value)

    def test_dentro_de_dominio_pasa_y_sin_contexto_no_se_comprueba(self) -> None:
        bruto = '{"resumen": "r", "continuidad": [{"personaje_id": 2}]}'
        dominio = Dominio(personajes=frozenset({2}))

        assert validar(SalidaExtractorDeCapitulo, bruto, {"dominio": dominio}).continuidad
        assert validar(SalidaExtractorDeCapitulo, bruto.replace("2", "9")).continuidad


class TestVolcadoDelExtractor:
    async def test_las_filas_cuelgan_del_intento(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Las de un intento descartado quedan colgando de una version que nadie recoge."""
        version = await texto.insertar_capitulo_version(
            db, capitulo_id=novela.capitulo_2, fase_run_id=novela.fase_run,
            texto="Un intento cualquiera.", intento=1,
        )
        salida = SalidaExtractorDeCapitulo(
            resumen="Manuel consigue media carga",
            hechos_usados=[UsoDeHecho(hecho_id=novela.hecho_anclado, escena=1)],
            elementos_usados=[UsoDeElemento(dato_id=novela.dato_obligatorio, escena=1)],
            continuidad=[
                EstadoDeContinuidad(
                    personaje_id=novela.homenajeado,
                    fecha_narrativa="1805-04-11",
                    posesiones=["media carga de roble"],
                )
            ],
            veredicto=VeredictoDeEjecucion(hitos_ejecutados=[novela.hito]),
        )
        await extraccion.volcar(db, salida, capitulo_version_id=version, numero=2)

        assert await extraccion.contar_filas_del_intento(db, version) == 4
        assert await extraccion.contar_filas_del_intento(db, version + 99) == 0

    async def test_la_cronologia_narrativa_la_escribe_el_extractor(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Nadie mas sabe que ocurrio en esa prosa: por eso Lean corre en esta pasada."""
        version = await texto.insertar_capitulo_version(
            db, capitulo_id=novela.capitulo_2, fase_run_id=novela.fase_run, texto="t"
        )
        salida = SalidaExtractorDeCapitulo(
            resumen="r",
            eventos=[
                EventoNarrativo(
                    clave="manuel-compra-roble",
                    descripcion="Manuel cierra el trato",
                    momento="1805-04-11",
                    escena=1,
                    participantes=[novela.homenajeado],
                )
            ],
        )
        await extraccion.volcar(db, salida, capitulo_version_id=version, numero=2)
        async with db.execute(
            "SELECT * FROM cronologia_evento WHERE origen = 'narrativo'"
        ) as cursor:
            filas = list(await cursor.fetchall())
        assert len(filas) == 1
        assert filas[0]["capitulo_version_id"] == version

    async def test_el_titulo_markdown_del_modelo_no_se_guarda(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """El título vive en la escaleta: dejarlo en el texto lo duplicaba en la página."""
        version = await texto.insertar_capitulo_version(
            db, capitulo_id=novela.capitulo_2, fase_run_id=novela.fase_run,
            texto=(
                "# Capítulo 2: El roble\n\n## Escena 1: El trato\n\nManuel cerro el trato.\n\n"
                "## Escena 2: La carga\n\nLa carga llego al alba. El #3 del muelle no."
            ),
        )
        async with db.execute(
            "SELECT texto, palabras FROM capitulo_version WHERE id = ?", (version,)
        ) as cursor:
            fila = await cursor.fetchone()
        assert fila["texto"] == (
            "Manuel cerro el trato.\n\nLa carga llego al alba. El #3 del muelle no."
        )
        assert fila["palabras"] == 14

    async def test_un_segundo_intento_con_las_mismas_claves_no_rompe_la_clave_foranea(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """El `INSERT OR IGNORE` ignorado deja `lastrowid` apuntando a otra tabla.

        Entre intento e intento se insertan filas en otras tablas —la versión nueva, su
        continuidad—, así que colgar los participantes de `lastrowid` los ataba a un evento
        inexistente. Detuvo dos veces una novela real en el intento 2 de un capítulo.
        """
        evento = EventoNarrativo(
            clave="manuel-compra-roble",
            descripcion="Manuel cierra el trato",
            momento="1805-04-11",
            escena=1,
            participantes=[novela.homenajeado],
        )
        salida = SalidaExtractorDeCapitulo(
            resumen="r",
            continuidad=[EstadoDeContinuidad(personaje_id=novela.homenajeado)],
            eventos=[evento],
        )
        for intento in (1, 2):
            version = await texto.insertar_capitulo_version(
                db, capitulo_id=novela.capitulo_2, fase_run_id=novela.fase_run,
                texto=f"intento {intento}", intento=intento,
            )
            await extraccion.volcar(db, salida, capitulo_version_id=version, numero=2)

        async with db.execute("PRAGMA foreign_key_check") as cursor:
            assert list(await cursor.fetchall()) == []

    async def test_el_resumen_se_guarda_sin_tocar_el_texto(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """El trigger permite el resumen porque no es contenido del escritor: lo mide otro."""
        version = await texto.insertar_capitulo_version(
            db, capitulo_id=novela.capitulo_2, fase_run_id=novela.fase_run, texto="el texto"
        )
        await extraccion.guardar_resumen(db, version, "un resumen medido por el extractor")
        assert await texto.resumen_de(db, version) == "un resumen medido por el extractor"
        async with db.execute("SELECT texto FROM capitulo_version WHERE id = ?", (version,)) as c:
            assert (await c.fetchone())["texto"] == "el texto"


class TestAvisos:
    async def test_los_tres_mas_recientes_viajan(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        for i in range(5):
            await arnes.registrar_incidencia(
                db,
                capitulo_version_id=novela.version_capitulo_1,
                validador="ejecucion_escaleta",
                severidad="aviso",
                mensaje=f"aviso {i}",
            )
        pendientes = await avisos.pendientes_para(db, 2)
        assert pendientes == ["aviso 2", "aviso 3", "aviso 4"]

    async def test_el_capitulo_1_no_arrastra_nada(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        assert await avisos.pendientes_para(db, 1) == []

    async def test_los_del_ultimo_capitulo_se_destacan(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """No hay capitulo N+1, y es donde cierra el arco del homenajeado."""
        version = await texto.insertar_capitulo_version(
            db, capitulo_id=novela.capitulo_2, fase_run_id=novela.fase_run, texto="final"
        )
        await texto.aprobar_capitulo(db, version)
        await arnes.registrar_incidencia(
            db,
            capitulo_version_id=version,
            validador="arco_ejecutado",
            severidad="aviso",
            mensaje="el hito de cierre no ocurrio",
        )
        destacados = await avisos.del_ultimo_capitulo(db)
        assert len(destacados) == 1
        assert destacados[0].capitulo == 2


class TestAutoSimilitud:
    async def test_detecta_dos_capitulos_casi_iguales(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba, vectorizador: VectorizadorFalso
    ) -> None:
        await indice.indexar_resumen(
            db,
            vectorizador,
            capitulo_version_id=novela.version_capitulo_1,
            resumen="Manuel recibe la orden de embargo y decide resistir",
            capitulo_numero=1,
        )
        parecidos = await similitud.buscar_repeticion(
            db,
            vectorizador,
            resumen="Manuel recibe la orden de embargo y decide resistir",
            capitulo_numero=2,
        )
        assert len(parecidos) == 1
        incidencias = similitud.como_incidencias(parecidos, 2)
        assert incidencias[0].severidad is Severidad.AVISO, "la repeticion no bloquea"

    async def test_dos_capitulos_distintos_no_saltan(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba, vectorizador: VectorizadorFalso
    ) -> None:
        await indice.indexar_resumen(
            db,
            vectorizador,
            capitulo_version_id=novela.version_capitulo_1,
            resumen="Manuel recibe la orden de embargo",
            capitulo_numero=1,
        )
        parecidos = await similitud.buscar_repeticion(
            db, vectorizador, resumen="Tomasa cierra la taberna bajo la lluvia", capitulo_numero=2
        )
        assert parecidos == []


class TestGateDeWriting:
    async def test_avisa_si_falta_algun_capitulo(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        informe = await gate.construir(db)
        assert informe.capitulos_totales == 2
        assert informe.capitulos_aprobados == 1
        assert not informe.completo
        assert "no esta lista para el juez" in informe.como_texto()

    async def test_la_cobertura_es_la_red_de_seguridad(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Anclar no es escribir: el elemento esta anclado y no ha aparecido en ningun capitulo."""
        informe = await gate.construir(db)
        assert any(i.validador == "cobertura_personalizacion" for i in informe.incidencias)

    async def test_con_todo_usado_la_cobertura_pasa(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        await intake.registrar_uso(
            db,
            capitulo_version_id=novela.version_capitulo_1,
            escena_id=novela.escena_1,
            dato_id=novela.dato_obligatorio,
        )
        informe = await gate.construir(db)
        assert informe.incidencias == ()
