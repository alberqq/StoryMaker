"""spec: §2.2 · arq: §19

Pruebas de `commons.config`. Comprueban dos cosas distintas: que los valores por
defecto del arnés son los que declara §19 de la arquitectura, y que `Settings` se
puede construir sin tocar el entorno del proceso — que es lo que permite a las
demás pruebas inyectar una configuración propia.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storymaker.commons.config import Defaults, Rol, Settings


class TestDefaults:
    """Los valores de §19, uno por uno. Un cambio aquí es un cambio de arquitectura."""

    def test_dimensiones_de_la_obra(self) -> None:
        assert Defaults.N_CAPITULOS == 10
        assert Defaults.PALABRAS_POR_CAPITULO == 1200
        assert Defaults.RANGO_PALABRAS == (1000, 1500)
        assert Defaults.RANGO_ESCENAS_POR_CAPITULO == (2, 4)

    def test_topes_de_la_investigacion(self) -> None:
        assert Defaults.WEBSEARCH_INVESTIGACION_INICIAL == 3
        assert Defaults.WEBFETCH_INVESTIGACION_INICIAL == 3
        assert Defaults.DIMENSIONES_DEL_PERIODO == 6
        assert Defaults.TECHO_WEBFETCH_TOKENS == 10_000
        assert Defaults.LONGITUD_MAXIMA_CITA == 300
        assert Defaults.HECHOS_POR_LOTE_VERIFICADOR == 20

    def test_topes_de_plotting_y_writing(self) -> None:
        assert Defaults.HUECOS_POR_PLOTTING == 5
        assert Defaults.WEBSEARCH_POR_HUECO == 1
        assert Defaults.REINTENTOS_POR_CAPITULO == 2
        assert Defaults.INVOCACIONES_EXTRACTOR_POR_CAPITULO == 3

    def test_exigencia_de_arco(self) -> None:
        assert Defaults.ESCENAS_PARA_EXIGIR_ARCO == 3
        assert Defaults.HITOS_MINIMOS_ARCO_CON_TRANSFORMACION == 2
        assert Defaults.HITOS_ARCO_PLANO == 0
        assert Defaults.AVISOS_QUE_VIAJAN_AL_SIGUIENTE == 3

    def test_embeddings_y_recuperacion(self) -> None:
        assert Defaults.MODELO_EMBEDDINGS == "paraphrase-multilingual-MiniLM-L12-v2"
        assert Defaults.DIMENSION_EMBEDDINGS == 384
        assert Defaults.K_VECINOS == 8

    def test_presupuesto_de_contexto(self) -> None:
        """El techo del sistema entero, del que cuelga §12."""
        assert Defaults.TOKENS_CONCURRENTES_MAXIMOS == 100_000
        assert Defaults.TECHO_TOTAL_PAQUETE == 12_000

    def test_diales_de_la_frontera(self) -> None:
        assert Defaults.GRADO_LICENCIA == "moderado"
        assert Defaults.ARCAISMO == "moderado"
        assert Defaults.CRITERIOS_RUBRICA == 7


class TestRol:
    """Los nueve roles de §5, que son el dominio de `modelo_por_rol`."""

    def test_son_nueve(self) -> None:
        assert len(list(Rol)) == 9

    def test_estan_los_que_declara_la_arquitectura(self) -> None:
        assert {r.value for r in Rol} == {
            "entrevistador",
            "extractor_intake",
            "investigador",
            "verificador",
            "arquitecto",
            "escritor",
            "editor",
            "extractor_capitulo",
            "juez",
        }


class TestSettings:
    def test_se_construye_sin_entorno(self) -> None:
        """Ninguna clave es obligatoria: las pruebas no necesitan un `.env`."""
        s = Settings(_env_file=None)
        assert s.directorio_proyectos.name == "proyectos"

    def test_los_limites_vienen_de_los_defaults(self) -> None:
        s = Settings(_env_file=None)
        assert s.reintentos_por_capitulo == Defaults.REINTENTOS_POR_CAPITULO
        assert s.huecos_por_plotting == Defaults.HUECOS_POR_PLOTTING
        assert s.k_vecinos == Defaults.K_VECINOS
        assert s.techo_webfetch_tokens == Defaults.TECHO_WEBFETCH_TOKENS

    def test_los_nueve_roles_arrancan_en_haiku(self) -> None:
        s = Settings(_env_file=None)
        assert set(s.modelo_por_rol) == set(Rol)
        assert set(s.modelo_por_rol.values()) == {Defaults.MODELO_HAIKU}

    def test_los_gates_estan_activos_por_defecto(self) -> None:
        """En interactivo se aprueba a mano; el modo batch los apaga (§10)."""
        s = Settings(_env_file=None)
        assert s.gates_enabled is True
        assert s.otlp_enabled is False

    def test_los_secretos_son_opcionales_y_nacen_vacios(self) -> None:
        s = Settings(_env_file=None)
        assert s.telegram_bot_token is None
        assert s.langfuse_public_key is None

    def test_el_entorno_manda_sobre_el_defecto(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STORYMAKER_GATES_ENABLED", "false")
        monkeypatch.setenv("STORYMAKER_K_VECINOS", "3")
        s = Settings(_env_file=None)
        assert s.gates_enabled is False
        assert s.k_vecinos == 3

    def test_se_puede_inyectar_una_configuracion_distinta(self, tmp_path: Path) -> None:
        """Lo que sostiene «quien necesita un valor lo recibe inyectado» de §2.2."""
        s = Settings(_env_file=None, directorio_proyectos=tmp_path, gates_enabled=False)
        assert s.directorio_proyectos == tmp_path
        assert s.gates_enabled is False

    def test_el_modo_batch_apaga_los_gates(self) -> None:
        s = Settings(_env_file=None).en_modo_batch()
        assert s.gates_enabled is False

    def test_un_limite_fuera_de_rango_no_se_acepta(self) -> None:
        """Un `k` de cero dejaría los bloques 2, 4 y 5 del paquete vacíos en silencio."""
        with pytest.raises(ValueError):
            Settings(_env_file=None, k_vecinos=0)
