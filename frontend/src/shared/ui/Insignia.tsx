import type { ReactNode } from 'react'

export type Tono = 'azul' | 'ambar' | 'rojo' | 'verde' | 'gris' | 'acento'

interface Props {
  tono?: Tono
  /** Un punto de color delante del texto; latiendo si `vivo`. */
  punto?: boolean
  vivo?: boolean
  children: ReactNode
}

/** Una etiqueta de color con su texto. El color nunca va solo. */
export function Insignia({ tono = 'gris', punto = false, vivo = false, children }: Props) {
  return (
    <span className={`insignia insignia-${tono}`}>
      {punto && <span className={`insignia-punto${vivo ? ' vivo' : ''}`} aria-hidden="true" />}
      {children}
    </span>
  )
}
