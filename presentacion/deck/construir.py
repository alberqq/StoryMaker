"""Construye el deck de Qapítulo para Relicario: PDF, PPTX editable y un PNG por slide.

Uso, desde backend/ (que tiene Playwright para Python con Chromium):

    uv run --with python-pptx python ../presentacion/deck/construir.py
    uv run --with python-pptx python ../presentacion/deck/construir.py --capturas DIR   # además, un PNG por slide
    uv run --with python-pptx python ../presentacion/deck/construir.py --solo-pdf

Qué hace:

1. Sirve presentacion/ por HTTP en 127.0.0.1 (un puerto libre) para que index.html pueda
   leer datos.json, y espera a que deck.js termine (window.DECK_LISTO).
2. Comprueba que nada se sale de su slide ni invade el pie; los avisos no detienen.
3. Imprime presentacion/storymaker-propuesta.pdf con Chromium.
4. Recorre el DOM ya pintado y escribe presentacion/storymaker-propuesta.pptx con python-pptx:
   cada caja CSS es una forma (rectángulo o rectángulo redondeado con su relleno y su borde),
   cada texto es un cuadro de texto editable con su fuente, tamaño, color e interlineado, cada
   imagen es una imagen, y cada SVG se inserta como imagen sin sus textos, que van encima
   como cuadros de texto. Las fuentes son las de fuentes/, las mismas del PDF.

Para que PowerPoint pinte las fuentes de marca en un equipo que no las tiene, instala las
TTF de fuentes/ o ejecuta incrustar_fuentes.ps1, que las incrusta en el PPTX.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import re
import socketserver
import sys
import threading
from pathlib import Path
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent  # presentacion/
PDF = RAIZ / "storymaker-propuesta.pdf"
PPTX = RAIZ / "storymaker-propuesta.pptx"
RASTER = AQUI / ".raster"  # imágenes intermedias de los SVG (se regeneran en cada ejecución)

PX = 9525  # EMU por píxel CSS (96 ppp): 1280 px = 13,333 pulgadas
ESPACIADO_PPTX = 1.0  # factor sobre letter-spacing (1 = el mismo que en Chromium)


# ---------------------------------------------------------------------------
# Servidor
# ---------------------------------------------------------------------------

class _Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D401
        pass


def servir() -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(_Silencioso, directory=str(RAIZ))
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


# ---------------------------------------------------------------------------
# Comprobaciones
# ---------------------------------------------------------------------------

COMPROBAR = r"""
() => {
  const avisos = [];
  document.querySelectorAll('section.slide').forEach((s, i) => {
    const R = s.getBoundingClientRect();
    const n = i + 1;
    const conPie = !!s.querySelector('.pie');
    const limite = conPie ? R.bottom - 60 : R.bottom - 20;
    const cuerpo = s.querySelector('main.cuerpo');
    if (cuerpo && cuerpo.scrollHeight > cuerpo.clientHeight + 1)
      avisos.push(`slide ${n}: .cuerpo desborda en vertical (${cuerpo.scrollHeight} > ${cuerpo.clientHeight})`);
    const h1 = s.querySelector('.cab h1');
    if (h1 && cuerpo && h1.getBoundingClientRect().bottom > cuerpo.getBoundingClientRect().top - 4)
      avisos.push(`slide ${n}: el título invade el cuerpo`);
    s.querySelectorAll('*').forEach(el => {
      if (el.closest('.pie') || el.closest('svg')) return;
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) return;
      if (r.right > R.right - 16 || r.left < R.left + 16 || r.bottom > limite || r.top < R.top + 8) {
        if (el.closest('.cubierta') && !el.classList.contains('dentro')) {
          if (r.right <= R.right && r.bottom <= R.bottom) return;
        }
        avisos.push(`slide ${n}: <${el.tagName.toLowerCase()} class="${el.className && el.className.baseVal === undefined ? el.className : ''}"> fuera de la zona útil «${(el.textContent || '').trim().slice(0, 50)}»`);
      }
      if (['TD', 'TH', 'PRE'].includes(el.tagName) || el.classList.contains('chip')) {
        if (el.scrollWidth > el.clientWidth + 1)
          avisos.push(`slide ${n}: texto cortado en <${el.tagName.toLowerCase()}> «${(el.textContent || '').trim().slice(0, 50)}»`);
      }
    });
    s.querySelectorAll('img').forEach(img => { if (!img.complete || img.naturalWidth === 0) avisos.push(`slide ${n}: imagen sin cargar ${img.getAttribute('src')}`); });
    if (s.innerText.includes('{{') || /\[[a-z_]+\.[a-z_.0-9]+\]/.test(s.innerText)) avisos.push(`slide ${n}: queda una plantilla sin resolver`);
  });
  return avisos.slice(0, 80);
}
"""

# ---------------------------------------------------------------------------
# Extracción del DOM para el PPTX
# ---------------------------------------------------------------------------

EXTRAER = r"""
(idx) => {
  const sec = document.querySelectorAll('section.slide')[idx];
  const R = sec.getBoundingClientRect();
  const items = [];
  const rgba = (c) => {
    if (!c) return null;
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(parseFloat);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const caja = (r) => ({ x: r.left - R.left, y: r.top - R.top, w: r.width, h: r.height });
  const fuente = (cs) => ({
    fam: cs.fontFamily.split(',')[0].replace(/['"]/g, '').trim(),
    peso: parseInt(cs.fontWeight, 10) || 400,
    it: cs.fontStyle === 'italic',
    px: parseFloat(cs.fontSize),
    color: rgba(cs.color),
    ls: cs.letterSpacing === 'normal' ? 0 : parseFloat(cs.letterSpacing) || 0,
    tt: cs.textTransform,
    sub: (cs.textDecorationLine || '').includes('underline'),
  });
  const lineHeight = (cs) => cs.lineHeight === 'normal' ? parseFloat(cs.fontSize) * 1.2 : parseFloat(cs.lineHeight);

  function forma(el, cs) {
    const fondo = rgba(cs.backgroundColor);
    const lados = ['Top', 'Right', 'Bottom', 'Left'].map((s, i) => ({
      lado: i, w: parseFloat(cs['border' + s + 'Width']) || 0, c: rgba(cs['border' + s + 'Color']), st: cs['border' + s + 'Style'],
    })).filter(b => b.w > 0 && b.st !== 'none' && b.st !== 'hidden' && b.c && b.c.a > 0.01);
    const hayFondo = fondo && fondo.a > 0.01;
    if (!hayFondo && !lados.length) return null;
    const r = el.getBoundingClientRect();
    if (r.width < 0.5 || r.height < 0.5) {
      if (!lados.length) return null;
    }
    const uniforme = lados.length === 4 && lados.every(b => Math.abs(b.w - lados[0].w) < 0.1 && b.st === lados[0].st &&
      b.c.r === lados[0].c.r && b.c.g === lados[0].c.g && b.c.b === lados[0].c.b);
    return {
      t: 'forma', ...caja(r), fondo: hayFondo ? fondo : null,
      radio: parseFloat(cs.borderTopLeftRadius) || 0,
      linea: uniforme ? { w: lados[0].w, c: lados[0].c, dash: lados[0].st === 'dashed' || lados[0].st === 'dotted' } : null,
      lados: uniforme ? [] : lados.map(b => ({ ...b, dash: b.st === 'dashed' || b.st === 'dotted' })),
    };
  }

  const esInline = (el, cs) => cs.display === 'inline' && !(el instanceof SVGElement) && !['IMG', 'BR'].includes(el.tagName);

  function recoger(nodo, runs, textos) {
    for (const ch of nodo.childNodes) {
      if (ch.nodeType === 3) {
        if (ch.nodeValue.length) { runs.push({ texto: ch.nodeValue, f: fuente(getComputedStyle(ch.parentElement)) }); textos.push(ch); }
      } else if (ch.nodeType === 1) {
        if (ch.tagName === 'BR') { runs.push({ br: true }); continue; }
        const c2 = getComputedStyle(ch);
        if (c2.display === 'none' || c2.visibility === 'hidden') continue;
        if (esInline(ch, c2)) recoger(ch, runs, textos);
      }
    }
  }

  function texto(el, cs) {
    const runs = [], textos = [];
    recoger(el, runs, textos);
    if (!runs.some(r => r.texto && r.texto.trim())) return null;
    const rects = [];
    textos.forEach(t => {
      if (!t.nodeValue.trim()) return;
      const rg = document.createRange(); rg.selectNodeContents(t);
      Array.from(rg.getClientRects()).forEach(q => { if (q.width > 0.2 && q.height > 0.2) rects.push(q); });
    });
    if (!rects.length) return null;
    const u = rects.reduce((a, q) => ({ l: Math.min(a.l, q.left), t: Math.min(a.t, q.top), r: Math.max(a.r, q.right), b: Math.max(a.b, q.bottom) }),
      { l: 1e9, t: 1e9, r: -1e9, b: -1e9 });
    const tops = [];
    rects.forEach(q => { if (!tops.some(t => Math.abs(t - q.top) < 4)) tops.push(q.top); });
    const r = el.getBoundingClientRect();
    const pl = parseFloat(cs.paddingLeft) + parseFloat(cs.borderLeftWidth);
    const pr = parseFloat(cs.paddingRight) + parseFloat(cs.borderRightWidth);
    let alinear = cs.textAlign;
    if (alinear === 'start' || alinear === 'justify' || alinear === '-webkit-auto') alinear = 'left';
    if (alinear === 'end') alinear = 'right';
    if (cs.display.includes('flex') && cs.justifyContent === 'center') alinear = 'center';
    const pre = cs.whiteSpace.startsWith('pre');
    return {
      t: 'texto', runs, pre, alinear, lineas: tops.length, lh: lineHeight(cs),
      u: { x: u.l - R.left, y: u.t - R.top, w: u.r - u.l, h: u.b - u.t },
      cb: { x: r.left - R.left + pl, y: r.top - R.top, w: r.width - pl - pr, h: r.height },
    };
  }

  let rid = document.querySelectorAll('[data-rid]').length;
  function svg(el) {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    const id = String(rid++);
    el.setAttribute('data-rid', id);
    const imagen = el.dataset.texto === 'imagen';
    items.push({ t: 'raster', rid: id, sintexto: !imagen, ...caja(r) });
    if (imagen) return;
    el.querySelectorAll('text').forEach(tx => {
      const b = tx.getBoundingClientRect();
      if (b.width < 0.5) return;
      const cs = getComputedStyle(tx);
      const f = fuente(cs);
      f.color = rgba(cs.fill) || f.color;
      let alinear = { start: 'left', middle: 'center', end: 'right' }[cs.textAnchor] || 'left';
      items.push({
        t: 'texto', runs: [{ texto: tx.textContent, f }], pre: false, alinear, lineas: 1, lh: b.height,
        u: { x: b.left - R.left, y: b.top - R.top, w: b.width, h: b.height }, cb: { x: b.left - R.left, y: b.top - R.top, w: b.width, h: b.height },
      });
    });
  }

  function recorrer(el) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    if (el instanceof SVGSVGElement) { svg(el); return; }
    if (el.tagName === 'IMG') {
      const r = el.getBoundingClientRect();
      items.push({ t: 'img', src: el.currentSrc || el.src, nw: el.naturalWidth, nh: el.naturalHeight, fit: cs.objectFit, pos: cs.objectPosition, ...caja(r) });
      return;
    }
    if (el !== sec) {
      if (esInline(el, cs)) {
        const fondo = rgba(cs.backgroundColor);
        if (fondo && fondo.a > 0.01) Array.from(el.getClientRects()).forEach(q => items.push({ t: 'forma', ...caja(q), fondo, radio: 0, linea: null, lados: [] }));
      } else {
        const f = forma(el, cs); if (f) items.push(f);
        const tx = texto(el, cs); if (tx) items.push(tx);
      }
    }
    for (const ch of el.children) recorrer(ch);
  }
  recorrer(sec);
  return { fondo: rgba(getComputedStyle(sec).backgroundColor), notas: sec.dataset.notas || '', items };
}
"""

CSS_RASTER = """
html.rasterizando, html.rasterizando body { background: transparent !important; }
html.rasterizando * { visibility: hidden !important; }
html.rasterizando .rtarget, html.rasterizando .rtarget * { visibility: visible !important; }
html.rasterizando .rtarget.sintexto text { visibility: hidden !important; }
"""


# ---------------------------------------------------------------------------
# PPTX
# ---------------------------------------------------------------------------

def tipografia(fam: str, peso: int, it: bool) -> tuple[str, bool, bool]:
    """(typeface de PowerPoint, negrita, cursiva) para cada fuente del deck."""
    if "Fraunces" in fam or fam in ("Georgia", "serif"):
        if peso >= 600:
            return "Fraunces SemiBold", False, it
        if peso == 500:
            return "Fraunces Medium", False, it
        return "Fraunces", False, it
    if "Mono" in fam or fam in ("Consolas", "monospace"):
        if peso >= 600:
            return "JetBrains Mono", True, False
        if peso == 500:
            return "JetBrains Mono Medium", False, False
        return "JetBrains Mono", False, False
    if peso >= 700:
        return "Inter", True, False
    if peso >= 600:
        return "Inter SemiBold", False, False
    if peso == 500:
        return "Inter Medium", False, False
    return "Inter", False, False


GUION = RAIZ / "guion.md"


def notas_del_guion() -> dict[int, str]:
    """Las notas del orador salen de presentacion/guion.md, para que guion y deck no diverjan.

    Toma de cada «### Slide N · …» su bloque «Qué decir» (las líneas «> ») y las notas en
    negrita que le siguen («Gesto», «Si vas justo», «Y en directo»), sin las marcas de Markdown.
    """
    if not GUION.exists():
        return {}
    notas: dict[int, str] = {}
    actual: int | None = None
    lineas: list[str] = []

    def cerrar() -> None:
        if actual is not None:
            notas[actual] = "\n\n".join(x for x in lineas if x)

    for linea in GUION.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^### Slide (\d+)\b", linea)
        if m or linea.startswith("## "):
            cerrar()
            actual, lineas = (int(m.group(1)), []) if m else (None, [])
            continue
        if actual is None or linea.startswith("**Qué decir"):
            continue
        texto = linea[2:] if linea.startswith("> ") else linea
        texto = re.sub(r"\*\*|`", "", texto).strip()
        if texto and texto != "---":
            lineas.append(texto)
    cerrar()
    return notas


def construir_pptx(slides: list[dict], rasters: dict[str, Path]) -> None:
    from lxml import etree
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.dml import MSO_LINE_DASH_STYLE
    from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
    from pptx.oxml.ns import qn
    from pptx.util import Emu, Pt

    prs = Presentation()
    prs.slide_width = Emu(1280 * PX)
    prs.slide_height = Emu(720 * PX)
    vacio = prs.slide_layouts[6]

    def E(v: float) -> Emu:
        return Emu(int(round(v * PX)))

    def rgb(c) -> RGBColor:
        return RGBColor(int(c["r"]), int(c["g"]), int(c["b"]))

    def alfa(elemento_color, a: float) -> None:
        """Añade <a:alpha> al srgbClr recién escrito si el color es translúcido."""
        if a >= 0.995:
            return
        clr = elemento_color._xFill if hasattr(elemento_color, "_xFill") else None
        return clr

    def poner_alfa(xml_padre, a: float) -> None:
        if a >= 0.995:
            return
        for srgb in xml_padre.iter(qn("a:srgbClr")):
            for viejo in srgb.findall(qn("a:alpha")):
                srgb.remove(viejo)
            al = etree.SubElement(srgb, qn("a:alpha"))
            al.set("val", str(int(round(a * 100000))))

    def sin_estilo(shape) -> None:
        st = shape._element.find(qn("p:style"))
        if st is not None:
            shape._element.remove(st)

    def local(url: str) -> Path:
        ruta = unquote(urlparse(url).path).lstrip("/")
        return RAIZ / ruta

    guion = notas_del_guion()
    for numero, s in enumerate(slides, 1):
        sl = prs.slides.add_slide(vacio)
        if s["fondo"]:
            sl.background.fill.solid()
            sl.background.fill.fore_color.rgb = rgb(s["fondo"])
        for it in s["items"]:
            t = it["t"]
            if t == "forma":
                redondo = it["radio"] > 0.5 and min(it["w"], it["h"]) > 2
                sh = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if redondo else MSO_SHAPE.RECTANGLE,
                                         E(it["x"]), E(it["y"]), E(max(it["w"], 0.5)), E(max(it["h"], 0.5)))
                sin_estilo(sh)
                if redondo:
                    sh.adjustments[0] = min(0.5, it["radio"] / min(it["w"], it["h"]))
                if it["fondo"]:
                    sh.fill.solid()
                    sh.fill.fore_color.rgb = rgb(it["fondo"])
                    poner_alfa(sh._element.spPr.find(qn("a:solidFill")), it["fondo"]["a"])
                else:
                    sh.fill.background()
                if it["linea"]:
                    ln = it["linea"]
                    sh.line.width = Pt(ln["w"] * 0.75)
                    sh.line.color.rgb = rgb(ln["c"])
                    if ln["dash"]:
                        sh.line.dash_style = MSO_LINE_DASH_STYLE.DASH
                else:
                    sh.line.fill.background()
                sh.text_frame.text = ""
                for b in it["lados"]:
                    x, y, w, h, bw = it["x"], it["y"], it["w"], it["h"], b["w"]
                    if b["lado"] == 0:
                        p1, p2 = (x, y + bw / 2), (x + w, y + bw / 2)
                    elif b["lado"] == 1:
                        p1, p2 = (x + w - bw / 2, y), (x + w - bw / 2, y + h)
                    elif b["lado"] == 2:
                        p1, p2 = (x, y + h - bw / 2), (x + w, y + h - bw / 2)
                    else:
                        p1, p2 = (x + bw / 2, y), (x + bw / 2, y + h)
                    cn = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(p1[0]), E(p1[1]), E(p2[0]), E(p2[1]))
                    sin_estilo(cn)
                    cn.line.width = Pt(bw * 0.75)
                    cn.line.color.rgb = rgb(b["c"])
                    if b["dash"]:
                        cn.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            elif t == "img":
                ruta = local(it["src"])
                x, y, w, h = it["x"], it["y"], it["w"], it["h"]
                nw, nh = it["nw"] or 1, it["nh"] or 1
                cl = cr = ct = cb = 0.0
                if it["fit"] in ("cover", "contain"):
                    esc = (max if it["fit"] == "cover" else min)(w / nw, h / nh)
                    dw, dh = nw * esc, nh * esc
                    pos = [v for v in it["pos"].split()] + ["50%"]
                    fx = float(pos[0].rstrip("%")) / 100 if pos[0].endswith("%") else 0.5
                    fy = float(pos[1].rstrip("%")) / 100 if pos[1].endswith("%") else 0.5
                    if it["fit"] == "cover":
                        ex, ey = (dw - w) / dw, (dh - h) / dh
                        cl, cr = ex * fx, ex * (1 - fx)
                        ct, cb = ey * fy, ey * (1 - fy)
                    else:
                        x += (w - dw) * fx
                        y += (h - dh) * fy
                        w, h = dw, dh
                pic = sl.shapes.add_picture(str(ruta), E(x), E(y), E(w), E(h))
                pic.crop_left, pic.crop_right, pic.crop_top, pic.crop_bottom = cl, cr, ct, cb
            elif t == "raster":
                ruta = rasters.get(it["rid"])
                if ruta and ruta.exists():
                    sl.shapes.add_picture(str(ruta), E(it["x"]), E(it["y"]), E(it["w"]), E(it["h"]))
            elif t == "texto":
                escribir_texto(sl, it, E, rgb, poner_alfa, Pt, PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE, qn, etree)
        nota = guion.get(numero, s["notas"])
        if nota:
            sl.notes_slide.notes_text_frame.text = nota
    prs.core_properties.title = "Novela Relicario · Qapítulo"
    prs.core_properties.author = "Qapítulo"
    prs.save(str(PPTX))


def escribir_texto(sl, it, E, rgb, poner_alfa, Pt, PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE, qn, etree) -> None:
    # Párrafos a partir de los runs: <br> y, en <pre>, los saltos de línea.
    parrafos: list[list[dict]] = [[]]
    for r in it["runs"]:
        if r.get("br"):
            parrafos.append([])
            continue
        txt = r["texto"]
        if it["pre"]:
            trozos = txt.split("\n")
            for i, tr in enumerate(trozos):
                if i:
                    parrafos.append([])
                if tr:
                    parrafos[-1].append({"texto": tr, "f": r["f"]})
        else:
            txt = re.sub(r"[ \t\r\n]+", " ", txt)
            parrafos[-1].append({"texto": txt, "f": r["f"]})
    if it["pre"]:
        while parrafos and not parrafos[0]:
            parrafos.pop(0)
        while parrafos and not parrafos[-1]:
            parrafos.pop()
    else:
        for p in parrafos:
            # colapsa espacios entre runs y recorta los extremos del párrafo
            prev_esp = True
            for r in p:
                if prev_esp:
                    r["texto"] = r["texto"].lstrip(" ")
                if r["texto"]:
                    prev_esp = r["texto"].endswith(" ")
            for r in reversed(p):
                r["texto"] = r["texto"].rstrip(" ")
                if r["texto"]:
                    break
            p[:] = [r for r in p if r["texto"]]
        parrafos = [p for p in parrafos if p] or [[]]
    if not any(parrafos):
        return

    u, cb = it["u"], it["cb"]
    una = it["lineas"] <= 1 or it["pre"]
    alinear = it["alinear"]
    if una:
        w = max(u["w"], 1) * 1.04 + 4
        if alinear == "center":
            x = u["x"] + u["w"] / 2 - w / 2
        elif alinear == "right":
            x = u["x"] + u["w"] - w
        else:
            x = u["x"]
    else:
        w = cb["w"] * 1.006 + 1
        x = cb["x"] - (cb["w"] * 0.003 + 0.5 if alinear == "center" else (cb["w"] * 0.006 + 1 if alinear == "right" else 0))
    y, h = u["y"], max(u["h"], 4)
    tb = sl.shapes.add_textbox(E(x), E(y), E(w), E(h))
    tf = tb.text_frame
    tf.word_wrap = not una
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.TOP
    al = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}.get(alinear, PP_ALIGN.LEFT)
    for i, p in enumerate(parrafos):
        par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        par.alignment = al
        par.line_spacing = Pt(it["lh"] * 0.75)
        par.space_before = Pt(0)
        par.space_after = Pt(0)
        for r in p:
            f = r["f"]
            txt = r["texto"].upper() if f["tt"] == "uppercase" else r["texto"]
            run = par.add_run()
            run.text = txt
            nombre, negrita, cursiva = tipografia(f["fam"], f["peso"], f["it"])
            run.font.name = nombre
            run.font.size = Pt(round(f["px"] * 0.75 * 2) / 2)
            run.font.bold = negrita
            run.font.italic = cursiva
            if f["sub"]:
                run.font.underline = True
            if f["color"]:
                run.font.color.rgb = rgb(f["color"])
                poner_alfa(run._r.find(qn("a:rPr")), f["color"]["a"])
            rpr = run._r.get_or_add_rPr()
            if f["ls"]:
                rpr.set("spc", str(int(round(f["ls"] * 0.75 * 100 * ESPACIADO_PPTX))))
            for etiqueta in ("a:ea", "a:cs"):
                if rpr.find(qn(etiqueta)) is None:
                    el = etree.SubElement(rpr, qn(etiqueta))
                    el.set("typeface", nombre)
            # el orden del esquema: latin, ea, cs deben ir tras los rellenos
            latin = rpr.find(qn("a:latin"))
            if latin is not None:
                rpr.remove(latin)
                ea = rpr.find(qn("a:ea"))
                ea.addprevious(latin)


# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--capturas", type=Path, default=None, help="carpeta para un PNG por slide")
    parser.add_argument("--solo-pdf", action="store_true", help="no genera el PPTX")
    args = parser.parse_args()

    srv, puerto = servir()
    url = f"http://127.0.0.1:{puerto}/deck/index.html"
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pag = nav.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
        errores: list[str] = []
        pag.on("console", lambda m: errores.append(m.text) if m.type in ("error", "warning") else None)
        pag.on("pageerror", lambda e: errores.append(str(e)))
        pag.goto(url, wait_until="networkidle")
        pag.wait_for_function("window.DECK_LISTO === true", timeout=30000)
        pag.evaluate("() => document.fonts.ready")
        faltan = pag.evaluate(
            "() => ['QFraunces','QInter','QMono'].filter(f => ![...document.fonts].some(x => x.family.replace(/[\"']/g,'') === f && x.status === 'loaded'))")
        n = pag.locator("section.slide").count()
        avisos = pag.evaluate(COMPROBAR)
        for e in errores:
            print("  CONSOLA", e)
        if faltan:
            print("  AVISO: fuentes sin cargar:", ", ".join(faltan))
        for a in avisos:
            print("  DESBORDE", a)

        if args.capturas:
            args.capturas.mkdir(parents=True, exist_ok=True)
            for i in range(n):
                pag.locator("section.slide").nth(i).screenshot(path=str(args.capturas / f"slide-{i + 1:02d}.png"))

        pag.emulate_media(media="print")
        pag.pdf(path=str(PDF), width="1280px", height="720px", print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}, prefer_css_page_size=True)
        pag.emulate_media(media="screen")
        print(f"{PDF.name}: {n} slides")

        if not args.solo_pdf:
            slides = [pag.evaluate(EXTRAER, i) for i in range(n)]
            RASTER.mkdir(exist_ok=True)
            for viejo in RASTER.glob("*.png"):
                viejo.unlink()
            pag.add_style_tag(content=CSS_RASTER)
            rasters: dict[str, Path] = {}
            for s in slides:
                for it in s["items"]:
                    if it["t"] != "raster":
                        continue
                    rid = it["rid"]
                    pag.evaluate(
                        "([rid, st]) => { document.documentElement.classList.add('rasterizando');"
                        " document.querySelectorAll('.rtarget').forEach(e => e.classList.remove('rtarget','sintexto'));"
                        " const el = document.querySelector(`[data-rid=\"${rid}\"]`); el.classList.add('rtarget'); if (st) el.classList.add('sintexto'); }",
                        [rid, it["sintexto"]])
                    destino = RASTER / f"r{int(rid):03d}.png"
                    pag.locator(f'[data-rid="{rid}"]').screenshot(path=str(destino), omit_background=True)
                    rasters[rid] = destino
            construir_pptx(slides, rasters)
            total = sum(1 for s in slides for it in s["items"] if it["t"] == "texto")
            print(f"{PPTX.name}: {n} slides, {total} cuadros de texto editables, {len(rasters)} SVG como imagen")
        nav.close()
    srv.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
