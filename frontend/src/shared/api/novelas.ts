// Lo que la API sirve sobre una novela: la ficha con su historial y la petición de
// cambio del lector. El listado del directorio es el taller, en `seguimiento.ts`.

import { cliente } from './cliente'
import type { components } from './transporte'

type Esquemas = components['schemas']

export type FichaConHistorial = Esquemas['FichaConHistorial']
export type VersionPublicada = Esquemas['VersionPublicada']
export type CuerpoDeCambio = Esquemas['CuerpoDeCambio']
export type AcuseDeCambio = Esquemas['AcuseDeCambio']

const seg = encodeURIComponent

export const leerFicha = (id: string) => cliente.get<FichaConHistorial>(`/novelas/${seg(id)}`)

export const pedirCambio = (id: string, cuerpo: CuerpoDeCambio) =>
  cliente.post<AcuseDeCambio>(`/novelas/${seg(id)}/cambios`, cuerpo)
