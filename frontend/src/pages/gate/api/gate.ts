import {
  type CuerpoDeEdicion,
  decidir,
  editarFila,
  type GateDeNovela,
  leerGate,
  leerPanel,
  NoEncontrado,
  type Panel,
} from '@/shared/api'

export interface EstadoDelGate {
  /** El gate que espera, o `null` si ahora mismo no hay ninguno. */
  gate: GateDeNovela | null
  /** El estado de la novela: sin gate, dice si está trabajando y en qué. */
  novela: Pick<Panel, 'estado' | 'fase' | 'trabajando_en'>
}

/**
 * El gate y el estado de la novela a la vez. Entre una ronda de la entrevista y la
 * siguiente no hay gate —la novela está trabajando—, y la pantalla tiene que poder decirlo.
 */
export async function cargarGate(id: string): Promise<EstadoDelGate> {
  const [gate, panel] = await Promise.all([
    leerGate(id).catch((error: unknown) => {
      if (error instanceof NoEncontrado) return null
      throw error
    }),
    leerPanel(id),
  ])
  return { gate, novela: { estado: panel.estado, fase: panel.fase, trabajando_en: panel.trabajando_en } }
}

/** Lanza `storymaker decidir`. La interfaz nunca envía `editar` (arq. §16.5). */
export const enviarDecision = (id: string, decision: 'aprobar' | 'rehacer' | 'abortar', comentario: string) =>
  decidir(id, decision, comentario)

/** La edición humana directa de una fila: se escribe en el acto, sin lanzar nada. */
export const guardarEdicion = (id: string, edicion: CuerpoDeEdicion) => editarFila(id, edicion)
