"""spec: §4.2 · arq: §4, §15

Pruebas de la Fase 2.

Lo que importa comprobar aquí son las tres decisiones que sostienen la fase: que **el
prompt del investigador no puede llevar datos personales** porque no los recibe, que
**rehacer no contamina el corpus**, y que un hecho sin respaldo **baja de firmeza y no
bloquea**, sin que nadie reescriba lo que declaró el investigador.

La calidad de lo que el investigador encuentre no se comprueba aquí: eso es U-2, la verdad
histórica, que ninguna técnica de software decide.
"""

from __future__ import annotations

import aiosqlite
import pytest
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.db.repos import arnes, mundo
from storymaker.commons.embeddings import indice
from storymaker.commons.validation.policy_checker import pii_en_prompt_de_investigacion
from storymaker.commons.validation.puras import firmeza
from storymaker.investigation import corpus, informe, prompts
from storymaker.investigation.esquemas import (
    Dimension,
    EstadoEpistemico,
    FuenteCitada,
    HechoPropuesto,
    SalidaInvestigador,
)


@pytest.fixture
def vectorizador() -> VectorizadorFalso:
    return VectorizadorFalso()


def hecho(**cambios: object) -> HechoPropuesto:
    base: dict[str, object] = {
        "enunciado": "El roble americano llegaba a Cadiz desde La Habana",
        "estado": EstadoEpistemico.VERIFICADO,
        "dimension": Dimension.CULTURA_MATERIAL,
        "cita": "los navios de la carrera traian roble de Indias",
        "fuentes": [FuenteCitada(url="https://ejemplo.test/cadiz", titulo="El puerto")],
    }
    base.update(cambios)
    return HechoPropuesto(**base)  # type: ignore[arg-type]


class TestPrompts:
    def test_el_encargo_nombra_las_seis_dimensiones(self) -> None:
        texto = prompts.prompt_de_investigacion("el Cadiz de las Cortes", "Cadiz")
        for dimension in Dimension:
            assert dimension.value.split("_")[0] in texto.lower()

    def test_dice_el_tope_de_busquedas(self) -> None:
        texto = prompts.prompt_de_investigacion("1805", "Cadiz")
        assert "3 busquedas" in texto or "**3" in texto
        assert "el arnes las" in texto, "el tope lo impone el arnes, no el prompt"

    def test_el_prompt_no_puede_llevar_datos_personales(self) -> None:
        """No se puede filtrar lo que no se tiene: la funcion recibe dos cadenas."""
        texto = prompts.prompt_de_investigacion("el Cadiz de las Cortes", "Cadiz")
        incidencias = pii_en_prompt_de_investigacion(
            texto, ["Manuel Ferrer", "1760-03-02", "jubilacion", "el reloj del abuelo"]
        )
        assert incidencias == []

    def test_el_verificador_recibe_pares_y_nada_mas(self) -> None:
        texto = prompts.prompt_de_verificacion([(7, "Cadiz tenia astilleros", "habia astilleros")])
        assert "Cadiz tenia astilleros" in texto
        assert "No juzgues si el hecho es cierto" in texto

    def test_sin_cita_el_verificador_lo_sabe(self) -> None:
        texto = prompts.prompt_de_verificacion([(7, "algo", "")])
        assert "(sin cita)" in texto
        assert "o no hay cita" in texto, "sin cita, el dato central no esta respaldado"

    def test_el_hueco_admite_no_encontrarlo(self) -> None:
        """Empujar a un modelo a responder lo que no sabe llena el corpus de invenciones."""
        texto = prompts.prompt_de_hueco("como se llamaba la calle", "1805", "Cadiz")
        assert "no_encontrado" in texto
        assert "una sola busqueda" in texto


class TestCorpus:
    async def test_el_hecho_nace_pendiente_de_verificar(
        self, db: aiosqlite.Connection, fase_run: int, vectorizador: VectorizadorFalso
    ) -> None:
        """Dar por bueno lo que nadie ha mirado es el fallo que el paso 2 existe para impedir."""
        await corpus.escribir_hecho(db, vectorizador, hecho(), fase_run_id=fase_run)
        (fila,) = await mundo.hechos_vigentes(db, fase_run)
        assert fila["respaldo"] == "pendiente"

    async def test_se_indexa_en_la_misma_operacion(
        self, db: aiosqlite.Connection, fase_run: int, vectorizador: VectorizadorFalso
    ) -> None:
        await corpus.escribir_hecho(db, vectorizador, hecho(), fase_run_id=fase_run)
        vecinos = await indice.buscar_hechos(db, vectorizador, "roble de La Habana")
        assert len(vecinos) == 1

    async def test_una_pagina_citada_por_varios_hechos_es_una_fila(
        self, db: aiosqlite.Connection, fase_run: int, vectorizador: VectorizadorFalso
    ) -> None:
        await corpus.escribir_lote(
            db,
            vectorizador,
            [hecho(), hecho(enunciado="Los toneleros trabajaban al pie del muelle")],
            fase_run_id=fase_run,
        )
        async with db.execute("SELECT COUNT(*) AS n FROM mundo_fuente") as cursor:
            assert int((await cursor.fetchone())["n"]) == 1

    async def test_rehacer_no_contamina(
        self, db: aiosqlite.Connection, vectorizador: VectorizadorFalso
    ) -> None:
        """Los de la ejecucion anterior quedan como historia, no como corpus."""
        primera = await arnes.abrir_fase_run(db, "investigation")
        await corpus.escribir_hecho(db, vectorizador, hecho(), fase_run_id=primera)
        segunda = await arnes.abrir_fase_run(db, "investigation", input_run_id=primera)
        await corpus.escribir_hecho(
            db, vectorizador, hecho(enunciado="Dato de la segunda pasada"), fase_run_id=segunda
        )
        vigentes = await mundo.hechos_vigentes(db, segunda)
        assert [f["enunciado"] for f in vigentes] == ["Dato de la segunda pasada"]

    async def test_un_hecho_sin_respaldo_baja_de_firmeza_sin_perder_lo_declarado(
        self, db: aiosqlite.Connection, fase_run: int, vectorizador: VectorizadorFalso
    ) -> None:
        """El verificador escribe su veredicto; lo que declaró el investigador no se toca."""
        hecho_id = await corpus.escribir_hecho(
            db, vectorizador, hecho(estado=EstadoEpistemico.VERIFICADO), fase_run_id=fase_run
        )
        await corpus.anotar_veredicto(db, hecho_id, respaldado=False)
        (fila,) = await mundo.hechos_vigentes(db, fase_run)
        assert fila["estado"] == "verificado"
        assert fila["respaldo"] == "no_respaldado"
        assert firmeza(fila["estado"], fila["respaldo"], fila["origen"]) == "inferido"

    async def test_lo_respaldado_conserva_su_estado_epistemico(
        self, db: aiosqlite.Connection, fase_run: int, vectorizador: VectorizadorFalso
    ) -> None:
        """`estado` y `respaldo` no dicen lo mismo: uno es del hecho, otro de la cita."""
        hecho_id = await corpus.escribir_hecho(
            db, vectorizador, hecho(estado=EstadoEpistemico.DEBATIDO), fase_run_id=fase_run
        )
        await corpus.anotar_veredicto(db, hecho_id, respaldado=True)
        (fila,) = await mundo.hechos_vigentes(db, fase_run)
        assert fila["estado"] == "debatido", "un hecho debatido y bien citado sigue debatido"
        assert fila["respaldo"] == "respaldado"


class TestSalidaDelInvestigador:
    def test_cuenta_por_dimension(self) -> None:
        salida = SalidaInvestigador(
            hechos=[hecho(), hecho(dimension=Dimension.MENTALIDAD)]
        )
        assert salida.por_dimension() == {"cultura_material": 1, "mentalidad": 1}

    def test_la_cita_no_pasa_de_300_caracteres(self) -> None:
        """El tope obliga a senalar el fragmento, no a volcar media pagina."""
        with pytest.raises(ValueError, match="cita"):
            hecho(cita="x" * 301)


class TestInforme:
    async def test_enseña_el_recuento_por_dimension(
        self, db: aiosqlite.Connection, fase_run: int, vectorizador: VectorizadorFalso
    ) -> None:
        """El reparto lo decide el modelo: la mitigacion declarada es que se vea."""
        await corpus.escribir_lote(
            db, vectorizador, [hecho(), hecho(dimension=Dimension.LUGAR)], fase_run_id=fase_run
        )
        resultado = await informe.construir(db, fase_run)
        assert resultado.total == 2
        assert "cultura_material: 1" in resultado.como_texto()
        assert "cronologia: 0" in resultado.como_texto()

    async def test_avisa_de_las_dimensiones_vacias_sin_bloquear(
        self, db: aiosqlite.Connection, fase_run: int, vectorizador: VectorizadorFalso
    ) -> None:
        await corpus.escribir_hecho(db, vectorizador, hecho(), fase_run_id=fase_run)
        resultado = await informe.construir(db, fase_run)
        assert len(resultado.dimensiones_vacias) == 5
        assert "rehacer con comentario" in resultado.como_texto()

    async def test_destaca_lo_no_respaldado_con_su_fuente(
        self, db: aiosqlite.Connection, fase_run: int, vectorizador: VectorizadorFalso
    ) -> None:
        """Es la mitigacion de la cita fabricada: el Autor la tiene a un clic."""
        hecho_id = await corpus.escribir_hecho(db, vectorizador, hecho(), fase_run_id=fase_run)
        await corpus.anotar_veredicto(db, hecho_id, respaldado=False)
        texto = (await informe.construir(db, fase_run)).como_texto()
        assert "su firmeza no pasa de inferido" in texto
        assert "https://ejemplo.test/cadiz" in texto

    async def test_cuenta_los_hechos_por_firmeza(
        self, db: aiosqlite.Connection, fase_run: int, vectorizador: VectorizadorFalso
    ) -> None:
        respaldado = await corpus.escribir_hecho(
            db, vectorizador, hecho(estado=EstadoEpistemico.VERIFICADO), fase_run_id=fase_run
        )
        flojo = await corpus.escribir_hecho(
            db, vectorizador, hecho(estado=EstadoEpistemico.VERIFICADO), fase_run_id=fase_run
        )
        await corpus.anotar_veredicto(db, respaldado, respaldado=True)
        await corpus.anotar_veredicto(db, flojo, respaldado=False)
        resultado = await informe.construir(db, fase_run)
        assert resultado.por_firmeza == {"documentado": 1, "inferido": 1}
        assert "Por firmeza: documentado 1, inferido 1." in resultado.como_texto()
