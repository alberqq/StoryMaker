import type { DragEvent } from 'react'
import { Link } from 'react-router'
import { InsigniaEstado, nombreDeFase } from '@/entities/novela'
import type { TarjetaNovela as Tarjeta } from '@/shared/api'
import { rutaPanel } from '@/shared/config'
import { formatearDinero, formatearHace } from '@/shared/lib'
import { Boton, Progreso } from '@/shared/ui'
import { arrastrable, columnaSiguiente, type Decision } from '../model/columnas'

interface Props {
  tarjeta: Tarjeta
  arrastrando: boolean
  onArrastrar: (nombre: string | null) => void
  onProponer: (tarjeta: Tarjeta, decision: Decision) => void
}

export function TarjetaNovela({ tarjeta, arrastrando, onArrastrar, onProponer }: Props) {
  const movible = arrastrable(tarjeta)
  const siguiente = columnaSiguiente(tarjeta)

  const empezar = (e: DragEvent) => {
    e.dataTransfer?.setData('text/plain', tarjeta.nombre)
    if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
    onArrastrar(tarjeta.nombre)
  }

  return (
    <article
      className={`tarjeta-novela${movible ? ' movible' : ''}${arrastrando ? ' arrastrada' : ''}`}
      draggable={movible}
      onDragStart={movible ? empezar : undefined}
      onDragEnd={() => onArrastrar(null)}
      aria-label={tarjeta.titulo}
      data-novela={tarjeta.nombre}
    >
      <div className="fila-entre">
        <InsigniaEstado estado={tarjeta.estado} />
        {movible && (
          <span className="asa" aria-hidden="true" title="Arrastra para decidir">
            ⠿
          </span>
        )}
      </div>
      <h3>
        <Link to={rutaPanel(tarjeta.nombre)}>{tarjeta.titulo}</Link>
      </h3>
      {tarjeta.homenajeado && <p className="tarjeta-homenajeado">Para {tarjeta.homenajeado}</p>}

      {tarjeta.gate && (
        <p className="tarjeta-gate">
          Gate de {nombreDeFase(tarjeta.gate.fase)} · {formatearHace(tarjeta.gate.abierto_en)}
        </p>
      )}

      {tarjeta.capitulos_total > 0 && (
        <div className="tarjeta-progreso">
          <div className="fila-entre nota">
            <span>Capítulos</span>
            <span>
              {tarjeta.capitulos_aprobados} / {tarjeta.capitulos_total}
            </span>
          </div>
          <Progreso
            valor={tarjeta.capitulos_aprobados}
            max={tarjeta.capitulos_total}
            tono={tarjeta.capitulos_aprobados === tarjeta.capitulos_total ? 'verde' : 'acento'}
            etiqueta={`Capítulos aprobados de ${tarjeta.titulo}`}
          />
        </div>
      )}

      <div className="fila-entre tarjeta-pie">
        <span>{formatearDinero(tarjeta.coste_usd)}</span>
        <span>
          {tarjeta.versiones > 0
            ? `${tarjeta.versiones} ${tarjeta.versiones === 1 ? 'versión' : 'versiones'}`
            : 'sin versiones'}
        </span>
      </div>

      {movible && (
        <div className="fila tarjeta-acciones">
          <Boton tamano="pequeno" onClick={() => onProponer(tarjeta, 'aprobar')}>
            Aprobar{siguiente ? ` → ${siguiente.titulo}` : ''}
          </Boton>
          <Boton tamano="pequeno" variante="secundario" onClick={() => onProponer(tarjeta, 'rehacer')}>
            Rehacer…
          </Boton>
        </div>
      )}
    </article>
  )
}
