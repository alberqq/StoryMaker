"""spec: §3.3 · arq: §1, §5, §14

El transporte de producción: **Claude Code lanzado como subproceso por el Agent SDK**.

Conviene decir con claridad de dónde sale la autenticación, porque determina la superficie
de secretos del proyecto entero: **el arnés no autentica nada**. El SDK arranca el CLI de
Claude Code, que ya tiene la sesión del Autor iniciada, y hereda esa credencial. No hay
clave de Anthropic en `Settings`, ni en `.env`, ni en el entorno que este proceso
construye; lo único que el arnés fija por invocación es el modelo, las herramientas
concedidas, los turnos y los hooks que imponen las cuotas.

De ahí que los únicos secretos del repositorio sean el token de Telegram y las claves de
Langfuse, y que `gitleaks` no tenga que buscar nada más.

Lo que sí sale del SDK es la contabilidad: el `ResultMessage` trae el uso desglosado
—entrada, salida, creación y lectura de caché— y un `total_cost_usd` que es una
**estimación en cliente**, no facturación (U-7).
"""

from __future__ import annotations

from typing import Any

from storymaker.commons.agents.hooks import CuotaDeHerramientas, truncar_salida
from storymaker.commons.agents.invocacion import Consumo, RespuestaBruta
from storymaker.commons.agents.techos import Perfil
from storymaker.commons.config import Defaults


class TransporteAgentSDK:
    """Habla con el modelo a través de Claude Code. No se ejercita en la suite.

    Las pruebas recorren el grafo con un doble determinista por el mismo camino de código,
    que es lo que permite comprobar el comportamiento del arnés sin gastar un token. Lo que
    esta clase hace de verdad —que el subproceso arranque y responda— se demuestra en los
    evals de G2 con el sistema entero corriendo, que es donde esa clase de fallo aparece.
    """

    def __init__(self, *, techo_webfetch: int = Defaults.TECHO_WEBFETCH_TOKENS) -> None:
        self._techo_webfetch = techo_webfetch

    def _hooks(self, cuota: CuotaDeHerramientas) -> dict[str, Any]:
        """Los dos hooks de §12, que son lo que impone el techo por construcción.

        `PreToolUse` deniega en cuanto la cuota se agota, de modo que la cuarta búsqueda no
        llega a emitirse. `PostToolUse` reescribe el resultado antes de que entre en el
        contexto, de modo que una página de cuarenta mil tokens no entra entera. Ninguno de
        los dos es declarativo: no hay opción que los haga, se programan.

        El SDK espera, por evento, **una lista de `HookMatcher`**, no la función suelta: con
        la función a pelo revienta al convertir las opciones, antes de lanzar el subproceso,
        y así cayó la primera ejecución real. `PostToolUse` va acotado a `WebFetch`, que es
        la única salida con techo; sin acotar, reescribiría también la de cualquier otra
        herramienta con una forma que no es la suya.
        """
        from claude_agent_sdk import HookMatcher

        async def pre_tool_use(entrada: dict[str, Any], *_: object) -> dict[str, Any]:
            herramienta = str(entrada.get("tool_name", ""))
            decision = cuota.decidir(herramienta)
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", **decision}}

        async def post_tool_use(entrada: dict[str, Any], *_: object) -> dict[str, Any]:
            bruto = str(entrada.get("tool_response", ""))
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "updatedToolOutput": truncar_salida(bruto, self._techo_webfetch),
                }
            }

        return {
            "PreToolUse": [HookMatcher(hooks=[pre_tool_use])],
            "PostToolUse": [HookMatcher(matcher="WebFetch", hooks=[post_tool_use])],
        }

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
        # El import es perezoso porque el SDK es un extra opcional: la persistencia, el
        # ensamblador y el Core Domain se pueden usar y probar sin él instalado.
        from claude_agent_sdk import ClaudeAgentOptions, query

        opciones = ClaudeAgentOptions(
            model=modelo,
            system_prompt=sistema or None,
            # `allowed_tools` solo aprueba sin preguntar; `tools` es lo que el rol **ve**.
            # Sin él, un rol sin herramientas intentaba usar las de Claude Code, el hook se
            # las denegaba y el único turno se gastaba sin respuesta.
            tools=list(herramientas),
            allowed_tools=list(herramientas),
            max_turns=max_turns,
            hooks=self._hooks(cuota),
            # Claude Code difiere `WebSearch` y `WebFetch` tras `ToolSearch`, y cargarlas
            # cuesta un turno que la micro-sesión de dos (arq. §4) no tiene. Con esto
            # llegan cargadas desde el primer turno.
            env={"ENABLE_TOOL_SEARCH": "false"},
        )

        partes: list[str] = []
        final = ""
        consumo = Consumo()
        try:
            async for mensaje in query(prompt=prompt, options=opciones):
                for bloque in getattr(mensaje, "content", []) or []:
                    if isinstance(getattr(bloque, "text", None), str):
                        partes.append(bloque.text)
                if type(mensaje).__name__ == "ResultMessage":
                    # La respuesta final del rol. El texto intermedio de un rol con
                    # herramientas («voy a buscar…») no es salida y no se valida.
                    if isinstance(getattr(mensaje, "result", None), str):
                        final = mensaje.result
                    consumo = _consumo_de(mensaje)
        except Exception as fallo:
            # Agotar los turnos no es una avería del sistema: lo que el rol llegó a decir
            # pasa a `schema_guard`, que decide y reintenta con el error inyectado.
            if "maximum number of turns" not in str(fallo):
                raise

        return RespuestaBruta(final or "\n".join(partes), consumo)


def _consumo_de(mensaje: object) -> Consumo:
    """Tokens y coste del `ResultMessage`, cuyo `usage` el SDK entrega como `dict`.

    Leerlo con `getattr` daba cero siempre, y `storymaker estado` enseñaba una novela
    gratis. `total_cost_usd` sigue siendo una estimación en cliente, no facturación (U-7).
    """
    uso = getattr(mensaje, "usage", None) or {}
    leer = uso.get if isinstance(uso, dict) else (lambda k, d=0: getattr(uso, k, d))
    entrada = sum(
        int(leer(k, 0) or 0)
        for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    )
    return Consumo(
        tokens_in=entrada,
        tokens_out=int(leer("output_tokens", 0) or 0),
        coste_usd=float(getattr(mensaje, "total_cost_usd", 0.0) or 0.0),
    )
