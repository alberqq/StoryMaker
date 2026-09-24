import { leerFicha } from '@/shared/api'

/** La ficha de la novela con sus versiones publicadas, su fecha y su puntuación. */
export const cargarHistorial = (id: string) => leerFicha(id)
