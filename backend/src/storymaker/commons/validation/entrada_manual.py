"""spec: §3.6 · arq: §3, §15

**El segundo punto de ejecución del Core Domain.**

En producción, el grafo ejecuta estos validadores como nodos. Aquí se exponen para que
Claude Code los ejecute como *skill* y como *hook* cuando una persona edita un capítulo a
mano en el disco: la misma validación comprueba que la edición no ha roto los guardrails ni
la continuidad antes de commitear o de regenerar el PDF.

**Una sola lógica, dos puntos de ejecución.** Si divergieran, el producto y el editor
dejarían de estar de acuerdo sobre qué es válido, y por eso la prueba de contrato más
valiosa del proyecto ejecuta el mismo capítulo por ambos caminos y exige el mismo veredicto,
incidencia por incidencia.

Este módulo **no abre la novela**: recibe el texto y el contexto ya resuelto. Es lo que
permite validar un fichero suelto sin base de datos, que es exactamente el caso del hook.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from storymaker.commons.config import Defaults
from storymaker.commons.validation.chapter_validator import validar_capitulo
from storymaker.commons.validation.modelos import (
    CapituloEnRevision,
    EntidadFechada,
    Incidencia,
    TerminoProhibido,
)
from storymaker.commons.validation.policy_checker import guardrail_prohibidas


@dataclass(frozen=True)
class Informe:
    """Lo que ve quien edita a mano: las incidencias y si alguna bloquea."""

    incidencias: tuple[Incidencia, ...]

    @property
    def limpio(self) -> bool:
        return not self.incidencias

    @property
    def bloquea(self) -> bool:
        return any(i.bloquea for i in self.incidencias)

    def como_texto(self) -> str:
        if self.limpio:
            return "Sin incidencias: la edicion no ha roto nada de lo comprobable."
        lineas = [f"{len(self.incidencias)} incidencia(s):"]
        for i in self.incidencias:
            marca = "BLOQUEA" if i.bloquea else "aviso  "
            lineas.append(f"  [{marca}] {i.validador}: {i.mensaje}")
        return "\n".join(lineas)

    def como_json(self) -> str:
        return json.dumps(
            [
                {
                    "validador": i.validador,
                    "severidad": str(i.severidad),
                    "mensaje": i.mensaje,
                    "ubicacion": i.ubicacion,
                }
                for i in self.incidencias
            ],
            ensure_ascii=False,
            indent=2,
        )


def contexto_desde_json(datos: dict[str, Any]) -> dict[str, Any]:
    """Traduce el JSON que acompaña al capítulo a los tipos del Core Domain.

    El formato es deliberadamente plano: lo escribe el arnés al exportar un capítulo para
    edición manual, y tiene que poder escribirlo también una persona a mano cuando esté
    depurando algo.
    """
    return {
        "nombres_canonicos": tuple(datos.get("nombres_canonicos", ())),
        "prohibidas": tuple(
            TerminoProhibido(p["nivel"], p["termino"], p.get("normalizado", ""))
            for p in datos.get("prohibidas", ())
        ),
        "entidades_fechadas": tuple(
            EntidadFechada(e["nombre"], e.get("fecha_inicio"), e.get("fecha_fin"))
            for e in datos.get("entidades_fechadas", ())
        ),
        "fecha_narrativa": datos.get("fecha_narrativa"),
        "rango_palabras": tuple(datos.get("rango_palabras", Defaults.RANGO_PALABRAS)),
    }


def revisar(texto: str, contexto: dict[str, Any], *, numero: int = 0) -> Informe:
    """Corre sobre el texto los validadores que no necesitan la base.

    Son los mismos objetos que ejecuta el grafo, no una reimplementación: lo único que
    cambia es quién los llama y de dónde sale el contexto.
    """
    capitulo = CapituloEnRevision(
        numero=numero,
        texto=texto,
        palabras=len(texto.split()),
        **contexto,
    )
    incidencias = [*validar_capitulo(capitulo), *guardrail_prohibidas(capitulo)]
    return Informe(tuple(incidencias))


def revisar_fichero(ruta: Path, ruta_contexto: Path | None = None) -> Informe:
    """El punto de entrada del hook: un capítulo en disco y su contexto al lado."""
    texto = ruta.read_text(encoding="utf-8")
    if ruta_contexto is None:
        ruta_contexto = ruta.with_suffix(".contexto.json")
    datos: dict[str, Any] = {}
    if ruta_contexto.exists():
        datos = json.loads(ruta_contexto.read_text(encoding="utf-8"))
    return revisar(texto, contexto_desde_json(datos), numero=int(datos.get("numero", 0)))
