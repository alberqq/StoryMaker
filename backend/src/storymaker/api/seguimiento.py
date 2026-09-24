"""spec: §5.2 · arq: §16.5

**El seguimiento se lee del fichero, no se empuja desde memoria.**

La interfaz pregunta cada pocos segundos, y todo lo que aquí se responde se recalcula en cada
consulta a partir de la carpeta de la novela: su cerrojo dice si algo trabaja, sus registros
de proceso dicen si algo acaba de lanzarse, y su fichero dice todo lo demás. El servidor no
guarda ningún proceso, así que reiniciarlo no hace perder ningún seguimiento: no lo tenía.

Lo que se devuelve está **interpretado**: el estado de la novela, el de cada fase y una
actividad en frases. El registro literal del proceso existe y se puede consultar, pero no es
lo que la pantalla enseña.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal

import aiosqlite
from fastapi import APIRouter, Request
from pydantic import BaseModel

from storymaker.api.lanzador import carpeta_de_registros
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela, ruta_de_novela
from storymaker.commons.errores import NovelaNoEncontrada
from storymaker.commons.graph import cerrojo

router = APIRouter(prefix="/novelas", tags=["seguimiento"])

#: El orden de las fases, con el nombre que llevan en `fase_run`.
FASES = ("intake", "investigation", "plotting", "writing", "publication", "regeneration")

#: Cuánto dura «arrancando»: lo que tarda la CLI en tomar el cerrojo tras ser lanzada.
SEGUNDOS_ARRANCANDO = 20

#: El encargo que escribe `POST /novelas` en la carpeta antes de que exista el fichero.
FICHERO_DE_ENCARGO = "encargo.json"

EstadoNovela = Literal[
    "en_marcha",
    "arrancando",
    "detenida",
    "esperando_autor",
    "aparcada",
    "fallida",
    "terminada",
    "en_pausa",
]

EstadoFase = Literal[
    "pendiente", "en_curso", "esperando_gate", "completada", "fallida", "aparcada", "abortada"
]


# --- Modelos -------------------------------------------------------------------------


class GatePendiente(BaseModel):
    id: int
    fase: str
    abierto_en: str | None = None


class Ejecucion(BaseModel):
    id: int
    fase: str
    estado: str
    inicio: str
    fin: str | None = None
    tokens_in: int
    tokens_out: int
    coste_usd: float
    modelo: str | None = None


class FaseDelPanel(BaseModel):
    fase: str
    estado: EstadoFase
    #: El estado no sale de `fase_run`, sino de que la fase dejó salida.
    deducida: bool
    tiene_salida: bool
    ejecuciones: list[Ejecucion]
    tokens_in: int
    tokens_out: int
    coste_usd: float
    inicio: str | None = None
    fin: str | None = None


class CapituloDelPanel(BaseModel):
    numero: int
    titulo: str | None = None
    estado: Literal["pendiente", "en_curso", "aprobado", "invalidado", "descartado"]
    intentos: int
    palabras: int | None = None


class Suceso(BaseModel):
    momento: str
    tipo: Literal["fase", "capitulo", "gate", "edicion", "accion", "peticion"]
    texto: str
    detalle: str | None = None


class IncidenciaReciente(BaseModel):
    capitulo: int | None = None
    validador: str
    severidad: str
    mensaje: str


class Consumo(BaseModel):
    tokens_in: int
    tokens_out: int
    coste_usd: float


class Proceso(BaseModel):
    cerrojo: bool
    pid: int | None = None
    vivo: bool


class VersionDelPanel(BaseModel):
    numero: int
    creada_en: str
    #: Si `publish` llegó a imprimir su PDF junto al fichero de la novela.
    pdf: bool = False


class TarjetaNovela(BaseModel):
    nombre: str
    titulo: str
    homenajeado: str | None = None
    fase: str
    estado: EstadoNovela
    gate: GatePendiente | None = None
    capitulos_aprobados: int
    capitulos_total: int
    coste_usd: float
    versiones: int
    actualizada: str | None = None


class Panel(TarjetaNovela):
    fases: list[FaseDelPanel]
    capitulos: list[CapituloDelPanel]
    actividad: list[Suceso]
    incidencias: list[IncidenciaReciente]
    consumo: Consumo
    proceso: Proceso
    registros: list[str]
    versiones_publicadas: list[VersionDelPanel]
    trabajando_en: str | None = None


class FilaEditable(BaseModel):
    objeto: Literal["hecho", "personaje", "escenario", "glosario"]
    fila_id: int
    etiqueta: str
    campos: dict[str, str | None]
    editable: bool


class Candidato(BaseModel):
    descripcion: str
    capitulos_a_regenerar: list[int]
    capitulos_a_revisar: list[int]
    coste: str


class PeticionDeRegeneracion(BaseModel):
    texto: str
    fragmento: str | None = None
    capitulo: int | None = None
    version: int | None = None
    candidatos: list[Candidato]


class Recuento(BaseModel):
    etiqueta: str
    valor: int


class Conversacion(BaseModel):
    """La entrevista de Intake hasta ahora: lo que se contó, lo que se respondió, lo cerrado."""

    descripcion: str | None = None
    #: Las respuestas de cada ronda anterior, en orden: los comentarios de «rehacer».
    rondas: list[str]
    #: El brief, si el entrevistador ya lo cerró.
    brief: dict[str, Any] | None = None


class GateDeNovela(BaseModel):
    id: int
    fase: str
    abierto_en: str | None = None
    recuentos: list[Recuento]
    preguntas: list[str]
    peticion: PeticionDeRegeneracion | None = None
    conversacion: Conversacion | None = None
    editables: list[FilaEditable]
    corpus_sellado: bool
    decisiones: list[str]


# --- Lectura del fichero -------------------------------------------------------------


def _settings(peticion: Request) -> Settings:
    return peticion.app.state.settings  # type: ignore[no-any-return]


def carpetas(settings: Settings) -> list[Path]:
    """Las carpetas del registro: las que tienen su fichero o, recién encargadas, su encargo."""
    raiz = settings.directorio_proyectos
    if not raiz.exists():
        return []
    return sorted(
        c
        for c in raiz.iterdir()
        if c.is_dir() and ((c / f"{c.name}.db").exists() or (c / FICHERO_DE_ENCARGO).exists())
    )


def carpeta_de(nombre: str, settings: Settings) -> Path:
    """La carpeta de una novela, o `NovelaNoEncontrada`. El nombre no sale del registro."""
    carpeta = ruta_de_novela(nombre, settings.directorio_proyectos).parent
    if (
        not (carpeta / f"{carpeta.name}.db").exists()
        and not (carpeta / FICHERO_DE_ENCARGO).exists()
    ):
        raise NovelaNoEncontrada(f"No hay ninguna novela llamada {nombre}")
    return carpeta


def registros_de(carpeta: Path) -> list[Path]:
    registros = carpeta_de_registros(carpeta)
    if not registros.exists():
        return []
    return sorted(registros.glob("*.log"), key=lambda p: p.name, reverse=True)


def _recien_lanzada(carpeta: Path) -> bool:
    ultimos = registros_de(carpeta)
    return bool(ultimos) and time.time() - ultimos[0].stat().st_mtime < SEGUNDOS_ARRANCANDO


def _proceso(ruta: Path) -> Proceso:
    if not cerrojo.esta_tomado(ruta):
        return Proceso(cerrojo=False, vivo=False)
    pid = cerrojo.pid_del_cerrojo(ruta)
    return Proceso(cerrojo=True, pid=pid, vivo=pid is not None and cerrojo.proceso_vivo(pid))


async def _uno(db: aiosqlite.Connection, consulta: str, *parametros: Any) -> Any:
    async with db.execute(consulta, parametros) as cursor:
        fila = await cursor.fetchone()
    return fila[0] if fila is not None else None


async def _filas(db: aiosqlite.Connection, consulta: str, *parametros: Any) -> list[Any]:
    async with db.execute(consulta, parametros) as cursor:
        return list(await cursor.fetchall())


async def _hay(db: aiosqlite.Connection, tabla: str) -> bool:
    return bool(await _uno(db, f"SELECT EXISTS (SELECT 1 FROM {tabla})"))  # noqa: S608


async def _tiene_salida(db: aiosqlite.Connection, fase: str) -> bool:
    if fase == "intake":
        return await _hay(db, "intake_brief") or await _hay(db, "intake_dato")
    if fase == "investigation":
        return await _hay(db, "mundo_hecho")
    if fase == "plotting":
        return await _hay(db, "plan_capitulo")
    if fase == "writing":
        return await _hay(db, "capitulo_version")
    if fase == "publication":
        return await _hay(db, "version_novela")
    return bool(await _uno(db, "SELECT COUNT(*) FROM fase_run WHERE fase = 'regeneration'"))


async def gate_pendiente(db: aiosqlite.Connection) -> GatePendiente | None:
    fila = await _filas(
        db,
        """
        SELECT g.id, f.fase, COALESCE(g.notificado_en, f.fin, f.inicio) AS abierto
          FROM gate g JOIN fase_run f ON f.id = g.fase_run_id
         WHERE g.estado = 'pendiente' ORDER BY g.id DESC LIMIT 1
        """,
    )
    if not fila:
        return None
    return GatePendiente(
        id=int(fila[0]["id"]), fase=str(fila[0]["fase"]), abierto_en=fila[0]["abierto"]
    )


async def fases_de(db: aiosqlite.Connection) -> list[FaseDelPanel]:
    """Las seis fases, cada una con su estado aunque no tenga filas.

    Sale de su última fila de `fase_run` y, si no tiene ninguna, de si dejó salida. Una fase
    con salida seguida de otra que ya trabajó está terminada aunque su fila diga otra cosa:
    es el caso de las novelas empezadas antes de que cada fase abriera y cerrara su fila.
    """
    salidas = {f: await _tiene_salida(db, f) for f in FASES}
    ejecuciones: dict[str, list[Ejecucion]] = {f: [] for f in FASES}
    for fila in await _filas(db, "SELECT * FROM fase_run ORDER BY id"):
        ejecuciones[str(fila["fase"])].append(
            Ejecucion(
                id=int(fila["id"]),
                fase=str(fila["fase"]),
                estado=str(fila["estado"]),
                inicio=str(fila["inicio"]),
                fin=fila["fin"],
                tokens_in=int(fila["tokens_in"]),
                tokens_out=int(fila["tokens_out"]),
                coste_usd=float(fila["coste_usd"]),
                modelo=fila["modelo"],
            )
        )

    lineales = FASES[:5]
    resultado = []
    for fase in FASES:
        filas = ejecuciones[fase]
        posteriores = lineales[lineales.index(fase) + 1 :] if fase in lineales else ()
        avanzada = any(salidas[p] or ejecuciones[p] for p in posteriores)
        deducida = False
        estado: EstadoFase
        if filas:
            estado = filas[-1].estado  # type: ignore[assignment]
            if estado != "completada" and salidas[fase] and avanzada:
                estado, deducida = "completada", True
        elif salidas[fase]:
            estado, deducida = "completada", True
        else:
            estado = "pendiente"
        abiertas = [e for e in filas if e.fin is None]
        resultado.append(
            FaseDelPanel(
                fase=fase,
                estado=estado,
                deducida=deducida,
                tiene_salida=salidas[fase],
                ejecuciones=filas,
                tokens_in=sum(e.tokens_in for e in filas),
                tokens_out=sum(e.tokens_out for e in filas),
                coste_usd=round(sum(e.coste_usd for e in filas), 6),
                inicio=filas[0].inicio if filas else None,
                fin=None if abiertas or not filas else filas[-1].fin,
            )
        )
    return resultado


def fase_actual(fases: list[FaseDelPanel]) -> str:
    """La más avanzada que ha trabajado o dejado salida; Regeneración si está abierta."""
    regeneracion = fases[-1]
    if regeneracion.ejecuciones and regeneracion.estado not in ("completada", "abortada"):
        return "regeneration"
    actual = "intake"
    for fase in fases[:5]:
        if fase.ejecuciones or fase.tiene_salida:
            actual = fase.fase
    return actual


async def estado_de(
    carpeta: Path, db: aiosqlite.Connection | None, gate: GatePendiente | None
) -> EstadoNovela:
    """El estado de la novela, con la precedencia de spec §5.2."""
    ruta = carpeta / f"{carpeta.name}.db"
    proceso = _proceso(ruta)
    if proceso.cerrojo:
        return "en_marcha" if proceso.vivo else "detenida"
    if db is None:
        return "arrancando" if _recien_lanzada(carpeta) else "fallida"
    if _recien_lanzada(carpeta):
        return "arrancando"
    if gate is not None:
        return "esperando_autor"
    if await _uno(db, "SELECT estado FROM gate ORDER BY id DESC LIMIT 1") == "aparcado":
        return "aparcada"
    if await _uno(db, "SELECT estado FROM fase_run ORDER BY id DESC LIMIT 1") == "fallida":
        return "fallida"
    abiertas = await _uno(db, "SELECT COUNT(*) FROM fase_run WHERE fin IS NULL")
    if await _hay(db, "version_novela") and not abiertas:
        return "terminada"
    return "en_pausa"


def _encargo_de(carpeta: Path) -> dict[str, Any]:
    fichero = carpeta / FICHERO_DE_ENCARGO
    if not fichero.exists():
        return {}
    try:
        datos = json.loads(fichero.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    return datos if isinstance(datos, dict) else {}


async def _homenajeado(db: aiosqlite.Connection, carpeta: Path) -> str | None:
    nombre = await _uno(
        db,
        "SELECT p.nombre FROM canon_obra o JOIN canon_personaje p ON p.id = o.homenajeado_id",
    )
    if nombre:
        return str(nombre)
    brief = await _uno(db, "SELECT json FROM intake_brief ORDER BY id DESC LIMIT 1")
    if brief:
        try:
            valor = json.loads(str(brief)).get("nombre_homenajeado")
        except (ValueError, AttributeError):
            valor = None
        if valor:
            return str(valor)
    return _homenajeado_del_encargo(carpeta)


def _homenajeado_del_encargo(carpeta: Path) -> str | None:
    homenajeado = _encargo_de(carpeta).get("homenajeado") or {}
    valor = homenajeado.get("nombre_homenajeado") if isinstance(homenajeado, dict) else None
    return str(valor) if valor else None


async def _tarjeta(carpeta: Path, db: aiosqlite.Connection | None) -> tuple[TarjetaNovela, Any]:
    if db is None:
        tarjeta = TarjetaNovela(
            nombre=carpeta.name,
            titulo=carpeta.name,
            homenajeado=_homenajeado_del_encargo(carpeta),
            fase="intake",
            estado=await estado_de(carpeta, None, None),
            capitulos_aprobados=0,
            capitulos_total=0,
            coste_usd=0.0,
            versiones=0,
        )
        return tarjeta, None
    gate = await gate_pendiente(db)
    fases = await fases_de(db)
    titulo = await _uno(db, "SELECT titulo FROM canon_obra LIMIT 1")
    total = await _uno(db, "SELECT COUNT(*) FROM plan_capitulo") or await _uno(
        db, "SELECT n_capitulos FROM canon_obra LIMIT 1"
    )
    aprobados = await _uno(
        db,
        "SELECT COUNT(DISTINCT capitulo_id) FROM capitulo_version WHERE estado = 'aprobado'",
    )
    actualizada = await _uno(
        db,
        """
        SELECT MAX(m) FROM (
          SELECT MAX(COALESCE(fin, inicio)) AS m FROM fase_run
          UNION ALL SELECT MAX(creado_en) FROM capitulo_version
          UNION ALL SELECT MAX(momento) FROM audit_log)
        """,
    )
    tarjeta = TarjetaNovela(
        nombre=carpeta.name,
        titulo=str(titulo) if titulo else carpeta.name,
        homenajeado=await _homenajeado(db, carpeta),
        fase=fase_actual(fases),
        estado=await estado_de(carpeta, db, gate),
        gate=gate,
        capitulos_aprobados=int(aprobados or 0),
        capitulos_total=int(total or 0),
        coste_usd=round(sum(f.coste_usd for f in fases), 6),
        versiones=int(await _uno(db, "SELECT COUNT(*) FROM version_novela") or 0),
        actualizada=actualizada,
    )
    return tarjeta, fases


async def _capitulos(db: aiosqlite.Connection) -> list[CapituloDelPanel]:
    capitulos = []
    for plan in await _filas(db, "SELECT id, numero, titulo FROM plan_capitulo ORDER BY numero"):
        intentos = await _filas(
            db,
            "SELECT estado, palabras FROM capitulo_version WHERE capitulo_id = ? ORDER BY id",
            plan["id"],
        )
        estados = [str(i["estado"]) for i in intentos]
        if "aprobado" in estados:
            estado = "aprobado"
        elif not estados:
            estado = "pendiente"
        elif estados[-1] == "invalidado":
            estado = "invalidado"
        else:
            estado = "en_curso"
        capitulos.append(
            CapituloDelPanel(
                numero=int(plan["numero"]),
                titulo=plan["titulo"],
                estado=estado,  # type: ignore[arg-type]
                intentos=len(intentos),
                palabras=int(intentos[-1]["palabras"]) if intentos else None,
            )
        )
    return capitulos


_NOMBRE_DE_FASE = {
    "intake": "Encargo",
    "investigation": "Investigación",
    "plotting": "Trama",
    "writing": "Escritura",
    "publication": "Publicación",
    "regeneration": "Regeneración",
}

_NOMBRE_DE_ESTADO = {
    "en_curso": "en curso",
    "esperando_gate": "espera tu decisión",
    "completada": "completada",
    "fallida": "fallida",
    "aparcada": "aparcada",
    "abortada": "abortada",
}


async def _actividad(db: aiosqlite.Connection) -> list[Suceso]:
    """Lo que ha pasado, en frases y con su momento. No es el registro del proceso."""
    sucesos: list[Suceso] = []
    for f in await _filas(db, "SELECT fase, estado, inicio, fin FROM fase_run"):
        nombre = _NOMBRE_DE_FASE.get(str(f["fase"]), str(f["fase"]))
        sucesos.append(Suceso(momento=str(f["inicio"]), tipo="fase", texto=f"Empieza {nombre}"))
        if f["fin"]:
            sucesos.append(
                Suceso(
                    momento=str(f["fin"]),
                    tipo="fase",
                    texto=f"{nombre}: {_NOMBRE_DE_ESTADO.get(str(f['estado']), f['estado'])}",
                )
            )
    for c in await _filas(
        db,
        """
        SELECT cv.creado_en, cv.intento, cv.estado, cv.palabras, pc.numero
          FROM capitulo_version cv JOIN plan_capitulo pc ON pc.id = cv.capitulo_id
        """,
    ):
        sucesos.append(
            Suceso(
                momento=str(c["creado_en"]),
                tipo="capitulo",
                texto=f"Capítulo {c['numero']}, intento {c['intento']}: {c['estado']}",
                detalle=f"{c['palabras']} palabras",
            )
        )
    for g in await _filas(
        db,
        """
        SELECT g.decision, g.comentario, g.decidido_en, g.notificado_en, f.fase
          FROM gate g JOIN fase_run f ON f.id = g.fase_run_id
        """,
    ):
        nombre = _NOMBRE_DE_FASE.get(str(g["fase"]), str(g["fase"]))
        if g["notificado_en"]:
            sucesos.append(
                Suceso(
                    momento=str(g["notificado_en"]),
                    tipo="gate",
                    texto=f"{nombre} espera tu decisión",
                )
            )
        if g["decidido_en"]:
            sucesos.append(
                Suceso(
                    momento=str(g["decidido_en"]),
                    tipo="gate",
                    texto=f"Gate de {nombre}: {g['decision']}",
                    detalle=g["comentario"],
                )
            )
    for a in await _filas(
        db, "SELECT momento, accion, objeto, despues_json FROM audit_log WHERE actor = 'autor'"
    ):
        accion = str(a["accion"])
        if accion.startswith("lanzar:"):
            texto, tipo = f"Lanzado desde la interfaz: {accion.removeprefix('lanzar:')}", "accion"
        elif accion == "peticion:lector":
            texto, tipo = "Petición de cambio del lector", "peticion"
        elif accion.startswith("cambio:"):
            texto, tipo = f"Edición de {accion.removeprefix('cambio:')} ({a['objeto']})", "edicion"
        else:
            texto, tipo = accion, "accion"
        sucesos.append(Suceso(momento=str(a["momento"]), tipo=tipo, texto=texto))  # type: ignore[arg-type]
    sucesos.sort(key=lambda s: s.momento, reverse=True)
    return sucesos[:40]


async def _incidencias_recientes(db: aiosqlite.Connection) -> list[IncidenciaReciente]:
    filas = await _filas(
        db,
        """
        SELECT i.validador, i.severidad, i.mensaje, pc.numero
          FROM incidencia i
          LEFT JOIN capitulo_version cv ON cv.id = i.capitulo_version_id
          LEFT JOIN plan_capitulo pc ON pc.id = cv.capitulo_id
         ORDER BY i.id DESC LIMIT 8
        """,
    )
    return [
        IncidenciaReciente(
            capitulo=f["numero"],
            validador=str(f["validador"]),
            severidad=str(f["severidad"]),
            mensaje=str(f["mensaje"]),
        )
        for f in filas
    ]


def _trabajando_en(estado: str, fase: str, capitulos: list[CapituloDelPanel]) -> str | None:
    if estado not in ("en_marcha", "arrancando"):
        return None
    nombre = _NOMBRE_DE_FASE.get(fase, fase)
    if fase == "writing":
        siguiente = next((c for c in capitulos if c.estado != "aprobado"), None)
        if siguiente is not None:
            return f"{nombre}: capítulo {siguiente.numero}, intento {siguiente.intentos + 1}"
    return nombre


async def panel_de(carpeta: Path) -> Panel:
    ruta = carpeta / f"{carpeta.name}.db"
    if not ruta.exists():
        tarjeta, _ = await _tarjeta(carpeta, None)
        return Panel(
            **tarjeta.model_dump(),
            fases=[
                FaseDelPanel(
                    fase=f,
                    estado="pendiente",
                    deducida=False,
                    tiene_salida=False,
                    ejecuciones=[],
                    tokens_in=0,
                    tokens_out=0,
                    coste_usd=0.0,
                )
                for f in FASES
            ],
            capitulos=[],
            actividad=[],
            incidencias=[],
            consumo=Consumo(tokens_in=0, tokens_out=0, coste_usd=0.0),
            proceso=_proceso(ruta),
            registros=[r.name for r in registros_de(carpeta)],
            versiones_publicadas=[],
            trabajando_en=_trabajando_en(tarjeta.estado, "intake", []),
        )
    async with abrir_novela(ruta) as db:
        tarjeta, fases = await _tarjeta(carpeta, db)
        capitulos = await _capitulos(db)
        actividad = await _actividad(db)
        incidencias = await _incidencias_recientes(db)
        versiones = [
            VersionDelPanel(
                numero=int(v["numero"]),
                creada_en=str(v["creada_en"]),
                pdf=ruta.with_suffix(f".v{int(v['numero'])}.pdf").is_file(),
            )
            for v in await _filas(
                db, "SELECT numero, creada_en FROM version_novela ORDER BY numero"
            )
        ]
    return Panel(
        **tarjeta.model_dump(),
        fases=fases,
        capitulos=capitulos,
        actividad=actividad,
        incidencias=incidencias,
        consumo=Consumo(
            tokens_in=sum(f.tokens_in for f in fases),
            tokens_out=sum(f.tokens_out for f in fases),
            coste_usd=round(sum(f.coste_usd for f in fases), 6),
        ),
        proceso=_proceso(ruta),
        registros=[r.name for r in registros_de(carpeta)],
        versiones_publicadas=versiones,
        trabajando_en=_trabajando_en(tarjeta.estado, tarjeta.fase, capitulos),
    )


# --- El gate -------------------------------------------------------------------------

#: Qué nodo de gate corresponde a cada fase, para reutilizar los recuentos del aviso.
_NODO_DEL_GATE = {
    "intake": "AwaitApproval",
    "investigation": "AwaitApproval2",
    "plotting": "AwaitApproval3",
    "writing": "AwaitApproval4",
}

#: Los campos que la edición humana directa puede tocar, por familia (arq. §8 y §16.5).
CAMPOS_EDITABLES: dict[str, tuple[str, ...]] = {
    "hecho": ("enunciado",),
    "personaje": ("nombre", "estatus", "objetivo", "miedo", "voz"),
    "escenario": ("descripcion",),
    "glosario": ("termino", "significado"),
}


async def corpus_sellado(db: aiosqlite.Connection) -> bool:
    return await _hay(db, "mundo_sello")


async def _editables(db: aiosqlite.Connection, sellado: bool) -> list[FilaEditable]:
    filas: list[FilaEditable] = []
    for h in await _filas(db, "SELECT id, enunciado, dimension FROM mundo_hecho ORDER BY id"):
        filas.append(
            FilaEditable(
                objeto="hecho",
                fila_id=int(h["id"]),
                etiqueta=str(h["dimension"]),
                campos={"enunciado": h["enunciado"]},
                editable=not sellado,
            )
        )
    for p in await _filas(
        db, "SELECT id, nombre, estatus, objetivo, miedo, voz FROM canon_personaje ORDER BY id"
    ):
        filas.append(
            FilaEditable(
                objeto="personaje",
                fila_id=int(p["id"]),
                etiqueta=str(p["nombre"]),
                campos={c: p[c] for c in CAMPOS_EDITABLES["personaje"]},
                editable=True,
            )
        )
    for e in await _filas(db, "SELECT id, descripcion FROM canon_escenario ORDER BY id"):
        filas.append(
            FilaEditable(
                objeto="escenario",
                fila_id=int(e["id"]),
                etiqueta=f"Escenario {e['id']}",
                campos={"descripcion": e["descripcion"]},
                editable=True,
            )
        )
    for g in await _filas(db, "SELECT id, termino, significado FROM canon_glosario ORDER BY id"):
        filas.append(
            FilaEditable(
                objeto="glosario",
                fila_id=int(g["id"]),
                etiqueta=str(g["termino"]),
                campos={"termino": g["termino"], "significado": g["significado"]},
                editable=True,
            )
        )
    return filas


async def _peticion(db: aiosqlite.Connection) -> PeticionDeRegeneracion | None:
    crudo = await _uno(
        db,
        "SELECT despues_json FROM audit_log WHERE accion = 'peticion:lector' "
        "ORDER BY id DESC LIMIT 1",
    )
    if not crudo:
        return None
    try:
        datos = json.loads(str(crudo))
    except ValueError:
        return None
    return PeticionDeRegeneracion(
        texto=str(datos.get("texto", "")),
        fragmento=datos.get("fragmento"),
        capitulo=datos.get("capitulo"),
        version=datos.get("version"),
        candidatos=[
            Candidato(
                descripcion=str(c.get("descripcion", "")),
                capitulos_a_regenerar=list(c.get("capitulos_a_regenerar", [])),
                capitulos_a_revisar=list(c.get("capitulos_a_revisar", [])),
                coste=str(c.get("coste", "")),
            )
            for c in datos.get("candidatos", [])
            if isinstance(c, dict)
        ],
    )


async def conversacion_de(db: aiosqlite.Connection, carpeta: Path) -> Conversacion:
    """La entrevista de Intake: la descripción del encargo, cada ronda y el brief si lo hay."""
    from storymaker.commons.db.repos import arnes

    descripcion = _encargo_de(carpeta).get("descripcion")
    brief = await _uno(db, "SELECT json FROM intake_brief ORDER BY id DESC LIMIT 1")
    try:
        cerrado = json.loads(str(brief)) if brief else None
    except ValueError:
        cerrado = None
    return Conversacion(
        descripcion=str(descripcion).strip() or None if descripcion else None,
        rondas=await arnes.comentarios_de_rehacer(db, "intake"),
        brief=cerrado if isinstance(cerrado, dict) else None,
    )


async def gate_de(carpeta: Path) -> GateDeNovela:
    ruta = carpeta / f"{carpeta.name}.db"
    if not ruta.exists():
        raise NovelaNoEncontrada(f"{carpeta.name} todavia no tiene ningun gate")
    from storymaker.commons.db.repos import arnes
    from storymaker.gates.nodos import _RESUMENES

    async with abrir_novela(ruta) as db:
        gate = await gate_pendiente(db)
        if gate is None:
            raise NovelaNoEncontrada(f"{carpeta.name} no tiene ningun gate esperando decision")
        recuentos = [
            Recuento(etiqueta=etiqueta, valor=int(await _uno(db, consulta) or 0))
            for etiqueta, consulta in _RESUMENES.get(_NODO_DEL_GATE.get(gate.fase, ""), ())
        ]
        preguntas = (
            await arnes.incidencias_sin_capitulo(db, "pregunta_del_entrevistador")
            if gate.fase == "intake"
            else []
        )
        sellado = await corpus_sellado(db)
        editables = await _editables(db, sellado)
        peticion = await _peticion(db) if gate.fase == "regeneration" else None
        conversacion = await conversacion_de(db, carpeta) if gate.fase == "intake" else None
    decisiones = ["aprobar", "rehacer"] + (["abortar"] if gate.fase == "intake" else [])
    return GateDeNovela(
        id=gate.id,
        fase=gate.fase,
        abierto_en=gate.abierto_en,
        recuentos=recuentos,
        preguntas=preguntas,
        peticion=peticion,
        conversacion=conversacion,
        editables=editables,
        corpus_sellado=sellado,
        decisiones=decisiones,
    )


async def tarjeta_de(carpeta: Path) -> TarjetaNovela:
    ruta = carpeta / f"{carpeta.name}.db"
    if not ruta.exists():
        return (await _tarjeta(carpeta, None))[0]
    async with abrir_novela(ruta) as db:
        return (await _tarjeta(carpeta, db))[0]


# --- Endpoints ------------------------------------------------------------------------


@router.get("")
async def listar(peticion: Request) -> list[TarjetaNovela]:
    """Una tarjeta por carpeta de `proyectos/`. No hay registro global: el directorio lo es."""
    return [await tarjeta_de(c) for c in carpetas(_settings(peticion))]


@router.get("/{nombre}/panel")
async def panel(nombre: str, peticion: Request) -> Panel:
    return await panel_de(carpeta_de(nombre, _settings(peticion)))


@router.get("/{nombre}/gate")
async def gate(nombre: str, peticion: Request) -> GateDeNovela:
    return await gate_de(carpeta_de(nombre, _settings(peticion)))
