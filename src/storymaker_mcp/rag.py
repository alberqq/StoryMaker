"""Servidor MCP `sm-rag`: consulta sobre el corpus indexado (RF-012).

Devuelve siempre referencia a documento y fragmento, nunca contenido suelto.

El indice es una tabla invertida en memoria construida por barrido del corpus. Es
deliberadamente simple y esta declarado como tal: la Tecnica deja abierto el indice
vectorial sin motor de base de datos porque requiere una prueba de concepto antes de
comprometer un diseno. Hasta que esa prueba exista, esto recupera por terminos, que
es suficiente para un corpus de trabajo de unos miles de documentos y no introduce
una dependencia que despues habria que desandar.

El corpus se declara en `SM_RAG_CORPUS`. Si no esta accesible, el servidor devuelve
ERR-801 y el investigador degrada al otro modo declarando la cobertura reducida.
"""

from __future__ import annotations

import os
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from storymaker_mcp.servidor import Resultado, Servidor, ahora, filtrar_validos

EXTENSIONES = (".md", ".txt", ".rst", ".json")
PALABRAS_FRAGMENTO = 120

servidor = Servidor("sm-rag")


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^\w\s]", " ", sin_tildes.lower())


def _terminos(texto: str) -> list[str]:
    return [t for t in _normalizar(texto).split() if len(t) > 2]


def _raiz_corpus() -> Path | None:
    declarado = os.environ.get("SM_RAG_CORPUS")
    if not declarado:
        return None
    raiz = Path(declarado)
    return raiz if raiz.exists() else None


def _documentos(raiz: Path) -> list[Path]:
    return [
        fichero
        for fichero in sorted(raiz.rglob("*"))
        if fichero.is_file() and fichero.suffix.lower() in EXTENSIONES
    ]


def _puntuar(terminos_consulta: list[str], texto: str) -> tuple[float, int]:
    """Puntuacion por frecuencia de termino, y la posicion del mejor fragmento."""
    normalizado = _normalizar(texto)
    palabras = normalizado.split()
    recuento = Counter(palabras)
    puntuacion = sum(recuento.get(t, 0) for t in terminos_consulta)
    if puntuacion == 0:
        return 0.0, 0
    # El mejor fragmento es la ventana con mas terminos de la consulta.
    mejor_indice, mejor_densidad = 0, 0
    for inicio in range(0, max(1, len(palabras) - PALABRAS_FRAGMENTO), 20):
        ventana = palabras[inicio:inicio + PALABRAS_FRAGMENTO]
        densidad = sum(1 for p in ventana if p in terminos_consulta)
        if densidad > mejor_densidad:
            mejor_indice, mejor_densidad = inicio, densidad
    return puntuacion / (len(palabras) or 1) * 1000, mejor_indice


def _fragmento(texto: str, indice_palabra: int) -> str:
    palabras = texto.split()
    return " ".join(palabras[indice_palabra:indice_palabra + PALABRAS_FRAGMENTO])


@servidor.herramienta(
    "buscar",
    "Busca en el corpus documental indexado. Devuelve, por cada resultado, el "
    "contenido del fragmento, la referencia al documento de origen y la fecha de "
    "consulta. Nunca devuelve contenido sin su localizador.",
    {
        "type": "object",
        "properties": {
            "consulta": {"type": "string", "description": "Terminos de busqueda"},
            "limite": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        },
        "required": ["consulta"],
    },
)
def buscar(argumentos: dict[str, Any]) -> dict[str, Any]:
    raiz = _raiz_corpus()
    if raiz is None:
        # ERR-801: el investigador degrada al otro modo y declara cobertura reducida.
        return {
            "ok": False,
            "codigo_error": "ERR-801",
            "mensaje": (
                "El corpus RAG no esta accesible. Declara su ruta en SM_RAG_CORPUS. "
                "Degrada a recuperacion web y marca la cobertura reducida en el "
                "Contexto historico."
            ),
            "resultados": [],
        }

    consulta = str(argumentos.get("consulta", ""))
    limite = int(argumentos.get("limite", 5))
    terminos = _terminos(consulta)
    if not terminos:
        return {"ok": False, "codigo_error": "ERR-802", "mensaje": "Consulta vacia", "resultados": []}

    candidatos: list[tuple[float, Resultado]] = []
    for documento in _documentos(raiz):
        try:
            texto = documento.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        puntuacion, indice = _puntuar(terminos, texto)
        if puntuacion <= 0:
            continue
        candidatos.append((puntuacion, Resultado(
            contenido=_fragmento(texto, indice),
            # El localizador de un resultado RAG es documento mas fragmento: sin la
            # posicion, "lo dice este fichero de 400 paginas" no es un localizador.
            localizador=f"rag://{documento.relative_to(raiz).as_posix()}#palabra={indice}",
            consultado_en=ahora(),
            titulo=documento.stem,
            fragmento=f"palabras {indice}-{indice + PALABRAS_FRAGMENTO}",
            fiabilidad="corpus_del_autor",
        )))

    candidatos.sort(key=lambda par: -par[0])
    validos, descartados = filtrar_validos([r for _, r in candidatos[:limite]])

    if not validos:
        return {
            "ok": True,
            "codigo_error": "ERR-802",
            "mensaje": (
                "Sin resultados en el corpus dentro del ambito. Declara laguna en lugar "
                "de rellenar con verosimilitud."
            ),
            "resultados": [],
            "descartados": descartados,
        }

    return {
        "ok": True,
        "consulta": consulta,
        "documentos_examinados": len(_documentos(raiz)),
        "resultados": validos,
        "descartados": descartados,
        "nota": (
            "Cada resultado trae contenido, localizador y fecha. Registralos con "
            "`storymaker contexto fuente --tipo rag` antes de afirmar nada sobre ellos."
        ),
    }


@servidor.herramienta(
    "estado_corpus",
    "Informa de si el corpus esta accesible y de cuantos documentos contiene, sin "
    "recuperar nada.",
    {"type": "object", "properties": {}},
)
def estado_corpus(_argumentos: dict[str, Any]) -> dict[str, Any]:
    raiz = _raiz_corpus()
    if raiz is None:
        return {
            "ok": False,
            "codigo_error": "ERR-801",
            "accesible": False,
            "mensaje": "SM_RAG_CORPUS no esta declarado o su ruta no existe",
        }
    documentos = _documentos(raiz)
    return {
        "ok": True,
        "accesible": True,
        "raiz": str(raiz),
        "documentos": len(documentos),
        "extensiones_indexadas": list(EXTENSIONES),
    }


def main() -> int:
    return servidor.ejecutar()


if __name__ == "__main__":
    raise SystemExit(main())
