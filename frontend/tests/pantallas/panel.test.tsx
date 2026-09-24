// El panel de una novela (IMP-41, spec §4.3 y §5.3).

import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import type { Panel } from '@/shared/api'
import { accionesDe } from '@/pages/novel/model/acciones'
import { montar } from '../montar'
import { API, enviados, panel, servidor } from '../servidor'

const conEstado = (estado: Panel['estado'], extra: Partial<Panel> = {}) =>
  servidor.use(http.get(`${API}/novelas/:id/panel`, () => HttpResponse.json({ ...panel('rio'), gate: null, ...extra, estado })))

describe('el panel', () => {
  it('enseña la línea de las seis fases, con la deducida marcada', async () => {
    montar('/novelas/mar')
    const linea = await screen.findByRole('list', { name: 'Fases de la novela' })
    const pasos = within(linea).getAllByRole('link')
    expect(pasos.map((p) => p.getAttribute('href'))).toEqual([
      '/novelas/mar/fases/encargo',
      '/novelas/mar/fases/investigacion',
      '/novelas/mar/fases/trama',
      '/novelas/mar/fases/escritura',
      '/novelas/mar/fases/publicacion',
      '/novelas/mar/fases/regeneracion',
    ])
    expect(within(pasos[0]!).getByText(/deducida/)).toBeInTheDocument()
    expect(within(pasos[1]!).getByText(/0,20/)).toBeInTheDocument()
  })

  it('enseña capítulos, actividad interpretada, consumo y versiones', async () => {
    montar('/novelas/mar')
    const rejilla = await screen.findByRole('list', { name: 'Capítulos' })
    expect(within(rejilla).getAllByRole('listitem')).toHaveLength(3)
    expect(screen.getByText('Capítulo 2, intento 2: borrador')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Versión 2' })).toHaveAttribute('href', '/novelas/mar/v/2')
    expect(screen.getByText('Demasiado corto')).toBeInTheDocument()
  })

  it('cada versión con PDF lo ofrece para descargar, y la que no lo tiene lo dice', async () => {
    montar('/novelas/mar')
    const enlace = await screen.findByRole('link', { name: 'PDF' })
    expect(enlace).toHaveAttribute('href', 'http://localhost/api/novelas/mar/versiones/1/pdf')
    expect(enlace).toHaveAttribute('download')
    expect(screen.getByText('sin PDF')).toBeInTheDocument()
  })

  it('con un gate pendiente ofrece decidir y enlaza al gate', async () => {
    montar('/novelas/rio')
    expect(await screen.findByRole('link', { name: 'Decidir el gate' })).toHaveAttribute('href', '/novelas/rio/gate')
    expect(screen.queryByRole('button', { name: 'Continuar' })).toBeNull()
  })

  it('en pausa ofrece continuar, y continuar dice que está lanzado', async () => {
    conEstado('en_pausa')
    montar('/novelas/rio')
    await userEvent.click(await screen.findByRole('button', { name: 'Continuar' }))
    expect(await screen.findByText('Lanzado.')).toBeInTheDocument()
    expect(enviados).toEqual([{ ruta: 'rio/continuar', cuerpo: {} }])
  })

  it('en marcha no ofrece ninguna acción y dice en qué trabaja', async () => {
    conEstado('en_marcha', { trabajando_en: 'Escritura: capítulo 2, intento 3' })
    montar('/novelas/rio')
    expect(await screen.findByText('Escritura: capítulo 2, intento 3')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Continuar|Desbloquear|Reintentar/ })).toBeNull()
  })

  it('detenida ofrece desbloquear, y pide confirmación', async () => {
    conEstado('detenida', { proceso: { cerrojo: true, pid: 4242, vivo: false } })
    montar('/novelas/rio')
    await userEvent.click(await screen.findByRole('button', { name: 'Desbloquear' }))
    const dialogo = await screen.findByRole('dialog', { name: 'Desbloquear la novela' })
    expect(within(dialogo).getByText(/PID 4242/)).toBeInTheDocument()
    expect(enviados).toEqual([])
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Romper el cerrojo' }))
    expect(await screen.findByText('Hecho.')).toBeInTheDocument()
    expect(enviados[0]!.ruta).toBe('rio/desbloquear')
  })

  it('cada estado ofrece exactamente sus acciones', () => {
    const base = { fase: 'writing', gate: null }
    expect(accionesDe({ ...base, estado: 'esperando_autor' })).toEqual(['decidir'])
    expect(accionesDe({ ...base, estado: 'fallida' })).toEqual(['reintentar', 'continuar'])
    expect(accionesDe({ ...base, fase: 'plotting', estado: 'fallida' })).toEqual(['continuar'])
    expect(accionesDe({ ...base, estado: 'detenida' })).toEqual(['desbloquear'])
    expect(accionesDe({ ...base, estado: 'aparcada' })).toEqual(['continuar'])
    expect(accionesDe({ ...base, estado: 'terminada' })).toEqual([])
    expect(accionesDe({ ...base, estado: 'arrancando' })).toEqual([])
  })

  it('una novela que no existe lleva a «no existe»', async () => {
    montar('/novelas/fantasma')
    expect(await screen.findByRole('heading', { name: 'No existe' })).toBeInTheDocument()
  })
})
