import type { CapituloDelManifiesto } from '@/shared/api'
import { EnlaceCapitulo } from '@/shared/ui'
import { anclaCapitulo } from '@/shared/config'
import { romano } from './romano'

interface Props {
  capitulos: CapituloDelManifiesto[]
  conNovedades: boolean
}

/** El índice del documento. Enlaza por ancla y no por router: en papel no hay navegación. */
export function Indice({ capitulos, conNovedades }: Props) {
  return (
    <section data-render="indice">
      <h2>Índice</h2>
      <ol className="indice-libro">
        {capitulos.map((c) => (
          <li key={c.id}>
            <span className="indice-numero">{romano(c.numero)}</span>
            <EnlaceCapitulo a={anclaCapitulo(c.numero)}>{c.titulo ? c.titulo : `Capítulo ${c.numero}`}</EnlaceCapitulo>
          </li>
        ))}
        <li className="indice-anexo">
          <span className="indice-numero" />
          <EnlaceCapitulo a="#personajes">Personajes y lugares</EnlaceCapitulo>
        </li>
        {conNovedades && (
          <li className="indice-anexo">
            <span className="indice-numero" />
            <EnlaceCapitulo a="#novedades">Novedades de esta versión</EnlaceCapitulo>
          </li>
        )}
      </ol>
    </section>
  )
}
