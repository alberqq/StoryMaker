import type { ReactNode } from 'react'
import type { Hecho } from '@/shared/api'
import { Insignia } from '@/shared/ui'
import { TONO_DE_LA_FIRMEZA, porRevisar } from '../model/hecho'

interface Props {
  hecho: Hecho
  /** Lo que se puede hacer con el hecho, si algo: en el gate, corregir y descartar. */
  acciones?: ReactNode
  /** Sustituye al enunciado: el editor en línea del gate. */
  enunciado?: ReactNode
}

/**
 * Un hecho del corpus con una sola etiqueta, su firmeza, y debajo su cita y sus fuentes.
 * Lo que dice el verificador va aparte, en un desplegable cerrado: explica la firmeza, pero
 * no tiene por qué ser lo primero que se ve.
 */
export function FilaHecho({ hecho, acciones, enunciado }: Props) {
  return (
    <li className="hecho" data-hecho={hecho.id}>
      {enunciado ?? <p>{hecho.enunciado}</p>}
      <div className="fila-entre">
        <div className="fila">
          {hecho.respaldo === 'pendiente' ? (
            // Para el escritor sería `inferido`; al Autor le haría creer que ya se juzgó.
            <Insignia tono="gris">En proceso de verificación</Insignia>
          ) : (
            <Insignia tono={TONO_DE_LA_FIRMEZA[hecho.firmeza] ?? 'gris'}>{hecho.firmeza}</Insignia>
          )}
        </div>
        {acciones && <div className="fila hecho-acciones">{acciones}</div>}
      </div>
      {hecho.cita && <blockquote className="cita-hecho">«{hecho.cita}»</blockquote>}
      {hecho.fuentes.length > 0 && (
        <ul className="fuentes">
          {hecho.fuentes.map((f, i) => (
            <li key={i}>
              {f.url ? (
                <a href={f.url} target="_blank" rel="noreferrer">
                  {f.titulo || f.url}
                </a>
              ) : (
                f.titulo || 'fuente sin título'
              )}
              {f.autor && <span className="nota"> · {f.autor}</span>}
              {f.fiabilidad && <span className="nota"> · fiabilidad {f.fiabilidad}</span>}
            </li>
          ))}
        </ul>
      )}
      {porRevisar(hecho) && (hecho.no_lo_dice_la_cita || hecho.motivo_respaldo) && (
        <details className="verificador">
          <summary>Nota del verificador</summary>
          {hecho.no_lo_dice_la_cita && (
            <p>
              <strong>No lo dice la cita:</strong> «{hecho.no_lo_dice_la_cita}»
            </p>
          )}
          {hecho.motivo_respaldo && <p>{hecho.motivo_respaldo}</p>}
        </details>
      )}
    </li>
  )
}
