import type { Diferencias } from '@/shared/api'

/**
 * Los números de los capítulos que cambian respecto de la versión anterior.
 *
 * Sale del endpoint de diff —un `JOIN` entre dos manifiestos, ya resuelto en el backend— y
 * no de comparar textos en el cliente. Sin versión anterior, no hay nada que marcar.
 */
export function capitulosCambiados(diff: Diferencias | null): ReadonlySet<number> {
  if (!diff) return new Set()
  return new Set(diff.cambios.filter((c) => c.estado !== 'igual').map((c) => c.capitulo))
}
