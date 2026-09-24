import { type DragEvent, useState } from 'react'
import { Link } from 'react-router'
import type { TarjetaNovela as Tarjeta } from '@/shared/api'
import { rutaEncargo } from '@/shared/config'
import { useSondeo } from '@/shared/lib'
import { EstadoCarga, EstadoError, EstadoVacio } from '@/shared/ui'
import { cargarTaller } from '../api/listar'
import { COLUMNAS, columnaDe, decisionAlSoltar, type Decision } from '../model/columnas'
import { ConfirmarGate } from './ConfirmarGate'
import { TarjetaNovela } from './TarjetaNovela'
import './tablero.css'

interface Propuesta {
  tarjeta: Tarjeta
  decision: Decision
}

/**
 * El taller: un tablero por fases, al estilo de Jira (spec §4.1). Se refresca solo; mientras
 * se arrastra o se confirma, el refresco espera, para no mover nada bajo el ratón.
 */
export function Tablero() {
  const [arrastrando, setArrastrando] = useState<string | null>(null)
  const [encima, setEncima] = useState<string | null>(null)
  const [propuesta, setPropuesta] = useState<Propuesta | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const taller = useSondeo(cargarTaller, [], { pausado: arrastrando !== null || propuesta !== null })

  const novelas = taller.datos ?? []
  const enMovimiento = novelas.find((n) => n.nombre === arrastrando)
  const esperan = novelas.filter((n) => n.estado === 'esperando_autor').length
  const trabajan = novelas.filter((n) => n.estado === 'en_marcha' || n.estado === 'arrancando').length

  const sobre = (columna: string) => (e: DragEvent) => {
    if (enMovimiento && decisionAlSoltar(enMovimiento, columna)) {
      e.preventDefault()
      setEncima(columna)
    }
  }
  const soltar = (columna: string) => (e: DragEvent) => {
    e.preventDefault()
    const decision = enMovimiento ? decisionAlSoltar(enMovimiento, columna) : null
    if (enMovimiento && decision) setPropuesta({ tarjeta: enMovimiento, decision })
    setArrastrando(null)
    setEncima(null)
  }

  return (
    <div className="contenido contenido-ancho">
      <header className="cabecera-pagina">
        <div>
          <h1>Taller</h1>
          <p className="subtitulo">
            {taller.datos
              ? `${novelas.length} ${novelas.length === 1 ? 'novela' : 'novelas'} · ${trabajan} en marcha · ${esperan} esperan tu decisión`
              : 'Las novelas del directorio de proyectos, por fases'}
          </p>
        </div>
        <Link className="boton boton-primario" to={rutaEncargo()}>
          + Nueva novela
        </Link>
      </header>

      {aviso && (
        <p className="aviso aviso-ok" role="status">
          {aviso}
        </p>
      )}
      {taller.error !== null && taller.datos !== undefined && (
        <p className="aviso aviso-error" role="alert">
          El servidor no responde; se sigue intentando. Lo que ves es lo último que llegó.
        </p>
      )}

      {taller.cargando && <EstadoCarga que="el taller" />}
      {!taller.cargando && taller.datos === undefined && (
        <EstadoError error={taller.error} onReintentar={taller.refrescar} />
      )}
      {taller.datos !== undefined && novelas.length === 0 && (
        <EstadoVacio>
          Todavía no hay ninguna novela en el directorio de proyectos. <Link to={rutaEncargo()}>Encarga la primera</Link>.
        </EstadoVacio>
      )}

      {novelas.length > 0 && (
        <div className="tablero" role="list" aria-label="Tablero por fases">
          {COLUMNAS.map((columna) => {
            const suyas = novelas.filter((n) => columnaDe(n) === columna.clave)
            const acepta = enMovimiento ? decisionAlSoltar(enMovimiento, columna.clave) : null
            return (
              <section
                key={columna.clave}
                role="listitem"
                aria-label={columna.titulo}
                className={`columna${acepta ? ` acepta acepta-${acepta}` : ''}${encima === columna.clave ? ' encima' : ''}`}
                onDragOver={sobre(columna.clave)}
                onDragLeave={() => setEncima(null)}
                onDrop={soltar(columna.clave)}
                data-columna={columna.clave}
              >
                <header className="columna-cabecera">
                  <h2>{columna.titulo}</h2>
                  <span className="columna-cuenta">{suyas.length}</span>
                </header>
                {acepta && (
                  <p className="columna-pista">{acepta === 'aprobar' ? 'Suelta para aprobar' : 'Suelta para rehacer'}</p>
                )}
                <div className="columna-tarjetas">
                  {suyas.map((n) => (
                    <TarjetaNovela
                      key={n.nombre}
                      tarjeta={n}
                      arrastrando={arrastrando === n.nombre}
                      onArrastrar={setArrastrando}
                      onProponer={(tarjeta, decision) => setPropuesta({ tarjeta, decision })}
                    />
                  ))}
                </div>
              </section>
            )
          })}
        </div>
      )}

      {propuesta && (
        <ConfirmarGate
          tarjeta={propuesta.tarjeta}
          decision={propuesta.decision}
          onCerrar={() => setPropuesta(null)}
          onHecho={(mensaje) => {
            setPropuesta(null)
            setAviso(mensaje)
            taller.refrescar()
          }}
        />
      )}
    </div>
  )
}
