import { Link } from 'react-router'
import type { CapituloDelPanel } from '@/shared/api'
import { rutaFase } from '@/shared/config'
import { EstadoVacio } from '@/shared/ui'

const ESTADOS: Record<CapituloDelPanel['estado'], string> = {
  pendiente: 'pendiente',
  en_curso: 'en curso',
  aprobado: 'aprobado',
  invalidado: 'invalidado',
  descartado: 'descartado',
}

/** La rejilla de capítulos: su estado, sus intentos y sus palabras. */
export function Capitulos({ id, capitulos }: { id: string; capitulos: CapituloDelPanel[] }) {
  if (capitulos.length === 0)
    return <EstadoVacio>La escaleta todavía no existe: los capítulos aparecen al cerrar la Trama.</EstadoVacio>
  return (
    <ol className="rejilla-capitulos" aria-label="Capítulos">
      {capitulos.map((c) => (
        <li key={c.numero} className={`casilla casilla-${c.estado}`}>
          <Link to={rutaFase(id, 'escritura')} title={c.titulo ?? undefined}>
            <span className="casilla-numero">{c.numero}</span>
            <span className="casilla-estado">{ESTADOS[c.estado]}</span>
            <span className="casilla-cifras">
              {c.intentos > 0 ? `${c.intentos} ${c.intentos === 1 ? 'intento' : 'intentos'}` : '—'}
              {c.palabras ? ` · ${c.palabras} pal.` : ''}
            </span>
          </Link>
        </li>
      ))}
    </ol>
  )
}
