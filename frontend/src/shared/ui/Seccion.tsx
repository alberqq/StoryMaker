import type { ReactNode } from 'react'

interface Props {
  titulo: ReactNode
  extra?: ReactNode
  /** Plegable: se abre y se cierra, y empieza cerrada si `plegada`. */
  plegable?: boolean
  plegada?: boolean
  children: ReactNode
}

/** Un bloque del panel, con su título y, si hace falta, plegable. */
export function Seccion({ titulo, extra, plegable = false, plegada = false, children }: Props) {
  if (plegable) {
    return (
      <details className="seccion" open={!plegada}>
        <summary className="seccion-cabecera">
          <h2>{titulo}</h2>
          {extra}
        </summary>
        <div className="seccion-cuerpo">{children}</div>
      </details>
    )
  }
  return (
    <section className="seccion">
      <div className="seccion-cabecera">
        <h2>{titulo}</h2>
        {extra}
      </div>
      <div className="seccion-cuerpo">{children}</div>
    </section>
  )
}
