"""spec: §2.3 · arq: §7, §16.2, §16.4

Abrir una novela. Es el único sitio del sistema que construye una conexión, y hace en
orden lo que §2.3 de la spec exige antes de aceptar trabajo: cargar `sqlite-vec`,
activar los `PRAGMA`, aplicar las migraciones pendientes y negarse a seguir si el
esquema del fichero es posterior al que este código conoce.

Una novela es un fichero, y el directorio es el registro: aquí no hay ninguna base de
datos global que consultar para saber qué novelas existen.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Final

import aiosqlite
import sqlite_vec

from storymaker.commons.errores import (
    EsquemaDelFuturo,
    NovelaNoEncontrada,
    SqliteVecNoDisponible,
)

VERSION_ESQUEMA: Final = 1

#: El orden importa: `arnes` primero porque casi todo referencia `fase_run`, y los
#: triggers al final, cuando ya existen las tablas que vigilan.
FICHEROS_DEL_ESQUEMA: Final = (
    "arnes.sql",
    "intake.sql",
    "mundo.sql",
    "canon.sql",
    "plan.sql",
    "texto.sql",
    "cronologia.sql",
    "vec.sql",
    "inmutabilidad.sql",
)

_DIRECTORIO_ESQUEMA: Final = Path(__file__).parent / "esquema"

#: Columnas añadidas después de crear su tabla, que son **aditivas y admiten nulos**: se
#: añaden en cada apertura si faltan, sin subir `VERSION_ESQUEMA`. Subirla haría que un
#: proceso con el código anterior se negara a abrir la novela en cuanto el nuevo la tocara,
#: y una columna que nadie antiguo lee no justifica eso (arq. §7).
COLUMNAS_ADITIVAS: Final = (
    (
        "mundo_hecho",
        "sin_respaldo",
        "TEXT CHECK (sin_respaldo IS NULL OR length(sin_respaldo) <= 300)",
    ),
    ("canon_obra", "fase_run_id", "INTEGER REFERENCES fase_run(id)"),
)

#: Tablas añadidas después de la primera versión del esquema, con la misma regla que las
#: columnas aditivas: nadie antiguo las lee, así que se crean al abrir si faltan.
TABLAS_ADITIVAS: Final = (
    (
        "plan_hueco",
        """
        CREATE TABLE IF NOT EXISTS plan_hueco (
          id        INTEGER PRIMARY KEY,
          escena_id INTEGER REFERENCES plan_escena(id),
          pregunta  TEXT    NOT NULL,
          dimension TEXT    NOT NULL,
          propuesta TEXT,
          hecho_id  INTEGER REFERENCES mundo_hecho(id),
          resultado TEXT    CHECK (resultado IS NULL OR resultado IN ('encontrado','inventado'))
        ) STRICT
        """,
    ),
)


async def _activar_extension(db: aiosqlite.Connection) -> None:
    try:
        # Se carga por SQL y no por la API privada de aiosqlite: `loadable_path()` da la
        # ruta de la biblioteca nativa y `load_extension` la abre en el hilo correcto.
        await db.enable_load_extension(True)
        await db.execute("SELECT load_extension(?)", (sqlite_vec.loadable_path(),))
        await db.enable_load_extension(False)
        async with db.execute("SELECT vec_version()") as cursor:
            await cursor.fetchone()
    except Exception as exc:
        raise SqliteVecNoDisponible(
            "No se pudo cargar la extension sqlite-vec en este interprete de Python. "
            "El arranque se detiene en lugar de seguir sin busqueda semantica: un "
            "ensamblador que no puede buscar produciria paquetes de contexto "
            "empobrecidos sin que nadie se enterase (U-15)."
        ) from exc


async def _activar_pragmas(db: aiosqlite.Connection) -> None:
    """WAL para que leer no bloquee escribir, claves foráneas y `synchronous=NORMAL`.

    Se activan antes de migrar y no después, porque el esquema se aplica bajo las mismas
    reglas con las que luego se escribe: una migración con las claves foráneas apagadas
    podría dejar el fichero en un estado que la aplicación ya no admitiría.
    """
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.execute("PRAGMA synchronous=NORMAL")


async def _version_del_esquema(db: aiosqlite.Connection) -> int:
    async with db.execute("PRAGMA user_version") as cursor:
        fila = await cursor.fetchone()
    return int(fila[0]) if fila is not None else 0


async def _migrar(db: aiosqlite.Connection, ruta: Path) -> None:
    version = await _version_del_esquema(db)
    if version > VERSION_ESQUEMA:
        raise EsquemaDelFuturo(
            f"La novela {ruta.name} tiene el esquema en version {version} y este codigo "
            f"conoce hasta la {VERSION_ESQUEMA}. Nunca se abre una novela con un esquema "
            f"del futuro: migrar hacia atras no esta definido."
        )
    if version == VERSION_ESQUEMA:
        return

    for fichero in FICHEROS_DEL_ESQUEMA:
        await db.executescript((_DIRECTORIO_ESQUEMA / fichero).read_text(encoding="utf-8"))
    # `executescript` cierra la transacción abierta, así que la versión se fija después
    # y con su propio commit: si algo falla a mitad, el fichero queda en versión 0 y la
    # próxima apertura vuelve a aplicarlo entero.
    await db.execute(f"PRAGMA user_version={VERSION_ESQUEMA}")
    await db.commit()


async def _anadir_columnas(db: aiosqlite.Connection) -> None:
    """Añade las tablas y columnas aditivas que le falten al fichero, sin tocar sus filas."""
    for tabla, ddl in TABLAS_ADITIVAS:
        async with db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (tabla,)
        ) as cursor:
            existe = await cursor.fetchone()
        if existe is None:
            await db.execute(ddl)
            await db.commit()
    for tabla, columna, definicion in COLUMNAS_ADITIVAS:
        async with db.execute(f"PRAGMA table_info({tabla})") as cursor:
            existentes = {str(fila["name"]) for fila in await cursor.fetchall()}
        # Una tabla que no existe no gana columnas: la creará el esquema, ya con ellas.
        if existentes and columna not in existentes:
            await db.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
            await db.commit()


@asynccontextmanager
async def abrir_novela(ruta: Path, *, crear: bool = False) -> AsyncIterator[aiosqlite.Connection]:
    """Abre el fichero de una novela dejándolo listo para trabajar.

    `crear=False` sobre un fichero que no existe es `NovelaNoEncontrada` y no un fichero
    vacío recién hecho: equivocarse de nombre no puede tener como consecuencia una novela
    nueva que nadie pidió.
    """
    if not crear and not ruta.exists():
        raise NovelaNoEncontrada(f"No hay ninguna novela en {ruta}")
    if crear:
        ruta.parent.mkdir(parents=True, exist_ok=True)

    # `isolation_level=None` desactiva las transacciones implícitas de Python. No es un
    # detalle: es lo que hace que `paso_atomico` sea el **único** dueño de la transacción.
    # Con el modo por defecto, el propio driver abriría una por su cuenta al primer INSERT
    # y el `BEGIN IMMEDIATE` del envoltorio chocaría contra ella, de modo que el nodo
    # acabaría escribiendo dentro de una transacción que nadie declaró.
    db = await aiosqlite.connect(ruta, isolation_level=None)
    db.row_factory = aiosqlite.Row
    try:
        await _activar_extension(db)
        await _activar_pragmas(db)
        await _migrar(db, ruta)
        await _anadir_columnas(db)
        yield db
    finally:
        await db.close()


async def crear_novela(ruta: Path) -> None:
    """Escribe el fichero de una novela con el esquema aplicado y nada dentro."""
    async with abrir_novela(ruta, crear=True):
        pass


def ruta_de_novela(nombre: str, directorio: Path) -> Path:
    """`proyectos/<nombre>/<nombre>.db`: **una carpeta por novela** (arq. §16.4).

    La novela sigue siendo un solo fichero; la carpeta guarda junto a él lo que se deriva
    de él —cerrojo, ficheros de trabajo de SQLite, PDF, capítulos exportados— para que
    varias novelas no se mezclen en un mismo directorio. El `name` final no es paranoia: el
    nombre llega por la URL o por la CLI, y sin él `../../algo` saldría del registro.
    """
    limpio = Path(nombre).name.removesuffix(".db")
    return directorio / limpio / f"{limpio}.db"


def novelas_en(directorio: Path) -> list[Path]:
    """Las novelas del registro: las carpetas que contienen su propio fichero."""
    if not directorio.exists():
        return []
    return sorted(p for p in directorio.glob("*/*.db") if p.stem == p.parent.name)
