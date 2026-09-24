import { ESTADOS_DE_FASE } from '@/entities/novela'
import type { EstadoDeFase, SalidaDeFase } from '@/shared/api'
import { formatearDinero, formatearDuracion, formatearHora, formatearTokens } from '@/shared/lib'
import { Insignia, Tabla } from '@/shared/ui'

/** Cuántas veces corrió la fase, qué costó cada vez y qué se decidió en sus gates. */
export function Ejecuciones({ salida }: { salida: SalidaDeFase }) {
  return (
    <div className="pila">
      {salida.ejecuciones.length === 0 ? (
        <p className="nota">
          Sin ejecuciones registradas. En las novelas empezadas antes de que cada fase abriera su fila, la salida se lee
          igual aunque no conste aquí.
        </p>
      ) : (
        <Tabla columnas={['Ejecución', 'Estado', 'Inicio', 'Duración', 'Tokens', 'Coste']}>
          {salida.ejecuciones.map((e) => {
            const estado = ESTADOS_DE_FASE[e.estado as EstadoDeFase] ?? { texto: e.estado, tono: 'gris' as const }
            return (
              <tr key={e.id}>
                <td>#{e.id}</td>
                <td>
                  <Insignia tono={estado.tono}>{estado.texto}</Insignia>
                </td>
                <td>{formatearHora(e.inicio)}</td>
                <td>{formatearDuracion(e.inicio, e.fin)}</td>
                <td>{formatearTokens(e.tokens_in + e.tokens_out)}</td>
                <td>{formatearDinero(e.coste_usd)}</td>
              </tr>
            )
          })}
        </Tabla>
      )}
      {salida.decisiones.length > 0 && (
        <ul className="decisiones">
          {salida.decisiones.map((d) => (
            <li key={d.gate_id}>
              <Insignia tono={d.decision === 'aprobar' ? 'verde' : d.decision ? 'ambar' : 'gris'}>
                {d.decision ?? d.estado}
              </Insignia>{' '}
              <span className="nota">Gate #{d.gate_id}{d.decidido_en ? ` · ${formatearHora(d.decidido_en)}` : ''}</span>
              {d.comentario && <blockquote className="comentario">{d.comentario}</blockquote>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
