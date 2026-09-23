"""spec: §4.1 · arq: §4

El fichero de encargo que escribe una persona, convertido en lo que el grafo sabe recibir.

**Es la puerta por la que entra una novela**, y hasta que existió no había ninguna: la CLI
recibía la ruta del brief, creaba el fichero de la novela y arrancaba la invocación sin
haber abierto el encargo, de modo que el entrevistador empezaba con una premisa vacía y
preguntaba por todo.

**Lo que produce es una premisa, no un `Brief`.** La distinción es el diseño de la Fase 1 y
conviene no pisarlo: el sistema arranca de materia prima y el entrevistador la convierte en
`Brief` preguntando solo por lo que falte. Un atajo que escribiera `intake_brief`
directamente desde el YAML tendría dos caminos de entrada con dos validaciones distintas, y
el segundo —el del comprador que escribe cuatro líneas— es el que de verdad importa.

Así que el encargo se **redacta en prosa** y entra como premisa. Un fichero completo deja al
entrevistador sin nada que preguntar, que es exactamente lo que el modo batch necesita; uno
a medias deja las preguntas justas.

Se admiten dos formas de fichero, y las dos existen en el repositorio: la de
`ejemplos/brief-ejemplo.yaml`, con los tres bloques arriba, y la de `evals/briefs/*.yaml`,
que los anida bajo `brief:` junto a lo que ese eval espera. Distinguirlas es mirar si hay
una clave `brief`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from storymaker.commons.config import Defaults
from storymaker.commons.errores import ErrorDeStoryMaker


class EncargoIlegible(ErrorDeStoryMaker):
    """El fichero no se puede leer, o no tiene la forma de un encargo.

    Es un error del Autor y no del sistema, así que dice qué falta en lugar de dónde
    reventó: quien escribe un brief a mano se equivoca en el nombre de una clave, no en la
    sintaxis de YAML.
    """


@dataclass(frozen=True)
class Encargo:
    """Lo que hace falta para arrancar una novela. Nada más."""

    #: El nombre del fichero de la novela en `proyectos/`, derivado del homenajeado.
    nombre: str
    #: La materia prima de la Fase 1, en prosa. No es la Premisa narrativa del módulo 2.
    premisa: str
    #: Cuántos capítulos pidió el encargo. Gobierna el bucle de Writing.
    n_capitulos: int
    #: Lo que el comprador pegó, si pegó algo. Entra en cuarentena.
    texto_pegado: str = ""


def _cargar(ruta: Path) -> dict[str, Any]:
    """YAML o JSON, según la extensión. Nada más elaborado hace falta."""
    if not ruta.exists():
        raise EncargoIlegible(f"No existe el fichero de encargo {ruta}.")

    texto = ruta.read_text(encoding="utf-8")
    try:
        if ruta.suffix.lower() in (".yaml", ".yml"):
            import yaml

            datos = yaml.safe_load(texto)
        else:
            datos = json.loads(texto)
    except Exception as fallo:
        raise EncargoIlegible(f"{ruta} no se puede interpretar: {fallo}") from fallo

    if not isinstance(datos, dict):
        raise EncargoIlegible(f"{ruta} no contiene un encargo: la raiz no es un mapa.")
    # Los briefs de evaluación anidan el encargo y le añaden lo que esperan de él.
    interior = datos.get("brief")
    return dict(interior) if isinstance(interior, dict) else datos


def _lista(valor: Any) -> list[Any]:
    if isinstance(valor, list):
        return valor
    return [] if valor is None else [valor]


def _nombre_de_fichero(nombre: str) -> str:
    """El nombre del homenajeado, reducido a algo que sirva de nombre de fichero."""
    from storymaker.commons.validation.puras import normalizar

    limpio = normalizar(nombre).replace(" ", "-")
    return limpio or "novela"


def redactar(datos: dict[str, Any]) -> str:
    """El encargo en prosa, que es como el entrevistador lo entiende.

    Se escribe en el orden de los tres bloques —a quién se regala, en qué mundo, con qué
    reglas— porque es el orden en el que una persona lo contaría, y el entrevistador está
    entrenado para conversar, no para leer un volcado de claves. Lo que falte sencillamente
    no se menciona: una línea «tono: None» le haría preguntar por un campo que el comprador
    no tiene por qué haber rellenado.
    """
    homenajeado = dict(datos.get("homenajeado") or {})
    mundo = dict(datos.get("mundo") or {})
    obra = dict(datos.get("obra") or {})
    partes: list[str] = []

    nombre = homenajeado.get("nombre_homenajeado")
    if nombre:
        quien = f"La novela es un regalo para {nombre}"
        if homenajeado.get("fecha_nacimiento"):
            quien += f", nacido el {homenajeado['fecha_nacimiento']}"
        if homenajeado.get("rol_epoca"):
            quien += f", y en la novela es {homenajeado['rol_epoca']}"
        if homenajeado.get("ocasion"):
            quien += f". La ocasion es su {homenajeado['ocasion']}"
        partes.append(quien + ".")
        partes.append(
            f"Su nombre tiene que aparecer escrito exactamente asi: {nombre}."
        )

    elementos = _lista(homenajeado.get("elementos_personalizacion"))
    if elementos:
        lineas = ["De su vida hay que incorporar:"]
        for elemento in elementos:
            if not isinstance(elemento, dict):
                continue
            marca = "obligatorio" if elemento.get("obligatorio") else "si encaja"
            lineas.append(f"  - {elemento.get('texto', '')} ({marca})")
        partes.append("\n".join(lineas))

    periodo = dict(mundo.get("periodo") or {})
    if periodo or mundo.get("lugar"):
        donde = "Transcurre"
        if periodo.get("denominacion"):
            donde += f" durante {periodo['denominacion']}"
        if periodo.get("inicio") and periodo.get("fin"):
            donde += f", entre {periodo['inicio']} y {periodo['fin']}"
        if mundo.get("lugar"):
            donde += f", en {mundo['lugar']}"
        partes.append(donde + ".")
    if mundo.get("evento_ancla"):
        partes.append(f"Conviene anclarla en {mundo['evento_ancla']}.")

    historicos = dict(mundo.get("personajes_historicos") or {})
    if _lista(historicos.get("aparecen")):
        partes.append(
            "Deben aparecer estos personajes historicos: "
            + ", ".join(str(p) for p in _lista(historicos["aparecen"]))
            + "."
        )
    if _lista(historicos.get("se_evitan")):
        partes.append(
            "Y estos no deben aparecer: "
            + ", ".join(str(p) for p in _lista(historicos["se_evitan"]))
            + "."
        )

    genero = obra.get("genero")
    if isinstance(genero, dict):
        etiqueta = str(genero.get("principal", ""))
        if genero.get("subgenero"):
            etiqueta += f" {genero['subgenero']}"
    else:
        etiqueta = str(genero or "")
    if etiqueta.strip():
        partes.append(f"El genero es {etiqueta.strip()}.")
    for clave, plantilla in (
        ("tono", "El tono, {}."),
        ("punto_de_vista", "El punto de vista, {}."),
        ("grado_licencia", "El grado de licencia historica es {}."),
        ("arcaismo", "El arcaismo del lenguaje, {}."),
        ("contenido_admisible", "Contenido admisible: {}."),
    ):
        if obra.get(clave):
            partes.append(plantilla.format(obra[clave]))

    prohibidas = obra.get("palabras_prohibidas")
    if isinstance(prohibidas, dict):
        for nivel, palabras in prohibidas.items():
            if _lista(palabras):
                partes.append(
                    f"Palabras prohibidas ({nivel}): "
                    + ", ".join(str(p) for p in _lista(palabras))
                    + "."
                )

    capitulos = obra.get("n_capitulos", Defaults.N_CAPITULOS)
    palabras = obra.get("palabras_por_capitulo", Defaults.PALABRAS_POR_CAPITULO)
    partes.append(f"Son {capitulos} capitulos de unas {palabras} palabras cada uno.")

    return "\n\n".join(partes)


def leer(ruta: Path) -> Encargo:
    """El encargo completo, listo para `Arranque`."""
    datos = _cargar(ruta)
    homenajeado = dict(datos.get("homenajeado") or {})
    obra = dict(datos.get("obra") or {})

    nombre = str(homenajeado.get("nombre_homenajeado") or "").strip()
    if not nombre:
        raise EncargoIlegible(
            f"{ruta} no dice a quien se regala la novela: falta "
            f"`homenajeado.nombre_homenajeado`, que es lo unico imprescindible."
        )

    try:
        capitulos = int(obra.get("n_capitulos", Defaults.N_CAPITULOS))
    except (TypeError, ValueError) as fallo:
        raise EncargoIlegible(f"{ruta}: `obra.n_capitulos` no es un numero.") from fallo

    return Encargo(
        nombre=_nombre_de_fichero(nombre),
        premisa=redactar(datos),
        n_capitulos=max(1, capitulos),
        texto_pegado=str(datos.get("texto_libre") or ""),
    )
