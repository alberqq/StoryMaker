// El encargo (IMP-40, spec §4.2).

import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { montar } from '../montar'
import { enviados } from '../servidor'

const alFormulario = async () =>
  userEvent.click(await screen.findByRole('tab', { name: 'Formulario completo' }))

describe('el encargo con el formulario completo', () => {
  it('sin nombre del homenajeado no se lanza, y el error sale junto a su campo', async () => {
    montar('/encargo')
    await alFormulario()
    await userEvent.click(await screen.findByRole('button', { name: 'Encargar y lanzar' }))
    expect(await screen.findByText('Falta el nombre del homenajeado.')).toBeInTheDocument()
    expect(enviados).toEqual([])
  })

  it('se puede partir de un ejemplo', async () => {
    montar('/encargo')
    await alFormulario()
    const selector = await screen.findByRole('combobox', { name: 'Partir de un ejemplo' })
    await userEvent.selectOptions(selector, 'brief-salamanca')
    expect(screen.getByDisplayValue('Tomás Aldecoa')).toBeInTheDocument()
    expect(screen.getByDisplayValue('cierre de su librería')).toBeInTheDocument()
  })

  it('lanza con gates por defecto y lleva al panel de la novela', async () => {
    const { router } = montar('/encargo')
    await alFormulario()
    await userEvent.type(
      await screen.findByRole('textbox', { name: /Nombre, tal como debe escribirse/ }),
      'Ana Ruiz',
    )
    await userEvent.click(screen.getByRole('button', { name: '+ Añadir elemento' }))
    await userEvent.type(screen.getByRole('textbox', { name: 'Elemento 1' }), 'tiene un perro')
    await userEvent.click(screen.getByRole('button', { name: 'Encargar y lanzar' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/novelas/ana-ruiz'))
    const cuerpo = enviados[0]!.cuerpo as { batch: boolean; encargo: Record<string, any> }
    expect(cuerpo.batch).toBe(false)
    expect(cuerpo.encargo.homenajeado.nombre_homenajeado).toBe('Ana Ruiz')
    expect(cuerpo.encargo.homenajeado.elementos_personalizacion).toEqual([
      { texto: 'tiene un perro', obligatorio: false },
    ])
    expect(cuerpo.encargo.obra.n_capitulos).toBe(10)
  })

  it('en batch lo dice al lanzar', async () => {
    montar('/encargo')
    await alFormulario()
    await userEvent.type(
      await screen.findByRole('textbox', { name: /Nombre, tal como debe escribirse/ }),
      'Ana Ruiz',
    )
    await userEvent.click(screen.getByRole('radio', { name: /En batch/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Encargar y lanzar' }))
    await waitFor(() => expect(enviados).toHaveLength(1))
    expect((enviados[0]!.cuerpo as { batch: boolean }).batch).toBe(true)
  })
})
