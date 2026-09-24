import { Corpus } from '@/entities/hecho'
import type { SalidaInvestigacion as Salida } from '@/shared/api'
import { formatearHora } from '@/shared/lib'
import { EstadoVacio, Seccion, Tabla } from '@/shared/ui'

/** El corpus agrupado por dimensión, con su estado epistémico, su respaldo, su cita y sus fuentes. */
export function SalidaInvestigacion({ salida }: { salida: Salida }) {
  if (salida.hechos.length === 0) return <EstadoVacio>La investigación todavía no ha dejado hechos en el corpus.</EstadoVacio>
  return (
    <>
      {salida.sello ? (
        <p className="aviso aviso-info">
          Corpus sellado {formatearHora(salida.sello.calculado_en)} · <span className="mono">{salida.sello.hash.slice(0, 16)}…</span>
        </p>
      ) : (
        <p className="aviso aviso-espera">El corpus aún no está sellado: se sella al cerrar la Trama.</p>
      )}
      <Corpus hechos={salida.hechos} />
      <Seccion titulo={`Entidades (${salida.entidades.length})`} plegable plegada>
        <Tabla columnas={['Tipo', 'Nombre', 'En la época', 'Fechas']}>
          {salida.entidades.map((e, i) => (
            <tr key={i}>
              <td>{e.tipo.replaceAll('_', ' ')}</td>
              <td>{e.nombre}</td>
              <td>{e.nombre_epoca ?? '—'}</td>
              <td>{[e.fecha_inicio, e.fecha_fin].filter(Boolean).join(' – ') || '—'}</td>
            </tr>
          ))}
        </Tabla>
      </Seccion>
    </>
  )
}
