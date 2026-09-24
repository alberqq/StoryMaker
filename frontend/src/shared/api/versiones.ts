// Lo que la API sirve sobre una versión: el manifiesto con su paratexto, el texto de un
// capítulo tal como esa versión lo fija, las fichas y el diff entre dos manifiestos.

import { API_URL } from '@/shared/config'
import { cliente } from './cliente'
import type { components } from './transporte'

type Esquemas = components['schemas']

export type VersionDeNovela = Esquemas['VersionDeNovela']
export type CapituloDelManifiesto = Esquemas['CapituloDelManifiesto']
export type Paratexto = Esquemas['Paratexto']
export type Licencia = Esquemas['Licencia']
export type TextoDeCapitulo = Esquemas['TextoDeCapitulo']
export type Fichas = Esquemas['Fichas']
export type FichaPersonaje = Esquemas['FichaPersonaje']
export type FichaEscenario = Esquemas['FichaEscenario']
export type Diferencias = Esquemas['Diferencias']

const version = (id: string, n: number) => `/novelas/${encodeURIComponent(id)}/versiones/${n}`

export const leerVersion = (id: string, n: number) => cliente.get<VersionDeNovela>(version(id, n))

export const leerCapitulo = (id: string, n: number, k: number) =>
  cliente.get<TextoDeCapitulo>(`${version(id, n)}/capitulos/${k}`)

export const leerFichas = (id: string, n: number) =>
  cliente.get<Fichas>(`${version(id, n)}/personajes`)

/**
 * La dirección de descarga del PDF de una versión. No es una petición del cliente sino un
 * enlace que abre el navegador, pero su forma vive aquí, junto a las demás rutas de la API.
 */
export const urlDelPdf = (id: string, n: number) => `${API_URL}/api${version(id, n)}/pdf`

export const leerDiferencias = (id: string, a: number, b: number) =>
  cliente.get<Diferencias>(`${version(id, a)}/diff/${b}`)
