"""Genera a5-evals-tabla.html (anexo A5) a partir de presentacion/datos/evals.json.

Uso, desde backend/:

    PYTHONIOENCODING=utf-8 uv run python ../presentacion/datos/extraer.py     # refresca evals.json
    uv run python ../presentacion/anexos/generar_a5.py                         # reescribe el HTML
    uv run python ../presentacion/anexos/imprimir.py a5                        # lo imprime a PDF

Las novelas se identifican por lugar, época y ocasión; ningún nombre de homenajeado.
"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DATOS = AQUI.parent / "datos" / "evals.json"
SALIDA = AQUI / "a5-evals-tabla.html"

ORDEN = [
    ("eval-01-jubilacion", "Cádiz, 1803–1806", "jubilación", "eval"),
    ("eval-02-hijo", "Madrid, 1787–1789", "18 cumpleaños", "eval"),
    ("eval-03-pareja", "Santiago, 1180–1188", "diez años de pareja", "eval"),
    ("eval-04-boda", "Barcelona, 1928–1929", "boda", "eval"),
    ("eval-05-aniversario", "Valencia, 1885–1886", "bodas de oro", "eval"),
    ("eval-06-injection", "Córdoba, 965–970", "adversarial · injection", "eval"),
    ("eval-07-temporal", "Cádiz, 1805–1808", "adversarial · temporal", "eval"),
    ("lozoya", "Madrid, 1856–1858", "jubilación · solo v1", "ref"),
    ("metro", "Madrid, 1917–1919", "60 cumpleaños", "ref"),
    ("pepa", "Cádiz, 1810–1812", "60 cumpleaños", "ref"),
]
ALERTAS = {
    "eval-01-jubilacion": ("aviso", "RT-08: texto de la política de privacidad colado en los capítulos 6 y 7; ningún validador lo vio. Regenerada como eval-01b: limpia, 7,38 del juez y 3,15 $; es la novela de ejemplo (ejemplos/novela-ejemplo.pdf)."),
    "eval-07-temporal": ("fallo", "RT-09: Lean no lo detecta. La fecha de muerte de Gravina del canon (1809) la inventó el arquitecto; murió en 1806."),
}
POR_CAPITULO = ["nombres_exactos", "longitud_capitulo", "guardrail_prohibidas", "anacronismo_fechado", "anclaje_valido", "cronologia_capitulo"]
CRITERIOS = ["continuidad", "arco", "coherencia_de_personajes", "ritmo", "tono", "prosa", "naturalidad_de_la_personalizacion", "autenticidad_de_epoca"]
CORTOS = {"continuidad": "contin.", "arco": "arco", "coherencia_de_personajes": "person.", "ritmo": "ritmo", "tono": "tono",
          "prosa": "prosa", "naturalidad_de_la_personalizacion": "natural.", "autenticidad_de_epoca": "época"}


def es(n: float, dec: int = 2) -> str:
    """Formato castellano con redondeo «mitad hacia arriba», como el deck (7,625 → 7,63)."""
    q = Decimal(str(n)).quantize(Decimal(1).scaleb(-dec), ROUND_HALF_UP)
    s = f"{q:,.{dec}f}"
    return s.replace(",", "·").replace(".", ",").replace("·", ".")


def miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def minutos(m: float | None) -> str:
    if m is None:
        return "—"
    m = round(m)
    return f"{m // 60} h {m % 60:02d} min" if m >= 60 else f"{m} min"


def celda_nombre(n: dict, lugar: str, ocasion: str, tipo: str) -> str:
    ref = ' <span class="sec">(ref.)</span>' if tipo == "ref" else ""
    return f'<td class="nov"><b>{lugar}</b>{ref} <span class="sec">· {ocasion}</span></td>'


def estado(n: dict) -> str:
    if n["estado"] == "terminada" and n.get("versiones"):
        return '<span class="chip pasa solo">publicada</span>'
    return '<span class="chip pend solo">en curso</span>'


def clase_fila(nombre: str, tipo: str) -> str:
    if nombre in ALERTAS and ALERTAS[nombre][0] == "fallo":
        return "fallo"
    if nombre in ALERTAS:
        return "aviso"
    return "ref" if tipo == "ref" else ""


def fila_alerta(nombre: str, columnas: int) -> str:
    if nombre not in ALERTAS:
        return ""
    tipo, texto = ALERTAS[nombre]
    return f'<tr class="alerta {tipo}"><td colspan="{columnas}">{"✕" if tipo == "fallo" else "!"} {texto}</td></tr>'


def main() -> None:
    d = json.loads(DATOS.read_text(encoding="utf-8"))
    nov = {n["nombre"]: n for n in d["novelas"]}
    extraido = d["extraido_local"]

    # ---------- Página 1: validadores por capítulo ----------
    filas1 = []
    for nombre, lugar, ocasion, tipo in ORDEN:
        n = nov[nombre]
        cap = n["capitulos"]
        celdas = []
        for v in POR_CAPITULO:
            x = (n.get("validadores_por_capitulo") or {}).get(v)
            if not x or not x.get("evaluaciones"):
                celdas.append('<td class="c sec">—</td>')
                continue
            pub = ""
            if x.get("publicados_evaluados") and x["publicados_pasan"] < x["publicados_evaluados"]:
                pub = f' <span class="rep">pub. {x["publicados_pasan"]}/{x["publicados_evaluados"]}</span>'
            falla = x["pasan"] < x["evaluaciones"]
            celdas.append(f'<td class="c"><span class="{"rep" if falla else "ok"}">{x["pasan"]}/{x["evaluaciones"]}</span>{pub}</td>')
        filas1.append(
            f'<tr class="{clase_fila(nombre, tipo)}">{celda_nombre(n, lugar, ocasion, tipo)}'
            f'<td class="num">{cap["aprobados"]}/{cap["planificados"]}</td><td class="c">{estado(n)}</td>'
            f'<td class="num">{cap["intentos_totales"]}</td>' + "".join(celdas) + "</tr>" + fila_alerta(nombre, 10))

    # ---------- Página 2: escaleta, novela e incidencias ----------
    filas2 = []
    for nombre, lugar, ocasion, tipo in ORDEN:
        n = nov[nombre]
        esc = n.get("validadores_escaleta") or {}
        nv = n.get("validadores_novela") or {}

        def ultimo(lista):
            if not lista:
                return '<span class="sec">—</span>'
            vals = [x["valor"] if isinstance(x, dict) else x for x in lista]
            seq = " · ".join("✓" if v >= 1 else "✕" for v in vals)
            return f'<span class="{"ok" if vals[-1] >= 1 else "rep"}">{seq}</span>'

        inc = n.get("incidencias_resumen") or {}
        bloq = sum(v["bloqueante"] for v in inc.values())
        avis = sum(v["aviso"] for v in inc.values())
        filas2.append(
            f'<tr class="{clase_fila(nombre, tipo)}">{celda_nombre(n, lugar, ocasion, tipo)}'
            f'<td class="c">{ultimo(esc.get("cobertura_anclada"))}</td>'
            f'<td class="c">{ultimo(esc.get("arco_anclado"))}</td>'
            f'<td class="c">{ultimo(esc.get("cronologia_escaleta"))}</td>'
            f'<td class="c">{ultimo(nv.get("cobertura_personalizacion"))}</td>'
            f'<td class="c">{ultimo(nv.get("cronologia_publicacion"))}</td>'
            f'<td class="c">{ultimo(nv.get("render_visual"))}</td>'
            f'<td class="num">{bloq}</td><td class="num">{avis}</td></tr>' + fila_alerta(nombre, 9))

    # ---------- Página 3: juez por criterio ----------
    filas3 = []
    medias = []
    for nombre, lugar, ocasion, tipo in ORDEN:
        n = nov[nombre]
        pub = [j for j in n.get("juez") or [] if j.get("version")]
        if not pub:
            filas3.append(f'<tr class="{clase_fila(nombre, tipo)}">{celda_nombre(n, lugar, ocasion, tipo)}'
                          f'<td colspan="10" class="sec">sin nota del juez todavía (en curso)</td></tr>')
            continue
        j = pub[-1]
        medias.append(j["media"])
        crit = "".join(
            f'<td class="num{" bajo" if isinstance(j["criterios"].get(c), (int, float)) and j["criterios"][c] < 6 else ""}">'
            f'{j["criterios"].get(c, "—") if j["criterios"].get(c) is not None else "—"}</td>' for c in CRITERIOS)
        filas3.append(f'<tr class="{clase_fila(nombre, tipo)}">{celda_nombre(n, lugar, ocasion, tipo)}{crit}'
                      f'<td class="num"><b>{es(j["media"])}</b></td><td class="num">{len(j.get("contradicciones") or [])}</td></tr>'
                      + fila_alerta(nombre, 11))
    media_global = sum(medias) / len(medias)

    # ---------- Página 4: coste, tokens y duración ----------
    filas4 = []
    for nombre, lugar, ocasion, tipo in ORDEN:
        n = nov[nombre]
        t = n["totales"]
        f = n.get("fases") or {}
        fase = lambda k: es(f[k]["coste_usd"]) if k in f else "—"
        curso = n["estado"] != "terminada"
        filas4.append(
            f'<tr class="{clase_fila(nombre, tipo)}">{celda_nombre(n, lugar, ocasion, tipo)}'
            f'<td class="num">{miles(t["tokens_in"])}</td><td class="num">{miles(t["tokens_out"])}</td>'
            f'<td class="num"><b>{es(t["coste_usd"])} $</b>{"*" if curso else ""}</td>'
            + "".join(f'<td class="num">{fase(k)}</td>' for k in ["intake", "investigation", "plotting", "writing", "publication"])
            + f'<td class="num">{minutos(t.get("minutos_de_trabajo"))}</td>'
            f'<td class="num">{minutos(n["duracion"].get("minutos_min_inicio_max_fin") or n["duracion"].get("minutos_hasta_ahora"))}</td></tr>')

    cab_nov = '<th>Novela · ocasión</th>'
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Anexo A5 · Resultados de las evals</title>
<link rel="stylesheet" href="marca.css">
<style>
  table.ev {{ width: 100%; border-collapse: collapse; font-size: 15px; line-height: 1.2; }}
  table.ev th {{ background: var(--tinta); color: var(--pergamino); font-weight: 600; padding: 5px 7px; text-align: center; vertical-align: bottom; font-size: 15px; }}
  table.ev th:first-child {{ text-align: left; }}
  table.ev td {{ border-bottom: 1px solid var(--tinta-12); padding: 5px 7px; vertical-align: middle; }}
  table.ev td.nov {{ white-space: nowrap; line-height: 1.15; }}
  table.ev td.nov .sec {{ font-size: 15px; }}
  table.ev td.c {{ text-align: center; white-space: nowrap; }}
  table.ev td.num {{ text-align: right; font-family: var(--mono); font-weight: 500; white-space: nowrap; }}
  table.ev td.num.bajo {{ color: var(--lacre); font-weight: 700; }}
  table.ev .ok {{ font-family: var(--mono); font-weight: 500; color: var(--salvia); }}
  table.ev .rep {{ font-family: var(--mono); font-weight: 700; color: var(--lacre); }}
  table.ev .pub {{ display: block; font-size: 15px; color: var(--piedra); font-family: var(--sans); }}
  table.ev tr.ref td {{ background: var(--tinta-06); }}
  table.ev tr.aviso td {{ background: var(--oro-18); }}
  table.ev tr.fallo td {{ background: var(--lacre-12); }}
  table.ev tr.alerta td {{ font-size: 15px; font-weight: 600; padding: 2px 10px 4px 10px; }}
  table.ev tr.alerta.aviso td {{ color: #7A5E1E; }}
  table.ev tr.alerta.fallo td {{ color: var(--lacre); }}
  table.ev .chip {{ font-size: 15px; padding: 2px 7px; }}
  .chip.solo::before {{ content: none; }}
</style>
</head>
<body data-anexo="A5">

<section class="pagina" data-fuente="<code>presentacion/datos/evals.json</code> (tabla <code>score</code>), extraído el {extraido}">
  <header class="cab">
    <div class="kicker"><span class="anexo">Anexo A5</span><span class="sep"></span>Resultados de las evals · validadores por capítulo</div>
    <h1>Todo capítulo publicado pasa los deterministas; los rechazos se repararon antes</h1>
  </header>
  <main class="cuerpo ancho">
    <table class="ev">
      <tr>{cab_nov}<th>Caps.</th><th>Estado</th><th>Intentos</th><th>nombres<br>exactos</th><th>longitud</th><th>prohibidas</th><th>anacronismo</th><th>anclaje</th><th>cronología<br>capítulo</th></tr>
      {"".join(filas1)}
    </table>
    <p class="nota" style="margin-top:6px">Cada celda: <b>pasan / evaluaciones</b> sobre todos los intentos de capítulo. En rojo, validadores que rechazaron algún intento: el capítulo volvió al escritor y se reparó. <b>Todos los capítulos de las versiones publicadas pasan los seis.</b> Las referencias de 5 capítulos no guardan score por capítulo de su versión 1: se cuentan sus incidencias en la página siguiente.</p>
  </main>
</section>

<section class="pagina" data-fuente="<code>presentacion/datos/evals.json</code> (<code>score</code> e <code>incidencia</code>), extraído el {extraido}">
  <header class="cab">
    <div class="kicker"><span class="anexo">Anexo A5</span><span class="sep"></span>Escaleta, novela e incidencias</div>
    <h1>La escaleta avisa, la novela se valida entera antes de publicar</h1>
  </header>
  <main class="cuerpo ancho">
    <table class="ev">
      <tr>{cab_nov}<th>cobertura<br>anclada</th><th>arco<br>anclado</th><th>cronología<br>escaleta</th><th>cobertura<br>personalización</th><th>cronología<br>publicación</th><th>render<br>visual</th><th>Incid.<br>bloq.</th><th>Incid.<br>avisos</th></tr>
      {"".join(filas2)}
    </table>
    <p class="nota" style="margin-top:6px">✓ pasa · ✕ falla o avisa; con varias pasadas, en orden (p. ej. la cronología de publicación de Cádiz 1803–1806 bloqueó tres veces antes de pasar). <code>arco_anclado</code> avisa en el gate de Plotting y el Autor puede aprobar con avisos; en batch no detiene. Incidencias: bloqueantes / avisos de todos los validadores, incluida la trama.</p>
  </main>
</section>

<section class="pagina" data-fuente="<code>presentacion/datos/evals.json</code> (score <code>juez_rubrica</code> de la versión publicada)">
  <header class="cab">
    <div class="kicker"><span class="anexo">Anexo A5</span><span class="sep"></span>Juez por criterio</div>
    <h1>Media del juez {es(media_global)} en {len(medias)} versiones publicadas; la continuidad es lo que más baja</h1>
  </header>
  <main class="cuerpo ancho">
    <table class="ev">
      <tr>{cab_nov}{"".join(f"<th>{CORTOS[c]}</th>" for c in CRITERIOS)}<th>Media</th><th>Contrad.</th></tr>
      {"".join(filas3)}
    </table>
    <p class="nota" style="margin-top:6px">Criterios de <code>rubrica.yaml</code>, de 1 a 10; en rojo, por debajo de 6. La continuidad la topa Python: 10 − 2 × nº de contradicciones enumeradas. <code>tono</code> no existía en la rúbrica cuando se juzgaron las referencias. Umbral de publicación: media ≥ 6,0 (en batch informa y no detiene). El adversarial temporal saca 7,63 sin ver a Gravina vivo en 1808.</p>
  </main>
</section>

<section class="pagina" data-fuente="<code>presentacion/datos/evals.json</code> (<code>fase_run</code>: <code>total_cost_usd</code> del Agent SDK por fase)">
  <header class="cab">
    <div class="kicker"><span class="anexo">Anexo A5</span><span class="sep"></span>Coste, tokens y duración</div>
    <h1>Diez capítulos cuestan de 2,31 a 3,68 $ y de 39 min a 1 h de trabajo del grafo</h1>
  </header>
  <main class="cuerpo ancho">
    <table class="ev">
      <tr>{cab_nov}<th>Tokens in</th><th>Tokens out</th><th>Coste</th><th>intake</th><th>investig.</th><th>plotting</th><th>writing</th><th>public.</th><th>Trabajo</th><th>Inicio → fin</th></tr>
      {"".join(filas4)}
    </table>
    <p class="nota" style="margin-top:6px">Coste por fase en USD. <i>Trabajo</i>: suma de las <code>fase_run</code> cerradas; <i>inicio → fin</i> incluye las esperas en los gates. Las evals corren en batch, sin gates; las referencias, con gates. Si una fase se repitió (publicación fallida y relanzada), se suman sus ejecuciones.</p>
  </main>
</section>

<script src="marca.js"></script>
</body>
</html>
"""
    SALIDA.write_text(html, encoding="utf-8")
    print(f"{SALIDA.name}: {len(ORDEN)} novelas, media del juez {media_global:.2f}")


if __name__ == "__main__":
    main()
