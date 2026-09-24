// @vitest-environment node
// Las reglas estructurales de la spec (§2.2, §3, §7, §8) que se pueden comprobar sin ejecutar
// nada. Steiger mira lo mismo e informa; estas pruebas miran lo que sostiene un requisito.

import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { ALIAS } from '../../vite.config'
import { RAIZ, SRC, fuentes, sinComentarios } from './fuentes'

const CAPAS = ['app', 'pages', 'entities', 'shared'] as const
const capaDe = (ruta: string) => ruta.split('/')[0] as (typeof CAPAS)[number]
const sliceDe = (ruta: string) => ruta.split('/')[1]

/** Los imports por alias de un fichero: `@/pages/reading/ui/Indice` → `pages/reading/ui/Indice`. */
const importsDe = (texto: string) =>
  [...texto.matchAll(/from\s+['"]@\/([^'"]+)['"]/g)].map((m) => m[1]!)

describe('capas de FSD', () => {
  it('existen app, pages, entities y shared; ni widgets ni features', () => {
    expect(existsSync(join(SRC, 'entities', 'novela', 'index.ts'))).toBe(true)
    for (const capa of ['widgets', 'features', 'processes']) {
      expect(existsSync(join(SRC, capa)), capa).toBe(false)
    }
    expect(existsSync(join(SRC, 'shared', 'index.ts'))).toBe(false)
    expect(existsSync(join(SRC, 'assets'))).toBe(false)
    expect(existsSync(join(SRC, 'shared', 'assets'))).toBe(false)
  })

  it('cada segmento de shared y cada slice de pages expone su index.ts', () => {
    for (const segmento of ['api', 'ui', 'lib', 'config']) {
      expect(existsSync(join(SRC, 'shared', segmento, 'index.ts')), segmento).toBe(true)
    }
    for (const slice of ['library', 'commission', 'novel', 'gate', 'phase', 'reading', 'characters', 'cover', 'versions', 'print']) {
      expect(existsSync(join(SRC, 'pages', slice, 'index.ts')), slice).toBe(true)
    }
  })

  it('un módulo solo importa de capas estrictamente inferiores', () => {
    const orden = { app: 3, pages: 2, entities: 1, shared: 0 }
    const violaciones = fuentes().flatMap((f) =>
      importsDe(f.texto)
        .filter((destino) => orden[capaDe(destino)] >= orden[capaDe(f.ruta)] && capaDe(destino) !== 'shared')
        .filter((destino) => !(capaDe(f.ruta) === 'app' && capaDe(destino) === 'app'))
        .map((destino) => `${f.ruta} → ${destino}`),
    )
    expect(violaciones).toEqual([])
  })

  it('entities/novela no llama a la API: de shared/api solo importa tipos', () => {
    const culpables = fuentes()
      .filter((f) => capaDe(f.ruta) === 'entities')
      .filter((f) => /import\s+\{[^}]*\}\s+from\s+['"]@\/shared\/api['"]/.test(f.texto))
      .map((f) => f.ruta)
    expect(culpables).toEqual([])
  })

  it('dos slices de pages nunca se importan entre sí', () => {
    const cruces = fuentes()
      .filter((f) => capaDe(f.ruta) === 'pages')
      .flatMap((f) =>
        importsDe(f.texto)
          .filter((d) => capaDe(d) === 'pages' && sliceDe(d) !== sliceDe(f.ruta))
          .map((d) => `${f.ruta} → ${d}`),
      )
    expect(cruces).toEqual([])
  })

  it('nadie de fuera entra al interior de una slice ni de un segmento de shared', () => {
    const profundos = fuentes().flatMap((f) =>
      importsDe(f.texto)
        .filter((d) => d.split('/').length > (capaDe(d) === 'app' ? 99 : 2))
        .filter((d) => !(capaDe(d) === capaDe(f.ruta) && sliceDe(d) === sliceDe(f.ruta)))
        .map((d) => `${f.ruta} → ${d}`),
    )
    expect(profundos).toEqual([])
  })
})

describe('shared', () => {
  it('ninguna página mira un código HTTP', () => {
    const culpables = fuentes()
      .filter((f) => capaDe(f.ruta) === 'pages')
      .filter((f) => /\b(404|409)\b|\.status\b/.test(sinComentarios(f.texto)))
      .map((f) => f.ruta)
    expect(culpables).toEqual([])
  })

  it('ninguna página construye una URL de la aplicación con plantilla propia', () => {
    const culpables = fuentes()
      .filter((f) => capaDe(f.ruta) === 'pages')
      .filter((f) => /['"`]\/novelas/.test(sinComentarios(f.texto)))
      .map((f) => f.ruta)
    expect(culpables).toEqual([])
  })

  it('solo se leen VITE_API_URL y VITE_BASE_PATH, y solo en shared/config', () => {
    const lecturas = fuentes().flatMap((f) =>
      [...f.texto.matchAll(/import\.meta\.env\.(\w+)/g)].map((m) => `${f.ruta}:${m[1]}`),
    )
    expect(lecturas.sort()).toEqual(['shared/config/entorno.ts:VITE_API_URL', 'shared/config/entorno.ts:VITE_BASE_PATH'])
  })

  it('shared/ui no conoce los tipos de dominio de la API', () => {
    const culpables = fuentes()
      .filter((f) => f.ruta.startsWith('shared/ui/'))
      .filter((f) => /Capitulo(DelManifiesto)?\b|VersionDeNovela|FichaPersonaje/.test(f.texto.replace(/EnlaceCapitulo/g, '')))
      .map((f) => f.ruta)
    expect(culpables).toEqual([])
  })

  it('los tipos de transporte están generados, no escritos a mano', () => {
    const transporte = readFileSync(join(SRC, 'shared', 'api', 'transporte.ts'), 'utf-8')
    expect(transporte.startsWith('// GENERADO')).toBe(true)
  })
})

describe('configuración', () => {
  it('los alias son el mismo mapa en tsconfig.json y en vite.config.ts', () => {
    const tsconfig = JSON.parse(readFileSync(join(RAIZ, 'tsconfig.json'), 'utf-8'))
    const deTs = Object.fromEntries(
      Object.entries(tsconfig.compilerOptions.paths as Record<string, string[]>).map(([k, [v]]) => [
        k.replace('/*', ''),
        v!.replace('/*', ''),
      ]),
    )
    const deVite = Object.fromEntries(
      Object.entries(ALIAS).map(([k, v]) => [k, `src/${v.replaceAll('\\', '/').split('/src/')[1]}`]),
    )
    expect(deTs).toEqual(deVite)
  })

  it('no hay capa de internacionalización', () => {
    expect(fuentes().some((f) => /i18n|i18next|react-intl/.test(f.texto))).toBe(false)
  })
})
