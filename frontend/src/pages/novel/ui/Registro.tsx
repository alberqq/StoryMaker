import { useState } from 'react'
import { useCarga } from '@/shared/lib'
import { EstadoCarga, EstadoError } from '@/shared/ui'
import { cargarRegistro } from '../api/panel'

/**
 * La salida literal de los procesos lanzados desde la interfaz, plegada: la pantalla enseña
 * la actividad interpretada, y esto queda para cuando haga falta mirar el detalle.
 */
export function Registro({ id, registros }: { id: string; registros: string[] }) {
  const [elegido, setElegido] = useState(registros[0] ?? '')
  if (registros.length === 0)
    return <p className="nota">Esta novela no se ha lanzado desde la interfaz: no hay registros de proceso.</p>
  return (
    <div className="pila">
      <select className="entrada" value={elegido} onChange={(e) => setElegido(e.target.value)} aria-label="Registro">
        {registros.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>
      {elegido && <Contenido id={id} registro={elegido} />}
    </div>
  )
}

function Contenido({ id, registro }: { id: string; registro: string }) {
  const carga = useCarga(() => cargarRegistro(id, registro), [id, registro])
  if (carga.estado === 'cargando') return <EstadoCarga que="el registro" />
  if (carga.estado === 'error') return <EstadoError error={carga.error} onReintentar={carga.reintentar} />
  return <pre className="registro">{carga.datos || '(vacío)'}</pre>
}
