"""spec: §5, §8 · arq: §16.4

Pruebas de la API.

Lo que importa comprobar aquí no son los cuerpos JSON sino **la separación de superficies**:
que el webhook —el único que reanuda una ejecución— rechaza sin secreto, que la lectura no
lo pide, y que una decisión malformada **no reanuda el grafo**. Esa última es la que
Schemathesis amplía después con entradas generadas; aquí se fija a mano el caso que importa.

La otra mitad es la traducción de errores: que `NovelaOcupada` sea `409` en todas las rutas
y no `500` en unas y `409` en otras, porque si cada endpoint decidiera su código la API
dejaría de tener contrato.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from storymaker.api.app import crear_app
from storymaker.api.manejadores import codigo_de
from storymaker.api.novelas import ruta_de
from storymaker.api.webhook import secreto_valido
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import crear_novela
from storymaker.commons.errores import (
    ErrorDeEntorno,
    EscaletaAusente,
    NovelaNoEncontrada,
    NovelaOcupada,
)


@pytest.fixture
def ajustes(tmp_path: Path) -> Settings:
    directorio = tmp_path / "proyectos"
    directorio.mkdir()
    return Settings(
        _env_file=None,
        directorio_proyectos=directorio,
        telegram_secret_token="secreto-de-prueba",  # noqa: S106
    )


@pytest.fixture
def cliente(ajustes: Settings) -> Any:
    return TestClient(crear_app(ajustes))


class TestSuperficies:
    def test_la_salud_no_abre_ninguna_novela(self, cliente: Any) -> None:
        assert cliente.get("/salud").json() == {"estado": "vivo"}

    def test_la_lectura_no_pide_secreto(self, cliente: Any) -> None:
        """Es una decision declarada, no un olvido: queda como U-17."""
        assert cliente.get("/novelas").status_code == 200

    def test_el_webhook_rechaza_sin_secreto(self, cliente: Any) -> None:
        respuesta = cliente.post("/webhook/telegram", json={})
        assert respuesta.status_code == 401

    def test_el_webhook_rechaza_con_secreto_equivocado(self, cliente: Any) -> None:
        respuesta = cliente.post(
            "/webhook/telegram",
            json={},
            headers={"X-Telegram-Bot-Api-Secret-Token": "otro"},
        )
        assert respuesta.status_code == 401


class TestSecreto:
    def test_sin_secreto_configurado_no_se_acepta_nada(self) -> None:
        """Un despliegue sin secreto no es abierto: es un despliegue mal configurado."""
        sin_secreto = Settings(_env_file=None)
        assert secreto_valido(None, sin_secreto) is False
        assert secreto_valido("lo-que-sea", sin_secreto) is False

    def test_con_secreto_solo_pasa_el_correcto(self, ajustes: Settings) -> None:
        assert secreto_valido("secreto-de-prueba", ajustes) is True
        assert secreto_valido("secreto-de-pruebaX", ajustes) is False


class TestListado:
    async def test_lista_el_directorio(self, ajustes: Settings, cliente: Any) -> None:
        """No hay registro global: listar las novelas es listar el directorio."""
        await crear_novela(ajustes.directorio_proyectos / "una.db")
        await crear_novela(ajustes.directorio_proyectos / "otra.db")
        cuerpo = cliente.get("/novelas").json()
        assert {n["nombre"] for n in cuerpo} == {"una", "otra"}

    def test_una_novela_que_no_existe_es_404(self, cliente: Any) -> None:
        assert cliente.get("/novelas/fantasma").status_code == 404


class TestRutas:
    def test_el_nombre_no_puede_salirse_del_directorio(self, ajustes: Settings) -> None:
        """El nombre llega por la URL: sin esto, `../../algo` abriria ficheros de fuera."""
        ruta = ruta_de("../../secreto", ajustes)
        assert ruta.parent == ajustes.directorio_proyectos
        assert ".." not in ruta.name

    def test_se_le_pone_la_extension(self, ajustes: Settings) -> None:
        assert ruta_de("novela-1", ajustes).name == "novela-1.db"


class TestTraduccionDeErrores:
    @pytest.mark.parametrize(
        ("error", "esperado"),
        [
            (NovelaNoEncontrada("x"), 404),
            (NovelaOcupada("x"), 409),
            (EscaletaAusente("x"), 422),
            (ErrorDeEntorno("x"), 503),
        ],
    )
    def test_cada_error_tiene_su_codigo(self, error: Exception, esperado: int) -> None:
        codigo, _ = codigo_de(error)
        assert codigo == esperado

    def test_lo_desconocido_es_500_y_no_culpa_al_cliente(self) -> None:
        """Un error que nadie previo no se disfraza de error del cliente."""
        codigo, _ = codigo_de(RuntimeError("algo raro"))
        assert codigo == 500

    def test_el_mensaje_de_novela_ocupada_explica_por_que(self) -> None:
        _, mensaje = codigo_de(NovelaOcupada("x"))
        assert "rechazado, no encolado" in mensaje
