import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router'
import logo from './logo.png'

interface Enlace {
  a: string
  texto: string
}

interface Props {
  enlaces: Enlace[]
  children: ReactNode
}

/** El marco de la aplicación: la barra persistente y el contenido. La impresión no lo usa. */
export function Marco({ enlaces, children }: Props) {
  return (
    <div className="marco">
      <header className="barra">
        <Link to="/" className="barra-marca" aria-label="StoryMaker, al taller">
          <img className="barra-logo" src={logo} alt="" width={30} height={30} />
          <span>StoryMaker</span>
        </Link>
        <nav className="barra-enlaces" aria-label="Navegación principal">
          {enlaces.map((e) => (
            <NavLink key={e.a} to={e.a} end className={({ isActive }) => (isActive ? 'activo' : '')}>
              {e.texto}
            </NavLink>
          ))}
        </nav>
      </header>
      <main>{children}</main>
    </div>
  )
}
