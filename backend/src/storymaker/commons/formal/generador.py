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

from storymaker.commons.validation.puras import normalizar

#: La época común: 1800-01-01. Se elige dentro del rango del dominio para que los números
#: del fichero generado sean legibles a ojo y un contraejemplo se pueda seguir a mano.
EPOCA: Final = date(1800, 1, 1)

_ISO = re.compile(r"^(-?\d{1,4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?$")
_PREFIJO = re.compile(r"^(-?\d{1,4})\b")
_ANIO = re.compile(r"\b(\d{4})\b")

_MESES: Final = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}  # fmt: skip
#: Una estación es un mes aproximado: vale para ordenar y para nacer, no para coincidir.
_ESTACIONES: Final = {"invierno": 1, "primavera": 4, "verano": 7, "otono": 10}

#: Cuánto dice una fecha. Solo lo fechado al día puede coincidir con otro evento el mismo
#: día; «1856» no es el 1 de enero de 1856 (spec trama-rehacible §3.3).
DIA: Final = "dia"
MES: Final = "mes"
ANIO: Final = "anio"


@dataclass(frozen=True)
class FechaLeida:
    momento: int | None
    precision: str = ""


def leer_fecha(fecha: str | None) -> FechaLeida:
    """Lee una fecha en ISO o en prosa castellana, y dice cuánto precisa.

    El corpus trae ISO —«1805», «1805-04», «1805-04-11»—, pero la escaleta la escribe el
    arquitecto y la escribía en prosa: «24 junio 1858, madrugada», «Primavera 1856». El
    lector anterior solo miraba el principio y leía ahí el año 24. Ahora, fuera del ISO,
    **el año es el primer número de cuatro cifras**, el mes su nombre o una estación, y el
    día el número que va delante del mes. Un rango —«1846-1850»— se lee por su principio.
    Sin año de cuatro cifras queda el número del principio, salvo que sea un día seguido de
    un mes, que sin año no es una fecha.
    """
    if not fecha or not fecha.strip():
        return FechaLeida(None)
    limpia = fecha.strip()
    if (iso := _ISO.match(limpia)) is not None:
        precision = DIA if iso.group(3) else MES if iso.group(2) else ANIO
        return FechaLeida(_dias(int(iso.group(1)), iso.group(2), iso.group(3)), precision)

    palabras = normalizar(limpia).split()
    mes = next((i for i, p in enumerate(palabras) if p in _MESES), None)
    if (anio := _ANIO.search(limpia)) is None:
        if mes is not None or (prefijo := _PREFIJO.match(limpia)) is None:
            return FechaLeida(None)
        return FechaLeida(_dias(int(prefijo.group(1)), None, None), ANIO)

    if mes is not None:
        numero_mes = _MESES[palabras[mes]]
        anterior = palabras[mes - 1] if mes >= 1 else ""
        if anterior == "de" and mes >= 2:
            anterior = palabras[mes - 2]
        dia = int(anterior) if anterior.isdigit() and 1 <= int(anterior) <= 31 else None
        return FechaLeida(
            _dias(int(anio.group(1)), str(numero_mes), str(dia) if dia else None),
            DIA if dia else MES,
        )
    estacion = next((_ESTACIONES[p] for p in palabras if p in _ESTACIONES), None)
    if estacion is not None:
        return FechaLeida(_dias(int(anio.group(1)), str(estacion), None), MES)
    return FechaLeida(_dias(int(anio.group(1)), None, None), ANIO)


def _dias(anio: int, mes: str | None, dia: str | None) -> int | None:
    numero_mes = min(max(int(mes or 1), 1), 12)
    numero_dia = min(max(int(dia or 1), 1), 28)
    try:
        return (date(anio, numero_mes, numero_dia) - EPOCA).days
    except ValueError:
        return None


def a_momento(fecha: str | None) -> int | None:
    """Convierte una fecha a días desde la época. `None` si no hay fecha.

    Un `None` no es un hueco que rellenar: en el modelo de Lean significa que no hay
    restricción por ese lado, que es exactamente lo que quiere decir no saber cuándo murió
    alguien.
    """
    return leer_fecha(fecha).momento


#: El nacimiento de quien no tiene fecha: tan atrás que ninguna escena cae antes. Con `0`
#: —el 1 de enero de 1800— toda escena del siglo XVI ponía a sus personajes antes de nacer.
NACIMIENTO_DESCONOCIDO = -(10**7)


def nacimiento_de(fecha: object) -> int:
    """El momento de nacer, o `NACIMIENTO_DESCONOCIDO` si no hay fecha que leer.

    Lo usan la revisión de la escaleta y la cronología de la publicación, para que «no se
    sabe» signifique lo mismo en los dos: ninguna restricción, no «nació en 1800».
    """
    momento = a_momento(str(fecha)) if fecha else None
    return NACIMIENTO_DESCONOCIDO if momento is None else momento


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
    """`some n`, con paréntesis si `n` es negativo.

    Sin ellos Lean lee `some -4035` como una resta y el fichero no compila. Pasa con todo
    personaje histórico que muere antes del origen de la cronología, como Carlos III en una
    novela de 1787.
    """
    if valor is None:
        return "none"
    return f"some ({valor})" if valor < 0 else f"some {valor}"


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
