// @vitest-environment node
// IMP-09 e IMP-27: ningún módulo fuera de `shared/api` emite una petición de red.
//
// Es condición de G5 y no higiene: lo que no pasa por el cliente único no lo puede
// interceptar `render_visual`, y lo juzgado dejaría de ser lo que se publica (spec §6).

import { describe, expect, it } from 'vitest'
import { fuentes, sinComentarios } from './fuentes'

const RED = [/\bfetch\s*\(/, /XMLHttpRequest/, /\bWebSocket\b/, /\bEventSource\b/, /navigator\.sendBeacon/, /\baxios\b/]

describe('cliente único', () => {
  it('fuera de shared/api nadie emite red', () => {
    const culpables = fuentes()
      .filter((f) => !f.ruta.startsWith('shared/api/'))
      .filter((f) => RED.some((patron) => patron.test(sinComentarios(f.texto))))
      .map((f) => f.ruta)
    expect(culpables).toEqual([])
  })

  it('dentro de shared/api solo el cliente llama a fetch', () => {
    const conFetch = fuentes()
      .filter((f) => f.ruta.startsWith('shared/api/') && /\bfetch\s*\(/.test(sinComentarios(f.texto)))
      .map((f) => f.ruta)
    expect(conFetch).toEqual(['shared/api/cliente.ts'])
  })

  it('no hay una segunda instancia de cliente', () => {
    const instancias = fuentes().filter((f) => /export const cliente\b/.test(f.texto))
    expect(instancias.map((f) => f.ruta)).toEqual(['shared/api/cliente.ts'])
  })

  it('el cliente no envía autenticación ni guarda credenciales (U-17)', () => {
    const cliente = fuentes().find((f) => f.ruta === 'shared/api/cliente.ts')!
    expect(sinComentarios(cliente.texto)).not.toMatch(/Authorization|credentials|token/i)
  })
})
