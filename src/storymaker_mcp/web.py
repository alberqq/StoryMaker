"""Servidor MCP `sm-web`: recuperacion en la web abierta (RF-011, RF-101).

Devuelve siempre contenido mas localizador mas fecha, y **conserva el contenido en
el momento de la consulta**. Un localizador puede morir; el contenido conservado es
lo que mantiene viva la trazabilidad de RF-082 meses despues.

## Sobre el proveedor de busqueda

El arnes no se casa con un buscador. `SM_WEB_PROVEEDOR` declara cual usar y
`SM_WEB_API_KEY` su credencial, que **se resuelve del entorno en tiempo de ejecucion
y nunca se persiste**: lo que se registra es el marcador, no el valor.

Sin proveedor declarado, la busqueda devuelve ERR-801 y el investigador degrada al
corpus RAG declarando la cobertura reducida. La recuperacion de una pagina concreta
si funciona siempre, porque no necesita buscador: solo necesita la direccion.

Si fallan los dos modos, la etapa falla y la Ejecucion se detiene (ERR-803):
redactar sin contexto contradice el segundo objetivo del arnes.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any

from storymaker_mcp.servidor import Resultado, Servidor, ahora, filtrar_validos

AGENTE = "StoryMaker/2.0 (arnes de novela historica; recuperacion documental)"
TIEMPO_ESPERA = 30
MAXIMO_CARACTERES = 60_000

servidor = Servidor("sm-web")


class _ExtractorTexto(HTMLParser):
    """Saca el texto legible de una pagina, sin dependencias.

    No hace falta un analizador completo: lo que se conserva es el material sobre el
    que se va a afirmar algo, y para eso sobra el marcado.
    """

    _IGNORADAS = {"script", "style", "noscript", "svg", "head", "nav", "footer"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.partes: list[str] = []
        self.titulo = ""
        self._en_titulo = False
        self._profundidad_ignorada = 0

    def handle_starttag(self, etiqueta, _atributos):
        if etiqueta in self._IGNORADAS:
            self._profundidad_ignorada += 1
        elif etiqueta == "title":
            self._en_titulo = True

    def handle_endtag(self, etiqueta):
        if etiqueta in self._IGNORADAS and self._profundidad_ignorada:
            self._profundidad_ignorada -= 1
        elif etiqueta == "title":
            self._en_titulo = False

    def handle_data(self, datos):
        if self._profundidad_ignorada:
            return
        if self._en_titulo:
            self.titulo += datos.strip()
            return
        limpio = datos.strip()
        if limpio:
            self.partes.append(limpio)

    @property
    def texto(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "\n".join(self.partes))


def _descargar(url: str) -> tuple[str, str]:
    peticion = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA) as respuesta:
        bruto = respuesta.read()
    texto = bruto.decode("utf-8", errors="replace")
    if "<" in texto[:2000] and ">" in texto[:2000]:
        extractor = _ExtractorTexto()
        extractor.feed(texto)
        return extractor.texto[:MAXIMO_CARACTERES], extractor.titulo
    return texto[:MAXIMO_CARACTERES], ""


@servidor.herramienta(
    "recuperar",
    "Recupera una pagina concreta y conserva su contenido con su localizador y la "
    "fecha de consulta. Es lo que RF-101 exige conservar: un localizador puede "
    "morir, y el contenido conservado es lo que mantiene viva la trazabilidad.",
    {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Direccion de la pagina"},
        },
        "required": ["url"],
    },
)
def recuperar(argumentos: dict[str, Any]) -> dict[str, Any]:
    url = str(argumentos.get("url", "")).strip()
    if not url.startswith(("http://", "https://")):
        return {
            "ok": False,
            "codigo_error": "ERR-802",
            "mensaje": f"Localizador no recuperable: {url!r}",
            "resultados": [],
        }

    try:
        contenido, titulo = _descargar(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as fallo:
        return {
            "ok": False,
            # ERR-607: el contenido no se pudo conservar, y hay que declarar por que.
            "codigo_error": "ERR-607",
            "mensaje": f"No se pudo recuperar el contenido: {fallo}",
            "localizador": url,
            "motivo_no_conservable": str(fallo)[:300],
            "resultados": [],
        }

    resultado = Resultado(
        contenido=contenido, localizador=url, consultado_en=ahora(),
        titulo=titulo, fiabilidad="web_abierta",
    )
    validos, descartados = filtrar_validos([resultado])
    if not validos:
        return {
            "ok": False,
            "codigo_error": "ERR-607",
            "mensaje": "La pagina no devolvio contenido conservable",
            "localizador": url,
            "motivo_no_conservable": "respuesta vacia",
            "resultados": [],
            "descartados": descartados,
        }

    return {
        "ok": True,
        "resultados": validos,
        "nota": (
            "Registralo con `storymaker contexto fuente --tipo web --localizador <url> "
            "--contenido @fichero` para que quede conservado (RF-101)."
        ),
    }


@servidor.herramienta(
    "buscar",
    "Busca en la web abierta dentro del ambito de investigacion registrado. Devuelve "
    "resultados con su localizador; el contenido de cada uno se recupera despues con "
    "`recuperar`.",
    {
        "type": "object",
        "properties": {
            "consulta": {"type": "string"},
            "limite": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        },
        "required": ["consulta"],
    },
)
def buscar(argumentos: dict[str, Any]) -> dict[str, Any]:
    proveedor = os.environ.get("SM_WEB_PROVEEDOR", "").strip().lower()
    credencial = os.environ.get("SM_WEB_API_KEY", "").strip()

    if not proveedor:
        return {
            "ok": False,
            "codigo_error": "ERR-801",
            "mensaje": (
                "No hay proveedor de busqueda declarado (SM_WEB_PROVEEDOR). Degrada al "
                "corpus RAG y marca la cobertura reducida en el Contexto historico. Si "
                "tambien falla el RAG, la etapa falla con ERR-803: redactar sin "
                "contexto contradice OBJ-2."
            ),
            # La credencial se referencia por marcador, nunca por su valor.
            "credencial": "<<presente>>" if credencial else "<<ausente>>",
            "resultados": [],
        }

    if not credencial:
        return {
            "ok": False,
            "codigo_error": "ERR-205",
            "mensaje": (
                f"El proveedor '{proveedor}' esta declarado pero SM_WEB_API_KEY no. "
                "La credencial se resuelve del entorno en ejecucion y nunca se persiste."
            ),
            "resultados": [],
        }

    try:
        resultados = _buscar_en_proveedor(proveedor, credencial, argumentos)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as fallo:
        return {
            "ok": False,
            "codigo_error": "ERR-203",
            "mensaje": f"El proveedor de busqueda fallo: {fallo}",
            "reintentable": True,
            "resultados": [],
        }

    validos, descartados = filtrar_validos(resultados)
    if not validos:
        return {
            "ok": True,
            "codigo_error": "ERR-802",
            "mensaje": (
                "Sin resultados dentro del ambito. Declara laguna en lugar de rellenar "
                "con verosimilitud."
            ),
            "resultados": [],
            "descartados": descartados,
        }
    return {"ok": True, "consulta": argumentos.get("consulta"), "resultados": validos,
            "descartados": descartados}


def _buscar_en_proveedor(
    proveedor: str, credencial: str, argumentos: dict[str, Any]
) -> list[Resultado]:
    """Adaptador por proveedor.

    Anadir uno es anadir una rama aqui: lo que no cambia es el contrato de salida,
    que es lo unico que el investigador ve. De ahi que cada rama termine devolviendo
    la misma lista de `Resultado`, con su localizador y su fecha de consulta.
    """
    consulta = str(argumentos.get("consulta", ""))
    limite = int(argumentos.get("limite", 5))

    adaptador = _ADAPTADORES.get(proveedor)
    if adaptador is None:
        raise OSError(
            f"Proveedor de busqueda no implementado: {proveedor!r}. "
            f"Implementados: {', '.join(sorted(_ADAPTADORES))}."
        )
    return adaptador(credencial, consulta, limite)


def _brave(credencial: str, consulta: str, limite: int) -> list[Resultado]:
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(
        {"q": consulta, "count": limite}
    )
    peticion = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": AGENTE,
        "X-Subscription-Token": credencial,
    })
    with urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA) as respuesta:
        datos = json.loads(respuesta.read().decode("utf-8"))

    momento = ahora()
    return [
        Resultado(
            contenido=entrada.get("description", ""),
            localizador=entrada.get("url", ""),
            consultado_en=momento,
            titulo=entrada.get("title", ""),
            fiabilidad="web_abierta",
        )
        for entrada in (datos.get("web", {}) or {}).get("results", [])
    ]


def _tavily(credencial: str, consulta: str, limite: int) -> list[Resultado]:
    """Tavily devuelve el fragmento de contenido junto al enlace.

    Eso importa aqui mas que la calidad del ranking: RF-101 obliga a conservar el
    contenido en el momento de la consulta, y un proveedor que ya lo entrega ahorra
    una recuperacion por resultado. Aun asi el fragmento es corto, de modo que una
    afirmacion que dependa del texto completo sigue necesitando `recuperar`.
    """
    cuerpo = json.dumps({
        "query": consulta,
        "max_results": limite,
        "search_depth": "basic",
    }).encode("utf-8")
    peticion = urllib.request.Request(
        "https://api.tavily.com/search",
        data=cuerpo,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": AGENTE,
            # La credencial viaja en la cabecera, nunca en el cuerpo: Tavily
            # deprecio el campo `api_key` y un cuerpo se registra mas facil que
            # una cabecera.
            "Authorization": f"Bearer {credencial}",
        },
        method="POST",
    )
    with urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA) as respuesta:
        datos = json.loads(respuesta.read().decode("utf-8"))

    momento = ahora()
    return [
        Resultado(
            contenido=entrada.get("content", ""),
            localizador=entrada.get("url", ""),
            consultado_en=momento,
            titulo=entrada.get("title", ""),
            fiabilidad="web_abierta",
        )
        for entrada in (datos.get("results") or [])
    ]


_ADAPTADORES = {"brave": _brave, "tavily": _tavily}


def main() -> int:
    return servidor.ejecutar()


if __name__ == "__main__":
    raise SystemExit(main())
