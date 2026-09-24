import { decidir, leerGate } from '@/shared/api'
import type { Decision } from '../model/columnas'

/** El resumen del gate que se enseña antes de confirmar. */
export const cargarResumenDelGate = (id: string) => leerGate(id)

/** La decisión confirmada. El backend lanza `storymaker decidir` y responde en el acto. */
export const confirmarDecision = (id: string, decision: Decision, comentario: string) =>
  decidir(id, decision, comentario)
