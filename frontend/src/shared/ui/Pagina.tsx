import type { CSSProperties, ReactNode } from 'react'
import { estiloDeLectura, usePreferenciasDeLectura } from '@/shared/lib'
import { AjustesDeLectura } from './AjustesDeLectura'

interface Props {
  titulo: string
  /** Enlaces propios de la pantalla, sobre el título. */
  navegacion?: ReactNode
  children: ReactNode
}

/**
 * Una pantalla del registro de libro: lector, portada, personajes, historial. Lleva la
 * pestaña «Aa» de los ajustes de lectura, que aplica el tamaño y la fuente como variables
 * CSS del libro (spec §4.6).
 */
export function Pagina({ titulo, navegacion, children }: Props) {
  const { preferencias, cambiar } = usePreferenciasDeLectura()
  return (
    <div className="contenido">
      <article
        className="libro pagina"
        style={estiloDeLectura(preferencias) as CSSProperties}
        data-tema-libro={preferencias.temaLibro === 'app' ? undefined : preferencias.temaLibro}
      >
        <div className="cabecera-libro">
          {navegacion ? <nav className="navegacion-libro navegacion">{navegacion}</nav> : <span />}
          <AjustesDeLectura preferencias={preferencias} onCambiar={cambiar} />
        </div>
        <h1>{titulo}</h1>
        {children}
      </article>
    </div>
  )
}
