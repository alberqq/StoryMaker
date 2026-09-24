import { Link } from 'react-router'
import type { FaseDelPanel } from '@/shared/api'
import { rutaFase } from '@/shared/config'
import { formatearDinero, formatearDuracion, formatearTokens } from '@/shared/lib'
import { ESTADOS_DE_FASE } from '../model/estado'
import { faseDeClave } from '../model/fases'
import './linea.css'

interface Props {
  id: string
  fases: FaseDelPanel[]
}

/**
 * Las seis fases de una novela, cada una con su estado, su coste y lo que duró, enlazada a
 * su salida. Una fase cuyo estado se dedujo de su salida lo dice.
 */
export function LineaDeFases({ id, fases }: Props) {
  return (
    <ol className="linea-fases" aria-label="Fases de la novela">
      {fases.map((f) => {
        const fase = faseDeClave(f.fase)
        const { texto, tono, vivo } = ESTADOS_DE_FASE[f.estado]
        return (
          <li key={f.fase} className={`linea-paso paso-${tono}${vivo ? ' paso-vivo' : ''}`}>
            <Link to={rutaFase(id, fase.segmento)} className="linea-enlace">
              <span className="linea-marca" aria-hidden="true" />
              <span className="linea-nombre">{fase.nombre}</span>
              <span className="linea-estado">
                {texto}
                {f.deducida && <span title="Deducido de lo que la fase dejó escrito"> · deducida</span>}
              </span>
              {f.ejecuciones.length > 0 && (
                <span className="linea-cifras">
                  {formatearDinero(f.coste_usd)} · {formatearTokens(f.tokens_in + f.tokens_out)} tokens ·{' '}
                  {formatearDuracion(f.inicio, f.fin)}
                </span>
              )}
            </Link>
          </li>
        )
      })}
    </ol>
  )
}
