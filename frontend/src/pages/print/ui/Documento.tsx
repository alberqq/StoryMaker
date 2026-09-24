import { useParams } from 'react-router'
import { EstadoCarga, EstadoError, NoExiste } from '@/shared/ui'
import { numeroDeRuta } from '@/shared/config'
import { parrafos, useCarga } from '@/shared/lib'
import { cargarDocumento } from '../api/todo'
import { Indice } from './Indice'
import { Novedades } from './Novedades'
import { Personajes } from './Personajes'
import { Portada } from './Portada'

export function Documento() {
  const params = useParams()
  const id = params.id ?? ''
  const n = numeroDeRuta(params.n)
  if (n == null) return <NoExiste />
  return <DocumentoDeVersion id={id} n={n} />
}

/**
 * La novela entera en una sola página: lo que imprime Playwright y lo que juzga
 * `render_visual` (spec §4.6 y §6). Una sola navegación la trae completa; dentro no hay
 * router ni paginación, y el orden es el de la spec: portada y dedicatoria, nota del autor,
 * índice, capítulos, personajes y lugares y —si hay predecesora— novedades.
 *
 * `data-estado="listo"` marca el momento en que el documento está completo, para que quien
 * imprime o juzga no lo haga sobre un estado de carga.
 */
function DocumentoDeVersion({ id, n }: { id: string; n: number }) {
  const carga = useCarga(() => cargarDocumento(id, n), [id, n])

  if (carga.estado === 'cargando') return <EstadoCarga que="el documento" />
  if (carga.estado === 'error')
    return <EstadoError error={carga.error} onReintentar={carga.reintentar} />

  const { version, capitulos, fichas, novedades } = carga.datos
  return (
    <div className="documento" data-estado="listo">
      <Portada paratexto={version.paratexto} />
      <Indice capitulos={version.capitulos} conNovedades={novedades != null} />
      {capitulos.map((capitulo, i) => {
        const numero = version.capitulos[i]?.numero ?? capitulo.orden
        return (
          <section key={numero} id={`capitulo-${numero}`} className="texto-capitulo">
            <h2>
              Capítulo {numero}
              {capitulo.titulo ? `. ${capitulo.titulo}` : ''}
            </h2>
            {parrafos(capitulo.texto).map((p, j) => (
              <p key={j}>{p}</p>
            ))}
          </section>
        )
      })}
      <Personajes fichas={fichas} />
      {novedades && <Novedades diff={novedades} />}
    </div>
  )
}
