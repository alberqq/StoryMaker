"""spec: §3.3 · arq: §5, §12

**La única puerta al modelo.** Ningún módulo del sistema llama al Agent SDK por su cuenta:
todo pasa por `invocar_rol`, y es lo que hace que el techo de §12 sea una propiedad de la
construcción y no una convención que haya que recordar.

Aquí se fijan por invocación el modelo, las herramientas concedidas, los turnos y el techo
del perfil; se cuenta el prompt antes de emitir; se imponen la cuota de herramientas y el
truncado de sus respuestas; y se valida la salida contra su esquema antes de que nadie
escriba en SQLite.

El transporte es un protocolo y no el SDK directamente. Eso permite que la suite recorra
el grafo entero con un doble determinista —sin gastar un token ni depender de la red— por
el mismo camino de código que usa la producción, que es la única forma de que las pruebas
de integración comprueben algo real.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol

from pydantic import BaseModel

from storymaker.commons.agents.hooks import CuotaDeHerramientas
from storymaker.commons.agents.presupuesto import guarda_techo
from storymaker.commons.agents.schema_guard import SalidaInvalida, validar
from storymaker.commons.agents.techos import TECHOS, Perfil, herramientas_de, turnos_de
from storymaker.commons.config import Rol, Settings


@dataclass(frozen=True)
class Consumo:
    """Lo que costó una invocación.

    `coste_usd` es una **estimación en cliente**, no facturación (U-7), y se etiqueta así
    en toda salida que lo enseñe.
    """

    tokens_in: int = 0
    tokens_out: int = 0
    coste_usd: float = 0.0

    def __add__(self, otro: Consumo) -> Consumo:
        return Consumo(
            self.tokens_in + otro.tokens_in,
            self.tokens_out + otro.tokens_out,
            self.coste_usd + otro.coste_usd,
        )


@dataclass(frozen=True)
class RespuestaBruta:
    """Lo que devuelve el transporte antes de validarse contra ningún esquema."""

    texto: str
    consumo: Consumo = field(default_factory=Consumo)


class Transporte(Protocol):
    """Lo mínimo que el arnés necesita de quien hable con el modelo."""

    async def pedir(
        self,
        *,
        perfil: Perfil,
        modelo: str,
        prompt: str,
        sistema: str,
        herramientas: tuple[str, ...],
        max_turns: int,
        cuota: CuotaDeHerramientas,
    ) -> RespuestaBruta: ...


@dataclass(frozen=True)
class Resultado[T: BaseModel]:
    """La salida validada, con lo que costó y cuántos intentos hicieron falta."""

    valor: T
    consumo: Consumo
    intentos: int


def contrato_de_salida(esquema: type[BaseModel]) -> str:
    """La forma de la salida, redactada para el rol a partir de su propio modelo Pydantic.

    **El contrato de salida viaja con la llamada** (arq. §5). El rol valida contra un
    esquema que tiene que ver: sin él, improvisa los nombres de los campos, que es lo que
    hizo el entrevistador en la primera ejecución real. Se genera del mismo modelo contra
    el que valida `schema_guard`, de modo que no hay una segunda descripción que pueda
    divergir, y se compacta porque cuenta contra el techo del rol como el resto del prompt.
    """
    esquema_json = json.dumps(
        esquema.model_json_schema(), ensure_ascii=False, separators=(",", ":")
    )
    return (
        "\n\n## Formato de la respuesta\n"
        "Responde **solo** con un objeto JSON que cumpla exactamente este JSON Schema: "
        "los mismos nombres de campo, todos los obligatorios presentes, los tipos y los "
        "valores de enumeración tal como se declaran. Sin texto antes ni después.\n"
        f"```json\n{esquema_json}\n```"
    )


async def invocar_rol[T: BaseModel](
    perfil: Perfil,
    prompt: str,
    esquema: type[T],
    *,
    transporte: Transporte,
    settings: Settings,
    sistema: str = "",
    reintentos_de_esquema: int = 1,
) -> Resultado[T]:
    """Invoca un rol y devuelve su salida ya validada.

    El orden de lo que ocurre aquí no es casual. Primero se cuenta —porque una llamada que
    no cabe es mejor no emitirla que emitirla y ver qué pasa—, después se llama con la
    cuota de herramientas ya construida, y solo al final se valida. Si la validación falla,
    se reintenta **inyectando el error de Pydantic en el prompt**: un modelo al que se le
    dice qué campo falta suele arreglarlo, y uno al que se le dice «no valida» no.
    """
    modelo = settings.modelo_por_rol[TECHOS[perfil].rol]
    cuota = CuotaDeHerramientas.para(perfil)
    consumo = Consumo()
    texto_extra = ""
    contrato = contrato_de_salida(esquema)

    for intento in range(1, reintentos_de_esquema + 2):
        prompt_completo = prompt + contrato + texto_extra
        guarda_techo(perfil, sistema + prompt_completo)
        respuesta = await transporte.pedir(
            perfil=perfil,
            modelo=modelo,
            prompt=prompt_completo,
            sistema=sistema,
            herramientas=herramientas_de(perfil),
            max_turns=turnos_de(perfil),
            cuota=cuota,
        )
        consumo = consumo + respuesta.consumo
        try:
            return Resultado(validar(esquema, respuesta.texto), consumo, intento)
        except SalidaInvalida as fallo:
            if intento > reintentos_de_esquema:
                raise
            texto_extra = (
                "\n\nTu respuesta anterior no cumplia el esquema y ha sido rechazada "
                f"por el arnes:\n{fallo}\n\nResponde de nuevo, solo con el JSON valido."
            )

    raise AssertionError("inalcanzable: el bucle sale por return o por raise")


def rol_de(perfil: Perfil) -> Rol:
    return TECHOS[perfil].rol
