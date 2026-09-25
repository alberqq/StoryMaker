"""spec: §3.3 · arq: §5, §12

Las herramientas propias del arnés: **cálculo de fechas para el arquitecto**. El contrato
está en `specs/final/spec.md` §4.

El arquitecto fecha cada escena y conoce las fechas de nacimiento y muerte de cada
personaje, y la aritmética de calendario es justo lo que un modelo hace mal de cabeza:
cuántos años tiene alguien en una escena, qué día cae cuarenta días después de otro. Son
funciones puras, sin red ni base, y su resultado es pequeño, de modo que no mueven el techo
del perfil.

**El esquema se valida dos veces y sale de un solo sitio.** Cada herramienta declara su
entrada como un modelo Pydantic; de él se genera el JSON Schema que ve el modelo —y contra
el que el SDK comprueba la llamada antes de ejecutarla— y contra él mismo se valida dentro
del manejador. Una entrada que no cumple vuelve al rol como error de herramienta, con el
mensaje de Pydantic, igual que hace `schema_guard` con las salidas: un modelo al que se le
dice qué campo falla suele corregirlo.

**Ninguna es un validador.** Los validadores son nodos del grafo y no se conceden como
herramienta (arq. §1, regla Semgrep `validador-no-es-tool`): estas ayudan a planificar y
nada de lo que devuelven se toma como veredicto.

El calendario es el gregoriano proléptico de `datetime`. Para fechas anteriores a 1582 el
día de la semana no coincide con el juliano que se usaba entonces, y la herramienta lo dice
en su propia respuesta.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

#: El nombre del servidor MCP en proceso. Claude Code expone cada herramienta como
#: `mcp__<servidor>__<herramienta>`, y ese nombre calificado es el que cuenta la cuota.
SERVIDOR: Final = "storymaker"

_FECHA_COMPLETA = r"^\d{4}-\d{2}-\d{2}$"
_FECHA_PARCIAL = r"^\d{4}(-\d{2}(-\d{2})?)?$"
_DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
_ADOPCION_GREGORIANA: Final = date(1582, 10, 15)


class EntradaSumarDias(BaseModel):
    """Una fecha exacta y un desplazamiento en días, hacia delante o hacia atrás."""

    model_config = ConfigDict(extra="forbid")

    fecha: str = Field(pattern=_FECHA_COMPLETA, description="Fecha de partida, AAAA-MM-DD")
    dias: int = Field(
        ge=-36_500, le=36_500, description="Dias a sumar; negativo para ir hacia atras"
    )


class EntradaEdad(BaseModel):
    """Una fecha de nacimiento y la fecha en la que se quiere la edad, a la precisión que haya."""

    model_config = ConfigDict(extra="forbid")

    nacimiento: str = Field(
        pattern=_FECHA_PARCIAL, description="Fecha de nacimiento: AAAA, AAAA-MM o AAAA-MM-DD"
    )
    fecha: str = Field(
        pattern=_FECHA_PARCIAL, description="Fecha de la escena: AAAA, AAAA-MM o AAAA-MM-DD"
    )


class EntradaInvalida(ValueError):
    """La entrada cumple el patrón pero no es una fecha real, como 1574-02-30."""


def _fecha(texto: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError as fallo:
        raise EntradaInvalida(f"«{texto}» no es una fecha real: {fallo}") from fallo


def _partes(texto: str) -> tuple[int, int | None, int | None]:
    """AAAA, AAAA-MM o AAAA-MM-DD, con lo que falte como `None`."""
    anio, *resto = (int(t) for t in texto.split("-"))
    mes = resto[0] if resto else None
    dia = resto[1] if len(resto) > 1 else None
    if mes is not None and not 1 <= mes <= 12:
        raise EntradaInvalida(f"«{texto}» tiene un mes fuera de rango")
    if dia is not None:
        _fecha(texto)
    return anio, mes, dia


def _aviso_de_calendario(*fechas: date) -> str:
    if any(f < _ADOPCION_GREGORIANA for f in fechas):
        return (
            " Calendario gregoriano proleptico: antes del 15 de octubre de 1582 el dia de la "
            "semana no coincide con el juliano de la epoca."
        )
    return ""


def sumar_dias(entrada: EntradaSumarDias) -> str:
    """La fecha resultante y el día de la semana en que cae."""
    partida = _fecha(entrada.fecha)
    try:
        resultado = partida + timedelta(days=entrada.dias)
    except OverflowError as fallo:
        raise EntradaInvalida("el resultado cae fuera del calendario representable") from fallo
    return f"{resultado.isoformat()} ({_DIAS[resultado.weekday()]})." + _aviso_de_calendario(
        partida, resultado
    )


def edad_en_fecha(entrada: EntradaEdad) -> str:
    """Los años cumplidos, o el intervalo posible si alguna fecha es parcial."""
    n_anio, n_mes, n_dia = _partes(entrada.nacimiento)
    f_anio, f_mes, f_dia = _partes(entrada.fecha)

    # Si el cumpleaños de ese año ya pasó: `None` cuando la precisión no alcanza a decirlo.
    cumplido: bool | None
    if n_mes is None or f_mes is None:
        cumplido = None
    elif n_mes != f_mes:
        cumplido = f_mes > n_mes
    elif n_dia is None or f_dia is None:
        cumplido = None
    else:
        cumplido = f_dia >= n_dia

    base = f_anio - n_anio
    if base < 0 or (base == 0 and cumplido is False):
        return "La fecha es anterior al nacimiento: el personaje aun no ha nacido."
    if cumplido is None:
        if base == 0:
            return "Nace ese mismo ano: en esa fecha puede no haber nacido todavia."
        return f"Entre {base - 1} y {base} anos: falta precision para decidir."
    return f"{base if cumplido else base - 1} anos cumplidos."


@dataclass(frozen=True)
class Herramienta:
    """Una herramienta propia: su nombre, lo que se le dice al modelo y su esquema."""

    nombre: str
    descripcion: str
    esquema: type[BaseModel]
    funcion: Callable[[Any], str]

    @property
    def calificado(self) -> str:
        return f"mcp__{SERVIDOR}__{self.nombre}"

    def json_schema(self) -> dict[str, Any]:
        return self.esquema.model_json_schema()


HERRAMIENTAS_PROPIAS: Final[dict[str, Herramienta]] = {
    h.calificado: h
    for h in (
        Herramienta(
            "sumar_dias",
            "Suma o resta dias a una fecha exacta y devuelve la fecha resultante y su dia "
            "de la semana. Usala para fechar escenas relativas a otras.",
            EntradaSumarDias,
            sumar_dias,
        ),
        Herramienta(
            "edad_en_fecha",
            "Devuelve la edad que tiene un personaje en una fecha, a partir de su fecha de "
            "nacimiento. Acepta fechas parciales (AAAA o AAAA-MM).",
            EntradaEdad,
            edad_en_fecha,
        ),
    )
}


def _texto(mensaje: str, *, error: bool = False) -> dict[str, Any]:
    resultado: dict[str, Any] = {"content": [{"type": "text", "text": mensaje}]}
    if error:
        resultado["is_error"] = True
    return resultado


def ejecutar(calificado: str, argumentos: dict[str, Any]) -> dict[str, Any]:
    """Valida la entrada contra su modelo y ejecuta. Nunca lanza: los fallos vuelven al rol.

    Es la parte que la suite ejercita sin el SDK instalado: el manejador MCP solo la envuelve.
    """
    herramienta = HERRAMIENTAS_PROPIAS.get(calificado)
    if herramienta is None:
        return _texto(f"Herramienta desconocida: {calificado}", error=True)
    try:
        entrada = herramienta.esquema.model_validate(argumentos)
        return _texto(herramienta.funcion(entrada))
    except ValidationError as fallo:
        errores = json.dumps(
            [{"campo": ".".join(map(str, e["loc"])), "error": e["msg"]} for e in fallo.errors()],
            ensure_ascii=False,
        )
        return _texto(f"Entrada rechazada por el esquema: {errores}", error=True)
    except EntradaInvalida as fallo:
        return _texto(f"Entrada rechazada: {fallo}", error=True)


def es_propia(nombre: str) -> bool:
    return nombre.startswith(f"mcp__{SERVIDOR}__")


def servidor_mcp(calificados: tuple[str, ...]) -> Any:
    """El servidor MCP en proceso con las herramientas pedidas.

    El import es perezoso por la misma razón que en el transporte: el SDK es un extra
    opcional y el resto del módulo se usa y se prueba sin él.
    """
    from claude_agent_sdk import create_sdk_mcp_server, tool

    def envolver(herramienta: Herramienta) -> Any:
        @tool(herramienta.nombre, herramienta.descripcion, herramienta.json_schema())
        async def manejador(argumentos: dict[str, Any]) -> dict[str, Any]:
            return ejecutar(herramienta.calificado, argumentos)

        return manejador

    return create_sdk_mcp_server(
        name=SERVIDOR,
        tools=[envolver(HERRAMIENTAS_PROPIAS[c]) for c in calificados],
    )
