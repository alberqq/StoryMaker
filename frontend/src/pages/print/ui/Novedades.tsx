import type { Diferencias } from '@/shared/api'
import { EnlaceCapitulo } from '@/shared/ui'
import { anclaCapitulo } from '@/shared/config'

const ESTADOS: Record<string, string> = {
  regenerado: 'reescrito',
  nuevo: 'nuevo',
  retirado: 'retirado',
}

/**
 * Lo que cambió respecto de la versión anterior. Solo existe si hay predecesora: sin ella
 * la sección se omite entera y el índice no la enlaza (spec §9).
 */
export function Novedades({ diff }: { diff: Diferencias }) {
  return (
    <section id="novedades" data-render="novedades">
      <h2>Novedades respecto de la versión {diff.version_a}</h2>
      {diff.cambios.length === 0 ? (
        <p>Ningún capítulo cambia respecto de la versión anterior.</p>
      ) : (
        <ul>
          {diff.cambios.map((c) => (
            <li key={c.capitulo}>
              {c.estado === 'retirado' ? (
                `Capítulo ${c.capitulo}`
              ) : (
                <EnlaceCapitulo a={anclaCapitulo(c.capitulo)}>Capítulo {c.capitulo}</EnlaceCapitulo>
              )}
              : {ESTADOS[c.estado] ?? c.estado}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
