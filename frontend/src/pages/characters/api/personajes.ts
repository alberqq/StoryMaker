import { leerFichas } from '@/shared/api'

/** Las fichas de la versión, con los capítulos de ese manifiesto en que aparece cada una. */
export const cargarFichas = (id: string, n: number) => leerFichas(id, n)
