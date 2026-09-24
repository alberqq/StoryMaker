import { leerIntento, leerSalida } from '@/shared/api'

export const cargarSalida = (id: string, segmento: string) => leerSalida(id, segmento)

export const cargarIntento = (id: string, capituloVersion: number) => leerIntento(id, capituloVersion)
