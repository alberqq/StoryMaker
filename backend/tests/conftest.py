"""spec: §7.1 · arq: §16.4

Andamiaje común de la suite: una configuración inyectable, un directorio de novelas
temporal y el doble del Agent SDK.

Todas las pruebas construyen su propio `Settings` en lugar de leer el entorno del
proceso. Es lo que hace que la suite corra igual en el portátil del Autor y en CI,
donde no hay ni `.env` ni credenciales.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import aiosqlite
import pytest
from dobles.agente_falso import AgenteFalso

from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela
from storymaker.commons.db.repos.arnes import abrir_fase_run


@pytest.fixture
def directorio_proyectos(tmp_path: Path) -> Path:
    """El registro de novelas, que es un directorio y no una base de datos (§16.4)."""
    d = tmp_path / "proyectos"
    d.mkdir()
    return d


@pytest.fixture
def settings(directorio_proyectos: Path) -> Settings:
    """Configuración de prueba: sin gates, para que nada se quede esperando al Autor."""
    return Settings(
        _env_file=None,
        directorio_proyectos=directorio_proyectos,
        gates_enabled=False,
    )


@pytest.fixture
def agente_falso() -> AgenteFalso:
    return AgenteFalso()

@pytest.fixture
async def db(tmp_path: Path) -> AsyncIterator[aiosqlite.Connection]:
    """Una novela recién creada: esquema aplicado, `sqlite-vec` cargado y nada dentro."""
    async with abrir_novela(tmp_path / "novela.db", crear=True) as conexion:
        yield conexion


@pytest.fixture
async def fase_run(db: aiosqlite.Connection) -> int:
    """Una ejecución de fase abierta, porque casi todas las tablas cuelgan de una."""
    identificador = await abrir_fase_run(db, "investigation")
    await db.commit()
    return identificador
