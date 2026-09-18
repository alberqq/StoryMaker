#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HOJ-002 - Conversion Markdown -> PDF.

Herramienta de hoja del arnes StoryMaker. Es, junto a la busqueda web, el UNICO
sitio del sistema donde hay codigo (RES-11, E66, ADR-016).

  TRANSFORMA. NO DECIDE.

No filtra, no prioriza, no reordena y no rechaza. Si empezara a hacer cualquiera
de esas cosas dejaria de ser una herramienta de hoja y volveria a estar prohibida
(RF-059, caso limite; RNF-027). Su unico cometido es que el PDF tenga el mismo
contenido que el Markdown (RNF-024).

Uso:
    python arnes/herramientas/md-a-pdf.py <entrada.md> <salida.pdf>

Salida: escribe el PDF y emite en stdout una linea JSON con el resultado, para
que el Orquestador la registre en la bitacora sin tener que interpretar prosa.

Codigos de salida:
    0  conversion realizada
    1  fallo -> el Orquestador registra ERR-405 y considera COMPLETA la entrega
       en Markdown, porque el manuscrito ya esta terminado (RF-053, caso limite).
"""

import json
import os
import re
import sys

ANCHO_PAGINA = 210.0   # A4 en mm
MARGEN = 25.0
INTERLINEA = 6.2

# Fuentes Unicode habituales en Windows, por orden de preferencia. Hace falta una
# TTF porque las fuentes nucleo de PDF son Latin-1 y no cubren la raya (—), los
# puntos suspensivos (…) ni las comillas tipograficas que usa el manuscrito.
CANDIDATAS = [
    ("Georgia",  r"C:\Windows\Fonts\georgia.ttf",  r"C:\Windows\Fonts\georgiab.ttf",  r"C:\Windows\Fonts\georgiai.ttf"),
    ("DejaVu",   r"C:\Windows\Fonts\DejaVuSerif.ttf", r"C:\Windows\Fonts\DejaVuSerif-Bold.ttf", None),
    ("Calibri",  r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\calibrib.ttf", r"C:\Windows\Fonts\calibrii.ttf"),
    ("Arial",    r"C:\Windows\Fonts\arial.ttf",   r"C:\Windows\Fonts\arialbd.ttf",   r"C:\Windows\Fonts\ariali.ttf"),
]


def elegir_fuente():
    for nombre, regular, negrita, cursiva in CANDIDATAS:
        if os.path.exists(regular):
            return nombre, regular, (negrita if negrita and os.path.exists(negrita) else None), \
                   (cursiva if cursiva and os.path.exists(cursiva) else None)
    return None, None, None, None


def limpiar_enfasis(t):
    """Retira las marcas de enfasis de Markdown SIN alterar el texto que envuelven."""
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"\*(.+?)\*", r"\1", t)
    t = re.sub(r"_(.+?)_", r"\1", t)
    t = re.sub(r"`(.+?)`", r"\1", t)
    return t


def trocear(texto):
    """Markdown -> lista de bloques (tipo, texto). Conserva el orden tal cual."""
    bloques = []
    for linea in texto.replace("\r\n", "\n").split("\n"):
        s = linea.strip()
        if not s:
            continue
        if s.startswith("### "):
            bloques.append(("h3", limpiar_enfasis(s[4:].strip())))
        elif s.startswith("## "):
            bloques.append(("h2", limpiar_enfasis(s[3:].strip())))
        elif s.startswith("# "):
            bloques.append(("h1", limpiar_enfasis(s[2:].strip())))
        elif s in ("---", "***", "___"):
            bloques.append(("regla", ""))
        else:
            bloques.append(("p", limpiar_enfasis(s)))
    return bloques


def convertir(ruta_md, ruta_pdf):
    from fpdf import FPDF

    with open(ruta_md, encoding="utf-8") as f:
        bloques = trocear(f.read())

    nombre, regular, negrita, cursiva = elegir_fuente()
    if not nombre:
        raise RuntimeError("No hay ninguna fuente TrueType disponible para incrustar")

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=MARGEN)
    pdf.set_margins(MARGEN, MARGEN, MARGEN)
    pdf.add_font(nombre, "", regular)
    if negrita:
        pdf.add_font(nombre, "B", negrita)
    if cursiva:
        pdf.add_font(nombre, "I", cursiva)
    est_negrita = "B" if negrita else ""

    util = ANCHO_PAGINA - 2 * MARGEN
    pdf.add_page()
    primero = True

    for tipo, texto in bloques:
        if tipo == "h1":
            pdf.set_font(nombre, est_negrita, 22)
            pdf.ln(18 if primero else 10)
            pdf.multi_cell(util, 10, texto, align="C")
            pdf.ln(10)
        elif tipo == "h2":
            if not primero:
                pdf.add_page()          # un capitulo por pagina
            pdf.set_font(nombre, est_negrita, 15)
            pdf.ln(6)
            pdf.multi_cell(util, 8, texto, align="L")
            pdf.ln(4)
        elif tipo == "h3":
            pdf.set_font(nombre, est_negrita, 12)
            pdf.ln(3)
            pdf.multi_cell(util, 7, texto, align="L")
            pdf.ln(2)
        elif tipo == "regla":
            pdf.ln(4)
        else:
            pdf.set_font(nombre, "", 11.5)
            pdf.multi_cell(util, INTERLINEA, texto, align="J")
            pdf.ln(3)
        primero = False

    destino = os.path.dirname(os.path.abspath(ruta_pdf))
    if destino and not os.path.isdir(destino):
        os.makedirs(destino)
    pdf.output(ruta_pdf)

    return {
        "herramienta": "HOJ-002",
        "resultado": "convertido",
        "entrada": ruta_md,
        "salida": ruta_pdf,
        "bloques": len(bloques),
        "parrafos": sum(1 for t, _ in bloques if t == "p"),
        "encabezados": sum(1 for t, _ in bloques if t.startswith("h")),
        "paginas": pdf.pages_count,
        "fuente": nombre,
        "bytes": os.path.getsize(ruta_pdf),
    }


def main():
    if len(sys.argv) != 3:
        print(json.dumps({"herramienta": "HOJ-002", "resultado": "error",
                          "codigo": "ERR-405",
                          "mensaje": "Uso: md-a-pdf.py <entrada.md> <salida.pdf>"},
                         ensure_ascii=False))
        return 1
    entrada, salida = sys.argv[1], sys.argv[2]
    if not os.path.exists(entrada):
        print(json.dumps({"herramienta": "HOJ-002", "resultado": "error",
                          "codigo": "ERR-405",
                          "mensaje": "No existe el fichero de entrada: %s" % entrada},
                         ensure_ascii=False))
        return 1
    try:
        print(json.dumps(convertir(entrada, salida), ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps({"herramienta": "HOJ-002", "resultado": "error",
                          "codigo": "ERR-405",
                          "mensaje": "%s: %s" % (type(e).__name__, e)},
                         ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
