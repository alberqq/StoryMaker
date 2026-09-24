// La petición de cambio del lector (IMP-20, IMP-21, spec §5).

import { fireEvent, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { montar } from '../montar'
import { API, recibidas, servidor } from '../servidor'

/** Selecciona un trozo del primer párrafo del capítulo, como lo haría el ratón. */
async function seleccionar(texto: string) {
  const parrafo = await screen.findByText(/Texto del capitulo 2/)
  const nodo = parrafo.firstChild!
  const inicio = nodo.textContent!.indexOf(texto)
  const rango = document.createRange()
  rango.setStart(nodo, inicio)
  rango.setEnd(nodo, inicio + texto.length)
  const seleccion = document.getSelection()!
  seleccion.removeAllRanges()
  seleccion.addRange(rango)
  fireEvent.mouseUp(parrafo)
}

describe('petición de cambio', () => {
  it('sin selección el formulario no se habilita', async () => {
    montar('/novelas/mar/v/2/capitulos/2')
    await screen.findByText(/Texto del capitulo 2/)
    expect(screen.getByRole('button', { name: 'Enviar petición' })).toBeDisabled()
    expect(screen.getByRole('textbox')).toBeDisabled()
  })

  it('viaja con fragmento, capítulo, versión y texto, y devuelve un acuse', async () => {
    let cuerpo: unknown
    servidor.use(
      http.post(`${API}/novelas/:id/cambios`, async ({ request }) => {
        cuerpo = await request.json()
        return HttpResponse.json({ peticion: 'x', gate_abierto: 7, candidatos: [], nota: '' })
      }),
    )
    montar('/novelas/mar/v/2/capitulos/2')
    await seleccionar('capitulo 2')
    expect(await screen.findByLabelText('Fragmento seleccionado')).toHaveTextContent('capitulo 2')
    await userEvent.type(screen.getByRole('textbox'), 'El perro se llama Nala')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar petición' }))

    expect(await screen.findByText(/ha quedado registrada/)).toBeInTheDocument()
    expect(cuerpo).toEqual({ texto: 'El perro se llama Nala', fragmento: 'capitulo 2', capitulo: 2, version: 2 })
  })

  it('un 409 se cuenta tal cual, sin reintento ni cola', async () => {
    servidor.use(
      http.post(`${API}/novelas/:id/cambios`, () =>
        HttpResponse.json({ error: 'NovelaOcupada', codigo: 409 }, { status: 409 }),
      ),
    )
    montar('/novelas/mar/v/2/capitulos/2')
    await seleccionar('capitulo 2')
    await userEvent.type(screen.getByRole('textbox'), 'Cambia esto')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar petición' }))

    expect(await screen.findByText(/ejecución en curso/)).toBeInTheDocument()
    await new Promise((r) => setTimeout(r, 50))
    expect(recibidas.filter((r) => r.startsWith('POST'))).toHaveLength(1)
  })
})
