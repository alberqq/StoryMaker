import { Link, useParams } from 'react-router'
import {
  EnlaceCapitulo,
  EstadoCarga,
  EstadoError,
  MarcaCambiado,
  NoExiste,
  Pagina,
} from '@/shared/ui'
import {
  numeroDeRuta,
  rutaCapitulo,
  rutaImprimir,
  rutaPersonajes,
  rutaPortada,
  rutaVersiones,
} from '@/shared/config'
import { urlDelPdf } from '@/shared/api'
import { useCarga } from '@/shared/lib'
import { cargarIndice } from '../api/manifiesto'

export function Indice() {
  const params = useParams()
  const id = params.id ?? ''
  const n = numeroDeRuta(params.n)
  if (n == null)
    return (
      <Pagina titulo="No existe">
        <NoExiste />
      </Pagina>
    )
  return <IndiceDeVersion id={id} n={n} />
}

function IndiceDeVersion({ id, n }: { id: string; n: number }) {
  const carga = useCarga(() => cargarIndice(id, n), [id, n])

  const navegacion = (
    <>
      <Link to={rutaPortada(id, n)}>Portada</Link>
      <Link to={rutaPersonajes(id, n)}>Personajes y lugares</Link>
      <Link to={rutaVersiones(id)}>Historial</Link>
      <Link to={rutaImprimir(id, n)}>Imprimir</Link>
      <a href={urlDelPdf(id, n)} download>
        Descargar PDF
      </a>
    </>
  )

  if (carga.estado === 'cargando')
    return (
      <Pagina titulo="Índice" navegacion={navegacion}>
        <EstadoCarga que="el índice" />
      </Pagina>
    )
  if (carga.estado === 'error')
    return (
      <Pagina titulo="Índice" navegacion={navegacion}>
        <EstadoError error={carga.error} onReintentar={carga.reintentar} />
      </Pagina>
    )

  const { version, cambiados } = carga.datos
  return (
    <Pagina titulo={version.paratexto.titulo} navegacion={navegacion}>
      <p className="nota">
        Versión {version.numero}
        {version.anterior != null &&
          cambiados.size > 0 &&
          ` · ${cambiados.size} capítulo(s) cambian respecto de la versión ${version.anterior}`}
      </p>
      <nav data-render="indice" aria-label="Índice de capítulos">
        <ol className="lista-capitulos">
          {version.capitulos.map((c) => (
            <li key={c.id}>
              <EnlaceCapitulo a={rutaCapitulo(id, n, c.numero)}>
                Capítulo {c.numero}
                {c.titulo ? `. ${c.titulo}` : ''}
              </EnlaceCapitulo>
              {cambiados.has(c.numero) && <MarcaCambiado />}
            </li>
          ))}
        </ol>
      </nav>
    </Pagina>
  )
}
