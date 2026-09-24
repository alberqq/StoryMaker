"""spec: §3.4, §4.2, §4.3 · arq: §4, §7

La firmeza en el flujo: dónde se escribe lo que la alimenta y dónde se lee.

`test_firmeza.py` demuestra la regla sobre su dominio entero. Aquí se comprueba lo que la
rodea: que los hechos de la micro-sesión pasan por el verificador y que un fallo suyo no
detiene la escaleta, que la invención no pasa por él, que el sello cambia con el respaldo,
que el investigador recibe las definiciones de los cuatro estados y que el arquitecto ve la
firmeza y no el estado declarado.
"""

from __future__ import annotations

import aiosqlite
import pytest
from dobles import guion
from dobles.agente_falso import TransporteFalso
from dobles.fabrica import poblar
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.agents.techos import Perfil
from storymaker.commons.config import Settings
from storymaker.commons.context.bloques import nota_de_la_cita
from storymaker.commons.db.repos import mundo, plan
from storymaker.commons.graph.dependencias import Dependencias, usando
from storymaker.commons.obs.trazas import ObservadorNulo
from storymaker.commons.validation.puras import firmeza
from storymaker.investigation import corpus, prompts
from storymaker.investigation.esquemas import (
    Dimension,
    EstadoEpistemico,
    HechoPropuesto,
    SalidaVerificador,
    VeredictoDeRespaldo,
)
from storymaker.plotting import contexto
from storymaker.plotting.informe import InformeDePlotting
from storymaker.plotting.nodos import USO_DE_LA_FIRMEZA_EN_LA_TRAMA, cubrir_hueco

PERIODO, LUGAR = "Siglo de Oro (1572-1576)", "Salamanca"


@pytest.fixture
def vectorizador() -> VectorizadorFalso:
    return VectorizadorFalso()


def dependencias(db: aiosqlite.Connection, transporte: TransporteFalso) -> Dependencias:
    return Dependencias(
        db=db,
        settings=Settings(_env_file=None),
        transporte=transporte,
        vectorizador=VectorizadorFalso(),
        observador=ObservadorNulo(),
    )


def veredicto(hecho_id: int, *, respaldado: bool) -> SalidaVerificador:
    return SalidaVerificador(
        veredictos=[VeredictoDeRespaldo(hecho_id=hecho_id, respaldado=respaldado, motivo="m")]
    )


async def hueco(db: aiosqlite.Connection, transporte: TransporteFalso, fase_run: int) -> int:
    with usando(dependencias(db, transporte)):
        hecho_id, _ = await cubrir_hueco(
            "Como eran los pupitres",
            periodo=PERIODO,
            lugar=LUGAR,
            fase_run_id=fase_run,
            dimension=Dimension.CULTURA_MATERIAL,
        )
    return hecho_id


class TestMicroSesion:
    async def test_el_hecho_de_la_micro_sesion_pasa_por_el_verificador(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        """Un veredicto mal numerado se toma igual: solo hay un hecho en juego."""
        transporte = TransporteFalso()
        transporte.preparar(Perfil.INVESTIGADOR_MICRO, guion.hueco_resuelto())
        transporte.preparar(Perfil.VERIFICADOR, veredicto(999, respaldado=False))
        hecho_id = await hueco(db, transporte, fase_run)

        fila = await mundo.hecho_por_id(db, hecho_id)
        assert fila is not None
        assert transporte.veces(Perfil.VERIFICADOR) == 1
        assert fila["estado"] == "verificado"
        assert fila["respaldo"] == "no_respaldado"
        assert firmeza(fila["estado"], fila["respaldo"], fila["origen"]) == "inferido"

    async def test_respaldado_queda_documentado(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        transporte = TransporteFalso()
        transporte.preparar(Perfil.INVESTIGADOR_MICRO, guion.hueco_resuelto())
        transporte.preparar(Perfil.VERIFICADOR, veredicto(1, respaldado=True))
        fila = await mundo.hecho_por_id(db, await hueco(db, transporte, fase_run))
        assert fila is not None
        assert firmeza(fila["estado"], fila["respaldo"], fila["origen"]) == "documentado"

    async def test_un_fallo_del_verificador_deja_el_hecho_pendiente(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        """La escaleta no se detiene, y lo que nadie comprobó no pasa de inferido."""
        transporte = TransporteFalso()
        transporte.preparar(Perfil.INVESTIGADOR_MICRO, guion.hueco_resuelto())
        transporte.preparar(Perfil.VERIFICADOR, "no es json", "tampoco", "nada")
        fila = await mundo.hecho_por_id(db, await hueco(db, transporte, fase_run))
        assert fila is not None
        assert fila["respaldo"] == "pendiente"
        assert firmeza(fila["estado"], fila["respaldo"], fila["origen"]) == "inferido"

    async def test_la_invencion_no_pasa_por_el_verificador(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        transporte = TransporteFalso()
        transporte.preparar(Perfil.INVESTIGADOR_MICRO, '{"encontrado": false}')
        fila = await mundo.hecho_por_id(db, await hueco(db, transporte, fase_run))
        assert fila is not None
        assert transporte.veces(Perfil.VERIFICADOR) == 0
        assert fila["respaldo"] == "no_aplica"
        assert firmeza(fila["estado"], fila["respaldo"], fila["origen"]) == "inventado"

    async def test_el_informe_de_plotting_cuenta_los_micro_sin_respaldo(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        transporte = TransporteFalso()
        transporte.preparar(Perfil.INVESTIGADOR_MICRO, guion.hueco_resuelto())
        transporte.preparar(Perfil.VERIFICADOR, veredicto(1, respaldado=False))
        await hueco(db, transporte, fase_run)

        cuantos = await mundo.micro_sin_respaldo(db, fase_run)
        assert cuantos == 1
        informe = InformeDePlotting(
            capitulos=1,
            escenas=2,
            inventados_por_dimension={},
            huecos_gastados=1,
            micro_sin_respaldo=cuantos,
        )
        assert "1 hecho(s) de la micro-investigacion sin respaldo" in informe.como_texto()


class TestSello:
    async def test_el_sello_cambia_con_el_respaldo(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        hecho_id = await mundo.insertar_hecho(
            db,
            fase_run_id=fase_run,
            enunciado="La imprenta de Salamanca tenia tres prensas",
            estado="verificado",
            dimension="cultura_material",
            cita="tres prensas",
        )
        antes = await mundo.calcular_hash_corpus(db, fase_run)
        await mundo.anotar_respaldo(db, hecho_id, "no_respaldado")
        assert await mundo.calcular_hash_corpus(db, fase_run) != antes


class TestPrompts:
    def test_los_prompts_definen_los_cuatro_estados(self) -> None:
        definicion = "versiones distintas"
        assert definicion in prompts.prompt_de_investigacion(PERIODO, LUGAR)
        assert definicion in prompts.prompt_de_dimension(
            PERIODO, LUGAR, Dimension.LUGAR, comentarios=""
        )
        assert definicion in prompts.prompt_de_hueco("Como eran los pupitres", PERIODO, LUGAR)

    def test_la_micro_sesion_pide_la_cita(self) -> None:
        """Sin cita, el verificador no tendría nada que leer y todo saldría sin respaldo."""
        assert "cita textual" in prompts.prompt_de_hueco("Como eran los pupitres", PERIODO, LUGAR)


class TestLectores:
    async def test_el_arquitecto_ve_la_firmeza(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        hecho_id = await mundo.insertar_hecho(
            db,
            fase_run_id=fase_run,
            enunciado="Fray Luis volvio a su catedra en 1576",
            estado="verificado",
            dimension="cronologia",
            cita="otra cosa",
        )
        await mundo.anotar_respaldo(db, hecho_id, "no_respaldado")
        texto = contexto.como_texto(await mundo.hechos_vigentes(db, fase_run))
        assert texto.startswith("[inferido·cronologia]")


class TestParcial:
    """El veredicto parcial: el dato central se respalda y el añadido se aparta."""

    async def test_el_parcial_conserva_la_firmeza_y_guarda_el_anadido(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        transporte = TransporteFalso()
        transporte.preparar(Perfil.INVESTIGADOR_MICRO, guion.hueco_resuelto())
        transporte.preparar(
            Perfil.VERIFICADOR,
            SalidaVerificador(
                veredictos=[
                    VeredictoDeRespaldo(
                        hecho_id=1, respaldado=True, sin_respaldo="con tintero empotrado"
                    )
                ]
            ),
        )
        fila = await mundo.hecho_por_id(db, await hueco(db, transporte, fase_run))
        assert fila is not None
        assert (fila["respaldo"], fila["sin_respaldo"]) == ("respaldado", "con tintero empotrado")
        assert firmeza(fila["estado"], fila["respaldo"], fila["origen"]) == "documentado"

    async def test_un_no_respaldado_no_guarda_anadido(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        """Si el dato central no se sostiene, no hay nada que separar."""
        hecho_id = await mundo.insertar_hecho(
            db, fase_run_id=fase_run, enunciado="x", estado="verificado", dimension="lugar"
        )
        await corpus.anotar_veredicto(db, hecho_id, respaldado=False, sin_respaldo="algo")
        fila = await mundo.hecho_por_id(db, hecho_id)
        assert fila is not None
        assert fila["sin_respaldo"] is None

    def test_el_prompt_del_verificador_pide_el_anadido(self) -> None:
        texto = prompts.prompt_de_verificacion([(1, "algo", "cita")])
        assert "dato central" in texto
        assert "sin_respaldo" in texto
        assert "no tumba el hecho" in texto, "la fecha o el lugar que falten son un añadido"
        assert "titulo" not in texto.lower(), "el verificador no ve el titulo de la fuente"

    async def test_una_laguna_no_pasa_por_el_verificador(
        self, db: aiosqlite.Connection, fase_run: int, vectorizador: VectorizadorFalso
    ) -> None:
        laguna = HechoPropuesto(
            enunciado="No se sabe como se trataba a los tipografos",
            estado=EstadoEpistemico.DESCONOCIDO,
            dimension=Dimension.LENGUAJE,
        )
        hecho_id = await corpus.escribir_hecho(db, vectorizador, laguna, fase_run_id=fase_run)
        fila = await mundo.hecho_por_id(db, hecho_id)
        assert fila is not None
        assert fila["respaldo"] == "no_aplica"
        assert await mundo.pendientes_de_verificar(db, fase_run, tamano_lote=20) == []
        assert firmeza(fila["estado"], fila["respaldo"], fila["origen"]) == "desconocido"

    async def test_el_sello_cambia_con_el_anadido(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        hecho_id = await mundo.insertar_hecho(
            db, fase_run_id=fase_run, enunciado="x y", estado="verificado", dimension="lugar"
        )
        await mundo.anotar_respaldo(db, hecho_id, "respaldado")
        antes = await mundo.calcular_hash_corpus(db, fase_run)
        await mundo.anotar_respaldo(db, hecho_id, "respaldado", "y")
        assert await mundo.calcular_hash_corpus(db, fase_run) != antes


class TestLectoresDelParcial:
    async def test_el_arquitecto_ve_lo_que_no_dice_la_cita(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        hecho_id = await mundo.insertar_hecho(
            db,
            fase_run_id=fase_run,
            enunciado="El Congreso se celebro en agosto de 1888, donde se fundo la UGT",
            estado="verificado",
            dimension="cronologia",
            cita="se celebro en agosto de 1888",
        )
        await mundo.anotar_respaldo(db, hecho_id, "respaldado", "donde se fundo la UGT")
        texto = contexto.como_texto(await mundo.hechos_vigentes(db, fase_run))
        assert texto.startswith("[documentado·cronologia]")
        assert "(no lo dice la cita: «donde se fundo la UGT»)" in texto

    def test_el_anadido_quitado_por_el_autor_deja_de_verse(self) -> None:
        assert nota_de_la_cita("El Congreso se celebro en 1888", "donde se fundo la UGT") == ""

    def test_el_arquitecto_recibe_el_uso_de_la_firmeza(self) -> None:
        assert "documentado: apoya aqui el evento ancla" in USO_DE_LA_FIRMEZA_EN_LA_TRAMA

    async def test_el_informe_de_plotting_avisa_de_las_escenas_poco_firmes(
        self, db: aiosqlite.Connection
    ) -> None:
        novela = await poblar(db)
        assert await plan.escenas_poco_firmes(db) == []
        await mundo.anotar_respaldo(db, novela.hecho_anclado, "no_respaldado")
        poco_firmes = await plan.escenas_poco_firmes(db)
        assert len(poco_firmes) == 1
        informe = InformeDePlotting(
            capitulos=2,
            escenas=2,
            inventados_por_dimension={},
            huecos_gastados=0,
            escenas_poco_firmes=tuple(poco_firmes),
        )
        capitulo, orden = poco_firmes[0]
        assert f"cap. {capitulo} esc. {orden}" in informe.como_texto()
