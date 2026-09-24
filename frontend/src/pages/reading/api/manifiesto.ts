import { leerDiferencias, leerVersion } from '@/shared/api'
import { capitulosCambiados } from '../model/cambiados'

/** El manifiesto de la versión y qué capítulos cambian. Sin anterior, no se pide el diff. */
export async function cargarIndice(id: string, n: number) {
  const version = await leerVersion(id, n)
  const diff = version.anterior != null ? await leerDiferencias(id, version.anterior, n) : null
  return { version, cambiados: capitulosCambiados(diff) }
}
