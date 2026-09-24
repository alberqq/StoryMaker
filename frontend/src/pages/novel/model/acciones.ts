// Qué acciones admite cada estado de una novela (spec §5.3). Una acción que el backend
// rechazaría no se ofrece: el panel no enseña botones que no sirven.

import type { Panel } from '@/shared/api'

export type Accion = 'decidir' | 'continuar' | 'reintentar' | 'desbloquear'

export function accionesDe(panel: Pick<Panel, 'estado' | 'fase' | 'gate'>): Accion[] {
  switch (panel.estado) {
    case 'esperando_autor':
      return ['decidir']
    case 'detenida':
      return ['desbloquear']
    case 'fallida':
      return panel.fase === 'writing' ? ['reintentar', 'continuar'] : ['continuar']
    case 'aparcada':
    case 'en_pausa':
      return ['continuar']
    default:
      return []
  }
}

/** Las que no se deshacen piden confirmación. */
export const pideConfirmacion = (accion: Accion) => accion === 'desbloquear'
