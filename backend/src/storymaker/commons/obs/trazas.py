"""spec: §3.8 · arq: §14

Observabilidad. **Los spans manuales que emiten los nodos son la fuente autorizada**, y la
exportación OTLP nativa de Claude Code es una capa enriquecedora y opcional: está en beta y
no está documentado que funcione por la vía del SDK de Python, así que la observabilidad no
depende de ella.

La semántica que importa la pone el orquestador, no la instrumentación automática: una
**sesión por novela** —que incluye la entrevista y todas las regeneraciones posteriores— y
un **span por invocación**, nombrado `capitulo_07 · escritor · intento_2`. Ese nombre es lo
que permite que la traza se lea como lo que pasó y no como una lista de llamadas HTTP.

El observador es un protocolo con una implementación nula. No es ceremonia: sin claves de
Langfuse el sistema tiene que correr igual —la suite lo hace en cada ejecución—, y la
alternativa sería un `if` repartido por todos los nodos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from storymaker.commons.agents.invocacion import Consumo
from storymaker.commons.config import Settings


def nombre_de_span(*, capitulo: int | None, rol: str, intento: int | None = None) -> str:
    """`capitulo_07 · escritor · intento_2`, y sin capítulo para las fases que no lo tienen."""
    partes = []
    if capitulo is not None:
        partes.append(f"capitulo_{capitulo:02d}")
    partes.append(rol)
    if intento is not None:
        partes.append(f"intento_{intento}")
    return " · ".join(partes)


@dataclass(frozen=True)
class Span:
    """Lo que se registra de una invocación.

    El coste va etiquetado **siempre** como estimación en cliente. No es un matiz legal: la
    propuesta económica del proyecto se apoya en estos números, y presentarlos como
    facturación sería afirmar algo que el SDK no dice (U-7).
    """

    nombre: str
    rol: str
    consumo: Consumo = field(default_factory=Consumo)
    prompt_version: str | None = None
    paquete_id: int | None = None
    metadatos: dict[str, Any] = field(default_factory=dict)

    def como_payload(self) -> dict[str, Any]:
        return {
            "name": self.nombre,
            "metadata": {
                "rol": self.rol,
                "prompt_version": self.prompt_version,
                "paquete_contexto_id": self.paquete_id,
                "coste_usd_estimado_en_cliente": self.consumo.coste_usd,
                **self.metadatos,
            },
            "usage": {
                "input": self.consumo.tokens_in,
                "output": self.consumo.tokens_out,
            },
        }


class Observador(Protocol):
    """Lo que los nodos necesitan de la capa de trazas."""

    def abrir_sesion(self, novela: str) -> None: ...

    def registrar_span(self, span: Span) -> None: ...

    def registrar_score(
        self, *, nombre: str, valor: float, objeto: str, detalle: dict[str, Any] | None = None
    ) -> None: ...

    def cerrar(self) -> None: ...


@dataclass
class ObservadorNulo:
    """No emite nada y lo recuerda todo. Es el que corre sin claves y en la suite.

    Guardar lo que se le pide en lugar de tirarlo tiene un motivo: las aserciones de G6
    sobre la traza se pueden ensayar contra este observador antes de ejercitarlas contra la
    API de Langfuse, que es lenta y necesita credenciales.
    """

    sesion: str | None = None
    spans: list[Span] = field(default_factory=list)
    scores: list[dict[str, Any]] = field(default_factory=list)

    def abrir_sesion(self, novela: str) -> None:
        self.sesion = novela

    def registrar_span(self, span: Span) -> None:
        self.spans.append(span)

    def registrar_score(
        self, *, nombre: str, valor: float, objeto: str, detalle: dict[str, Any] | None = None
    ) -> None:
        self.scores.append(
            {"nombre": nombre, "valor": valor, "objeto": objeto, "detalle": detalle or {}}
        )

    def cerrar(self) -> None:
        return None


class ObservadorLangfuse:
    """La implementación real. Una sesión por novela y un span por invocación.

    El cliente se construye de forma perezosa por la misma razón que el modelo de
    embeddings: la CLI es un proceso por comando y `storymaker estado` no tiene por qué
    abrir una conexión que no va a usar.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cliente: Any = None
        self._sesion: str | None = None

    def _asegurar_cliente(self) -> Any:
        if self._cliente is None:
            from langfuse import Langfuse

            self._cliente = Langfuse(
                public_key=self._settings.langfuse_public_key,
                secret_key=self._settings.langfuse_secret_key,
                host=self._settings.langfuse_host,
            )
        return self._cliente

    def abrir_sesion(self, novela: str) -> None:
        self._sesion = novela

    def registrar_span(self, span: Span) -> None:
        cliente = self._asegurar_cliente()
        payload = span.como_payload()
        cliente.trace(session_id=self._sesion, **payload)

    def registrar_score(
        self, *, nombre: str, valor: float, objeto: str, detalle: dict[str, Any] | None = None
    ) -> None:
        cliente = self._asegurar_cliente()
        cliente.score(name=nombre, value=valor, comment=objeto, metadata=detalle or {})

    def cerrar(self) -> None:
        if self._cliente is not None:
            self._cliente.flush()


def construir(settings: Settings) -> Observador:
    """Devuelve el observador que corresponde a la configuración.

    Sin claves, el nulo. No es degradación silenciosa como la de `sqlite-vec`: perder las
    trazas no corrompe una novela ni la empobrece, solo deja de poder explicarse hacia
    atrás, y el Autor lo sabe porque no ha puesto las claves.
    """
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        return ObservadorLangfuse(settings)
    return ObservadorNulo()
