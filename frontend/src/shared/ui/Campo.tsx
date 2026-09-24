import type { ReactNode } from 'react'

interface Props {
  etiqueta: string
  ayuda?: string
  error?: string
  obligatorio?: boolean
  ancho?: 'completo' | 'medio'
  children: ReactNode
}

/** Un campo de formulario con su etiqueta, su ayuda y su error debajo. */
export function Campo({ etiqueta, ayuda, error, obligatorio, ancho = 'medio', children }: Props) {
  return (
    <label className={`campo campo-${ancho}${error ? ' con-error' : ''}`}>
      <span className="campo-etiqueta">
        {etiqueta}
        {obligatorio && <span className="campo-obligatorio"> · obligatorio</span>}
      </span>
      {children}
      {error ? (
        <span className="campo-error" role="alert">
          {error}
        </span>
      ) : (
        ayuda && <span className="campo-ayuda">{ayuda}</span>
      )}
    </label>
  )
}
