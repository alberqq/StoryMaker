"""El Run Ledger (seccion 5.5).

`ledger.jsonl` es la unica fuente de la trazabilidad y de la contabilidad. Un
evento por linea, tipado, de solo anexion.

Lo que el ledger no es: la verdad del dominio. El Canon y la Novela son
autoritativos por si mismos. El ledger explica *como* llegaron a serlo, y de el
se reconstruyen los indices. Por eso nunca se migra.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from storymaker import SCHEMA_VERSION
from storymaker.almacen import Almacen
from storymaker.errores import ErrorStoryMaker, redactar_secretos
from storymaker.sobre import ahora

# Tipos de evento de la tabla de la seccion 5.5. La lista es cerrada: un evento
# que no figure aqui no se anexa, porque un ledger con tipos libres deja de ser
# consultable.
EVENTOS = {
    "ejecucion_iniciada": "Configuracion congelada: presupuestos con sus dos tramos, modo, versiones de agentes y rubricas, catalogo de modelos",
    "unidad_iniciada": "Identificador, etapa, unidad, intento, clave de idempotencia y manifiesto de contexto",
    "llamada_modelo": "Prompt renderizado, salida cruda, tokens, coste, latencia, modelo solicitado y servido",
    "fidelidad_verificada": "Afirmacion, resultado y contenido cotejado (RF-100)",
    "refutacion_emitida": "Afirmacion, veredicto, fuentes contrarias y consultas (RF-102)",
    "hallazgo_emitido": "Hallazgo completo",
    "hallazgo_transicionado": "Nuevo estado del hallazgo y motivo",
    "evaluacion_registrada": "Puntuacion por criterio, version de rubrica y marca de sin historial (SUP-023)",
    "unidad_cerrada": "Modo de terminacion, version vigente resultante y deuda emitida",
    "presupuesto_admitido": "Ambito, estimacion, remanente y tramo de reserva usado",
    "presupuesto_denegado": "Ambito, estimacion, remanente y motivo de la denegacion",
    "punto_control_abierto": "Tipo y que se presento",
    "punto_control_resuelto": "Decision, quien y cuando",
    "piloto_sometido": "Version de escena del piloto",
    "piloto_resuelto": "Decision del Autor sobre el piloto",
    "canon_versionado": "Version anterior y nueva, motivo, capitulos invalidados y licencias aprobadas",
    "ejecucion_finalizada": "Estado, consumo total e informe de calibracion",
    # Transversales exigidos por la seccion 10 y por ADR-02/ADR-06.
    "error_registrado": "Codigo de error, familia y accion aplicada. Ningun error se traga",
    "escritura_denegada": "Una llamada de agente que intento escribir estado y fue bloqueada (ADR-02)",
    "frontera_esquema_cruzada": "Promocion en lectura al reanudar sobre un esquema anterior (ADR-06 regla 5)",
}


@dataclass
class Evento:
    tipo: str
    carga: dict[str, Any]
    momento: str
    secuencia: int
    proyecto: str
    ejecucion: str
    schema_version: str = SCHEMA_VERSION

    def como_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "secuencia": self.secuencia,
            "momento": self.momento,
            "tipo": self.tipo,
            "proyecto": self.proyecto,
            "ejecucion": self.ejecucion,
            "carga": self.carga,
        }


class Ledger:
    """Anexion y lectura del ledger de una Ejecucion."""

    def __init__(self, almacen: Almacen, id_ejecucion: str):
        self.almacen = almacen
        self.id_ejecucion = id_ejecucion
        self.ruta = almacen.ledger(id_ejecucion)

    # -- escritura ---------------------------------------------------------

    def anexar(self, tipo_evento: str, /, **carga: Any) -> Evento:
        # `tipo_evento` es posicional-solo a proposito: varias cargas del catalogo
        # llevan un campo `tipo` propio, y sin la barra chocarian con el parametro.
        if tipo_evento not in EVENTOS:
            raise ErrorStoryMaker(
                "ERR-302",
                f"Tipo de evento fuera del catalogo del ledger: {tipo_evento}",
                tipo_evento=tipo_evento,
                admitidos=sorted(EVENTOS),
            )
        evento = Evento(
            tipo=tipo_evento,
            carga=redactar_secretos(carga),
            momento=ahora(),
            secuencia=self.siguiente_secuencia(),
            proyecto=self.almacen.id_proyecto,
            ejecucion=self.id_ejecucion,
        )
        self.almacen.anexar(self.ruta, evento.como_dict())
        return evento

    def registrar_error(self, error: ErrorStoryMaker, /, **contexto: Any) -> Evento:
        """Regla transversal de la seccion 10: ningun error se traga.

        Se anexa el evento *antes* de aplicar la accion, porque un error que solo
        aparece en pantalla rompe la trazabilidad.
        """
        return self.anexar("error_registrado", error=error.como_dict(), contexto=contexto)

    # -- lectura -----------------------------------------------------------

    def eventos(self, tipo: str | None = None) -> list[dict[str, Any]]:
        todos = self.almacen.leer_jsonl(self.ruta)
        if tipo is None:
            return todos
        return [evento for evento in todos if evento.get("tipo") == tipo]

    def eventos_de(self, tipos: Iterable[str]) -> list[dict[str, Any]]:
        conjunto = set(tipos)
        return [e for e in self.eventos() if e.get("tipo") in conjunto]

    def siguiente_secuencia(self) -> int:
        eventos = self.almacen.leer_jsonl(self.ruta)
        return (eventos[-1].get("secuencia", len(eventos)) + 1) if eventos else 1

    def ultimo(self, tipo: str) -> dict[str, Any] | None:
        candidatos = self.eventos(tipo)
        return candidatos[-1] if candidatos else None

    def cierre_de_clave(self, clave_idempotencia: str) -> dict[str, Any] | None:
        """Idempotencia (seccion 7.4).

        Antes de despachar, el nucleo pregunta aqui: si esta clave ya tiene un
        cierre registrado, no se vuelve a gastar y se devuelve el resultado
        anterior. Es lo que permite reanudar una Ejecucion caida sin pagar dos
        veces, y lo que hace que `etapa reejecutar` sea seguro.
        """
        for evento in reversed(self.eventos("unidad_cerrada")):
            if evento.get("carga", {}).get("clave_idempotencia") == clave_idempotencia:
                return evento
        return None

    def lineas_descartadas(self) -> list[dict[str, Any]]:
        """Evidencia de ERR-503: lineas truncadas por un corte."""
        return [
            {"numero": d.numero, "motivo": d.motivo}
            for d in self.almacen.lineas_descartadas
        ]
