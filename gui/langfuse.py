"""Envio de trazas a Langfuse por OpenTelemetry, con biblioteca estandar.

No se usa el SDK oficial a proposito. La arquitectura declara que el arnes no
tiene dependencias en tiempo de ejecucion, y la telemetria no es razon suficiente
para romper eso: OTLP sobre HTTP admite JSON, y eso `urllib` ya lo sabe hacer.

**Por que OpenTelemetry y no la API de ingestion.** Hubo una version anterior que
hablaba con `POST /api/public/ingestion`. Aceptaba todo sin una queja --- HTTP 207,
dos eventos, cero errores --- y sin embargo el coste salia a cero en la interfaz
de Langfuse, tirada tras tirada. El motivo lo trae la propia respuesta en un aviso
de obsolescencia: esa API se apaga el 16 de noviembre de 2026 y **el unico camino
a datos en vivo es la ingesta por OpenTelemetry**. Lo que mandabamos por ahi
llegaba a medias: el nombre y los tiempos si, el modelo, los tokens y el coste no.
Se comprobo mandando una sonda con `usageDetails` y `costDetails` bien puestos y
viendo que no aparecia jamas en `/api/public/v2/observations`.

O sea que el problema nunca estuvo en lo que mandabamos, sino en por donde.

**Las credenciales se resuelven del entorno y no se escriben en ningun sitio.**
Ni en un fichero de configuracion, ni en el ledger, ni en un mensaje de error. Si
no estan, el modulo se desactiva solo y el resto sigue funcionando: una Ejecucion
no se cae porque falte la observabilidad.

    LANGFUSE_PUBLIC_KEY   pk-lf-...
    LANGFUSE_SECRET_KEY   sk-lf-...
    LANGFUSE_HOST         https://cloud.langfuse.com  (o tu instancia)

Lo que se traza, como arbol de spans de OpenTelemetry:

    span raiz     una Ejecucion completa del proceso
      span          cada paso: los tres tramos y las dos paradas del Autor
        agent         cada despacho de subagente, con su etapa y su tarea
        generation    el consumo de cada modelo que intervino en ese paso, con sus
                      tokens y su coste, sacados del evento `result` de Claude Code

Las llamadas al nucleo no se trazan: son cientos por Ejecucion y ahogarian el
arbol. Quedan en el Run Ledger, que es su sitio.

El envio va en segundo plano y **nunca levanta una excepcion hacia el que traza**.
Una traza perdida es una molestia; una Ejecucion caida por telemetria seria un
defecto.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import queue
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
HOST_POR_DEFECTO = "https://cloud.langfuse.com"
TIEMPO_ENVIO = 20
LOTE = 20

# Sin esta cabecera, Langfuse acepta los spans pero los mete por la via lenta y
# tardan minutos en poder leerse. Con ella, la ingesta es en tiempo real.
VERSION_INGESTA = "4"

# Codigos de estado de OpenTelemetry. El 0 es "sin fijar" y no se usa aqui.
ESTADO_BIEN = 1
ESTADO_ERROR = 2

_cola: "queue.Queue[dict[str, Any] | None]" = queue.Queue()
_hilo: threading.Thread | None = None
_arranque = threading.Lock()
_ultimo_error: str | None = None


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _nanos() -> int:
    """El reloj en nanosegundos desde la epoca, que es lo que OTLP pide."""
    return int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)


def cargar_env(fichero: Path | None = None) -> int:
    """Mete en el entorno lo que haya en `.env`, sin pisar lo ya definido.

    Las credenciales viven ahi y no en un fichero del Proyecto, que es la regla:
    ninguna credencial aparece en un artefacto persistido. Este cargador las lee
    y las deja en el entorno del proceso, desde donde `credenciales()` las toma.

    **Nunca devuelve ni registra un valor**, solo cuantas claves cargo. Un modulo
    que imprime lo que lee acaba escribiendo un secreto en un log el dia que
    alguien anada un `print` de depuracion.

    Lo ya definido manda: si alguien exporto la variable a mano, el fichero no la
    pisa. Asi se puede probar contra otra instancia sin editar nada.
    """
    fichero = fichero or (RAIZ / ".env")
    try:
        crudo = fichero.read_text(encoding="utf-8")
    except OSError:
        return 0

    cargadas = 0
    for linea in crudo.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        clave = clave.strip().removeprefix("export ").strip()
        valor = valor.strip().strip('"').strip("'")
        if clave and valor and clave not in os.environ:
            os.environ[clave] = valor
            cargadas += 1
    return cargadas


def credenciales() -> tuple[str, str, str] | None:
    publica = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
    secreta = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
    host = os.environ.get("LANGFUSE_HOST", HOST_POR_DEFECTO).strip().rstrip("/")
    if not publica or not secreta:
        return None
    return publica, secreta, host


def activo() -> bool:
    return credenciales() is not None


def estado() -> dict[str, Any]:
    """Para que la interfaz pueda decir si esto esta grabando o no.

    Nunca devuelve las claves, ni recortadas: el host si, porque saber contra que
    instancia se traza es util y no es un secreto.
    """
    credencial = credenciales()
    return {
        "activo": credencial is not None,
        "host": credencial[2] if credencial else os.environ.get("LANGFUSE_HOST", HOST_POR_DEFECTO),
        "protocolo": "opentelemetry",
        "ultimo_error": _ultimo_error,
        "nota": (
            None if credencial else
            "Faltan LANGFUSE_PUBLIC_KEY y LANGFUSE_SECRET_KEY en el entorno. "
            "Se resuelven de ahi y no se guardan en ningun fichero."
        ),
    }


# ==========================================================================
# Identificadores y atributos de OpenTelemetry
# ==========================================================================


def _hex(semilla: str, octetos: int) -> str:
    """Un identificador de OTLP, derivado de forma estable de una clave nuestra.

    Se derivan y no se sortean para que el identificador de una traza se pueda
    reconstruir sabiendo el del proceso: buscar en Langfuse la tirada `prc_...`
    que uno tiene delante deja de ser un ejercicio de correlacion.
    """
    return hashlib.sha256(semilla.encode("utf-8")).hexdigest()[: octetos * 2]


def _atributo(clave: str, valor: Any) -> dict[str, Any] | None:
    """Un atributo de span en la forma que OTLP/JSON exige.

    Los nulos se descartan en lugar de mandarse: un atributo presente con valor
    vacio se distingue mal de uno que si se midio y salio cero, y aqui hay
    numeros --- tokens, coste --- donde esa diferencia importa.
    """
    if valor is None or valor == "":
        return None
    if isinstance(valor, bool):
        return {"key": clave, "value": {"boolValue": valor}}
    if isinstance(valor, int):
        return {"key": clave, "value": {"intValue": str(valor)}}
    if isinstance(valor, float):
        return {"key": clave, "value": {"doubleValue": valor}}
    if isinstance(valor, (dict, list)):
        return {"key": clave, "value": {"stringValue": json.dumps(valor, ensure_ascii=False)}}
    return {"key": clave, "value": {"stringValue": str(valor)}}


def _sumar_modelos(por_modelo: dict[str, dict[str, int]]) -> dict[str, int]:
    """Junta el consumo de varios modelos en una sola ficha de uso."""
    total = {"input": 0, "output": 0,
             "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    for uso in por_modelo.values():
        total["input"] += uso.get("inputTokens") or 0
        total["output"] += uso.get("outputTokens") or 0
        total["cache_read_input_tokens"] += uso.get("cacheReadInputTokens") or 0
        total["cache_creation_input_tokens"] += uso.get("cacheCreationInputTokens") or 0
    total["total"] = sum(total.values())
    return total


def _atributos(pares: dict[str, Any]) -> list[dict[str, Any]]:
    return [a for a in (_atributo(k, v) for k, v in pares.items()) if a is not None]


# ==========================================================================
# Envio
# ==========================================================================


def _enviar(spans: list[dict[str, Any]]) -> None:
    global _ultimo_error
    credencial = credenciales()
    if credencial is None or not spans:
        return
    publica, secreta, host = credencial
    autorizacion = base64.b64encode(f"{publica}:{secreta}".encode()).decode()

    cuerpo = json.dumps({
        "resourceSpans": [{
            "resource": {"attributes": _atributos({"service.name": "storymaker"})},
            "scopeSpans": [{
                "scope": {"name": "storymaker.gui", "version": "2.0"},
                "spans": spans,
            }],
        }],
    }).encode("utf-8")

    peticion = urllib.request.Request(
        f"{host}/api/public/otel/v1/traces",
        data=cuerpo,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {autorizacion}",
            "x-langfuse-ingestion-version": VERSION_INGESTA,
        },
    )
    try:
        with urllib.request.urlopen(peticion, timeout=TIEMPO_ENVIO) as respuesta:
            respuesta.read()
        _ultimo_error = None
    except urllib.error.HTTPError as error:
        # El detalle del error si interesa; la credencial que lo produjo, no.
        detalle = ""
        try:
            detalle = error.read()[:200].decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            pass
        _ultimo_error = f"HTTP {error.code} al exportar a Langfuse: {detalle}".strip()
        _apartar(spans)
    except Exception as error:  # noqa: BLE001 - la telemetria no tumba nada
        _ultimo_error = f"{type(error).__name__} al exportar a Langfuse"
        _apartar(spans)


def _apartar(spans: list[dict[str, Any]]) -> None:
    """Guarda en disco los spans que no se pudieron exportar.

    Antes se perdian en silencio: si Langfuse estaba caido o las credenciales
    habian caducado, la traza de esa Ejecucion simplemente no existia y nadie se
    enteraba hasta ir a buscarla. Aqui quedan, en OTLP tal cual, listos para
    reenviarse o para mirarlos a mano.
    """
    try:
        destino = RAIZ / "tmp" / "trazas_sin_enviar"
        destino.mkdir(parents=True, exist_ok=True)
        fichero = destino / f"{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        with fichero.open("a", encoding="utf-8") as salida:
            for span in spans:
                salida.write(json.dumps(span, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass


def _bombear() -> None:
    lote: list[dict[str, Any]] = []
    while True:
        span = _cola.get()
        if span is None:
            _enviar(lote)
            return
        lote.append(span)
        if len(lote) >= LOTE or _cola.empty():
            _enviar(lote)
            lote = []


def _encolar(span: dict[str, Any]) -> None:
    global _hilo
    if not activo():
        return
    with _arranque:
        if _hilo is None or not _hilo.is_alive():
            _hilo = threading.Thread(target=_bombear, daemon=True)
            _hilo.start()
    _cola.put(span)


# ==========================================================================
# La traza
# ==========================================================================


class Traza:
    """Una Ejecucion trazada. Sin credenciales, todos sus metodos no hacen nada.

    Un span de OpenTelemetry se manda entero, con su principio y su final a la
    vez: no existe "abrir" y "actualizar". Por eso aqui se guardan los inicios y
    cada span se emite al cerrarse. Con la API anterior ese detalle costo caro ---
    mandar creacion y actualizacion producia dos observaciones en lugar de una, y
    la traza salia con cada paso duplicado --- y aqui ya no se puede caer en ello.
    """

    def __init__(
        self, identificador: str, nombre: str, metadatos: dict[str, Any],
        clave_traza: str | None = None,
    ):
        """`identificador` es el proceso; `clave_traza`, lo que la traza representa.

        Son cosas distintas y confundirlas salia caro. Una Ejecucion cortada se
        relanza --- porque la sesion murio, porque el Autor la paro, porque se
        rechazo un tramo --- y cada relanzamiento levanta un proceso nuevo. Cuando
        la traza se identificaba por el proceso, **cada relanzamiento aparecia en
        Langfuse como una traza aparte**, con el mismo nombre que las anteriores y
        sin forma de distinguirlas: cuatro «Ejecucion - El cartografo de Amberes»
        para una sola novela.

        Con la clave estable --- el Proyecto --- todas las tiradas de una novela
        caen en la misma traza y se ven como lo que son: intentos sucesivos de
        terminar el mismo trabajo. El proceso no se pierde: viaja en los
        identificadores de los spans, para que dos tiradas no se pisen, y en los
        metadatos, para saber cual emitio cada cosa.
        """
        self.id = identificador
        self.clave = clave_traza or identificador
        self.nombre = nombre
        self.metadatos = metadatos
        self.activa = activo()
        self.traza_otel = _hex(self.clave, 16)
        # La raiz es **por tirada**, no por traza. Reemitir una misma raiz en cada
        # relanzamiento no la actualiza: Langfuse no funde dos spans con el mismo
        # identificador, y la traza acababa con una raiz por tirada y todas con el
        # mismo nombre. Asi cada una se ve como lo que es, un intento fechado, y
        # la traza entera sigue llamandose como la novela.
        self.span_raiz = _hex(f"{self.clave}:{self.id}:raiz", 8)
        self.inicio = _nanos()
        self._inicios: dict[str, int] = {}
        self._esperas: set[str] = set()
        self._por_rol: dict[str, dict[str, dict[str, dict[str, int]]]] = {}

    def _span_paso(self, clave: str) -> str:
        """El span de un paso, unico por tirada.

        Lleva el proceso dentro a proposito: si dos tiradas de la misma Ejecucion
        compartieran identificador de span, la segunda machacaria a la primera y
        se perderia justo lo que interesa mirar --- por que hubo que relanzar.
        """
        return _hex(f"{self.clave}:{self.id}:{clave}", 8)

    # -- construccion de spans --------------------------------------------

    def _span(
        self, span_id: str, padre: str | None, nombre: str,
        inicio: int, fin: int, atributos: dict[str, Any],
        error: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        span: dict[str, Any] = {
            "traceId": self.traza_otel,
            "spanId": span_id,
            "name": nombre,
            "kind": 1,  # INTERNAL
            "startTimeUnixNano": str(inicio),
            "endTimeUnixNano": str(fin),
            "attributes": _atributos(atributos),
            "status": {"code": ESTADO_ERROR if error else ESTADO_BIEN},
        }
        if padre:
            span["parentSpanId"] = padre
        if error:
            span["status"]["message"] = str(error.get("mensaje") or error)[:500]
        return span

    # -- superficie que usa el orquestador --------------------------------

    def paso_inicio(self, clave: str, nombre: str, entrada: str, tipo: str) -> None:
        self._inicios[clave] = _nanos()
        # Se recuerda cuales son paradas del Autor. Su duracion es real y se manda
        # tal cual --- falsearla seria mentir sobre cuando ocurrio cada cosa ---,
        # pero va marcada para que al sumar tiempos se pueda separar lo que el
        # arnes tardo en trabajar de lo que tardo el Autor en decidir.
        if tipo == "espera":
            self._esperas.add(clave)

    def paso_fin(self, clave: str, salida: str, error: dict[str, Any] | None) -> None:
        if not self.activa:
            return
        _encolar(self._span(
            self._span_paso(clave), self.span_raiz, clave,
            self._inicios.get(clave, _nanos()), _nanos(),
            {
                "langfuse.observation.type": "span",
                "langfuse.observation.output": salida[:8000],
                "langfuse.trace.name": self.nombre,
                "langfuse.observation.metadata.espera_del_autor": clave in self._esperas,
            },
            error,
        ))

    def subagente(
        self, clave: str, identificador: str, quien: str, que: str,
        inicio: int, fin: int, error: bool = False,
        uso: dict[str, dict[str, int]] | None = None,
    ) -> None:
        """Un despacho de subagente, como span hijo del tramo que lo lanzo.

        Sin esto, la traza de una Ejecucion son tres cajas --- un span por tramo ---
        y no se ve quien trabajo dentro de cada una. El gasto se atribuia al
        modelo, que dice si la culpa es del conductor o de los subagentes, pero no
        **cual** subagente ni sobre que: un `tramo_novela` de seis euros no decia
        si se fueron en redactar, en refinar o en un capitulo que el validador
        devolvio cuatro veces.

        El tipo `agent` es uno de los que Langfuse entiende, asi que estos spans
        salen distinguidos de los tramos y de las generaciones en su interfaz.

        Las llamadas al nucleo no se emiten: son cientos por Ejecucion, ahogarian
        el arbol, y ya quedan en el Run Ledger, que es su sitio.
        """
        if not self.activa:
            return
        _encolar(self._span(
            _hex(f"{self.clave}:{self.id}:{clave}:{identificador}", 8),
            self._span_paso(clave),
            f"{quien} · {que}"[:120] if que else quien,
            inicio, fin,
            {
                "langfuse.observation.type": "agent",
                "langfuse.observation.input": que,
                "langfuse.observation.metadata.etapa": quien,
                "langfuse.observation.metadata.tramo": clave,
                "langfuse.observation.metadata.rol": "subagente",
                # Lo que gasto **este** despacho, no el modelo que lo sirvio. Se
                # busca por el identificador de la llamada que lo lanzo.
                "langfuse.observation.usage_details": _sumar_modelos(uso) if uso else None,
                "langfuse.trace.name": self.nombre,
            },
            {"mensaje": "el subagente devolvio error"} if error else None,
        ))

    def consumo(
        self, clave: str, resultado: dict[str, Any],
        por_rol: dict[str, dict[str, dict[str, int]]] | None = None,
    ) -> None:
        """El gasto real de una etapa, del evento `result` de Claude Code.

        Se emite una generacion por modelo y no una sola agregada, porque una
        etapa mezcla modelos --- el que conduce el tramo y el que despacha cada
        subagente --- y agregarlos esconde justo lo que se quiere ver al calibrar.

        `usage_details` y `cost_details` viajan como cadenas JSON, que es lo que
        Langfuse espera en un atributo de span: OTLP no admite objetos anidados.
        """
        if not self.activa or not isinstance(resultado, dict):
            return
        por_modelo = resultado.get("modelUsage") or {}
        inicio = self._inicios.get(clave, _nanos())
        fin = _nanos()
        padre = self._span_paso(clave)

        # El reparto entre el conductor y los subagentes se guarda para que los
        # spans de cada uno puedan llevarlo, y se anota tambien aqui: sin esto,
        # distinguir quien gasta exige mirar el modelo, y eso deja de funcionar
        # en cuanto conductor y subagentes compartan modelo.
        self._por_rol[clave] = por_rol or {}
        conductor = (por_rol or {}).get("conductor") or {}
        if conductor:
            _encolar(self._span(
                _hex(f"{self.clave}:{self.id}:{clave}:conductor", 8), padre,
                f"{clave} · conductor", inicio, fin,
                {
                    "langfuse.observation.type": "generation",
                    "langfuse.observation.model.name": sorted(conductor)[0],
                    "langfuse.observation.usage_details": _sumar_modelos(conductor),
                    "langfuse.observation.metadata.rol": "conductor",
                    "langfuse.trace.name": self.nombre,
                },
            ))

        for modelo, uso in por_modelo.items():
            if not isinstance(uso, dict):
                continue
            entrada = uso.get("inputTokens") or 0
            salida = uso.get("outputTokens") or 0
            cache_lectura = uso.get("cacheReadInputTokens") or 0
            cache_escritura = uso.get("cacheCreationInputTokens") or 0
            nombre_modelo = uso.get("canonicalModel") or modelo

            _encolar(self._span(
                _hex(f"{self.clave}:{self.id}:{clave}:{modelo}", 8), padre,
                f"{clave} · {nombre_modelo}", inicio, fin,
                {
                    "langfuse.observation.type": "generation",
                    "langfuse.observation.model.name": nombre_modelo,
                    "gen_ai.request.model": nombre_modelo,
                    "langfuse.observation.usage_details": {
                        "input": entrada,
                        "output": salida,
                        "cache_read_input_tokens": cache_lectura,
                        "cache_creation_input_tokens": cache_escritura,
                        "total": entrada + salida + cache_lectura + cache_escritura,
                    },
                    "langfuse.observation.cost_details": {
                        "total": float(uso.get("costUSD") or 0.0),
                    },
                    "langfuse.observation.metadata.ventana_contexto": uso.get("contextWindow"),
                    "langfuse.observation.metadata.sesion_claude": resultado.get("session_id"),
                    "langfuse.trace.name": self.nombre,
                },
            ))

    def cerrar(self, estado_final: str, resumen: dict[str, Any]) -> None:
        """El span raiz, que es el que da nombre y forma a la traza entera.

        Se emite al final porque abarca todo lo demas, y un span de OTLP necesita
        saber cuando termina para poder mandarse.
        """
        if not self.activa:
            return
        momento = datetime.fromtimestamp(self.inicio / 1e9, timezone.utc)
        _encolar(self._span(
            self.span_raiz, None,
            f"Tirada · {momento.strftime('%d/%m %H:%M:%S')}", self.inicio, _nanos(),
            {
                "langfuse.observation.type": "span",
                "langfuse.trace.name": self.nombre,
                "langfuse.observation.output": resumen,
                "langfuse.observation.metadata.estado_final": estado_final,
                "langfuse.observation.metadata.proceso": self.id,
                **{
                    f"langfuse.observation.metadata.{k}": v
                    for k, v in (self.metadatos or {}).items()
                },
            },
            None if estado_final in ("terminado", "cancelado") else {"mensaje": estado_final},
        ))
        _cola.put(None)
