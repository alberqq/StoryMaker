"""Imprime los anexos HTML de presentacion/anexos/ a PDF en presentacion/.

Uso, desde backend/ (que tiene Playwright para Python con Chromium):

    uv run python ../presentacion/anexos/imprimir.py            # todos
    uv run python ../presentacion/anexos/imprimir.py a2-tla     # uno o varios, por prefijo
    uv run python ../presentacion/anexos/imprimir.py --capturas DIR   # además, un PNG por página

Cada página es de 1280 x 720 px (16:9). Antes de imprimir se espera a que carguen las
fuentes de Google Fonts; si no hay red, se imprime con la pila de reserva y se avisa.
También se comprueba que nada se sale de la zona de contenido de su página: un aviso
de desbordamiento no detiene la impresión, pero se lista para corregirlo.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI.parent

ANEXOS: dict[str, str] = {
    "a1-arquitectura.html": "anexo-arquitectura.pdf",
    "a2-tla-spec.html": "anexo-tla-spec.pdf",
    "a3-esquema-sqlite.html": "anexo-esquema-sqlite.pdf",
    "a4-validadores.html": "anexo-validadores.pdf",
    "a5-evals-tabla.html": "anexo-evals-tabla.pdf",
    "a6-juez-vs-humano.html": "anexo-juez-vs-humano.pdf",
    "a7-red-team.html": "anexo-red-team.pdf",
    "a8-sensibilidad.html": "anexo-sensibilidad.pdf",
}

FUENTES = ("Fraunces", "Inter", "JetBrains Mono")

# Busca elementos que se salgan de su página o invadan el pie (los últimos 58 px).
COMPROBAR_DESBORDES = """
() => {
  const avisos = [];
  const paginas = Array.from(document.querySelectorAll('section.pagina'));
  paginas.forEach((pag, i) => {
    const r = pag.getBoundingClientRect();
    const limiteInferior = r.bottom - 58;
    const cuerpo = pag.querySelector('.cuerpo');
    if (cuerpo && cuerpo.scrollHeight > cuerpo.clientHeight + 1) {
      avisos.push(`página ${i + 1}: .cuerpo desborda en vertical (${cuerpo.scrollHeight} > ${cuerpo.clientHeight})`);
    }
    const h1 = pag.querySelector('.cab h1');
    if (h1 && cuerpo && h1.getBoundingClientRect().bottom > cuerpo.getBoundingClientRect().top - 2) {
      avisos.push(`página ${i + 1}: el título invade el cuerpo`);
    }
    const fuente = pag.querySelector('.pie .fuente');
    if (fuente && fuente.scrollWidth > fuente.clientWidth + 1) {
      avisos.push(`página ${i + 1}: la fuente del pie no cabe`);
    }
    pag.querySelectorAll('.cab *, .cuerpo *').forEach(el => {
      const e = el.getBoundingClientRect();
      if (e.width === 0 && e.height === 0) return;
      const fuera = e.right > r.right - 20 || e.left < r.left + 20 || e.bottom > limiteInferior || e.top < r.top + 8;
      if (fuera) {
        const txt = (el.textContent || '').trim().slice(0, 50);
        avisos.push(`página ${i + 1}: <${el.tagName.toLowerCase()}> fuera de la zona útil «${txt}»`);
      }
      if (el.tagName === 'TD' || el.tagName === 'TH' || el.tagName === 'PRE' || el.classList.contains('chip')) {
        if (el.scrollWidth > el.clientWidth + 1) {
          avisos.push(`página ${i + 1}: texto cortado en <${el.tagName.toLowerCase()}> «${(el.textContent || '').trim().slice(0, 50)}»`);
        }
      }
    });
  });
  return avisos.slice(0, 40);
}
"""


def imprimir(nombre_html: str, nombre_pdf: str, capturas: Path | None, navegador) -> None:
    ruta = AQUI / nombre_html
    pagina = navegador.new_page(viewport={"width": 1280, "height": 720})
    pagina.goto(ruta.as_uri(), wait_until="networkidle")
    pagina.evaluate("() => document.fonts.ready")
    cargadas = pagina.evaluate(
        "(fs) => fs.map(f => [f, [...document.fonts].some("
        "x => x.family.replace(/[\"']/g, '') === f && x.status === 'loaded')])",
        list(FUENTES),
    )
    faltan = [f for f, ok in cargadas if not ok]
    n = pagina.locator("section.pagina").count()
    avisos = pagina.evaluate(COMPROBAR_DESBORDES)

    pagina.emulate_media(media="print")
    destino = SALIDA / nombre_pdf
    pagina.pdf(
        path=str(destino),
        width="1280px",
        height="720px",
        print_background=True,
        margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        prefer_css_page_size=True,
    )
    print(f"{nombre_pdf}: {n} páginas")
    if faltan:
        print(f"  AVISO: sin cargar {', '.join(faltan)}; se usó la pila de reserva")
    for aviso in avisos:
        print(f"  DESBORDE {aviso}")

    if capturas is not None:
        pagina.emulate_media(media="screen")
        capturas.mkdir(parents=True, exist_ok=True)
        base = Path(nombre_pdf).stem
        for i in range(n):
            pagina.locator("section.pagina").nth(i).screenshot(
                path=str(capturas / f"{base}-{i + 1:02d}.png")
            )
    pagina.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("filtro", nargs="*", help="prefijos de los HTML a imprimir")
    parser.add_argument("--capturas", type=Path, default=None, help="carpeta para un PNG por página")
    args = parser.parse_args()

    elegidos = {
        html: pdf
        for html, pdf in ANEXOS.items()
        if not args.filtro or any(html.startswith(f) for f in args.filtro)
    }
    if not elegidos:
        print("Ningún anexo coincide con el filtro.", file=sys.stderr)
        return 1
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        for html, pdf in elegidos.items():
            imprimir(html, pdf, args.capturas, navegador)
        navegador.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
