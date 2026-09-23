"""spec: §3.7 · arq: §11c

Genera `formal/lean/Cronologia/Generado.lean`: **solo datos**, nunca teoremas.

La separación no es de estilo. `Cronologia.Basico` se escribe a mano una vez y define
qué significa que una cronología sea coherente; aquí se vuelca el material de una novela
concreta. Si el generador emitiera también los invariantes, cada novela traería su propia
definición de «coherente» y la palabra dejaría de significar nada.

**Los momentos son enteros, no fechas.** El modelo de Lean usa días desde una época común
y el generador es quien convierte, porque la aritmética de calendario es una fuente de
fallos que no aporta nada a lo que aquí se comprueba. La precisión de las fechas del corpus
es desigual —«1805», «1805-04», «1805-04-11»— y una fecha incompleta se completa por el
principio: para lo que estos invariantes detectan, el día exacto rara vez es el problema.

Este módulo es Python corriente y se verifica como tal, con una prueba de contrato que
regenera un fichero de referencia y lo compara. La brecha entre lo que dice el modelo y lo
que hace el código queda declarada como riesgo aceptado U-1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Final

#: La época común: 1800-01-01. Se elige dentro del rango del dominio para que los números
#: del fichero generado sean legibles a ojo y un contraejemplo se pueda seguir a mano.
EPOCA: Final = date(1800, 1, 1)

_FECHA = re.compile(r"^(-?\d{1,4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?")


def a_momento(fecha: str | None) -> int | None:
    """Convierte una fecha del corpus a días desde la época. `None` si no hay fecha.

    Un `None` no es un hueco que rellenar: en el modelo de Lean significa que no hay
    restricción por ese lado, que es exactamente lo que quiere decir no saber cuándo murió
    alguien.
    """
    if not fecha:
        return None
    casa = _FECHA.match(fecha.strip())
    if casa is None:
        return None
    anio = int(casa.group(1))
    mes = min(max(int(casa.group(2) or 1), 1), 12)
    dia = min(max(int(casa.group(3) or 1), 1), 28)
    try:
        return (date(anio, mes, dia) - EPOCA).days
    except ValueError:
        return None


@dataclass(frozen=True)
class Persona:
    """Alguien de la novela, histórico o inventado: a estos efectos da igual."""

    id: int
    nombre: str
    nacimiento: int
    muerte: int | None = None


@dataclass(frozen=True)
class Objeto:
    """Un objeto, término o concepto con existencia fechada, volcado de `mundo_entidad`.

    Es lo que el dominio histórico regala: un telégrafo eléctrico en 1805 es comprobable
    sin que nadie opine.
    """

    id: int
    nombre: str
    aparece: int
    desaparece: int | None = None


@dataclass(frozen=True)
class Evento:
    """Cuándo, dónde, quién estuvo y qué objetos aparecen.

    Lo histórico y lo narrativo van en la misma lista a propósito: es en la mezcla donde
    aparece el personaje inventado que asiste a un acontecimiento antes de que ocurra.
    """

    id: int
    clave: str
    momento: int
    lugar: int
    participantes: tuple[int, ...] = ()
    objetos: tuple[int, ...] = ()
    origen: str = "narrativo"


@dataclass(frozen=True)
class NovelaLean:
    personas: tuple[Persona, ...] = ()
    objetos: tuple[Objeto, ...] = ()
    eventos: tuple[Evento, ...] = field(default_factory=tuple)


def _cadena(valor: str) -> str:
    return '"' + valor.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _opcional(valor: int | None) -> str:
    return "none" if valor is None else f"some {valor}"


def _lista(valores: tuple[int, ...]) -> str:
    return "[" + ", ".join(str(v) for v in valores) + "]"


def _persona(p: Persona) -> str:
    return (
        f"  {{ id := {p.id}, nombre := {_cadena(p.nombre)},\n"
        f"    nacimiento := {p.nacimiento}, muerte := {_opcional(p.muerte)} }}"
    )


def _objeto(o: Objeto) -> str:
    return (
        f"  {{ id := {o.id}, nombre := {_cadena(o.nombre)}, "
        f"aparece := {o.aparece}, desaparece := {_opcional(o.desaparece)} }}"
    )


def _evento(e: Evento) -> str:
    return (
        f"  {{ id := {e.id}, clave := {_cadena(e.clave)}, momento := {e.momento}, "
        f"lugar := {e.lugar},\n"
        f"    participantes := {_lista(e.participantes)}, objetos := {_lista(e.objetos)},\n"
        f"    origen := Origen.{e.origen} }}"
    )


def generar(novela: NovelaLean) -> str:
    """Devuelve el contenido de `Cronologia/Generado.lean`, listo para compilar."""
    personas = ",\n\n".join(_persona(p) for p in novela.personas)
    objetos = ",\n".join(_objeto(o) for o in novela.objetos)
    eventos = ",\n\n".join(_evento(e) for e in novela.eventos)

    return f"""/-
  GENERADO AUTOMATICAMENTE por `commons/formal/generador.py` — no editar a mano.

  Vuelca las tablas `cronologia_evento`, `cronologia_participante`, `canon_personaje` y
  `mundo_entidad` del fichero SQLite de una novela. Se regenera entero en cada invocacion
  del validador, de modo que lo que hay aqui es siempre el estado actual de esa novela.

  Los momentos son dias desde {EPOCA.isoformat()}.
-/
import Cronologia.Basico

namespace Cronologia.Generado

open Cronologia

/-- Personas. `muerte = none` significa que no hay restriccion por ese lado. -/
def personas : List Persona := [
{personas}
]

/-- Objetos con existencia fechada, volcados de `mundo_entidad`. -/
def objetos : List Objeto := [
{objetos}
]

/-- Eventos, historicos y narrativos mezclados a proposito en la misma lista. -/
def eventos : List Evento := [
{eventos}
]

def novela : Novela :=
  {{ personas := personas, objetos := objetos, eventos := eventos }}

end Cronologia.Generado
"""


#: Los cuatro invariantes tal como `Cronologia.Basico` los enuncia, con el mensaje que
#: recibe el editor cuando cae cada uno. Las etiquetas son las que `Verificar.lean`
#: imprime, que es lo que permite emparejar su salida con una incidencia concreta.
INVARIANTES: Final[dict[str, str]] = {
    "I1": "Un personaje participa en un evento anterior a su nacimiento.",
    "I2": (
        "Un personaje participa en un evento posterior a su muerte documentada. Es el caso "
        "que un modelo no detecta: no tiene aritmetica temporal."
    ),
    "I3": "Un personaje esta en dos lugares distintos el mismo dia.",
    "I4": "Aparece un objeto, termino o concepto que aun no existe en esa fecha.",
}
