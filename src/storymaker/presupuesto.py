"""Presupuestos y contabilidad (seccion 8, RF-070 a RF-079).

Toda llamada pasa por el nucleo, de modo que la contabilidad es exacta por
construccion y no por muestreo.

Dos ideas gobiernan este modulo:

**Admision previa.** El control de presupuesto no es un aviso a posteriori: es
una puerta previa. Antes de despachar una unidad se estima su coste y se compara
con el remanente. Si no cabe, se deniega la unidad y se cierra ordenadamente, en
lugar de descubrir el sobrecoste cuando ya se gasto.

**Los dos tramos de reserva (D24).** La reserva comun se parte en dos, y el
segundo tramo solo lo libera el ultimo tercio de la Novela. Sin esa particion, la
reserva se la comen los primeros capitulos -- que siempre iteran mas, porque la
voz aun no esta fijada y el libro de hechos esta vacio -- y el ultimo tercio
llega sin credito, que es justo donde el riesgo de degradacion es mayor. Una
unidad anterior al ultimo tercio que solicite el tramo final recibe una
denegacion, no un prestamo.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from storymaker.errores import ErrorStoryMaker

# Valores por defecto de la Funcional 10.1. Todos son SUP-027 y deben
# recalibrarse tras la primera novela completa: el informe de RF-079 es la unica
# via por la que dejaran de ser una suposicion.
POR_DEFECTO: dict[str, Any] = {
    "iteraciones_bucle_interno_por_escena": 3,
    "iteraciones_bucle_externo_por_capitulo": 2,
    "iteraciones_validacion_canon": 3,
    "reserva_porcentaje": 0.20,
    "reserva_tramo_libre": 0.60,
    "reserva_tramo_final": 0.40,
    "reserva_tope_por_unidad": 3,
    "solicitudes_investigacion_por_escena": 2,
    "solicitudes_investigacion_por_ejecucion": 15,
    "factor_arnes_maximo": 15,
    "duracion_reloj_horas": 24,
    "aviso_proyeccion_en_avance": 0.25,
    "tolerancia_extension": 0.10,
    "umbral_mayores_por_capitulo": 2,
    "umbral_menores_agregado": 8,
}

AMBITO_EJECUCION = "ejecucion"
AMBITO_CAPITULO = "capitulo"
AMBITO_ESCENA = "escena"

TRAMO_LIBRE = "libre"
TRAMO_FINAL = "final"


@dataclass
class Consumo:
    iteraciones: int = 0
    reserva_libre: int = 0
    reserva_final: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    coste: float = 0.0
    segundos: float = 0.0
    solicitudes_investigacion: int = 0

    def sumar(self, otro: "Consumo") -> "Consumo":
        return Consumo(
            iteraciones=self.iteraciones + otro.iteraciones,
            reserva_libre=self.reserva_libre + otro.reserva_libre,
            reserva_final=self.reserva_final + otro.reserva_final,
            tokens_entrada=self.tokens_entrada + otro.tokens_entrada,
            tokens_salida=self.tokens_salida + otro.tokens_salida,
            coste=self.coste + otro.coste,
            segundos=self.segundos + otro.segundos,
            solicitudes_investigacion=self.solicitudes_investigacion + otro.solicitudes_investigacion,
        )

    def como_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Estimacion:
    """Lo que una unidad cree que va a costar, antes de gastarlo."""

    iteraciones: int = 1
    coste: float = 0.0
    segundos: float = 0.0
    tokens_manifiesto: int = 0


@dataclass
class Veredicto:
    """Resultado de la puerta de admision."""

    admitida: bool
    motivo: str
    tramo: str | None = None
    codigo_error: str | None = None
    remanente: dict[str, Any] = field(default_factory=dict)

    def como_dict(self) -> dict[str, Any]:
        return {
            "admitida": self.admitida,
            "motivo": self.motivo,
            "tramo": self.tramo,
            "codigo_error": self.codigo_error,
            "remanente": self.remanente,
        }


@dataclass
class Presupuesto:
    """Presupuesto congelado de una Ejecucion (RF-070, RF-071)."""

    coste_total: float
    segundos_total: float
    iteraciones_total: int
    reserva_porcentaje: float = POR_DEFECTO["reserva_porcentaje"]
    reserva_tramo_libre: float = POR_DEFECTO["reserva_tramo_libre"]
    reserva_tope_por_unidad: int = POR_DEFECTO["reserva_tope_por_unidad"]
    iteraciones_escena: int = POR_DEFECTO["iteraciones_bucle_interno_por_escena"]
    iteraciones_capitulo: int = POR_DEFECTO["iteraciones_bucle_externo_por_capitulo"]
    iteraciones_canon: int = POR_DEFECTO["iteraciones_validacion_canon"]
    solicitudes_por_escena: int = POR_DEFECTO["solicitudes_investigacion_por_escena"]
    solicitudes_por_ejecucion: int = POR_DEFECTO["solicitudes_investigacion_por_ejecucion"]

    @property
    def reserva_total(self) -> int:
        return int(round(self.iteraciones_total * self.reserva_porcentaje))

    @property
    def reserva_libre(self) -> int:
        return int(round(self.reserva_total * self.reserva_tramo_libre))

    @property
    def reserva_final(self) -> int:
        return self.reserva_total - self.reserva_libre

    @property
    def iteraciones_repartidas(self) -> int:
        """Lo que queda tras apartar la reserva comun."""
        return self.iteraciones_total - self.reserva_total

    def como_dict(self) -> dict[str, Any]:
        base = asdict(self)
        base.update(
            reserva_total=self.reserva_total,
            reserva_libre=self.reserva_libre,
            reserva_final=self.reserva_final,
            iteraciones_repartidas=self.iteraciones_repartidas,
        )
        return base

    @classmethod
    def desde_dict(cls, dato: dict[str, Any]) -> "Presupuesto":
        campos = {
            clave: dato[clave]
            for clave in cls.__dataclass_fields__
            if clave in dato
        }
        return cls(**campos)


class Contabilidad:
    """Lleva el consumo de una Ejecucion y ejerce la puerta de admision."""

    def __init__(self, presupuesto: Presupuesto):
        self.presupuesto = presupuesto
        self.global_: Consumo = Consumo()
        self.por_unidad: dict[str, Consumo] = {}

    # -- lectura -----------------------------------------------------------

    def remanente(self) -> dict[str, Any]:
        return {
            "coste": round(self.presupuesto.coste_total - self.global_.coste, 6),
            "segundos": round(self.presupuesto.segundos_total - self.global_.segundos, 3),
            "iteraciones": self.presupuesto.iteraciones_total - self.global_.iteraciones,
            "reserva_libre": self.presupuesto.reserva_libre - self.global_.reserva_libre,
            "reserva_final": self.presupuesto.reserva_final - self.global_.reserva_final,
            "solicitudes_investigacion": (
                self.presupuesto.solicitudes_por_ejecucion
                - self.global_.solicitudes_investigacion
            ),
        }

    def consumo_de(self, unidad: str) -> Consumo:
        return self.por_unidad.get(unidad, Consumo())

    # -- puerta de admision (RF-072, ERR-404) ------------------------------

    def admitir(
        self,
        unidad: str,
        estimacion: Estimacion,
        *,
        ambito: str = AMBITO_ESCENA,
        tramo_solicitado: str | None = None,
        en_ultimo_tercio: bool = False,
    ) -> Veredicto:
        """Decide si una unidad puede despacharse, antes de que exista la llamada.

        Se comprueba en orden: primero lo que se agota antes, para que el motivo
        que se registra sea el que de verdad detuvo el bucle (RF-072).
        """
        restante = self.remanente()

        if estimacion.coste > restante["coste"]:
            return Veredicto(
                False,
                f"La estimacion de coste ({estimacion.coste}) supera el remanente ({restante['coste']})",
                codigo_error="ERR-404",
                remanente=restante,
            )
        if estimacion.segundos > restante["segundos"]:
            return Veredicto(
                False,
                "La estimacion de duracion supera el remanente de tiempo",
                codigo_error="ERR-403",
                remanente=restante,
            )

        if tramo_solicitado == TRAMO_FINAL and not en_ultimo_tercio:
            # D24: el tramo final es una reserva, no un prestamo.
            return Veredicto(
                False,
                "El tramo final de la reserva solo lo libera el ultimo tercio de la Novela",
                tramo=TRAMO_FINAL,
                codigo_error="ERR-407",
                remanente=restante,
            )

        if tramo_solicitado is not None:
            disponible = restante["reserva_final" if tramo_solicitado == TRAMO_FINAL else "reserva_libre"]
            if estimacion.iteraciones > disponible:
                return Veredicto(
                    False,
                    f"El tramo {tramo_solicitado} de la reserva no tiene credito suficiente",
                    tramo=tramo_solicitado,
                    codigo_error="ERR-406" if tramo_solicitado == TRAMO_LIBRE else "ERR-401",
                    remanente=restante,
                )
            ya_usadas = self.consumo_de(unidad)
            usadas_de_reserva = ya_usadas.reserva_libre + ya_usadas.reserva_final
            if usadas_de_reserva + estimacion.iteraciones > self.presupuesto.reserva_tope_por_unidad:
                return Veredicto(
                    False,
                    "Esta unidad agotaria su tope de reserva y dejaria sin credito al resto de la novela",
                    tramo=tramo_solicitado,
                    codigo_error="ERR-401",
                    remanente=restante,
                )
        elif estimacion.iteraciones > restante["iteraciones"]:
            return Veredicto(
                False,
                "No quedan iteraciones presupuestadas",
                codigo_error="ERR-401",
                remanente=restante,
            )

        return Veredicto(
            True,
            f"Admitida en ambito {ambito}",
            tramo=tramo_solicitado,
            remanente=restante,
        )

    # -- registro del consumo real -----------------------------------------

    def registrar(self, unidad: str, consumo: Consumo, tramo: str | None = None) -> None:
        if tramo == TRAMO_LIBRE:
            consumo = Consumo(**{**consumo.como_dict(), "reserva_libre": consumo.iteraciones})
        elif tramo == TRAMO_FINAL:
            consumo = Consumo(**{**consumo.como_dict(), "reserva_final": consumo.iteraciones})
        self.por_unidad[unidad] = self.consumo_de(unidad).sumar(consumo)
        self.global_ = self.global_.sumar(consumo)

    def registrar_solicitud_investigacion(self, unidad: str) -> None:
        """RF-017 con los dos topes de 10.1: por escena y por Ejecucion."""
        de_la_unidad = self.consumo_de(unidad)
        if de_la_unidad.solicitudes_investigacion >= self.presupuesto.solicitudes_por_escena:
            raise ErrorStoryMaker(
                "ERR-405",
                "Esta escena agoto sus solicitudes de investigacion. Mas solicitudes "
                "indican una laguna estructural del Contexto, y eso se resuelve en E2.",
                unidad=unidad,
                tope=self.presupuesto.solicitudes_por_escena,
            )
        if self.global_.solicitudes_investigacion >= self.presupuesto.solicitudes_por_ejecucion:
            raise ErrorStoryMaker(
                "ERR-405",
                "La Ejecucion agoto su tope de solicitudes de investigacion",
                tope=self.presupuesto.solicitudes_por_ejecucion,
            )
        self.registrar(unidad, Consumo(solicitudes_investigacion=1))

    # -- proyeccion y calibracion ------------------------------------------

    def proyeccion(self, avance: float) -> dict[str, Any] | None:
        """Proyeccion a terminacion, emitida al 25 % de avance (RNF-016).

        Antes de ese punto la proyeccion no es informativa; despues, ya no queda
        margen para abortar barato.
        """
        if avance < POR_DEFECTO["aviso_proyeccion_en_avance"] or avance <= 0:
            return None
        return {
            "avance": round(avance, 4),
            "coste_proyectado": round(self.global_.coste / avance, 4),
            "segundos_proyectados": round(self.global_.segundos / avance, 2),
            "iteraciones_proyectadas": int(round(self.global_.iteraciones / avance)),
            "coste_presupuestado": self.presupuesto.coste_total,
            "excede": (self.global_.coste / avance) > self.presupuesto.coste_total,
        }

    def factor_arnes(self, coste_generacion_bruta: float) -> float | None:
        """Cociente entre el coste total y el de una generacion en bruto (RNF-015)."""
        if coste_generacion_bruta <= 0:
            return None
        return round(self.global_.coste / coste_generacion_bruta, 3)

    def informe_calibracion(
        self,
        modos_terminacion: dict[str, int],
        coste_generacion_bruta: float = 0.0,
    ) -> dict[str, Any]:
        """Consumo real frente a presupuestado (RF-079)."""
        return {
            "presupuestado": self.presupuesto.como_dict(),
            "consumido": self.global_.como_dict(),
            "remanente": self.remanente(),
            "por_unidad": {
                unidad: consumo.como_dict() for unidad, consumo in sorted(self.por_unidad.items())
            },
            "uso_reserva": {
                "tramo_libre": self.global_.reserva_libre,
                "tramo_final": self.global_.reserva_final,
                "tope_por_unidad": self.presupuesto.reserva_tope_por_unidad,
            },
            "solicitudes_investigacion": self.global_.solicitudes_investigacion,
            "factor_arnes": self.factor_arnes(coste_generacion_bruta),
            "distribucion_modos_terminacion": modos_terminacion,
            "aviso": (
                "Todos los valores presupuestados son SUP-027. Este informe es la "
                "unica via por la que dejaran de ser una suposicion."
            ),
        }


def en_ultimo_tercio(capitulo_actual: int, capitulos_totales: int) -> bool:
    """Frontera del tramo final de la reserva (D24).

    Se calcula sobre capitulos planificados, no sobre palabras escritas, porque
    la decision de admision ocurre antes de escribir.
    """
    if capitulos_totales <= 0:
        return False
    return capitulo_actual > (capitulos_totales * 2) / 3
