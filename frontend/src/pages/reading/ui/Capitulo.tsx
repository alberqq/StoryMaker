import { useRef } from 'react'
import { Link, useParams } from 'react-router'
import { EstadoCarga, EstadoError, NoExiste, Pagina } from '@/shared/ui'
import { numeroDeRuta, rutaCapitulo, rutaIndice } from '@/shared/config'
import { parrafos, useCarga } from '@/shared/lib'
import { cargarCapitulo } from '../api/capitulo'
import { PeticionCambio } from './PeticionCambio'

export function Capitulo() {
  const params = useParams()
  const id = params.id ?? ''
  const n = numeroDeRuta(params.n)
  const k = numeroDeRuta(params.k)
  if (n == null || k == null)
    return (
      <Pagina titulo="No existe">
        <NoExiste />
      </Pagina>
    )
  // La clave reinicia la pantalla al pasar de capítulo: la selección y la petición a medio
  // escribir son de un capítulo, no del siguiente.
  return <CapituloDeVersion key={`${id}/${n}/${k}`} id={id} n={n} k={k} />
}

function CapituloDeVersion({ id, n, k }: { id: string; n: number; k: number }) {
  const carga = useCarga(() => cargarCapitulo(id, n, k), [id, n, k])
  const texto = useRef<HTMLElement>(null)

  const volver = <Link to={rutaIndice(id, n)}>Índice</Link>

  if (carga.estado === 'cargando')
    return (
      <Pagina titulo={`Capítulo ${k}`} navegacion={volver}>
        <EstadoCarga que="el capítulo" />
      </Pagina>
    )
  if (carga.estado === 'error')
    return (
      <Pagina titulo={`Capítulo ${k}`} navegacion={volver}>
        <EstadoError error={carga.error} onReintentar={carga.reintentar} />
      </Pagina>
    )

  const capitulo = carga.datos
  const lineas = parrafos(capitulo.texto)
  const titulo = `Capítulo ${k}${capitulo.titulo ? `. ${capitulo.titulo}` : ''}`

  return (
    <Pagina titulo={titulo} navegacion={volver}>
      <article ref={texto} className="texto-capitulo" data-origen={k}>
        {lineas.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </article>
      <nav className="navegacion-capitulo" aria-label="Navegación entre capítulos">
        <span>{k > 1 && <Link to={rutaCapitulo(id, n, k - 1)}>← Capítulo anterior</Link>}</span>
        {volver}
        <span>
          {k < capitulo.total && (
            <Link to={rutaCapitulo(id, n, k + 1)}>Capítulo siguiente →</Link>
          )}
        </span>
      </nav>
      <PeticionCambio id={id} version={n} capitulo={k} texto={texto} />
    </Pagina>
  )
}
