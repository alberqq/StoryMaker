import type { ReactNode } from 'react'

interface Props {
  titulo: string
  /** Enlaces propios de la pantalla, sobre el título. */
  navegacion?: ReactNode
  children: ReactNode
}

/** Una pantalla del registro de libro: lector, portada, personajes, historial. */
export function Pagina({ titulo, navegacion, children }: Props) {
  return (
    <div className="contenido">
      <article className="libro pagina">
        {navegacion && <nav className="navegacion-libro navegacion">{navegacion}</nav>}
        <h1>{titulo}</h1>
        {children}
      </article>
    </div>
  )
}
