import { type ReactNode, useState } from 'react'
import type { Hecho } from '@/shared/api'
import { Metrica, Seccion } from '@/shared/ui'
import { DIMENSIONES } from '../model/hecho'
import { FilaHecho } from './FilaHecho'
import './hecho.css'

interface Props {
  hechos: Hecho[]
  /** Lo que se puede hacer con cada hecho; sin esto, el corpus es de solo lectura. */
  acciones?: (hecho: Hecho) => ReactNode
  /** El enunciado de cada hecho, si se edita en línea. */
  enunciado?: (hecho: Hecho) => ReactNode
}

const cuantos = (hechos: Hecho[], dimension: string) =>
  hechos.filter((h) => h.dimension === dimension).length

/**
 * El corpus con una pestaña por dimensión, y ninguna más. Lo que hay que revisar de cada
 * hecho —lo que no dice la cita, el motivo del verificador— se lee debajo de él.
 */
export function Corpus({ hechos, acciones, enunciado }: Props) {
  const dimensiones = Object.keys(DIMENSIONES)
  const [elegida, setElegida] = useState<string>(
    () => dimensiones.find((d) => cuantos(hechos, d) > 0) ?? dimensiones[0]!,
  )
  const visibles = hechos.filter((h) => h.dimension === elegida)
  const titulo = DIMENSIONES[elegida] ?? elegida

  return (
    <>
      <div className="rejilla-metricas">
        {dimensiones.map((clave) => (
          <button
            key={clave}
            type="button"
            className={`metrica-boton${clave === elegida ? ' activa' : ''}`}
            onClick={() => setElegida(clave)}
          >
            <Metrica etiqueta={DIMENSIONES[clave] ?? clave} valor={cuantos(hechos, clave)} />
          </button>
        ))}
      </div>
      <Seccion titulo={`${titulo} (${visibles.length})`}>
        {visibles.length === 0 ? (
          <p className="nota">Ningún hecho aquí.</p>
        ) : (
          <ul className="hechos">
            {visibles.map((h) => (
              <FilaHecho key={h.id} hecho={h} acciones={acciones?.(h)} enunciado={enunciado?.(h)} />
            ))}
          </ul>
        )}
      </Seccion>
    </>
  )
}
