import { leerCapitulo, leerDiferencias, leerFichas, leerVersion } from '@/shared/api'

/**
 * La versión entera, para imprimirla en un solo documento.
 *
 * Todas las peticiones salen de `shared/api`, y eso es lo que permite que `render_visual`,
 * dentro de `PublishVersion`, sirva la versión candidata interceptándolas (spec §6).
 */
export async function cargarDocumento(id: string, n: number) {
  const version = await leerVersion(id, n)
  const [capitulos, fichas, novedades] = await Promise.all([
    Promise.all(version.capitulos.map((c) => leerCapitulo(id, n, c.numero))),
    leerFichas(id, n),
    version.anterior != null ? leerDiferencias(id, version.anterior, n) : Promise.resolve(null),
  ])
  return { version, capitulos, fichas, novedades }
}

export type Documento = Awaited<ReturnType<typeof cargarDocumento>>
