import type { ReactNode } from 'react'

interface Props {
  columnas: string[]
  children: ReactNode
}

export function Tabla({ columnas, children }: Props) {
  return (
    <table className="tabla">
      <thead>
        <tr>
          {columnas.map((c) => (
            <th key={c}>{c}</th>
          ))}
        </tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
  )
}
