"""spec: §5, §8 · arq: §16.4

Pruebas de la API.

Lo que importa comprobar aquí no son los cuerpos JSON sino **la separación de superficies**:
que **ningún endpoint reanuda una ejecución** —los gates se deciden con la CLI— y que la
lectura queda abierta por decisión declarada (U-17).

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
    )


@pytest.fixture
def cliente(ajustes: Settings) -> Any:
    return TestClient(crear_app(ajustes))


class TestSuperficies:
    def test_la_salud_no_abre_ninguna_novela(self, cliente: Any) -> None:
        assert cliente.get("/salud").json() == {"estado": "vivo"}

    def test_la_lectura_no_pide_secreto(self, cliente: Any) -> None:
        """Es una decision declarada, no un olvido: queda como U-17."""
        assert cliente.get("/api/novelas").status_code == 200

    def test_ningun_endpoint_reanuda_una_ejecucion(self, cliente: Any) -> None:
        """Telegram solo avisa: el webhook que reanudaba se retiro con su secreto."""
        assert cliente.post("/webhook/telegram", json={}).status_code == 404
        rutas = {getattr(r, "path", "") for r in cliente.app.routes}
        assert not any("webhook" in r or "gate" in r for r in rutas)


class TestListado:
    async def test_lista_el_directorio(self, ajustes: Settings, cliente: Any) -> None:
        """No hay registro global: listar las novelas es listar sus carpetas."""
        await crear_novela(ruta_de("una", ajustes))
        await crear_novela(ruta_de("otra", ajustes))
        # Lo que no es la carpeta de una novela no es una novela.
        (ajustes.directorio_proyectos / "suelta.db").write_bytes(b"")
        cuerpo = cliente.get("/api/novelas").json()
        assert {n["nombre"] for n in cuerpo} == {"una", "otra"}

    def test_una_novela_que_no_existe_es_404(self, cliente: Any) -> None:
        assert cliente.get("/api/novelas/fantasma").status_code == 404


class TestRutas:
    def test_el_nombre_no_puede_salirse_del_directorio(self, ajustes: Settings) -> None:
        """El nombre llega por la URL: sin esto, `../../algo` abriria ficheros de fuera."""
        ruta = ruta_de("../../secreto", ajustes)
        assert ruta.parent.parent == ajustes.directorio_proyectos
        assert ".." not in ruta.parts

    def test_cada_novela_tiene_su_carpeta(self, ajustes: Settings) -> None:
        ruta = ruta_de("novela-1.db", ajustes)
        assert ruta == ajustes.directorio_proyectos / "novela-1" / "novela-1.db"


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


class TestLectura:
    """La superficie que el frontend consume, contra una novela publicada dos veces."""

    @pytest.fixture
    async def publicada(self, ajustes: Settings) -> str:
        from dobles.novela_de_lectura import sembrar

        await sembrar(ruta_de("mar", ajustes))
        return "mar"

    def test_la_ficha_trae_el_historial(self, publicada: str, cliente: Any) -> None:
        cuerpo = cliente.get(f"/api/novelas/{publicada}").json()
        assert [v["numero"] for v in cuerpo["historial"]] == [1, 2]
        assert cuerpo["historial"][0]["puntuacion"] is None

    def test_la_version_trae_su_paratexto(self, publicada: str, cliente: Any) -> None:
        cuerpo = cliente.get(f"/api/novelas/{publicada}/versiones/2").json()
        assert cuerpo["anterior"] == 1
        assert [c["titulo"] for c in cuerpo["capitulos"]] == ["Titulo 1", "Titulo 2", "Titulo 3"]
        paratexto = cuerpo["paratexto"]
        assert paratexto["titulo"] == "La mar de Cadiz"
        assert paratexto["homenajeado"] == "Elvira Ponce"
        assert paratexto["ocasion"] == "jubilacion"
        assert len(paratexto["licencias"]) == 1

    def test_la_primera_version_no_tiene_anterior(self, publicada: str, cliente: Any) -> None:
        assert cliente.get(f"/api/novelas/{publicada}/versiones/1").json()["anterior"] is None

    def test_el_capitulo_es_el_de_esa_version(self, publicada: str, cliente: Any) -> None:
        v1 = cliente.get(f"/api/novelas/{publicada}/versiones/1/capitulos/2").json()
        v2 = cliente.get(f"/api/novelas/{publicada}/versiones/2/capitulos/2").json()
        assert v1["texto"] != v2["texto"]
        assert v2["total"] == 3 and v2["titulo"] == "Titulo 2"

    def test_capitulo_fuera_del_manifiesto_es_404(self, publicada: str, cliente: Any) -> None:
        assert cliente.get(f"/api/novelas/{publicada}/versiones/1/capitulos/9").status_code == 404

    def test_la_ficha_de_personajes_cuelga_de_una_version(
        self, publicada: str, cliente: Any
    ) -> None:
        cuerpo = cliente.get(f"/api/novelas/{publicada}/versiones/2/personajes").json()
        por_nombre = {p["nombre"]: p for p in cuerpo["personajes"]}
        assert por_nombre["Elvira Ponce"]["es_homenajeado"]
        assert por_nombre["Elvira Ponce"]["capitulos"] == [1, 2, 3]
        assert por_nombre["Tomas Ruiz"]["relacion_con_homenajeado"] == "hermano"
        # Una ficha sin escenas se sirve igual, sin capitulos: no se oculta.
        assert por_nombre["Sin Escena"]["capitulos"] == []
        assert cuerpo["escenarios"][0]["lugar_de_epoca"] == "Cadiz de las Cortes"
        assert cliente.get(f"/api/novelas/{publicada}/versiones/7/personajes").status_code == 404

    def test_el_diff_dice_que_cambia(self, publicada: str, cliente: Any) -> None:
        cuerpo = cliente.get(f"/api/novelas/{publicada}/versiones/1/diff/2").json()
        assert [c["capitulo"] for c in cuerpo["cambios"]] == [2]

    def test_una_peticion_sin_texto_no_abre_la_fase_6(self, publicada: str, cliente: Any) -> None:
        assert cliente.post(f"/api/novelas/{publicada}/cambios", json={}).status_code == 422


class TestFrontendServido:
    """FastAPI sirve el `dist/`: un solo origen para lector, PDF y `render_visual`."""

    @pytest.fixture
    def con_dist(self, ajustes: Settings, tmp_path: Path) -> Any:
        dist = tmp_path / "dist"
        (dist / "assets").mkdir(parents=True)
        (dist / "index.html").write_text("<div id=root></div>", encoding="utf-8")
        (dist / "assets" / "app.js").write_text("//js", encoding="utf-8")
        return TestClient(crear_app(ajustes.model_copy(update={"frontend_dist": dist})))

    def test_una_ruta_de_la_aplicacion_sirve_index(self, con_dist: Any) -> None:
        respuesta = con_dist.get("/novelas/mar/v/2/capitulos/1")
        assert respuesta.status_code == 200 and "root" in respuesta.text

    def test_los_estaticos_se_sirven_tal_cual(self, con_dist: Any) -> None:
        assert con_dist.get("/assets/app.js").text == "//js"

    def test_la_api_no_cae_en_la_aplicacion(self, con_dist: Any) -> None:
        respuesta = con_dist.get("/api/no-existe")
        assert respuesta.status_code == 404 and "root" not in respuesta.text

    def test_un_post_desconocido_sigue_siendo_404(self, con_dist: Any) -> None:
        assert con_dist.post("/webhook/telegram", json={}).status_code == 404

    def test_sin_dist_el_servidor_levanta(self, cliente: Any, ajustes: Settings) -> None:
        sin = TestClient(crear_app(ajustes.model_copy(update={"frontend_dist": Path("no-existe")})))
        assert sin.get("/salud").status_code == 200
        assert sin.get("/novelas/x").status_code == 404


class TestNombreCortoDeEscenario:
    """El título de un lugar es corto aunque el arquitecto solo escribiera una descripción."""

    @pytest.mark.parametrize(
        ("descripcion", "esperado"),
        [
            ("Taller de imprenta con máquinas de prensa, cajas de tipos", "Taller de imprenta"),
            ("Casa modesta llena de mapas del padre en rollos", "Casa modesta"),
            ("Edificio oficial, pasillos serios", "Edificio oficial"),
            (
                "Zona de preparación de la armada en agosto de 1519. Carabelas",
                "Zona de preparación de la armada…",
            ),
            ("calles transformadas por la corte de Carlos I", "Calles transformadas por la corte…"),
        ],
    )
    def test_el_arranque_de_la_descripcion(self, descripcion: str, esperado: str) -> None:
        from storymaker.api.lectura import nombre_corto

        assert nombre_corto(descripcion) == esperado

    def test_el_lugar_del_corpus_manda(self) -> None:
        from storymaker.api.lectura import nombre_de_escenario

        assert nombre_de_escenario(1, "Cádiz", "Una descripción larguísima") == "Cádiz"
        assert nombre_de_escenario(3, None, None) == "Escenario 3"


class TestPdf:
    async def test_el_pdf_de_una_version_se_descarga(self, ajustes: Settings, cliente: Any) -> None:
        from dobles.novela_de_lectura import sembrar

        ruta = ruta_de("mar", ajustes)
        await sembrar(ruta)
        ruta.with_suffix(".v1.pdf").write_bytes(b"%PDF-1.4 falso")
        respuesta = cliente.get("/api/novelas/mar/versiones/1/pdf")
        assert respuesta.status_code == 200
        assert respuesta.headers["content-type"] == "application/pdf"
        assert respuesta.content.startswith(b"%PDF")
        assert cliente.get("/api/novelas/mar/versiones/2/pdf").status_code == 404
