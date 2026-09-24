"""spec: §5.3 · arq: §16.5

**Lo que ejecuta el grafo no lo ejecuta la API: lanza la CLI como proceso aparte.**

Encargar, continuar, decidir y reintentar son comandos de `storymaker`, y la interfaz los
lanza exactamente como los teclearía el Autor. De ahí salen las tres propiedades de §16.5:
un solo camino de código, un servidor que no guarda nada en memoria —reiniciarlo no mata
ninguna ejecución, porque el proceso no es suyo— y ninguna cola.

El proceso se crea en su propio grupo, desacoplado del servidor, con el mismo intérprete y
el mismo directorio de proyectos. Su salida va a un registro dentro de la carpeta de la
novela, que el panel puede consultar; el servidor no se queda con ningún identificador.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from storymaker.commons.config import Settings

#: La carpeta de registros de proceso dentro de la de cada novela.
CARPETA_DE_REGISTROS = "registro"

#: El backend, que es el directorio desde el que la CLI lee su `.env`.
_BACKEND = Path(__file__).resolve().parents[3]


def carpeta_de_registros(carpeta_novela: Path) -> Path:
    return carpeta_novela / CARPETA_DE_REGISTROS


def lanzar(carpeta_novela: Path, argumentos: list[str], settings: Settings) -> str:
    """Lanza `python -m storymaker <argumentos>` y devuelve el nombre de su registro.

    No espera a que termine ni se queda con el proceso: el seguimiento lee el fichero de la
    novela, y el cerrojo que la CLI toma es lo que dice que está en marcha.
    """
    registros = carpeta_de_registros(carpeta_novela)
    registros.mkdir(parents=True, exist_ok=True)
    momento = datetime.now().strftime("%Y%m%d-%H%M%S")
    nombre = f"{momento}-{argumentos[0]}.log"
    registro = registros / nombre

    entorno = {
        **os.environ,
        "STORYMAKER_DIRECTORIO_PROYECTOS": str(settings.directorio_proyectos.resolve()),
        # La salida va a un fichero: en Windows, sin esto, se escribe en cp1252 y la
        # primera raya o flecha de un mensaje tumba el proceso.
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "NO_COLOR": "1",
    }
    opciones: dict[str, object] = {}
    if os.name == "nt":
        # Una consola oculta, y no ninguna: un proceso sin consola (`DETACHED_PROCESS`) hace
        # que Windows abra una ventana visible a cada proceso de consola que él lance —la CLI
        # de Claude del Agent SDK, `lake`, Playwright—. Con una oculta, la heredan todos.
        opciones["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        )
    else:
        opciones["start_new_session"] = True

    with registro.open("ab") as salida:
        subprocess.Popen(  # noqa: S603 — argumentos propios, sin shell
            [sys.executable, "-m", "storymaker", *argumentos],
            cwd=_BACKEND,
            env=entorno,
            stdin=subprocess.DEVNULL,
            stdout=salida,
            stderr=subprocess.STDOUT,
            **opciones,  # type: ignore[call-overload]
        )
    return nombre
