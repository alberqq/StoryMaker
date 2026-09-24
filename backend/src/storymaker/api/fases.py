"""spec: §5.2 · arq: §16.5

**La salida de cada fase**: lo que dejó escrito en el fichero, tal como el Autor necesita
consultarlo para seguir una novela o para decidir un gate.

Cada fase devuelve además sus ejecuciones y las decisiones de sus gates, porque lo que una
fase produjo solo se entiende junto a cuántas veces corrió y qué se le pidió al rehacerla.
Todo sale de las tablas de dominio que §7 de la arquitectura ya exige: aquí no se calcula
nada que no se pueda leer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from storymaker.api.lectura import nombre_de_escenario
from storymaker.api.seguimiento import (
    Ejecucion,
    _settings,
    carpeta_de,
    registros_de,
)
from storymaker.commons.db.apertura import abrir_novela
from storymaker.commons.errores import NovelaNoEncontrada

router = APIRouter(prefix="/novelas", tags=["seguimiento"])

#: El segmento castellano de la URL y el nombre de la fase en `fase_run`.
FASE_DE_URL = {
    "encargo": "intake",
    "investigacion": "investigation",
    "trama": "plotting",
    "escritura": "writing",
    "publicacion": "publication",
    "regeneracion": "regeneration",
}

#: Cuánto del final de un registro se devuelve. Lo que importa es cómo acabó.
BYTES_DE_REGISTRO = 64_000


# --- Modelos -------------------------------------------------------------------------


class Decision(BaseModel):
    gate_id: int
    estado: str
    decision: str | None = None
    comentario: str | None = None
    decidido_en: str | None = None


class DatoDelEncargo(BaseModel):
    id: int
    tipo: str
    valor: str
    origen: str
    obligatorio: bool


class TextoEnCuarentena(BaseModel):
    texto: str
    recibido_en: str
    procesado_en: str | None = None


class SalidaEncargo(BaseModel):
    encargo: dict[str, Any] | None = None
    brief: dict[str, Any] | None = None
    datos: list[DatoDelEncargo]
    cuarentena: list[TextoEnCuarentena]


class Fuente(BaseModel):
    titulo: str | None = None
    url: str | None = None
    autor: str | None = None
    fecha: str | None = None
    fiabilidad: str | None = None


class Hecho(BaseModel):
    id: int
    enunciado: str
    estado: str
    dimension: str
    origen: str
    respaldo: str
    cita: str | None = None
    fuentes: list[Fuente]


class Entidad(BaseModel):
    tipo: str
    nombre: str
    nombre_epoca: str | None = None
    fecha_inicio: str | None = None
    fecha_fin: str | None = None


class Sello(BaseModel):
    hash: str
    calculado_en: str


class SalidaInvestigacion(BaseModel):
    hechos: list[Hecho]
    recuento: dict[str, int]
    entidades: list[Entidad]
    sello: Sello | None = None


class Obra(BaseModel):
    titulo: str | None = None
    premisa: str | None = None
    tema: str | None = None
    genero: str | None = None
    voz: str | None = None
    estilo: dict[str, Any] | None = None
    n_capitulos: int
    palabras_por_capitulo: int


class Hito(BaseModel):
    orden: int
    descripcion: str


class Arco(BaseModel):
    tipo: str
    estado_inicial: str | None = None
    estado_final: str | None = None
    hitos: list[Hito]


class Personaje(BaseModel):
    id: int
    nombre: str
    tipo: str
    rasgos: list[str]
    objetivo: str | None = None
    miedo: str | None = None
    voz: str | None = None
    estatus: str | None = None
    es_homenajeado: bool
    arcos: list[Arco]


class Relacion(BaseModel):
    a: str
    b: str
    tipo: str
    intensidad: int | None = None


class Escenario(BaseModel):
    id: int
    nombre: str
    lugar: str | None = None
    nombre_epoca: str | None = None
    descripcion: str | None = None


class LicenciaDelCanon(BaseModel):
    alteracion: str
    justificacion: str
    declarada: bool


class TerminoGlosario(BaseModel):
    termino: str
    significado: str
    registro: str | None = None


class Beat(BaseModel):
    orden: int
    accion: str
    cambio_de_valor: str | None = None


class Anclaje(BaseModel):
    tipo_vinculo: str
    descripcion: str


class Escena(BaseModel):
    orden: int
    escenario: str | None = None
    fecha_narrativa: str | None = None
    punto_de_vista: str | None = None
    objetivo: str | None = None
    conflicto: str | None = None
    resultado: str | None = None
    personajes: list[str]
    beats: list[Beat]
    anclajes: list[Anclaje]


class CapituloDeEscaleta(BaseModel):
    numero: int
    titulo: str | None = None
    funcion: str | None = None
    gancho: str | None = None
    escenas: list[Escena]


class SalidaTrama(BaseModel):
    obra: Obra | None = None
    personajes: list[Personaje]
    relaciones: list[Relacion]
    escenarios: list[Escenario]
    licencias: list[LicenciaDelCanon]
    glosario: list[TerminoGlosario]
    escaleta: list[CapituloDeEscaleta]


class Incidencia(BaseModel):
    validador: str
    severidad: str
    ubicacion: str | None = None
    mensaje: str
    propuesta: str | None = None


class Intento(BaseModel):
    id: int
    intento: int
    estado: str
    palabras: int
    creado_en: str
    incidencias: list[Incidencia]


class CapituloEscrito(BaseModel):
    numero: int
    titulo: str | None = None
    intentos: list[Intento]


class SalidaEscritura(BaseModel):
    capitulos: list[CapituloEscrito]


class Criterio(BaseModel):
    criterio: str
    valor: float


class Rubrica(BaseModel):
    media: float
    criterios: list[Criterio]


class ManifiestoPublicado(BaseModel):
    brief_hash: str
    sello_corpus_hash: str
    modelos: str
    embeddings: str
    sdk_version: str | None = None
    gates_enabled: bool
    creado_en: str


class VersionConManifiesto(BaseModel):
    numero: int
    creada_en: str
    capitulos: int
    manifiesto: ManifiestoPublicado | None = None


class SalidaPublicacion(BaseModel):
    versiones: list[VersionConManifiesto]
    rubricas: list[Rubrica]


class Peticion(BaseModel):
    momento: str
    texto: str
    fragmento: str | None = None
    capitulo: int | None = None


class EdicionHumana(BaseModel):
    tabla: str
    fila_id: int
    campo: str
    antes: str | None = None
    despues: str | None = None
    motivo: str | None = None


class SalidaRegeneracion(BaseModel):
    peticiones: list[Peticion]
    ediciones: list[EdicionHumana]


class SalidaDeFase(BaseModel):
    fase: str
    ejecuciones: list[Ejecucion]
    decisiones: list[Decision]
    encargo: SalidaEncargo | None = None
    investigacion: SalidaInvestigacion | None = None
    trama: SalidaTrama | None = None
    escritura: SalidaEscritura | None = None
    publicacion: SalidaPublicacion | None = None
    regeneracion: SalidaRegeneracion | None = None


class TextoDeIntento(BaseModel):
    id: int
    capitulo: int
    intento: int
    estado: str
    palabras: int
    texto: str
    incidencias: list[Incidencia]
    tokens_de_contexto: int | None = None


# --- Lectura -------------------------------------------------------------------------


async def _filas(db: aiosqlite.Connection, consulta: str, *parametros: Any) -> list[Any]:
    async with db.execute(consulta, parametros) as cursor:
        return list(await cursor.fetchall())


def _json(crudo: Any) -> Any:
    if not crudo:
        return None
    try:
        return json.loads(str(crudo))
    except ValueError:
        return None


def _texto(valor: Any) -> str:
    """Un valor de JSON tal como lo leería una persona."""
    datos = _json(valor)
    if isinstance(datos, str):
        return datos
    if isinstance(datos, dict):
        return ", ".join(f"{k}: {v}" for k, v in datos.items())
    if isinstance(datos, list):
        return ", ".join(str(v) for v in datos)
    return str(valor) if valor is not None else ""


def _lista(valor: Any) -> list[str]:
    datos = _json(valor)
    if isinstance(datos, list):
        return [str(v) for v in datos]
    if isinstance(datos, dict):
        return [f"{k}: {v}" for k, v in datos.items()]
    return [str(datos)] if datos else []


async def _incidencias(db: aiosqlite.Connection, capitulo_version_id: int) -> list[Incidencia]:
    return [
        Incidencia(
            validador=str(i["validador"]),
            severidad=str(i["severidad"]),
            ubicacion=i["ubicacion"],
            mensaje=str(i["mensaje"]),
            propuesta=i["propuesta"],
        )
        for i in await _filas(
            db,
            "SELECT * FROM incidencia WHERE capitulo_version_id = ? ORDER BY id",
            capitulo_version_id,
        )
    ]


async def _encargo(db: aiosqlite.Connection, carpeta: Path) -> SalidaEncargo:
    from storymaker.api.seguimiento import _encargo_de

    brief = await _filas(db, "SELECT json FROM intake_brief ORDER BY id DESC LIMIT 1")
    return SalidaEncargo(
        encargo=_encargo_de(carpeta) or None,
        brief=_json(brief[0]["json"]) if brief else None,
        datos=[
            DatoDelEncargo(
                id=int(d["id"]),
                tipo=str(d["tipo"]),
                valor=_texto(d["valor_json"]),
                origen=str(d["origen"]),
                obligatorio=bool(d["obligatorio"]),
            )
            for d in await _filas(db, "SELECT * FROM intake_dato ORDER BY id")
        ],
        cuarentena=[
            TextoEnCuarentena(
                texto=str(t["texto"]),
                recibido_en=str(t["recibido_en"]),
                procesado_en=t["procesado_en"],
            )
            for t in await _filas(db, "SELECT * FROM intake_texto_crudo ORDER BY id")
        ],
    )


async def _investigacion(db: aiosqlite.Connection) -> SalidaInvestigacion:
    fuentes: dict[int, list[Fuente]] = {}
    for f in await _filas(
        db,
        """
        SELECT hf.hecho_id, f.titulo, f.url, f.autor, f.fecha, f.fiabilidad
          FROM mundo_hecho_fuente hf JOIN mundo_fuente f ON f.id = hf.fuente_id
        """,
    ):
        fuentes.setdefault(int(f["hecho_id"]), []).append(
            Fuente(
                titulo=f["titulo"],
                url=f["url"],
                autor=f["autor"],
                fecha=f["fecha"],
                fiabilidad=f["fiabilidad"],
            )
        )
    hechos = [
        Hecho(
            id=int(h["id"]),
            enunciado=str(h["enunciado"]),
            estado=str(h["estado"]),
            dimension=str(h["dimension"]),
            origen=str(h["origen"]),
            respaldo=str(h["respaldo"]),
            cita=h["cita"],
            fuentes=fuentes.get(int(h["id"]), []),
        )
        for h in await _filas(db, "SELECT * FROM mundo_hecho ORDER BY dimension, id")
    ]
    recuento: dict[str, int] = {}
    for h in hechos:
        recuento[h.dimension] = recuento.get(h.dimension, 0) + 1
    sello = await _filas(db, "SELECT hash, calculado_en FROM mundo_sello ORDER BY id DESC LIMIT 1")
    return SalidaInvestigacion(
        hechos=hechos,
        recuento=recuento,
        entidades=[
            Entidad(
                tipo=str(e["tipo"]),
                nombre=str(e["nombre"]),
                nombre_epoca=e["nombre_epoca"],
                fecha_inicio=e["fecha_inicio"],
                fecha_fin=e["fecha_fin"],
            )
            for e in await _filas(db, "SELECT * FROM mundo_entidad ORDER BY tipo, nombre")
        ],
        sello=Sello(hash=str(sello[0]["hash"]), calculado_en=str(sello[0]["calculado_en"]))
        if sello
        else None,
    )


async def _trama(db: aiosqlite.Connection) -> SalidaTrama:
    obra_filas = await _filas(db, "SELECT * FROM canon_obra LIMIT 1")
    obra = obra_filas[0] if obra_filas else None
    homenajeado_id = obra["homenajeado_id"] if obra is not None else None
    nombres = {
        int(p["id"]): str(p["nombre"])
        for p in await _filas(db, "SELECT id, nombre FROM canon_personaje")
    }

    arcos: dict[int, list[Arco]] = {}
    for a in await _filas(db, "SELECT * FROM canon_arco ORDER BY id"):
        hitos = [
            Hito(orden=int(h["orden"]), descripcion=str(h["descripcion"]))
            for h in await _filas(
                db,
                "SELECT orden, descripcion FROM canon_arco_hito WHERE arco_id = ? ORDER BY orden",
                a["id"],
            )
        ]
        arcos.setdefault(int(a["personaje_id"]), []).append(
            Arco(
                tipo=str(a["tipo"]),
                estado_inicial=a["estado_inicial"],
                estado_final=a["estado_final"],
                hitos=hitos,
            )
        )

    escenarios = {
        int(e["id"]): e
        for e in await _filas(
            db,
            """
            SELECT s.id, s.descripcion, m.nombre AS lugar, m.nombre_epoca
              FROM canon_escenario s LEFT JOIN mundo_entidad m ON m.id = s.lugar_entidad_id
            """,
        )
    }

    escaleta = []
    for c in await _filas(db, "SELECT * FROM plan_capitulo ORDER BY numero"):
        escenas = []
        for e in await _filas(
            db, "SELECT * FROM plan_escena WHERE capitulo_id = ? ORDER BY orden", c["id"]
        ):
            escenario = escenarios.get(int(e["escenario_id"])) if e["escenario_id"] else None
            anclajes = []
            for a in await _filas(
                db,
                """
                SELECT a.tipo_vinculo, h.enunciado, m.nombre, d.valor_json
                  FROM plan_anclaje a
                  LEFT JOIN mundo_hecho h ON h.id = a.hecho_id
                  LEFT JOIN mundo_entidad m ON m.id = a.entidad_id
                  LEFT JOIN intake_dato d ON d.id = a.dato_id
                 WHERE a.escena_id = ?
                """,
                e["id"],
            ):
                descripcion = a["enunciado"] or a["nombre"] or _texto(a["valor_json"])
                anclajes.append(
                    Anclaje(tipo_vinculo=str(a["tipo_vinculo"]), descripcion=str(descripcion or ""))
                )
            escenas.append(
                Escena(
                    orden=int(e["orden"]),
                    escenario=nombre_de_escenario(
                        int(escenario["id"]), escenario["lugar"], escenario["descripcion"]
                    )
                    if escenario is not None
                    else None,
                    fecha_narrativa=e["fecha_narrativa"],
                    punto_de_vista=nombres.get(int(e["pdv_personaje_id"]))
                    if e["pdv_personaje_id"]
                    else None,
                    objetivo=e["objetivo"],
                    conflicto=e["conflicto"],
                    resultado=e["resultado"],
                    personajes=[
                        nombres.get(int(p["personaje_id"]), "?")
                        for p in await _filas(
                            db,
                            "SELECT personaje_id FROM plan_escena_personaje WHERE escena_id = ?",
                            e["id"],
                        )
                    ],
                    beats=[
                        Beat(
                            orden=int(b["orden"]),
                            accion=str(b["accion"]),
                            cambio_de_valor=b["cambio_de_valor"],
                        )
                        for b in await _filas(
                            db,
                            "SELECT * FROM plan_beat WHERE escena_id = ? ORDER BY orden",
                            e["id"],
                        )
                    ],
                    anclajes=anclajes,
                )
            )
        escaleta.append(
            CapituloDeEscaleta(
                numero=int(c["numero"]),
                titulo=c["titulo"],
                funcion=c["funcion"],
                gancho=c["gancho"],
                escenas=escenas,
            )
        )

    return SalidaTrama(
        obra=Obra(
            titulo=obra["titulo"],
            premisa=obra["premisa"],
            tema=obra["tema"],
            genero=obra["genero"],
            voz=obra["voz"],
            estilo=_json(obra["estilo_json"]),
            n_capitulos=int(obra["n_capitulos"]),
            palabras_por_capitulo=int(obra["palabras_por_capitulo"]),
        )
        if obra is not None
        else None,
        personajes=[
            Personaje(
                id=int(p["id"]),
                nombre=str(p["nombre"]),
                tipo=str(p["tipo"]),
                rasgos=_lista(p["rasgos_json"]),
                objetivo=p["objetivo"],
                miedo=p["miedo"],
                voz=p["voz"],
                estatus=p["estatus"],
                es_homenajeado=homenajeado_id is not None and int(p["id"]) == homenajeado_id,
                arcos=arcos.get(int(p["id"]), []),
            )
            for p in await _filas(db, "SELECT * FROM canon_personaje ORDER BY id")
        ],
        relaciones=[
            Relacion(
                a=nombres.get(int(r["a_id"]), "?"),
                b=nombres.get(int(r["b_id"]), "?"),
                tipo=str(r["tipo"]),
                intensidad=r["intensidad"],
            )
            for r in await _filas(db, "SELECT * FROM canon_relacion")
        ],
        escenarios=[
            Escenario(
                id=i,
                nombre=nombre_de_escenario(i, e["lugar"], e["descripcion"]),
                lugar=e["lugar"],
                nombre_epoca=e["nombre_epoca"],
                descripcion=e["descripcion"],
            )
            for i, e in sorted(escenarios.items())
        ],
        licencias=[
            LicenciaDelCanon(
                alteracion=str(lic["alteracion"]),
                justificacion=str(lic["justificacion"]),
                declarada=bool(lic["declarada"]),
            )
            for lic in await _filas(db, "SELECT * FROM canon_licencia ORDER BY id")
        ],
        glosario=[
            TerminoGlosario(
                termino=str(g["termino"]), significado=str(g["significado"]), registro=g["registro"]
            )
            for g in await _filas(db, "SELECT * FROM canon_glosario ORDER BY termino")
        ],
        escaleta=escaleta,
    )


async def _escritura(db: aiosqlite.Connection) -> SalidaEscritura:
    capitulos = []
    for c in await _filas(db, "SELECT id, numero, titulo FROM plan_capitulo ORDER BY numero"):
        intentos = [
            Intento(
                id=int(v["id"]),
                intento=int(v["intento"]),
                estado=str(v["estado"]),
                palabras=int(v["palabras"]),
                creado_en=str(v["creado_en"]),
                incidencias=await _incidencias(db, int(v["id"])),
            )
            for v in await _filas(
                db,
                "SELECT id, intento, estado, palabras, creado_en FROM capitulo_version "
                "WHERE capitulo_id = ? ORDER BY id",
                c["id"],
            )
        ]
        capitulos.append(
            CapituloEscrito(numero=int(c["numero"]), titulo=c["titulo"], intentos=intentos)
        )
    return SalidaEscritura(capitulos=capitulos)


async def _publicacion(db: aiosqlite.Connection) -> SalidaPublicacion:
    versiones = []
    for v in await _filas(db, "SELECT * FROM version_novela ORDER BY numero"):
        m = await _filas(
            db, "SELECT * FROM manifiesto WHERE version_novela_id = ? LIMIT 1", v["id"]
        )
        n = await _filas(
            db, "SELECT COUNT(*) AS n FROM version_capitulo WHERE version_id = ?", v["id"]
        )
        versiones.append(
            VersionConManifiesto(
                numero=int(v["numero"]),
                creada_en=str(v["creada_en"]),
                capitulos=int(n[0]["n"]) if n else 0,
                manifiesto=ManifiestoPublicado(
                    brief_hash=str(m[0]["brief_hash"]),
                    sello_corpus_hash=str(m[0]["sello_corpus_hash"]),
                    modelos=str(m[0]["modelos_json"]),
                    embeddings=str(m[0]["embeddings_json"]),
                    sdk_version=m[0]["sdk_version"],
                    gates_enabled=bool(m[0]["gates_enabled"]),
                    creado_en=str(m[0]["creado_en"]),
                )
                if m
                else None,
            )
        )
    rubricas = []
    for s in await _filas(
        db, "SELECT valor, detalle_json FROM score WHERE validador = 'juez_rubrica' ORDER BY id"
    ):
        detalle = _json(s["detalle_json"]) or {}
        rubricas.append(
            Rubrica(
                media=round(float(s["valor"]), 2),
                criterios=[
                    Criterio(criterio=str(k), valor=float(v))
                    for k, v in detalle.items()
                    if isinstance(v, int | float)
                ],
            )
        )
    return SalidaPublicacion(versiones=versiones, rubricas=rubricas)


async def _regeneracion(db: aiosqlite.Connection) -> SalidaRegeneracion:
    peticiones = []
    for a in await _filas(
        db,
        "SELECT momento, despues_json FROM audit_log WHERE accion = 'peticion:lector' ORDER BY id",
    ):
        datos = _json(a["despues_json"]) or {}
        peticiones.append(
            Peticion(
                momento=str(a["momento"]),
                texto=str(datos.get("texto", "")),
                fragmento=datos.get("fragmento"),
                capitulo=datos.get("capitulo"),
            )
        )
    return SalidaRegeneracion(
        peticiones=peticiones,
        ediciones=[
            EdicionHumana(
                tabla=str(e["tabla"]),
                fila_id=int(e["fila_id"]),
                campo=str(e["campo"]),
                antes=e["antes"],
                despues=e["despues"],
                motivo=e["motivo"],
            )
            for e in await _filas(db, "SELECT * FROM edicion_humana ORDER BY id")
        ],
    )


async def salida_de(carpeta: Path, fase: str) -> SalidaDeFase:
    ruta = carpeta / f"{carpeta.name}.db"
    if not ruta.exists():
        return SalidaDeFase(fase=fase, ejecuciones=[], decisiones=[])
    async with abrir_novela(ruta) as db:
        ejecuciones = [
            Ejecucion(
                id=int(f["id"]),
                fase=str(f["fase"]),
                estado=str(f["estado"]),
                inicio=str(f["inicio"]),
                fin=f["fin"],
                tokens_in=int(f["tokens_in"]),
                tokens_out=int(f["tokens_out"]),
                coste_usd=float(f["coste_usd"]),
                modelo=f["modelo"],
            )
            for f in await _filas(db, "SELECT * FROM fase_run WHERE fase = ? ORDER BY id", fase)
        ]
        decisiones = [
            Decision(
                gate_id=int(g["id"]),
                estado=str(g["estado"]),
                decision=g["decision"],
                comentario=g["comentario"],
                decidido_en=g["decidido_en"],
            )
            for g in await _filas(
                db,
                "SELECT g.* FROM gate g JOIN fase_run f ON f.id = g.fase_run_id "
                "WHERE f.fase = ? ORDER BY g.id",
                fase,
            )
        ]
        salida = SalidaDeFase(fase=fase, ejecuciones=ejecuciones, decisiones=decisiones)
        if fase == "intake":
            salida.encargo = await _encargo(db, carpeta)
        elif fase == "investigation":
            salida.investigacion = await _investigacion(db)
        elif fase == "plotting":
            salida.trama = await _trama(db)
        elif fase == "writing":
            salida.escritura = await _escritura(db)
        elif fase == "publication":
            salida.publicacion = await _publicacion(db)
        else:
            salida.regeneracion = await _regeneracion(db)
    return salida


# --- Endpoints ------------------------------------------------------------------------


@router.get("/{nombre}/fases/{fase}")
async def salida(nombre: str, fase: str, peticion: Request) -> SalidaDeFase:
    """La salida de una fase por su nombre castellano: `encargo`, `investigacion`, …"""
    if fase not in FASE_DE_URL:
        raise NovelaNoEncontrada(f"No hay ninguna fase llamada {fase}")
    return await salida_de(carpeta_de(nombre, _settings(peticion)), FASE_DE_URL[fase])


@router.get("/{nombre}/intentos/{capitulo_version}")
async def intento(nombre: str, capitulo_version: int, peticion: Request) -> TextoDeIntento:
    """El texto de un intento de capítulo, con sus incidencias."""
    carpeta = carpeta_de(nombre, _settings(peticion))
    ruta = carpeta / f"{carpeta.name}.db"
    if not ruta.exists():
        raise NovelaNoEncontrada(f"{nombre} todavia no tiene capitulos")
    async with abrir_novela(ruta) as db:
        filas = await _filas(
            db,
            """
            SELECT cv.*, pc.numero FROM capitulo_version cv
              JOIN plan_capitulo pc ON pc.id = cv.capitulo_id WHERE cv.id = ?
            """,
            capitulo_version,
        )
        if not filas:
            raise NovelaNoEncontrada(f"No hay ningun intento {capitulo_version}")
        v = filas[0]
        paquete = await _filas(
            db,
            "SELECT tokens FROM paquete_contexto WHERE capitulo_version_id = ? LIMIT 1",
            capitulo_version,
        )
        return TextoDeIntento(
            id=int(v["id"]),
            capitulo=int(v["numero"]),
            intento=int(v["intento"]),
            estado=str(v["estado"]),
            palabras=int(v["palabras"]),
            texto=str(v["texto"]),
            incidencias=await _incidencias(db, int(v["id"])),
            tokens_de_contexto=int(paquete[0]["tokens"]) if paquete else None,
        )


@router.get("/{nombre}/registros/{registro}", response_class=PlainTextResponse)
async def registro(nombre: str, registro: str, peticion: Request) -> str:
    """El final del registro de un proceso lanzado desde la interfaz."""
    carpeta = carpeta_de(nombre, _settings(peticion))
    elegido = next((r for r in registros_de(carpeta) if r.name == Path(registro).name), None)
    if elegido is None:
        raise NovelaNoEncontrada(f"No hay ningun registro {registro}")
    datos = elegido.read_bytes()[-BYTES_DE_REGISTRO:]
    return datos.decode("utf-8", errors="replace")
