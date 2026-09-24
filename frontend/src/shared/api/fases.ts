// La salida de cada fase y el texto de un intento de capítulo.

import { cliente } from './cliente'
import type { components } from './transporte'

type Esquemas = components['schemas']

export type SalidaDeFase = Esquemas['SalidaDeFase']
export type SalidaEncargo = Esquemas['SalidaEncargo']
export type SalidaInvestigacion = Esquemas['SalidaInvestigacion']
export type SalidaTrama = Esquemas['SalidaTrama']
export type SalidaEscritura = Esquemas['SalidaEscritura']
export type SalidaPublicacion = Esquemas['SalidaPublicacion']
export type SalidaRegeneracion = Esquemas['SalidaRegeneracion']
export type Ejecucion = Esquemas['Ejecucion']
export type TextoDeIntento = Esquemas['TextoDeIntento']
export type Hecho = Esquemas['Hecho']

const seg = encodeURIComponent

/** `segmento` es el nombre castellano de la fase en la URL: `encargo`, `investigacion`… */
export const leerSalida = (id: string, segmento: string) =>
  cliente.get<SalidaDeFase>(`/novelas/${seg(id)}/fases/${seg(segmento)}`)

export const leerIntento = (id: string, capituloVersion: number) =>
  cliente.get<TextoDeIntento>(`/novelas/${seg(id)}/intentos/${capituloVersion}`)
