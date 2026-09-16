"""Terminacion de bucles y evaluacion (secciones 7.3 y 9, RF-055, RF-075).

Cuatro modos cierran una unidad y un quinto no la cierra:

| Modo | Nombre        | Que lo dispara                                        |
|------|---------------|-------------------------------------------------------|
| T1   | convergencia  | No quedan bloqueantes ni mayores por encima del umbral |
| T2   | estancamiento | El conjunto no mejora, o reaparece un hallazgo resuelto|
| T3   | regresion     | La evaluacion empeora respecto a la anterior           |
| T4   | agotamiento   | Se agota cualquiera de los presupuestos                |
| T5   | escalado      | Bloqueo irresoluble: **no cierra**, detiene y eleva    |

En T2, T3 y T4 se emite Deuda de calidad con lo que queda abierto. En T3 ademas
se revierte a la mejor version, porque INV-4 exige que la Novela contenga la mejor
version evaluada de cada escena y no la ultima generada.

Sobre la evaluacion: la seccion 9.3 lo dice sin rodeos, y conviene repetirlo aqui
porque es una carencia conocida y no un olvido. Las puntuaciones de rubrica se
calculan, se persisten y **solo se usan para comparar una version consigo misma**.
Ningun minimo las convierte en puerta. Convertir la rubrica en puerta es la
decision funcional pendiente T-02.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from storymaker import SCHEMA_VERSION
from storymaker.hallazgos import (
    BLOQUEANTE,
    MAYOR,
    Hallazgo,
    abiertos,
    peso_total,
    reaparecidos,
)
from storymaker.sobre import ahora

T1_CONVERGENCIA = "convergencia"
T2_ESTANCAMIENTO = "estancamiento"
T3_REGRESION = "regresion"
T4_AGOTAMIENTO = "agotamiento"
T5_ESCALADO = "escalado"

MODOS_QUE_CIERRAN = (T1_CONVERGENCIA, T2_ESTANCAMIENTO, T3_REGRESION, T4_AGOTAMIENTO)
MODOS_CON_DEUDA = (T2_ESTANCAMIENTO, T3_REGRESION, T4_AGOTAMIENTO)


@dataclass
class Evaluacion:
    """Puntuacion de una version bajo una rubrica versionada.

    `sin_historial` documenta que el evaluador no vio las iteraciones previas
    (SUP-023). Sin esa marca, la comparacion entre iteraciones no es valida:
    un evaluador que arrastra contexto se ablanda por acumulacion segun avanza
    el bucle, y entonces la convergencia que mide es la suya, no la del texto.
    """

    version_rubrica: str
    puntuaciones: dict[str, float]
    sin_historial: bool = True
    evaluado_en: str = field(default_factory=ahora)
    schema_version: str = SCHEMA_VERSION

    @property
    def total(self) -> float:
        if not self.puntuaciones:
            return 0.0
        return round(sum(self.puntuaciones.values()) / len(self.puntuaciones), 4)

    def comparable_con(self, otra: "Evaluacion") -> bool:
        """Mismos criterios, misma escala, ambas sin historial (Funcional 11.3)."""
        return (
            self.version_rubrica == otra.version_rubrica
            and set(self.puntuaciones) == set(otra.puntuaciones)
            and self.sin_historial
            and otra.sin_historial
        )

    def como_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "version_rubrica": self.version_rubrica,
            "puntuaciones": self.puntuaciones,
            "total": self.total,
            "sin_historial": self.sin_historial,
            "evaluado_en": self.evaluado_en,
        }

    @classmethod
    def desde_dict(cls, dato: dict[str, Any]) -> "Evaluacion":
        return cls(
            version_rubrica=dato["version_rubrica"],
            puntuaciones=dato.get("puntuaciones", {}),
            sin_historial=dato.get("sin_historial", True),
            evaluado_en=dato.get("evaluado_en", ahora()),
            schema_version=dato.get("schema_version", SCHEMA_VERSION),
        )


@dataclass
class Iteracion:
    numero: int
    id_version: str
    hallazgos: list[Hallazgo] = field(default_factory=list)
    evaluacion: Evaluacion | None = None

    @property
    def peso(self) -> int:
        return peso_total(self.hallazgos)


@dataclass
class Decision:
    """Lo que el nucleo decide al terminar una iteracion."""

    continua: bool
    modo: str | None
    motivo: str
    version_conservada: str | None = None
    emite_deuda: bool = False
    hallazgos_pendientes: list[str] = field(default_factory=list)
    codigo_error: str | None = None

    def como_dict(self) -> dict[str, Any]:
        return {
            "continua": self.continua,
            "modo_terminacion": self.modo,
            "motivo": self.motivo,
            "version_conservada": self.version_conservada,
            "emite_deuda": self.emite_deuda,
            "hallazgos_pendientes": self.hallazgos_pendientes,
            "codigo_error": self.codigo_error,
        }


def mejor_version(iteraciones: Sequence[Iteracion]) -> str | None:
    """INV-4 y RF-056: la mejor version evaluada, nunca la ultima generada.

    Sin evaluaciones comparables se cae a la ultima version, que es lo unico que
    se puede afirmar; el llamante vera que no hubo evaluacion y sabra por que.
    """
    evaluadas = [it for it in iteraciones if it.evaluacion is not None]
    if not evaluadas:
        return iteraciones[-1].id_version if iteraciones else None
    return max(evaluadas, key=lambda it: it.evaluacion.total).id_version


def decidir(
    iteraciones: Sequence[Iteracion],
    *,
    presupuesto_agotado: bool = False,
    codigo_agotamiento: str | None = None,
    bloqueo_irresoluble: bool = False,
    umbral_mayores: int = 2,
    resueltos_previos: Iterable[str] = (),
) -> Decision:
    """Aplica los cinco modos en el orden en que la especificacion los prioriza.

    El orden importa. Un bloqueo irresoluble se escala aunque el presupuesto este
    agotado, porque escalar no cuesta iteraciones y cerrar con reservas algo que
    una persona podria desbloquear en un minuto seria tirar la novela.
    """
    if not iteraciones:
        return Decision(True, None, "No hay ninguna iteracion registrada todavia")

    actual = iteraciones[-1]
    pendientes = abiertos(actual.hallazgos)
    ids_pendientes = sorted(h.id for h in pendientes)
    bloqueantes = [h for h in pendientes if h.severidad == BLOQUEANTE]
    mayores = [h for h in pendientes if h.severidad == MAYOR]

    # T5 -- no cierra la unidad: la detiene y la eleva (RF-076).
    if bloqueo_irresoluble:
        return Decision(
            False,
            T5_ESCALADO,
            "Bloqueo irresoluble dentro del arnes: se detiene sin consumir mas iteraciones "
            "y se eleva a PC-5",
            version_conservada=mejor_version(iteraciones),
            emite_deuda=False,
            hallazgos_pendientes=ids_pendientes,
            codigo_error="ERR-705",
        )

    # T1 -- convergencia.
    if not bloqueantes and len(mayores) <= umbral_mayores:
        return Decision(
            False,
            T1_CONVERGENCIA,
            f"Sin bloqueantes y con {len(mayores)} mayores, por debajo del umbral de {umbral_mayores}",
            version_conservada=mejor_version(iteraciones),
            emite_deuda=False,
            hallazgos_pendientes=ids_pendientes,
        )

    # T3 -- regresion. Se comprueba antes que el estancamiento porque una
    # evaluacion que empeora es informacion mas fuerte que un conjunto de
    # hallazgos que no mejora: obliga ademas a revertir.
    if len(iteraciones) >= 2:
        anterior = iteraciones[-2]
        if (
            actual.evaluacion is not None
            and anterior.evaluacion is not None
            and actual.evaluacion.comparable_con(anterior.evaluacion)
            and actual.evaluacion.total < anterior.evaluacion.total
        ):
            return Decision(
                False,
                T3_REGRESION,
                f"La evaluacion cae de {anterior.evaluacion.total} a {actual.evaluacion.total}. "
                "Se revierte a la mejor version.",
                version_conservada=mejor_version(iteraciones),
                emite_deuda=True,
                hallazgos_pendientes=ids_pendientes,
                codigo_error="ERR-703",
            )

        # T2 -- estancamiento por conjunto que no mejora.
        if actual.peso >= anterior.peso:
            return Decision(
                False,
                T2_ESTANCAMIENTO,
                f"El conjunto de hallazgos ponderado por severidad no mejora "
                f"({anterior.peso} -> {actual.peso})",
                version_conservada=mejor_version(iteraciones),
                emite_deuda=True,
                hallazgos_pendientes=ids_pendientes,
                codigo_error="ERR-702",
            )

    # T2 -- estancamiento por reaparicion. Esto es lo que RF-075 existe para
    # detectar, y solo funciona porque la identidad del hallazgo es estable.
    vueltos = reaparecidos(actual.hallazgos, resueltos_previos)
    if vueltos:
        return Decision(
            False,
            T2_ESTANCAMIENTO,
            f"Reaparecen hallazgos ya resueltos: {', '.join(vueltos)}",
            version_conservada=mejor_version(iteraciones),
            emite_deuda=True,
            hallazgos_pendientes=ids_pendientes,
            codigo_error="ERR-702",
        )

    # T4 -- agotamiento.
    if presupuesto_agotado:
        return Decision(
            False,
            T4_AGOTAMIENTO,
            "Se agoto uno de los presupuestos de la unidad",
            version_conservada=mejor_version(iteraciones),
            emite_deuda=True,
            hallazgos_pendientes=ids_pendientes,
            codigo_error=codigo_agotamiento or "ERR-401",
        )

    return Decision(
        True,
        None,
        f"Quedan {len(bloqueantes)} bloqueantes y {len(mayores)} mayores por atender",
        hallazgos_pendientes=ids_pendientes,
    )


@dataclass
class Deuda:
    """Deuda de calidad: lo que de otro modo se entregaria en silencio (RF-078)."""

    unidad: str
    modo_cierre: str
    hallazgos: list[str]
    motivo: str
    id: str = ""
    emitida_en: str = field(default_factory=ahora)
    schema_version: str = SCHEMA_VERSION

    def como_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "unidad": self.unidad,
            "modo_cierre": self.modo_cierre,
            "hallazgos": self.hallazgos,
            "motivo": self.motivo,
            "emitida_en": self.emitida_en,
        }


def distribucion_modos(cierres: Iterable[str]) -> dict[str, int]:
    """Reparto de modos de terminacion para el informe de calibracion (RF-079)."""
    reparto = {modo: 0 for modo in (*MODOS_QUE_CIERRAN, T5_ESCALADO)}
    for modo in cierres:
        if modo in reparto:
            reparto[modo] += 1
    return reparto
