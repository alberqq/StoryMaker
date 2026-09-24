import type { CapituloDelManifiesto } from '@/shared/api'
import { EnlaceCapitulo } from '@/shared/ui'
import { anclaCapitulo } from '@/shared/config'

interface Props {
  capitulos: CapituloDelManifiesto[]
  conNovedades: boolean
}

/** El índice del documento. Enlaza por ancla y no por router: en papel no hay navegación. */
export function Indice({ capitulos, conNovedades }: Props) {
  return (
    <section data-render="indice">
      <h2>Índice</h2>
      <ol className="lista-capitulos">
        {capitulos.map((c) => (
          <li key={c.id}>
            <EnlaceCapitulo a={anclaCapitulo(c.numero)}>
              Capítulo {c.numero}
              {c.titulo ? `. ${c.titulo}` : ''}
            </EnlaceCapitulo>
          </li>
        ))}
        <li>
          <EnlaceCapitulo a="#personajes">Personajes y lugares</EnlaceCapitulo>
        </li>
        {conNovedades && (
          <li>
            <EnlaceCapitulo a="#novedades">Novedades de esta versión</EnlaceCapitulo>
          </li>
        )}
      </ol>
    </section>
  )
}
