// @vitest-environment node
// IMP-38: los colores son tokens de `app/styles/tokens.css`, y ningún componente ni hoja
// escribe un color literal (spec §8). El modo oscuro es una redefinición de tokens.

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'
import { SRC } from './fuentes'

const COLOR_LITERAL = /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(/

function recorrer(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const ruta = join(dir, n)
    return statSync(ruta).isDirectory() ? recorrer(ruta) : [ruta]
  })
}

describe('tokens de diseño', () => {
  it('fuera de tokens.css no hay colores literales', () => {
    const culpables = recorrer(SRC)
      .filter((r) => /\.(css|tsx)$/.test(r))
      .map((r) => relative(SRC, r).replaceAll('\\', '/'))
      .filter((r) => r !== 'app/styles/tokens.css')
      .filter((r) => COLOR_LITERAL.test(readFileSync(join(SRC, r), 'utf-8')))
    expect(culpables).toEqual([])
  })

  it('el modo oscuro redefine los tokens', () => {
    const tokens = readFileSync(join(SRC, 'app', 'styles', 'tokens.css'), 'utf-8')
    expect(tokens).toMatch(/@media \(prefers-color-scheme: dark\)/)
    expect(tokens).toMatch(/--fondo:/)
  })
})
