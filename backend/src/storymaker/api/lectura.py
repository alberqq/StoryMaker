"""spec: §5 · arq: §16.4

Los endpoints de lectura: la superficie que el frontend consume.

Todos son `GET`, ninguno escribe y ninguno lleva autenticación. **Es una decisión declarada
y no un olvido**: ningún endpoint reanuda una ejecución —los gates se deciden con la CLI—,
de modo que lo que queda abierto es leer, y leer una novela que corre en la máquina del
Autor no justifica montar usuarios y sesiones. Queda como riesgo aceptado U-17.

Lo que devuelven sale del **manifiesto** y no de «los capítulos aprobados»: una versión es
exactamente la lista de `capitulo_version` que la componen, y servir otra cosa enseñaría una
novela que ningún manifiesto describe.

Cada respuesta declara su modelo, y no por estética: el frontend **deriva sus tipos de
transporte del OpenAPI** que FastAPI publica, y un `dict[str, Any]` ahí se traduce en un
tipo que no dice nada. Con el modelo declarado, un campo renombrado aquí rompe la
construcción del frontend en lugar de romper la pantalla el día de la demo.
"""

from __future__ import annotations

import json
import re
from typing import Any

import aiosqlite
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from storymaker.api import novelas
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela
from storymaker.commons.db.repos import canon, texto
from storymaker.commons.errores import NovelaNoEncontrada
from storymaker.publication import manifiesto
from storymaker.regeneration import diff

router = APIRouter(prefix="/novelas", tags=["lectura"])


# --- Modelos de respuesta ------------------------------------------------------------


class FichaNovela(BaseModel):
    nombre: str
    titulo: str
    fase: str
    versiones: int
    gate_abierto: int | None = None
    ocupada: bool = False


class VersionPublicada(BaseModel):
    numero: int
    creada_en: str
    #: La media de la rúbrica del juez, o nada si la versión no guardó puntuación.
    puntuacion: float | None = None


class FichaConHistorial(FichaNovela):
    historial: list[VersionPublicada]


class CapituloDelManifiesto(BaseModel):
    id: int
    numero: int
    titulo: str | None = None
    palabras: int
    resumen: str | None = None


class Licencia(BaseModel):
    alteracion: str
    justificacion: str


class Paratexto(BaseModel):
    """Con lo que se arma la portada: título, dedicatoria y nota del autor."""

    titulo: str
    homenajeado: str | None = None
    ocasion: str | None = None
    licencias: list[Licencia]


class Manifiesto(BaseModel):
    brief_hash: str | None = None
    sello_corpus_hash: str | None = None
    embeddings: str | None = None


class VersionDeNovela(BaseModel):
    numero: int
    #: La versión inmediatamente anterior, si la hay. Sin ella no hay nada que marcar.
    anterior: int | None = None
    capitulos: list[CapituloDelManifiesto]
    paratexto: Paratexto
    manifiesto: Manifiesto


class TextoDeCapitulo(BaseModel):
    orden: int
    titulo: str | None = None
    texto: str
    palabras: int
    total: int


class FichaPersonaje(BaseModel):
    id: int
    nombre: str
    tipo: str
    estatus: str
    rasgos: list[str]
    es_homenajeado: bool
    relacion_con_homenajeado: str | None = None
    capitulos: list[int]


class FichaEscenario(BaseModel):
    id: int
    #: El nombre con el que se titula: el del lugar o el arranque de la descripción.
    nombre: str
    lugar: str | None = None
    lugar_de_epoca: str | None = None
    descripcion: str | None = None
    capitulos: list[int]


class Fichas(BaseModel):
    personajes: list[FichaPersonaje]
    escenarios: list[FichaEscenario]


class CapituloCambiado(BaseModel):
    capitulo: int
    estado: str


class Diferencias(BaseModel):
    version_a: int
    version_b: int
    cambios: list[CapituloCambiado]
    resumen: str


# --- Consultas auxiliares ------------------------------------------------------------

#: Donde acaba el nombre de un lugar dentro de su descripción: la primera puntuación o la
#: primera cláusula de detalle. «Taller de imprenta con máquinas de prensa, …» se llama
#: «Taller de imprenta».
_CORTE_DEL_NOMBRE = re.compile(
    r"[,.;:()\n]|\s(?:con|donde|que|llen[oa]s?|en el que|en la que|cuyo|cuya)\s",
    re.IGNORECASE,
)
_PALABRAS_DEL_NOMBRE = 6
_VACIAS_AL_FINAL = {
    "de",
    "del",
    "la",
    "el",
    "las",
    "los",
    "en",
    "por",
    "y",
    "a",
    "al",
    "con",
    "un",
    "una",
}


def nombre_corto(descripcion: str) -> str:
    """El arranque de una descripción, como nombre: hasta el primer corte, seis palabras."""
    arranque = _CORTE_DEL_NOMBRE.split(descripcion.strip(), maxsplit=1)[0].strip()
    palabras = arranque.split()
    recortado = len(palabras) > _PALABRAS_DEL_NOMBRE
    palabras = palabras[:_PALABRAS_DEL_NOMBRE]
    while recortado and len(palabras) > 1 and palabras[-1].lower() in _VACIAS_AL_FINAL:
        palabras.pop()
    nombre = " ".join(palabras) + ("…" if recortado else "")
    return nombre[:1].upper() + nombre[1:]


def nombre_de_escenario(escenario_id: int, lugar: Any, descripcion: Any) -> str:
    """El nombre con el que se titula un escenario, el mismo en todas las pantallas.

    El del lugar del corpus si está enlazado a uno; si no, el arranque de su descripción. El
    arquitecto solo escribe una descripción, y titular con ella ponía un párrafo por nombre.
    """
    if lugar:
        return str(lugar)
    if descripcion and str(descripcion).strip():
        return nombre_corto(str(descripcion))
    return f"Escenario {escenario_id}"


def _settings(peticion: Request) -> Settings:
    return peticion.app.state.settings  # type: ignore[no-any-return]


async def _version_id(db: aiosqlite.Connection, nombre: str, numero: int) -> int:
    async with db.execute("SELECT id FROM version_novela WHERE numero = ?", (numero,)) as cursor:
        fila = await cursor.fetchone()
    if fila is None:
        raise NovelaNoEncontrada(f"La novela {nombre} no tiene version {numero}")
    return int(fila["id"])


def _media_del_juez(crudo: str | None) -> float | None:
    """La nota media de la rúbrica, leída con indulgencia: un JSON raro no tumba la lista."""
    if not crudo:
        return None
    try:
        valor: Any = json.loads(crudo)
    except ValueError:
        return None
    if isinstance(valor, int | float):
        return float(valor)
    if isinstance(valor, dict):
        puntuaciones = valor.get("puntuaciones")
        if isinstance(puntuaciones, list) and puntuaciones:
            notas: list[float] = [
                float(p["valor"])
                for p in puntuaciones
                if isinstance(p, dict) and isinstance(p.get("valor"), int | float)
            ]
            if notas:
                return round(sum(notas) / len(notas), 2)
        media = valor.get("media")
        if isinstance(media, int | float):
            return float(media)
    return None


def _rasgos(crudo: str | None) -> list[str]:
    if not crudo:
        return []
    try:
        valor: Any = json.loads(crudo)
    except ValueError:
        return [crudo]
    if isinstance(valor, list):
        return [str(r) for r in valor]
    if isinstance(valor, dict):
        return [f"{k}: {v}" for k, v in valor.items()]
    return [str(valor)]


async def _paratexto(db: aiosqlite.Connection) -> Paratexto:
    """Título, homenajeado, ocasión y Licencias declaradas.

    El homenajeado se escribe **como lo fija el canon**, que es el nombre que el validador
    `nombres_exactos` exige en la prosa; el brief solo cubre el caso de una novela cuyo
    canon todavía no lo enlazó. La ocasión solo vive en el brief.
    """
    obra = await canon.obra(db)
    titulo = str(obra["titulo"]) if obra is not None and obra["titulo"] else "Sin titulo"

    homenajeado: str | None = None
    if obra is not None and obra["homenajeado_id"] is not None:
        async with db.execute(
            "SELECT nombre FROM canon_personaje WHERE id = ?", (obra["homenajeado_id"],)
        ) as cursor:
            fila = await cursor.fetchone()
        homenajeado = str(fila["nombre"]) if fila is not None else None

    ocasion: str | None = None
    async with db.execute("SELECT json FROM intake_brief ORDER BY id DESC LIMIT 1") as cursor:
        brief = await cursor.fetchone()
    if brief is not None:
        try:
            datos = json.loads(str(brief["json"]))
        except ValueError:
            datos = {}
        ocasion = datos.get("ocasion") or None
        homenajeado = homenajeado or datos.get("nombre_homenajeado") or None

    async with db.execute(
        "SELECT alteracion, justificacion FROM canon_licencia WHERE declarada = 1 ORDER BY id"
    ) as cursor:
        licencias = [
            Licencia(alteracion=str(f["alteracion"]), justificacion=str(f["justificacion"]))
            for f in await cursor.fetchall()
        ]

    return Paratexto(titulo=titulo, homenajeado=homenajeado, ocasion=ocasion, licencias=licencias)


async def _numeros_de_la_version(db: aiosqlite.Connection, version_id: int) -> set[int]:
    async with db.execute(
        """
        SELECT pc.numero
          FROM version_capitulo vc
          JOIN capitulo_version cv ON cv.id = vc.capitulo_version_id
          JOIN plan_capitulo pc ON pc.id = cv.capitulo_id
         WHERE vc.version_id = ?
        """,
        (version_id,),
    ) as cursor:
        return {int(f["numero"]) for f in await cursor.fetchall()}


def _capitulos(crudo: Any, validos: set[int]) -> list[int]:
    return sorted({int(n) for n in str(crudo or "").split(",") if n} & validos)


# --- Endpoints ------------------------------------------------------------------------


@router.get("/{nombre}")
async def ficha(nombre: str, peticion: Request) -> FichaConHistorial:
    """Fase, gate abierto si lo hay, y las versiones publicadas con fecha y puntuación."""
    ruta = await novelas.exigir(nombre, _settings(peticion))
    f = await novelas.ficha(ruta)
    async with abrir_novela(ruta) as db:
        async with db.execute(
            "SELECT numero, creada_en, judge_score_json FROM version_novela ORDER BY numero"
        ) as cursor:
            historial = [
                VersionPublicada(
                    numero=int(v["numero"]),
                    creada_en=str(v["creada_en"]),
                    puntuacion=_media_del_juez(v["judge_score_json"]),
                )
                for v in await cursor.fetchall()
            ]
    return FichaConHistorial(
        nombre=f.nombre,
        titulo=f.titulo,
        fase=f.fase,
        versiones=f.versiones,
        gate_abierto=f.gate_abierto,
        ocupada=f.ocupada,
        historial=historial,
    )


@router.get("/{nombre}/versiones/{numero}")
async def version(nombre: str, numero: int, peticion: Request) -> VersionDeNovela:
    """El manifiesto de una versión, sus capítulos en orden y el bloque de paratexto."""
    ruta = await novelas.exigir(nombre, _settings(peticion))
    async with abrir_novela(ruta) as db:
        version_id = await _version_id(db, nombre, numero)
        async with db.execute(
            """
            SELECT cv.id, cv.palabras, cv.resumen, pc.numero, pc.titulo
              FROM version_capitulo vc
              JOIN capitulo_version cv ON cv.id = vc.capitulo_version_id
              JOIN plan_capitulo pc ON pc.id = cv.capitulo_id
             WHERE vc.version_id = ?
             ORDER BY pc.numero
            """,
            (version_id,),
        ) as cursor:
            capitulos = list(await cursor.fetchall())
        async with db.execute(
            "SELECT MAX(numero) AS n FROM version_novela WHERE numero < ?", (numero,)
        ) as cursor:
            previa = await cursor.fetchone()
        registro = await manifiesto.de_version(db, version_id)
        paratexto = await _paratexto(db)

    return VersionDeNovela(
        numero=numero,
        anterior=int(previa["n"]) if previa is not None and previa["n"] is not None else None,
        capitulos=[
            CapituloDelManifiesto(
                id=int(c["id"]),
                numero=int(c["numero"]),
                titulo=str(c["titulo"]) if c["titulo"] else None,
                palabras=int(c["palabras"]),
                resumen=c["resumen"],
            )
            for c in capitulos
        ],
        paratexto=paratexto,
        manifiesto=Manifiesto(
            brief_hash=str(registro["brief_hash"]) if registro else None,
            sello_corpus_hash=str(registro["sello_corpus_hash"]) if registro else None,
            embeddings=str(registro["embeddings_json"]) if registro else None,
        ),
    )


@router.get("/{nombre}/versiones/{numero}/capitulos/{orden}")
async def capitulo(nombre: str, numero: int, orden: int, peticion: Request) -> TextoDeCapitulo:
    """El texto del capítulo **tal como esa versión lo fija**.

    Se pide por versión y no «el último»: un capítulo no regenerado se comparte entre
    versiones, y uno regenerado tiene texto distinto en cada una.
    """
    ruta = await novelas.exigir(nombre, _settings(peticion))
    async with abrir_novela(ruta) as db:
        capitulos = await texto.capitulos_de_version(db, await _version_id(db, nombre, numero))
        if orden < 1 or orden > len(capitulos):
            raise NovelaNoEncontrada(f"La version {numero} no tiene capitulo {orden}")
        elegido = capitulos[orden - 1]
        async with db.execute(
            "SELECT titulo FROM plan_capitulo WHERE id = ?", (elegido["capitulo_id"],)
        ) as cursor:
            plan = await cursor.fetchone()

    return TextoDeCapitulo(
        orden=orden,
        titulo=str(plan["titulo"]) if plan is not None and plan["titulo"] else None,
        texto=str(elegido["texto"]),
        palabras=int(elegido["palabras"]),
        total=len(capitulos),
    )


@router.get("/{nombre}/versiones/{numero}/personajes")
async def personajes(nombre: str, numero: int, peticion: Request) -> Fichas:
    """Fichas de personajes y lugares, con los capítulos **de esa versión** en que aparecen.

    La ficha cuelga de una versión y no de la novela: el canon es vivo, pero «los capítulos
    en los que aparece» solo tiene respuesta dentro de un manifiesto.
    """
    ruta = await novelas.exigir(nombre, _settings(peticion))
    async with abrir_novela(ruta) as db:
        validos = await _numeros_de_la_version(db, await _version_id(db, nombre, numero))
        obra = await canon.obra(db)
        homenajeado_id = obra["homenajeado_id"] if obra is not None else None

        async with db.execute(
            """
            SELECT p.id, p.nombre, p.tipo, p.estatus, p.rasgos_json,
                   GROUP_CONCAT(DISTINCT c.numero) AS capitulos
              FROM canon_personaje p
              LEFT JOIN plan_escena_personaje ep ON ep.personaje_id = p.id
              LEFT JOIN plan_escena e ON e.id = ep.escena_id
              LEFT JOIN plan_capitulo c ON c.id = e.capitulo_id
             GROUP BY p.id
             ORDER BY p.id
            """
        ) as cursor:
            filas_personajes = list(await cursor.fetchall())

        relaciones: dict[int, str] = {}
        if homenajeado_id is not None:
            async with db.execute(
                "SELECT a_id, b_id, tipo FROM canon_relacion WHERE a_id = ? OR b_id = ?",
                (homenajeado_id, homenajeado_id),
            ) as cursor:
                for r in await cursor.fetchall():
                    otro = int(r["b_id"]) if int(r["a_id"]) == homenajeado_id else int(r["a_id"])
                    relaciones.setdefault(otro, str(r["tipo"]))

        async with db.execute(
            """
            SELECT s.id, s.descripcion, m.nombre AS lugar, m.nombre_epoca,
                   GROUP_CONCAT(DISTINCT c.numero) AS capitulos
              FROM canon_escenario s
              LEFT JOIN mundo_entidad m ON m.id = s.lugar_entidad_id
              LEFT JOIN plan_escena e ON e.escenario_id = s.id
              LEFT JOIN plan_capitulo c ON c.id = e.capitulo_id
             GROUP BY s.id
             ORDER BY s.id
            """
        ) as cursor:
            filas_escenarios = list(await cursor.fetchall())

    return Fichas(
        personajes=[
            FichaPersonaje(
                id=int(f["id"]),
                nombre=str(f["nombre"]),
                tipo=str(f["tipo"]),
                estatus=str(f["estatus"] or ""),
                rasgos=_rasgos(f["rasgos_json"]),
                es_homenajeado=homenajeado_id is not None and int(f["id"]) == homenajeado_id,
                relacion_con_homenajeado=relaciones.get(int(f["id"])),
                capitulos=_capitulos(f["capitulos"], validos),
            )
            for f in filas_personajes
        ],
        escenarios=[
            FichaEscenario(
                id=int(f["id"]),
                nombre=nombre_de_escenario(int(f["id"]), f["lugar"], f["descripcion"]),
                lugar=str(f["lugar"]) if f["lugar"] else None,
                lugar_de_epoca=str(f["nombre_epoca"]) if f["nombre_epoca"] else None,
                descripcion=str(f["descripcion"]) if f["descripcion"] else None,
                capitulos=_capitulos(f["capitulos"], validos),
            )
            for f in filas_escenarios
        ],
    )


@router.get(
    "/{nombre}/versiones/{numero}/pdf",
    response_class=FileResponse,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def pdf(nombre: str, numero: int, peticion: Request) -> FileResponse:
    """El PDF que `publish` imprimió junto al fichero de la novela, para descargarlo."""
    ruta = await novelas.exigir(nombre, _settings(peticion))
    fichero = ruta.with_suffix(f".v{numero}.pdf")
    if not fichero.is_file():
        raise NovelaNoEncontrada(
            f"La version {numero} de {nombre} no tiene PDF: no existe o no se pudo imprimir."
        )
    return FileResponse(fichero, media_type="application/pdf", filename=fichero.name)


@router.get("/{nombre}/versiones/{a}/diff/{b}")
async def diferencias(nombre: str, a: int, b: int, peticion: Request) -> Diferencias:
    """Qué capítulos cambian entre dos versiones. Un `JOIN`, no un diff de texto."""
    ruta = await novelas.exigir(nombre, _settings(peticion))
    async with abrir_novela(ruta) as db:
        id_a = await _version_id(db, nombre, a)
        id_b = await _version_id(db, nombre, b)
        resultado = await diff.entre(db, id_a, id_b)

    return Diferencias(
        version_a=a,
        version_b=b,
        cambios=[CapituloCambiado(capitulo=c.numero, estado=c.estado) for c in resultado.cambiados],
        resumen=resultado.como_texto(),
    )
