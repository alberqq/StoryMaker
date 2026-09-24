import { continuar, desbloquear, leerPanel, leerRegistro, reintentar } from '@/shared/api'

export const cargarPanel = (id: string) => leerPanel(id)

export const cargarRegistro = (id: string, registro: string) => leerRegistro(id, registro)

/** Lanzan la CLI (continuar, reintentar) o rompen un cerrojo huérfano (desbloquear). */
export const lanzarContinuar = (id: string) => continuar(id)
export const lanzarReintento = (id: string) => reintentar(id)
export const romperCerrojo = (id: string) => desbloquear(id)
