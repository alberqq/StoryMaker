// El gate de la Trama con su revisión a la vista (spec trama-rehacible §3).

import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import type { RevisionDeLaTrama } from '@/shared/api'
import { montar } from '../montar'
import { API, gateDe, servidor } from '../servidor'

const revision: RevisionDeLaTrama = {
  avisos: [
    { validador: 'arco_anclado', grave: true, mensaje: 'El arco del homenajeado es plano.', ubicacion: null },
    {
      validador: 'cobertura_reparada',
      grave: false,
      mensaje: '«el reloj» se ha anclado al capitulo 2, escena 1.',
      ubicacion: 'cap2-esc1',
    },
  ],
  huecos: [
    { pregunta: 'Como eran los pupitres', dimension: 'cultura_material', resultado: 'inventado', enunciado: 'Bancos de pino.', capitulo: 1, escena: 2 },
  ],
  inventados: 1,
  escenas_poco_firmes: [],
}

const conRevision = (trama: RevisionDeLaTrama | null) =>
  servidor.use(
    http.get(`${API}/novelas/:id/gate`, () =>
      HttpResponse.json({ ...gateDe('rio'), fase: 'plotting', corpus_sellado: false, editables: [], trama }),
    ),
  )

describe('el gate de la Trama', () => {
  it('enseña los avisos de la revisión y dice que rehacer los lleva al arquitecto', async () => {
    conRevision(revision)
    montar('/novelas/rio/gate')
    expect(await screen.findByText('El arco del homenajeado es plano.')).toBeInTheDocument()
    expect(screen.getByText('Anclado por el arnés')).toBeInTheDocument()
    expect(screen.getByText(/el arquitecto recibe estos avisos/)).toBeInTheDocument()
  })

  it('enseña cada hueco con su escena y cómo se cubrió', async () => {
    conRevision(revision)
    montar('/novelas/rio/gate')
    expect(await screen.findByText('Como eran los pupitres')).toBeInTheDocument()
    expect(screen.getByText('cap. 1 esc. 2')).toBeInTheDocument()
    expect(screen.getByText('inventado')).toBeInTheDocument()
    expect(screen.getByText('Bancos de pino.')).toBeInTheDocument()
  })

  it('sin avisos lo dice en verde', async () => {
    conRevision({ ...revision, avisos: [], huecos: [] })
    montar('/novelas/rio/gate')
    expect(await screen.findByText(/en verde: la escaleta puede sellarse/)).toBeInTheDocument()
  })
})
