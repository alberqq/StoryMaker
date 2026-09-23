"""spec: §3.3 · arq: §12

Las dos piezas que gobiernan lo que entra por herramientas, y que son las que sostienen el
techo del investigador.

**Contar invocaciones** se hace con un hook `PreToolUse` que devuelve
`permissionDecision: "deny"` en cuanto se agota la cuota, de modo que la cuarta búsqueda
no llega a emitirse. **Acotar el tamaño de una respuesta** se hace con un hook
`PostToolUse` que reescribe el resultado con `updatedToolOutput` antes de que entre en el
contexto del agente.

Ninguna de las dos es declarativa: no hay opción en `settings.json` ni en
`ClaudeAgentOptions` que las haga. Se programan una vez aquí y se aplican por invocación.

El tope es doble —tres `WebSearch` y tres `WebFetch`— porque quien llena la ventana no es
la búsqueda sino la página: una búsqueda devuelve una lista de resultados, así que topar
solo las búsquedas permitiría abrir doce páginas y reventar el presupuesto igual que
antes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from storymaker.commons.agents.presupuesto import estimar_tokens
from storymaker.commons.agents.techos import TECHOS, Perfil
from storymaker.commons.config import Defaults


@dataclass
class CuotaDeHerramientas:
    """Contador por sesión. Vive fuera del modelo, que es lo que lo hace imponible."""

    limites: dict[str, int] = field(default_factory=dict)
    usos: dict[str, int] = field(default_factory=dict)

    @classmethod
    def para(cls, perfil: Perfil) -> CuotaDeHerramientas:
        return cls(limites=dict(TECHOS[perfil].cuota_de_herramientas))

    def restantes(self, herramienta: str) -> int:
        return self.limites.get(herramienta, 0) - self.usos.get(herramienta, 0)

    def decidir(self, herramienta: str) -> dict[str, Any]:
        """La respuesta del hook `PreToolUse`.

        Deniega tanto la herramienta agotada como la que nunca estuvo concedida: un rol sin
        cuota declarada para `WebFetch` no tiene «cero usos disponibles», tiene prohibido
        salir a la red, y las dos cosas se resuelven igual aquí.
        """
        if self.restantes(herramienta) <= 0:
            return {
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Cuota agotada para {herramienta}: el arnes concede "
                    f"{self.limites.get(herramienta, 0)} en esta sesion."
                ),
            }
        self.usos[herramienta] = self.usos.get(herramienta, 0) + 1
        return {"permissionDecision": "allow"}


def truncar_salida(texto: str, techo_tokens: int = Defaults.TECHO_WEBFETCH_TOKENS) -> str:
    """Recorta el resultado de una herramienta antes de que entre en el contexto.

    Se corta por el final y se deja dicho que se cortó: un agente que recibe media página
    sin saberlo puede citar como completa una lista que no lo es.
    """
    limite_en_caracteres = techo_tokens * 3
    if estimar_tokens(texto) <= techo_tokens:
        return texto
    aviso = f"\n\n[...] Resultado recortado por el arnes a {techo_tokens} tokens."
    return texto[:limite_en_caracteres] + aviso


def hook_post_tool_use(
    resultado: str, techo_tokens: int = Defaults.TECHO_WEBFETCH_TOKENS
) -> dict[str, Any]:
    """La respuesta del hook `PostToolUse`, con el resultado ya acotado."""
    return {"updatedToolOutput": truncar_salida(resultado, techo_tokens)}
