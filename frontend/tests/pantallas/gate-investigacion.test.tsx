// El gate de Investigation con el corpus a la vista (spec gate-investigacion).

import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import type { Hecho, SalidaDeFase } from '@/shared/api'
import { montar } from '../montar'
import { API, enviados, gateDe, servidor } from '../servidor'

const base = { origen: 'investigacion_inicial', fuentes: [] as Hecho['fuentes'], motivo_respaldo: null }
const hechos: Hecho[] = [
  { ...base, id: 1, enunciado: 'En 1982 se fundó el movimiento', estado: 'verificado', dimension: 'cronologia', respaldo: 'respaldado', firmeza: 'documentado', cita: 'fundado en 1982' },
  {
    ...base,
    id: 2,
    enunciado: 'En 1983 cambiaron la bandera por una blanca',
    estado: 'verificado',
    dimension: 'cronologia',
    respaldo: 'no_respaldado',
    firmeza: 'inferido',
    cita: 'se reunieron en 1983',
    motivo_respaldo: 'La cita no menciona ninguna bandera.',
  },
  {
    ...base,
    id: 3,
    enunciado: 'Se hablaba wólof en el mercado de Sandaga',
    estado: 'verificado',
    dimension: 'lenguaje',
    respaldo: 'respaldado',
    firmeza: 'documentado',
    no_lo_dice_la_cita: 'de Sandaga',
    cita: 'se hablaba wólof en el mercado',
  },
]

const salida: SalidaDeFase = {
  fase: 'investigation',
  ejecuciones: [],
  decisiones: [{ gate_id: 6, estado: 'pendiente', decision: null, comentario: null, decidido_en: null }],
  investigacion: { hechos, recuento: { cronologia: 2, lenguaje: 1 }, entidades: [], sello: null },
}

let descartados: { hecho: string; cuerpo: unknown }[] = []

beforeEach(() => {
  descartados = []
  servidor.use(
    http.get(`${API}/novelas/:id/gate`, () =>
      HttpResponse.json({ ...gateDe('rio'), fase: 'investigation', corpus_sellado: false, editables: [] }),
    ),
    http.get(`${API}/novelas/:id/fases/investigacion`, () => HttpResponse.json(salida)),
    http.post(`${API}/novelas/:id/hechos/:hecho/descartar`, async ({ params, request }) => {
      descartados.push({ hecho: String(params.hecho), cuerpo: await request.json() })
      return HttpResponse.json({ nombre: 'rio', mensaje: 'Hecho descartado del corpus.' })
    }),
  )
})

describe('el gate de Investigación', () => {
  it('cada hecho lleva una sola etiqueta: su firmeza', async () => {
    montar('/novelas/rio/gate')
    const flojo = (await screen.findByText('En 1983 cambiaron la bandera por una blanca')).closest('li')!
    expect(within(flojo).getByText('inferido')).toBeInTheDocument()
    expect(within(flojo).queryByText(/^(verificado|no respaldado)$/)).toBeNull()
    const firme = screen.getByText('En 1982 se fundó el movimiento').closest('li')!
    expect(within(firme).getByText('documentado')).toBeInTheDocument()
    expect(within(firme).queryByText(/^(verificado|respaldado)$/)).toBeNull()
  })

  it('lo que el verificador no ha mirado sale en proceso de verificación, no inferido', async () => {
    const pendiente = { ...hechos[0]!, id: 9, enunciado: 'Se abrió el mercado del Born', respaldo: 'pendiente', firmeza: 'inferido' }
    servidor.use(
      http.get(`${API}/novelas/:id/fases/investigacion`, () =>
        HttpResponse.json({ ...salida, investigacion: { ...salida.investigacion!, hechos: [pendiente] } }),
      ),
    )
    montar('/novelas/rio/gate')
    const fila = (await screen.findByText('Se abrió el mercado del Born')).closest('li')!
    expect(within(fila).getByText('En proceso de verificación')).toBeInTheDocument()
    expect(within(fila).queryByText('inferido')).toBeNull()
  })

  it('solo hay pestañas de dimensión', async () => {
    montar('/novelas/rio/gate')
    await screen.findByText('En 1983 cambiaron la bandera por una blanca')
    expect(screen.queryByRole('button', { name: /Por revisar|Sin respaldo/ })).toBeNull()
    expect(screen.getByRole('button', { name: /Lenguaje/ })).toBeInTheDocument()
  })

  it('lo que no dice la cita va en el desplegable del verificador, sin quitar la cita', async () => {
    montar('/novelas/rio/gate')
    await userEvent.click(await screen.findByRole('button', { name: /Lenguaje/ }))
    const parcial = screen.getByText('Se hablaba wólof en el mercado de Sandaga').closest('li')!
    expect(within(parcial).getByText('«de Sandaga»').closest('details')).not.toHaveAttribute('open')
    expect(within(parcial).getByText('«se hablaba wólof en el mercado»')).toBeInTheDocument()
  })

  it('el motivo del verificador va en un desplegable cerrado, y solo bajo lo no respaldado', async () => {
    montar('/novelas/rio/gate')
    const flojo = (await screen.findByText('En 1983 cambiaron la bandera por una blanca')).closest('li')!
    const motivo = within(flojo).getByText('La cita no menciona ninguna bandera.')
    const desplegable = motivo.closest('details')!
    expect(desplegable).not.toHaveAttribute('open')
    expect(within(desplegable).getByText('Nota del verificador').tagName).toBe('SUMMARY')
    const firme = screen.getByText('En 1982 se fundó el movimiento').closest('li')!
    expect(within(firme).queryByText(/El verificador/)).toBeNull()
    expect(screen.getByRole('button', { name: 'Rehacer con el comentario' })).toBeInTheDocument()
  })

  it('descartar pide confirmación, envía el motivo y quita el hecho de la lista', async () => {
    montar('/novelas/rio/gate')
    const hecho = (await screen.findByText('En 1983 cambiaron la bandera por una blanca')).closest('li')!
    await userEvent.click(within(hecho).getByRole('button', { name: 'Descartar' }))
    const dialogo = await screen.findByRole('dialog', { name: 'Descartar el hecho' })
    expect(descartados).toEqual([])
    await userEvent.type(within(dialogo).getByPlaceholderText(/Por qué/), 'adornado')
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Sí, descartar' }))
    await waitFor(() => expect(descartados).toEqual([{ hecho: '2', cuerpo: { motivo: 'adornado' } }]))
    expect(await screen.findByText('Hecho descartado.')).toBeInTheDocument()
    expect(screen.queryByText('En 1983 cambiaron la bandera por una blanca')).toBeNull()
  })

  it('corregir guarda el enunciado nuevo como edición del hecho', async () => {
    montar('/novelas/rio/gate')
    const hecho = (await screen.findByText('En 1983 cambiaron la bandera por una blanca')).closest('li')!
    await userEvent.click(within(hecho).getByRole('button', { name: 'Corregir' }))
    const enunciado = screen.getByRole('textbox', { name: 'Enunciado' })
    await userEvent.clear(enunciado)
    await userEvent.type(enunciado, 'En 1983 hubo una reunión')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    await waitFor(() =>
      expect(enviados).toContainEqual({
        ruta: 'rio/ediciones',
        cuerpo: { objeto: 'hecho', fila_id: 2, campo: 'enunciado', valor: 'En 1983 hubo una reunión', motivo: '' },
      }),
    )
    expect(await screen.findByText('En 1983 hubo una reunión')).toBeInTheDocument()
  })

  it('la salida de la fase enlaza al gate mientras espera', async () => {
    montar('/novelas/rio/fases/investigacion')
    expect(await screen.findByRole('link', { name: 'Decidir en el gate →' })).toHaveAttribute('href', '/novelas/rio/gate')
  })
})
