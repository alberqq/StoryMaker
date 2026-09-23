"""spec: §7.1 · arq: §5

Doble del Agent SDK para las pruebas. Devuelve respuestas fijadas por rol y anota
qué se le pidió, de modo que una prueba de integración pueda recorrer el grafo entero
sin gastar un token ni depender de la red.

Registra la invocación además de responderla porque media suite comprueba cosas que
solo se ven en la llamada: que el investigador es el único que recibe herramientas de
red, que nadie escribe en la base sin pasar por el esquema, o que el editor se invoca
como mucho dos veces por capítulo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from storymaker.commons.agents.invocacion import Consumo, RespuestaBruta
from storymaker.commons.agents.techos import Perfil
from storymaker.commons.config import Rol


class SinRespuestaPreparada(AssertionError):
    """El grafo pidió un rol para el que la prueba no dejó respuesta.

    Es un fallo de la prueba, no del código: significa que el recorrido tocó un agente
    que no se había previsto, y eso es justo lo que conviene que salte.
    """


@dataclass(frozen=True)
class Invocacion:
    """Lo que el arnés pidió: el rol, el prompt ya ensamblado y las herramientas."""

    rol: Rol
    prompt: str
    herramientas: tuple[str, ...] = ()


@dataclass
class AgenteFalso:
    """Cola de respuestas por rol, más el registro de lo que se pidió."""

    respuestas: dict[Rol, list[Any]] = field(default_factory=dict)
    invocaciones: list[Invocacion] = field(default_factory=list)

    def preparar(self, rol: Rol, *respuestas: Any) -> AgenteFalso:
        self.respuestas.setdefault(rol, []).extend(respuestas)
        return self

    def invocar_rol(
        self, rol: Rol, prompt: str, herramientas: tuple[str, ...] = ()
    ) -> Any:
        self.invocaciones.append(Invocacion(rol=rol, prompt=prompt, herramientas=herramientas))
        cola = self.respuestas.get(rol)
        if not cola:
            raise SinRespuestaPreparada(f"ninguna respuesta preparada para el rol {rol.value!r}")
        return cola.pop(0)

    def veces(self, rol: Rol) -> int:
        return sum(1 for i in self.invocaciones if i.rol == rol)

    def prompts_de(self, rol: Rol) -> list[str]:
        return [i.prompt for i in self.invocaciones if i.rol == rol]


@dataclass
class TransporteFalso:
    """Un `Transporte` de verdad —cumple el `Protocol`— alimentado por respuestas en cola.

    `AgenteFalso` sirve para las pruebas de las funciones que piden un rol; este doble está
    un escalón más abajo, en el sitio exacto donde el arnés habla con el modelo, y es el que
    permite recorrer el grafo entero sin abrir una sesión de Claude Code.

    Devuelve **JSON serializado**, no objetos ya validados, porque el reintento por esquema
    de `invocar_rol` es parte de lo que conviene ejercitar: un doble que devolviera modelos
    de Pydantic se saltaría precisamente esa pieza.
    """

    respuestas: dict[Perfil, list[Any]] = field(default_factory=dict)
    pedidos: list[Perfil] = field(default_factory=list)

    def preparar(self, perfil: Perfil, *respuestas: Any) -> TransporteFalso:
        self.respuestas.setdefault(perfil, []).extend(respuestas)
        return self

    async def pedir(
        self,
        *,
        perfil: Perfil,
        modelo: str,
        prompt: str,
        sistema: str,
        herramientas: tuple[str, ...],
        max_turns: int,
        cuota: Any,
    ) -> RespuestaBruta:
        self.pedidos.append(perfil)
        cola = self.respuestas.get(perfil)
        if not cola:
            raise SinRespuestaPreparada(
                f"ninguna respuesta preparada para el perfil {perfil.value!r}"
            )
        valor = cola.pop(0)
        texto = valor if isinstance(valor, str) else valor.model_dump_json()
        return RespuestaBruta(texto=texto, consumo=Consumo(tokens_in=10, tokens_out=10))

    def veces(self, perfil: Perfil) -> int:
        return sum(1 for p in self.pedidos if p is perfil)
