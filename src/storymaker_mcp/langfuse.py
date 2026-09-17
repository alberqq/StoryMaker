#!/usr/bin/env python3
"""Servidor MCP de consulta a Langfuse.

Expone la observabilidad de las Ejecuciones como herramientas, para poder
preguntar "que hizo la ultima tirada y en que se fue el tiempo" sin salir de la
conversacion.

Es **de solo lectura**. No ingiere nada ni borra nada: para eso ya esta
`gui/langfuse.py`, que es quien traza. Separar las dos direcciones evita que una
consulta mal hecha escriba en la observabilidad, que es justo donde uno quiere
poder fiarse de lo que lee.

Biblioteca estandar, como el resto del arnes: JSON-RPC sobre entrada y salida
estandar, y `urllib` contra la API de Langfuse.

Las credenciales se resuelven del entorno --- `LANGFUSE_PUBLIC_KEY`,
`LANGFUSE_SECRET_KEY` y `LANGFUSE_HOST` --- o del fichero `.env` de la raiz.
Ninguna aparece jamas en una respuesta, ni recortada.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]
HOST_POR_DEFECTO = "https://cloud.langfuse.com"
VENTANA_POR_DEFECTO = 24


# ==========================================================================
# Credenciales y acceso
# ==========================================================================


def cargar_env() -> None:
    """Lee `.env` sin pisar lo que ya este definido en el entorno."""
    try:
        crudo = (RAIZ / ".env").read_text(encoding="utf-8")
    except OSError:
        return
    for linea in crudo.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        clave = clave.strip().removeprefix("export ").strip()
        valor = valor.strip().strip('"').strip("'")
        if clave and valor and clave not in os.environ:
            os.environ[clave] = valor


def credenciales() -> tuple[str, str, str] | None:
    cargar_env()
    publica = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
    secreta = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
    host = os.environ.get("LANGFUSE_HOST", HOST_POR_DEFECTO).strip().rstrip("/")
    return (publica, secreta, host) if publica and secreta else None


def consultar(ruta: str) -> dict[str, Any]:
    credencial = credenciales()
    if credencial is None:
        return {"error": "Faltan LANGFUSE_PUBLIC_KEY y LANGFUSE_SECRET_KEY"}
    publica, secreta, host = credencial
    autorizacion = base64.b64encode(f"{publica}:{secreta}".encode()).decode()
    peticion = urllib.request.Request(
        f"{host}{ruta}", headers={"Authorization": f"Basic {autorizacion}"}
    )
    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            return json.loads(respuesta.read())
    except urllib.error.HTTPError as error:
        # El codigo y el motivo si; la credencial que lo produjo, nunca.
        return {"error": f"HTTP {error.code}", "detalle": error.read()[:300].decode(
            "utf-8", "replace")}
    except Exception as error:  # noqa: BLE001
        return {"error": f"{type(error).__name__} al consultar Langfuse"}


def _ventana(horas: int) -> tuple[str, str]:
    ahora = datetime.now(timezone.utc)
    return (
        (ahora - timedelta(hours=horas)).isoformat().replace("+00:00", "Z"),
        (ahora + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
    )


def costes(horas: int) -> dict[tuple[str, str], dict[str, float]]:
    """Coste y tokens por traza y observacion, de la API de metricas.

    Aqui vive una leccion cara. El coste **no aparece** en
    `/api/public/v2/observations`: ese listado trae `inputPrice`, `outputPrice` y
    `totalPrice`, y los tres vuelven siempre nulos porque es una vista de lista y
    no calcula precios. Durante varias tiradas dimos por hecho que la traza salia
    a cero euros y buscamos el fallo en lo que mandabamos, cuando lo que estaba
    mal era **por donde lo leiamos**: el dato estaba en Langfuse desde el primer
    dia, en `/api/public/v2/metrics`.

    La dimension `traceId` es de cardinalidad alta y la API exige entonces
    `config.row_limit` y un `orderBy`. No es un capricho: sin tope, una consulta
    sobre muchas trazas se lleva por delante el servidor que la responde.
    """
    desde, hasta = _ventana(horas)
    consulta = {
        "view": "observations",
        "metrics": [
            {"measure": "totalCost", "aggregation": "sum"},
            {"measure": "totalTokens", "aggregation": "sum"},
        ],
        "dimensions": [{"field": "traceId"}, {"field": "name"}],
        "fromTimestamp": desde,
        "toTimestamp": hasta,
        "orderBy": [{"field": "sum_totalCost", "direction": "desc"}],
        "config": {"row_limit": 500},
    }
    datos = consultar(
        "/api/public/v2/metrics?query=" + urllib.parse.quote(json.dumps(consulta))
    )
    if "error" in datos:
        return {}

    tabla: dict[tuple[str, str], dict[str, float]] = {}
    for fila in datos.get("data") or []:
        clave = (fila.get("traceId") or "", fila.get("name") or "")
        tabla[clave] = {
            "coste": float(fila.get("sum_totalCost") or 0),
            "tokens": int(fila.get("sum_totalTokens") or 0),
        }
    return tabla


def observaciones(horas: int) -> list[dict[str, Any]]:
    """Las observaciones de las ultimas `horas`.

    Se usa la API v2 y no la de trazas: la primera quedo retirada para las
    organizaciones nuevas, y lo descubrimos con un 410 en la cara.
    """
    desde, hasta = _ventana(horas)
    datos = consultar(
        f"/api/public/v2/observations?fromStartTime={desde}&toStartTime={hasta}&limit=100"
    )
    return datos.get("data", []) if "error" not in datos else []


# ==========================================================================
# Lo que las herramientas responden
# ==========================================================================


# Las dos paradas de la Ejecucion. Se reconocen por el nombre del span, que es la
# clave del paso, porque los metadatos no vuelven en el listado de observaciones.
ESPERAS = ("espera_contexto", "espera_canon")


def _es_espera(observacion: dict[str, Any]) -> bool:
    return (observacion.get("name") or "") in ESPERAS


def _minutos(observacion: dict[str, Any]) -> float | None:
    ini, fin = observacion.get("startTime"), observacion.get("endTime")
    if not ini or not fin:
        return None
    a = datetime.fromisoformat(ini.replace("Z", "+00:00"))
    b = datetime.fromisoformat(fin.replace("Z", "+00:00"))
    return round((b - a).total_seconds() / 60, 1)


def _coste(observacion: dict[str, Any], tabla: dict[tuple[str, str], dict[str, float]]) -> float:
    """El coste de una observacion, cruzado con la tabla de metricas.

    No se lee de la observacion: ahi no esta. Se cruza por traza y nombre, que es
    la unica pareja que la API de metricas admite como dimension sin pedir
    permisos especiales.
    """
    ficha = tabla.get(((observacion.get("traceId") or ""), (observacion.get("name") or "")))
    return ficha["coste"] if ficha else 0.0


def listar_trazas(horas: int = VENTANA_POR_DEFECTO) -> dict[str, Any]:
    datos = observaciones(horas)
    tabla = costes(horas)
    if not datos:
        return {"trazas": [], "nota": f"Sin observaciones en las ultimas {horas} horas"}
    por_traza: dict[str, dict[str, Any]] = {}
    for observacion in datos:
        traza = observacion.get("traceId")
        ficha = por_traza.setdefault(traza, {
            "traza": traza, "observaciones": 0, "coste": 0.0,
            "minutos_trabajando": 0.0, "minutos_esperandote": 0.0,
            "errores": 0, "desde": observacion.get("startTime"),
        })
        ficha["observaciones"] += 1
        ficha["coste"] += _coste(observacion, tabla)
        # El tiempo de una parada no es tiempo de trabajo: el arnes esta quieto y
        # no consume presupuesto. Sumarlo al total hacia parecer lentas las
        # Ejecuciones en las que el Autor tardo en mirar.
        destino = "minutos_esperandote" if _es_espera(observacion) else "minutos_trabajando"
        ficha[destino] += _minutos(observacion) or 0
        if observacion.get("level") == "ERROR":
            ficha["errores"] += 1
        if (observacion.get("startTime") or "") < (ficha["desde"] or "z"):
            ficha["desde"] = observacion.get("startTime")
    trazas = sorted(por_traza.values(), key=lambda f: f["desde"] or "", reverse=True)
    for ficha in trazas:
        ficha["coste"] = round(ficha["coste"], 4)
        ficha["minutos_trabajando"] = round(ficha["minutos_trabajando"], 1)
        ficha["minutos_esperandote"] = round(ficha["minutos_esperandote"], 1)
    return {"trazas": trazas, "ventana_horas": horas}


def detalle_traza(traza: str, horas: int = VENTANA_POR_DEFECTO) -> dict[str, Any]:
    datos = [x for x in observaciones(horas) if x.get("traceId") == traza]
    tabla = costes(horas)
    if not datos:
        return {"error": f"Sin observaciones de {traza} en las ultimas {horas} horas"}
    datos.sort(key=lambda x: x.get("startTime") or "")
    pasos, generaciones = [], []
    for observacion in datos:
        comun = {
            "nombre": observacion.get("name"),
            "minutos": _minutos(observacion),
            "inicio": observacion.get("startTime"),
        }
        if observacion.get("type") == "GENERATION":
            ficha = tabla.get(
                ((observacion.get("traceId") or ""), (observacion.get("name") or ""))) or {}
            generaciones.append({
                **comun,
                # El modelo va en el nombre porque la observacion no lo devuelve:
                # se emite un span por modelo y el nombre es "<paso> - <modelo>".
                "modelo": (observacion.get("name") or "").split("\u00b7")[-1].strip(),
                "tokens": ficha.get("tokens"),
                "coste": round(ficha.get("coste", 0.0), 4),
            })
        else:
            paso = {**comun, "espera_del_autor": _es_espera(observacion)}
            if observacion.get("level") == "ERROR":
                paso["error"] = observacion.get("statusMessage")
            pasos.append(paso)
    return {
        "traza": traza,
        "pasos": pasos,
        "generaciones": generaciones,
        "coste_total": round(sum(g["coste"] for g in generaciones), 4),
        "minutos_trabajando": round(
            sum(p["minutos"] or 0 for p in pasos if not p.get("espera_del_autor")), 1),
        "minutos_esperandote": round(
            sum(p["minutos"] or 0 for p in pasos if p.get("espera_del_autor")), 1),
        "errores": [p for p in pasos if "error" in p],
    }


def resumen(horas: int = VENTANA_POR_DEFECTO) -> dict[str, Any]:
    datos = observaciones(horas)
    tabla = costes(horas)
    errores = [x for x in datos if x.get("level") == "ERROR"]
    # Las paradas se excluyen del ranking: una espera de tres horas siempre
    # ganaria, y lo que interesa saber es que **trabajo** tarda.
    lentos = sorted(
        [x for x in datos if _minutos(x) and not _es_espera(x)],
        key=lambda x: _minutos(x), reverse=True,
    )[:5]
    return {
        "ventana_horas": horas,
        "observaciones": len(datos),
        "trazas": len({x.get("traceId") for x in datos}),
        "por_tipo": dict(Counter(x.get("type") for x in datos)),
        "coste_total": round(sum(f["coste"] for f in tabla.values()), 4),
        "mas_caros": [
            {"traza": t, "nombre": n, "coste": round(f["coste"], 4), "tokens": f["tokens"]}
            for (t, n), f in sorted(
                tabla.items(), key=lambda p: p[1]["coste"], reverse=True)[:5]
            if f["coste"]
        ],
        "errores": [
            {"nombre": x.get("name"), "mensaje": x.get("statusMessage")} for x in errores
        ],
        "mas_lentos": [
            {"nombre": x.get("name"), "minutos": _minutos(x)} for x in lentos
        ],
        "minutos_esperandote": round(
            sum(_minutos(x) or 0 for x in datos if _es_espera(x)), 1),
        "nota_esperas": (
            "El tiempo de las dos paradas del Autor va aparte. No consume "
            "presupuesto y no cuenta como tiempo de trabajo del arnes."
        ),
    }


HERRAMIENTAS = [
    {
        "name": "langfuse_resumen",
        "description": (
            "Panorama de las Ejecuciones trazadas: cuantas, su coste, sus errores y "
            "los pasos mas lentos. Empieza por aqui."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"horas": {"type": "integer", "description": "Ventana hacia atras"}},
        },
    },
    {
        "name": "langfuse_trazas",
        "description": "Lista las trazas recientes con su coste, duracion y errores.",
        "inputSchema": {
            "type": "object",
            "properties": {"horas": {"type": "integer"}},
        },
    },
    {
        "name": "langfuse_traza",
        "description": (
            "El detalle de una traza: cada paso con su duracion, cada generacion con "
            "su modelo y su coste, y los errores."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "traza": {"type": "string", "description": "Identificador, como prc_..."},
                "horas": {"type": "integer"},
            },
            "required": ["traza"],
        },
    },
]

DESPACHO = {
    "langfuse_resumen": lambda a: resumen(a.get("horas", VENTANA_POR_DEFECTO)),
    "langfuse_trazas": lambda a: listar_trazas(a.get("horas", VENTANA_POR_DEFECTO)),
    "langfuse_traza": lambda a: detalle_traza(a["traza"], a.get("horas", VENTANA_POR_DEFECTO)),
}


# ==========================================================================
# Protocolo MCP sobre entrada y salida estandar
# ==========================================================================


def responder(identificador: Any, resultado: Any = None, error: Any = None) -> None:
    sobre: dict[str, Any] = {"jsonrpc": "2.0", "id": identificador}
    if error is not None:
        sobre["error"] = error
    else:
        sobre["result"] = resultado
    sys.stdout.write(json.dumps(sobre, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> int:
    for linea in sys.stdin:
        linea = linea.strip()
        if not linea:
            continue
        try:
            peticion = json.loads(linea)
        except json.JSONDecodeError:
            continue

        metodo = peticion.get("method")
        identificador = peticion.get("id")

        if metodo == "initialize":
            responder(identificador, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "sm-langfuse", "version": "1.0.0"},
            })
        elif metodo == "tools/list":
            responder(identificador, {"tools": HERRAMIENTAS})
        elif metodo == "tools/call":
            parametros = peticion.get("params") or {}
            nombre = parametros.get("name")
            argumentos = parametros.get("arguments") or {}
            funcion = DESPACHO.get(nombre)
            if funcion is None:
                responder(identificador, error={
                    "code": -32601, "message": f"Herramienta desconocida: {nombre}"})
                continue
            try:
                salida = funcion(argumentos)
            except Exception as fallo:  # noqa: BLE001
                salida = {"error": f"{type(fallo).__name__}: {fallo}"}
            responder(identificador, {
                "content": [{
                    "type": "text",
                    "text": json.dumps(salida, ensure_ascii=False, indent=1),
                }],
            })
        elif identificador is not None:
            responder(identificador, error={"code": -32601, "message": f"Metodo: {metodo}"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
