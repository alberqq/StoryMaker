"""Hallazgos: severidad, causa raiz, enrutado y ciclo de vida (RF-064 a RF-066).

La forma canonica de un hallazgo tiene cinco piezas y ninguna es opcional:
severidad, causa raiz, localizacion, accion exigida y evidencia. Una critica sin
pasaje identificable no es un hallazgo: es una opinion, y por eso nace menor.

La identidad del hallazgo la calcula `ids.id_hallazgo` y excluye deliberadamente
el enunciado y los desplazamientos de caracter. Aqui se depende de esa estabilidad
para detectar reapariciones (RF-075).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from storymaker import SCHEMA_VERSION
from storymaker.ids import id_hallazgo
from storymaker.sobre import ahora

BLOQUEANTE = "bloqueante"
MAYOR = "mayor"
MENOR = "menor"

SEVERIDADES = (BLOQUEANTE, MAYOR, MENOR)

# Peso por severidad para comparar conjuntos de hallazgos entre iteraciones. Es
# lo que hace medible el estancamiento de RF-075: sin ponderacion, cambiar un
# bloqueante por tres menores pareceria un empeoramiento.
PESO = {BLOQUEANTE: 100, MAYOR: 10, MENOR: 1}

CAUSAS_RAIZ = ("entrada", "investigacion", "diseno", "redaccion", "refinamiento")

# Categorias que merecen severidad bloqueante por definicion (Funcional 11.2).
CATEGORIAS_BLOQUEANTES = (
    "anacronismo",
    "contradiccion_canon",
    "contradiccion_continuidad",
    "revelacion_anticipada",
    "hilo_sin_avanzar",
    "afirmacion_sin_respaldo",
)

CATEGORIAS_MAYORES = (
    "voz_de_personaje",
    "funcion_narrativa_incompleta",
    "desviacion_estilo_declarado",
    "extension_fuera_de_tolerancia",
)

ABIERTO = "abierto"
EN_CORRECCION = "en_correccion"
RESUELTO = "resuelto"
ACEPTADO_COMO_DEUDA = "aceptado_como_deuda"
DESCARTADO = "descartado"

ESTADOS = (ABIERTO, EN_CORRECCION, RESUELTO, ACEPTADO_COMO_DEUDA, DESCARTADO)


@dataclass
class Hallazgo:
    unidad: str
    categoria: str
    elemento_senalado: str
    severidad: str
    causa_raiz: str
    descripcion: str
    accion_exigida: str
    evidencia: str = ""
    localizacion: dict[str, Any] = field(default_factory=dict)
    estado: str = ABIERTO
    iteracion: int = 1
    etapa_destino: str = "redaccion"
    id: str = ""
    creado_en: str = field(default_factory=ahora)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.id:
            self.id = id_hallazgo(self.unidad, self.categoria, self.elemento_senalado)
        if self.severidad not in SEVERIDADES:
            raise ValueError(f"severidad desconocida: {self.severidad}")
        if self.causa_raiz not in CAUSAS_RAIZ:
            raise ValueError(f"causa raiz desconocida: {self.causa_raiz}")

    @property
    def peso(self) -> int:
        return PESO[self.severidad]

    @property
    def fuerza_iteracion(self) -> bool:
        """Solo bloqueantes y mayores fuerzan iteracion (RF-064).

        Los menores se acumulan; su acumulacion por encima del umbral eleva un
        mayor agregado, que es lo que impide que una critica infinita sobre
        cuestiones menores mantenga vivo un bucle para siempre.
        """
        return self.severidad in (BLOQUEANTE, MAYOR)

    def como_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "unidad": self.unidad,
            "categoria": self.categoria,
            "elemento_senalado": self.elemento_senalado,
            "severidad": self.severidad,
            "causa_raiz": self.causa_raiz,
            "etapa_destino": self.etapa_destino,
            "descripcion": self.descripcion,
            "accion_exigida": self.accion_exigida,
            "evidencia": self.evidencia,
            "localizacion": self.localizacion,
            "estado": self.estado,
            "iteracion": self.iteracion,
            "creado_en": self.creado_en,
        }

    @classmethod
    def desde_dict(cls, dato: dict[str, Any]) -> "Hallazgo":
        return cls(
            unidad=dato["unidad"],
            categoria=dato["categoria"],
            elemento_senalado=dato.get("elemento_senalado", ""),
            severidad=dato["severidad"],
            causa_raiz=dato.get("causa_raiz", "redaccion"),
            descripcion=dato.get("descripcion", ""),
            accion_exigida=dato.get("accion_exigida", ""),
            evidencia=dato.get("evidencia", ""),
            localizacion=dato.get("localizacion", {}),
            estado=dato.get("estado", ABIERTO),
            iteracion=dato.get("iteracion", 1),
            etapa_destino=dato.get("etapa_destino", "redaccion"),
            id=dato.get("id", ""),
            creado_en=dato.get("creado_en", ahora()),
            schema_version=dato.get("schema_version", SCHEMA_VERSION),
        )


def severidad_canonica(categoria: str, propuesta: str) -> str:
    """Impone la escala de la Funcional 11.2 sobre lo que proponga un agente.

    Un agente puede proponer severidad, pero no rebajarla: un anacronismo es
    bloqueante lo llame como lo llame quien lo encontro. Al reves si se admite
    -- se puede elevar -- porque elevar nunca relaja una puerta.
    """
    if categoria in CATEGORIAS_BLOQUEANTES:
        return BLOQUEANTE
    if categoria in CATEGORIAS_MAYORES and propuesta == MENOR:
        return MAYOR
    return propuesta if propuesta in SEVERIDADES else MENOR


def enrutar(causa_raiz: str) -> str:
    """RF-065: cada hallazgo a su etapa responsable, con la redaccion por defecto."""
    return {
        "entrada": "E1",
        "investigacion": "E2",
        "diseno": "E3",
        "redaccion": "E5",
        "refinamiento": "E6",
    }.get(causa_raiz, "E5")


def peso_total(hallazgos: Iterable[Hallazgo]) -> int:
    return sum(h.peso for h in hallazgos if h.estado in (ABIERTO, EN_CORRECCION))


def abiertos(hallazgos: Iterable[Hallazgo], severidad: str | None = None) -> list[Hallazgo]:
    seleccion = [h for h in hallazgos if h.estado in (ABIERTO, EN_CORRECCION)]
    if severidad:
        seleccion = [h for h in seleccion if h.severidad == severidad]
    return seleccion


def recuento_por_severidad(hallazgos: Iterable[Hallazgo]) -> dict[str, int]:
    recuento = {severidad: 0 for severidad in SEVERIDADES}
    for hallazgo in abiertos(hallazgos):
        recuento[hallazgo.severidad] += 1
    return recuento


def elevar_menores_acumulados(
    hallazgos: list[Hallazgo], unidad: str, umbral: int
) -> Hallazgo | None:
    """La acumulacion de menores por encima del umbral eleva un mayor agregado.

    Es la valvula que da sentido a que un menor no fuerce iteracion: no la fuerza
    uno, pero doce si, porque doce menores ya no son ruido.
    """
    menores = abiertos(hallazgos, MENOR)
    if len(menores) < umbral:
        return None
    return Hallazgo(
        unidad=unidad,
        categoria="acumulacion_de_menores",
        elemento_senalado=unidad,
        severidad=MAYOR,
        causa_raiz="refinamiento",
        descripcion=(
            f"Se acumulan {len(menores)} hallazgos menores abiertos en la unidad, por "
            f"encima del umbral de {umbral}."
        ),
        accion_exigida="Atender el conjunto de menores antes de cerrar la unidad",
        evidencia=", ".join(sorted(h.id for h in menores)),
    )


def reaparecidos(actuales: Iterable[Hallazgo], resueltos_previos: Iterable[str]) -> list[str]:
    """Hallazgos ya resueltos que vuelven a aparecer (RF-075).

    Esto es lo que hace de la identidad estable del hallazgo una pieza critica: si
    el identificador cambiara al reescribirse el parrafo, el estancamiento no se
    detectaria jamas.
    """
    previos = set(resueltos_previos)
    return sorted({h.id for h in abiertos(actuales)} & previos)
