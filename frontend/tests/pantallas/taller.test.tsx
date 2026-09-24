// El taller como tablero (IMP-39, IMP-55, spec §4.1): columnas, tarjetas, arrastre,
// confirmación y el listado de las publicadas.

import { createEvent, fireEvent, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { montar } from '../montar'
import { API, enviados, recibidas, servidor } from '../servidor'

const columna = (nombre: string) => screen.getByRole('listitem', { name: nombre })
const tarjeta = (titulo: string) => screen.getByRole('article', { name: titulo })

function arrastrar(origen: HTMLElement, destino: HTMLElement) {
  const datos = { setData: () => {}, getData: () => '', effectAllowed: 'move', dropEffect: 'move' }
  fireEvent.dragStart(origen, { dataTransfer: datos })
  const sobre = createEvent.dragOver(destino, { dataTransfer: datos })
  fireEvent(destino, sobre)
  fireEvent.drop(destino, { dataTransfer: datos })
  fireEvent.dragEnd(origen, { dataTransfer: datos })
  return sobre
}

describe('el tablero', () => {
  it('pone cada novela en curso en la columna de su fase, en cinco columnas', async () => {
    montar('/')
    const tablero = await screen.findByRole('list', { name: 'Tablero por fases' })
    expect(within(tablero).getAllByRole('listitem').map((c) => c.getAttribute('aria-label'))).toEqual([
      'Encargo',
      'Investigación',
      'Trama',
      'Escritura',
      'Publicación',
    ])
    expect(within(columna('Trama')).getByText('El río de Sevilla')).toBeInTheDocument()
    expect(within(columna('Encargo')).getByText('lago')).toBeInTheDocument()
    expect(within(columna('Encargo')).getByText('nueva')).toBeInTheDocument()
  })

  it('las publicadas van en un listado bajo el tablero, no como tarjetas', async () => {
    montar('/')
    const listado = await screen.findByRole('region', { name: 'Publicadas' })
    expect(within(listado).getByRole('link', { name: 'La mar de Cádiz' })).toHaveAttribute('href', '/novelas/mar')
    expect(within(listado).getByRole('link', { name: /Leer v/ })).toHaveAttribute('href', expect.stringMatching(/^\/novelas\/mar\/v\/\d+$/))
    expect(screen.queryByRole('article', { name: 'La mar de Cádiz' })).toBeNull()
  })

  it('cada tarjeta dice su estado con texto, su homenajeado y su gate', async () => {
    montar('/')
    const rio = await screen.findByRole('article', { name: 'El río de Sevilla' })
    expect(within(rio).getByText('Espera tu decisión')).toBeInTheDocument()
    expect(within(rio).getByText('Para Luis Vera')).toBeInTheDocument()
    expect(within(rio).getByText(/Gate de Trama/)).toBeInTheDocument()
  })

  it('solo son arrastrables las tarjetas con gate pendiente', async () => {
    montar('/')
    await screen.findByRole('list', { name: 'Tablero por fases' })
    expect(tarjeta('El río de Sevilla')).toHaveAttribute('draggable', 'true')
    expect(tarjeta('lago')).toHaveAttribute('draggable', 'true')
    expect(tarjeta('nueva')).toHaveAttribute('draggable', 'false')
  })

  it('arrastrar a la columna siguiente propone aprobar, y nada se decide sin confirmar', async () => {
    montar('/')
    await screen.findByRole('list', { name: 'Tablero por fases' })
    arrastrar(tarjeta('El río de Sevilla'), columna('Escritura'))
    const dialogo = await screen.findByRole('dialog', { name: /Aprobar Trama y pasar a Escritura/ })
    expect(await within(dialogo).findByText('capitulos en la escaleta')).toBeInTheDocument()
    expect(enviados).toEqual([])
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Confirmar aprobación' }))
    expect(await screen.findByText(/Aprobado el gate de Trama/)).toBeInTheDocument()
    expect(enviados).toEqual([{ ruta: 'rio/decisiones', cuerpo: { decision: 'aprobar', comentario: '' } }])
  })

  it('soltar en su misma columna propone rehacer, con comentario', async () => {
    montar('/')
    await screen.findByRole('list', { name: 'Tablero por fases' })
    arrastrar(tarjeta('El río de Sevilla'), columna('Trama'))
    const dialogo = await screen.findByRole('dialog', { name: 'Rehacer Trama' })
    await userEvent.type(within(dialogo).getByRole('textbox'), 'Más escenas en el puerto')
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Confirmar rehacer' }))
    await screen.findByText(/Pedido rehacer Trama/)
    expect(enviados[0]).toEqual({
      ruta: 'rio/decisiones',
      cuerpo: { decision: 'rehacer', comentario: 'Más escenas en el puerto' },
    })
  })

  it('soltar en cualquier otra columna no hace nada', async () => {
    montar('/')
    await screen.findByRole('list', { name: 'Tablero por fases' })
    const sobre = arrastrar(tarjeta('El río de Sevilla'), columna('Encargo'))
    expect(sobre.defaultPrevented).toBe(false)
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('cancelar la confirmación no envía nada', async () => {
    montar('/')
    await screen.findByRole('list', { name: 'Tablero por fases' })
    arrastrar(tarjeta('El río de Sevilla'), columna('Escritura'))
    await userEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Cancelar' }))
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(enviados).toEqual([])
  })

  it('cada gesto tiene su botón en la tarjeta', async () => {
    montar('/')
    const rio = await screen.findByRole('article', { name: 'El río de Sevilla' })
    await userEvent.click(within(rio).getByRole('button', { name: 'Aprobar → Escritura' }))
    expect(await screen.findByRole('dialog', { name: /Aprobar Trama/ })).toBeInTheDocument()
  })

  it('un 409 al decidir se cuenta tal cual', async () => {
    servidor.use(
      http.post(`${API}/novelas/:id/decisiones`, () =>
        HttpResponse.json({ error: 'NovelaOcupada', codigo: 409 }, { status: 409 }),
      ),
    )
    montar('/')
    const rio = await screen.findByRole('article', { name: 'El río de Sevilla' })
    await userEvent.click(within(rio).getByRole('button', { name: 'Aprobar → Escritura' }))
    const dialogo = await screen.findByRole('dialog')
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Confirmar aprobación' }))
    expect(await within(dialogo).findByText('Hay una ejecución en curso')).toBeInTheDocument()
  })

  it('una novela sin versiones no tiene enlace de lectura, y se abre su panel', async () => {
    montar('/')
    const nueva = await screen.findByRole('article', { name: 'nueva' })
    expect(within(nueva).getByRole('link', { name: 'nueva' })).toHaveAttribute('href', '/novelas/nueva')
    expect(within(nueva).getByText('sin versiones')).toBeInTheDocument()
  })

  it('un directorio vacío se anuncia como vacío, con la llamada a encargar', async () => {
    servidor.use(http.get(`${API}/novelas`, () => HttpResponse.json([])))
    montar('/')
    expect(await screen.findByText(/Todavía no hay ninguna novela/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Encarga la primera' })).toHaveAttribute('href', '/encargo')
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('con la API caída avisa y ofrece reintento', async () => {
    servidor.use(http.get(`${API}/novelas`, () => HttpResponse.error()))
    montar('/')
    expect(await screen.findByText('El servidor no responde')).toBeInTheDocument()
    servidor.resetHandlers()
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('article', { name: 'El río de Sevilla' })).toBeInTheDocument()
    expect(recibidas.filter((r) => r === 'GET /api/novelas').length).toBeGreaterThanOrEqual(2)
  })
})
