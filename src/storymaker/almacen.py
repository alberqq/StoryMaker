"""El almacen de ficheros (ADR-03) y el protocolo de escritura (ADR-04).

No hay motor de base de datos y no hay transacciones entre ficheros. En su lugar,
cuatro reglas, y ninguna es negociable:

1. **Escritor unico.** El nucleo toma un cerrojo de Proyecto. Un segundo proceso
   falla con ERR-501.
2. **Escritura atomica por fichero.** Escribir a `<destino>.tmp`, sincronizar,
   renombrar. El renombrado en el mismo volumen es atomico.
3. **Anexion de linea completa.** Los `.jsonl` se abren en modo anexion, se
   escribe una linea terminada y se sincroniza. Una linea truncada por un corte
   se descarta al leer, se registra ERR-503 y se rehace el trabajo posterior.
4. **Orden canonico de persistencia.** Blob, ledger, artefacto, indice, puntero.
   Siempre en ese orden. Una caida deja como mucho un blob huerfano, que es
   inocuo, o un artefacto sin puntero, que es invisible y se rehace. Nunca un
   puntero a algo que no existe.

Consecuencia asumida: no hay vuelta atras, solo compensacion por anexion. El
libro mayor crece de forma monotona, y esa es la propiedad que lo hace auditable.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from storymaker.errores import ErrorStoryMaker
from storymaker.ids import sha256_bytes, sha256_texto

# El orden canonico de la regla 4, declarado como dato para que las pruebas de
# recuperacion puedan recorrerlo paso a paso.
ORDEN_CANONICO = ("blob", "ledger", "artefacto", "indice", "puntero")


def _escribir_atomico(destino: Path, datos: bytes) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporal = tempfile.mkstemp(dir=str(destino.parent), suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as mango:
            mango.write(datos)
            mango.flush()
            os.fsync(mango.fileno())
        os.replace(temporal, destino)
    except BaseException:
        Path(temporal).unlink(missing_ok=True)
        raise


def json_canonico(dato: Any) -> str:
    """Serializacion estable: mismo dato, mismos bytes, mismo hash."""
    return json.dumps(dato, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass
class LineaDescartada:
    numero: int
    motivo: str
    contenido_bruto: str


class Almacen:
    """Acceso a todo el arbol de un Proyecto.

    Es el unico sitio del nucleo que abre ficheros de estado en modo escritura.
    Fuera de aqui no hay `open(..., "w")` sobre `proyectos/`.
    """

    def __init__(self, raiz_proyectos: Path | str, id_proyecto: str):
        self.raiz_proyectos = Path(raiz_proyectos)
        self.id_proyecto = id_proyecto
        self.raiz = self.raiz_proyectos / id_proyecto
        self.lineas_descartadas: list[LineaDescartada] = []

    # -- rutas del arbol de la seccion 5.1 ---------------------------------

    @property
    def fichero_proyecto(self) -> Path:
        return self.raiz / "proyecto.json"

    def encargo(self, version: str) -> Path:
        return self.raiz / "encargo" / f"{version}.json"

    def contexto(self, version: str) -> Path:
        return self.raiz / "contexto" / f"{version}.json"

    @property
    def afirmaciones(self) -> Path:
        return self.raiz / "contexto" / "afirmaciones.jsonl"

    @property
    def fuentes(self) -> Path:
        return self.raiz / "contexto" / "fuentes.jsonl"

    @property
    def refutaciones(self) -> Path:
        return self.raiz / "contexto" / "refutaciones.jsonl"

    @property
    def restricciones(self) -> Path:
        return self.raiz / "contexto" / "restricciones.jsonl"

    def figura_real(self, id_figura: str) -> Path:
        return self.raiz / "contexto" / "figuras_reales" / f"{id_figura}.json"

    def plan_canon(self, version: str) -> Path:
        return self.raiz / "canon" / "plan" / f"{version}.json"

    @property
    def hechos(self) -> Path:
        return self.raiz / "canon" / "hechos.jsonl"

    def texto_escena(self, id_escena: str, id_version: str) -> Path:
        return self.raiz / "novela" / "escenas" / id_escena / f"{id_version}.md"

    def meta_escena(self, id_escena: str, id_version: str) -> Path:
        return self.raiz / "novela" / "escenas" / id_escena / f"{id_version}.json"

    def sinopsis(self, id_capitulo: str) -> Path:
        return self.raiz / "novela" / "sinopsis" / f"{id_capitulo}.md"

    @property
    def ramas(self) -> Path:
        return self.raiz / "novela" / "ramas.json"

    @property
    def hallazgos(self) -> Path:
        return self.raiz / "hallazgos.jsonl"

    @property
    def licencias(self) -> Path:
        return self.raiz / "licencias.jsonl"

    @property
    def deudas(self) -> Path:
        return self.raiz / "deudas.jsonl"

    def ejecucion(self, id_ejecucion: str) -> Path:
        return self.raiz / "ejecuciones" / id_ejecucion

    def fichero_ejecucion(self, id_ejecucion: str) -> Path:
        return self.ejecucion(id_ejecucion) / "ejecucion.json"

    def ledger(self, id_ejecucion: str) -> Path:
        return self.ejecucion(id_ejecucion) / "ledger.jsonl"

    def unidades(self, id_ejecucion: str) -> Path:
        return self.ejecucion(id_ejecucion) / "unidades.jsonl"

    def consumo(self, id_ejecucion: str) -> Path:
        return self.ejecucion(id_ejecucion) / "consumo.jsonl"

    def punto_control(self, id_ejecucion: str, id_punto: str) -> Path:
        return self.ejecucion(id_ejecucion) / "puntos_control" / f"{id_punto}.json"

    def contenido_fuente(self, sha256: str) -> Path:
        return self.raiz / "fuentes" / sha256[:2] / sha256

    def blob(self, sha256: str) -> Path:
        return self.raiz / "blobs" / sha256[:2] / sha256

    def tmp(self, id_unidad: str) -> Path:
        return self.raiz / "tmp" / id_unidad

    @property
    def indices(self) -> Path:
        return self.raiz / "indices"

    @property
    def entrega(self) -> Path:
        return self.raiz / "entrega"

    # -- regla 2: escritura atomica por fichero ----------------------------

    def escribir_json(self, ruta: Path, dato: Any) -> Path:
        _escribir_atomico(ruta, (json_canonico(dato) + "\n").encode("utf-8"))
        return ruta

    def escribir_texto(self, ruta: Path, texto: str) -> Path:
        _escribir_atomico(ruta, texto.encode("utf-8"))
        return ruta

    def leer_json(self, ruta: Path, por_defecto: Any = None) -> Any:
        if not ruta.exists():
            return por_defecto
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))
        except json.JSONDecodeError as fallo:
            raise ErrorStoryMaker(
                "ERR-503",
                f"Fichero JSON ilegible: {ruta.name}",
                ruta=str(ruta),
                detalle_json=str(fallo),
            ) from fallo

    def leer_texto(self, ruta: Path, por_defecto: str | None = None) -> str | None:
        if not ruta.exists():
            return por_defecto
        return ruta.read_text(encoding="utf-8")

    # -- regla 3: anexion de linea completa --------------------------------

    def anexar(self, ruta: Path, registro: dict[str, Any]) -> dict[str, Any]:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        linea = json_canonico(registro) + "\n"
        with open(ruta, "a", encoding="utf-8", newline="\n") as mango:
            mango.write(linea)
            mango.flush()
            os.fsync(mango.fileno())
        return registro

    def leer_jsonl(self, ruta: Path) -> list[dict[str, Any]]:
        """Lee un libro de solo anexion descartando la ultima linea si esta truncada.

        Una linea truncada por un corte de corriente no es un error del que haya
        que morir: es la evidencia de una unidad que no llego a cerrarse. Se
        descarta, se anota, y el trabajo posterior a ella se rehace.
        """
        registros: list[dict[str, Any]] = []
        if not ruta.exists():
            return registros
        with open(ruta, "r", encoding="utf-8") as mango:
            for numero, linea in enumerate(mango, start=1):
                texto = linea.strip()
                if not texto:
                    continue
                try:
                    registros.append(json.loads(texto))
                except json.JSONDecodeError as fallo:
                    self.lineas_descartadas.append(
                        LineaDescartada(numero, f"linea truncada o corrupta: {fallo}", texto[:200])
                    )
        return registros

    def iterar_jsonl(self, ruta: Path) -> Iterator[dict[str, Any]]:
        yield from self.leer_jsonl(ruta)

    # -- almacen por contenido ---------------------------------------------

    def guardar_blob(self, contenido: str | bytes) -> str:
        """Primer paso del orden canonico. Idempotente por construccion."""
        datos = contenido.encode("utf-8") if isinstance(contenido, str) else contenido
        digest = sha256_bytes(datos)
        destino = self.blob(digest)
        if not destino.exists():
            _escribir_atomico(destino, datos)
        return digest

    def guardar_contenido_fuente(self, contenido: str) -> str:
        """Conservacion del contenido consultado de una Fuente (RF-101)."""
        digest = sha256_texto(contenido)
        destino = self.contenido_fuente(digest)
        if not destino.exists():
            _escribir_atomico(destino, contenido.encode("utf-8"))
        return digest

    def recuperar_blob(self, digest: str) -> bytes | None:
        ruta = self.blob(digest)
        return ruta.read_bytes() if ruta.exists() else None

    def recuperar_contenido_fuente(self, digest: str) -> str | None:
        ruta = self.contenido_fuente(digest)
        return ruta.read_text(encoding="utf-8") if ruta.exists() else None

    # -- memoria efimera ---------------------------------------------------

    def preparar_tmp(self, id_unidad: str) -> Path:
        """Unico sitio bajo `proyectos/` donde los permisos dejan escribir a un agente."""
        carpeta = self.tmp(id_unidad)
        carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta

    def borrar_tmp(self, id_unidad: str) -> None:
        """La memoria efimera se borra al cerrar la unidad. Nunca es autoritativa."""
        shutil.rmtree(self.tmp(id_unidad), ignore_errors=True)

    # -- existencia --------------------------------------------------------

    def existe(self) -> bool:
        return self.fichero_proyecto.exists()

    def crear_arbol(self) -> None:
        for relativa in (
            "encargo", "contexto/figuras_reales", "canon/plan", "novela/escenas",
            "novela/sinopsis", "ejecuciones", "fuentes", "blobs", "tmp", "indices", "entrega",
        ):
            (self.raiz / relativa).mkdir(parents=True, exist_ok=True)


class CerrojoProyecto:
    """Regla 1 de ADR-04: escritor unico.

    Sustituye al control de concurrencia que no hay. Se toma al arrancar una
    Ejecucion y se libera al cerrarla; un segundo proceso falla con ERR-501 en
    lugar de corromper el arbol a dos manos.
    """

    def __init__(self, almacen: Almacen, titular: str = "nucleo"):
        self.almacen = almacen
        self.titular = titular
        self.ruta = almacen.raiz / ".cerrojo"
        self._tomado = False

    def tomar(self) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(str(self.ruta), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            actual = {}
            try:
                actual = json.loads(self.ruta.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
            raise ErrorStoryMaker(
                "ERR-501",
                "El Proyecto ya tiene un escritor. Solo un proceso escribe a la vez.",
                proyecto=self.almacen.id_proyecto,
                titular_actual=actual.get("titular"),
                tomado_en=actual.get("tomado_en"),
            ) from None
        from storymaker.sobre import ahora  # importacion local: evita el ciclo

        with os.fdopen(descriptor, "w", encoding="utf-8") as mango:
            json.dump(
                {"titular": self.titular, "pid": os.getpid(), "tomado_en": ahora()},
                mango,
            )
        self._tomado = True

    def liberar(self) -> None:
        if self._tomado:
            self.ruta.unlink(missing_ok=True)
            self._tomado = False

    def __enter__(self) -> "CerrojoProyecto":
        self.tomar()
        return self

    def __exit__(self, *_excepcion: Any) -> None:
        self.liberar()


@contextmanager
def escritura_serializada(almacen: Almacen, titular: str = "nucleo") -> Iterator[Almacen]:
    with CerrojoProyecto(almacen, titular):
        yield almacen
