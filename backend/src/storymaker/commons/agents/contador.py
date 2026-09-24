"""spec: §3.3 · arq: §8

Realiza §9.2 de la spec de ejecución real.

El consumo se cuenta **en el transporte**, no en cada nodo.

`TransporteContado` envuelve a cualquier `Transporte` —el del Agent SDK o el doble de la
suite— y acumula lo que devuelve cada `pedir`. Contarlo aquí tiene dos ventajas sobre
sumar el `Resultado` en cada nodo agente: no depende de que ningún nodo se acuerde, y
cuenta también los intentos que `invocar_rol` descarta por esquema inválido, que se pagan
igual y que ningún `Resultado` llega a enseñar.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from storymaker.commons.agents.invocacion import Consumo, RespuestaBruta, Transporte

if TYPE_CHECKING:
    from storymaker.commons.agents.hooks import CuotaDeHerramientas
    from storymaker.commons.agents.techos import Perfil


class TransporteContado:
    """Un `Transporte` que deja pasar cada llamada y suma su consumo."""

    def __init__(self, interior: Transporte) -> None:
        self.interior = interior
        self.consumo = Consumo()

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
    ) -> RespuestaBruta:
        respuesta = await self.interior.pedir(
            perfil=perfil,
            modelo=modelo,
            prompt=prompt,
            sistema=sistema,
            herramientas=herramientas,
            max_turns=max_turns,
            cuota=cuota,
        )
        self.consumo = self.consumo + respuesta.consumo
        return respuesta
