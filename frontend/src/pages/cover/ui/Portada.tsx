import { Link, useParams } from 'react-router'
import { EstadoCarga, EstadoError, NoExiste, Pagina } from '@/shared/ui'
import { numeroDeRuta, rutaIndice } from '@/shared/config'
import { useCarga } from '@/shared/lib'
import { cargarParatexto } from '../api/paratexto'

export function Portada() {
  const params = useParams()
  const id = params.id ?? ''
  const n = numeroDeRuta(params.n)
  if (n == null)
    return (
      <Pagina titulo="No existe">
        <NoExiste />
      </Pagina>
    )
  return <PortadaDeVersion id={id} n={n} />
}

/** «con motivo de su jubilación»; si la ocasión ya lleva su «su», no se le añade otro. */
const conMotivoDe = (ocasion: string) =>
  /\bsu\b/.test(ocasion) ? `con motivo de ${ocasion}` : `con motivo de su ${ocasion}`

/**
 * Título, dedicatoria y nota del autor: el paratexto de la obra (spec §4.4). La nota declara
 * las Licencias que la novela se tomó; sin ninguna declarada se omite, y no es un fallo.
 */
function PortadaDeVersion({ id, n }: { id: string; n: number }) {
  const carga = useCarga(() => cargarParatexto(id, n), [id, n])
  const volver = <Link to={rutaIndice(id, n)}>Índice</Link>

  if (carga.estado === 'cargando')
    return (
      <Pagina titulo="Portada" navegacion={volver}>
        <EstadoCarga que="la portada" />
      </Pagina>
    )
  if (carga.estado === 'error')
    return (
      <Pagina titulo="Portada" navegacion={volver}>
        <EstadoError error={carga.error} onReintentar={carga.reintentar} />
      </Pagina>
    )

  const paratexto = carga.datos
  return (
    <Pagina titulo="Portada" navegacion={volver}>
      <section className="portada" data-render="portada">
        <p className="titulo-obra">{paratexto.titulo}</p>
        {paratexto.homenajeado && (
          <div className="dedicatoria">
            <p>Para {paratexto.homenajeado}</p>
            {paratexto.ocasion && <p>{conMotivoDe(paratexto.ocasion)}</p>}
          </div>
        )}
      </section>
      {paratexto.licencias.length > 0 && (
        <section className="nota-del-autor">
          <h2>Nota del autor</h2>
          <p>
            Esta novela es ficción sobre un fondo histórico. Estas son las libertades que se ha
            tomado con los hechos:
          </p>
          <ul>
            {paratexto.licencias.map((l, i) => (
              <li key={i}>
                {l.alteracion}. <span className="nota">{l.justificacion}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </Pagina>
  )
}
