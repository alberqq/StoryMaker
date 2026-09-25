"""spec: §3.8 · arq: §14

Observabilidad. **Los spans manuales que emiten los nodos son la fuente autorizada**, y la
exportación OTLP nativa de Claude Code es una capa enriquecedora y opcional: está en beta y
no está documentado que funcione por la vía del SDK de Python, así que la observabilidad no
depende de ella.

La semántica que importa la pone el orquestador, no la instrumentación automática: una
**sesión por novela** —que incluye la entrevista y todas las regeneraciones posteriores—,
una **traza por generación**, un **span por capítulo** y una `generation` por invocación,
nombrada `capitulo_07 · escritor · intento_2`, con sus herramientas debajo. Ese nombre es
lo que permite que la traza se lea como lo que pasó y no como una lista de llamadas HTTP.

El observador es un protocolo con una implementación nula. No es ceremonia: sin claves de
Langfuse el sistema tiene que correr igual —la suite lo hace en cada ejecución—, y la
alternativa sería un `if` repartido por todos los nodos.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from storymaker.commons.agents.invocacion import Consumo
from storymaker.commons.config import Settings

_log = logging.getLogger(__name__)

_CAPITULO = re.compile(r"^capitulo_(\d+)\b")


def nombre_de_span(*, capitulo: int | None, rol: str, intento: int | None = None) -> str:
    """`capitulo_07 · escritor · intento_2`, y sin capítulo para las fases que no lo tienen."""
    partes = []
    if capitulo is not None:
        partes.append(f"capitulo_{capitulo:02d}")
    partes.append(rol)
    if intento is not None:
        partes.append(f"intento_{intento}")
    return " · ".join(partes)


def capitulo_de(nombre: str) -> int | None:
    """El capítulo de un nombre de span, o `None` si la invocación no tiene capítulo.

    Se lee del nombre porque es el que todos los nodos ya construyen con `nombre_de_span`:
    agrupar por capítulo no obliga a pasar un dato más desde cada uno.
    """
    coincidencia = _CAPITULO.match(nombre)
    return int(coincidencia.group(1)) if coincidencia else None


@dataclass(frozen=True)
class Span:
    """Lo que se registra de una invocación.

    El coste va etiquetado **siempre** como estimación en cliente. No es un matiz legal: la
    propuesta económica del proyecto se apoya en estos números, y presentarlos como
    facturación sería afirmar algo que el SDK no dice (U-7).

    `prompt_nombre` es el nombre del prompt en Langfuse; sin él se usa el `rol`, que
    coincide con el perfil salvo en el investigador, que tiene tres.
    """

    nombre: str
    rol: str
    consumo: Consumo = field(default_factory=Consumo)
    prompt_version: str | None = None
    paquete_id: int | None = None
    metadatos: dict[str, Any] = field(default_factory=dict)
    prompt_nombre: str | None = None

    def como_payload(self) -> dict[str, Any]:
        return {
            "name": self.nombre,
            "metadata": {
                "rol": self.rol,
                "prompt_version": self.prompt_version,
                "prompt_nombre": self.prompt_nombre or self.rol,
                "paquete_contexto_id": self.paquete_id,
                "coste_usd_estimado_en_cliente": self.consumo.coste_usd,
                "duracion_ms": self.consumo.duracion_ms,
                "llamadas_a_herramientas": len(self.consumo.herramientas),
                **self.metadatos,
            },
            "usage_details": {
                "input": self.consumo.tokens_in,
                "output": self.consumo.tokens_out,
            },
            # Es lo que Langfuse suma por sesión, y por tanto el coste por novela. Sigue
            # siendo la estimación del SDK: la etiqueta la lleva el metadato de arriba.
            "cost_details": {"total": self.consumo.coste_usd},
        }


class Observador(Protocol):
    """Lo que los nodos necesitan de la capa de trazas."""

    def abrir_sesion(self, novela: str, *, generacion: int | None = None) -> None: ...

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
    generacion: int | None = None
    spans: list[Span] = field(default_factory=list)
    scores: list[dict[str, Any]] = field(default_factory=list)

    def abrir_sesion(self, novela: str, *, generacion: int | None = None) -> None:
        self.sesion = novela
        self.generacion = generacion

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


@dataclass
class _Observacion:
    """Una observación abierta y por qué vía se abrió, que decide cómo se cierra."""

    sdk: Any
    interna: bool


def _ns(segundos: float) -> int:
    return int(segundos * 1_000_000_000)


class ObservadorLangfuse:
    """La implementación real sobre la API v4 del SDK, construida sobre OpenTelemetry.

    **La traza es la generación** (arq. §14): con `generacion`, su id se deriva de la novela
    y de la versión objetivo, de modo que el arranque y cada reanudación tras un gate caen
    en la misma traza sin guardar nada en la base, y una regeneración abre la suya. Debajo
    cuelgan los spans de capítulo, y de ellos —o de la traza, si no hay capítulo— cada
    invocación como `generation`, que es lo que hace que Langfuse cuente sus tokens y su
    coste. Las herramientas son observaciones `tool` hijas de su invocación.

    **La latencia es real.** Los nodos registran el span cuando la invocación ya terminó,
    así que su inicio es el fin menos `duracion_ms`. La API pública no deja fijarlo, y por
    eso se crea el span con el tracer interno del cliente; si esa vía falla, se usa la
    pública y la latencia queda a cero (U-20).

    El cliente se construye de forma perezosa por la misma razón que el modelo de
    embeddings: la CLI es un proceso por comando y `storymaker estado` no tiene por qué
    abrir una conexión que no va a usar.

    **Un fallo de Langfuse no tumba un nodo.** Perder una traza no corrompe la novela (lo
    dice `construir`), así que el envío se protege y el fallo se anota en el log.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cliente: Any = None
        self._sesion: str | None = None
        self._traza_id: str | None = None
        self._nombre_traza: str | None = None
        self._capitulos: dict[int, _Observacion] = {}
        self._fin_de_capitulo: dict[int, int] = {}

    def _asegurar_cliente(self) -> Any:
        if self._cliente is None:
            from langfuse import Langfuse

            self._cliente = Langfuse(
                public_key=self._settings.langfuse_public_key,
                secret_key=self._settings.langfuse_secret_key,
                host=self._settings.langfuse_host,
            )
        return self._cliente

    def abrir_sesion(self, novela: str, *, generacion: int | None = None) -> None:
        self._sesion = novela
        if generacion is not None:
            from langfuse import Langfuse

            # Determinista y sin red: los procesos de una generación coinciden en el id.
            self._traza_id = Langfuse.create_trace_id(seed=f"{novela}·v{generacion}")
            self._nombre_traza = f"{novela} · v{generacion}"

    def registrar_span(self, span: Span) -> None:
        try:
            from langfuse import propagate_attributes

            self._asegurar_cliente()
            fin = time.time_ns()
            inicio = fin - span.consumo.duracion_ms * 1_000_000
            payload = span.como_payload()
            nombre = payload.pop("name")
            numero = capitulo_de(nombre)
            with propagate_attributes(
                session_id=self._sesion, trace_name=self._nombre_traza or nombre
            ):
                padre = self._capitulo(numero, inicio) if numero is not None else None
                generacion = self._iniciar(
                    padre,
                    nombre=nombre,
                    as_type="generation",
                    inicio_ns=inicio,
                    prompt=self._prompt(span),
                    **payload,
                )
                for llamada in span.consumo.herramientas:
                    herramienta = self._iniciar(
                        generacion,
                        nombre=llamada.nombre,
                        as_type="tool",
                        inicio_ns=_ns(llamada.inicio),
                        input=llamada.entrada,
                        level="ERROR" if llamada.error else None,
                    )
                    self._terminar(herramienta, _ns(llamada.fin))
                self._terminar(generacion, fin)
            if numero is not None:
                self._fin_de_capitulo[numero] = max(self._fin_de_capitulo[numero], fin)
        except Exception:
            _log.warning("No se pudo enviar a Langfuse el span %s", span.nombre, exc_info=True)

    def _capitulo(self, numero: int, inicio: int) -> _Observacion:
        """El span del capítulo, abierto con su primer hijo y cerrado en `cerrar`."""
        if numero not in self._capitulos:
            self._capitulos[numero] = self._iniciar(
                None, nombre=f"capitulo_{numero:02d}", as_type="span", inicio_ns=inicio
            )
            self._fin_de_capitulo[numero] = inicio
        return self._capitulos[numero]

    def _iniciar(
        self,
        padre: _Observacion | None,
        *,
        nombre: str,
        as_type: str,
        inicio_ns: int,
        **campos: Any,
    ) -> _Observacion:
        """Abre una observación con su inicio real, o por la API pública si no se puede.

        Se crea en el contexto actual para que conserve la sesión y el nombre de traza que
        propaga `propagate_attributes`. Sin padre y con traza fija, cuelga de la traza igual
        que lo haría `start_observation(trace_context=…)`.
        """
        cliente = self._cliente
        try:
            from opentelemetry import trace as otel

            raiz = padre is None and self._traza_id is not None
            if padre is not None:
                contexto = otel.set_span_in_context(padre.sdk._otel_span)
            elif raiz:
                remoto = cliente._create_remote_parent_span(
                    trace_id=self._traza_id, parent_span_id=None
                )
                contexto = otel.set_span_in_context(remoto)
            else:
                contexto = None
            otel_span = cliente._otel_tracer.start_span(
                name=nombre, context=contexto, start_time=inicio_ns
            )
            if raiz:
                from langfuse._client.attributes import LangfuseOtelSpanAttributes

                otel_span.set_attribute(LangfuseOtelSpanAttributes.AS_ROOT, True)
            return _Observacion(
                cliente._create_observation_from_otel_span(
                    otel_span=otel_span, as_type=as_type, **campos
                ),
                interna=True,
            )
        except Exception:
            _log.debug("Vía interna del SDK no disponible para %s", nombre, exc_info=True)

        if padre is not None:
            sdk = padre.sdk.start_observation(name=nombre, as_type=as_type, **campos)
        elif self._traza_id is not None:
            sdk = cliente.start_observation(
                trace_context={"trace_id": self._traza_id},
                name=nombre,
                as_type=as_type,
                **campos,
            )
        else:
            sdk = cliente.start_observation(name=nombre, as_type=as_type, **campos)
        return _Observacion(sdk, interna=False)

    @staticmethod
    def _terminar(observacion: _Observacion, fin_ns: int) -> None:
        if observacion.interna:
            observacion.sdk.end(end_time=fin_ns)
        else:
            observacion.sdk.end()

    def _prompt(self, span: Span) -> Any:
        """El prompt de Langfuse con el que se invocó, para enlazarlo a la `generation`."""
        version = span.prompt_version
        if not version or not version.isdigit():
            return None
        try:
            return self._cliente.get_prompt(span.prompt_nombre or span.rol, version=int(version))
        except Exception:
            _log.warning("No se encontró en Langfuse el prompt de %s", span.nombre, exc_info=True)
            return None

    def registrar_score(
        self, *, nombre: str, valor: float, objeto: str, detalle: dict[str, Any] | None = None
    ) -> None:
        # A la traza de la generación si la hay; si no —un `decidir` suelto—, a la sesión.
        destino = (
            {"trace_id": self._traza_id}
            if self._traza_id is not None
            else {"session_id": self._sesion}
        )
        try:
            self._asegurar_cliente().create_score(
                name=nombre,
                value=valor,
                comment=objeto,
                metadata=detalle or {},
                **destino,
            )
        except Exception:
            _log.warning("No se pudo enviar a Langfuse el score %s", nombre, exc_info=True)

    def cerrar(self) -> None:
        for numero, capitulo in self._capitulos.items():
            try:
                self._terminar(capitulo, self._fin_de_capitulo[numero])
            except Exception:
                _log.warning("No se pudo cerrar el span del capitulo %s", numero, exc_info=True)
        self._capitulos.clear()
        if self._cliente is not None:
            self._cliente.flush()


def construir(settings: Settings, *, novela: str | None = None) -> Observador:
    """Devuelve el observador que corresponde a la configuración, con la sesión abierta.

    Con `novela`, la sesión queda abierta desde el principio: un observador sin sesión
    enviaría trazas sueltas que Langfuse no sabría sumar por novela.

    Sin claves, el nulo. No es degradación silenciosa como la de `sqlite-vec`: perder las
    trazas no corrompe una novela ni la empobrece, solo deja de poder explicarse hacia
    atrás, y el Autor lo sabe porque no ha puesto las claves.
    """
    observador: Observador
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        observador = ObservadorLangfuse(settings)
    else:
        observador = ObservadorNulo()
    if novela is not None:
        observador.abrir_sesion(novela)
    return observador
