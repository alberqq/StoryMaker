"""spec: §5 · arq: §16.4

**Una novela es un fichero, y el directorio es el registro.**

No hay una base de datos global de novelas, y no la va a haber: si el registro viviera fuera
del fichero, copiarlo dejaría de ser ramificar y descargar una novela dejaría de ser
copiarla, que son las dos propiedades de las que cuelga aquella decisión.

Listar las novelas es listar el directorio, y los datos que la lista enseña —título, fase en
curso, número de versiones— se leen abriendo cada fichero. El precio es que listar cuesta
tantas aperturas como novelas haya; con las decenas que este sistema contempla es
instantáneo, y no aspira a miles.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela
from storymaker.commons.db.repos import canon
from storymaker.commons.errores import NovelaNoEncontrada
from storymaker.commons.graph import cerrojo


@dataclass(frozen=True)
class FichaDeNovela:
    """Lo que la lista enseña de cada novela."""

    nombre: str
    titulo: str
    fase: str
    versiones: int
    gate_abierto: int | None = None
    ocupada: bool = False


def ruta_de(nombre: str, settings: Settings) -> Path:
    """La ruta de una novela por su nombre, sin salirse del directorio.

    El `name` final no es paranoia: el nombre llega por la URL, y sin esto `../../algo`
    abriría ficheros de fuera del registro.
    """
    limpio = Path(nombre).name
    if not limpio.endswith(".db"):
        limpio = f"{limpio}.db"
    return settings.directorio_proyectos / limpio


def listar_ficheros(settings: Settings) -> list[Path]:
    directorio = settings.directorio_proyectos
    if not directorio.exists():
        return []
    return sorted(p for p in directorio.glob("*.db") if not p.name.endswith(".lock"))


async def ficha(ruta: Path) -> FichaDeNovela:
    """Abre el fichero y lee lo justo para la lista."""
    async with abrir_novela(ruta) as db:
        obra = await canon.obra(db)
        async with db.execute("SELECT COUNT(*) AS n FROM version_novela") as cursor:
            fila = await cursor.fetchone()
        versiones = int(fila["n"]) if fila is not None else 0
        async with db.execute(
            "SELECT fase FROM fase_run ORDER BY id DESC LIMIT 1"
        ) as cursor:
            ultima = await cursor.fetchone()
        async with db.execute(
            "SELECT id FROM gate WHERE estado = 'pendiente' ORDER BY id DESC LIMIT 1"
        ) as cursor:
            gate = await cursor.fetchone()

    return FichaDeNovela(
        nombre=ruta.stem,
        titulo=str(obra["titulo"]) if obra is not None and obra["titulo"] else ruta.stem,
        fase=str(ultima["fase"]) if ultima is not None else "sin empezar",
        versiones=versiones,
        gate_abierto=int(gate["id"]) if gate is not None else None,
        ocupada=cerrojo.esta_tomado(ruta),
    )


async def listar(settings: Settings) -> list[FichaDeNovela]:
    return [await ficha(ruta) for ruta in listar_ficheros(settings)]


async def exigir(nombre: str, settings: Settings) -> Path:
    ruta = ruta_de(nombre, settings)
    if not ruta.exists():
        raise NovelaNoEncontrada(f"No hay ninguna novela llamada {nombre}")
    return ruta
