import type { Tono } from './Insignia'

/** Una barra de progreso con su valor accesible. */
export function Progreso({ valor, max, tono = 'acento', etiqueta }: { valor: number; max: number; tono?: Tono; etiqueta: string }) {
  const porcentaje = max > 0 ? Math.min(100, Math.round((valor / max) * 100)) : 0
  return (
    <div className="progreso" role="progressbar" aria-label={etiqueta} aria-valuemin={0} aria-valuemax={max} aria-valuenow={valor}>
      <div className={`progreso-barra progreso-${tono}`} style={{ width: `${porcentaje}%` }} />
    </div>
  )
}
