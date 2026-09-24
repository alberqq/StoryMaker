"""spec: §3.3 · arq: §12

Pruebas de la única puerta al modelo y de sus tres guardas.

Las tres son estructurales —impiden el acto en lugar de emitir un veredicto—, así que lo
que se comprueba aquí no es que informen, sino que **no dejan pasar**: que la llamada que
no cabe no se emite, que la cuarta búsqueda se deniega y que una página enorme no entra
entera en el contexto.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from pydantic import BaseModel

from storymaker.commons.agents.hooks import CuotaDeHerramientas, hook_post_tool_use, truncar_salida
from storymaker.commons.agents.invocacion import (
    Consumo,
    RespuestaBruta,
    invocar_rol,
)
from storymaker.commons.agents.presupuesto import estimar_tokens, guarda_techo
from storymaker.commons.agents.schema_guard import SalidaInvalida, validar
from storymaker.commons.agents.techos import (
    PEOR_CASO_DEL_SISTEMA,
    TECHOS,
    Perfil,
    herramientas_de,
    turnos_de,
)
from storymaker.commons.config import Defaults, Rol, Settings
from storymaker.commons.errores import PresupuestoExcedido


class SalidaDePrueba(BaseModel):
    titulo: str
    capitulos: int


@dataclass
class TransporteFalso:
    """Devuelve respuestas fijadas y anota lo que se le pidió."""

    respuestas: list[str] = field(default_factory=list)
    llamadas: list[dict[str, object]] = field(default_factory=list)

    async def pedir(self, **kwargs: object) -> RespuestaBruta:
        self.llamadas.append(kwargs)
        texto = self.respuestas.pop(0) if self.respuestas else "{}"
        return RespuestaBruta(texto, Consumo(tokens_in=100, tokens_out=50, coste_usd=0.001))


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None)


class TestTechos:
    def test_los_once_perfiles_tienen_techo(self) -> None:
        """Un agente sin fila seria un hueco en la suma con la que se garantiza §12."""
        assert len(TECHOS) == len(Perfil) == 11
        assert {t.rol for t in TECHOS.values()} == set(Rol)

    def test_el_peor_caso_es_la_sesion_inicial_del_investigador(self) -> None:
        assert PEOR_CASO_DEL_SISTEMA == 45_000
        assert TECHOS[Perfil.INVESTIGADOR_INICIAL].total == PEOR_CASO_DEL_SISTEMA
        assert PEOR_CASO_DEL_SISTEMA < Defaults.TOKENS_CONCURRENTES_MAXIMOS

    def test_solo_el_investigador_tiene_red(self) -> None:
        con_red = {p for p in Perfil if herramientas_de(p)}
        assert con_red == {
            Perfil.INVESTIGADOR_INICIAL,
            Perfil.INVESTIGADOR_MICRO,
            Perfil.INVESTIGADOR_DIRIGIDO,
        }
        assert {TECHOS[p].rol for p in con_red} == {Rol.INVESTIGADOR}
        assert herramientas_de(Perfil.ESCRITOR) == ()
        assert herramientas_de(Perfil.VERIFICADOR) == (), "el verificador trabaja sobre la cita"

    def test_la_micro_sesion_del_arquitecto_es_de_dos_turnos(self) -> None:
        assert turnos_de(Perfil.INVESTIGADOR_MICRO) == 2
        assert turnos_de(Perfil.ESCRITOR) == 1


class TestGuardaDePresupuesto:
    def test_un_prompt_que_cabe_pasa(self) -> None:
        assert guarda_techo(Perfil.ESCRITOR, "un encargo corto") > 0

    def test_un_prompt_que_no_cabe_no_se_emite(self) -> None:
        """No es una comprobación posterior: la llamada no llega a hacerse."""
        enorme = "palabra " * 20_000
        with pytest.raises(PresupuestoExcedido):
            guarda_techo(Perfil.ESCRITOR, enorme)

    def test_la_estimacion_es_por_lo_alto(self) -> None:
        """Sobreestimar rechaza algo que cabía; subestimar revienta la ventana."""
        texto = "a" * 350
        assert estimar_tokens(texto) >= 100


class TestCuotaDeHerramientas:
    def test_las_tres_primeras_busquedas_pasan_y_la_cuarta_no(self) -> None:
        cuota = CuotaDeHerramientas.para(Perfil.INVESTIGADOR_INICIAL)
        decisiones = [cuota.decidir("WebSearch")["permissionDecision"] for _ in range(4)]
        assert decisiones == ["allow", "allow", "allow", "deny"]

    def test_los_fetches_llevan_su_propia_cuenta(self) -> None:
        """El tope es doble: quien llena la ventana no es la busqueda, es la pagina."""
        cuota = CuotaDeHerramientas.para(Perfil.INVESTIGADOR_INICIAL)
        for _ in range(3):
            cuota.decidir("WebSearch")
        assert cuota.decidir("WebFetch")["permissionDecision"] == "allow"

    def test_la_micro_sesion_solo_tiene_una(self) -> None:
        cuota = CuotaDeHerramientas.para(Perfil.INVESTIGADOR_MICRO)
        assert cuota.decidir("WebSearch")["permissionDecision"] == "allow"
        assert cuota.decidir("WebSearch")["permissionDecision"] == "deny"

    def test_toolsearch_carga_las_herramientas_diferidas_sin_gastar_cuota(self) -> None:
        """Sin ella el investigador no podia cargar `WebSearch` y sellaba un corpus vacio."""
        cuota = CuotaDeHerramientas.para(Perfil.INVESTIGADOR_MICRO)
        assert cuota.decidir("ToolSearch")["permissionDecision"] == "allow"
        assert cuota.decidir("ToolSearch")["permissionDecision"] == "allow"
        assert cuota.decidir("WebSearch")["permissionDecision"] == "allow"
        assert cuota.decidir("WebSearch")["permissionDecision"] == "deny"

    def test_un_rol_sin_red_tampoco_carga_herramientas(self) -> None:
        cuota = CuotaDeHerramientas.para(Perfil.ESCRITOR)
        assert cuota.decidir("ToolSearch")["permissionDecision"] == "deny"

    def test_un_rol_sin_cuota_no_puede_salir_a_la_red(self) -> None:
        cuota = CuotaDeHerramientas.para(Perfil.ESCRITOR)
        assert cuota.decidir("WebFetch")["permissionDecision"] == "deny"


class TestTruncado:
    def test_una_pagina_enorme_no_entra_entera(self) -> None:
        pagina = "contenido " * 20_000
        recortada = truncar_salida(pagina, techo_tokens=Defaults.TECHO_WEBFETCH_TOKENS)
        assert estimar_tokens(recortada) <= Defaults.TECHO_WEBFETCH_TOKENS + 50
        assert "recortado por el arnes" in recortada

    def test_lo_que_cabe_se_deja_intacto(self) -> None:
        corto = "un resultado breve"
        assert truncar_salida(corto) == corto

    def test_el_hook_devuelve_la_forma_que_el_sdk_espera(self) -> None:
        assert "updatedToolOutput" in hook_post_tool_use("texto")


class TestSchemaGuard:
    def test_acepta_json_envuelto_en_prosa(self) -> None:
        """Fallar por una valla de markdown gastaria un reintento en algo ajeno al contenido."""
        bruto = 'Aqui tienes:\n```json\n{"titulo": "La bahia", "capitulos": 10}\n```\nEso es todo.'
        assert validar(SalidaDePrueba, bruto).titulo == "La bahia"

    def test_rechaza_lo_que_no_cumple_el_esquema(self) -> None:
        with pytest.raises(SalidaInvalida) as fallo:
            validar(SalidaDePrueba, '{"titulo": "La bahia"}')
        assert "capitulos" in str(fallo.value), "el motivo viaja al reintento"


class TestInvocacion:
    async def test_devuelve_la_salida_validada_y_el_consumo(self, settings: Settings) -> None:
        transporte = TransporteFalso(respuestas=['{"titulo": "La bahia", "capitulos": 10}'])
        resultado = await invocar_rol(
            Perfil.ARQUITECTO, "construye la escaleta", SalidaDePrueba,
            transporte=transporte, settings=settings,
        )
        assert resultado.valor.capitulos == 10
        assert resultado.consumo.tokens_in == 100
        assert resultado.intentos == 1

    async def test_fija_modelo_herramientas_y_turnos_por_invocacion(
        self, settings: Settings
    ) -> None:
        transporte = TransporteFalso(respuestas=['{"titulo": "x", "capitulos": 1}'])
        await invocar_rol(
            Perfil.INVESTIGADOR_INICIAL, "investiga Cadiz 1805", SalidaDePrueba,
            transporte=transporte, settings=settings,
        )
        (llamada,) = transporte.llamadas
        assert llamada["modelo"] == Defaults.MODELO_HAIKU
        assert llamada["herramientas"] == ("WebSearch", "WebFetch")
        assert llamada["max_turns"] == 20

    async def test_el_esquema_de_salida_viaja_con_la_llamada(self, settings: Settings) -> None:
        """REQ-BE-132: sin él, el rol improvisa los campos, como en la primera ejecución real."""
        transporte = TransporteFalso(respuestas=['{"titulo": "x", "capitulos": 1}'])
        await invocar_rol(
            Perfil.ARQUITECTO, "construye la escaleta", SalidaDePrueba,
            transporte=transporte, settings=settings,
        )
        (llamada,) = transporte.llamadas
        prompt = str(llamada["prompt"])
        assert prompt.startswith("construye la escaleta")
        assert '"titulo"' in prompt and '"capitulos"' in prompt
        assert '"required":["titulo","capitulos"]' in prompt

    async def test_reintenta_inyectando_el_error_de_validacion(
        self, settings: Settings
    ) -> None:
        transporte = TransporteFalso(
            respuestas=['{"titulo": "falta el resto"}', '{"titulo": "ok", "capitulos": 3}']
        )
        resultado = await invocar_rol(
            Perfil.ARQUITECTO, "construye la escaleta", SalidaDePrueba,
            transporte=transporte, settings=settings,
        )
        assert resultado.intentos == 2
        segundo_prompt = str(transporte.llamadas[1]["prompt"])
        assert "no cumplia el esquema" in segundo_prompt
        assert "capitulos" in segundo_prompt

    async def test_agotados_los_reintentos_falla(self, settings: Settings) -> None:
        transporte = TransporteFalso(respuestas=['{"mal": 1}', '{"peor": 2}'])
        with pytest.raises(SalidaInvalida):
            await invocar_rol(
                Perfil.ARQUITECTO, "x", SalidaDePrueba,
                transporte=transporte, settings=settings,
            )

    async def test_si_no_cabe_el_transporte_ni_se_toca(self, settings: Settings) -> None:
        transporte = TransporteFalso(respuestas=['{"titulo": "x", "capitulos": 1}'])
        with pytest.raises(PresupuestoExcedido):
            await invocar_rol(
                Perfil.ESCRITOR, "palabra " * 20_000, SalidaDePrueba,
                transporte=transporte, settings=settings,
            )
        assert transporte.llamadas == [], "la llamada no se emitio"


class TestHooksDelTransporte:
    """La forma que el SDK exige a los hooks, que la suite no veía y la primera ejecución real sí.

    Con la función suelta en lugar de una lista de `HookMatcher`, el SDK revienta al convertir
    las opciones, antes de lanzar el subproceso. Solo corre con el extra `agentes` instalado.
    """

    def test_cada_evento_lleva_una_lista_de_matchers(self) -> None:
        sdk = pytest.importorskip("claude_agent_sdk")
        from storymaker.commons.agents.transporte_sdk import TransporteAgentSDK

        hooks = TransporteAgentSDK()._hooks(CuotaDeHerramientas.para(Perfil.INVESTIGADOR_INICIAL))
        assert set(hooks) == {"PreToolUse", "PostToolUse"}
        for matchers in hooks.values():
            assert all(isinstance(m, sdk.HookMatcher) and m.hooks for m in matchers)

    def test_el_truncado_solo_toca_webfetch(self) -> None:
        pytest.importorskip("claude_agent_sdk")
        from storymaker.commons.agents.transporte_sdk import TransporteAgentSDK

        hooks = TransporteAgentSDK()._hooks(CuotaDeHerramientas.para(Perfil.INVESTIGADOR_INICIAL))
        assert [m.matcher for m in hooks["PostToolUse"]] == ["WebFetch"]
