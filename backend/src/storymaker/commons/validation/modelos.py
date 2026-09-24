"""spec: §3.6 · arq: §11a, §15

Los tipos del Core Domain: lo que un validador recibe y lo que devuelve.

Todo es **dato plano**. Ningún validador ve una conexión, un cursor ni una fila de
SQLite, y eso no es purismo: es lo que permite que la misma implementación corra como nodo
del grafo y como hook de `.claude/` cuando una persona edita un capítulo a mano. Si los
validadores tomaran una conexión, el hook tendría que abrir la novela para comprobar un
fichero suelto, y la segunda puerta dejaría de poder abrirse.

Quien traduce filas a estos tipos es la capa que llama, no el validador.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Severidad(StrEnum):
    """Bloqueante vuelve al editor; aviso viaja al encargo del capítulo siguiente."""

    BLOQUEANTE = "bloqueante"
    AVISO = "aviso"


@dataclass(frozen=True)
class Incidencia:
    """Un defecto del contenido, con camino de vuelta.

    No es un error: un error es una avería y detiene la invocación. Confundirlos aprobaría
    capítulos por avería, que es el fallo más caro que este sistema puede tener.
    """

    validador: str
    severidad: Severidad
    mensaje: str
    ubicacion: str | None = None
    propuesta: str | None = None

    @property
    def bloquea(self) -> bool:
        return self.severidad is Severidad.BLOQUEANTE


@dataclass(frozen=True)
class TerminoProhibido:
    """Un término vetado, con su nivel y su forma normalizada."""

    nivel: str
    termino: str
    normalizado: str


@dataclass(frozen=True)
class EntidadFechada:
    """Algo que existe entre dos fechas: un objeto, un término, un personaje histórico.

    Sus dos fechas son las que alimentan el detector de anacronismos y el cuarto invariante
    de Lean, que es el caso demostrativo: un personaje en escena tres años después de su
    muerte documentada le parece natural a un modelo, que no tiene aritmética temporal.
    """

    nombre: str
    fecha_inicio: str | None = None
    fecha_fin: str | None = None


@dataclass(frozen=True)
class AnclajeDeEscena:
    """Un anclaje de la escaleta, tal como el validador necesita verlo."""

    escena_id: int
    hecho_id: int | None = None
    entidad_id: int | None = None
    dato_id: int | None = None


@dataclass(frozen=True)
class CapituloEnRevision:
    """Todo lo que hace falta para juzgar un capítulo, ya extraído de la base.

    Es deliberadamente explícito: que el validador reciba los nombres canónicos y los
    términos prohibidos en lugar de ir a buscarlos es lo que lo hace ejecutable desde un
    hook, desde una prueba y desde el grafo sin cambiar una línea.
    """

    numero: int
    texto: str
    palabras: int
    rango_palabras: tuple[int, int]
    nombres_canonicos: tuple[str, ...] = ()
    prohibidas: tuple[TerminoProhibido, ...] = ()
    entidades_fechadas: tuple[EntidadFechada, ...] = ()
    fecha_narrativa: str | None = None
    anclajes: tuple[AnclajeDeEscena, ...] = ()
    hechos_sellados: frozenset[int] = frozenset()
    licencias_declaradas: frozenset[int] = frozenset()
    #: Elementos obligatorios que la escaleta encomendó a este capítulo.
    personalizacion_encomendada: tuple[int, ...] = ()
    #: Los que el extractor dice haber encontrado en el texto.
    personalizacion_usada: frozenset[int] = frozenset()
    #: El texto de cada elemento encomendado, por identificador. Es lo que la incidencia
    #: enseña: con el número solo, el editor no sabe qué falta.
    personalizacion_textos: tuple[tuple[int, str], ...] = ()


@dataclass(frozen=True)
class ArcoEnRevision:
    """Un arco con sus hitos, para el validador del gate de Plotting."""

    personaje_id: int
    personaje: str
    tipo: str
    hitos_por_capitulo: tuple[int, ...] = ()
    es_homenajeado: bool = False


@dataclass(frozen=True)
class EscaletaEnRevision:
    """La escaleta entera, vista por los dos validadores del gate de Plotting."""

    n_capitulos: int
    apariciones_por_personaje: dict[int, int] = field(default_factory=dict)
    nombres_por_personaje: dict[int, str] = field(default_factory=dict)
    arcos: tuple[ArcoEnRevision, ...] = ()
    obligatorios: tuple[int, ...] = ()
    obligatorios_anclados: frozenset[int] = frozenset()
