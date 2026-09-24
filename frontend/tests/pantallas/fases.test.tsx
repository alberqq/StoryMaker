// La salida de cada fase (IMP-43, spec §4.5).

import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { montar } from '../montar'

describe('las salidas por fase', () => {
  it('hay una pestaña por fase, y la actual está marcada', async () => {
    montar('/novelas/rio/fases/trama')
    const pestanas = await screen.findByRole('navigation', { name: 'Fases' })
    expect(pestanas.querySelectorAll('a')).toHaveLength(6)
    expect(screen.getByRole('link', { name: 'Trama' })).toHaveAttribute('aria-current', 'page')
  })

  it('la Trama enseña la obra, la escaleta con sus anclajes y los personajes', async () => {
    montar('/novelas/rio/fases/trama')
    expect(await screen.findByText('Un cartógrafo…')).toBeInTheDocument()
    expect(screen.getByText(/Capítulo 1\. El puerto/)).toBeInTheDocument()
    expect(screen.getByText('ambienta: La Casa de Contratación')).toBeInTheDocument()
    expect(screen.getByText('homenajeado')).toBeInTheDocument()
  })

  it('las decisiones de sus gates salen con su comentario', async () => {
    montar('/novelas/rio/fases/trama')
    expect(await screen.findByText('Más mar')).toBeInTheDocument()
  })

  it('una fase sin salida lo dice, sin error', async () => {
    montar('/novelas/rio/fases/escritura')
    expect(await screen.findByRole('heading', { name: 'Escritura' })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('una fase que no existe lleva a «no existe»', async () => {
    montar('/novelas/rio/fases/cocina')
    expect(await screen.findByRole('heading', { name: 'No existe' })).toBeInTheDocument()
  })
})
