import { useState } from 'react'
import type { Hecho, SalidaInvestigacion as Salida } from '@/shared/api'
import { formatearHora } from '@/shared/lib'
import { EstadoVacio, Insignia, Metrica, Seccion, Tabla, type Tono } from '@/shared/ui'

const DIMENSIONES: Record<string, string> = {
  cronologia: 'Cronología',
  lugar: 'Lugar',
  cultura_material: 'Cultura material',
  lenguaje: 'Lenguaje',
  mentalidad: 'Mentalidad',
  estructura_social: 'Estructura social',
}

const ESTADO: Record<string, Tono> = { verificado: 'verde', debatido: 'ambar', inferido: 'gris', desconocido: 'rojo' }
const RESPALDO: Record<string, Tono> = { respaldado: 'verde', no_respaldado: 'rojo', pendiente: 'gris', no_aplica: 'gris' }

function FilaHecho({ hecho }: { hecho: Hecho }) {
  return (
    <li className="hecho">
      <p>{hecho.enunciado}</p>
      <div className="fila">
        <Insignia tono={ESTADO[hecho.estado] ?? 'gris'}>{hecho.estado}</Insignia>
        <Insignia tono={RESPALDO[hecho.respaldo] ?? 'gris'}>{hecho.respaldo.replace('_', ' ')}</Insignia>
        {hecho.origen !== 'investigacion_inicial' && <Insignia>{hecho.origen.replaceAll('_', ' ')}</Insignia>}
      </div>
      {hecho.cita && <blockquote className="comentario">«{hecho.cita}»</blockquote>}
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
    </li>
  )
}

/** El corpus agrupado por dimensión, con su estado epistémico, su respaldo, su cita y sus fuentes. */
export function SalidaInvestigacion({ salida }: { salida: Salida }) {
  const dimensiones = Object.keys(DIMENSIONES).filter((d) => salida.recuento[d])
  const [dimension, setDimension] = useState<string>(dimensiones[0] ?? '')
  if (salida.hechos.length === 0) return <EstadoVacio>La investigación todavía no ha dejado hechos en el corpus.</EstadoVacio>
  const visibles = salida.hechos.filter((h) => h.dimension === dimension)
  return (
    <>
      <div className="rejilla-metricas">
        {Object.entries(DIMENSIONES).map(([clave, nombre]) => (
          <button key={clave} type="button" className={`metrica-boton${clave === dimension ? ' activa' : ''}`} onClick={() => setDimension(clave)}>
            <Metrica etiqueta={nombre} valor={salida.recuento[clave] ?? 0} />
          </button>
        ))}
      </div>
      {salida.sello ? (
        <p className="aviso aviso-info">
          Corpus sellado {formatearHora(salida.sello.calculado_en)} · <span className="mono">{salida.sello.hash.slice(0, 16)}…</span>
        </p>
      ) : (
        <p className="aviso aviso-espera">El corpus aún no está sellado: se sella al cerrar la Trama.</p>
      )}
      <Seccion titulo={`${DIMENSIONES[dimension] ?? dimension} (${visibles.length})`}>
        <ul className="hechos">
          {visibles.map((h) => (
            <FilaHecho key={h.id} hecho={h} />
          ))}
        </ul>
      </Seccion>
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
