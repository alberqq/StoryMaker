// El nombre y el color de cada estado de spec §5.2. El estado lo calcula el backend: aquí
// solo se nombra. El color tiene significado fijo —azul trabaja, ámbar espera al Autor,
// rojo está detenido, verde ha terminado— y nunca va sin su texto.

import type { EstadoDeFase, EstadoDeNovela } from '@/shared/api'
import type { Tono } from '@/shared/ui'

interface Presentacion {
  texto: string
  tono: Tono
  vivo?: boolean
}

export const ESTADOS_DE_NOVELA: Record<EstadoDeNovela, Presentacion> = {
  en_marcha: { texto: 'En marcha', tono: 'azul', vivo: true },
  arrancando: { texto: 'Arrancando', tono: 'azul', vivo: true },
  esperando_autor: { texto: 'Espera tu decisión', tono: 'ambar' },
  aparcada: { texto: 'Aparcada', tono: 'ambar' },
  detenida: { texto: 'Detenida', tono: 'rojo' },
  fallida: { texto: 'Parada por un fallo', tono: 'rojo' },
  terminada: { texto: 'Terminada', tono: 'verde' },
  en_pausa: { texto: 'En pausa', tono: 'gris' },
}

export const ESTADOS_DE_FASE: Record<EstadoDeFase, Presentacion> = {
  pendiente: { texto: 'Pendiente', tono: 'gris' },
  en_curso: { texto: 'En curso', tono: 'azul', vivo: true },
  esperando_gate: { texto: 'Espera tu decisión', tono: 'ambar' },
  completada: { texto: 'Completada', tono: 'verde' },
  fallida: { texto: 'Fallida', tono: 'rojo' },
  aparcada: { texto: 'Aparcada', tono: 'ambar' },
  abortada: { texto: 'Abortada', tono: 'rojo' },
}

/** Si la novela trabaja ahora mismo: el panel lo usa para decir qué está haciendo. */
export const trabaja = (estado: EstadoDeNovela) => estado === 'en_marcha' || estado === 'arrancando'
