"""Versionado de esquema con promocion en lectura (ADR-06).

Un Proyecto dura semanas y el esquema cambiara a mitad. La decision es version
por registro con promocion en lectura, sin reescritura retroactiva, y con una
excepcion: **el ledger no se migra nunca**. Se lee siempre con el promotor de su
propia version, porque migrarlo destruiria la evidencia que justifica que exista.

Reglas:

1. Todo registro persistido lleva `schema_version`.
2. Un cambio compatible -- campo opcional nuevo, valor de enumerado nuevo no
   obligatorio -- incrementa la version menor y no exige promotor.
3. Un cambio incompatible incrementa la mayor y exige promotor registrado. Sin
   promotor, el arranque falla con ERR-505: se prefiere no arrancar a leer mal.
4. Los artefactos inmutables ya persistidos no se reescriben jamas; se promueven
   en memoria al leerlos.
5. Al reanudar una Ejecucion cuyo esquema es anterior, el nucleo promueve en
   lectura y anexa un evento que deja constancia de que cruzo una frontera.
6. Los indices llevan la version del codigo que los genero; si no coincide, se
   descartan y se reconstruyen sin preguntar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from storymaker import SCHEMA_VERSION
from storymaker.errores import ErrorStoryMaker

Promotor = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class Frontera:
    """Una promocion registrada de una version mayor a la siguiente."""

    entidad: str
    desde_mayor: int
    hasta_mayor: int
    promotor: Promotor
    motivo: str


_REGISTRO: dict[tuple[str, int], Frontera] = {}


def registrar_promotor(entidad: str, desde_mayor: int, hasta_mayor: int, motivo: str):
    """Decorador que registra el promotor de un cambio incompatible."""

    def envoltorio(funcion: Promotor) -> Promotor:
        _REGISTRO[(entidad, desde_mayor)] = Frontera(
            entidad, desde_mayor, hasta_mayor, funcion, motivo
        )
        return funcion

    return envoltorio


def partir(version: str) -> tuple[int, int]:
    try:
        mayor, menor = version.split(".", 1)
        return int(mayor), int(menor)
    except (ValueError, AttributeError) as fallo:
        raise ErrorStoryMaker(
            "ERR-505", f"schema_version mal formada: {version!r}", version=version
        ) from fallo


def compatible(version_registro: str, version_codigo: str = SCHEMA_VERSION) -> bool:
    """Compatible si comparten la mayor y la menor del registro no es futura."""
    mayor_r, menor_r = partir(version_registro)
    mayor_c, menor_c = partir(version_codigo)
    return mayor_r == mayor_c and menor_r <= menor_c


def promover(
    registro: dict[str, Any],
    entidad: str,
    version_destino: str = SCHEMA_VERSION,
) -> tuple[dict[str, Any], list[str]]:
    """Promueve un registro en memoria hasta la version de destino.

    Devuelve el registro promovido y la lista de fronteras cruzadas, que el
    llamante anexa al ledger (regla 5). No escribe nada: la regla 4 prohibe
    reescribir artefactos inmutables ya persistidos.
    """
    version_actual = registro.get("schema_version")
    if version_actual is None:
        raise ErrorStoryMaker(
            "ERR-505",
            f"Registro de {entidad} sin schema_version; no se puede leer con garantias",
            entidad=entidad,
        )

    mayor_destino, _ = partir(version_destino)
    mayor_actual, menor_actual = partir(version_actual)

    if mayor_actual > mayor_destino:
        raise ErrorStoryMaker(
            "ERR-505",
            f"El registro de {entidad} es de una version mayor que la del codigo "
            f"({version_actual} > {version_destino}). No se arranca.",
            entidad=entidad,
            version_registro=version_actual,
            version_codigo=version_destino,
        )

    promovido = dict(registro)
    fronteras: list[str] = []
    while mayor_actual < mayor_destino:
        frontera = _REGISTRO.get((entidad, mayor_actual))
        if frontera is None:
            raise ErrorStoryMaker(
                "ERR-505",
                f"No hay promotor registrado de {entidad} v{mayor_actual} a "
                f"v{mayor_actual + 1}. Se prefiere no arrancar a leer mal.",
                entidad=entidad,
                desde=mayor_actual,
            )
        promovido = frontera.promotor(promovido)
        fronteras.append(f"{entidad}:{frontera.desde_mayor}->{frontera.hasta_mayor}")
        mayor_actual = frontera.hasta_mayor

    # Un cambio menor no exige promotor: solo se actualiza la marca en memoria.
    promovido["schema_version"] = version_destino
    return promovido, fronteras


def sellar(registro: dict[str, Any]) -> dict[str, Any]:
    """Estampa `schema_version` en un registro que va a persistirse (MD-2)."""
    registro.setdefault("schema_version", SCHEMA_VERSION)
    return registro


def fronteras_registradas() -> list[Frontera]:
    return sorted(_REGISTRO.values(), key=lambda f: (f.entidad, f.desde_mayor))


# --- Promotores de ejemplo -------------------------------------------------
#
# La 1.x almacenaba la vigencia de una version de escena en la propia version.
# La 2.0 la saco a `ramas.json` para que no hubiera dos fuentes de la misma
# verdad divergiendo sin transacciones que lo impidan. Un artefacto de la 1.x se
# lee con este promotor y no se reescribe.


@registrar_promotor(
    "escena_version",
    desde_mayor=1,
    hasta_mayor=2,
    motivo="La vigencia deja de vivir en la version de escena y pasa a ramas.json",
)
def _escena_version_1_a_2(registro: dict[str, Any]) -> dict[str, Any]:
    promovido = dict(registro)
    promovido.pop("vigente", None)
    promovido.setdefault("protegido_palabras", 0)
    promovido.setdefault("es_piloto", False)
    return promovido
