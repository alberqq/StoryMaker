import type { HTMLAttributes, ReactNode } from 'react'

interface Props extends HTMLAttributes<HTMLElement> {
  titulo?: ReactNode
  children: ReactNode
}

export function Tarjeta({ titulo, children, className, ...resto }: Props) {
  return (
    <section className={['tarjeta', className].filter(Boolean).join(' ')} {...resto}>
      {titulo && <h2>{titulo}</h2>}
      {children}
    </section>
  )
}
