import { Link } from 'react-router'

interface Pestana {
  a: string
  texto: string
  activa: boolean
  nota?: string
}

/** Pestañas que son enlaces: cada una tiene su URL y se puede compartir. */
export function Pestanas({ pestanas, etiqueta }: { pestanas: Pestana[]; etiqueta: string }) {
  return (
    <nav className="pestanas" aria-label={etiqueta}>
      {pestanas.map((p) => (
        <Link key={p.a} to={p.a} className={p.activa ? 'activa' : ''} aria-current={p.activa ? 'page' : undefined}>
          {p.texto}
          {p.nota && <span className="pestana-nota">{p.nota}</span>}
        </Link>
      ))}
    </nav>
  )
}
