import { Link, useParams } from 'react-router'
import type { FichaEscenario, FichaPersonaje } from '@/shared/api'
import { EnlaceCapitulo, EstadoCarga, EstadoError, EstadoVacio, NoExiste, Pagina, Tarjeta } from '@/shared/ui'
import { numeroDeRuta, rutaCapitulo, rutaIndice } from '@/shared/config'
import { useCarga } from '@/shared/lib'
import { cargarFichas } from '../api/personajes'

const TIPOS: Record<string, string> = {
  inventado: 'Inventado',
  historico_ficcionalizado: 'Histórico ficcionalizado',
  historico_de_fondo: 'Histórico de fondo',
}

export function Fichas() {
  const params = useParams()
  const id = params.id ?? ''
  const n = numeroDeRuta(params.n)
  if (n == null)
    return (
      <Pagina titulo="No existe">
        <NoExiste />
      </Pagina>
    )
  return <FichasDeVersion id={id} n={n} />
}

/**
 * Cada entrada enlaza a los capítulos donde aparece, con la versión que la ruta lleva puesta
 * (spec §4.3). Una entrada sin apariciones se enseña sin enlaces: no se oculta.
 */
function Apariciones({ id, n, capitulos }: { id: string; n: number; capitulos: number[] }) {
  if (capitulos.length === 0)
    return <p className="nota">No aparece en ningún capítulo de esta versión.</p>
  return (
    <p>
      Aparece en:{' '}
      {capitulos.map((k, i) => (
        <span key={k}>
          {i > 0 && ', '}
          <EnlaceCapitulo a={rutaCapitulo(id, n, k)}>capítulo {k}</EnlaceCapitulo>
        </span>
      ))}
    </p>
  )
}

function Personaje({ id, n, p }: { id: string; n: number; p: FichaPersonaje }) {
  return (
    <Tarjeta titulo={p.nombre}>
      <p className="nota">
        {TIPOS[p.tipo] ?? p.tipo}
        {p.es_homenajeado && ' · homenajeado'}
        {p.estatus && ` · ${p.estatus}`}
      </p>
      {p.relacion_con_homenajeado && <p>Relación con el homenajeado: {p.relacion_con_homenajeado}</p>}
      {p.rasgos.length > 0 && <p>Rasgos: {p.rasgos.join(', ')}</p>}
      <Apariciones id={id} n={n} capitulos={p.capitulos} />
    </Tarjeta>
  )
}

function Escenario({ id, n, e }: { id: string; n: number; e: FichaEscenario }) {
  return (
    <Tarjeta titulo={e.nombre}>
      {e.lugar_de_epoca && <p className="nota">En la época: {e.lugar_de_epoca}</p>}
      {e.descripcion && e.descripcion !== e.nombre && <p>{e.descripcion}</p>}
      <Apariciones id={id} n={n} capitulos={e.capitulos} />
    </Tarjeta>
  )
}

function FichasDeVersion({ id, n }: { id: string; n: number }) {
  const carga = useCarga(() => cargarFichas(id, n), [id, n])
  const volver = <Link to={rutaIndice(id, n)}>Índice</Link>

  return (
    <Pagina titulo="Personajes y lugares" navegacion={volver}>
      {carga.estado === 'cargando' && <EstadoCarga que="las fichas" />}
      {carga.estado === 'error' && (
        <EstadoError error={carga.error} onReintentar={carga.reintentar} />
      )}
      {carga.estado === 'listo' && (
        <div data-render="personajes">
          <h2>Personajes</h2>
          {carga.datos.personajes.length === 0 && (
            <EstadoVacio>Esta novela no tiene personajes en su canon.</EstadoVacio>
          )}
          {carga.datos.personajes.map((p) => (
            <Personaje key={p.id} id={id} n={n} p={p} />
          ))}
          <h2>Lugares</h2>
          {carga.datos.escenarios.length === 0 && (
            <EstadoVacio>Esta novela no tiene escenarios en su canon.</EstadoVacio>
          )}
          {carga.datos.escenarios.map((e) => (
            <Escenario key={e.id} id={id} n={n} e={e} />
          ))}
        </div>
      )}
    </Pagina>
  )
}
