import type { GateDeNovela } from '@/shared/api'

export type CandidatoDeRegeneracion = NonNullable<GateDeNovela['peticion']>['candidatos'][number]

/** Se puede elegir si la petición guardó su fila; las registradas antes no la llevan. */
export const elegible = (c: CandidatoDeRegeneracion) => c.objeto != null && c.fila_id != null && c.campo != null

/**
 * El comentario con el que se aprueba el gate de Regeneración: `<objeto>:<fila_id>
 * <campo>=<valor>`, que el backend aplica a esa fila sin volver a buscar (spec §4.4).
 *
 * Vacío si no hay candidato elegible o el valor no cambia: un comentario sin esa forma deja
 * pasar la regeneración sin tocar nada, que es lo que el Autor pidió al no cambiar nada.
 */
export function comentarioDeEleccion(candidato: CandidatoDeRegeneracion | undefined, valor: string): string {
  const nuevo = valor.trim()
  if (!candidato || !elegible(candidato) || !nuevo || nuevo === candidato.valor.trim()) return ''
  return `${candidato.objeto}:${candidato.fila_id} ${candidato.campo}=${nuevo}`
}
