import { pedirCambio } from '@/shared/api'

export interface Peticion {
  texto: string
  fragmento: string
  capitulo: number
  version: number
}

/** Registra la petición. No resuelve nada: abre la Fase 6, que se detiene en su gate. */
export const enviarPeticion = (id: string, peticion: Peticion) => pedirCambio(id, peticion)
