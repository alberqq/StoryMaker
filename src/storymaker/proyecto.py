"""El Proyecto: instantanea mutable y punto de entrada del nucleo.

`proyecto.json` es la unica instantanea mutable del arbol. Su historia no vive en
el fichero -- se sobrescribe -- sino en el ledger, que es de solo anexion. Esa
asimetria es deliberada: el fichero responde "como esta esto ahora" barato, y el
ledger responde "como llego a estarlo" sin ambiguedad.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from storymaker import SCHEMA_VERSION
from storymaker.almacen import Almacen
from storymaker.errores import ErrorStoryMaker
from storymaker.ids import id_proyecto
from storymaker.sobre import ahora

# Ciclo de vida del Proyecto (Funcional 6.1).
CREADO = "creado"
EN_ENCARGO = "en_encargo"
EN_INVESTIGACION = "en_investigacion"
EN_DISENO = "en_diseno"
EN_PRODUCCION = "en_produccion"
FINALIZADO = "finalizado"
FINALIZADO_CON_RESERVAS = "finalizado_con_reservas"
ABANDONADO = "abandonado"

ESTADOS_PROYECTO = (
    CREADO, EN_ENCARGO, EN_INVESTIGACION, EN_DISENO, EN_PRODUCCION,
    FINALIZADO, FINALIZADO_CON_RESERVAS, ABANDONADO,
)

# Estados de la maquina de la seccion 7.2, que es la de la Ejecucion y no la del
# Proyecto. Se declaran aqui porque el Proyecto guarda el ultimo conocido.
ETAPAS = (
    "Encargo", "Investigacion", "Refutacion", "Diseno", "ValidacionCanon",
    "Produccion", "PasadaGlobal", "Entrega", "Detenida",
)

# El unico modo de operacion. Hubo tres mas --- asistido, autonomo supervisado y
# autonomo --- que se distinguian por quien resolvia los puntos de control y por
# si la Ejecucion se detenia a esperar. Se retiraron porque ninguno se usaba: el
# Autor revisa en persona el Contexto historico y el Canon, y ese es el flujo.
#
# La constante se conserva en lugar de disolverse en una cadena suelta porque el
# estado del Proyecto la persiste y el dia que vuelva a haber mas de uno, el sitio
# donde anadirlos es este.
MODO_REVISION_DEL_AUTOR = "revision_del_autor"

MODOS = (MODO_REVISION_DEL_AUTOR,)


@dataclass
class EstadoProyecto:
    id: str
    titulo_provisional: str
    estado: str = CREADO
    etapa: str = "Encargo"
    creado_en: str = field(default_factory=ahora)
    actualizado_en: str = field(default_factory=ahora)
    modo: str = MODO_REVISION_DEL_AUTOR
    encargo_version_vigente: str | None = None
    contexto_version_vigente: str | None = None
    canon_version_vigente: str | None = None
    canon_estado: str | None = None
    ejecucion_activa: str | None = None
    # D23: si el Canon se aprobo con bloqueantes asumidos por una persona, el
    # Proyecto ya no puede alcanzar *finalizado*, solo *finalizado con reservas*.
    limitado_a_reservas: bool = False
    motivo_reservas: list[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    def como_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "titulo_provisional": self.titulo_provisional,
            "estado": self.estado,
            "etapa": self.etapa,
            "creado_en": self.creado_en,
            "actualizado_en": self.actualizado_en,
            "modo": self.modo,
            "encargo_version_vigente": self.encargo_version_vigente,
            "contexto_version_vigente": self.contexto_version_vigente,
            "canon_version_vigente": self.canon_version_vigente,
            "canon_estado": self.canon_estado,
            "ejecucion_activa": self.ejecucion_activa,
            "limitado_a_reservas": self.limitado_a_reservas,
            "motivo_reservas": self.motivo_reservas,
        }

    @classmethod
    def desde_dict(cls, dato: dict[str, Any]) -> "EstadoProyecto":
        campos = {
            clave: dato[clave]
            for clave in cls.__dataclass_fields__
            if clave in dato
        }
        return cls(**campos)


class Proyecto:
    """Fachada del nucleo sobre un Proyecto concreto."""

    def __init__(self, raiz_proyectos: Path | str, identificador: str):
        self.almacen = Almacen(raiz_proyectos, identificador)
        if not self.almacen.existe():
            raise ErrorStoryMaker(
                "ERR-304",
                f"No existe el Proyecto {identificador}",
                proyecto=identificador,
                raiz=str(raiz_proyectos),
            )
        self.estado = EstadoProyecto.desde_dict(
            self.almacen.leer_json(self.almacen.fichero_proyecto)
        )

    # -- creacion ----------------------------------------------------------

    @staticmethod
    def crear(
        raiz_proyectos: Path | str,
        titulo_provisional: str,
        modo: str = MODO_REVISION_DEL_AUTOR,
        identificador: str | None = None,
    ) -> "Proyecto":
        if modo not in MODOS:
            raise ErrorStoryMaker(
                "ERR-105",
                f"Modo de operacion desconocido: {modo!r}. El unico es {MODOS[0]}.",
                campo="modo",
            )
        identificador = identificador or id_proyecto()
        almacen = Almacen(raiz_proyectos, identificador)
        if almacen.existe():
            raise ErrorStoryMaker(
                "ERR-501", f"El Proyecto {identificador} ya existe", proyecto=identificador
            )
        almacen.crear_arbol()
        estado = EstadoProyecto(
            id=identificador, titulo_provisional=titulo_provisional, modo=modo
        )
        almacen.escribir_json(almacen.fichero_proyecto, estado.como_dict())
        almacen.escribir_json(almacen.ramas, {"principal": {}, "alternativas": {}})
        return Proyecto(raiz_proyectos, identificador)

    # -- persistencia del estado -------------------------------------------

    def guardar(self, **cambios: Any) -> EstadoProyecto:
        for clave, valor in cambios.items():
            if not hasattr(self.estado, clave):
                raise ErrorStoryMaker(
                    "ERR-105", f"Campo desconocido del estado de Proyecto: {clave}", campo=clave
                )
            setattr(self.estado, clave, valor)
        self.estado.actualizado_en = ahora()
        self.almacen.escribir_json(self.almacen.fichero_proyecto, self.estado.como_dict())
        return self.estado

    def limitar_a_reservas(self, motivo: str) -> None:
        """Marca el Proyecto como incapaz de alcanzar *finalizado* a secas.

        Es irreversible dentro de la Ejecucion: una vez que alguien aprobo algo
        con bloqueantes abiertos, la novela ya se entrega con reservas por mucho
        que despues todo converja.
        """
        motivos = list(self.estado.motivo_reservas)
        if motivo not in motivos:
            motivos.append(motivo)
        self.guardar(limitado_a_reservas=True, motivo_reservas=motivos)

    # -- lecturas de conveniencia ------------------------------------------

    def encargo(self) -> dict[str, Any] | None:
        if not self.estado.encargo_version_vigente:
            return None
        return self.almacen.leer_json(self.almacen.encargo(self.estado.encargo_version_vigente))

    def contexto_cabecera(self) -> dict[str, Any] | None:
        if not self.estado.contexto_version_vigente:
            return None
        return self.almacen.leer_json(self.almacen.contexto(self.estado.contexto_version_vigente))

    def plan_canon(self, version: str | None = None) -> dict[str, Any] | None:
        version = version or self.estado.canon_version_vigente
        if not version:
            return None
        return self.almacen.leer_json(self.almacen.plan_canon(version))

    def ramas(self) -> dict[str, Any]:
        return self.almacen.leer_json(self.almacen.ramas, {"principal": {}, "alternativas": {}})

    def exigir_canon_aprobado(self) -> dict[str, Any]:
        """INV-1: ningun texto se redacta sobre un Canon no aprobado.

        Esta es la comprobacion del nucleo. El hook `guard-canon` la repite antes
        de que la llamada exista. La redundancia es deliberada: el hook protege de
        un agente descaminado, esto protege de un error en el hook.
        """
        if self.estado.canon_estado != "aprobado" or not self.estado.canon_version_vigente:
            raise ErrorStoryMaker(
                "ERR-502",
                "No se redacta sobre un Canon que no esta aprobado",
                canon_estado=self.estado.canon_estado,
                canon_version=self.estado.canon_version_vigente,
            )
        plan = self.plan_canon()
        if plan is None:
            raise ErrorStoryMaker(
                "ERR-304",
                "El Proyecto apunta a una version de Canon que no existe en el almacen",
                version=self.estado.canon_version_vigente,
            )
        return plan

    def siguiente_version(self, prefijo: str) -> int:
        """Numero de la proxima version de Encargo, Contexto o plan de Canon."""
        carpeta = {
            "enc": self.almacen.raiz / "encargo",
            "ctx": self.almacen.raiz / "contexto",
            "can": self.almacen.raiz / "canon" / "plan",
        }[prefijo]
        if not carpeta.exists():
            return 1
        numeros = []
        for fichero in carpeta.glob(f"{prefijo}_*.json"):
            marca = fichero.stem.rsplit("_v", 1)
            if len(marca) == 2 and marca[1].isdigit():
                numeros.append(int(marca[1]))
        return max(numeros, default=0) + 1
