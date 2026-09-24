"""spec: §4.3 · arq: §4, §11a, §11c

Pruebas de la Fase 3.

Lo que se comprueba aquí es lo que hace que esta fase sea la más rentable del sistema: que
**el gate se cierra antes de escribir una línea** cuando falta cobertura o un arco, que el
sello deja el corpus de solo lectura, y que un hueco que el investigador no encuentra **no
detiene la escaleta** sino que entra como invención declarada.
"""

from __future__ import annotations

import aiosqlite
import pytest
from dobles.fabrica import NovelaDePrueba, poblar
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.config import Settings
from storymaker.commons.db.repos import intake as repo_intake
from storymaker.commons.db.repos import mundo
from storymaker.commons.formal.generador import generar
from storymaker.intake.esquemas import Brief, Periodo
from storymaker.investigation.corpus import escribir_hecho
from storymaker.investigation.esquemas import (
    Dimension,
    EstadoEpistemico,
    HechoPropuesto,
)
from storymaker.plotting import contexto, gate, informe


@pytest.fixture
def vectorizador() -> VectorizadorFalso:
    return VectorizadorFalso()


@pytest.fixture
def ajustes() -> Settings:
    return Settings(_env_file=None)


@pytest.fixture
async def novela(db: aiosqlite.Connection) -> NovelaDePrueba:
    return await poblar(db)


def brief() -> Brief:
    return Brief(
        nombre_homenajeado="Manuel Ferrer",
        fecha_nacimiento="1760-03-02",
        rol_epoca="armador",
        ocasion="jubilacion",
        periodo=Periodo(inicio=1800, fin=1810, denominacion="el Cadiz de las Cortes"),
        lugar="Cadiz",
        genero="novela historica",
        tono="sobrio",
    )


class TestPuertaDelGate:
    async def test_un_obligatorio_sin_anclar_cierra_la_puerta(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Convierte un fallo de diez capitulos escritos y pagados en un fallo de escaleta."""
        await repo_intake.insertar_dato(
            db,
            tipo="objeto",
            valor_json='{"valor": "la brujula del abuelo"}',
            origen="entrevista",
            obligatorio=True,
        )
        puerta = await gate.comprobar(db)
        assert not puerta.abierta
        assert any(i.validador == "cobertura_anclada" for i in puerta.incidencias)

    async def test_con_todo_anclado_la_puerta_se_abre(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        puerta = await gate.comprobar(db)
        assert puerta.abierta, [i.mensaje for i in puerta.incidencias]

    async def test_el_homenajeado_necesita_arco_con_cierre_tardio(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Su hito cae en el capitulo 2 de 2, que es el tercio final: pasa."""
        revision = await gate.construir_revision(db)
        arco = next(a for a in revision.arcos if a.es_homenajeado)
        assert arco.tipo == "positivo"
        assert arco.hitos_por_capitulo == (2,)

    async def test_un_personaje_de_una_escena_no_necesita_arco(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Con tres escenas de minimo se recoge a quien recurre, no a quien cruza una taberna."""
        revision = await gate.construir_revision(db)
        assert max(revision.apariciones_por_personaje.values()) < 3
        assert gate.PuertaDePlotting(tuple()).abierta


class TestCronologiaDeLaEscaleta:
    async def test_cada_escena_fechada_es_un_evento(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """La escaleta ya dice que dia ocurre cada escena: eso basta para los invariantes."""
        cronologia = await gate.cronologia_de_la_escaleta(db)
        assert len(cronologia.eventos) == 2
        assert {e.clave for e in cronologia.eventos} == {"cap1-esc1", "cap2-esc1"}

    async def test_los_personajes_viajan_con_sus_fechas_vitales(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        cronologia = await gate.cronologia_de_la_escaleta(db)
        manuel = next(p for p in cronologia.personas if p.nombre == "Manuel Ferrer")
        assert manuel.nacimiento < 0, "nace en 1760, antes de la epoca de referencia"
        assert manuel.muerte is None, "sin fecha de muerte no hay restriccion por ese lado"

    async def test_una_escena_sin_fecha_no_se_juzga(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Lean no opina sobre lo que no sabe: dejar una escena al aire no es un error."""
        await db.execute("UPDATE plan_escena SET fecha_narrativa = NULL")
        cronologia = await gate.cronologia_de_la_escaleta(db)
        assert cronologia.eventos == ()

    async def test_produce_un_fichero_lean_compilable(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        fuente = generar(await gate.cronologia_de_la_escaleta(db))
        assert "def novela : Novela" in fuente
        assert "cap2-esc1" in fuente


class TestSello:
    async def test_tras_sellar_nadie_anade_hechos(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba, vectorizador: VectorizadorFalso
    ) -> None:
        """Durante Writing solo se puede anclar a lo existente o declarar una Licencia."""
        await mundo.sellar_corpus(db, novela.fase_run)
        with pytest.raises(aiosqlite.IntegrityError):
            await escribir_hecho(
                db,
                vectorizador,
                HechoPropuesto(
                    enunciado="Un hecho tardio",
                    estado=EstadoEpistemico.INFERIDO,
                    dimension=Dimension.LUGAR,
                ),
                fase_run_id=novela.fase_run,
            )

    async def test_el_sello_se_calcula_sobre_lo_vigente(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        hash_corpus = await mundo.sellar_corpus(db, novela.fase_run)
        assert len(hash_corpus) == 64
        assert await mundo.hay_sello(db)


class TestCorpusParaElArquitecto:
    async def test_se_pide_por_dimension_y_no_en_bloque(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba, vectorizador: VectorizadorFalso,
        ajustes: Settings,
    ) -> None:
        """Quien planifica necesita algo de las seis dimensiones, no mucho de una."""
        from storymaker.commons.embeddings import indice

        for fila in await mundo.hechos_vigentes(db, novela.fase_run):
            await indice.indexar_hecho(
                db,
                vectorizador,
                hecho_id=int(fila["id"]),
                enunciado=str(fila["enunciado"]),
                estado=str(fila["estado"]),
                dimension=str(fila["dimension"]),
            )
        hechos = await contexto.hechos_relevantes(db, vectorizador, brief(), settings=ajustes)
        dimensiones = {str(f["dimension"]) for f in hechos}
        assert len(dimensiones) >= 2

    def test_la_consulta_sale_del_encargo_y_no_del_modelo(self) -> None:
        consulta = contexto.consulta_para(brief())
        assert "Cadiz" in consulta
        assert "armador" in consulta

    async def test_el_estado_epistemico_va_delante(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Sobre un verificado se ancla una escena; sobre un desconocido, no se apoya la trama."""
        texto = contexto.como_texto(await mundo.hechos_vigentes(db, novela.fase_run))
        assert texto.startswith("[verificado")


class TestInforme:
    async def test_cuenta_los_inventados_por_dimension(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba, vectorizador: VectorizadorFalso
    ) -> None:
        """La invencion no se topa: se cuenta y se ensena."""
        await escribir_hecho(
            db,
            vectorizador,
            HechoPropuesto(
                enunciado="La calle se llamaba de los Toneleros",
                estado=EstadoEpistemico.INFERIDO,
                dimension=Dimension.LUGAR,
            ),
            fase_run_id=novela.fase_run,
            origen="invencion_autorizada",
        )
        puerta = await gate.comprobar(db)
        resultado = await informe.construir(db, novela.fase_run, puerta, huecos_gastados=3)
        assert resultado.inventados == 1
        assert resultado.inventados_por_dimension == {"lugar": 1}
        assert "No se topan a proposito" in resultado.como_texto()

    async def test_sin_invencion_lo_dice(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        puerta = await gate.comprobar(db)
        resultado = await informe.construir(db, novela.fase_run, puerta, huecos_gastados=0)
        assert "Ningun hecho inventado" in resultado.como_texto()

    async def test_una_puerta_cerrada_explica_lo_que_cuesta_arreglarla_tarde(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        await repo_intake.insertar_dato(
            db,
            tipo="objeto",
            valor_json='{"valor": "sin anclar"}',
            origen="entrevista",
            obligatorio=True,
        )
        puerta = await gate.comprobar(db)
        resultado = await informe.construir(db, novela.fase_run, puerta, huecos_gastados=0)
        assert not resultado.puede_avanzar
        assert "cuesta diez capitulos" in resultado.como_texto()


class TestAnclajesDeLaEscaleta:
    """ER §7.2: el arquitecto ancla por clave, y lo que no resuelve lo enseña el gate."""

    def test_la_clave_se_resuelve_como_la_escriba(self) -> None:
        from storymaker.plotting.escaleta import mapa_de_claves, resolver_clave

        mapa = mapa_de_claves({12: "Las aulas se calentaban con estufa de leña."})

        assert resolver_clave(mapa, "#12") == 12
        assert resolver_clave(mapa, "hecho #12") == 12
        assert resolver_clave(mapa, "12") == 12
        assert resolver_clave(mapa, "las aulas se calentaban con estufa de lena.") == 12
        assert resolver_clave(mapa, "#99") is None
        assert resolver_clave(mapa, None) is None

    async def test_el_volcado_escribe_los_anclajes_y_apunta_los_que_no_resuelve(
        self, db: aiosqlite.Connection, vectorizador: VectorizadorFalso
    ) -> None:
        from dobles import guion

        from storymaker.plotting import canon, escaleta

        salida = guion.arquitectura()
        personajes = await canon.volcar_canon(db, vectorizador, salida, brief())
        enunciado = salida.capitulos[0].escenas[0].anclajes[0].hecho or ""

        from storymaker.commons.db.repos import arnes

        hecho_id = await escribir_hecho(
            db,
            vectorizador,
            HechoPropuesto(
                enunciado=enunciado, estado=EstadoEpistemico.VERIFICADO, dimension=Dimension.LUGAR
            ),
            fase_run_id=await arnes.abrir_fase_run(db, "investigation"),
        )
        sin_resolver: list[str] = []
        await escaleta.volcar_escaleta(
            db,
            salida,
            personajes=personajes,
            hechos=escaleta.mapa_de_claves({hecho_id: enunciado}),
            sin_resolver=sin_resolver,
        )
        async with db.execute("SELECT COUNT(*) AS n FROM plan_anclaje") as cursor:
            fila = await cursor.fetchone()

        assert fila is not None and int(fila["n"]) > 0
        assert sin_resolver == []

    async def test_el_homenajeado_se_llama_como_dice_el_encargo(
        self, db: aiosqlite.Connection, vectorizador: VectorizadorFalso
    ) -> None:
        """Si el arquitecto lo abrevia, nombres_exactos no exigiria nunca el nombre entero."""
        from dobles import guion

        from storymaker.plotting import canon

        encargo = brief().model_copy(update={"nombre_homenajeado": "Casilda Berrocal Diaz"})
        personajes = await canon.volcar_canon(db, vectorizador, guion.arquitectura(), encargo)
        async with db.execute(
            "SELECT p.nombre FROM canon_obra o JOIN canon_personaje p ON p.id = o.homenajeado_id"
        ) as cursor:
            fila = await cursor.fetchone()

        assert fila is not None and fila["nombre"] == "Casilda Berrocal Diaz"
        assert guion.HOMENAJEADO in personajes


class TestFormaDeLaEscaleta:
    """REQ-BE-135: el arquitecto conoce el rango de escenas y el gate avisa si no lo cumple."""

    def test_el_prompt_dice_capitulos_escenas_y_extension(self) -> None:
        from types import SimpleNamespace

        from storymaker.plotting.nodos import forma_de_la_escaleta

        texto = forma_de_la_escaleta(
            SimpleNamespace(n_capitulos=12, palabras_por_capitulo=1500)  # type: ignore[arg-type]
        )
        assert "12 capitulos" in texto
        assert "entre 2 y 4 escenas" in texto
        assert "1500 palabras" in texto

    async def test_el_gate_avisa_de_cada_capitulo_fuera_de_rango(
        self, db: aiosqlite.Connection
    ) -> None:
        from storymaker.plotting.gate import escenas_fuera_de_rango

        for numero, escenas in ((1, 1), (2, 3), (3, 5)):
            cursor = await db.execute("INSERT INTO plan_capitulo (numero) VALUES (?)", (numero,))
            for orden in range(escenas):
                await db.execute(
                    "INSERT INTO plan_escena (capitulo_id, orden) VALUES (?, ?)",
                    (cursor.lastrowid, orden),
                )
        avisos = await escenas_fuera_de_rango(db)
        assert [a.mensaje.split(" tiene")[0] for a in avisos] == ["El capitulo 1", "El capitulo 3"]
        assert all(not a.bloquea for a in avisos)
