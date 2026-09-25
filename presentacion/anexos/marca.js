// Pie común de los anexos: línea fina de Oro viejo con marcas de línea de tiempo, logo de
// Qapítulo a la izquierda, la fuente de la página en el centro y el número a la derecha.
// Cada <section class="pagina"> declara su fuente en data-fuente; el <body>, su anexo en
// data-anexo. El script no pinta nada más: el contenido vive en el HTML.
//
// El logo es una «Q» serif cuya cola es la cinta de un marcapáginas, con la terminación
// en cola de milano: el ojo en Tinta y la cinta en Oro viejo (sobre fondo claro).

(function () {
  const LOGO =
    '<svg viewBox="0 0 40 44" aria-hidden="true">' +
    '<path fill="#1C2433" fill-rule="evenodd" d="M19 2 A15 16 0 1 1 18.99 2 Z ' +
    'M19 5.4 A10.2 12.6 0 1 0 19.01 5.4 Z" transform="rotate(-8 19 18)"/>' +
    '<path fill="#C9A34E" d="M20.6 26.2 L27.4 24.6 L33.6 42.4 L29.6 38.9 L27 43.6 Z"/>' +
    '</svg>';

  function linea(ancho) {
    let marcas = '';
    for (let x = 0; x <= ancho; x += 30) {
      const larga = x % 150 === 0;
      marcas += '<line x1="' + x + '" y1="' + (larga ? 0 : 2) + '" x2="' + x + '" y2="4" ' +
        'stroke="#C9A34E" stroke-width="1"/>';
    }
    return '<svg viewBox="0 0 ' + ancho + ' 8" preserveAspectRatio="none">' +
      '<line x1="0" y1="4" x2="' + ancho + '" y2="4" stroke="#C9A34E" stroke-width="1"/>' +
      marcas + '</svg>';
  }

  const anexo = document.body.dataset.anexo || '';
  const paginas = Array.from(document.querySelectorAll('section.pagina'));
  const total = String(paginas.length).padStart(2, '0');

  paginas.forEach(function (pagina, i) {
    const pie = document.createElement('footer');
    pie.className = 'pie';
    const n = String(i + 1).padStart(2, '0');
    const fuente = pagina.dataset.fuente || '';
    pie.innerHTML =
      '<div class="linea">' + linea(1200) + '</div>' +
      '<div class="fila-pie">' +
      '<div class="marca">' + LOGO + '<span>Qapítulo</span></div>' +
      '<div class="fuente">' + (fuente ? 'Fuente: ' + fuente : '') + '</div>' +
      '<div class="num">' + anexo + ' · ' + n + ' / ' + total + '</div>' +
      '</div>';
    pagina.appendChild(pie);
  });
})();
