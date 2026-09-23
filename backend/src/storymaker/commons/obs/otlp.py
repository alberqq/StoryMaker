"""spec: §3.8 · arq: §14, §18

La exportación OTLP nativa de Claude Code: **capa enriquecedora y opcional**.

Añade por debajo los spans internos de cada agente —llamadas al modelo, ejecuciones de
herramientas y de hooks, cadenas de subagentes— sin instrumentar nada. Es información que
los spans manuales no tienen, porque el arnés no ve dentro de la sesión del agente.

Y **la observabilidad no depende de ella**, por dos razones declaradas: está en beta y no
está documentado que funcione por la vía del SDK de Python. Por eso se activa por variable
de entorno y por eso lo que se considera fuente autorizada son los spans que emiten los
nodos. Si OTLP no llega, la traza sigue contando la historia completa a la escala que
importa: sesión por novela, span por invocación.

Este módulo no exporta nada por su cuenta: solo prepara el entorno del subproceso que el
SDK lanza, que es donde esa telemetría se configura.
"""

from __future__ import annotations

from typing import Final

from storymaker.commons.config import Settings

#: Las variables que Claude Code lee para emitir OTLP. Se ponen en el entorno del
#: subproceso y no en el del arnés: activarlo aquí no debe activarlo para todo lo demás.
VARIABLES: Final = (
    "CLAUDE_CODE_ENABLE_TELEMETRY",
    "OTEL_METRICS_EXPORTER",
    "OTEL_LOGS_EXPORTER",
    "OTEL_EXPORTER_OTLP_PROTOCOL",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
)


def entorno_para_el_subproceso(settings: Settings) -> dict[str, str]:
    """Las variables que hay que pasarle al subproceso, o un diccionario vacío.

    Vacío cuando está desactivado, y eso es lo normal: el valor por defecto de
    `otlp_enabled` es `false`. Una capa opcional que estuviera activada por defecto dejaría
    de ser opcional en la práctica.
    """
    if not settings.otlp_enabled:
        return {}

    return {
        "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
        "OTEL_METRICS_EXPORTER": "otlp",
        "OTEL_LOGS_EXPORTER": "otlp",
        "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
        "OTEL_EXPORTER_OTLP_ENDPOINT": settings.langfuse_host.rstrip("/") + "/api/public/otel",
    }


def esta_activo(settings: Settings) -> bool:
    return bool(entorno_para_el_subproceso(settings))
