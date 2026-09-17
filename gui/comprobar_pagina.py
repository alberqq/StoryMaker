#!/usr/bin/env python3
"""Comprobacion de cordura del JavaScript de `index.html`.

Existe por una razon concreta: aqui no hay Node ni navegador, asi que nadie
ejecuta la pagina antes de publicarla. Un solo error de sintaxis la deja en blanco
--- no a medias, en blanco --- y desde fuera es indistinguible de un servidor
caido. Esto no sustituye a un compilador: caza la clase de fallo que de verdad ha
ocurrido, que es una cadena cortada por un salto de linea al generar el fichero
desde un script.

Se ejecuta con `python gui/comprobar_pagina.py` y devuelve 0 si no ve nada raro.
"""

from __future__ import annotations

import sys
from pathlib import Path

PAGINA = Path(__file__).resolve().parent / "index.html"
APERTURA = '<script type="text/babel" data-presets="react">'
CIERRE = "</script>"

PAREJAS = {")": "(", "]": "[", "}": "{"}


def extraer(html: str) -> str:
    if APERTURA not in html:
        raise SystemExit("La pagina no lleva el bloque de Babel esperado")
    return html.split(APERTURA, 1)[1].split(CIERRE, 1)[0]


def revisar(js: str) -> list[str]:
    """Recorre el codigo distinguiendo cadenas, plantillas y comentarios."""
    fallos: list[str] = []
    pila: list[tuple[str, int]] = []
    linea = 1
    i = 0
    n = len(js)

    while i < n:
        c = js[i]

        if c == "\n":
            linea += 1
            i += 1
            continue

        # Comentarios
        if c == "/" and i + 1 < n and js[i + 1] == "/":
            while i < n and js[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and js[i + 1] == "*":
            i += 2
            while i + 1 < n and not (js[i] == "*" and js[i + 1] == "/"):
                if js[i] == "\n":
                    linea += 1
                i += 1
            i += 2
            continue

        # Cadenas de comillas simples o dobles: un salto de linea sin escapar las
        # rompe, y es exactamente el fallo que esto busca.
        if c in "\"'":
            comilla = c
            inicio = linea
            i += 1
            cerrada = False
            while i < n:
                if js[i] == "\\":
                    i += 2
                    continue
                if js[i] == "\n":
                    fallos.append(
                        f"linea {inicio}: cadena {comilla}...{comilla} cortada por un "
                        "salto de linea sin escapar"
                    )
                    linea += 1
                    break
                if js[i] == comilla:
                    cerrada = True
                    i += 1
                    break
                i += 1
            if not cerrada and i >= n:
                fallos.append(f"linea {inicio}: cadena sin cerrar al final del fichero")
            continue

        # Plantillas: ahi el salto de linea si es legitimo.
        if c == "`":
            i += 1
            while i < n:
                if js[i] == "\\":
                    i += 2
                    continue
                if js[i] == "\n":
                    linea += 1
                if js[i] == "`":
                    i += 1
                    break
                i += 1
            continue

        if c in "([{":
            pila.append((c, linea))
        elif c in ")]}":
            if not pila:
                fallos.append(f"linea {linea}: '{c}' sin su pareja")
            elif pila[-1][0] != PAREJAS[c]:
                abierto, donde = pila[-1]
                fallos.append(
                    f"linea {linea}: '{c}' cierra un '{abierto}' abierto en la linea {donde}"
                )
                pila.pop()
            else:
                pila.pop()
        i += 1

    for abierto, donde in pila:
        fallos.append(f"linea {donde}: '{abierto}' se queda sin cerrar")

    return fallos


def componentes_sin_definir(js: str) -> list[str]:
    """Componentes que la pagina usa y nadie define.

    La sintaxis puede estar impecable y la pagina salir en blanco igual: basta
    con que un `<Componente/>` no exista para que React tire toda la raiz. Paso
    justo eso al recortar una pestana y llevarme por delante otro componente que
    estaba a su lado.
    """
    import re

    definidos = set(re.findall(r"^(?:function|const)\s+([A-Z][A-Za-z_0-9]*)", js, re.M))
    # Una variable que decide que componente pintar no es un literal JSX.
    definidos.update(re.findall(r"const\s+([A-Z][A-Za-z_0-9]*)\s*=", js))
    usados = set(re.findall(r"<([A-Z][A-Za-z_0-9]*)", js))
    return sorted(usados - definidos)


def regex_cortadas(js: str) -> list[str]:
    """Expresiones regulares partidas por un salto de linea.

    Una expresion regular literal no puede abarcar dos lineas, igual que una
    cadena. Lo detecta aparte porque `revisar` solo entiende de comillas, y esto
    ya ha roto la pagina una vez: un `\n` mal escapado al generar el fichero se
    convirtio en salto de verdad dentro de un `split(/.../)`.
    """
    import re

    fallos = []
    for numero, linea in enumerate(js.splitlines(), 1):
        for metodo in ("split", "replace", "match", "test", "search"):
            marca = metodo + "(/"
            desde = linea.find(marca)
            if desde == -1:
                continue
            resto = linea[desde + len(marca):]
            if "/" not in resto:
                fallos.append(
                    f"linea {numero}: la expresion regular de `{metodo}(` no se cierra "
                    "en su linea; un salto dentro de una regex la rompe"
                )
    return fallos


def _sin_textos(js: str) -> str:
    """El codigo con el contenido de las cadenas vaciado.

    Sirve para no confundir un color hexadecimal escrito dentro de una cadena con
    una constante que alguien olvido declarar.
    """
    fuera = []
    i, n = 0, len(js)
    while i < n:
        c = js[i]
        if c in "\"'`":
            comilla = c
            i += 1
            while i < n and js[i] != comilla:
                i += 2 if js[i] == "\\" else 1
            i += 1
            fuera.append('""')
            continue
        fuera.append(c)
        i += 1
    return "".join(fuera)


def constantes_sin_definir(js: str) -> list[str]:
    """Constantes en mayusculas que se usan y nadie declara.

    Es lo que dejo la pagina en negro: un recorte se llevo `PARAMETROS_ESTILO` y
    el componente que la usaba reventaba al pintarse, tirando la raiz de React
    entera. La sintaxis estaba impecable, que es justo lo que hace falta detectar
    aparte.
    """
    import re

    codigo = _sin_textos(js)
    declaradas = set(re.findall(r"\b(?:const|let|var|function)\s+([A-Z][A-Z_0-9]{2,})\b", codigo))
    usadas = set(re.findall(r"\b([A-Z][A-Z_0-9]{2,})\b", codigo))
    conocidas = {"JSON", "URL", "POST", "GET", "DOCTYPE", "NaN"}
    return sorted(usadas - declaradas - conocidas)


def main() -> int:
    js = extraer(PAGINA.read_text(encoding="utf-8"))
    fallos = revisar(js)
    fallos += [
        f"el componente <{nombre}> se usa y no esta definido"
        for nombre in componentes_sin_definir(js)
    ]
    fallos += regex_cortadas(js)
    fallos += [
        f"la constante {nombre} se usa y no esta declarada"
        for nombre in constantes_sin_definir(js)
    ]
    if fallos:
        print(f"{len(fallos)} problema(s) en el JavaScript de la pagina:")
        for fallo in fallos:
            print(f"  - {fallo}")
        return 1
    print(f"La pagina parece sana: {len(js.splitlines())} lineas de JavaScript revisadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
