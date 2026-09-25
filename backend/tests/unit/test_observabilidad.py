"""spec: §3.8 · arq: §13, §14

Pruebas de la capa de trazas.

Lo que importa comprobar aquí no es que Langfuse reciba los datos —eso es integración y se
demuestra observando la traza real—, sino tres cosas que sí son del arnés: que el nombre
del span identifica capítulo, rol e intento; que el coste viaja **etiquetado como
estimación**; y que sin credenciales el sistema corre igual.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import aiosqlite
import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from storymaker.commons.agents.invocacion import Consumo, LlamadaAHerramienta
from storymaker.commons.agents.techos import Perfil
from storymaker.commons.agents.transporte_sdk import (
    RegistroDeHerramientas,
    _consumo_de,
    recortar,
)
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


class ClienteFalso:
    """Lo que `ObservadorLangfuse` usa del SDK v4, grabado en lugar de enviado."""

    def __init__(self) -> None:
        self.observaciones: list[dict[str, Any]] = []
        self.scores: list[dict[str, Any]] = []
        self.vaciado = False

    def start_observation(self, **argumentos: Any) -> ClienteFalso:
        self.observaciones.append(argumentos)
        return self

    def end(self) -> None:
        return None

    def create_score(self, **argumentos: Any) -> None:
        self.scores.append(argumentos)

    def flush(self) -> None:
        self.vaciado = True


def _con_cliente(cliente: object) -> ObservadorLangfuse:
    observador = ObservadorLangfuse(Settings(_env_file=None))
    observador._cliente = cliente
    return observador


class TestLangfuse:
    """La API v4: una `generation` por invocación, con tokens y coste, y todo en la sesión."""

    def test_cada_invocacion_es_una_generation_con_tokens_y_coste(self) -> None:
        cliente = ClienteFalso()
        observador = _con_cliente(cliente)
        observador.abrir_sesion("sevilla")
        observador.registrar_span(
            Span(
                nombre="capitulo_01 · escritor · intento_1",
                rol="escritor",
                consumo=Consumo(tokens_in=1200, tokens_out=800, coste_usd=0.031),
            )
        )
        # El capítulo abre antes su span; la invocación es la `generation` que cuelga de él.
        capitulo, observacion = cliente.observaciones
        assert capitulo["name"] == "capitulo_01" and capitulo["as_type"] == "span"
        assert observacion["as_type"] == "generation"
        assert observacion["usage_details"] == {"input": 1200, "output": 800}
        assert observacion["cost_details"] == {"total": 0.031}

    def test_la_sesion_es_la_novela(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Sin sesión, Langfuse no podría sumar el coste por novela."""
        import langfuse

        propagadas: list[dict[str, Any]] = []

        @contextmanager
        def propagar(**argumentos: Any) -> Iterator[None]:
            propagadas.append(argumentos)
            yield

        monkeypatch.setattr(langfuse, "propagate_attributes", propagar)
        cliente = ClienteFalso()
        observador = _con_cliente(cliente)
        observador.abrir_sesion("sevilla")
        observador.registrar_span(Span(nombre="arquitecto", rol="arquitecto"))
        observador.registrar_score(nombre="juez_rubrica", valor=7.0, objeto="novela:1")
        assert propagadas[0]["session_id"] == "sevilla"
        assert cliente.scores[0]["session_id"] == "sevilla"

    def test_un_fallo_de_langfuse_no_tumba_el_nodo(self) -> None:
        class Roto:
            def start_observation(self, **_: Any) -> None:
                raise ConnectionError("sin red")

            def create_score(self, **_: Any) -> None:
                raise ConnectionError("sin red")

        observador = _con_cliente(Roto())
        observador.registrar_span(Span(nombre="x", rol="escritor"))
        observador.registrar_score(nombre="x", valor=1.0, objeto="y")

    def test_cerrar_vacia_lo_pendiente(self) -> None:
        cliente = ClienteFalso()
        _con_cliente(cliente).cerrar()
        assert cliente.vaciado

    def test_construir_con_novela_abre_la_sesion(self, ajustes: Settings) -> None:
        observador = construir(ajustes, novela="sevilla")
        assert isinstance(observador, ObservadorNulo) and observador.sesion == "sevilla"


class TestScores:
    async def test_un_veredicto_favorable_tambien_puntua(self, db: aiosqlite.Connection) -> None:
        """Sin esto no se distingue un validador correcto de uno que no llego a correr."""
        observador = ObservadorNulo()
        await scores.registrar_veredicto(
            db,
            observador,
            validador="longitud_capitulo",
            incidencias=[],
            objeto_tipo="capitulo_version",
            objeto_id=1,
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
            db,
            observador,
            gate_id=3,
            decision="rehacer",
            actor="autor",
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


# --- spec observabilidad: la traza de una generación ------------------------------------


class TestConsumo:
    def test_sumar_acumula_duracion_y_concatena_herramientas(self) -> None:
        """Con reintentos de esquema, la invocación duró lo que duraron sus intentos."""
        primera = LlamadaAHerramienta("WebSearch", "{}", 1.0, 2.0)
        segunda = LlamadaAHerramienta("WebFetch", "{}", 3.0, 4.0, error=True)
        total = Consumo(duracion_ms=1500, herramientas=(primera,)) + Consumo(
            duracion_ms=500, herramientas=(segunda,)
        )
        assert total.duracion_ms == 2000
        assert total.herramientas == (primera, segunda)


class TestRegistroDeHerramientas:
    """Del flujo de mensajes del SDK salen las llamadas, sin tocar los hooks de cuota."""

    @staticmethod
    def _bloque(tipo: str, **campos: Any) -> object:
        return type(tipo, (), campos)()

    def test_empareja_uso_y_resultado_por_id(self) -> None:
        registro = RegistroDeHerramientas()
        registro.ver(self._bloque("ToolUseBlock", id="t1", name="WebSearch", input={"q": "x"}))
        registro.ver(self._bloque("TextBlock", text="buscando"))
        registro.ver(self._bloque("ToolResultBlock", tool_use_id="t1", is_error=False))
        (llamada,) = registro.cerrar()
        assert llamada.nombre == "WebSearch"
        assert llamada.entrada == '{"q": "x"}'
        assert llamada.fin >= llamada.inicio and not llamada.error

    def test_una_denegada_o_sin_resultado_es_error(self) -> None:
        registro = RegistroDeHerramientas()
        registro.ver(self._bloque("ToolUseBlock", id="t1", name="WebFetch", input={}))
        registro.ver(self._bloque("ToolResultBlock", tool_use_id="t1", is_error=True))
        registro.ver(self._bloque("ToolUseBlock", id="t2", name="WebFetch", input={}))
        assert [llamada.error for llamada in registro.cerrar()] == [True, True]

    def test_la_entrada_se_recorta(self) -> None:
        assert len(recortar({"contenido": "a" * 2000})) == 500

    def test_la_duracion_sale_del_result_message(self) -> None:
        mensaje = self._bloque("ResultMessage", usage={}, total_cost_usd=0.0, duration_ms=4200)
        assert _consumo_de(mensaje).duracion_ms == 4200


@pytest.fixture
def exportados() -> Iterator[tuple[ObservadorLangfuse, InMemorySpanExporter]]:
    """El observador sobre el SDK real, exportando a memoria: sin red y sin claves."""
    from langfuse import Langfuse

    exportador = InMemorySpanExporter()
    observador = ObservadorLangfuse(Settings(_env_file=None))
    # Valores de prueba, no credenciales: el exportador en memoria no envía nada.
    observador._cliente = Langfuse(
        public_key="pk-lf-prueba-traza",
        secret_key="sk-lf-prueba-traza",  # noqa: S106
        host="http://127.0.0.1:9",
        span_exporter=exportador,
    )
    yield observador, exportador
    exportador.clear()


def _por_nombre(exportador: InMemorySpanExporter) -> dict[str, Any]:
    return {span.name: span for span in exportador.get_finished_spans()}


class TestTrazaDeGeneracion:
    def test_la_misma_generacion_es_la_misma_traza(self) -> None:
        """Arranque y reanudaciones son procesos distintos, pero una sola generación."""
        ajustes = Settings(_env_file=None)
        arranque, reanudacion, regeneracion = (ObservadorLangfuse(ajustes) for _ in range(3))
        arranque.abrir_sesion("sevilla", generacion=1)
        reanudacion.abrir_sesion("sevilla", generacion=1)
        regeneracion.abrir_sesion("sevilla", generacion=2)
        assert arranque._traza_id == reanudacion._traza_id
        assert arranque._traza_id != regeneracion._traza_id

    def test_capitulo_generation_y_tool_con_su_latencia(
        self, exportados: tuple[ObservadorLangfuse, InMemorySpanExporter]
    ) -> None:
        observador, exportador = exportados
        observador.abrir_sesion("sevilla", generacion=1)
        ahora = time.time()
        busqueda = LlamadaAHerramienta("WebSearch", '{"q": "x"}', ahora - 2, ahora - 1)
        observador.registrar_span(
            Span(
                nombre="capitulo_03 · escritor · intento_1",
                rol="escritor",
                consumo=Consumo(duracion_ms=2500, herramientas=(busqueda,)),
            )
        )
        observador.registrar_span(
            Span(nombre="arquitecto", rol="arquitecto", consumo=Consumo(duracion_ms=1000))
        )
        cliente = observador._cliente
        cliente.flush = lambda: None
        observador.cerrar()
        cliente._resources.tracer_provider.force_flush()

        spans = _por_nombre(exportador)
        capitulo = spans["capitulo_03"]
        escritor = spans["capitulo_03 · escritor · intento_1"]
        herramienta = spans["WebSearch"]
        arquitecto = spans["arquitecto"]
        # Todo en la traza de la generación, y en la sesión de la novela.
        assert {f"{s.context.trace_id:032x}" for s in spans.values()} == {observador._traza_id}
        assert {s.attributes["session.id"] for s in spans.values()} == {"sevilla"}
        # La jerarquía: capítulo → generation → tool; sin capítulo, directo a la traza.
        assert escritor.parent.span_id == capitulo.context.span_id
        assert herramienta.parent.span_id == escritor.context.span_id
        assert arquitecto.parent.span_id != capitulo.context.span_id
        # La latencia es la del SDK, no cero.
        assert (escritor.end_time - escritor.start_time) // 1_000_000 == 2500
        assert (arquitecto.end_time - arquitecto.start_time) // 1_000_000 == 1000
        assert capitulo.end_time == escritor.end_time

    def test_sin_via_interna_se_usa_la_publica(self) -> None:
        """El `ClienteFalso` no tiene tracer: la observación sale igual, a latencia cero."""
        cliente = ClienteFalso()
        observador = _con_cliente(cliente)
        observador.abrir_sesion("sevilla", generacion=1)
        observador.registrar_span(Span(nombre="juez", rol="juez", consumo=Consumo(duracion_ms=9)))
        (observacion,) = cliente.observaciones
        assert observacion["trace_context"] == {"trace_id": observador._traza_id}
        assert observacion["metadata"]["duracion_ms"] == 9

    def test_las_herramientas_fallidas_van_como_error(self) -> None:
        cliente = ClienteFalso()
        observador = _con_cliente(cliente)
        fallida = LlamadaAHerramienta("WebFetch", "{}", 1.0, 2.0, error=True)
        observador.registrar_span(
            Span(
                nombre="investigador",
                rol="investigador",
                consumo=Consumo(herramientas=(fallida,)),
            )
        )
        _, herramienta = cliente.observaciones
        assert herramienta["as_type"] == "tool" and herramienta["level"] == "ERROR"
        assert herramienta["input"] == "{}"

    def test_la_generation_se_enlaza_a_su_prompt(self) -> None:
        pedidos: list[tuple[str, int]] = []

        class ConPrompts(ClienteFalso):
            def get_prompt(self, nombre: str, *, version: int) -> str:
                pedidos.append((nombre, version))
                return f"prompt:{nombre}:{version}"

        cliente = ConPrompts()
        observador = _con_cliente(cliente)
        observador.registrar_span(
            Span(
                nombre="investigador",
                rol="investigador",
                prompt_version="3",
                prompt_nombre="investigador_micro",
            )
        )
        observador.registrar_span(Span(nombre="juez", rol="juez", prompt_version="local"))
        assert pedidos == [("investigador_micro", 3)]
        assert cliente.observaciones[0]["prompt"] == "prompt:investigador_micro:3"
        assert cliente.observaciones[1]["prompt"] is None

    def test_los_scores_van_a_la_traza(self) -> None:
        cliente = ClienteFalso()
        observador = _con_cliente(cliente)
        observador.abrir_sesion("sevilla", generacion=1)
        observador.registrar_score(nombre="longitud_capitulo", valor=1.0, objeto="c:1")
        assert cliente.scores[0]["trace_id"] == observador._traza_id
        assert "session_id" not in cliente.scores[0]


class _PromptsRemotos:
    """Lo que `RepositorioDePrompts` usa de Langfuse, con un juego de prompts existentes."""

    def __init__(self, existentes: set[str]) -> None:
        self.existentes = existentes
        self.creados: list[dict[str, Any]] = []

    def get_prompt(self, nombre: str, **opciones: Any) -> Any:
        if nombre in self.existentes:
            return type("P", (), {"prompt": "remoto", "version": 7, "is_fallback": False})()
        if "fallback" in opciones:
            campos = {"prompt": opciones["fallback"], "version": 0, "is_fallback": True}
            return type("P", (), campos)()
        raise LookupError(nombre)

    def create_prompt(self, **argumentos: Any) -> None:
        self.creados.append(argumentos)

    def flush(self) -> None:
        return None


def _repositorio(remoto: object) -> RepositorioDePrompts:
    repositorio = RepositorioDePrompts(Settings(_env_file=None))
    repositorio._cliente = remoto
    return repositorio


class TestSiembraDePrompts:
    def test_el_respaldo_de_langfuse_dice_local(self) -> None:
        prompt = _repositorio(_PromptsRemotos(set())).para(Perfil.ESCRITOR)
        assert prompt.version == "local" and prompt.nombre == "escritor"
        assert prompt.texto == RESPALDO[Perfil.ESCRITOR]

    def test_el_remoto_trae_su_version(self) -> None:
        prompt = _repositorio(_PromptsRemotos({"juez"})).para(Perfil.JUEZ)
        assert (prompt.texto, prompt.version, prompt.nombre) == ("remoto", "7", "juez")

    def test_subir_solo_crea_los_que_faltan(self) -> None:
        """La versión que el Autor editó en Langfuse manda sobre la semilla."""
        remoto = _PromptsRemotos({"juez", "escritor"})
        creados, existentes = _repositorio(remoto).subir()
        assert sorted(existentes) == ["escritor", "juez"]
        assert len(creados) == len(Perfil) - 2
        assert all(c["labels"] == ["production"] for c in remoto.creados)
        assert {c["name"] for c in remoto.creados}.isdisjoint({"juez", "escritor"})
