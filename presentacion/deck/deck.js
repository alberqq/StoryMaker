// Deck de Qapítulo para Relicario.
//
// Lee datos.json y rellena la maqueta: sustituye cada {{ruta|formato}} de los textos y de
// los atributos src, pinta las tablas y gráficos que llevan data-render y añade el pie de
// cada slide (línea de tiempo de Oro viejo, logo y «03 / 22»). Al terminar deja
// window.DECK_LISTO = true, que es lo que espera construir.py antes de imprimir.
//
// Formatos: |0 entero con punto de miles, |1 y |2 decimales con coma. Sin formato, el valor
// se escribe tal cual.

(function () {
  'use strict';

  // ---------- Formato numérico en castellano ----------
  function fmt(n, dec) {
    if (typeof n !== 'number') return String(n);
    const s = Math.abs(n).toFixed(dec);
    let [ent, frac] = s.split('.');
    if (ent.length > 3) ent = ent.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return (n < 0 ? '−' : '') + ent + (frac ? ',' + frac : '');
  }
  function valor(datos, ruta) {
    return ruta.split('.').reduce((o, k) => (o == null ? undefined : o[k]), datos);
  }
  function plantilla(datos, texto) {
    return texto.replace(/\{\{\s*([\w.]+)\s*(?:\|\s*(\d))?\s*\}\}/g, (m, ruta, f) => {
      const v = valor(datos, ruta);
      if (v === undefined) { console.warn('dato ausente', ruta); return '[' + ruta + ']'; }
      return f !== undefined ? fmt(v, Number(f)) : String(v);
    });
  }
  function aplicarPlantillas(datos) {
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodos = [];
    let n;
    while ((n = w.nextNode())) if (n.nodeValue.includes('{{')) nodos.push(n);
    nodos.forEach(t => { t.nodeValue = plantilla(datos, t.nodeValue); });
    document.querySelectorAll('[data-notas*="{{"]').forEach(el => {
      el.setAttribute('data-notas', plantilla(datos, el.getAttribute('data-notas')));
    });
    document.querySelectorAll('[src*="{{"], [data-src]').forEach(el => {
      const src = el.getAttribute('data-src') || el.getAttribute('src');
      el.setAttribute('src', plantilla(datos, src));
    });
  }

  // ---------- Piezas ----------
  const e = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  function chip(v) {
    if (v === undefined || v === null) return '';
    if (v === 'falla') return '<span class="chip falla">✕ no lo ve</span>';
    if (v === 'pasa') return '<span class="chip pasa"><span class="g">✓</span></span>';
    if (v === 'pend') return '<span class="chip pend">en curso</span>';
    const partes = String(v).split('+').map(p => {
      const [tipo, n] = p.split(':');
      if (tipo === 'rep') return '<span class="chip rep">✕→<span class="ok">✓</span>' + (n > 1 ? ' ×' + n : '') + '</span>';
      if (tipo === 'falla') return '<span class="chip falla">✕ no lo ve</span>';
      if (tipo === 'aviso') return '<span class="chip aviso">!' + (n > 1 ? ' ×' + n : '') + '</span>';
      return '<span class="chip neutro">' + e(p) + '</span>';
    });
    return partes.join(' ');
  }

  const LOGO_Q = (bowl, cinta) =>
    '<svg viewBox="0 0 40 44" data-texto="imagen" aria-hidden="true">' +
    '<path fill="' + bowl + '" fill-rule="evenodd" d="M19 2 A15 16 0 1 1 18.99 2 Z M19 5.4 A10.2 12.6 0 1 0 19.01 5.4 Z" transform="rotate(-8 19 18)"/>' +
    '<path fill="' + cinta + '" d="M20.6 26.2 L27.4 24.6 L33.6 42.4 L29.6 38.9 L27 43.6 Z"/>' +
    '</svg>';
  const LOGO_R = (color) =>
    '<svg viewBox="0 0 40 52" data-texto="imagen" aria-hidden="true">' +
    '<circle cx="20" cy="5" r="3.2" fill="none" stroke="' + color + '" stroke-width="1.8"/>' +
    '<ellipse cx="20" cy="29" rx="16" ry="20.5" fill="none" stroke="' + color + '" stroke-width="2.2"/>' +
    '<ellipse cx="20" cy="29" rx="12.6" ry="17" fill="none" stroke="' + color + '" stroke-width="0.9"/>' +
    '<text x="20" y="37.5" text-anchor="middle" font-family="QFraunces" font-weight="600" font-size="23" fill="' + color + '">R</text>' +
    '</svg>';

  function lineaTiempo(ancho, color) {
    let marcas = '';
    for (let x = 0; x <= ancho; x += 30) {
      const larga = x % 150 === 0;
      marcas += '<line x1="' + x + '" y1="' + (larga ? 0 : 2) + '" x2="' + x + '" y2="4" stroke="' + color + '" stroke-width="1"/>';
    }
    return '<svg viewBox="0 0 ' + ancho + ' 8" data-texto="imagen" preserveAspectRatio="none">' +
      '<line x1="0" y1="4" x2="' + ancho + '" y2="4" stroke="' + color + '" stroke-width="1"/>' + marcas + '</svg>';
  }

  // ---------- Renders con datos ----------
  const RENDER = {
    logoQ: (el) => { el.innerHTML = LOGO_Q(el.dataset.bowl || '#1C2433', el.dataset.cinta || '#C9A34E'); },
    logoR: (el) => { el.innerHTML = LOGO_R(el.dataset.color || '#C9A34E'); },

    ejemplos: (el, d) => {
      el.innerHTML = d.ejemplos.map(x =>
        '<div class="ej"><span class="anio">' + e(x.anio) + '</span><span class="txt">' + e(x.texto) + '</span></div>').join('');
    },

    evals: (el, d) => {
      el.innerHTML = d.evals.filas.map(f => {
        const nov = '<td class="nov"><b>' + e(f.novela) + '</b> <span class="oc">' + e(f.ocasion) + '</span></td>';
        const est = f.estado === 'publicada'
          ? '<span class="chip pasa"><span class="g">✓</span> publicada</span>'
          : '<span class="chip pend">en curso</span>';
        if (f.estado !== 'publicada') {
          return '<tr class="curso">' + nov + '<td class="c">' + f.caps + '</td><td class="c">' + est +
            '</td><td colspan="8" class="nota-curso">' + e(f.nota || '') + ' · sin resultados todavía</td></tr>';
        }
        const clase = f.fallo ? 'fallo' : (f.tipo === 'ref' ? 'ref' : '');
        const alerta = f.alerta ? '<tr class="alerta' + (f.fallo ? ' fallo' : '') + '"><td colspan="11">' + (f.fallo ? '✕ ' : '! ') + e(f.alerta) + '</td></tr>' : '';
        return '<tr class="' + clase + '">' + nov +
          '<td class="c">' + f.caps + '</td>' +
          '<td class="c">' + est + '</td>' +
          '<td class="num">' + f.intentos + '</td>' +
          '<td class="c">' + chip(f.nombres) + '</td>' +
          '<td class="c">' + chip(f.longitud) + '</td>' +
          '<td class="c">' + chip(f.prohibidas) + '</td>' +
          '<td class="c">' + chip(f.lean) + '</td>' +
          '<td class="num">' + fmt(f.juez, 2) + ' / ' + f.cont + '</td>' +
          '<td class="num">' + e(f.tokens) + '</td>' +
          '<td class="num">' + fmt(f.usd, 2) + ' $</td></tr>' + alerta;
      }).join('');
    },

    tuningAntes: (el, d) => { el.innerHTML = d.tuning.antes.map(x => '<li><span class="m">✕</span>' + e(x) + '</li>').join(''); },
    tuningDespues: (el, d) => { el.innerHTML = d.tuning.despues.map(x => '<li><span class="m">✓</span>' + e(x) + '</li>').join(''); },
    tuningBarras: (el, d) => {
      el.innerHTML = d.tuning.barras.map(b => {
        const color = b.valor >= 7 ? 'var(--salvia)' : (b.valor >= 5 ? 'var(--oro)' : 'var(--lacre)');
        return '<div class="barra-fila"><span class="be">' + e(b.etiqueta) + '</span>' +
          '<span class="bc">' + b.contradicciones + (b.contradicciones === 1 ? ' contradicción' : ' contradicciones') + '</span>' +
          '<span class="bpista"><span class="bb" style="width:' + (b.valor * 10) + '%;background:' + color + '"></span></span>' +
          '<span class="bv">' + b.valor + '</span></div>';
      }).join('');
    },

    etiquetasLangfuse: (el, d) => {
      el.innerHTML = d.langfuse.etiquetas.map((t, i) =>
        '<div class="e16"><span class="num-circ">' + (i + 1) + '</span><p>' + e(t) + '</p></div>').join('');
    },

    costeFases: (el, d) => {
      const L = d.langfuse, tot = L.fases.reduce((a, f) => a + f.usd, 0);
      const tonos = ['#C9A34E', '#7D7869', '#1C2433', '#5E8C6A', '#B9B3A3'];
      el.innerHTML = '<div class="apilada">' + L.fases.map((f, i) =>
        '<span class="seg" style="width:' + (f.usd / tot * 100) + '%;background:' + tonos[i] + '"></span>').join('') + '</div>' +
        '<div class="leyenda">' + L.fases.map((f, i) =>
          '<span class="ley"><span class="sw" style="background:' + tonos[i] + '"></span>' + e(f.fase) + ' <b>' + fmt(f.usd, 2) + ' $</b></span>').join('') +
        '<span class="ley tot">= <b>' + fmt(L.total_usd, 2) + ' $</b></span></div>';
    },

    proyecto: (el, d) => {
      el.innerHTML = d.proyecto.fases.map(f =>
        '<tr><td><b>' + e(f.fase) + '</b> <span class="sec">· ' + e(f.detalle) + '</span></td><td class="num">' + f.horas + ' h</td></tr>').join('') +
        '<tr class="total"><td>Total · ' + d.proyecto.tarifa_eur_h + ' €/h</td><td class="num">' + d.proyecto.total_horas + ' h · ' + fmt(d.proyecto.total_eur, 0) + ' €</td></tr>';
    },

    escenarios: (el, d) => {
      const filas = d.escenarios.filas, max = Math.max(...filas.map(f => f.margen_eur));
      const alto = 104;
      el.innerHTML = filas.map(f => {
        const h = Math.max(6, Math.round(f.margen_eur / max * alto));
        return '<div class="esc"><span class="ev">' + fmt(f.margen_eur, 0) + ' €</span>' +
          '<span class="eb" style="height:' + h + 'px"></span>' +
          '<span class="en">' + fmt(f.novelas, 0) + ' novelas/mes</span>' +
          '<span class="ep">' + fmt(f.margen_pct, f.margen_pct % 1 ? 1 : 0) + ' %</span></div>';
      }).join('');
    },

    tornado: (el, d) => {
      const S = d.sensibilidad, base = S.base_eur;
      const ancho = 520; // px que representan el margen base completo
      el.innerHTML =
        '<div class="tor-fila base"><span class="tl">Margen base</span><span class="tp"><span class="tb" style="width:' + ancho + 'px;background:var(--salvia)"></span></span><span class="tv">' + fmt(base, 2) + ' €</span></div>' +
        S.casos.map(c => {
          const w = Math.round(c.margen_eur / base * ancho);
          const perd = ancho - w;
          const col = c.tono === 'lacre' ? 'var(--lacre)' : 'var(--oro)';
          return '<div class="tor-fila"><span class="tl">' + e(c.caso) + '</span><span class="tp">' +
            '<span class="tb" style="width:' + w + 'px;background:var(--salvia)"></span>' +
            '<span class="tb perd" style="width:' + perd + 'px;background:' + col + '"></span></span>' +
            '<span class="tv">' + fmt(c.margen_eur, 2) + ' € <span class="td" style="color:' + col + '">(' + fmt(c.delta_pct, 1) + ' %)</span></span></div>';
        }).join('');
    },

    manifiesto: (el, d) => {
      el.innerHTML = '<tr><th class="c">Cap.</th><th class="c">v' + d.demo.version_origen + '</th><th class="c">v' + d.demo.version_nueva + '</th><th>Qué pasó</th></tr>' +
        d.demo.manifiesto.map(m => {
          const que = m.tipo === 'reparado' ? 'reparado (' + e(m.nota) + ')' : 'previsto';
          return '<tr><td class="c mono">' + m.cap + '</td><td class="c mono">cv ' + m.v2 + '</td>' +
            '<td class="c"><span class="chip ' + (m.tipo === 'reparado' ? 'aviso' : 'rep') + ' mf">cv ' + m.v3 + '</span></td>' +
            '<td class="q">' + que + '</td></tr>';
        }).join('');
    },
  };

  // ---------- Pie ----------
  function pies(datos) {
    const slides = Array.from(document.querySelectorAll('section.slide'));
    const total = String(slides.length).padStart(2, '0');
    slides.forEach((s, i) => {
      if (s.dataset.pie === 'no') return;
      const oscura = s.classList.contains('oscura');
      const pie = document.createElement('footer');
      pie.className = 'pie';
      pie.innerHTML =
        '<div class="linea">' + lineaTiempo(1200, '#C9A34E') + '</div>' +
        '<div class="fila-pie">' +
        '<div class="marca">' + LOGO_Q(oscura ? '#C9A34E' : '#1C2433', oscura ? '#F5EFE3' : '#C9A34E') +
        '<span class="nombre">' + e(datos.empresa) + '</span><span class="ini">· ' + e(datos.iniciativa) + '</span></div>' +
        '<div class="centro">' + e(datos.producto) + ' · ' + e(datos.ocasion) + '</div>' +
        '<div class="num">' + String(i + 1).padStart(2, '0') + ' / ' + total + '</div></div>';
      s.appendChild(pie);
    });
  }

  async function iniciar() {
    let datos;
    try {
      datos = await (await fetch('datos.json', { cache: 'no-store' })).json();
    } catch (err) {
      document.body.insertAdjacentHTML('afterbegin',
        '<p style="padding:16px;font:16px sans-serif">No se pudo leer datos.json. Abre el deck con un servidor (construir.py lo hace) y no como fichero suelto.</p>');
      throw err;
    }
    document.querySelectorAll('[data-render]').forEach(el => {
      const f = RENDER[el.dataset.render];
      if (f) f(el, datos); else console.warn('render desconocido', el.dataset.render);
    });
    aplicarPlantillas(datos);
    pies(datos);
    await document.fonts.ready;
    window.DECK_LISTO = true;
  }
  iniciar();
})();
