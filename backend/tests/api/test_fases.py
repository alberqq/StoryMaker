"""spec: §5.2 · arq: §16.5

La salida de cada fase, el texto de un intento y el final de un registro.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from dobles.novela_de_lectura import sembrar
from fastapi.testclient import TestClient

from storymaker.api.app import crear_app
from storymaker.api.novelas import ruta_de
from storymaker.commons.config import Settings


@pytest.fixture
def ajustes(tmp_path: Path) -> Settings:
    directorio = tmp_path / "proyectos"
    directorio.mkdir()
    return Settings(_env_file=None, directorio_proyectos=directorio)


@pytest.fixture
def cliente(ajustes: Settings) -> Any:
    return TestClient(crear_app(ajustes))


@pytest.fixture
async def publicada(ajustes: Settings) -> Path:
    ruta = ruta_de("mar", ajustes)
    await sembrar(ruta)
    return ruta


def test_la_trama_trae_canon_y_escaleta(publicada: Path, cliente: Any) -> None:
    salida = cliente.get("/api/novelas/mar/fases/trama").json()
    trama = salida["trama"]
    assert trama["obra"]["titulo"] == "La mar de Cadiz"
    assert [p["nombre"] for p in trama["personajes"]][:2] == ["Elvira Ponce", "Tomas Ruiz"]
    assert trama["personajes"][0]["es_homenajeado"]
    assert trama["relaciones"][0]["tipo"] == "hermano"
    assert [c["numero"] for c in trama["escaleta"]] == [1, 2, 3]
    assert trama["escaleta"][1]["escenas"][0]["personajes"] == ["Elvira Ponce", "Tomas Ruiz"]
    assert trama["licencias"][0]["declarada"]


def test_la_escritura_trae_los_intentos(publicada: Path, cliente: Any) -> None:
    escritura = cliente.get("/api/novelas/mar/fases/escritura").json()["escritura"]
    segundo = escritura["capitulos"][1]
    assert len(segundo["intentos"]) == 2
    intento = segundo["intentos"][1]
    texto = cliente.get(f"/api/novelas/mar/intentos/{intento['id']}").json()
    assert texto["capitulo"] == 2 and "regenerado" in texto["texto"]


def test_la_publicacion_trae_las_versiones(publicada: Path, cliente: Any) -> None:
    publicacion = cliente.get("/api/novelas/mar/fases/publicacion").json()["publicacion"]
    assert [v["numero"] for v in publicacion["versiones"]] == [1, 2]
    assert publicacion["versiones"][1]["capitulos"] == 3


def test_el_encargo_trae_el_brief(publicada: Path, cliente: Any) -> None:
    salida = cliente.get("/api/novelas/mar/fases/encargo").json()
    assert salida["encargo"]["brief"]["ocasion"] == "jubilacion"
    assert salida["ejecuciones"] == []


def test_la_investigacion_vacia_no_es_un_error(publicada: Path, cliente: Any) -> None:
    investigacion = cliente.get("/api/novelas/mar/fases/investigacion").json()["investigacion"]
    assert investigacion["hechos"] == [] and investigacion["sello"] is None


def test_una_fase_desconocida_es_404(publicada: Path, cliente: Any) -> None:
    assert cliente.get("/api/novelas/mar/fases/cocina").status_code == 404


def test_el_registro_se_lee_y_no_se_sale_de_su_carpeta(publicada: Path, cliente: Any) -> None:
    registros = publicada.parent / "registro"
    registros.mkdir()
    (registros / "20260924-100000-continuar.log").write_bytes(b"hola\nadios\n")
    assert cliente.get("/api/novelas/mar/registros/20260924-100000-continuar.log").text.endswith(
        "adios\n"
    )
    assert cliente.get("/api/novelas/mar/registros/..%2F..%2Fmar.db").status_code == 404
