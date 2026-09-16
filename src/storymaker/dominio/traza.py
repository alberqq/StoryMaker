"""Trazabilidad (RF-081, RF-082, seccion 11).

Lo que un revisor puede reconstruir meses despues, sin preguntar a nadie: de que
escena planificada procede un pasaje, bajo que version de Canon se redacto, que
unidad y que llamada lo produjeron, que hallazgos lo modificaron, que afirmacion
historica lo respalda y de que fuente salio esa afirmacion, **con el contenido de
la fuente conservado aunque su localizador haya muerto**.

Todo sale del ledger y de los indices que de el se reconstruyen. Ninguna de las
dos consultas exige instrumentacion aparte.
"""

from __future__ import annotations

from typing import Any

from storymaker.errores import ErrorStoryMaker
from storymaker.ids import normalizar
from storymaker.indices import GestorIndices
from storymaker.ledger import Ledger
from storymaker.proyecto import Proyecto


def trazar_pasaje(
    proyecto: Proyecto, id_version_escena: str
) -> dict[str, Any]:
    """RF-081: dado un pasaje, toda su cadena de origen."""
    gestor = GestorIndices(proyecto.almacen)
    indice = gestor.leer("idx_traza_pasaje")
    if indice is None:
        gestor.reconstruir_todos()
        indice = gestor.leer("idx_traza_pasaje") or {}

    entrada = indice.get(id_version_escena)
    if entrada is None:
        raise ErrorStoryMaker(
            "ERR-304",
            f"No hay traza para {id_version_escena}. Puede ser una version descartada: "
            "el indice recorre la rama vigente.",
            version_escena=id_version_escena,
        )

    plan = proyecto.plan_canon(entrada.get("canon_plan_version"))
    ficha = _ficha(plan, entrada.get("escena")) if plan else None

    hallazgos = {
        h.get("id"): h
        for h in proyecto.almacen.leer_jsonl(proyecto.almacen.hallazgos)
        if h.get("id") in set(entrada.get("hallazgos_que_lo_modificaron", []))
    }

    llamadas = []
    if entrada.get("ejecucion"):
        ledger = Ledger(proyecto.almacen, entrada["ejecucion"])
        llamadas = [
            evento["carga"]
            for evento in ledger.eventos("llamada_modelo")
            if evento.get("carga", {}).get("id_unidad") == entrada.get("udt_origen")
        ]

    return {
        "version_escena": id_version_escena,
        "escena_planificada": ficha,
        "capitulo": entrada.get("capitulo"),
        "version_canon": entrada.get("canon_plan_version"),
        "guia_estilo_hash": entrada.get("guia_estilo_hash"),
        "ejecucion": entrada.get("ejecucion"),
        "unidad_de_trabajo": entrada.get("udt_origen"),
        "iteracion": entrada.get("iteracion"),
        "hash_texto": entrada.get("hash_texto"),
        "hallazgos_que_lo_modificaron": list(hallazgos.values()),
        "llamadas_a_modelo": llamadas,
        "cadena_completa": all([
            entrada.get("escena"),
            entrada.get("canon_plan_version"),
            entrada.get("ejecucion"),
            entrada.get("udt_origen"),
        ]),
    }


def trazar_afirmacion(proyecto: Proyecto, consulta: str) -> dict[str, Any]:
    """RF-082: dada una afirmacion historica, su respaldo o su licencia.

    Se admite tanto el identificador como un fragmento de texto: quien revisa una
    novela tiene delante una frase, no un `aff_`.
    """
    gestor = GestorIndices(proyecto.almacen)
    indice = gestor.leer("idx_afirmacion_novela")
    if indice is None:
        gestor.reconstruir_todos()
        indice = gestor.leer("idx_afirmacion_novela") or {}

    entrada = indice.get(consulta)
    identificador = consulta
    if entrada is None:
        aguja = normalizar(consulta)
        for clave, valor in indice.items():
            if clave.startswith("_"):
                continue
            if aguja and aguja in normalizar(valor.get("enunciado", "")):
                entrada, identificador = valor, clave
                break

    if entrada is None:
        return {
            "encontrada": False,
            "consulta": consulta,
            "nota": (
                "Sin respaldo en el Contexto historico. Una afirmacion historica del texto "
                "en esta situacion exige Licencia literaria registrada (INV-3)."
            ),
            "licencias_por_pasaje": indice.get("_licencias_por_pasaje", {}),
        }

    refutacion = next(
        (r for r in proyecto.almacen.leer_jsonl(proyecto.almacen.refutaciones)
         if r.get("afirmacion_id") == identificador),
        None,
    )
    restricciones = [
        r for r in proyecto.almacen.leer_jsonl(proyecto.almacen.restricciones)
        if r.get("afirmacion_id") == identificador
    ]

    fuentes = []
    for fuente in entrada.get("fuentes", []):
        contenido = None
        digest = (fuente.get("contenido_conservado") or "").removeprefix("cnt_")
        if digest:
            contenido = proyecto.almacen.recuperar_contenido_fuente(digest)
        fuentes.append({
            **fuente,
            "contenido_disponible": contenido is not None,
            "extracto": (contenido or "")[:600] or None,
        })

    return {
        "encontrada": True,
        "afirmacion": identificador,
        "enunciado": entrada.get("enunciado"),
        "estado": entrada.get("estado"),
        "fidelidad": entrada.get("fidelidad"),
        "refutacion": refutacion,
        "restricciones_derivadas": restricciones,
        "fuentes": fuentes,
        "nota_conservacion": (
            "El contenido conservado sostiene la trazabilidad aunque el localizador "
            "haya dejado de responder (RF-101)."
        ),
    }


def _ficha(plan: dict[str, Any] | None, id_escena: str | None) -> dict[str, Any] | None:
    if not plan or not id_escena:
        return None
    for capitulo in plan.get("capitulos", []):
        for escena in capitulo.get("escenas", []):
            if escena.get("id") == id_escena:
                return {"capitulo": capitulo["id"], **escena}
    return None
