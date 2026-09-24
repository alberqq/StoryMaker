// @vitest-environment node
// IMP-32 e IMP-56: sin copia local de la novela. Ni almacenamiento del navegador, ni caché
// persistente de respuestas, ni service worker (spec §1 y §9).

import { describe, expect, it } from 'vitest'
import { fuentes, sinComentarios } from './fuentes'

/** El único módulo que puede usar el almacenamiento del navegador (spec §1 y §4.6). */
const PREFERENCIAS = 'shared/lib/preferencias.ts'

const COPIA_LOCAL = [/localStorage/, /sessionStorage/, /indexedDB/, /\bcaches\./, /serviceWorker/]

describe('sin copia local', () => {
  it('nada en src guarda la novela en el navegador', () => {
    const culpables = fuentes()
      .filter((f) => f.ruta !== PREFERENCIAS)
      .filter((f) => COPIA_LOCAL.some((p) => p.test(sinComentarios(f.texto))))
      .map((f) => f.ruta)
    expect(culpables).toEqual([])
  })

  it('las preferencias de lectura son lo único que se guarda, bajo una sola clave', () => {
    const texto = sinComentarios(fuentes().find((f) => f.ruta === PREFERENCIAS)!.texto)
    expect(texto).not.toMatch(/sessionStorage|indexedDB|caches\.|serviceWorker/)
    expect(texto.match(/localStorage\.(\w+)\(/g)?.sort()).toEqual(['localStorage.getItem(', 'localStorage.setItem('])
    expect(texto.match(/localStorage\.\w+\((\w+)/g)?.every((l) => l.endsWith('(CLAVE'))).toBe(true)
  })

  it('el cliente pide sin caché', () => {
    const cliente = fuentes().find((f) => f.ruta === 'shared/api/cliente.ts')!
    expect(cliente.texto).toContain("cache: 'no-store'")
  })
})
