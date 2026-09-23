"""spec: §4.1 · arq: §10

El informe del gate de Intake: lo que el Autor ve antes de aprobar el encargo.

Es el primero de los cinco y el más barato de todos, porque todavía no se ha gastado nada.
Lo que enseña es exactamente lo que va a costar dinero si está mal: quién es el homenajeado,
en qué período va a vivir, qué elementos son obligatorios y **qué sigue vacío**.

Un brief incompleto no detiene la fase. El gate se abre igualmente con el informe delante,
y el Autor decide si lo completa, lo deja así o aborta. Es el criterio de producto: la
respuesta por defecto ante una puerta que puede bloquear es ablandarla, no reforzarla.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from storymaker.intake.esquemas import Brief


@dataclass(frozen=True)
class InformeDeIntake:
    """Lo que se le enseña al Autor, ya resuelto: aquí no se consulta nada."""

    nombre_homenajeado: str
    periodo: str
    lugar: str
    obligatorios: tuple[str, ...] = ()
    contradicciones: tuple[str, ...] = ()
    campos_vacios: tuple[str, ...] = field(default_factory=tuple)

    @property
    def listo(self) -> bool:
        return not self.contradicciones and not self.campos_vacios

    def como_texto(self) -> str:
        lineas = [
            f"Novela para {self.nombre_homenajeado}.",
            f"Periodo: {self.periodo}. Lugar: {self.lugar}.",
        ]
        if self.obligatorios:
            lineas.append("Elementos obligatorios, que la novela tiene que recoger:")
            lineas += [f"  - {e}" for e in self.obligatorios]
        else:
            lineas.append(
                "Sin elementos obligatorios: nada de lo personal sera exigible, y la "
                "cobertura no tendra nada que comprobar."
            )
        if self.campos_vacios:
            lineas.append("Sigue sin rellenar:")
            lineas += [f"  - {c}" for c in self.campos_vacios]
        if self.contradicciones:
            lineas.append("Contradicciones detectadas:")
            lineas += [f"  ! {c}" for c in self.contradicciones]
        if self.listo:
            lineas.append("Sin contradicciones ni huecos: el encargo esta cerrado.")
        return "\n".join(lineas)


#: Los campos que, vacíos, conviene enseñar al Autor. Los demás tienen valor por defecto o
#: los rellena el arquitecto, así que su ausencia no es un hueco.
OPCIONALES_QUE_IMPORTAN: tuple[tuple[str, str], ...] = (
    ("evento_ancla", "el acontecimiento del que cuelga la novela"),
    ("subgenero", "el subgenero"),
    ("punto_de_vista", "el punto de vista (por defecto lo fija el arquitecto)"),
)


def construir(brief: Brief, contradicciones: list[str]) -> InformeDeIntake:
    vacios = tuple(
        descripcion
        for campo, descripcion in OPCIONALES_QUE_IMPORTAN
        if not getattr(brief, campo, None)
    )
    return InformeDeIntake(
        nombre_homenajeado=brief.nombre_homenajeado,
        periodo=f"{brief.periodo.denominacion} ({brief.periodo.inicio}-{brief.periodo.fin})",
        lugar=brief.lugar,
        obligatorios=tuple(e.valor for e in brief.obligatorios),
        contradicciones=tuple(contradicciones),
        campos_vacios=vacios,
    )
