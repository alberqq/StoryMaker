// Las columnas del tablero, qué novelas van al listado de publicadas y las reglas del
// arrastre (spec §4.1).
//
// Una tarjeta solo se arrastra si su novela espera en un gate que no sea el de Regeneración,
// y solo se suelta en dos sitios: la columna siguiente, que es aprobar, y la suya, que es
// rehacer. El tablero no mueve una novela a una fase que el grafo no le daría.

import type { TarjetaNovela } from '@/shared/api'

export interface Columna {
  clave: string
  titulo: string
}

export const COLUMNAS: readonly Columna[] = [
  { clave: 'intake', titulo: 'Encargo' },
  { clave: 'investigation', titulo: 'Investigación' },
  { clave: 'plotting', titulo: 'Trama' },
  { clave: 'writing', titulo: 'Escritura' },
  { clave: 'publication', titulo: 'Publicación' },
]

export type Decision = 'aprobar' | 'rehacer'

const indice = (clave: string) => COLUMNAS.findIndex((c) => c.clave === clave)

/**
 * Si la novela va en el listado de publicadas, bajo el tablero, y no en una columna: las
 * publicadas sin trabajo en marcha y las que están en Regeneración.
 */
export function enListado(tarjeta: TarjetaNovela): boolean {
  if (tarjeta.gate && tarjeta.gate.fase !== 'regeneration') return false
  if (tarjeta.fase === 'regeneration') return true
  const trabajando = tarjeta.estado === 'en_marcha' || tarjeta.estado === 'arrancando'
  return tarjeta.fase === 'publication' && tarjeta.versiones > 0 && !trabajando
}

/** La columna de una novela en curso: la de su gate si espera, si no la de su fase. */
export function columnaDe(tarjeta: TarjetaNovela): string {
  if (tarjeta.gate && tarjeta.gate.fase !== 'regeneration') return tarjeta.gate.fase
  return indice(tarjeta.fase) >= 0 ? tarjeta.fase : 'intake'
}

export function arrastrable(tarjeta: TarjetaNovela): boolean {
  return tarjeta.estado === 'esperando_autor' && !!tarjeta.gate && tarjeta.gate.fase !== 'regeneration'
}

/** Qué decisión propone soltar la tarjeta en una columna, o `null` si ahí no se puede. */
export function decisionAlSoltar(tarjeta: TarjetaNovela, destino: string): Decision | null {
  if (!arrastrable(tarjeta)) return null
  const origen = columnaDe(tarjeta)
  if (destino === origen) return 'rehacer'
  if (indice(destino) === indice(origen) + 1) return 'aprobar'
  return null
}

/** La columna a la que llevaría aprobar, para nombrarla en el diálogo y en el botón. */
export function columnaSiguiente(tarjeta: TarjetaNovela): Columna | undefined {
  return COLUMNAS[indice(columnaDe(tarjeta)) + 1]
}
