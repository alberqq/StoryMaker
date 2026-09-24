import { Link } from 'react-router'
import { InsigniaEstado } from '@/entities/novela'
import type { TarjetaNovela } from '@/shared/api'
import { rutaGate, rutaIndice, rutaPanel } from '@/shared/config'
import { formatearDinero, formatearHace } from '@/shared/lib'
import { Tabla } from '@/shared/ui'

/**
 * Las novelas publicadas, debajo del tablero (spec §4.1): son las que más se acumulan, y
 * como columna estiraban el tablero hacia la derecha. Nada se decide arrastrándolas, así que
 * una fila por novela basta.
 */
export function Publicadas({ novelas }: { novelas: TarjetaNovela[] }) {
  return (
    <section className="publicadas" aria-label="Publicadas">
      <header className="columna-cabecera">
        <h2>Publicadas</h2>
        <span className="columna-cuenta">{novelas.length}</span>
      </header>
      <div className="publicadas-tabla">
        <Tabla columnas={['Novela', 'Estado', 'Versiones', 'Gastado', 'Actividad', '']}>
          {novelas.map((n) => (
            <tr key={n.nombre} data-novela={n.nombre}>
              <td>
                <Link to={rutaPanel(n.nombre)}>
                  <strong>{n.titulo}</strong>
                </Link>
                {n.homenajeado && <div className="tarjeta-homenajeado">Para {n.homenajeado}</div>}
              </td>
              <td>
                <InsigniaEstado estado={n.estado} />
              </td>
              <td className="numero">{n.versiones}</td>
              <td className="numero">{formatearDinero(n.coste_usd)}</td>
              <td className="nota">{n.actualizada ? formatearHace(n.actualizada) : '—'}</td>
              <td className="publicadas-acciones">
                {n.gate?.fase === 'regeneration' && <Link to={rutaGate(n.nombre)}>Decidir el cambio</Link>}
                {n.versiones > 0 && <Link to={rutaIndice(n.nombre, n.versiones)}>Leer v{n.versiones} →</Link>}
              </td>
            </tr>
          ))}
        </Tabla>
      </div>
    </section>
  )
}
