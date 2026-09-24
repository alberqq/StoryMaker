"""spec: §3.2 · arq: §16.4

**Una invocación por novela a la vez, y el fichero es el cerrojo.**

Dos invocaciones simultáneas sobre la misma novela —el Autor que pulsa *Aprobar* dos veces,
o la CLI lanzada mientras el servidor atiende un gate— escribirían sobre el mismo
checkpoint y podrían duplicar un capítulo, que es exactamente lo que `ResumeIsExactlyOnce`
prohíbe.

Un cerrojo en memoria no basta, porque la CLI y la API son **procesos distintos** y no se
verían. De ahí que sea un fichero al lado de la novela, tomado en exclusiva con `O_EXCL`,
que es la única primitiva que el sistema de ficheros garantiza atómica.

**Quien llega segundo es rechazado, no encolado.** Una cola sería ese segundo lugar donde
vive el estado que §16.4 acaba de descartar, y el rechazo no pierde nada: la decisión del
gate ya está escrita y reanudar es el camino de siempre.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from storymaker.commons.errores import NovelaOcupada


def ruta_del_cerrojo(novela: Path) -> Path:
    return novela.with_name(novela.name + ".lock")


@contextmanager
def tomar(novela: Path) -> Iterator[Path]:
    """Toma el cerrojo, o lanza `NovelaOcupada`. Se suelta pase lo que pase.

    Dentro se escribe el PID, que no es ceremonia: cuando un proceso muere sin soltar el
    cerrojo, el Autor necesita poder mirar el fichero y saber si ese proceso sigue vivo
    antes de romperlo con `storymaker desbloquear`.
    """
    cerrojo = ruta_del_cerrojo(novela)
    try:
        descriptor = os.open(cerrojo, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise NovelaOcupada(
            f"Ya hay una invocacion en curso sobre {novela.name}. Quien llega segundo es "
            f"rechazado, no encolado: la decision ya esta escrita y reanudar es el camino "
            f"de siempre. Si el proceso murio, rompe el cerrojo con `storymaker desbloquear`."
        ) from exc

    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as fichero:
            fichero.write(str(os.getpid()))
        yield cerrojo
    finally:
        cerrojo.unlink(missing_ok=True)


def esta_tomado(novela: Path) -> bool:
    return ruta_del_cerrojo(novela).exists()


def romper(novela: Path) -> bool:
    """Rompe un cerrojo huérfano. Devuelve si había alguno.

    Es la operación de mantenimiento que el Autor hará una vez cada muchas, y por eso vive
    en la CLI y no en un reintento automático: un cerrojo que se rompe solo deja de ser un
    cerrojo.
    """
    cerrojo = ruta_del_cerrojo(novela)
    if not cerrojo.exists():
        return False
    cerrojo.unlink()
    return True


def pid_del_cerrojo(novela: Path) -> int | None:
    """El PID que escribió quien tomó el cerrojo, o `None` si no hay cerrojo o no se lee."""
    try:
        return int(ruta_del_cerrojo(novela).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def proceso_vivo(pid: int) -> bool:
    """Si un proceso sigue vivo, **sin tocarlo**.

    En Windows no vale `os.kill(pid, 0)`: allí cualquier señal que no sea de consola termina
    el proceso con `TerminateProcess`, de modo que preguntar si vive lo mataría. Se pregunta
    con `OpenProcess` y `GetExitCodeProcess`, que solo leen.
    """
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        acceso = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION
        sigue_activo = 259  # STILL_ACTIVE
        kernel32 = ctypes.windll.kernel32
        manejador = kernel32.OpenProcess(acceso, False, pid)
        if not manejador:
            return False
        try:
            codigo = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(manejador, ctypes.byref(codigo)):
                return False
            return codigo.value == sigue_activo
        finally:
            kernel32.CloseHandle(manejador)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
