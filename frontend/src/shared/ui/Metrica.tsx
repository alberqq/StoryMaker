import type { ReactNode } from 'react'

/** Una cifra con su etiqueta. */
export function Metrica({ etiqueta, valor, detalle }: { etiqueta: string; valor: ReactNode; detalle?: ReactNode }) {
  return (
    <div className="metrica">
      <span className="metrica-etiqueta">{etiqueta}</span>
      <span className="metrica-valor">{valor}</span>
      {detalle && <span className="metrica-detalle">{detalle}</span>}
    </div>
  )
}
