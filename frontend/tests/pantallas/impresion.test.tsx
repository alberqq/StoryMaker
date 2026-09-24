// El documento de impresión (IMP-22 a IMP-25): lo que imprime Playwright y juzga
// `render_visual`.

import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { montar } from '../montar'
import { recibidas } from '../servidor'

async function documento(url: string) {
  const { container } = montar(url)
  await screen.findByText('Índice')
  return container.querySelector<HTMLElement>('[data-estado="listo"]')!
}

describe('print', () => {
  it('es un solo documento, en el orden de la spec', async () => {
    const doc = await documento('/novelas/mar/v/2/imprimir')
    const orden = [...doc.children].map((s) => s.getAttribute('data-render') || s.id || s.className)
    expect(orden).toEqual([
      'portada',
      'nota-del-autor',
      'indice',
      'capitulo-1',
      'capitulo-2',
      'capitulo-3',
      'personajes',
      'novedades',
    ])
  })

  it('las cuatro regiones llevan su `data-render`, sin depender de clases ni rótulos', async () => {
    const doc = await documento('/novelas/mar/v/2/imprimir')
    for (const region of ['indice', 'portada', 'personajes', 'novedades']) {
      expect(doc.querySelector(`[data-render="${region}"]`)).not.toBeNull()
    }
  })

  it('el índice y la ficha enlazan por ancla, no por router', async () => {
    const doc = await documento('/novelas/mar/v/2/imprimir')
    const indice = doc.querySelector('[data-render="indice"]')!
    const destinos = [...indice.querySelectorAll('a')].map((a) => a.getAttribute('href'))
    expect(destinos).toEqual(['#capitulo-1', '#capitulo-2', '#capitulo-3', '#personajes', '#novedades'])
    for (const destino of destinos) expect(doc.querySelector(destino!)).not.toBeNull()
    const ficha = doc.querySelector('[data-render="personajes"]')!
    expect([...ficha.querySelectorAll('a')].every((a) => a.getAttribute('href')!.startsWith('#'))).toBe(true)
  })

  it('una sola navegación lo trae entero', async () => {
    await documento('/novelas/mar/v/2/imprimir')
    expect(recibidas).toEqual(
      expect.arrayContaining([
        'GET /api/novelas/mar/versiones/2',
        'GET /api/novelas/mar/versiones/2/capitulos/1',
        'GET /api/novelas/mar/versiones/2/capitulos/3',
        'GET /api/novelas/mar/versiones/2/personajes',
        'GET /api/novelas/mar/versiones/1/diff/2',
      ]),
    )
  })

  it('sin predecesora se omite la página de novedades y el índice no la enlaza', async () => {
    const doc = await documento('/novelas/mar/v/1/imprimir')
    expect(doc.querySelector('[data-render="novedades"]')).toBeNull()
    expect(doc.querySelector('a[href="#novedades"]')).toBeNull()
  })
})
