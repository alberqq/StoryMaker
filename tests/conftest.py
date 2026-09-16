"""Utilidades compartidas por las pruebas.

La estrategia de la seccion 12 pide cinco niveles. Aqui se cubren los cuatro que
no exigen agentes reales: unitario determinista, contrato, recuperacion e
integracion sobre una novela minima. La regresion de arnes necesita el conjunto de
encargos de referencia y un proveedor de modelos, y queda fuera del nucleo.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from storymaker.dominio import canon as d_canon  # noqa: E402
from storymaker.dominio import contexto as d_contexto  # noqa: E402
from storymaker.dominio import encargo as d_encargo  # noqa: E402
from storymaker.proyecto import Proyecto  # noqa: E402


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    return tmp_path / "proyectos"


@pytest.fixture
def proyecto(raiz: Path) -> Proyecto:
    return Proyecto.crear(raiz, "Prueba")


def encargo_minimo(**sobrescritos: Any) -> dict[str, Any]:
    """Encargo valido de dos capitulos, el mas pequeno que pasa las invariantes."""
    base = {
        "semillas": [{"tipo": "personaje", "texto_literal": "un cartografo flamenco que miente en sus mapas"}],
        "premisa": "Un cartografo falsifica una carta de navegacion y la corona la compra.",
        "epoca": {"desde": "1560", "hasta": "1570", "precision": "decada"},
        "ambito_geografico": "Amberes y Sevilla",
        "extension_objetivo_palabras": 2000,
        "tolerancia_extension": 0.10,
        "capitulos_objetivo": 2,
        "politica_hechos_sensibles": {"valor": "sin eufemismos y sin regodeo", "origen": "autor"},
        "politica_figuras_reales": {"valor": "solo lo documentado", "origen": "autor"},
        "guia_estilo": {
            "persona_narrativa": {"valor": "tercera", "estado": "declarado"},
            "tiempo_verbal": {"valor": "pasado", "estado": "declarado"},
            "registro": {"valor": None, "estado": "sin_preferencia"},
            "densidad_descriptiva": {"valor": "media", "estado": "declarado"},
            "recursos_apertura": {"valor": "in medias res", "estado": "declarado"},
            "longitud_media_frase": {"valor": 18, "estado": "declarado"},
            "prohibiciones": {"valor": None, "estado": "sin_preferencia"},
        },
    }
    base.update(sobrescritos)
    return base


def plan_minimo(**sobrescritos: Any) -> dict[str, Any]:
    """Plan de dos capitulos y cuatro escenas que cumple las ocho invariantes."""
    base = {
        "arco": "El enganno se descubre y cuesta lo que valia ocultarlo.",
        "hilos": [
            {
                "id": "hil_el-mapa-falso",
                "pregunta": "Se descubrira la falsificacion",
                "escena_apertura": "esc_001_001",
                "escenas_avance": ["esc_001_002", "esc_002_001"],
                "escena_resolucion": "esc_002_002",
            }
        ],
        "personajes": [
            {
                "id": "per_joos-van-der-beke",
                "nombre": "Joos van der Beke",
                "tipo": "ficticio",
                "funcion_narrativa": "protagonista",
                "rasgos": ["meticuloso"],
                "voz": "seca",
                "arco": "de la impunidad al miedo",
                "conocimiento_inicial": ["sabe que el mapa es falso"],
            }
        ],
        "lugares": [{"id": "lug_taller", "nombre": "El taller", "naturaleza": "ficticio"}],
        "revelaciones": [
            {
                "id": "rev_el-mapa-es-falso",
                "informacion": "El mapa esta falsificado",
                "escena": "esc_002_002",
                "ante": ["lector", "corona"],
                "escenas_actuando_sin_saberlo": ["esc_001_001", "esc_002_001"],
            }
        ],
        "linea_temporal": [{"id": "evf_entrega", "descripcion": "Entrega del mapa", "posicion": 1}],
        "capitulos": [
            {
                "id": "cap_001",
                "orden": 1,
                "titulo": "El taller",
                "escenas": [
                    _escena("esc_001_001", 1, "presentar al falsificador", "1560-03-01"),
                    _escena("esc_001_002", 2, "mostrar el encargo", "1560-03-02"),
                ],
            },
            {
                "id": "cap_002",
                "orden": 2,
                "titulo": "La corona",
                "escenas": [
                    _escena("esc_002_001", 1, "entregar el mapa", "1560-04-01"),
                    _escena(
                        "esc_002_002", 2, "descubrir la falsificacion", "1560-04-02",
                        revelaciones=["rev_el-mapa-es-falso"],
                    ),
                ],
            },
        ],
    }
    base.update(sobrescritos)
    return base


def _escena(
    identificador: str,
    orden: int,
    funcion: str,
    momento: str,
    revelaciones: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": identificador,
        "orden": orden,
        "funcion_narrativa": funcion,
        "personajes": ["per_joos-van-der-beke"],
        "lugar": "lug_taller",
        "momento": momento,
        "hilos": ["hil_el-mapa-falso"],
        "revelaciones": revelaciones or [],
        "presupuesto_palabras": 500,
    }


def cerrar_encargo(proyecto: Proyecto, **sobrescritos: Any) -> dict[str, Any]:
    d_encargo.ingerir_fichero(proyecto, encargo_minimo(**sobrescritos))
    return d_encargo.confirmar(proyecto, "autor-de-prueba")


def poblar_contexto(proyecto: Proyecto) -> dict[str, str]:
    """Contexto minimo: una afirmacion por seccion, verificada y refutada."""
    identificadores: dict[str, str] = {}
    fuente = d_contexto.registrar_fuente(
        proyecto, "https://ejemplo.test/amberes-1560", "web",
        contenido="En Amberes hacia 1560 los cartografos trabajaban con vitela y compas.",
    )
    contraria = d_contexto.registrar_fuente(
        proyecto, "https://ejemplo.test/critica", "rag",
        contenido="Una revision posterior matiza el uso de la vitela en talleres pequenos.",
    )
    identificadores["fuente"] = fuente["id"]
    identificadores["contraria"] = contraria["id"]

    from storymaker.invariantes import SECCIONES_OBLIGATORIAS

    for seccion in SECCIONES_OBLIGATORIAS:
        afirmacion = d_contexto.afirmar(
            proyecto,
            f"En Amberes hacia 1560, la seccion {seccion} se documenta con vitela y compas.",
            seccion,
            fuentes=[fuente["id"]],
        )
        identificadores[seccion] = afirmacion["id"]

    return identificadores


def aprobar_canon(proyecto: Proyecto, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    d_canon.proponer(proyecto, plan or plan_minimo())
    return d_canon.aprobar(proyecto, modo="agente", quien="sm-validador-canon")
