import type { Suceso } from '@/shared/api'
import { formatearHora } from '@/shared/lib'
import { EstadoVacio } from '@/shared/ui'

const MARCA: Record<Suceso['tipo'], string> = {
  fase: 'fase',
  capitulo: 'capitulo',
  gate: 'gate',
  edicion: 'edicion',
  accion: 'accion',
  peticion: 'peticion',
}

/** Lo que ha pasado, en frases: no el registro del proceso (spec §4.3). */
export function Actividad({ sucesos }: { sucesos: Suceso[] }) {
  if (sucesos.length === 0) return <EstadoVacio>Todavía no ha pasado nada en esta novela.</EstadoVacio>
  return (
    <ol className="actividad">
      {sucesos.map((s, i) => (
        <li key={`${s.momento}-${i}`} className={`suceso suceso-${MARCA[s.tipo]}`}>
          <span className="suceso-hora">{formatearHora(s.momento)}</span>
          <span className="suceso-texto">
            {s.texto}
            {s.detalle && <span className="suceso-detalle"> — {s.detalle}</span>}
          </span>
        </li>
      ))}
    </ol>
  )
}
