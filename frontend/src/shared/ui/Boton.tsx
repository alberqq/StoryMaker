import type { ButtonHTMLAttributes } from 'react'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: 'primario' | 'secundario' | 'fantasma' | 'peligro'
  tamano?: 'normal' | 'pequeno'
}

export function Boton({
  className,
  type = 'button',
  variante = 'primario',
  tamano = 'normal',
  ...resto
}: Props) {
  return (
    <button
      type={type}
      className={['boton', `boton-${variante}`, tamano === 'pequeno' ? 'boton-pequeno' : '', className]
        .filter(Boolean)
        .join(' ')}
      {...resto}
    />
  )
}
