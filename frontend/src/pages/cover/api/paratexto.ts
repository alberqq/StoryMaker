import { leerVersion } from '@/shared/api'

/** El bloque de paratexto de la versión: título, homenajeado, ocasión y Licencias. */
export const cargarParatexto = (id: string, n: number) =>
  leerVersion(id, n).then((version) => version.paratexto)
