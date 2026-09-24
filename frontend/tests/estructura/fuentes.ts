// Lectura de `frontend/src` para las pruebas de repositorio.

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

export const RAIZ = resolve(fileURLToPath(new URL('../..', import.meta.url)))
export const SRC = join(RAIZ, 'src')

export interface Fuente {
  ruta: string
  texto: string
}

function recorrer(dir: string): string[] {
  return readdirSync(dir).flatMap((nombre) => {
    const ruta = join(dir, nombre)
    return statSync(ruta).isDirectory() ? recorrer(ruta) : [ruta]
  })
}

/** Todo `.ts`/`.tsx` de `src`, con su ruta relativa a `src` y con barras normales. */
export function fuentes(): Fuente[] {
  return recorrer(SRC)
    .filter((r) => /\.tsx?$/.test(r))
    .map((r) => ({ ruta: relative(SRC, r).replaceAll('\\', '/'), texto: readFileSync(r, 'utf-8') }))
}

/** El código sin comentarios, para no confundir la prosa que explica una regla con su violación. */
export const sinComentarios = (texto: string) =>
  texto.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/.*$/gm, '$1')
