import { type ReactNode, useEffect, useRef } from 'react'

interface Props {
  abierto: boolean
  titulo: string
  onCerrar: () => void
  acciones?: ReactNode
  children: ReactNode
}

/** Un diálogo modal: atrapa el foco, se cierra con Escape y con el velo. */
export function Dialogo({ abierto, titulo, onCerrar, acciones, children }: Props) {
  const caja = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!abierto) return
    const anterior = document.activeElement as HTMLElement | null
    const enfocables = () =>
      Array.from(
        caja.current?.querySelectorAll<HTMLElement>(
          'button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select, a[href]',
        ) ?? [],
      )
    enfocables()[0]?.focus()
    const teclado = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCerrar()
      if (e.key !== 'Tab') return
      const lista = enfocables()
      const primero = lista[0]
      const ultimo = lista[lista.length - 1]
      if (!primero || !ultimo) return
      if (e.shiftKey && document.activeElement === primero) {
        e.preventDefault()
        ultimo.focus()
      } else if (!e.shiftKey && document.activeElement === ultimo) {
        e.preventDefault()
        primero.focus()
      }
    }
    document.addEventListener('keydown', teclado)
    return () => {
      document.removeEventListener('keydown', teclado)
      anterior?.focus?.()
    }
  }, [abierto, onCerrar])

  if (!abierto) return null
  return (
    <div className="velo" onMouseDown={(e) => e.target === e.currentTarget && onCerrar()}>
      <div className="dialogo" role="dialog" aria-modal="true" aria-label={titulo} ref={caja}>
        <h2>{titulo}</h2>
        <div className="dialogo-cuerpo">{children}</div>
        {acciones && <div className="dialogo-acciones">{acciones}</div>}
      </div>
    </div>
  )
}
