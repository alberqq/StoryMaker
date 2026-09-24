// La pantalla del gate (IMP-42, spec §4.4).

import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { montar } from '../montar'
import { API, enviados, gateDe, servidor } from '../servidor'

/** El gate de Regeneración de `rio`, con dos candidatos elegibles y uno registrado sin fila. */
function conRegeneracion() {
  const alcance = { capitulos_a_revisar: [], coste: '' }
  servidor.use(
    http.get(`${API}/novelas/:id/gate`, () =>
      HttpResponse.json({
        ...gateDe('rio'),
        fase: 'regeneration',
        peticion: {
          texto: 'Quita el apellido del protagonista',
          fragmento: null,
          capitulo: null,
          version: null,
          candidatos: [
            { objeto: 'personaje', fila_id: 1, campo: 'nombre', valor: 'Tomás Ruiz', descripcion: 'Tomás Ruiz', capitulos_a_regenerar: [1, 2], ...alcance },
            { objeto: 'hecho', fila_id: 9, campo: 'enunciado', valor: 'El muelle existía', descripcion: 'El muelle existía', capitulos_a_regenerar: [3], ...alcance },
            { objeto: null, fila_id: null, campo: null, valor: 'Viejo', descripcion: 'Viejo', capitulos_a_regenerar: [], ...alcance },
          ],
        },
      }),
    ),
  )
}

describe('el gate', () => {
  it('dice qué fase espera, su resumen y enlaza a la salida completa', async () => {
    montar('/novelas/rio/gate')
    expect(await screen.findByRole('heading', { name: 'Trama espera tu decisión' })).toBeInTheDocument()
    expect(screen.getByText('capitulos en la escaleta')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Leer la salida completa de Trama/ })).toHaveAttribute(
      'href',
      '/novelas/rio/fases/trama',
    )
  })

  it('fuera de Intake no ofrece abortar', async () => {
    montar('/novelas/rio/gate')
    await screen.findByRole('button', { name: 'Aprobar' })
    expect(screen.queryByRole('button', { name: 'Abortar' })).toBeNull()
  })

  it('rehacer envía el comentario y vuelve al panel', async () => {
    const { router } = montar('/novelas/rio/gate')
    await userEvent.type(await screen.findByRole('textbox', { name: 'Comentario' }), 'Otro final')
    await userEvent.click(screen.getByRole('button', { name: 'Rehacer con el comentario' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/novelas/rio'))
    expect(enviados).toEqual([{ ruta: 'rio/decisiones', cuerpo: { decision: 'rehacer', comentario: 'Otro final' } }])
  })

  it('en Intake las preguntas se contestan y contestar es rehacer con las respuestas', async () => {
    montar('/novelas/lago/gate')
    const primera = await screen.findByRole('textbox', { name: '¿Cómo se llama su perro?' })
    await userEvent.type(primera, 'Nala')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar 1 respuesta(s)' }))
    await waitFor(() => expect(enviados).toHaveLength(1))
    expect(enviados[0]).toEqual({
      ruta: 'lago/decisiones',
      cuerpo: { decision: 'rehacer', comentario: '1. ¿Cómo se llama su perro?\n   Nala' },
    })
  })

  it('en Intake abortar existe y pide confirmación', async () => {
    montar('/novelas/lago/gate')
    await userEvent.click(await screen.findByRole('button', { name: 'Abortar' }))
    const dialogo = await screen.findByRole('dialog', { name: 'Abortar la novela' })
    expect(enviados).toEqual([])
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Sí, abortar' }))
    await waitFor(() => expect(enviados[0]?.cuerpo).toEqual({ decision: 'abortar', comentario: '' }))
  })

  it('el editor guarda una fila sin enviar ninguna decisión', async () => {
    montar('/novelas/rio/gate')
    await screen.findByRole('heading', { name: 'Trama espera tu decisión' })
    const estatus = screen.getByDisplayValue('piloto')
    await userEvent.clear(estatus)
    await userEvent.type(estatus, 'contramaestre')
    await userEvent.type(screen.getByPlaceholderText(/Motivo del cambio/), 'así era')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    expect(await screen.findByText('Guardado: estatus')).toBeInTheDocument()
    expect(enviados).toEqual([
      {
        ruta: 'rio/ediciones',
        cuerpo: { objeto: 'personaje', fila_id: 2, campo: 'estatus', valor: 'contramaestre', motivo: 'así era' },
      },
    ])
    expect(enviados.some((e) => e.ruta.endsWith('decisiones'))).toBe(false)
  })

  it('un hecho de un corpus sellado no se ofrece como editable', async () => {
    montar('/novelas/rio/gate')
    await screen.findByRole('heading', { name: 'Trama espera tu decisión' })
    await userEvent.click(screen.getByRole('button', { name: /Hechos del corpus/ }))
    expect(screen.getByText(/El corpus está sellado/)).toBeInTheDocument()
    expect(screen.getByDisplayValue('El muelle existía')).toBeDisabled()
  })

  it('sin gate pendiente lo dice y enlaza al panel', async () => {
    montar('/novelas/mar/gate')
    expect(await screen.findByText('No hay ningún gate esperando')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ir al panel de la novela' })).toHaveAttribute('href', '/novelas/mar')
  })

  describe('en Regeneración', () => {
    it('el primer candidato viene elegido y su valor precargado', async () => {
      conRegeneracion()
      montar('/novelas/rio/gate')
      await waitFor(() => expect(screen.getByRole('radio', { name: /Tomás Ruiz/ })).toBeChecked())
      expect(await screen.findByRole('textbox', { name: /Valor nuevo/ })).toHaveValue('Tomás Ruiz')
      expect(screen.getByRole('radio', { name: /Viejo/ })).toBeDisabled()
    })

    it('aprobar envía la fila elegida y su valor nuevo', async () => {
      conRegeneracion()
      montar('/novelas/rio/gate')
      await userEvent.click(await screen.findByRole('radio', { name: /El muelle existía/ }))
      const valor = await screen.findByRole('textbox', { name: /Valor nuevo/ })
      await waitFor(() => expect(valor).toHaveValue('El muelle existía'))
      await userEvent.clear(valor)
      await userEvent.type(valor, 'El muelle no existía')
      await userEvent.click(screen.getByRole('button', { name: 'Aprobar' }))
      await waitFor(() => expect(enviados).toHaveLength(1))
      expect(enviados[0]?.cuerpo).toEqual({ decision: 'aprobar', comentario: 'hecho:9 enunciado=El muelle no existía' })
    })

    it('aprobar sin cambiar el valor no envía ninguna elección', async () => {
      conRegeneracion()
      montar('/novelas/rio/gate')
      expect(await screen.findByText('Sin cambiar el valor, aprobar no toca nada.')).toBeInTheDocument()
      await userEvent.click(screen.getByRole('button', { name: 'Aprobar' }))
      await waitFor(() => expect(enviados[0]?.cuerpo).toEqual({ decision: 'aprobar', comentario: '' }))
    })
  })
})
