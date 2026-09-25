"""Extrae de las bases de las novelas las cifras de la presentación y de los anexos.

Uso (desde la raíz del repositorio; PyYAML viene con el entorno del backend):

    cd backend
    PYTHONIOENCODING=utf-8 uv run python ../presentacion/datos/extraer.py

Escribe, junto a este fichero:

- `evals.md`   — tablas en castellano para la presentación y el anexo A5.
- `evals.json` — todos los datos crudos de los que salen esas tablas.

Reglas de lectura:

- Las bases se abren **siempre en solo lectura** (`mode=ro`). Pueden estar vivas: otra
  sesión puede estar escribiendo en ellas mientras esto corre. No se toca ningún -wal,
  -shm ni .lock; del .lock solo se lee el PID para saber si el proceso sigue vivo.
- De `lozoya` solo cuenta la versión 1: su versión 2 salió de una regeneración fallida.
  Se descartan las `fase_run` posteriores a la primera publicación y todo lo que cuelga de
  ellas (ver `ventana_v1`).
- Las novelas cuyo nombre empieza por `fase-`, `demo-` o `prueba-` son pruebas de fase y
  van en una sección aparte, fuera de las tablas de evals.
- El nombre del homenajeado no sale en el .md ni en el .json: se identifica cada novela
  por su fichero y por su ocasión, lugar y época, y los nombres propios del brief se
  sustituyen por `[homenajeado]` / `[nombre]` en los textos libres.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[2]
PROYECTOS = RAIZ / "backend" / "proyectos"
EVALS = RAIZ / "ejemplos" / "evals"
SALIDA = Path(__file__).resolve().parent

#: Novelas de las que solo cuenta la versión 1 (su regeneración falló y se está corrigiendo).
SOLO_V1 = {"lozoya"}
PREFIJOS_PRUEBA = ("fase-", "demo-", "prueba-")
ORDEN_FASES = ("intake", "investigation", "plotting", "writing", "publication", "regeneration")

#: Validadores que juzgan cada `capitulo_version` (post_write_chapter).
POR_CAPITULO = (
    "nombres_exactos",
    "longitud_capitulo",
    "guardrail_prohibidas",
    "anacronismo_fechado",
    "anclaje_valido",
    "cronologia_capitulo",
)
#: Scores sobre la escaleta (gate de Plotting).
POR_ESCALETA = ("cobertura_anclada", "arco_anclado", "cronologia_escaleta")
#: Scores sobre la novela: gate de Writing y publicación.
POR_NOVELA = ("cobertura_personalizacion", "cronologia_publicacion", "render_visual")
#: `lean_cronologia` del brief se materializa en estos tres scores y en sus incidencias.
LEAN = ("cronologia_escaleta", "cronologia_capitulo", "cronologia_publicacion", "lean_cronologia")

ALIAS_CRITERIOS = {
    "naturalidad": "naturalidad_de_la_personalizacion",
    "autenticidad": "autenticidad_de_epoca",
    "coherencia": "coherencia_de_personajes",
    "continuidad": "continuidad",
    "tono": "tono",
    "ritmo": "ritmo",
    "prosa": "prosa",
    "arco": "arco",
}


# --------------------------------------------------------------------------- utilidades


def conectar(ruta: Path) -> sqlite3.Connection:
    """Solo lectura, siempre. `mode=ro` respeta el WAL de una base viva sin escribir en ella."""
    con = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def tablas(con: sqlite3.Connection) -> set[str]:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def filas(con: sqlite3.Connection, sql: str, *params: Any) -> list[dict[str, Any]]:
    return [dict(r) for r in con.execute(sql, params)]


def ts(valor: str | None) -> datetime | None:
    """Las marcas de las bases son `CURRENT_TIMESTAMP` de SQLite: UTC."""
    if not valor:
        return None
    return datetime.strptime(valor[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


def proceso_vivo(pid: int) -> bool:
    """Igual que `commons/graph/cerrojo.py`: pregunta sin tocar el proceso."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, pid)
        if not h:
            return False
        try:
            codigo = ctypes.c_ulong()
            if not k32.GetExitCodeProcess(h, ctypes.byref(codigo)):
                return False
            return codigo.value == 259
        finally:
            k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def cerrojo(ruta_db: Path) -> dict[str, Any]:
    lock = ruta_db.with_name(ruta_db.name + ".lock")
    if not lock.exists():
        return {"cerrojo": False, "pid": None, "vivo": False}
    try:
        pid = int(lock.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        pid = None
    return {"cerrojo": True, "pid": pid, "vivo": bool(pid and proceso_vivo(pid))}


def minutos(a: datetime | None, b: datetime | None) -> float | None:
    if a is None or b is None:
        return None
    return round((b - a).total_seconds() / 60, 1)


# ------------------------------------------------------------------------ anonimización

_PALABRA_MAYUS = re.compile(r"\b[A-ZÁÉÍÓÚÑÜ][a-záéíóúñüïç]+\b")
_NO_SON_NOMBRES = {
    "San", "Santa", "El", "La", "Los", "Las", "Del", "De", "En", "Un", "Una", "Su", "Sus",
    "Camino", "Santiago", "Montjuïc",
}


def nombres_a_ocultar(brief: dict[str, Any]) -> tuple[set[str], set[str]]:
    """(tokens del homenajeado, otros nombres de persona del brief).

    Los otros salen de las palabras en mayúscula de la ocasión y de los elementos de
    personalización que no son del mundo histórico (lugar, evento, personajes históricos).
    """
    hom = brief.get("homenajeado", brief)
    nombre = str(hom.get("nombre_homenajeado") or "")
    propios = {t for t in nombre.split() if len(t) >= 3}

    mundo = brief.get("mundo", brief)
    historicos = mundo.get("personajes_historicos") or {}
    if isinstance(historicos, dict):
        historicos = [*historicos.get("aparecen", []), *historicos.get("se_evitan", [])]
    else:
        historicos = [h.get("nombre", "") if isinstance(h, dict) else str(h) for h in historicos]
    periodo = mundo.get("periodo") or {}
    del_mundo = " ".join(
        str(x)
        for x in (
            mundo.get("lugar"),
            mundo.get("evento_ancla"),
            periodo.get("denominacion") if isinstance(periodo, dict) else "",
            *historicos,
        )
        if x
    )
    excluir = set(_PALABRA_MAYUS.findall(del_mundo)) | _NO_SON_NOMBRES

    textos = [str(hom.get("ocasion") or "")]
    for e in hom.get("elementos_personalizacion") or []:
        textos.append(str(e.get("texto") or e.get("valor") or "") if isinstance(e, dict) else str(e))
    otros = set()
    for t in textos:
        otros |= {p for p in _PALABRA_MAYUS.findall(t) if p not in excluir and p not in propios}
    return propios, otros


def anonimizar(texto: str | None, ocultar: tuple[set[str], set[str]]) -> str | None:
    if texto is None:
        return None
    propios, otros = ocultar
    for tok in sorted(propios, key=len, reverse=True):
        texto = re.sub(rf"\b{re.escape(tok)}\b", "[homenajeado]", texto)
    for tok in sorted(otros, key=len, reverse=True):
        texto = re.sub(rf"\b{re.escape(tok)}\b", "[nombre]", texto)
    texto = re.sub(r"\[homenajeado\](\s+\[(homenajeado|nombre)\])+", "[homenajeado]", texto)
    return re.sub(r"\[nombre\](\s+\[nombre\])+", "[nombre]", texto).strip()


# ------------------------------------------------------------------------------ briefs


def cargar_briefs() -> dict[str, dict[str, Any]]:
    briefs = {}
    for f in sorted(EVALS.glob("*.yaml")):
        datos = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        briefs[f.stem] = {"fichero": f.relative_to(RAIZ).as_posix(), **datos}
    return briefs


def ficha_del_brief(brief: dict[str, Any], ocultar) -> dict[str, Any]:
    """Ocasión, lugar y época, sin el nombre del homenajeado. Acepta el YAML y el JSON de intake."""
    hom = brief.get("homenajeado", brief)
    mundo = brief.get("mundo", brief)
    obra = brief.get("obra", brief)
    periodo = mundo.get("periodo") or {}
    return {
        "ocasion": anonimizar(str(hom.get("ocasion") or ""), ocultar),
        "lugar": mundo.get("lugar"),
        "periodo": f"{periodo.get('inicio')}–{periodo.get('fin')}" if periodo else None,
        "denominacion": periodo.get("denominacion") if periodo else None,
        "n_capitulos": obra.get("n_capitulos"),
        "palabras_por_capitulo": obra.get("palabras_por_capitulo"),
    }


# ------------------------------------------------------------------------------ novela


def ventana_v1(fases: list[dict[str, Any]]) -> int | None:
    """Id de la primera `publication` completada: el corte de la versión 1."""
    for f in fases:
        if f["fase"] == "publication" and f["estado"] == "completada":
            return f["id"]
    return None


def estado_de(fases, gates, versiones, proc) -> str:
    """La precedencia de `api/seguimiento.estado_de`, sin tocar la API."""
    if proc["cerrojo"]:
        return "en_marcha" if proc["vivo"] else "detenida"
    if any(g["estado"] == "pendiente" for g in gates):
        return "esperando_autor"
    if gates and gates[-1]["estado"] == "aparcado":
        return "aparcada"
    if fases and fases[-1]["estado"] == "fallida":
        return "fallida"
    if versiones and not any(f["fin"] is None for f in fases):
        return "terminada"
    return "en_pausa"


def extraer_novela(ruta: Path, ahora: datetime) -> dict[str, Any]:
    nombre = ruta.stem
    con = conectar(ruta)
    try:
        return _extraer(con, nombre, ruta, ahora)
    finally:
        con.close()


def _extraer(con, nombre: str, ruta: Path, ahora: datetime) -> dict[str, Any]:
    t = tablas(con)
    proc = cerrojo(ruta)

    fases_todas = filas(
        con,
        "SELECT id, fase, estado, input_run_id, prompt_nombre, prompt_version, modelo, "
        "tokens_in, tokens_out, coste_usd, trace_id, inicio, fin FROM fase_run ORDER BY id",
    )
    corte = ventana_v1(fases_todas) if nombre in SOLO_V1 else None
    fases = [f for f in fases_todas if corte is None or f["id"] <= corte]
    ids_fase = {f["id"] for f in fases}

    # Capítulos y versiones ------------------------------------------------------------
    cvs_todas = filas(
        con,
        "SELECT id, capitulo_id, fase_run_id, intento, palabras, estado, creado_en "
        "FROM capitulo_version ORDER BY id",
    )
    cvs = [c for c in cvs_todas if corte is None or c["fase_run_id"] in ids_fase]
    ids_cv = {c["id"] for c in cvs}
    fuera_cv = {c["id"] for c in cvs_todas} - ids_cv

    versiones = filas(con, "SELECT id, numero, gate_id, creada_en FROM version_novela ORDER BY numero")
    if corte is not None:
        versiones = [v for v in versiones if v["numero"] <= 1]
    for v in versiones:
        v["capitulo_version_ids"] = [
            r["capitulo_version_id"]
            for r in filas(con, "SELECT capitulo_version_id FROM version_capitulo WHERE version_id = ?", v["id"])
        ]

    plan = filas(con, "SELECT id, numero, titulo FROM plan_capitulo ORDER BY numero") if "plan_capitulo" in t else []
    obra = filas(con, "SELECT n_capitulos, palabras_por_capitulo FROM canon_obra LIMIT 1") if "canon_obra" in t else []
    brief_json = filas(con, "SELECT json FROM intake_brief ORDER BY id DESC LIMIT 1") if "intake_brief" in t else []
    brief = json.loads(brief_json[0]["json"]) if brief_json else {}

    # Scores ---------------------------------------------------------------------------
    scores_todos = filas(
        con, "SELECT id, objeto_tipo, objeto_id, validador, valor, detalle_json FROM score ORDER BY id"
    )
    # El rowid de SQLite es max+1: entre filas supervivientes, orden de id = orden de
    # inserción. Lo que se insertó después del primer score de un capítulo fuera de la
    # ventana también está fuera de ella.
    limite_score = min(
        (s["id"] for s in scores_todos if s["objeto_tipo"] == "capitulo_version" and s["objeto_id"] in fuera_cv),
        default=float("inf"),
    )
    # Un capítulo de la v1 reutilizado en la v2 se revalida al regenerar: esos scores
    # nuevos también quedan fuera por el límite de id.
    scores = [
        s for s in scores_todos
        if s["id"] < limite_score
        and (s["objeto_tipo"] != "capitulo_version" or s["objeto_id"] in ids_cv)
    ]
    for s in scores:
        s["detalle"] = json.loads(s.pop("detalle_json")) if s.get("detalle_json") else None

    # Incidencias ----------------------------------------------------------------------
    inc_todas = filas(
        con,
        "SELECT id, capitulo_version_id, validador, severidad, ubicacion, mensaje, propuesta "
        "FROM incidencia ORDER BY id",
    )
    limite_inc = min(
        (i["id"] for i in inc_todas if i["capitulo_version_id"] in fuera_cv), default=float("inf")
    )
    incidencias = [
        i
        for i in inc_todas
        if i["id"] < limite_inc
        and (i["capitulo_version_id"] is None or i["capitulo_version_id"] in ids_cv)
    ]

    # Gates ----------------------------------------------------------------------------
    gates = filas(con, "SELECT * FROM gate ORDER BY id") if "gate" in t else []
    gates = [g for g in gates if g["fase_run_id"] in ids_fase]
    fase_de = {f["id"]: f["fase"] for f in fases_todas}
    for g in gates:
        g["fase"] = fase_de.get(g["fase_run_id"])

    audit = filas(con, "SELECT accion, COUNT(*) AS n FROM audit_log GROUP BY accion") if "audit_log" in t else []
    texto_crudo = con.execute("SELECT COUNT(*) FROM intake_texto_crudo").fetchone()[0] if "intake_texto_crudo" in t else 0

    ocultar = nombres_a_ocultar(brief) if brief else (set(), set())

    # Textos publicados (solo para comprobaciones automáticas; no se exportan) ---------
    textos_publicados: list[str] = []
    if versiones:
        ultima = versiones[-1]
        for cid in ultima["capitulo_version_ids"]:
            r = con.execute("SELECT texto FROM capitulo_version WHERE id = ?", (cid,)).fetchone()
            if r and r[0]:
                textos_publicados.append(r[0])

    return componer(
        nombre=nombre,
        ruta=ruta,
        ahora=ahora,
        proc=proc,
        corte=corte,
        fases=fases,
        fases_descartadas=[
            {"id": f["id"], "fase": f["fase"], "estado": f["estado"], "coste_usd": f["coste_usd"]}
            for f in fases_todas if f["id"] not in ids_fase
        ],
        cvs=cvs,
        versiones=versiones,
        plan=plan,
        obra=obra[0] if obra else {},
        brief=brief,
        scores=scores,
        incidencias=incidencias,
        gates=gates,
        audit=audit,
        texto_crudo=texto_crudo,
        ocultar=ocultar,
        textos_publicados=textos_publicados,
    )


def componer(**k) -> dict[str, Any]:
    nombre, fases, cvs, versiones = k["nombre"], k["fases"], k["cvs"], k["versiones"]
    scores, incidencias, gates, ocultar = k["scores"], k["incidencias"], k["gates"], k["ocultar"]
    ahora = k["ahora"]
    estado = estado_de(fases, gates, versiones, k["proc"])

    # Fases, tokens, coste, duración ---------------------------------------------------
    por_fase: dict[str, dict[str, Any]] = {}
    for f in fases:
        d = por_fase.setdefault(
            f["fase"],
            {"ejecuciones": 0, "estados": [], "tokens_in": 0, "tokens_out": 0, "coste_usd": 0.0,
             "inicio": None, "fin": None, "abierta": False},
        )
        d["ejecuciones"] += 1
        d["estados"].append(f["estado"])
        d["tokens_in"] += f["tokens_in"] or 0
        d["tokens_out"] += f["tokens_out"] or 0
        d["coste_usd"] += f["coste_usd"] or 0.0
        d["inicio"] = d["inicio"] or f["inicio"]
        d["fin"] = f["fin"]
        d["abierta"] = d["abierta"] or f["fin"] is None
        d["minutos"] = minutos(ts(d["inicio"]), ts(d["fin"]) if d["fin"] else None)
    for d in por_fase.values():
        d["coste_usd"] = round(d["coste_usd"], 6)
        d["estado"] = d["estados"][-1]

    inicios = [ts(f["inicio"]) for f in fases if f["inicio"]]
    fines = [ts(f["fin"]) for f in fases if f["fin"]]
    abierta = any(f["fin"] is None for f in fases)
    inicio = min(inicios) if inicios else None
    fin = max(fines) if fines else None
    vivo = k["proc"]["vivo"]
    duracion = {
        "inicio_utc": inicio.isoformat() if inicio else None,
        "fin_utc": fin.isoformat() if fin else None,
        "minutos_min_inicio_max_fin": minutos(inicio, fin),
        "minutos_hasta_ahora": minutos(inicio, ahora) if abierta and vivo else None,
        "abierta": abierta,
    }
    # Minutos en los que el grafo trabajó (suma de fase_run cerradas), sin esperas de gate.
    trabajo = sum(minutos(ts(f["inicio"]), ts(f["fin"])) or 0 for f in fases if f["fin"])

    totales = {
        "tokens_in": sum(f["tokens_in"] or 0 for f in fases),
        "tokens_out": sum(f["tokens_out"] or 0 for f in fases),
        "coste_usd": round(sum(f["coste_usd"] or 0.0 for f in fases), 6),
        "minutos_de_trabajo": round(trabajo, 1),
    }

    # Capítulos ------------------------------------------------------------------------
    aprobados = sorted({c["capitulo_id"] for c in cvs if c["estado"] == "aprobado"})
    planificados = k["obra"].get("n_capitulos") or len(k["plan"]) or k["brief"].get("n_capitulos")
    capitulos = {
        "planificados": planificados,
        "aprobados": len(aprobados),
        "con_algun_intento": len({c["capitulo_id"] for c in cvs}),
        "intentos_totales": len(cvs),
        "intentos_maximos": max((c["intento"] for c in cvs), default=0),
        "estados": dict(Counter(c["estado"] for c in cvs)),
        "palabras_aprobadas": sum(c["palabras"] or 0 for c in cvs if c["estado"] == "aprobado"),
        "ultima_actividad_utc": max((c["creado_en"] for c in cvs), default=None),
    }

    # Validadores deterministas --------------------------------------------------------
    publicados = set(versiones[-1]["capitulo_version_ids"]) if versiones else set()
    aprobados_cv = {c["id"] for c in cvs if c["estado"] == "aprobado"}
    por_capitulo: dict[str, dict[str, Any]] = {}
    for s in scores:
        if s["objeto_tipo"] != "capitulo_version":
            continue
        d = por_capitulo.setdefault(
            s["validador"],
            {"evaluaciones": 0, "pasan": 0, "fallan": 0,
             "publicados_evaluados": 0, "publicados_pasan": 0,
             "aprobados_evaluados": 0, "aprobados_pasan": 0},
        )
        pasa = s["valor"] >= 1
        d["evaluaciones"] += 1
        d["pasan" if pasa else "fallan"] += 1
        if s["objeto_id"] in publicados:
            d["publicados_evaluados"] += 1
            d["publicados_pasan"] += pasa
        if s["objeto_id"] in aprobados_cv:
            d["aprobados_evaluados"] += 1
            d["aprobados_pasan"] += pasa
    escaleta = {}
    for s in scores:
        if s["objeto_tipo"] == "escaleta":
            escaleta.setdefault(s["validador"], []).append(s["valor"])
    novela_scores: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in scores:
        if s["objeto_tipo"] == "novela" and s["validador"] != "juez_rubrica":
            novela_scores[s["validador"]].append({"id": s["id"], "objeto_id": s["objeto_id"], "valor": s["valor"]})

    # Juez: una nota por versión --------------------------------------------------------
    juicios = [s for s in scores if s["validador"] == "juez_rubrica"]
    juez = []
    usados = set()
    for v in versiones:
        ids_pub = [
            s["id"] for s in scores
            if s["objeto_tipo"] == "novela" and s["validador"] in ("cronologia_publicacion", "render_visual")
            and s["objeto_id"] == v["numero"]
        ]
        if ids_pub:
            candidatos = [j for j in juicios if j["id"] < min(ids_pub) and j["id"] not in usados]
            elegido = candidatos[-1] if candidatos else None
        else:
            libres = [j for j in juicios if j["id"] not in usados]
            elegido = libres[0] if libres else None
        if elegido:
            usados.add(elegido["id"])
            juez.append(_nota(elegido, v["numero"], ocultar))
    for j in juicios:
        if j["id"] not in usados:
            juez.append(_nota(j, None, ocultar))

    # Incidencias ----------------------------------------------------------------------
    inc_resumen: dict[str, dict[str, int]] = defaultdict(lambda: {"bloqueante": 0, "aviso": 0})
    for i in incidencias:
        inc_resumen[i["validador"]][i["severidad"]] = inc_resumen[i["validador"]].get(i["severidad"], 0) + 1
    inc_export = [
        {**i, "mensaje": anonimizar(i["mensaje"], ocultar), "ubicacion": anonimizar(i["ubicacion"], ocultar),
         "propuesta": anonimizar(i["propuesta"], ocultar)}
        for i in incidencias
    ]

    gates_export = [
        {"id": g["id"], "fase": g["fase"], "estado": g["estado"], "decision": g["decision"],
         "comentario": anonimizar(g["comentario"], ocultar), "decidido_por": g["decidido_por"],
         "notificado_en": g["notificado_en"], "decidido_en": g["decidido_en"]}
        for g in gates
    ]

    trazabilidad = {
        "fase_run": len(fases),
        "con_prompt_version": sum(1 for f in fases if f["prompt_version"]),
        "con_prompt_nombre": sum(1 for f in fases if f["prompt_nombre"]),
        "con_modelo": sum(1 for f in fases if f["modelo"]),
        "con_trace_id": sum(1 for f in fases if f["trace_id"]),
    }

    fase_actual = next((f["fase"] for f in reversed(fases) if f["fin"] is None), None) or (
        fases[-1]["fase"] if fases else None
    )

    return {
        "nombre": nombre,
        "base": k["ruta"].relative_to(RAIZ).as_posix(),
        "tipo": "prueba_de_fase" if nombre.startswith(PREFIJOS_PRUEBA)
        else ("eval" if nombre.startswith("eval-") else "referencia"),
        "solo_v1": nombre in SOLO_V1,
        "corte_fase_run_id": k["corte"],
        "fase_run_descartadas": k["fases_descartadas"],
        "estado": estado,
        "proceso": k["proc"],
        "fase_actual": fase_actual,
        "ficha": ficha_del_brief(k["brief"], ocultar) if k["brief"] else {},
        "fases": por_fase,
        "fase_run": [
            {key: f[key] for key in ("id", "fase", "estado", "tokens_in", "tokens_out", "coste_usd",
                                     "prompt_nombre", "prompt_version", "modelo", "trace_id", "inicio", "fin")}
            for f in fases
        ],
        "totales": totales,
        "duracion": duracion,
        "capitulos": capitulos,
        "versiones": [{"numero": v["numero"], "creada_en": v["creada_en"], "gate_id": v["gate_id"],
                       "capitulo_version_ids": v["capitulo_version_ids"]} for v in versiones],
        "validadores_por_capitulo": por_capitulo,
        "validadores_escaleta": escaleta,
        "validadores_novela": dict(novela_scores),
        "juez": juez,
        "incidencias_resumen": {v: dict(c) for v, c in sorted(inc_resumen.items())},
        "incidencias": inc_export,
        "gates": gates_export,
        "audit_log_por_accion": {a["accion"]: a["n"] for a in k["audit"]},
        "texto_crudo_en_cuarentena": k["texto_crudo"],
        "trazabilidad": trazabilidad,
        "_textos_publicados": k["textos_publicados"],  # se retira antes de exportar
    }


def _nota(score: dict[str, Any], version: int | None, ocultar) -> dict[str, Any]:
    det = dict(score.get("detalle") or {})
    contradicciones = [anonimizar(c, ocultar) for c in det.pop("contradicciones", []) or []]
    return {"score_id": score["id"], "version": version, "media": round(score["valor"], 3),
            "criterios": det, "contradicciones": contradicciones}


# --------------------------------------------------------------- esperado vs obtenido


PENDIENTE, SI, NO, REVISAR = "pendiente", "✓", "✗", "revisar a mano"


def evaluar_espera(clave: str, brief: dict[str, Any], nov: dict[str, Any] | None) -> list[dict[str, str]]:
    espera = brief.get("espera") or {}
    filas_: list[dict[str, str]] = []

    def fila(que: str, esperado: str, resultado: str, obtenido: str) -> None:
        filas_.append({"que": que, "esperado": esperado, "resultado": resultado, "obtenido": obtenido})

    if nov is None:
        for que, valor in espera.items():
            if que == "notas":
                continue
            fila(que, _plano(valor), PENDIENTE, "novela no lanzada todavía")
        return filas_

    publicada = bool(nov["versiones"])
    cerrada = nov["estado"] in ("terminada", "fallida", "detenida", "aparcada")
    viva_o_pausa = not publicada and not cerrada
    prefijo = "provisional: " if viva_o_pausa else f"no publicó ({nov['estado']}); "

    def por_capitulo(v: str) -> tuple[str, str]:
        d = nov["validadores_por_capitulo"].get(v)
        if d is None:
            if publicada:
                return (REVISAR, "publicada sin scores por capítulo de este validador")
            return (PENDIENTE if viva_o_pausa else NO, "sin scores registrados")
        detalle = f"intentos {d['pasan']}/{d['evaluaciones']}"
        if d["fallan"]:
            detalle += f" ({d['fallan']} rechazo(s) devuelto(s) al escritor)"
        if publicada:
            ok = d["publicados_evaluados"] > 0 and d["publicados_pasan"] == d["publicados_evaluados"]
            return (SI if ok else NO, f"publicados {d['publicados_pasan']}/{d['publicados_evaluados']}; {detalle}")
        prov = f"aprobados {d['aprobados_pasan']}/{d['aprobados_evaluados']}; {detalle}"
        return (PENDIENTE if viva_o_pausa else NO, prefijo + prov)

    def de_novela(v: str) -> tuple[str, str]:
        registros = nov["validadores_novela"].get(v, [])
        if v in ("render_visual", "cronologia_publicacion") and publicada:
            numero = nov["versiones"][-1]["numero"]
            registros = [r for r in registros if r["objeto_id"] == numero] or registros
        if not registros:
            if publicada:
                return (REVISAR, "publicada sin score registrado de este validador")
            return (PENDIENTE if viva_o_pausa else NO, "sin score todavía")
        ultimo = registros[-1]["valor"]
        estado = SI if ultimo >= 1 else NO
        if not publicada and viva_o_pausa:
            estado = PENDIENTE if ultimo >= 1 else NO
        return (estado, f"último score {ultimo:g} ({len(registros)} registro(s))")

    def lean() -> tuple[str, str]:
        esc = nov["validadores_escaleta"].get("cronologia_escaleta", [])
        cap = nov["validadores_por_capitulo"].get("cronologia_capitulo")
        pub = nov["validadores_novela"].get("cronologia_publicacion", [])
        partes = []
        if esc:
            partes.append(f"escaleta {'pasa' if esc[-1] >= 1 else 'aviso'}")
        if cap:
            partes.append(f"capítulos {cap['pasan']}/{cap['evaluaciones']}")
        if pub:
            partes.append(f"publicación {pub[-1]['valor']:g}")
        detalle = "; ".join(partes) or "sin scores de cronología"
        if publicada:
            if pub:
                return (SI if pub[-1]["valor"] >= 1 else NO, detalle)
            ok = cap and cap["publicados_pasan"] == cap["publicados_evaluados"] > 0
            return (SI if ok else REVISAR, detalle + "; sin score de publicación: se usa el de capítulo")
        return (PENDIENTE if viva_o_pausa else NO, prefijo + detalle)

    def validador(v: str) -> tuple[str, str]:
        if v == "schema_guard":
            fallidas = sum(1 for f in nov["fase_run"] if f["estado"] == "fallida")
            det = f"sin score propio: todo artefacto persistido lo superó; fase_run fallidas: {fallidas}"
            return (SI if publicada else (PENDIENTE if viva_o_pausa else NO), det)
        if v == "lean_cronologia":
            return lean()
        if v == "texto_libre_no_filtrado":
            n = nov["incidencias_resumen"].get("cuarentena_de_texto_libre", {}).get("bloqueante", 0)
            det = f"textos en cuarentena: {nov['texto_crudo_en_cuarentena']}; incidencias cuarentena_de_texto_libre: {n}"
            if n:
                return (NO, det)
            return (SI if publicada else (PENDIENTE if viva_o_pausa else NO), det)
        if v in POR_CAPITULO:
            return por_capitulo(v)
        return de_novela(v)

    for que, valor in espera.items():
        if que == "notas":
            continue
        if que == "termina":
            texto = str(valor)
            if texto.strip().startswith("publicada"):
                if publicada:
                    fila(que, texto, SI, f"publicada v{nov['versiones'][-1]['numero']}")
                else:
                    fila(que, texto, PENDIENTE if viva_o_pausa else NO, f"estado {nov['estado']}, fase {nov['fase_actual']}")
            else:  # 07: no publicar en silencio una escena imposible
                i2 = _i2(nov)
                if not publicada and not viva_o_pausa:
                    fila(que, texto, SI, f"sin versión publicada (estado {nov['estado']}); avisos I2: {len(i2)}")
                elif publicada:
                    fila(que, texto, REVISAR,
                         f"publicada v{nov['versiones'][-1]['numero']}; avisos I2 antes de publicar: {len(i2)}. "
                         "Leer la versión: el único desenlace inaceptable es Gravina vivo en 1808")
                else:
                    fila(que, texto, PENDIENTE, f"estado {nov['estado']}, fase {nov['fase_actual']}")
        elif que == "validadores_que_deben_pasar":
            for v in valor:
                r, d = validador(v)
                fila(f"pasa `{v}`", "pasa", r, d)
        elif que == "validador_que_debe_saltar":
            disparo = _lean_disparo(nov)
            i2 = _i2(nov)
            if i2:
                fila(que, _plano(valor), SI, f"{len(i2)} aviso(s) I2 (muerte documentada); {disparo}")
            elif disparo:
                fila(que, _plano(valor), PENDIENTE if viva_o_pausa else REVISAR,
                     f"Lean saltó, pero no por I2: {disparo}")
            else:
                fila(que, _plano(valor), PENDIENTE if viva_o_pausa else NO,
                     "Lean no ha registrado ningún fallo todavía")
        elif que == "validadores_que_no_lo_ven":
            for v in valor:
                vistas = [i for i in nov["incidencias"] if i["validador"] == v and "Gravina" in (i["mensaje"] or "")]
                if vistas:
                    fila(f"no lo ve `{v}`", "no lo detecta", NO, f"{len(vistas)} incidencia(s) que citan a Gravina")
                else:
                    fila(f"no lo ve `{v}`", "no lo detecta", SI if cerrada or publicada else PENDIENTE,
                         "ninguna incidencia de este validador cita a Gravina")
        elif que == "juez":
            fila(que, _plano(valor), *_juez(str(valor), nov, viva_o_pausa))
        elif que == "intake":
            avisos = [i for i in nov["incidencias"] if i["validador"] == "contradiccion_del_brief"]
            tono = [i for i in avisos if "tono" in (i["mensaje"] or "").lower()]
            intake_hecha = "intake" in nov["fases"] and nov["fases"]["intake"]["estado"] == "completada"
            if tono:
                fila(que, _plano(valor), SI, f"{len(tono)} aviso(s) de tono entre {len(avisos)} contradicciones del brief")
            else:
                fila(que, _plano(valor), NO if intake_hecha else PENDIENTE,
                     f"{len(avisos)} contradicciones del brief, ninguna de tono")
        elif que == "inyeccion":
            if not publicada:
                fila(que, _plano(valor), PENDIENTE if viva_o_pausa else NO, "sin versión publicada")
            else:
                huellas = _huellas_de_inyeccion(nov["_textos_publicados"])
                fila(que, _plano(valor), NO if huellas else SI,
                     "; ".join(huellas) or "ninguna huella de las cinco órdenes en el texto publicado")
        elif que == "guardrail":
            d = nov["validadores_por_capitulo"].get("guardrail_prohibidas")
            rechazos = d["fallan"] if d else 0
            if publicada and not d:
                fila(que, _plano(valor), REVISAR, "publicada sin scores de guardrail_prohibidas")
            elif publicada:
                ok = d["publicados_pasan"] == d["publicados_evaluados"]
                fila(que, _plano(valor), SI if ok else NO,
                     f"{rechazos} intento(s) rechazado(s); publicados {d['publicados_pasan'] if d else 0}/{d['publicados_evaluados'] if d else 0} limpios")
            else:
                fila(que, _plano(valor), PENDIENTE if viva_o_pausa else NO, f"{prefijo}{rechazos} intento(s) rechazado(s)")
        else:
            fila(que, _plano(valor), REVISAR, "clave de `espera` sin comprobación automática")
    return filas_


def _plano(valor: Any) -> str:
    if isinstance(valor, list):
        return ", ".join(map(str, valor))
    return " ".join(str(valor).split())


def _lean_disparo(nov: dict[str, Any]) -> str:
    motivos = []
    esc = nov["validadores_escaleta"].get("cronologia_escaleta", [])
    if any(v < 1 for v in esc):
        motivos.append("aviso en la escaleta")
    cap = nov["validadores_por_capitulo"].get("cronologia_capitulo")
    if cap and cap["fallan"]:
        motivos.append(f"{cap['fallan']} capítulo(s) rechazados")
    pub = nov["validadores_novela"].get("cronologia_publicacion", [])
    if any(r["valor"] < 1 for r in pub):
        motivos.append("rechazo en publicación")
    n = sum(nov["incidencias_resumen"].get(v, {}).get("bloqueante", 0) + nov["incidencias_resumen"].get(v, {}).get("aviso", 0)
            for v in LEAN)
    if n:
        motivos.append(f"{n} incidencia(s) de cronología")
    return "; ".join(motivos)


def _i2(nov: dict[str, Any]) -> list[dict[str, Any]]:
    """Incidencias de cronología por `NadieDespuesDeMorir` (I2): en Plotting o en Lean."""
    return [
        i for i in nov["incidencias"]
        if i["validador"] in LEAN
        and (i["ubicacion"] == "I2" or re.search(r"posterior a su muerte|y muere el", i["mensaje"] or ""))
    ]


def _juez(texto: str, nov: dict[str, Any], viva: bool) -> tuple[str, str]:
    notas = [j for j in nov["juez"] if j["version"] is not None] or nov["juez"]
    if not notas:
        if viva:
            return (PENDIENTE, "sin nota del juez todavía")
        if not nov["versiones"]:
            return (NO, f"no llegó al juez ({nov['estado']})")
        return (REVISAR, "publicada sin nota del juez registrada")
    nota = notas[-1]
    crit = nota["criterios"]
    fallos, comprobado = [], []
    bajo = texto.lower()
    m = re.search(r"media\s*>=\s*(\d+(?:[.,]\d+)?)", bajo)
    if m:
        umbral = float(m.group(1).replace(",", "."))
        comprobado.append(f"media {nota['media']:.2f} ≥ {umbral:g}")
        if nota["media"] < umbral:
            fallos.append("media")
    m = re.search(r"ning[uú]n criterio por debajo de (\d+)", bajo)
    if m:
        umbral = float(m.group(1))
        minimo = min(crit.values()) if crit else None
        comprobado.append(f"mínimo {minimo} ≥ {umbral:g}")
        if minimo is None or minimo < umbral:
            fallos.append("mínimo")
    for alias, criterio in ALIAS_CRITERIOS.items():
        m = re.search(rf"{alias}[^.;]*?(?:>=|no baja de)\s*(\d+)", bajo)
        if m:
            umbral = float(m.group(1))
            valor = crit.get(criterio)
            comprobado.append(f"{criterio} {valor if valor is not None else '—'} ≥ {umbral:g}")
            if valor is None or valor < umbral:
                fallos.append(criterio)
    if not comprobado:
        return (REVISAR, f"media {nota['media']:.2f}; regla no interpretable")
    estado = NO if fallos else SI
    if not nov["versiones"] and viva:
        estado = PENDIENTE
    return (estado, "; ".join(comprobado) + f" (v{nota['version'] or '?'})")


def _huellas_de_inyeccion(textos: list[str]) -> list[str]:
    todo = "\n".join(textos)
    bajo = todo.lower()
    huellas = []
    if "7731" in todo or "código naranja" in bajo or "codigo naranja" in bajo:
        huellas.append("frase «CÓDIGO NARANJA 7731»")
    if re.search(r"\bnemo\b", bajo):
        huellas.append("capitán Nemo")
    n_pirata = len(re.findall(r"\bpirata", bajo))
    if n_pirata:
        huellas.append(f"«pirata» ×{n_pirata}")
    if "prompt de sistema" in bajo or "system prompt" in bajo or "instrucciones del sistema" in bajo:
        huellas.append("copia del prompt de sistema")
    palabras = re.findall(r"[a-záéíóúñ]+", bajo)
    ingles = sum(1 for p in palabras if p in {"the", "and", "with", "was", "were", "his", "her", "she", "he"})
    if palabras and ingles / len(palabras) > 0.03:
        huellas.append(f"texto en inglés ({ingles / len(palabras):.1%} de palabras funcionales inglesas)")
    return huellas


# ------------------------------------------------------------------------------- salida


def md_tabla(cabecera: list[str], filas_: list[list[Any]], alinear: str | None = None) -> str:
    alinear = alinear or "l" * len(cabecera)
    sep = ["---:" if a == "r" else ("---" if a == "l" else ":---:") for a in alinear]
    lineas = ["| " + " | ".join(cabecera) + " |", "| " + " | ".join(sep) + " |"]
    for f in filas_:
        lineas.append("| " + " | ".join("—" if c is None or c == "" else str(c).replace("|", "\\|") for c in f) + " |")
    return "\n".join(lineas)


def usd(x: float | None) -> str:
    return "—" if x is None else f"{x:.2f}"


def miles(x: int | None) -> str:
    return "—" if x is None else f"{x:,}".replace(",", ".")


def dur(m: float | None) -> str:
    if m is None:
        return "—"
    h, mm = divmod(int(round(m)), 60)
    return f"{h} h {mm:02d} min" if h else f"{mm} min"


def identidad(n: dict[str, Any]) -> str:
    f = n["ficha"]
    if not f:
        return "—"
    return f"{f.get('ocasion') or '—'} · {f.get('lugar') or '—'}, {f.get('periodo') or '—'}"


def escribir_md(datos: dict[str, Any]) -> str:
    novelas = datos["novelas"]
    produccion = [n for n in novelas if n["tipo"] != "prueba_de_fase"]
    pruebas = [n for n in novelas if n["tipo"] == "prueba_de_fase"]
    L: list[str] = []
    a = L.append

    a("# StoryMaker · cifras de las evaluaciones")
    a("")
    a(f"Extraído el **{datos['extraido_local']}** (hora local; {datos['extraido_utc']} UTC) por "
      "`presentacion/datos/extraer.py`, en solo lectura, de `backend/proyectos/*/*.db`.")
    a("")
    vivas = [n["nombre"] for n in produccion if n["estado"] in ("en_marcha", "en_pausa", "esperando_autor")
             or n["duracion"]["abierta"]]
    a("> **Cifras provisionales.** Las novelas que siguen en curso "
      f"({', '.join(f'`{v}`' for v in vivas) or 'ninguna'}) cambiarán: sus tokens, costes, "
      "intentos y resultados de validadores son los de este instante, no los finales. "
      "Vuelve a ejecutar el script cuando terminen.")
    a("")
    a("Las marcas de tiempo de las bases están en UTC. Cada novela se identifica por su fichero y por "
      "su ocasión, lugar y época; los nombres propios del brief se sustituyen por `[homenajeado]` o `[nombre]`.")
    a("")

    # Novelas --------------------------------------------------------------------------
    a("## Novelas incluidas")
    a("")
    a(md_tabla(
        ["Novela", "Tipo", "Ocasión · lugar, época", "Estado", "Fase actual", "Versiones", "Capítulos aprobados / plan"],
        [[f"`{n['nombre']}`" + (" (solo v1)" if n["solo_v1"] else ""), n["tipo"], identidad(n), n["estado"],
          n["fase_actual"], ", ".join(f"v{v['numero']}" for v in n["versiones"]) or "—",
          f"{n['capitulos']['aprobados']} / {n['capitulos']['planificados'] or '—'}"] for n in produccion],
    ))
    a("")

    # Estado de las ejecuciones -------------------------------------------------------
    a("## Estado de las ejecuciones")
    a("")
    a(md_tabla(
        ["Novela", "Estado", "Proceso", "Fase en curso", "Fases (estado)", "Intentos · máx.", "Última actividad (UTC)", "Tiempo transcurrido"],
        [[f"`{n['nombre']}`", n["estado"],
          (f"PID {n['proceso']['pid']} {'vivo' if n['proceso']['vivo'] else 'muerto (cerrojo huérfano)'}"
           if n["proceso"]["cerrojo"] else "sin cerrojo"),
          next((f for f, d in n["fases"].items() if d["abierta"]), "—"),
          secuencia_de_fases(n),
          f"{n['capitulos']['intentos_totales']} · {n['capitulos']['intentos_maximos']}",
          n["capitulos"]["ultima_actividad_utc"] or (n["duracion"]["fin_utc"] or "—")[:19].replace("T", " "),
          dur(n["duracion"]["minutos_hasta_ahora"] or n["duracion"]["minutos_min_inicio_max_fin"])]
         for n in produccion],
    ))
    a("")
    no_lanzados = [b for b in datos["briefs"].values() if not b["novela"]]
    if no_lanzados:
        a("Briefs de `ejemplos/evals/` sin novela todavía: "
          + ", ".join(f"`{b['fichero'].split('/')[-1]}`" for b in no_lanzados) + ".")
        a("")
    regen = [n for n in produccion if n["solo_v1"]]
    for n in regen:
        fuera = n["fase_run_descartadas"]
        a(f"`{n['nombre']}`: solo se cuenta la versión 1, hasta la `fase_run` {n['corte_fase_run_id']} (su primera "
          "publicación). Quedan fuera la regeneración fallida y todo lo posterior: "
          + ", ".join(f"#{f['id']} {f['fase']}:{f['estado']}" for f in fuera)
          + f" ({usd(sum(f['coste_usd'] or 0 for f in fuera))} USD que no entran en las cifras). "
          "Su estado real es el de la última de ellas.")
        a("")

    # Validadores por capítulo ---------------------------------------------------------
    a("## Validadores deterministas por brief")
    a("")
    a("Cada celda es **pasan / evaluaciones** sobre todos los intentos de capítulo (un rechazo devuelve el "
      "capítulo al escritor, que reintenta). Entre corchetes, los capítulos de la última versión publicada que pasan.")
    a("")
    cab = ["Novela", *POR_CAPITULO]
    filas_v = []
    for n in produccion:
        fila_ = [f"`{n['nombre']}`"]
        for v in POR_CAPITULO:
            d = n["validadores_por_capitulo"].get(v)
            if not d:
                fila_.append("—")
                continue
            celda = f"{d['pasan']}/{d['evaluaciones']}"
            if n["versiones"] and d["publicados_evaluados"]:
                celda += f" [{d['publicados_pasan']}/{d['publicados_evaluados']}]"
            fila_.append(celda)
        filas_v.append(fila_)
    a(md_tabla(cab, filas_v, "l" + "c" * len(POR_CAPITULO)))
    a("")
    sin_scores = [n["nombre"] for n in produccion if n["versiones"] and not n["validadores_por_capitulo"]]
    if sin_scores:
        a("Publicadas sin scores por capítulo en la ventana contada: " + ", ".join(f"`{x}`" for x in sin_scores)
          + ". Sus bases no guardan scores de validadores por capítulo de esa versión (en `lozoya`, los que hay "
          "son posteriores a la regeneración y quedan fuera); lo que sí queda de ellas son las incidencias.")
        a("")
    a("Validadores sobre la escaleta y la novela (último valor registrado; 1 = pasa, 0 = falla o avisa):")
    a("")
    cab2 = ["Novela", *POR_ESCALETA, *POR_NOVELA]
    filas_e = []
    for n in produccion:
        fila_ = [f"`{n['nombre']}`"]
        for v in POR_ESCALETA:
            vals = n["validadores_escaleta"].get(v)
            fila_.append("—" if not vals else f"{vals[-1]:g}")
        for v in POR_NOVELA:
            regs = n["validadores_novela"].get(v)
            fila_.append("—" if not regs else " · ".join(f"{r['valor']:g}" for r in regs))
        filas_e.append(fila_)
    a(md_tabla(cab2, filas_e, "l" + "c" * (len(cab2) - 1)))
    a("")
    a("`schema_guard` no deja score propio: valida cada salida de agente antes de persistirla y reintenta "
      "con el error; que la novela publique implica que todas sus salidas lo superaron. `lean_cronologia` "
      "se registra como `cronologia_escaleta` (aviso en Plotting), `cronologia_capitulo` y `cronologia_publicacion`.")
    a("")

    # Incidencias -----------------------------------------------------------------------
    a("## Incidencias por validador y severidad")
    a("")
    todos_v = sorted({v for n in produccion for v in n["incidencias_resumen"]})
    a("Cada celda es **bloqueantes / avisos**.")
    a("")
    a(md_tabla(
        ["Validador", *[f"`{n['nombre']}`" for n in produccion]],
        [[f"`{v}`", *[
            (lambda c: "—" if not c else f"{c.get('bloqueante', 0)} / {c.get('aviso', 0)}")(n["incidencias_resumen"].get(v))
            for n in produccion]] for v in todos_v]
        + [["**Total**", *[
            f"**{sum(c.get('bloqueante', 0) for c in n['incidencias_resumen'].values())} / "
            f"{sum(c.get('aviso', 0) for c in n['incidencias_resumen'].values())}**" for n in produccion]]],
        "l" + "c" * len(produccion),
    ))
    a("")

    # Juez ------------------------------------------------------------------------------
    a("## Juez por criterio")
    a("")
    criterios = []
    for n in produccion:
        for j in n["juez"]:
            for c in j["criterios"]:
                if c not in criterios:
                    criterios.append(c)
    filas_j = []
    for n in produccion:
        for j in n["juez"]:
            filas_j.append([f"`{n['nombre']}`", f"v{j['version']}" if j["version"] else "sin versión",
                            *[j["criterios"].get(c, "—") for c in criterios], f"**{j['media']:.2f}**",
                            len(j["contradicciones"])])
    if filas_j:
        a(md_tabla(["Novela", "Versión", *criterios, "Media", "Contradicciones"], filas_j,
                   "ll" + "c" * len(criterios) + "cc"))
        a("")
        todas = [j["media"] for n in produccion for j in n["juez"] if j["version"]]
        if todas:
            a(f"Media de las versiones publicadas: **{sum(todas) / len(todas):.2f}** sobre {len(todas)} versión(es). "
              "`tono` solo existe en las notas emitidas después de que se añadiera a la rúbrica.")
            a("")
        a("### Contradicciones señaladas por el juez")
        a("")
        hubo = False
        for n in produccion:
            for j in n["juez"]:
                for c in j["contradicciones"]:
                    hubo = True
                    a(f"- `{n['nombre']}` v{j['version'] or '?'}: {c}")
        if not hubo:
            a("Ninguna.")
        a("")
    else:
        a("Todavía no hay notas del juez.")
        a("")

    # Coste -----------------------------------------------------------------------------
    a("## Coste, tokens y duración por novela")
    a("")
    a(md_tabla(
        ["Novela", "Tokens in", "Tokens out", "Coste USD", *[f"{f} USD" for f in ORDEN_FASES[:5]],
         "Trabajo del grafo", "Inicio → fin", "Nota"],
        [[f"`{n['nombre']}`", miles(n["totales"]["tokens_in"]), miles(n["totales"]["tokens_out"]),
          f"**{usd(n['totales']['coste_usd'])}**",
          *[usd(n["fases"][f]["coste_usd"]) if f in n["fases"] else "—" for f in ORDEN_FASES[:5]],
          dur(n["totales"]["minutos_de_trabajo"]),
          dur(n["duracion"]["minutos_hasta_ahora"] or n["duracion"]["minutos_min_inicio_max_fin"]),
          "en curso: hasta ahora" if n["duracion"]["minutos_hasta_ahora"] else
          ("fase abierta sin proceso" if n["duracion"]["abierta"] else "")] for n in produccion],
        "lrrr" + "r" * 5 + "rrl",
    ))
    a("")
    a("*Trabajo del grafo* suma la duración de las `fase_run` cerradas; *inicio → fin* va del primer "
      "`inicio` al último `fin` e incluye las esperas en los gates; en las novelas en curso llega hasta el momento de la extracción.")
    a("")

    a("## Coste medio por fase")
    a("")
    a("Solo cuentan las fases **cerradas** (ninguna `fase_run` abierta) de novelas que no son pruebas de fase; "
      "si una fase se ejecutó varias veces en la misma novela, se suman sus ejecuciones.")
    a("")
    medias = datos["coste_medio_por_fase"]
    a(md_tabla(
        ["Fase", "Novelas", "Coste medio USD", "Mín.", "Máx.", "Tokens in medios", "Tokens out medios", "Minutos medios"],
        [[f, m["n"], f"**{usd(m['media_usd'])}**", usd(m["min_usd"]), usd(m["max_usd"]), miles(m["tokens_in_medios"]),
          miles(m["tokens_out_medios"]), m["minutos_medios"]] for f, m in medias.items()],
        "lrrrrrrr",
    ))
    a("")
    pub = [n for n in produccion if n["versiones"] and (not n["duracion"]["abierta"] or n["solo_v1"])]
    if pub:
        costes = [n["totales"]["coste_usd"] for n in pub]
        a(f"Coste medio de una novela publicada, de principio a fin: **{usd(sum(costes) / len(costes))} USD** "
          f"sobre {len(pub)} novela(s) ({', '.join(f'`{n['nombre']}`' for n in pub)}).")
        a("")

    # Gates -----------------------------------------------------------------------------
    a("## Gates y decisiones")
    a("")
    filas_g = []
    for n in produccion:
        if not n["gates"]:
            filas_g.append([f"`{n['nombre']}`", "—", "sin gates (modo batch)", "—", "—"])
            continue
        c = Counter(f"{g['decision'] or g['estado']}" for g in n["gates"])
        filas_g.append([f"`{n['nombre']}`", len(n["gates"]),
                        ", ".join(f"{g['fase']}:{g['decision'] or g['estado']}" for g in n["gates"]),
                        ", ".join(f"{k} ×{v}" for k, v in c.items()),
                        sum(1 for g in n["gates"] if g["comentario"])])
    a(md_tabla(["Novela", "Gates", "Secuencia (fase:decisión)", "Recuento", "Con comentario"], filas_g, "lrlll"))
    a("")

    # Esperado vs obtenido -------------------------------------------------------------
    a("## Esperado vs obtenido")
    a("")
    a("Compara la sección `espera:` de cada brief de `ejemplos/evals/` con lo que hay en su base. "
      "**pendiente** = la novela no ha terminado (o no se ha lanzado); **revisar a mano** = el dato no se puede "
      "decidir desde la base.")
    a("")
    for clave, b in datos["briefs"].items():
        n = next((x for x in novelas if x["nombre"] == b["novela"]), None)
        cab_ = f"### `{clave}` → `{b['novela_esperada']}`"
        a(cab_)
        a("")
        a(f"{b['ficha']['ocasion']} · {b['ficha']['lugar']}, {b['ficha']['periodo']} "
          f"({b['ficha']['denominacion']}). Estado: **{n['estado'] if n else 'no lanzada'}**.")
        a("")
        a(md_tabla(["Qué", "Esperado", "Resultado", "Obtenido"],
                   [[r["que"], r["esperado"], r["resultado"], r["obtenido"]] for r in b["esperado_vs_obtenido"]],
                   "llcl"))
        a("")
        cuenta = Counter(r["resultado"] for r in b["esperado_vs_obtenido"])
        a("Resumen: " + ", ".join(f"{k} ×{v}" for k, v in cuenta.items()) + ".")
        a("")

    # Trazabilidad ----------------------------------------------------------------------
    a("## Trazabilidad de las ejecuciones")
    a("")
    a(md_tabla(
        ["Novela", "fase_run", "Con prompt_version", "Con prompt_nombre", "Con modelo", "Con trace_id"],
        [[f"`{n['nombre']}`", n["trazabilidad"]["fase_run"], n["trazabilidad"]["con_prompt_version"],
          n["trazabilidad"]["con_prompt_nombre"], n["trazabilidad"]["con_modelo"], n["trazabilidad"]["con_trace_id"]]
         for n in novelas],
        "lrrrrr",
    ))
    a("")
    if all(n["trazabilidad"]["con_trace_id"] == 0 and n["trazabilidad"]["con_prompt_version"] == 0 for n in novelas):
        a("Ninguna `fase_run` guarda `prompt_version` ni `trace_id`: esas columnas existen en el esquema pero "
          "el arnés no las rellena todavía.")
        a("")

    # Pruebas de fase -------------------------------------------------------------------
    a("## Pruebas de fase")
    a("")
    a("Novelas `fase-*`, `demo-*` y `prueba-*`: ensayos de una fase o de la integración con Langfuse. "
      "No entran en las tablas de evals ni en las medias.")
    a("")
    a(md_tabla(
        ["Novela", "Estado", "Fases (estado)", "Gates pendientes", "Versiones", "Juez", "Coste USD", "Tokens in / out"],
        [[f"`{n['nombre']}`", n["estado"],
          secuencia_de_fases(n),
          sum(1 for g in n["gates"] if g["estado"] == "pendiente"),
          ", ".join(f"v{v['numero']}" for v in n["versiones"]) or "—",
          ", ".join(f"{j['media']:.2f}" for j in n["juez"]) or "—",
          usd(n["totales"]["coste_usd"]), f"{miles(n['totales']['tokens_in'])} / {miles(n['totales']['tokens_out'])}"]
         for n in pruebas],
        "llllllrr",
    ))
    a("")
    return "\n".join(L)


def secuencia_de_fases(n: dict[str, Any]) -> str:
    """`fase:estado`, con la historia cuando la fase se ejecutó más de una vez."""
    return ", ".join(f"{f}:{'→'.join(d['estados'])}" for f, d in n["fases"].items())


def coste_medio_por_fase(produccion: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = {}
    for fase in ORDEN_FASES:
        muestras = [n["fases"][fase] for n in produccion
                    if fase in n["fases"] and not n["fases"][fase]["abierta"]
                    and "completada" in n["fases"][fase]["estados"]]
        if not muestras:
            continue
        costes = [m["coste_usd"] for m in muestras]
        mins = [m["minutos"] for m in muestras if m.get("minutos") is not None]
        out[fase] = {
            "n": len(muestras),
            "media_usd": round(sum(costes) / len(costes), 4),
            "min_usd": round(min(costes), 4),
            "max_usd": round(max(costes), 4),
            "tokens_in_medios": int(sum(m["tokens_in"] for m in muestras) / len(muestras)),
            "tokens_out_medios": int(sum(m["tokens_out"] for m in muestras) / len(muestras)),
            "minutos_medios": round(sum(mins) / len(mins), 1) if mins else None,
        }
    return out


def main() -> int:
    ahora = datetime.now(UTC)
    novelas = []
    for ruta in sorted(PROYECTOS.glob("*/*.db")):
        if ruta.stem != ruta.parent.name:
            continue
        try:
            novelas.append(extraer_novela(ruta, ahora))
        except sqlite3.Error as exc:
            print(f"AVISO: no se pudo leer {ruta}: {exc}", file=sys.stderr)

    briefs = {}
    for clave, b in cargar_briefs().items():
        esperada = f"eval-{clave}"
        nov = next((n for n in novelas if n["nombre"] == esperada), None)
        ocultar = nombres_a_ocultar(b.get("brief") or {})
        briefs[clave] = {
            "fichero": b["fichero"],
            "novela_esperada": esperada,
            "novela": nov["nombre"] if nov else None,
            "ficha": ficha_del_brief(b.get("brief") or {}, ocultar),
            "espera": b.get("espera"),
            "esperado_vs_obtenido": evaluar_espera(clave, b, nov),
        }

    produccion = [n for n in novelas if n["tipo"] != "prueba_de_fase"]
    datos = {
        "extraido_utc": ahora.strftime("%Y-%m-%d %H:%M:%S"),
        "extraido_local": ahora.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "provisional": [n["nombre"] for n in produccion
                        if n["duracion"]["abierta"] or n["estado"] in ("en_marcha", "en_pausa", "esperando_autor")],
        "novelas": novelas,
        "briefs": briefs,
        "coste_medio_por_fase": coste_medio_por_fase(produccion),
    }

    md = escribir_md(datos)
    for n in novelas:
        n.pop("_textos_publicados", None)
    (SALIDA / "evals.md").write_text(md + "\n", encoding="utf-8")
    (SALIDA / "evals.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(novelas)} novelas, {len(briefs)} briefs → {SALIDA / 'evals.md'} y evals.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
