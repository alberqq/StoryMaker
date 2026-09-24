import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { tipoDeError } from '@/shared/api'
import { rutaBiblioteca } from '@/shared/config'
import { Boton } from './Boton'

// Los tres estados que toda pantalla enseña mientras no tiene sus datos. Son parte del
// contrato (spec §4): ninguna pantalla se queda en blanco.

export function EstadoCarga({ que = 'la novela' }: { que?: string }) {
  return (
    <p className="estado estado-carga" role="status">
      Cargando {que}…
    </p>
  )
}

export function EstadoVacio({ children }: { children: ReactNode }) {
  return <p className="estado estado-vacio">{children}</p>
}

/** Lo que no existe: nunca una página en blanco, siempre con vuelta al listado. */
export function NoExiste({ detalle }: { detalle?: string }) {
  return (
    <div className="estado estado-error" role="alert">
      <h2>No existe</h2>
      <p>{detalle ?? 'Esa novela, versión o capítulo no existe.'}</p>
      <Link to={rutaBiblioteca()}>Volver al taller</Link>
    </div>
  )
}

interface PropsError {
  error: unknown
  onReintentar?: () => void
}

export function EstadoError({ error, onReintentar }: PropsError) {
  const tipo = tipoDeError(error)
  if (tipo === 'no_encontrado') return <NoExiste />
  const [titulo, texto] =
    tipo === 'sin_respuesta'
      ? ['El servidor no responde', 'No se ha podido hablar con la API de StoryMaker.']
      : tipo === 'ocupada'
        ? ['Hay una ejecución en curso', 'La novela está ocupada. Inténtalo más tarde.']
        : tipo === 'rechazada'
          ? ['No se puede hacer ahora', error instanceof Error ? error.message : '']
          : ['Algo ha fallado en el servidor', error instanceof Error ? error.message : '']
  return (
    <div className="estado estado-error" role="alert">
      <h2>{titulo}</h2>
      <p>{texto}</p>
      {onReintentar && <Boton onClick={onReintentar}>Reintentar</Boton>}
    </div>
  )
}
