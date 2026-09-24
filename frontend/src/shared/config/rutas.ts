// Los constructores de URL de la aplicación, y los patrones que el router monta.
//
// Una página que enlaza a otra pantalla llama a uno de estos en lugar de importar nada de
// la slice vecina (spec §3). Es la manera de que la ficha de personajes enlace al capítulo
// sin que `pages/characters` importe de `pages/reading`, que es lo que la segunda regla de
// FSD prohíbe. **Toda ruta de lectura lleva el número de versión**: un capítulo fuera de un
// manifiesto no identifica ningún texto.

export const PATRONES = {
  biblioteca: '/',
  encargo: '/encargo',
  novela: '/novelas/:id',
  gate: '/novelas/:id/gate',
  fase: '/novelas/:id/fases/:fase',
  indice: '/novelas/:id/v/:n',
  capitulo: '/novelas/:id/v/:n/capitulos/:k',
  portada: '/novelas/:id/v/:n/portada',
  personajes: '/novelas/:id/v/:n/personajes',
  versiones: '/novelas/:id/versiones',
  imprimir: '/novelas/:id/v/:n/imprimir',
} as const

const seg = (valor: string | number) => encodeURIComponent(String(valor))

export const rutaBiblioteca = () => '/'

export const rutaNovela = (id: string) => `/novelas/${seg(id)}`

export const rutaEncargo = () => '/encargo'

/** El panel de la novela, que es lo que abre `/novelas/:id`. */
export const rutaPanel = (id: string) => rutaNovela(id)

export const rutaGate = (id: string) => `${rutaNovela(id)}/gate`

/** `segmento` es el nombre castellano de la fase: `encargo`, `investigacion`… */
export const rutaFase = (id: string, segmento: string) => `${rutaNovela(id)}/fases/${seg(segmento)}`

export const rutaIndice = (id: string, n: number) => `${rutaNovela(id)}/v/${seg(n)}`

export const rutaCapitulo = (id: string, n: number, k: number) =>
  `${rutaIndice(id, n)}/capitulos/${seg(k)}`

export const rutaPortada = (id: string, n: number) => `${rutaIndice(id, n)}/portada`

export const rutaPersonajes = (id: string, n: number) => `${rutaIndice(id, n)}/personajes`

export const rutaImprimir = (id: string, n: number) => `${rutaIndice(id, n)}/imprimir`

export const rutaVersiones = (id: string) => `${rutaNovela(id)}/versiones`

/** El ancla de un capítulo dentro del documento de impresión. No navega: salta. */
export const anclaCapitulo = (k: number) => `#capitulo-${k}`

/** Lee un número de versión o de capítulo de la URL. `null` si no es un entero positivo. */
export function numeroDeRuta(valor: string | undefined): number | null {
  if (!valor || !/^\d+$/.test(valor)) return null
  const numero = Number(valor)
  return numero >= 1 ? numero : null
}
