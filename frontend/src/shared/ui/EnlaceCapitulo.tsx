import type { ReactNode } from 'react'
import { Link } from 'react-router'

interface Props {
  /** Una ruta de la aplicación, o un ancla (`#…`) dentro del mismo documento. */
  a: string
  children: ReactNode
}

/**
 * Un enlace a una parte de la obra. Con un ancla no pasa por el router, porque en el
 * documento de impresión no hay navegación que seguir: el enlace salta, también en el PDF.
 */
export function EnlaceCapitulo({ a, children }: Props) {
  if (a.startsWith('#')) {
    return (
      <a className="enlace-capitulo" href={a}>
        {children}
      </a>
    )
  }
  return (
    <Link className="enlace-capitulo" to={a}>
      {children}
    </Link>
  )
}
