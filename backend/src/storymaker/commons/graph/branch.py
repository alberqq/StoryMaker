"""spec: §6 · arq: §8

**Ramificar es copiar el fichero.** `novela-7.db` → `novela-7b.db`, una fila en
`procedencia` con el fichero y la ejecución de origen, y se continúa desde ahí.

La alternativa —ramas conviviendo en un mismo fichero con una columna de rama— obligaría a
meter un filtro en **todas** las consultas del sistema: el índice hecho→capítulo, la
continuidad, los manifiestos, la generación de Lean. Bastaría con que una lo olvidara para
que la rama B leyese capítulos de la rama A, y ese fallo no se ve hasta que alguien lee la
novela.

El coste es unos cientos de kilobytes de corpus duplicado, y se conserva una propiedad
cómoda: una novela es un fichero, y descargarla es copiarlo.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from storymaker.commons.db.apertura import abrir_novela
from storymaker.commons.errores import NovelaNoEncontrada, NovelaOcupada
from storymaker.commons.graph import cerrojo
from storymaker.commons.graph.estado import EstadoNovela


async def fork(estado: EstadoNovela) -> EstadoNovela:
    """El nodo `Branch` del grafo. Termina la invocación: la rama sigue por su lado."""
    return estado


async def ramificar(origen: Path, destino: Path, *, fase_run_id: int | None = None) -> Path:
    """Copia la novela y deja escrita su procedencia.

    Se copia con el cerrojo del origen tomado, porque copiar un fichero SQLite mientras
    alguien escribe en él produce una novela hija con media transacción dentro. Y el
    destino no puede existir: sobrescribir una novela por equivocarse de nombre sería el
    borrado más caro de este sistema.
    """
    if not origen.exists():
        raise NovelaNoEncontrada(f"No hay ninguna novela en {origen}")
    if destino.exists():
        raise NovelaOcupada(f"Ya existe una novela en {destino}: ramificar no sobrescribe")

    with cerrojo.tomar(origen):
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, destino)

    async with abrir_novela(destino) as db:
        await db.execute(
            "INSERT INTO procedencia (origen_db, origen_fase_run_id) VALUES (?, ?)",
            (origen.name, fase_run_id),
        )
        await db.commit()

    return destino
