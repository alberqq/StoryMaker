"""spec: §4.5 · arq: §16.1

El PDF sale de la ruta de impresión del frontend, tras confirmar la invocación.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from dobles.novela_de_lectura import sembrar

from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import ruta_de_novela
from storymaker.publication import render


@pytest.fixture
async def novela(tmp_path: Path) -> tuple[Path, Settings]:
    directorio = tmp_path / "proyectos"
    ruta = ruta_de_novela("mar", directorio)
    await sembrar(ruta)
    return ruta, Settings(_env_file=None, directorio_proyectos=directorio)


async def test_sin_frontend_cae_al_html_minimo(
    novela: tuple[Path, Settings], monkeypatch: Any, tmp_path: Path
) -> None:
    ruta, settings = novela
    sin_dist = settings.model_copy(update={"frontend_dist": tmp_path / "no-existe"})
    impresos: list[str] = []

    async def falso(html: str, destino: str) -> None:
        impresos.append(destino)
        Path(destino).write_bytes(b"%PDF-minimo")

    monkeypatch.setattr(render, "imprimir_pdf", falso)
    hechos = await render.imprimir_pendientes(ruta, sin_dist)
    assert [p.name for p in hechos] == ["mar.v1.pdf", "mar.v2.pdf"]
    assert len(impresos) == 2


async def test_solo_imprime_lo_que_falta(novela: tuple[Path, Settings], monkeypatch: Any) -> None:
    ruta, settings = novela
    ruta.with_suffix(".v1.pdf").write_bytes(b"%PDF-ya")
    pedidos: list[int] = []

    async def falso(novela: Path, numero: int, destino: Path, settings: Settings) -> None:
        pedidos.append(numero)
        destino.write_bytes(b"%PDF")

    monkeypatch.setattr(render, "imprimir_version", falso)
    await render.imprimir_pendientes(ruta, settings)
    assert pedidos == [2]
    await render.imprimir_pendientes(ruta, settings, rehacer=True)
    assert pedidos == [2, 1, 2]


async def test_imprime_la_ruta_del_frontend(novela: tuple[Path, Settings]) -> None:
    """De verdad: Playwright abre `/imprimir` y el propio proceso le sirve estáticos y API."""
    ruta, settings = novela
    dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    settings = settings.model_copy(update={"frontend_dist": dist})
    if not (settings.frontend_dist / "index.html").is_file():
        pytest.skip("no hay frontend construido")
    pytest.importorskip("playwright")
    destino = ruta.with_suffix(".v2.pdf")
    try:
        await render.imprimir_version(ruta, 2, destino, settings)
    except Exception as fallo:  # un navegador ausente es entorno, no la prueba
        if "Executable doesn't exist" in str(fallo):
            pytest.skip("Chromium de Playwright no instalado")
        raise
    contenido = destino.read_bytes()
    assert contenido.startswith(b"%PDF")
    assert len(contenido) > 20_000  # con fuentes y maqueta, no una página vacía
