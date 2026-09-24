// @vitest-environment node
// IMP-32: sin copia local de la novela. Ni almacenamiento del navegador, ni caché
// persistente de respuestas, ni service worker (spec §1 y §9).

import { describe, expect, it } from 'vitest'
import { fuentes, sinComentarios } from './fuentes'

const COPIA_LOCAL = [/localStorage/, /sessionStorage/, /indexedDB/, /\bcaches\./, /serviceWorker/]

describe('sin copia local', () => {
  it('nada en src guarda la novela en el navegador', () => {
    const culpables = fuentes()
      .filter((f) => COPIA_LOCAL.some((p) => p.test(sinComentarios(f.texto))))
      .map((f) => f.ruta)
    expect(culpables).toEqual([])
  })

  it('el cliente pide sin caché', () => {
    const cliente = fuentes().find((f) => f.ruta === 'shared/api/cliente.ts')!
    expect(cliente.texto).toContain("cache: 'no-store'")
  })
})
