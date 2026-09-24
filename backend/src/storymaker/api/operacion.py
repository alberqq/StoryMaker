"""spec: §5.3 · arq: §16.5, §10

**La operación de una novela desde la interfaz.**

Encargar, continuar, decidir y reintentar ejecutan el grafo, y por eso aquí no se ejecutan:
se lanza el comando de la CLI que lo hace, como proceso aparte, y se responde en el acto
con un `202`. Antes de lanzar se comprueba lo que el comando rechazaría —novela ocupada, gate
ausente o presente, una decisión que no cabe—, para que el Autor lo vea en la pantalla y no
en un registro. Las comprobaciones no sustituyen al comando: si dos acciones se cruzan, la
segunda choca con el cerrojo en su proceso, y no se pierde nada.

Desbloquear y editar no ejecutan el grafo, así que los hace la API misma: desbloquear solo
rompe un cerrojo cuyo proceso ha muerto, y editar toma el cerrojo mientras escribe, con la
maquinaria de `regeneration/` que ya reindexa y deja traza.

Todas las rutas pasan por `solo_local`: solo se opera desde la propia máquina, y en JSON.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from storymaker.api import lanzador
from storymaker.api.guardas import solo_local
from storymaker.api.seguimiento import (
    CAMPOS_EDITABLES,
    FICHERO_DE_ENCARGO,
    _settings,
    carpeta_de,
    corpus_sellado,
)
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela, ruta_de_novela
from storymaker.commons.db.repos import arnes
from storymaker.commons.graph import cerrojo

router = APIRouter(tags=["operacion"], dependencies=[Depends(solo_local)])
ejemplos_router = APIRouter(tags=["operacion"])

#: La carpeta de briefs de ejemplo del repositorio.
_EJEMPLOS = Path(__file__).resolve().parents[4] / "ejemplos"


# --- Modelos -------------------------------------------------------------------------


class ErrorDeCampo(BaseModel):
    campo: str
    mensaje: str


class Validacion(BaseModel):
    valido: bool
    errores: list[ErrorDeCampo]
    nombre_sugerido: str | None = None


class CuerpoDeEncargo(BaseModel):
    encargo: dict[str, Any]


class CuerpoDeNovela(BaseModel):
    encargo: dict[str, Any]
    nombre: str = ""
    batch: bool = False
    #: El modo de investigación de arq. §4, Fase 2, que se elige al crear la novela.
    investigacion: Literal["estandar", "exhaustiva"] = "estandar"


class CuerpoDeDecision(BaseModel):
    decision: str
    comentario: str = ""


class CuerpoDeEdicion(BaseModel):
    objeto: Literal["hecho", "personaje", "escenario", "glosario"]
    fila_id: int
    campo: str
    valor: str = Field(min_length=1)
    motivo: str = ""


class Lanzada(BaseModel):
    nombre: str
    registro: str
    mensaje: str


class Hecha(BaseModel):
    nombre: str
    mensaje: str


class Ejemplo(BaseModel):
    nombre: str
    encargo: dict[str, Any]


# --- Ayudas --------------------------------------------------------------------------


def _rechazo(codigo: int, mensaje: str) -> HTTPException:
    return HTTPException(status_code=codigo, detail=mensaje)


def _lanzar(peticion: Request) -> Callable[[Path, list[str], Settings], str]:
    """El lanzador de la aplicación. Las pruebas ponen uno que no abre procesos."""
    return getattr(peticion.app.state, "lanzar", lanzador.lanzar)


def validar_encargo(encargo: dict[str, Any]) -> Validacion:
    """El encargo con **el mismo lector que `storymaker nueva`**, más los tipos por campo.

    El lector es deliberadamente indulgente —solo exige a quién se regala la novela, porque
    la entrevista pregunta el resto—, así que aquí se añaden las comprobaciones de forma que
    un formulario puede señalar junto a su campo.
    """
    from storymaker.intake.encargo import EncargoIlegible, leer

    errores: list[ErrorDeCampo] = []
    obra = encargo.get("obra") if isinstance(encargo.get("obra"), dict) else {}
    for campo, minimo, maximo in (("n_capitulos", 1, 60), ("palabras_por_capitulo", 300, 10_000)):
        valor = obra.get(campo) if isinstance(obra, dict) else None
        if valor in (None, ""):
            continue
        try:
            numero = int(valor)
        except (TypeError, ValueError):
            errores.append(ErrorDeCampo(campo=f"obra.{campo}", mensaje="Tiene que ser un número."))
            continue
        if not minimo <= numero <= maximo:
            errores.append(
                ErrorDeCampo(campo=f"obra.{campo}", mensaje=f"Entre {minimo} y {maximo}.")
            )

    nombre: str | None = None
    with tempfile.TemporaryDirectory() as carpeta:
        fichero = Path(carpeta) / "encargo.json"
        fichero.write_text(json.dumps(encargo, ensure_ascii=False), encoding="utf-8")
        try:
            nombre = leer(fichero).nombre
        except EncargoIlegible as error:
            campo = (
                "homenajeado.nombre_homenajeado"
                if "nombre_homenajeado" in str(error)
                else "encargo"
            )
            mensaje = (
                "Falta el nombre del homenajeado: es lo único imprescindible."
                if campo != "encargo"
                else str(error)
            )
            errores.append(ErrorDeCampo(campo=campo, mensaje=mensaje))
    return Validacion(valido=not errores, errores=errores, nombre_sugerido=nombre)


async def _registrar(ruta: Path, accion: str, despues: dict[str, Any]) -> None:
    """La acción de la interfaz en `audit_log`, con el actor `autor`."""
    if not ruta.exists():
        return
    async with abrir_novela(ruta) as db:
        await arnes.registrar_audit(
            db,
            actor="autor",
            accion=f"lanzar:{accion}",
            objeto=f"novela:{ruta.stem}",
            despues=despues,
        )
        await db.commit()


def _exigir_libre(ruta: Path) -> None:
    if cerrojo.esta_tomado(ruta):
        raise _rechazo(
            409, "Hay una ejecución en curso sobre esta novela. Inténtalo cuando termine."
        )


def _aceptada(cuerpo: BaseModel) -> JSONResponse:
    return JSONResponse(status_code=202, content=cuerpo.model_dump())


# --- Endpoints ------------------------------------------------------------------------


@ejemplos_router.get("/ejemplos")
async def ejemplos() -> list[Ejemplo]:
    """Los briefs de `ejemplos/`, ya leídos, para partir de uno en el encargo."""
    import yaml

    resultado = []
    for fichero in sorted(_EJEMPLOS.glob("*.yaml")):
        try:
            datos = yaml.safe_load(fichero.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if isinstance(datos, dict):
            resultado.append(
                Ejemplo(nombre=fichero.stem, encargo=json.loads(json.dumps(datos, default=str)))
            )
    return resultado


@router.post("/encargos/validar")
async def validar(cuerpo: CuerpoDeEncargo) -> Validacion:
    return validar_encargo(cuerpo.encargo)


@router.post("/novelas", status_code=202, response_model=Lanzada)
async def encargar(cuerpo: CuerpoDeNovela, peticion: Request) -> Any:
    """Escribe el encargo en la carpeta de la novela y lanza `storymaker nueva`."""
    settings = _settings(peticion)
    validacion = validar_encargo(cuerpo.encargo)
    if not validacion.valido:
        raise _rechazo(422, "; ".join(f"{e.campo}: {e.mensaje}" for e in validacion.errores))
    nombre = cuerpo.nombre.strip() or validacion.nombre_sugerido or "novela"
    ruta = ruta_de_novela(nombre, settings.directorio_proyectos)
    if ruta.exists():
        raise _rechazo(409, f"Ya existe una novela llamada {ruta.stem}. Elige otro nombre.")
    carpeta = ruta.parent
    carpeta.mkdir(parents=True, exist_ok=True)
    encargo = carpeta / FICHERO_DE_ENCARGO
    encargo.write_text(json.dumps(cuerpo.encargo, ensure_ascii=False, indent=2), encoding="utf-8")
    argumentos = ["nueva", str(encargo.resolve()), "--nombre", ruta.stem]
    if cuerpo.batch:
        argumentos.append("--batch")
    if cuerpo.investigacion == "exhaustiva":
        argumentos += ["--investigacion", "exhaustiva"]
    registro = _lanzar(peticion)(carpeta, argumentos, settings)
    return _aceptada(
        Lanzada(nombre=ruta.stem, registro=registro, mensaje="Encargo lanzado. La novela arranca.")
    )


@router.post("/novelas/{nombre}/continuar", status_code=202, response_model=Lanzada)
async def continuar(nombre: str, peticion: Request) -> Any:
    settings = _settings(peticion)
    carpeta = carpeta_de(nombre, settings)
    ruta = carpeta / f"{carpeta.name}.db"
    _exigir_libre(ruta)
    if ruta.exists():
        async with abrir_novela(ruta) as db:
            pendiente = await arnes.gate_pendiente(db)
        if pendiente is not None:
            raise _rechazo(
                422, "La novela espera tu decisión en un gate: decide antes de continuar."
            )
    registro = _lanzar(peticion)(carpeta, ["continuar", carpeta.name], settings)
    await _registrar(ruta, "continuar", {"registro": registro})
    return _aceptada(
        Lanzada(nombre=carpeta.name, registro=registro, mensaje="Continuación lanzada.")
    )


@router.post("/novelas/{nombre}/decisiones", status_code=202, response_model=Lanzada)
async def decidir(nombre: str, cuerpo: CuerpoDeDecision, peticion: Request) -> Any:
    """Lanza `storymaker decidir`. La interfaz nunca envía `editar` (arq. §16.5)."""
    settings = _settings(peticion)
    carpeta = carpeta_de(nombre, settings)
    ruta = carpeta / f"{carpeta.name}.db"
    if cuerpo.decision == "editar":
        raise _rechazo(
            422,
            "En la interfaz, editar es corregir filas y después aprobar o rehacer; "
            "la decisión «editar» es solo de la CLI.",
        )
    if cuerpo.decision not in ("aprobar", "rehacer", "abortar"):
        raise _rechazo(422, f"«{cuerpo.decision}» no es una decisión.")
    _exigir_libre(ruta)
    if not ruta.exists():
        raise _rechazo(422, "La novela todavía no tiene ningún gate.")
    async with abrir_novela(ruta) as db:
        pendiente = await arnes.gate_pendiente(db)
        fase = None
        if pendiente is not None:
            async with db.execute(
                "SELECT fase FROM fase_run WHERE id = ?", (pendiente["fase_run_id"],)
            ) as cursor:
                fila = await cursor.fetchone()
            fase = str(fila["fase"]) if fila is not None else None
    if pendiente is None:
        raise _rechazo(422, "La novela no tiene ningún gate esperando decisión.")
    if cuerpo.decision == "abortar" and fase != "intake":
        raise _rechazo(422, "Abortar solo cabe en el gate de Intake.")
    argumentos = ["decidir", carpeta.name, cuerpo.decision]
    if cuerpo.comentario.strip():
        argumentos += ["--comentario", cuerpo.comentario.strip()]
    registro = _lanzar(peticion)(carpeta, argumentos, settings)
    await _registrar(
        ruta, "decidir", {"decision": cuerpo.decision, "comentario": cuerpo.comentario or None}
    )
    return _aceptada(
        Lanzada(
            nombre=carpeta.name, registro=registro, mensaje=f"Decisión «{cuerpo.decision}» lanzada."
        )
    )


@router.post("/novelas/{nombre}/reintentar", status_code=202, response_model=Lanzada)
async def reintentar(nombre: str, peticion: Request) -> Any:
    """Lanza `storymaker reintentar`, que decide él mismo si procede."""
    settings = _settings(peticion)
    carpeta = carpeta_de(nombre, settings)
    ruta = carpeta / f"{carpeta.name}.db"
    _exigir_libre(ruta)
    registro = _lanzar(peticion)(carpeta, ["reintentar", carpeta.name], settings)
    await _registrar(ruta, "reintentar", {"registro": registro})
    return _aceptada(Lanzada(nombre=carpeta.name, registro=registro, mensaje="Reintento lanzado."))


@router.post("/novelas/{nombre}/desbloquear")
async def desbloquear(nombre: str, peticion: Request) -> Hecha:
    """Rompe el cerrojo **solo si su proceso ha muerto**."""
    carpeta = carpeta_de(nombre, _settings(peticion))
    ruta = carpeta / f"{carpeta.name}.db"
    if not cerrojo.esta_tomado(ruta):
        raise _rechazo(422, "La novela no tiene ningún cerrojo que romper.")
    pid = cerrojo.pid_del_cerrojo(ruta)
    if pid is not None and cerrojo.proceso_vivo(pid):
        raise _rechazo(
            409, "El proceso que tiene el cerrojo sigue vivo: no se rompe un cerrojo vivo."
        )
    cerrojo.romper(ruta)
    return Hecha(nombre=carpeta.name, mensaje="Cerrojo roto. Ya puedes continuar la novela.")


@router.post("/novelas/{nombre}/ediciones")
async def editar(nombre: str, cuerpo: CuerpoDeEdicion, peticion: Request) -> Hecha:
    """Edición humana directa de una fila, con el cerrojo tomado mientras se escribe."""
    from storymaker.regeneration import cambio
    from storymaker.regeneration.esquemas import CambioResuelto, ObjetoDelCambio

    carpeta = carpeta_de(nombre, _settings(peticion))
    ruta = carpeta / f"{carpeta.name}.db"
    if cuerpo.campo not in CAMPOS_EDITABLES[cuerpo.objeto]:
        raise _rechazo(422, f"El campo «{cuerpo.campo}» de {cuerpo.objeto} no se edita desde aquí.")
    if not ruta.exists():
        raise _rechazo(422, "La novela todavía no tiene nada que editar.")
    objeto = ObjetoDelCambio(cuerpo.objeto)
    tabla = cambio.TABLA_DE[objeto]
    fabrica = getattr(peticion.app.state, "vectorizador", None)
    if fabrica is None:
        from storymaker.commons.embeddings.modelo import FastEmbedVectorizador

        fabrica = FastEmbedVectorizador
    try:
        with cerrojo.tomar(ruta):
            async with abrir_novela(ruta) as db:
                if objeto is ObjetoDelCambio.HECHO and await corpus_sellado(db):
                    raise _rechazo(422, "El corpus ya está sellado: sus hechos no se editan.")
                async with db.execute(
                    f"SELECT {cuerpo.campo} FROM {tabla} WHERE id = ?",  # noqa: S608 — lista cerrada
                    (cuerpo.fila_id,),
                ) as cursor:
                    fila = await cursor.fetchone()
                if fila is None:
                    raise _rechazo(422, f"No hay ninguna fila {cuerpo.fila_id} en {cuerpo.objeto}.")
                pendiente = await arnes.gate_pendiente(db)
                await cambio.aplicar(
                    db,
                    fabrica(),
                    CambioResuelto(
                        objeto=objeto,
                        fila_id=cuerpo.fila_id,
                        campo=cuerpo.campo,
                        antes=str(fila[0] or ""),
                        despues=cuerpo.valor,
                        motivo=cuerpo.motivo,
                    ),
                    actor="autor",
                    fase_run_id=int(pendiente["fase_run_id"]) if pendiente is not None else None,
                )
                await db.commit()
    except HTTPException:
        raise
    except Exception as error:
        from storymaker.commons.errores import NovelaOcupada

        if isinstance(error, NovelaOcupada):
            raise _rechazo(409, "Hay una ejecución en curso sobre esta novela.") from error
        raise
    return Hecha(nombre=carpeta.name, mensaje="Edición guardada y trazada.")
