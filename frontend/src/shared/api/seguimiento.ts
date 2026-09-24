// El seguimiento: el taller, el panel de una novela y su gate. Todo se recalcula en el
// backend en cada consulta; aquí solo se pide.

import { cliente } from './cliente'
import type { components } from './transporte'

type Esquemas = components['schemas']

export type TarjetaNovela = Esquemas['TarjetaNovela']
export type Panel = Esquemas['Panel']
export type FaseDelPanel = Esquemas['FaseDelPanel']
export type CapituloDelPanel = Esquemas['CapituloDelPanel']
export type Suceso = Esquemas['Suceso']
export type GatePendiente = Esquemas['GatePendiente']
export type GateDeNovela = Esquemas['GateDeNovela']
export type FilaEditable = Esquemas['FilaEditable']
export type Conversacion = Esquemas['Conversacion']
export type RevisionDeLaTrama = Esquemas['RevisionDeLaTrama']
export type EstadoDeNovela = TarjetaNovela['estado']
export type EstadoDeFase = FaseDelPanel['estado']

const seg = encodeURIComponent

export const leerTaller = () => cliente.get<TarjetaNovela[]>('/novelas')

export const leerPanel = (id: string) => cliente.get<Panel>(`/novelas/${seg(id)}/panel`)

export const leerGate = (id: string) => cliente.get<GateDeNovela>(`/novelas/${seg(id)}/gate`)

export const leerRegistro = (id: string, registro: string) =>
  cliente.texto(`/novelas/${seg(id)}/registros/${seg(registro)}`)
