// La operación de una novela. Lo que ejecuta el grafo lo lanza el backend como proceso
// aparte y responde en el acto: estas funciones resuelven con «lanzada», no con el resultado.

import { cliente } from './cliente'
import type { components } from './transporte'

type Esquemas = components['schemas']

export type Ejemplo = Esquemas['Ejemplo']
export type Validacion = Esquemas['Validacion']
export type ErrorDeCampo = Esquemas['ErrorDeCampo']
export type Lanzada = Esquemas['Lanzada']
export type Hecha = Esquemas['Hecha']
export type CuerpoDeEdicion = Esquemas['CuerpoDeEdicion']
export type Encargo = Record<string, unknown>

const seg = encodeURIComponent

export const leerEjemplos = () => cliente.get<Ejemplo[]>('/ejemplos')

export const validarEncargo = (encargo: Encargo) =>
  cliente.post<Validacion>('/encargos/validar', { encargo })

export type ModoDeInvestigacion = 'estandar' | 'exhaustiva'

export const encargar = (encargo: Encargo, nombre: string, batch: boolean, investigacion: ModoDeInvestigacion) =>
  cliente.post<Lanzada>('/novelas', { encargo, nombre, batch, investigacion })

export const continuar = (id: string) => cliente.post<Lanzada>(`/novelas/${seg(id)}/continuar`, {})

export const decidir = (id: string, decision: 'aprobar' | 'rehacer' | 'abortar', comentario = '') =>
  cliente.post<Lanzada>(`/novelas/${seg(id)}/decisiones`, { decision, comentario })

export const reintentar = (id: string) => cliente.post<Lanzada>(`/novelas/${seg(id)}/reintentar`, {})

export const desbloquear = (id: string) => cliente.post<Hecha>(`/novelas/${seg(id)}/desbloquear`, {})

export const editarFila = (id: string, edicion: CuerpoDeEdicion) =>
  cliente.post<Hecha>(`/novelas/${seg(id)}/ediciones`, edicion)

/** Quita un hecho del corpus antes del sello. Se escribe en el acto y queda trazado. */
export const descartarHecho = (id: string, hecho: number, motivo = '') =>
  cliente.post<Hecha>(`/novelas/${seg(id)}/hechos/${hecho}/descartar`, { motivo })
