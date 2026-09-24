// Las pantallas de lectura contra los contratos de `shared/api` (IMP-13 a IMP-19), con los
// casos de error de §9 de la spec.

import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { cambiarPreferencias, POR_DEFECTO } from '@/shared/lib'
import { montar } from '../montar'
import { API, recibidas, servidor } from '../servidor'

describe('reading · índice', () => {
  it('lista los capítulos en orden y marca el que cambió, según el diff', async () => {
    montar('/novelas/mar/v/2')
    const indice = await screen.findByRole('navigation', { name: 'Índice de capítulos' })
    const enlaces = within(indice).getAllByRole('link')
    expect(enlaces.map((a) => a.getAttribute('href'))).toEqual([
      '/novelas/mar/v/2/capitulos/1',
      '/novelas/mar/v/2/capitulos/2',
      '/novelas/mar/v/2/capitulos/3',
    ])
    const marcas = within(indice).getAllByText('cambiado')
    expect(marcas).toHaveLength(1)
    expect(marcas[0]!.closest('li')).toHaveTextContent('Capítulo 2')
    expect(recibidas).toContain('GET /api/novelas/mar/versiones/1/diff/2')
  })

  it('sin versión anterior no marca nada y no pide el diff', async () => {
    montar('/novelas/mar/v/1')
    await screen.findByRole('navigation', { name: 'Índice de capítulos' })
    expect(screen.queryByText('cambiado')).toBeNull()
    expect(recibidas.some((r) => r.includes('/diff/'))).toBe(false)
  })

  it('una versión inexistente lleva a «no existe» con vuelta al listado', async () => {
    montar('/novelas/mar/v/9')
    expect(await screen.findByRole('heading', { level: 2, name: 'No existe' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /volver al taller/i })).toHaveAttribute('href', '/')
  })

  it('una novela inexistente también', async () => {
    montar('/novelas/fantasma/v/1')
    expect(await screen.findByRole('heading', { level: 2, name: 'No existe' })).toBeInTheDocument()
  })
})

describe('reading · capítulo', () => {
  it('muestra el texto de esa versión, con anterior, siguiente e índice', async () => {
    montar('/novelas/mar/v/2/capitulos/2')
    expect(await screen.findByText(/Texto del capitulo 2 en la version 2/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /anterior/ })).toHaveAttribute('href', '/novelas/mar/v/2/capitulos/1')
    expect(screen.getByRole('link', { name: /siguiente/ })).toHaveAttribute('href', '/novelas/mar/v/2/capitulos/3')
  })

  it('el primero no ofrece anterior y el último no ofrece siguiente', async () => {
    const primero = montar('/novelas/mar/v/1/capitulos/1')
    await screen.findByText(/Texto del capitulo 1/)
    expect(screen.queryByRole('link', { name: /anterior/ })).toBeNull()
    primero.unmount()
    montar('/novelas/mar/v/1/capitulos/3')
    await screen.findByText(/Texto del capitulo 3/)
    expect(screen.queryByRole('link', { name: /siguiente/ })).toBeNull()
  })

  it('un capítulo inexistente muestra «no existe»', async () => {
    montar('/novelas/mar/v/1/capitulos/9')
    expect(await screen.findByRole('heading', { level: 2, name: 'No existe' })).toBeInTheDocument()
  })

  it('una URL con versión no numérica no identifica ningún texto', async () => {
    montar('/novelas/mar/v/ultima/capitulos/1')
    expect(await screen.findByRole('heading', { level: 2, name: 'No existe' })).toBeInTheDocument()
    expect(recibidas).toEqual([])
  })
})

describe('characters', () => {
  it('cada entrada enlaza a sus capítulos con la versión de la ruta', async () => {
    montar('/novelas/mar/v/2/personajes')
    const tomas = (await screen.findByText('Tomás Ruiz')).closest('section')!
    expect(within(tomas).getByRole('link', { name: 'capítulo 2' })).toHaveAttribute(
      'href',
      '/novelas/mar/v/2/capitulos/2',
    )
    expect(within(tomas).getByText(/hermano/)).toBeInTheDocument()
    expect(screen.getByText('Cádiz de las Cortes', { exact: false })).toBeInTheDocument()
  })

  it('un lugar se titula con su nombre corto y la descripción va debajo', async () => {
    montar('/novelas/mar/v/2/personajes')
    const taller = (await screen.findByRole('heading', { name: 'Taller de imprenta' })).closest('section')!
    expect(within(taller).getByText('Taller de imprenta con máquinas de prensa y cajas de tipos')).toBeInTheDocument()
  })

  it('una ficha sin capítulos se enseña sin enlaces y no se oculta', async () => {
    montar('/novelas/mar/v/2/personajes')
    const sin = (await screen.findByText('Sin Escena')).closest('section')!
    expect(within(sin).queryByRole('link')).toBeNull()
    expect(within(sin).getByText(/no aparece en ningún capítulo/i)).toBeInTheDocument()
  })
})

describe('cover', () => {
  it('lleva título, dedicatoria con la ocasión y nota del autor', async () => {
    montar('/novelas/mar/v/2/portada')
    expect(await screen.findByText('Para Elvira Ponce')).toBeInTheDocument()
    expect(screen.getByText(/con motivo de su jubilación/)).toBeInTheDocument()
    expect(screen.getByText('Nota del autor')).toBeInTheDocument()
  })

  it('sin Licencias declaradas enseña la portada y omite la nota', async () => {
    servidor.use(
      http.get(`${API}/novelas/:id/versiones/:n`, async () => {
        const { version } = await import('../servidor')
        const v = version(1)
        return HttpResponse.json({ ...v, paratexto: { ...v.paratexto, licencias: [] } })
      }),
    )
    montar('/novelas/mar/v/1/portada')
    expect(await screen.findByText('Para Elvira Ponce')).toBeInTheDocument()
    expect(screen.queryByText('Nota del autor')).toBeNull()
  })
})

describe('versions', () => {
  it('lista las versiones con fecha y puntuación, y abre cualquiera', async () => {
    montar('/novelas/mar/versiones')
    expect(await screen.findByRole('link', { name: 'Versión 1' })).toHaveAttribute('href', '/novelas/mar/v/1')
    expect(screen.getByText('7,3 / 10')).toBeInTheDocument()
    expect(screen.getByText('20 de septiembre de 2026')).toBeInTheDocument()
  })

  it('enseña qué capítulos cambian entre dos versiones', async () => {
    montar('/novelas/mar/versiones')
    const enlace = await screen.findByRole('link', { name: 'Capítulo 2' })
    expect(enlace).toHaveAttribute('href', '/novelas/mar/v/2/capitulos/2')
    expect(enlace.closest('li')).toHaveTextContent('reescrito')
  })
})

describe('rutas desconocidas', () => {
  it('caen en «no existe», nunca en blanco', async () => {
    montar('/esto/no/es/nada')
    expect(await screen.findByRole('heading', { level: 2, name: 'No existe' })).toBeInTheDocument()
  })
})

describe('reading · ajustes de lectura', () => {
  const libro = () => document.querySelector<HTMLElement>('article.libro')!
  beforeEach(() => cambiarPreferencias(POR_DEFECTO))

  it('la pestaña «Aa» cambia el tamaño y la fuente en vivo', async () => {
    montar('/novelas/mar/v/2/capitulos/2')
    await screen.findByText(/Texto del capitulo 2/)
    expect(libro().style.getPropertyValue('--lectura-tamano')).toBe('1.2rem')
    await userEvent.click(screen.getByRole('button', { name: 'Ajustes de lectura' }))
    const panel = screen.getByRole('dialog', { name: 'Ajustes de lectura' })
    await userEvent.click(within(panel).getByRole('button', { name: 'Letra más grande' }))
    expect(libro().style.getPropertyValue('--lectura-tamano')).toBe('1.35rem')
    await userEvent.click(within(panel).getByRole('radio', { name: /Inter/ }))
    expect(libro().style.getPropertyValue('--lectura-fuente')).toMatch(/^Inter/)
    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('dialog', { name: 'Ajustes de lectura' })).toBeNull()
  })

  it('el interlineado y la negrita cambian el texto en vivo', async () => {
    montar('/novelas/mar/v/2/capitulos/2')
    await screen.findByText(/Texto del capitulo 2/)
    await userEvent.click(screen.getByRole('button', { name: 'Ajustes de lectura' }))
    await userEvent.click(screen.getByRole('radio', { name: 'Amplio' }))
    expect(libro().style.getPropertyValue('--lectura-interlineado')).toBe('1.95')
    await userEvent.click(screen.getByRole('switch'))
    expect(libro().style.getPropertyValue('--lectura-peso')).toBe('600')
  })

  it('la aplicación en oscuro puede leer el libro en claro', async () => {
    montar('/novelas/mar/v/2/capitulos/2')
    await screen.findByText(/Texto del capitulo 2/)
    await userEvent.click(screen.getByRole('radio', { name: 'Tema oscuro' }))
    expect(document.documentElement.dataset.tema).toBe('oscuro')
    expect(libro()).not.toHaveAttribute('data-tema-libro')
    await userEvent.click(screen.getByRole('button', { name: 'Ajustes de lectura' }))
    await userEvent.click(screen.getByRole('radio', { name: /Claro/ }))
    expect(libro()).toHaveAttribute('data-tema-libro', 'claro')
    expect(document.documentElement.dataset.tema).toBe('oscuro')
    await userEvent.click(screen.getByRole('radio', { name: 'Tema claro' }))
    expect(document.documentElement.dataset.tema).toBe('claro')
  })

  it('los ajustes se recuerdan al volver a abrir el lector', async () => {
    const { router } = montar('/novelas/mar/v/2/capitulos/2')
    await screen.findByText(/Texto del capitulo 2/)
    await userEvent.click(screen.getByRole('button', { name: 'Ajustes de lectura' }))
    await userEvent.click(screen.getByRole('button', { name: 'Letra más pequeña' }))
    await router.navigate('/novelas/mar/v/2')
    await screen.findByRole('navigation', { name: 'Índice de capítulos' })
    expect(libro().style.getPropertyValue('--lectura-tamano')).toBe('1.05rem')
    expect(JSON.parse(window.localStorage.getItem('storymaker.preferencias')!)).toMatchObject({ tamano: 1 })
  })

  it('el lector no ofrece imprimir', async () => {
    montar('/novelas/mar/v/2')
    await screen.findByRole('navigation', { name: 'Índice de capítulos' })
    expect(screen.queryByRole('link', { name: 'Imprimir' })).toBeNull()
    expect(document.querySelector('a[href$="/imprimir"]')).toBeNull()
  })
})
