import type { Fichas } from '@/shared/api'
import { EnlaceCapitulo } from '@/shared/ui'
import { anclaCapitulo } from '@/shared/config'

function Apariciones({ capitulos }: { capitulos: number[] }) {
  if (capitulos.length === 0) return null
  return (
    <>
      {' '}— capítulos{' '}
      {capitulos.map((k, i) => (
        <span key={k}>
          {i > 0 && ', '}
          <EnlaceCapitulo a={anclaCapitulo(k)}>{k}</EnlaceCapitulo>
        </span>
      ))}
    </>
  )
}

/** La ficha de personajes y lugares, cada entrada enlazada por ancla a sus capítulos. */
export function Personajes({ fichas }: { fichas: Fichas }) {
  return (
    <section id="personajes" data-render="personajes">
      <h2>Personajes y lugares</h2>
      <ul>
        {fichas.personajes.map((p) => (
          <li key={`p${p.id}`}>
            <strong>{p.nombre}</strong>
            {p.estatus && `, ${p.estatus}`}
            {p.relacion_con_homenajeado && ` (${p.relacion_con_homenajeado} del homenajeado)`}
            <Apariciones capitulos={p.capitulos} />
          </li>
        ))}
      </ul>
      {fichas.escenarios.length > 0 && (
        <ul>
          {fichas.escenarios.map((e) => (
            <li key={`e${e.id}`}>
              <strong>{e.nombre}</strong>
              {e.lugar_de_epoca && ` (${e.lugar_de_epoca})`}
              <Apariciones capitulos={e.capitulos} />
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
