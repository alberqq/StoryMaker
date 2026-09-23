"""spec: §3.8 · arq: §13, §14

Pruebas de la capa de trazas.

Lo que importa comprobar aquí no es que Langfuse reciba los datos —eso es integración y se
demuestra observando la traza real—, sino tres cosas que sí son del arnés: que el nombre
del span identifica capítulo, rol e intento; que el coste viaja **etiquetado como
estimación**; y que sin credenciales el sistema corre igual.
"""

from __future__ import annotations

import aiosqlite
import pytest

from storymaker.commons.agents.invocacion import Consumo
from storymaker.commons.agents.techos import Perfil
from storymaker.commons.config import Settings
from storymaker.commons.obs import scores
from storymaker.commons.obs.prompts import RESPALDO, RepositorioDePrompts
from storymaker.commons.obs.trazas import (
    ObservadorLangfuse,
    ObservadorNulo,
    Span,
    construir,
    nombre_de_span,
)
from storymaker.commons.validation.modelos import Incidencia, Severidad


@pytest.fixture
def ajustes() -> Settings:
    return Settings(_env_file=None)


class TestNombreDeSpan:
    def test_capitulo_rol_e_intento(self) -> None:
        assert nombre_de_span(capitulo=7, rol="escritor", intento=2) == (
            "capitulo_07 · escritor · intento_2"
        )

    def test_las_fases_sin_capitulo_no_lo_inventan(self) -> None:
        assert nombre_de_span(capitulo=None, rol="investigador") == "investigador"


class TestSpan:
    def test_el_coste_viaja_etiquetado_como_estimacion(self) -> None:
        """Presentarlo como facturacion seria afirmar algo que el SDK no dice (U-7)."""
        span = Span(
            nombre=nombre_de_span(capitulo=1, rol="escritor", intento=1),
            rol="escritor",
            consumo=Consumo(tokens_in=1200, tokens_out=800, coste_usd=0.031),
        )
        payload = span.como_payload()
        assert payload["metadata"]["coste_usd_estimado_en_cliente"] == 0.031
        assert "coste_usd" not in payload["metadata"]

    def test_el_span_enlaza_el_paquete_de_contexto(self) -> None:
        """Poder abrir lo que el modelo vio es la definicion operativa de interpretable."""
        span = Span(nombre="capitulo_07 · escritor", rol="escritor", paquete_id=42)
        assert span.como_payload()["metadata"]["paquete_contexto_id"] == 42

    def test_la_version_del_prompt_viaja_en_el_span(self) -> None:
        span = Span(nombre="x", rol="arquitecto", prompt_version="7")
        assert span.como_payload()["metadata"]["prompt_version"] == "7"


class TestConstruccion:
    def test_sin_claves_el_observador_es_nulo(self, ajustes: Settings) -> None:
        """Perder las trazas no corrompe una novela: el sistema corre igual."""
        assert isinstance(construir(ajustes), ObservadorNulo)

    def test_con_claves_es_el_de_langfuse(self) -> None:
        # Valores de prueba, no credenciales: lo unico que se comprueba es la rama.
        con_claves = Settings(
            _env_file=None,
            langfuse_public_key="pk-de-prueba",
            langfuse_secret_key="sk-de-prueba",  # noqa: S106
        )
        assert isinstance(construir(con_claves), ObservadorLangfuse)


class TestScores:
    async def test_un_veredicto_favorable_tambien_puntua(
        self, db: aiosqlite.Connection
    ) -> None:
        """Sin esto no se distingue un validador correcto de uno que no llego a correr."""
        observador = ObservadorNulo()
        await scores.registrar_veredicto(
            db, observador, validador="longitud_capitulo", incidencias=[],
            objeto_tipo="capitulo_version", objeto_id=1,
        )
        assert observador.scores[0]["valor"] == 1.0
        async with db.execute("SELECT * FROM score") as cursor:
            fila = await cursor.fetchone()
        assert fila is not None and fila["validador"] == "longitud_capitulo"

    async def test_un_veredicto_con_incidencias_puntua_cero_y_las_lleva(
        self, db: aiosqlite.Connection
    ) -> None:
        observador = ObservadorNulo()
        await scores.registrar_veredicto(
            db,
            observador,
            validador="guardrail_prohibidas",
            incidencias=[
                Incidencia("guardrail_prohibidas", Severidad.BLOQUEANTE, "aparece «Beatriz»")
            ],
            objeto_tipo="capitulo_version",
            objeto_id=1,
        )
        assert observador.scores[0]["valor"] == 0.0
        assert "Beatriz" in observador.scores[0]["detalle"]["incidencias"][0]

    async def test_la_decision_del_autor_queda_trazada_como_la_de_un_agente(
        self, db: aiosqlite.Connection
    ) -> None:
        """Es parte de la revision humana que el enunciado exige, y tiene que verse."""
        observador = ObservadorNulo()
        await scores.registrar_decision_de_gate(
            db, observador, gate_id=3, decision="rehacer", actor="autor",
            comentario="falta cultura material",
        )
        async with db.execute("SELECT * FROM audit_log") as cursor:
            fila = await cursor.fetchone()
        assert fila is not None
        assert fila["accion"] == "gate:rehacer"
        assert observador.scores[0]["detalle"]["comentario"] == "falta cultura material"


class TestPrompts:
    def test_hay_respaldo_para_los_diez_perfiles(self, ajustes: Settings) -> None:
        """Sin credenciales el sistema tiene que poder escribir una novela igual."""
        assert set(RESPALDO) == set(Perfil)

    def test_sin_langfuse_la_version_dice_local(self, ajustes: Settings) -> None:
        """Una metrica producida sin Langfuse no se confunde con la version 7 de un prompt."""
        prompt = RepositorioDePrompts(ajustes).para(Perfil.ESCRITOR)
        assert prompt.es_local
        assert prompt.version == "local"
        assert "capitulo entero" in prompt.texto

    def test_el_verificador_sabe_que_no_tiene_red(self, ajustes: Settings) -> None:
        texto = RepositorioDePrompts(ajustes).para(Perfil.VERIFICADOR).texto
        assert "no tienes herramientas" in texto.lower()
