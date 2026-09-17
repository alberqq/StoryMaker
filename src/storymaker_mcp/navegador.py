#!/usr/bin/env python3
"""Servidor MCP de inspeccion de la interfaz grafica, sobre Playwright.

Existe por un agujero concreto: **aqui no hay navegador**, y la pagina de la
interfaz es React compilado en el navegador con Babel. Nada de lo que escribimos
en `gui/index.html` se ejecuta hasta que alguien la abre, asi que un error de
JavaScript --- una cadena sin cerrar, un componente que se quedo sin definir al
recortar, una constante que se uso y nunca se declaro --- no se detecta: la
pagina sale **en negro** y no hay ni un mensaje.

Eso paso cuatro veces. `gui/comprobar_pagina.py` se escribio para taparlo y hace
lo que puede, pero es un comprobador estatico a base de expresiones regulares:
detecta las formas de romperla que ya conocemos y ninguna de las que no. Esto
abre la pagina de verdad, la recorre y dice si algo revento.

**Es una herramienta de desarrollo, no parte del arnes.** No entra en el flujo de
ninguna Ejecucion, ningun subagente lo usa, y Playwright es una dependencia de
desarrollo como `pytest`: el nucleo sigue sin ninguna en tiempo de ejecucion.

## De solo lectura, por construccion

La interfaz tiene botones que invocan al nucleo: aprobar el Canon, firmar el
Contexto, transicionar un hallazgo. Un servidor que pudiera pulsar cualquier cosa
seria una via para escribir estado saltandose la regla de que solo escribe el
nucleo tras sus puertas --- no porque el nucleo dejara de comprobar, sino porque
la decision la estaria tomando un agente en lugar del Autor.

Asi que aqui **no se pulsa nada salvo las pestanas**, y se pulsan buscandolas
dentro de `nav`, que es donde viven y donde no hay ningun boton que llame al
nucleo. No es una promesa: es que no hay ninguna herramienta que acepte otro
selector.

Instalacion:

    pip install playwright
    python -m playwright install chromium
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]
URL_POR_DEFECTO = os.environ.get("STORYMAKER_GUI_URL", "http://127.0.0.1:8765/")

# Cuanto se espera a que Babel compile y React pinte. La pagina no trae bundle:
# el navegador transforma el JSX al vuelo, y eso tarda lo suyo en arrancar.
ESPERA_PINTADO = 2500


# ==========================================================================
# El navegador
# ==========================================================================


def _sin_playwright() -> dict[str, Any]:
    return {
        "error": "Playwright no esta instalado",
        "remedio": "pip install playwright && python -m playwright install chromium",
    }


class Sesion:
    """Una pagina abierta, con lo que haya gritado por el camino.

    Los errores se recogen con escuchas y no preguntando despues, porque un error
    de JavaScript ocurre una vez y no deja rastro en el DOM: si no estabas
    escuchando cuando paso, para ti no paso.
    """

    def __init__(self, navegador: Any, url: str):
        self.errores: list[str] = []
        self.consola: list[str] = []
        self.pagina = navegador.new_page(viewport={"width": 1400, "height": 1000})
        self.pagina.on("pageerror", lambda e: self.errores.append(str(e)))
        self.pagina.on(
            "console",
            lambda m: self.consola.append(f"{m.type}: {m.text}")
            if m.type in ("error", "warning") else None,
        )
        self.pagina.goto(url, wait_until="networkidle", timeout=30000)
        self.pagina.wait_for_timeout(ESPERA_PINTADO)

    def pestanas(self) -> list[str]:
        return [b.inner_text().strip() for b in self.pagina.query_selector_all("nav button")]

    def ir_a(self, nombre: str) -> bool:
        """Pulsa una pestana. Solo dentro de `nav`: ahi no hay nada que escriba."""
        for boton in self.pagina.query_selector_all("nav button"):
            if boton.inner_text().strip().lower() == nombre.strip().lower():
                boton.click()
                self.pagina.wait_for_timeout(900)
                return True
        return False

    def texto(self, limite: int = 4000) -> str:
        try:
            return self.pagina.inner_text("body")[:limite]
        except Exception:  # noqa: BLE001
            return ""

    def en_negro(self) -> bool:
        """La pagina no pinto nada. Es el sintoma exacto que esto viene a cazar."""
        try:
            return len(self.pagina.inner_text("#raiz").strip()) < 40
        except Exception:  # noqa: BLE001
            return True

    def informe(self) -> dict[str, Any]:
        return {
            "errores_de_pagina": self.errores,
            "consola": self.consola[:20],
            "en_negro": self.en_negro(),
        }


def _con_navegador(funcion):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _sin_playwright()
    try:
        with sync_playwright() as pw:
            navegador = pw.chromium.launch()
            try:
                return funcion(navegador)
            finally:
                navegador.close()
    except Exception as fallo:  # noqa: BLE001
        return {"error": f"{type(fallo).__name__}: {fallo}"}


# ==========================================================================
# Lo que las herramientas responden
# ==========================================================================


def revisar(url: str = URL_POR_DEFECTO) -> dict[str, Any]:
    """Recorre todas las pestanas y dice cual revienta.

    Es la herramienta principal, y la que sustituye a mirar la pagina a ojo. Un
    error de JavaScript tumba el arbol de React entero: la pestana que lo provoca
    sale en negro y **las demas tambien**, asi que saber cual fue importa.
    """
    def dentro(navegador: Any) -> dict[str, Any]:
        sesion = Sesion(navegador, url)
        arranque = sesion.informe()
        if arranque["en_negro"]:
            return {
                "url": url,
                "veredicto": "LA PAGINA NO PINTA NADA",
                "arranque": arranque,
                "nota": "Con el arbol caido no tiene sentido recorrer pestanas.",
            }

        nombres = sesion.pestanas()
        por_pestana = []
        for nombre in nombres:
            antes = len(sesion.errores)
            if not sesion.ir_a(nombre):
                continue
            por_pestana.append({
                "pestana": nombre,
                "pinta": not sesion.en_negro(),
                "errores_nuevos": sesion.errores[antes:],
                "texto": sesion.texto(700),
            })

        rotas = [p["pestana"] for p in por_pestana if not p["pinta"] or p["errores_nuevos"]]
        return {
            "url": url,
            "veredicto": "sana" if not rotas and not sesion.errores else "hay problemas",
            "pestanas_con_problema": rotas,
            "errores_de_pagina": sesion.errores,
            "consola": sesion.consola[:20],
            "por_pestana": por_pestana,
        }

    return _con_navegador(dentro)


def mirar(pestana: str = "", url: str = URL_POR_DEFECTO) -> dict[str, Any]:
    """El texto que una pestana ensena de verdad, y lo que haya fallado en ella."""
    def dentro(navegador: Any) -> dict[str, Any]:
        sesion = Sesion(navegador, url)
        encontrada = sesion.ir_a(pestana) if pestana else True
        return {
            "url": url,
            "pestana": pestana or "(la que abre por defecto)",
            "encontrada": encontrada,
            "pestanas_disponibles": sesion.pestanas(),
            "texto": sesion.texto(),
            **sesion.informe(),
        }

    return _con_navegador(dentro)


def captura(pestana: str = "", url: str = URL_POR_DEFECTO, ruta: str = "") -> dict[str, Any]:
    """Una captura de pantalla en un fichero, para poder mirarla.

    Se guarda fuera del arbol de Proyectos a proposito: `proyectos/` es estado
    autoritativo y esto es una foto de desarrollo.
    """
    destino = Path(ruta) if ruta else RAIZ / "tmp" / "capturas" / (
        f"gui-{(pestana or 'inicio').lower().replace(' ', '-')}.png")

    def dentro(navegador: Any) -> dict[str, Any]:
        sesion = Sesion(navegador, url)
        encontrada = sesion.ir_a(pestana) if pestana else True
        destino.parent.mkdir(parents=True, exist_ok=True)
        sesion.pagina.screenshot(path=str(destino), full_page=True)
        return {
            "fichero": str(destino),
            "pestana": pestana or "(la que abre por defecto)",
            "encontrada": encontrada,
            **sesion.informe(),
        }

    return _con_navegador(dentro)


HERRAMIENTAS = [
    {
        "name": "gui_revisar",
        "description": (
            "Abre la interfaz en un navegador de verdad, recorre todas sus pestanas y "
            "dice cuales revientan. Usala despues de tocar `gui/index.html`: un error "
            "de JavaScript deja la pagina en negro sin ningun mensaje."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "Por defecto, la GUI local"}},
        },
    },
    {
        "name": "gui_mirar",
        "description": (
            "El texto que una pestana ensena realmente, con sus errores. Para comprobar "
            "que lo que creias haber puesto en la pantalla esta en la pantalla."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "pestana": {"type": "string", "description": "Nombre, como aparece en la barra"},
                "url": {"type": "string"},
            },
        },
    },
    {
        "name": "gui_captura",
        "description": "Guarda una captura de pantalla de una pestana en un fichero PNG.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pestana": {"type": "string"},
                "url": {"type": "string"},
                "ruta": {"type": "string", "description": "Destino del PNG"},
            },
        },
    },
]

DESPACHO = {
    "gui_revisar": lambda a: revisar(a.get("url") or URL_POR_DEFECTO),
    "gui_mirar": lambda a: mirar(a.get("pestana", ""), a.get("url") or URL_POR_DEFECTO),
    "gui_captura": lambda a: captura(
        a.get("pestana", ""), a.get("url") or URL_POR_DEFECTO, a.get("ruta", "")),
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
                "serverInfo": {"name": "sm-navegador", "version": "1.0.0"},
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
