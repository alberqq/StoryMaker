"""Indices derivados (seccion 4.4).

Se borran y se reconstruyen por barrido completo. Su perdida cuesta tiempo, nunca
informacion. Ninguno existe si no lo justifica una consulta concreta.

MD-6 gobierna su uso: **ningun derivado alimenta una decision de negocio, solo una
consulta.** Un indice puede estar obsoleto; una decision no puede apoyarse en algo
que puede estarlo. Por eso `idx_hilos_estado` alimenta el panel de `/estado` y no
decide RF-077: esa decision recalcula el estado de los hilos en el momento de
decidirlo.

Los indices llevan la version del codigo que los genero (ADR-06 regla 6); si no
coincide, se descartan y se reconstruyen sin preguntar.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from storymaker import SCHEMA_VERSION, __version__
from storymaker.almacen import Almacen
from storymaker.ids import normalizar

# Cada indice, con la consulta que lo justifica y el requisito del que cuelga. Un
# indice que no pueda rellenar estas dos columnas no se construye.
CATALOGO_INDICES: dict[str, tuple[str, str]] = {
    "idx_traza_pasaje": ("Dado un pasaje, todo su origen", "RF-081, RNF-007"),
    "idx_afirmacion_novela": ("Dada una afirmacion historica del texto, su respaldo", "RF-082, RNF-008"),
    "idx_hechos_por_sujeto": ("Continuidad sin releer la Novela", "RF-062"),
    "idx_hallazgos_abiertos": ("Condicion de avance de todo bucle", "RF-064, RF-077"),
    "idx_consumo": ("Admision de presupuesto y calibracion", "RF-070 a RF-072, RF-079"),
    "idx_hilos_estado": ("Panel y consulta. NO decide RF-077", "RNF-002, RF-086"),
    "idx_restricciones_lexicas": ("Barrido de anacronismos por capitulo", "RF-063, RNF-005"),
    "idx_refutacion": ("Puede esta afirmacion sostener una Restriccion", "RF-100, RF-102"),
    "idx_protegido": ("Superficie de texto protegido y su umbral", "RNF-026"),
    "idx_cache": ("Evitar pagar dos veces lo mismo", "RNF-015"),
}


@dataclass
class Indice:
    nombre: str
    contenido: dict[str, Any]
    version_codigo: str = __version__
    schema_version: str = SCHEMA_VERSION
    construido_en: float = 0.0

    def como_dict(self) -> dict[str, Any]:
        consulta, requisito = CATALOGO_INDICES.get(self.nombre, ("", ""))
        return {
            "schema_version": self.schema_version,
            "nombre": self.nombre,
            "version_codigo": self.version_codigo,
            "consulta_que_lo_justifica": consulta,
            "requisito": requisito,
            "segundos_de_construccion": round(self.construido_en, 3),
            "contenido": self.contenido,
        }


class GestorIndices:
    def __init__(self, almacen: Almacen):
        self.almacen = almacen

    def ruta(self, nombre: str):
        return self.almacen.indices / f"{nombre}.json"

    def leer(self, nombre: str) -> dict[str, Any] | None:
        """Lee un indice, descartandolo si lo genero otra version del codigo."""
        dato = self.almacen.leer_json(self.ruta(nombre))
        if dato is None:
            return None
        if dato.get("version_codigo") != __version__:
            # ADR-06 regla 6: no se pregunta, se descarta.
            return None
        return dato.get("contenido")

    def escribir(self, indice: Indice) -> None:
        self.almacen.escribir_json(self.ruta(indice.nombre), indice.como_dict())

    def reconstruir_todos(self) -> dict[str, Any]:
        arranque = time.perf_counter()
        resultado: dict[str, Any] = {}
        for nombre, constructor in _CONSTRUCTORES.items():
            inicio = time.perf_counter()
            contenido = constructor(self.almacen)
            indice = Indice(nombre, contenido, construido_en=time.perf_counter() - inicio)
            self.escribir(indice)
            resultado[nombre] = {
                "entradas": len(contenido),
                "segundos": round(indice.construido_en, 3),
            }
        resultado["_total_segundos"] = round(time.perf_counter() - arranque, 3)
        return resultado


# --- Constructores por barrido completo -----------------------------------


def _idx_hechos_por_sujeto(almacen: Almacen) -> dict[str, Any]:
    """RF-062: continuidad sin releer la Novela.

    Es el indice que sustituye a darle al validador la novela entera. El detalle
    que causa las contradicciones de continuidad -- que mano, que color, que
    promesa exacta -- vive aqui y no se resume.
    """
    por_sujeto: dict[str, list[dict[str, Any]]] = {}
    retractados: set[str] = set()
    for hecho in almacen.leer_jsonl(almacen.hechos):
        if hecho.get("retracta"):
            retractados.add(hecho["retracta"])
    for hecho in almacen.leer_jsonl(almacen.hechos):
        if hecho.get("id") in retractados:
            continue
        clave = normalizar(hecho.get("sujeto", ""))
        por_sujeto.setdefault(clave, []).append({
            "id": hecho.get("id"),
            "enunciado": hecho.get("enunciado"),
            "sujeto": hecho.get("sujeto"),
            "tipo_sujeto": hecho.get("tipo_sujeto"),
            "escena_origen": hecho.get("escena_origen"),
        })
    return por_sujeto


def _idx_hallazgos_abiertos(almacen: Almacen) -> dict[str, Any]:
    """Condicion de avance de todo bucle (RF-064).

    El ultimo estado registrado de cada identificador gana: los hallazgos son de
    solo anexion y su ciclo de vida se compensa anexando transiciones.
    """
    ultimo: dict[str, dict[str, Any]] = {}
    for registro in almacen.leer_jsonl(almacen.hallazgos):
        ultimo[registro.get("id", "")] = registro
    abiertos: dict[str, list[dict[str, Any]]] = {}
    for registro in ultimo.values():
        if registro.get("estado") not in ("abierto", "en_correccion"):
            continue
        abiertos.setdefault(registro.get("unidad", "?"), []).append({
            "id": registro.get("id"),
            "severidad": registro.get("severidad"),
            "categoria": registro.get("categoria"),
            "causa_raiz": registro.get("causa_raiz"),
            "etapa_destino": registro.get("etapa_destino"),
        })
    return abiertos


def _idx_refutacion(almacen: Almacen) -> dict[str, Any]:
    """Puede esta afirmacion sostener una Restriccion (RF-100, RF-102)."""
    fidelidad = {
        a.get("id"): a.get("fidelidad")
        for a in almacen.leer_jsonl(almacen.afirmaciones)
    }
    salida: dict[str, Any] = {}
    for refutacion in almacen.leer_jsonl(almacen.refutaciones):
        identificador = refutacion.get("afirmacion_id")
        veredicto = refutacion.get("veredicto")
        salida[identificador] = {
            "veredicto": veredicto,
            "fidelidad": fidelidad.get(identificador),
            "sostiene_comprobable": (
                veredicto in ("confirmada", "matizada")
                and fidelidad.get(identificador) == "verificada"
            ),
            "solo_cualitativa": veredicto == "no_refutable_documentalmente",
        }
    return salida


def _idx_restricciones_lexicas(almacen: Almacen) -> dict[str, Any]:
    """Barrido de anacronismos por capitulo (RF-063, RNF-005).

    Solo las lexicas: son las unicas que se comprueban por presencia de termino.
    Las de mentalidad se juzgan, y por eso no estan aqui.
    """
    lexicas: dict[str, Any] = {}
    for restriccion in almacen.leer_jsonl(almacen.restricciones):
        if restriccion.get("categoria") != "lexica" or restriccion.get("estado") == "revocada":
            continue
        lexicas[restriccion["id"]] = {
            "enunciado": restriccion.get("enunciado"),
            "terminos_prohibidos": restriccion.get("terminos_prohibidos", []),
            "afirmacion_id": restriccion.get("afirmacion_id"),
            "severidad": restriccion.get("severidad_incumplimiento", "bloqueante"),
        }
    return lexicas


def _idx_hilos_estado(almacen: Almacen) -> dict[str, Any]:
    """Panel y consulta. NO decide RF-077 (MD-6).

    Se deja constancia del aviso dentro del propio indice para que nadie lo use
    para decidir por comodidad.
    """
    plan = _plan_vigente(almacen)
    if not plan:
        return {}
    hechos_por_escena = {}
    for hecho in almacen.leer_jsonl(almacen.hechos):
        hechos_por_escena.setdefault(hecho.get("escena_origen"), []).append(hecho.get("id"))

    ramas = almacen.leer_json(almacen.ramas, {}) or {}
    vigentes = set((ramas.get("principal") or {}).keys())

    estado: dict[str, Any] = {
        "_aviso": "Indice de consulta. MD-6 prohibe decidir RF-077 sobre este dato.",
    }
    for hilo in plan.get("hilos", []):
        escenas = set(hilo.get("escenas_avance", []))
        if hilo.get("escena_apertura"):
            escenas.add(hilo["escena_apertura"])
        resolucion = hilo.get("escena_resolucion")
        escritas = escenas & vigentes
        if resolucion and resolucion in vigentes:
            situacion = "resuelto"
        elif escritas:
            situacion = "avanzado"
        elif hilo.get("escena_apertura") in vigentes:
            situacion = "abierto"
        else:
            situacion = "planificado"
        estado[hilo["id"]] = {
            "estado": situacion,
            "escenas_escritas": sorted(escritas),
            "escena_resolucion": resolucion,
        }
    return estado


def _idx_protegido(almacen: Almacen) -> dict[str, Any]:
    """Superficie de texto protegido y su umbral (RNF-026).

    Aviso por encima del 15 % en un capitulo o del 10 % en la novela. La pasada
    global revisa las protecciones vigentes y libera las que ya no sostienen
    ningun Hallazgo, que es lo que impide que la novela se osifique.
    """
    por_capitulo: dict[str, dict[str, int]] = {}
    total_palabras = 0
    total_protegidas = 0

    ramas = almacen.leer_json(almacen.ramas, {}) or {}
    for id_escena, id_version in (ramas.get("principal") or {}).items():
        meta = almacen.leer_json(almacen.meta_escena(id_escena, id_version), {}) or {}
        capitulo = meta.get("capitulo", "?")
        palabras = meta.get("palabras", 0)
        protegidas = meta.get("protegido_palabras", 0)
        entrada = por_capitulo.setdefault(capitulo, {"palabras": 0, "protegidas": 0})
        entrada["palabras"] += palabras
        entrada["protegidas"] += protegidas
        total_palabras += palabras
        total_protegidas += protegidas

    salida: dict[str, Any] = {}
    for capitulo, datos in sorted(por_capitulo.items()):
        proporcion = datos["protegidas"] / datos["palabras"] if datos["palabras"] else 0.0
        salida[capitulo] = {
            **datos,
            "proporcion": round(proporcion, 4),
            "sobre_umbral": proporcion > 0.15,
        }
    proporcion_total = total_protegidas / total_palabras if total_palabras else 0.0
    salida["_novela"] = {
        "palabras": total_palabras,
        "protegidas": total_protegidas,
        "proporcion": round(proporcion_total, 4),
        "sobre_umbral": proporcion_total > 0.10,
    }
    return salida


def _idx_traza_pasaje(almacen: Almacen) -> dict[str, Any]:
    """Dado un pasaje, todo su origen (RF-081, RNF-007)."""
    traza: dict[str, Any] = {}
    ramas = almacen.leer_json(almacen.ramas, {}) or {}
    for id_escena, id_version in (ramas.get("principal") or {}).items():
        meta = almacen.leer_json(almacen.meta_escena(id_escena, id_version), {}) or {}
        traza[id_version] = {
            "escena": id_escena,
            "capitulo": meta.get("capitulo"),
            "canon_plan_version": meta.get("canon_plan_version"),
            "guia_estilo_hash": meta.get("guia_estilo_hash"),
            "udt_origen": meta.get("udt_origen"),
            "ejecucion": meta.get("ejecucion"),
            "iteracion": meta.get("iteracion"),
            "hallazgos_que_lo_modificaron": meta.get("hallazgos_aplicados", []),
            "hash_texto": meta.get("hash_texto"),
        }
    return traza


def _idx_afirmacion_novela(almacen: Almacen) -> dict[str, Any]:
    """Dada una afirmacion historica del texto, su respaldo (RF-082, RNF-008)."""
    fuentes = {f.get("id"): f for f in almacen.leer_jsonl(almacen.fuentes)}
    licencias = {}
    for licencia in almacen.leer_jsonl(almacen.licencias):
        for pasaje in licencia.get("pasajes", []):
            licencias.setdefault(pasaje, []).append(licencia.get("id"))

    respaldo: dict[str, Any] = {}
    for afirmacion in almacen.leer_jsonl(almacen.afirmaciones):
        respaldo[afirmacion["id"]] = {
            "enunciado": afirmacion.get("enunciado"),
            "estado": afirmacion.get("estado"),
            "fidelidad": afirmacion.get("fidelidad"),
            "fuentes": [
                {
                    "id": identificador,
                    "localizador": (fuentes.get(identificador) or {}).get("localizador"),
                    "consultada_en": (fuentes.get(identificador) or {}).get("consultada_en"),
                    "contenido_conservado": (fuentes.get(identificador) or {}).get("contenido_id"),
                }
                for identificador in afirmacion.get("fuentes", [])
            ],
        }
    respaldo["_licencias_por_pasaje"] = licencias
    return respaldo


def _idx_consumo(almacen: Almacen) -> dict[str, Any]:
    """Admision de presupuesto y calibracion (RF-070 a RF-072, RF-079)."""
    por_ejecucion: dict[str, Any] = {}
    carpeta = almacen.raiz / "ejecuciones"
    if not carpeta.exists():
        return por_ejecucion
    for directorio in sorted(carpeta.iterdir()):
        if not directorio.is_dir():
            continue
        registros = almacen.leer_jsonl(directorio / "consumo.jsonl")
        acumulado = {
            "iteraciones": 0, "coste": 0.0, "segundos": 0.0,
            "tokens_entrada": 0, "tokens_salida": 0,
        }
        for registro in registros:
            for clave in acumulado:
                acumulado[clave] += registro.get(clave, 0)
        acumulado["coste"] = round(acumulado["coste"], 6)
        acumulado["llamadas"] = len(registros)
        por_ejecucion[directorio.name] = acumulado
    return por_ejecucion


def _idx_cache(almacen: Almacen) -> dict[str, Any]:
    """Evitar pagar dos veces lo mismo (RNF-015).

    Clave de idempotencia -> resultado de la unidad ya cerrada. Es lo que hace
    que reanudar una Ejecucion caida no vuelva a gastar.
    """
    cache: dict[str, Any] = {}
    carpeta = almacen.raiz / "ejecuciones"
    if not carpeta.exists():
        return cache
    for directorio in sorted(carpeta.iterdir()):
        if not directorio.is_dir():
            continue
        for evento in almacen.leer_jsonl(directorio / "ledger.jsonl"):
            if evento.get("tipo") != "unidad_cerrada":
                continue
            carga = evento.get("carga", {})
            clave = carga.get("clave_idempotencia")
            if clave:
                cache[clave] = {
                    "ejecucion": directorio.name,
                    "unidad": carga.get("unidad"),
                    "modo_cierre": carga.get("modo_cierre"),
                    "version_vigente": carga.get("version_vigente"),
                }
    return cache


def _plan_vigente(almacen: Almacen) -> dict[str, Any] | None:
    proyecto = almacen.leer_json(almacen.fichero_proyecto, {}) or {}
    version = proyecto.get("canon_version_vigente")
    if not version:
        return None
    return almacen.leer_json(almacen.plan_canon(version))


_CONSTRUCTORES: dict[str, Callable[[Almacen], dict[str, Any]]] = {
    "idx_traza_pasaje": _idx_traza_pasaje,
    "idx_afirmacion_novela": _idx_afirmacion_novela,
    "idx_hechos_por_sujeto": _idx_hechos_por_sujeto,
    "idx_hallazgos_abiertos": _idx_hallazgos_abiertos,
    "idx_consumo": _idx_consumo,
    "idx_hilos_estado": _idx_hilos_estado,
    "idx_restricciones_lexicas": _idx_restricciones_lexicas,
    "idx_refutacion": _idx_refutacion,
    "idx_protegido": _idx_protegido,
    "idx_cache": _idx_cache,
}
