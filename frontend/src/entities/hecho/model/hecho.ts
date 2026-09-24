import type { Hecho } from '@/shared/api'
import type { Tono } from '@/shared/ui'

export const DIMENSIONES: Record<string, string> = {
  cronologia: 'Cronología',
  lugar: 'Lugar',
  cultura_material: 'Cultura material',
  lenguaje: 'Lenguaje',
  mentalidad: 'Mentalidad',
  estructura_social: 'Estructura social',
}

/** La firmeza es la única etiqueta de un hecho: lo que el escritor verá de él. */
export const TONO_DE_LA_FIRMEZA: Record<string, Tono> = {
  documentado: 'verde',
  debatido: 'ambar',
  inferido: 'gris',
  desconocido: 'rojo',
  // Ni bueno ni malo: es una licencia.
  inventado: 'azul',
}

/**
 * Lo que el verificador no respaldó, y lo que respaldó con un añadido que la cita no dice
 * y que sigue en el enunciado: los hechos bajo los que se enseña su motivo. Lo decide el
 * servidor; aquí solo se lee lo que sirve.
 */
export function porRevisar(hecho: Pick<Hecho, 'respaldo' | 'no_lo_dice_la_cita'>): boolean {
  return hecho.respaldo === 'no_respaldado' || Boolean(hecho.no_lo_dice_la_cita)
}
