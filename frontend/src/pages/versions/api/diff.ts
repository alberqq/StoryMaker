import { leerDiferencias } from '@/shared/api'

/** Qué capítulos cambian entre dos manifiestos. Es un `JOIN` en el backend, no un diff de texto. */
export const cargarDiff = (id: string, a: number, b: number) => leerDiferencias(id, a, b)
