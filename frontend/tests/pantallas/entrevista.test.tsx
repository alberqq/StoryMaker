// El encargo por conversación y la entrevista en el gate de Intake (IMP-47, IMP-48, spec §4.2 y §4.4).

import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { leerRonda } from '@/pages/gate/ui/Entrevista'
import { montar } from '../montar'
import { API, enviados, gateDe, panel, servidor } from '../servidor'

describe('el encargo por conversación', () => {
  it('es el modo con el que se abre el encargo', async () => {
    montar('/encargo')
    expect(await screen.findByRole('tab', { name: 'Conversación' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('textbox', { name: /La novela, con tus palabras/ })).toBeInTheDocument()
  })

  it('lanza con la descripción, siempre con gates, y lleva a la pantalla del gate', async () => {
    const { router } = montar('/encargo')
    await userEvent.type(await screen.findByRole('textbox', { name: /¿A quién se regala\?/ }), 'Ana Ruiz')
    await userEvent.type(screen.getByRole('textbox', { name: /La novela, con tus palabras/ }), 'Piratas en Cádiz')
    await userEvent.click(screen.getByRole('button', { name: 'Empezar la entrevista' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/novelas/ana-ruiz/gate'))
    expect(enviados[0]!.cuerpo).toEqual({
      encargo: { descripcion: 'Piratas en Cádiz', homenajeado: { nombre_homenajeado: 'Ana Ruiz' } },
      nombre: '',
      batch: false,
      investigacion: 'estandar',
    })
  })

  it('la casilla de investigación exhaustiva viaja con el encargo', async () => {
    montar('/encargo')
    await userEvent.type(await screen.findByRole('textbox', { name: /¿A quién se regala\?/ }), 'Ana Ruiz')
    await userEvent.click(screen.getByRole('checkbox', { name: /Investigación exhaustiva/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Empezar la entrevista' }))
    await waitFor(() => expect(enviados).toHaveLength(1))
    expect((enviados[0]!.cuerpo as { investigacion: string }).investigacion).toBe('exhaustiva')
  })

  it('sin homenajeado no se lanza', async () => {
    montar('/encargo')
    await userEvent.click(await screen.findByRole('button', { name: 'Empezar la entrevista' }))
    expect(await screen.findByText('Falta el nombre del homenajeado.')).toBeInTheDocument()
    expect(enviados).toEqual([])
  })
})

describe('la entrevista en el gate de Intake', () => {
  it('enseña la descripción, las rondas anteriores y las preguntas nuevas', async () => {
    montar('/novelas/lago/gate')
    const chat = await screen.findByLabelText('Conversación con el entrevistador')
    expect(within(chat).getByText('Una novela de piratas en Cádiz para mi madre.')).toBeInTheDocument()
    expect(within(chat).getByText('¿En qué año?')).toBeInTheDocument()
    expect(within(chat).getByText('En 1812')).toBeInTheDocument()
    expect(within(chat).getByRole('textbox', { name: '¿Cómo se llama su perro?' })).toBeInTheDocument()
  })

  it('tras contestar se queda y dice que el entrevistador está pensando', async () => {
    const { router } = montar('/novelas/lago/gate')
    await userEvent.type(await screen.findByRole('textbox', { name: '¿Dónde nació?' }), 'En Cádiz')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar 1 respuesta(s)' }))
    expect(await screen.findByText('está leyendo tus respuestas…')).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/novelas/lago/gate')
    expect(enviados[0]).toEqual({
      ruta: 'lago/decisiones',
      cuerpo: { decision: 'rehacer', comentario: '2. ¿Dónde nació?\n   En Cádiz' },
    })
  })

  it('sin preguntas enseña el brief cerrado y propone aprobar', async () => {
    const gate = gateDe('lago')
    servidor.use(
      http.get(`${API}/novelas/:id/gate`, () =>
        HttpResponse.json({
          ...gate,
          preguntas: [],
          conversacion: { ...gate.conversacion!, brief: { nombre_homenajeado: 'Ana Ruiz', lugar: 'Cádiz' } },
        }),
      ),
    )
    const { router } = montar('/novelas/lago/gate')
    expect(await screen.findByText('Tengo todo lo que necesito.')).toBeInTheDocument()
    expect(screen.getByText('Cádiz')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Aprobar y pasar a la Investigación' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/novelas/lago'))
    expect(enviados[0]!.cuerpo).toEqual({ decision: 'aprobar', comentario: '' })
  })

  it('sin gate y con la novela en el encargo, dice que el entrevistador está leyendo', async () => {
    servidor.use(
      http.get(`${API}/novelas/:id/gate`, () => HttpResponse.json({ codigo: 404 }, { status: 404 })),
      http.get(`${API}/novelas/:id/panel`, () =>
        HttpResponse.json({ ...panel('nueva'), estado: 'en_marcha', fase: 'intake' }),
      ),
    )
    montar('/novelas/nueva/gate')
    expect(await screen.findByText(/El entrevistador está leyendo el encargo/)).toBeInTheDocument()
  })
})

describe('leer una ronda', () => {
  it('separa preguntas y respuestas del comentario', () => {
    expect(leerRonda('1. ¿Perro?\n   Nala\n2. ¿Año?\n   1812').pares).toEqual([
      { pregunta: '¿Perro?', respuesta: 'Nala' },
      { pregunta: '¿Año?', respuesta: '1812' },
    ])
  })

  it('un comentario escrito a mano se enseña entero', () => {
    expect(leerRonda('Se llama Nala y nació en Cádiz')).toEqual({ pares: [], libre: 'Se llama Nala y nació en Cádiz' })
  })
})
