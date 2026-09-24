import { leerCapitulo } from '@/shared/api'

/** El texto del capítulo tal como esa versión lo fija. */
export const cargarCapitulo = (id: string, n: number, k: number) => leerCapitulo(id, n, k)
