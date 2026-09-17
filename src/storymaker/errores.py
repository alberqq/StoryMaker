"""Taxonomia de errores (Tecnica 2.0, seccion 10).

Ocho familias. `reintentable` significa que el mismo trabajo puede repetirse sin
intervencion, no que se repita siempre.

Dos reglas transversales que el resto del nucleo debe respetar:

1. Ningun error se traga: todo error anexa un evento al ledger con su codigo
   antes de aplicar la accion. Lo impone `ledger.Ledger.registrar_error`.
2. Ninguna credencial aparece jamas en un artefacto persistido. Lo impone
   `redactar_secretos`, que se aplica a todo detalle antes de serializarlo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

FAMILIA_ENTRADA = "entrada"
FAMILIA_PROVEEDOR = "proveedor"
FAMILIA_ESQUEMA = "esquema"
FAMILIA_PRESUPUESTO = "presupuesto"
FAMILIA_ESTADO = "estado"
FAMILIA_CONTRADICCION = "contradiccion"
FAMILIA_EVALUACION = "evaluacion"
FAMILIA_ENTREGA = "entrega"


@dataclass(frozen=True)
class DefinicionError:
    codigo: str
    familia: str
    condicion: str
    reintentable: bool
    accion: str


def _d(codigo, familia, condicion, reintentable, accion):
    return DefinicionError(codigo, familia, condicion, reintentable, accion)


CATALOGO: dict[str, DefinicionError] = {
    d.codigo: d
    for d in [
        # --- Entrada -------------------------------------------------------
        _d("ERR-101", FAMILIA_ENTRADA, "Semilla vacia", False,
           "Volver a preguntar"),
        _d("ERR-102", FAMILIA_ENTRADA, "Campo obligatorio sin valor ni marca de sin_preferencia", False,
           "Reabrir el bucle de entrada"),
        _d("ERR-103", FAMILIA_ENTRADA, "Incompatibilidad interna del Encargo", False,
           "Elevar al Autor; no se resuelve en silencio (RF-007)"),
        _d("ERR-104", FAMILIA_ENTRADA, "Epoca no acotable a un rango", False,
           "Reabrir el bucle de entrada"),
        _d("ERR-105", FAMILIA_ENTRADA, "Campo desconocido en fichero de Encargo o en configuracion", False,
           "Rechazar nombrando el campo (RF-110)"),
        # --- Proveedor -----------------------------------------------------
        _d("ERR-201", FAMILIA_PROVEEDOR, "Tiempo de espera agotado", True,
           "Reintentar con retroceso"),
        _d("ERR-202", FAMILIA_PROVEEDOR, "Limite de tasa", True,
           "Reintentar con retroceso"),
        _d("ERR-203", FAMILIA_PROVEEDOR, "Error del servidor", True,
           "Reintentar con retroceso"),
        _d("ERR-204", FAMILIA_PROVEEDOR, "Modelo no disponible", True,
           "Degradar al modelo alternativo declarado"),
        _d("ERR-205", FAMILIA_PROVEEDOR, "Credencial invalida", False,
           "Escalar. Nunca se registra el valor de la credencial"),
        _d("ERR-206", FAMILIA_PROVEEDOR, "Contexto excedido: el manifiesto no cabe en la ventana", False,
           "Aplicar la prelacion declarada y dejar constancia de lo excluido"),
        _d("ERR-207", FAMILIA_PROVEEDOR, "Respuesta truncada", True,
           "Reintentar"),
        _d("ERR-208", FAMILIA_PROVEEDOR, "Filtro de contenido", False,
           "Escalar"),
        # --- Esquema -------------------------------------------------------
        _d("ERR-301", FAMILIA_ESQUEMA, "Salida no parseable", True,
           "Reparacion de nivel 1"),
        _d("ERR-302", FAMILIA_ESQUEMA, "Esquema incumplido", True,
           "Reparacion de nivel 2"),
        _d("ERR-303", FAMILIA_ESQUEMA, "Reparacion agotada", False,
           "Abortar la unidad y contar la iteracion"),
        _d("ERR-304", FAMILIA_ESQUEMA, "Referencia a identificador inexistente", False,
           "Rechazar la propuesta"),
        # --- Presupuesto ---------------------------------------------------
        _d("ERR-401", FAMILIA_PRESUPUESTO, "Iteraciones agotadas", False,
           "Politica de agotamiento del bucle correspondiente"),
        _d("ERR-402", FAMILIA_PRESUPUESTO, "Coste agotado", False,
           "Politica de agotamiento del bucle correspondiente"),
        _d("ERR-403", FAMILIA_PRESUPUESTO, "Tiempo agotado", False,
           "Politica de agotamiento del bucle correspondiente"),
        _d("ERR-404", FAMILIA_PRESUPUESTO, "Admision denegada: la estimacion supera el remanente", False,
           "Cerrar ordenadamente sin despachar la unidad"),
        _d("ERR-405", FAMILIA_PRESUPUESTO, "Tope de solicitudes de investigacion alcanzado", False,
           "Declarar laguna"),
        _d("ERR-406", FAMILIA_PRESUPUESTO, "Tramo libre de la reserva agotado", False,
           "Elevar al Autor"),
        _d("ERR-407", FAMILIA_PRESUPUESTO, "Tramo final solicitado antes del ultimo tercio", False,
           "Denegar: es una reserva, no un prestamo (D24)"),
        # --- Estado --------------------------------------------------------
        _d("ERR-501", FAMILIA_ESTADO, "Proyecto bloqueado por otro proceso", False,
           "Abortar: escritor unico (ADR-04)"),
        _d("ERR-502", FAMILIA_ESTADO, "Escritura sobre Canon no aprobado", False,
           "Rechazar la operacion (INV-1)"),
        _d("ERR-503", FAMILIA_ESTADO, "Linea truncada en un fichero de solo anexion", True,
           "Descartar la linea y rehacer el trabajo posterior a ella"),
        _d("ERR-504", FAMILIA_ESTADO, "Indice inconsistente", True,
           "Reconstruir el indice por barrido completo"),
        _d("ERR-505", FAMILIA_ESTADO, "Esquema sin promotor registrado", False,
           "No arrancar: se prefiere no arrancar a leer mal"),
        _d("ERR-506", FAMILIA_ESTADO, "Escena vigente inexistente al ensamblar", False,
           "Abortar el ensamblado"),
        # --- Contradiccion y recuperacion ----------------------------------
        _d("ERR-601", FAMILIA_CONTRADICCION, "Hecho que contradice un hecho establecido", False,
           "Hallazgo bloqueante de continuidad con causa raiz en la redaccion"),
        _d("ERR-602", FAMILIA_CONTRADICCION, "Escena irrealizable como esta planificada", False,
           "Hallazgo contra el Canon; nunca improvisar"),
        _d("ERR-603", FAMILIA_CONTRADICCION, "Replanificacion que invalida capitulos validados", False,
           "Elevar a PC-4 con el inventario de invalidados"),
        _d("ERR-604", FAMILIA_CONTRADICCION, "Modificacion del Canon sin versionar", False,
           "Rechazar la operacion (INV-6)"),
        _d("ERR-605", FAMILIA_CONTRADICCION, "La Fuente no sostiene la afirmacion que se le atribuye", False,
           "Hallazgo bloqueante con causa raiz en investigacion (RF-100)"),
        _d("ERR-606", FAMILIA_CONTRADICCION, "Afirmacion refutada o no verificada que pretende sostener una Restriccion", False,
           "Rechazar la derivacion (MD-7)"),
        _d("ERR-607", FAMILIA_CONTRADICCION, "Contenido de la Fuente no conservable", False,
           "Declarar por que no pudo conservarse (RF-101)"),
        _d("ERR-608", FAMILIA_CONTRADICCION, "Refutacion sin fuente contraria que la sostenga", False,
           "No se registra: no es una refutacion (RF-102)"),
        # --- Evaluacion ----------------------------------------------------
        _d("ERR-701", FAMILIA_EVALUACION, "Hallazgos bloqueantes abiertos al cerrar la unidad", False,
           "Iterar mientras haya presupuesto (INV-5)"),
        _d("ERR-702", FAMILIA_EVALUACION, "Estancamiento del bucle", False,
           "Cerrar por T2 y emitir Deuda de calidad"),
        _d("ERR-703", FAMILIA_EVALUACION, "Regresion respecto a la version anterior", False,
           "Cerrar por T3 y revertir a la mejor version"),
        _d("ERR-704", FAMILIA_EVALUACION, "Aprobacion de capitulo sin cambio de texto", False,
           "Rechazar la aprobacion (RF-067)"),
        _d("ERR-705", FAMILIA_EVALUACION, "Bloqueo irresoluble dentro del arnes", False,
           "Escalar T5 a PC-5 sin consumir mas iteraciones"),
        _d("ERR-706", FAMILIA_EVALUACION, "Licencia literaria sin autorizante", False,
           "Rechazar el registro de la licencia"),
        _d("ERR-707", FAMILIA_EVALUACION, "Superficie de texto protegido por encima del umbral", True,
           "Aviso; la pasada global libera las protecciones caducas (RNF-026)"),
        _d("ERR-708", FAMILIA_EVALUACION, "Reescritura de pasaje protegido sin justificacion registrada", False,
           "Denegar la operacion (RF-054)"),
        _d("ERR-709", FAMILIA_EVALUACION, "Canon aprobado con bloqueantes asumidos", False,
           "Registrar la asuncion; el Proyecto queda limitado a finalizado con reservas (D23)"),
        # --- Recuperacion y entrega ----------------------------------------
        _d("ERR-801", FAMILIA_ENTREGA, "Corpus RAG inaccesible", True,
           "Degradar al otro modo y declarar cobertura reducida"),
        _d("ERR-802", FAMILIA_ENTREGA, "Web sin resultados dentro del ambito", False,
           "Declarar laguna"),
        _d("ERR-803", FAMILIA_ENTREGA, "Ambos modos de recuperacion fallan", False,
           "Abortar la etapa: redactar sin contexto contradice OBJ-2"),
        _d("ERR-901", FAMILIA_ENTREGA, "Fuente inaccesible en el momento de entregar", True,
           "Entregar el contenido conservado (RF-101)"),
        _d("ERR-902", FAMILIA_ENTREGA, "PDF fallido o divergencia entre formatos", True,
           "Entregar solo Markdown y declararlo (RNF-025)"),
    ]
}


# El orden importa. Los patrones que reconocen un secreto por su forma propia van
# primero, porque un `Authorization: Bearer <token>` tiene dos partes y el patron
# generico de clave-valor solo se comeria la palabra `Bearer`, dejando el token
# intacto. Y el generico admite el esquema por delante para que, si llega antes,
# se lleve el valor entero y no solo su prefijo.
_PATRONES_SECRETO: list[re.Pattern[str]] = [
    re.compile(r"(?i)\b(Bearer\s+[A-Za-z0-9._-]{8,})"),
    re.compile(r"(?i)\b(Basic\s+[A-Za-z0-9+/=]{8,})"),
    re.compile(r"(?i)\b(sk-[A-Za-z0-9_-]{8,})"),
    re.compile(r"\b(eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})"),
    re.compile(
        r"(?i)((?:api[_-]?key|apikey|token|password|passwd|secret|client[_-]?secret"
        r"|authorization)\s*[=:]\s*)(\"?)((?:Bearer\s+|Basic\s+)?[^\s\"',;]{4,})"
    ),
]

MARCADOR_SECRETO = "<<REDACTADO>>"

_CLAVES_SECRETAS = re.compile(
    r"(?i)(api[_-]?key|apikey|token|password|passwd|secret|credencial|credential|authorization|bearer)"
)


def redactar_secretos(valor: Any) -> Any:
    """Sustituye por un marcador todo lo que parezca una credencial.

    Se aplica antes de persistir cualquier detalle de error y cualquier carga de
    ledger. La regla de la seccion 10 es absoluta: ninguna credencial aparece en
    un artefacto persistido. Se resuelven del entorno en ejecucion y se
    referencian siempre por marcador.
    """
    if isinstance(valor, str):
        texto = valor
        for patron in _PATRONES_SECRETO:
            if patron.groups >= 3:
                texto = patron.sub(lambda m: m.group(1) + m.group(2) + MARCADOR_SECRETO, texto)
            else:
                texto = patron.sub(MARCADOR_SECRETO, texto)
        return texto
    if isinstance(valor, dict):
        # Una clave que se llama `api_key` delata su valor aunque el valor en si
        # no case con ningun patron: se redacta por el nombre.
        return {
            clave: (MARCADOR_SECRETO
                    if isinstance(clave, str) and _CLAVES_SECRETAS.search(clave)
                    else redactar_secretos(sub))
            for clave, sub in valor.items()
        }
    if isinstance(valor, (list, tuple)):
        return [redactar_secretos(sub) for sub in valor]
    return valor


class ErrorStoryMaker(Exception):
    """Error del nucleo, siempre con un codigo del catalogo."""

    def __init__(self, codigo: str, mensaje: str = "", **detalle: Any):
        if codigo not in CATALOGO:
            raise KeyError(f"codigo de error fuera del catalogo: {codigo}")
        self.definicion = CATALOGO[codigo]
        self.codigo = codigo
        self.mensaje = mensaje or self.definicion.condicion
        self.detalle: dict[str, Any] = redactar_secretos(detalle)
        super().__init__(f"{codigo}: {self.mensaje}")

    @property
    def familia(self) -> str:
        return self.definicion.familia

    @property
    def reintentable(self) -> bool:
        return self.definicion.reintentable

    def como_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "familia": self.familia,
            "mensaje": redactar_secretos(self.mensaje),
            "reintentable": self.reintentable,
            "accion": self.definicion.accion,
            "detalle": self.detalle,
        }
