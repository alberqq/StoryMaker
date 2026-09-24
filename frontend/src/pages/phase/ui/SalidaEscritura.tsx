import { useState } from 'react'
import type { SalidaEscritura as Salida } from '@/shared/api'
import { formatearHora, parrafos, useCarga } from '@/shared/lib'
import { Boton, EstadoCarga, EstadoError, EstadoVacio, Insignia, Seccion, type Tono } from '@/shared/ui'
import { cargarIntento } from '../api/fase'

const ESTADO: Record<string, Tono> = { aprobado: 'verde', borrador: 'azul', invalidado: 'rojo', descartado: 'gris' }

/** Cada capítulo con sus intentos, las incidencias de cada uno y el texto de cualquiera. */
export function SalidaEscritura({ id, salida }: { id: string; salida: Salida }) {
  const [leyendo, setLeyendo] = useState<number | null>(null)
  const escritos = salida.capitulos.filter((c) => c.intentos.length > 0)
  if (escritos.length === 0) return <EstadoVacio>La escritura todavía no ha empezado ningún capítulo.</EstadoVacio>
  return (
    <>
      {salida.capitulos.map((c) => (
        <Seccion
          key={c.numero}
          titulo={`Capítulo ${c.numero}${c.titulo ? `. ${c.titulo}` : ''}`}
          extra={<span className="nota">{c.intentos.length} intento(s)</span>}
          plegable
          plegada={c.intentos.every((i) => i.estado === 'aprobado' && i.incidencias.length === 0)}
        >
          {c.intentos.length === 0 ? (
            <p className="nota">Sin escribir todavía.</p>
          ) : (
            <ol className="intentos">
              {c.intentos.map((i) => {
                const bloqueantes = i.incidencias.filter((x) => x.severidad === 'bloqueante').length
                return (
                  <li key={i.id} className="intento">
                    <div className="fila-entre">
                      <div className="fila">
                        <strong>Intento {i.intento}</strong>
                        <Insignia tono={ESTADO[i.estado] ?? 'gris'}>{i.estado}</Insignia>
                        <span className="nota">{i.palabras} palabras · {formatearHora(i.creado_en)}</span>
                        {bloqueantes > 0 && <Insignia tono="rojo">{bloqueantes} bloqueantes</Insignia>}
                      </div>
                      <Boton tamano="pequeno" variante="secundario" onClick={() => setLeyendo(leyendo === i.id ? null : i.id)}>
                        {leyendo === i.id ? 'Ocultar texto' : 'Leer el texto'}
                      </Boton>
                    </div>
                    {i.incidencias.length > 0 && (
                      <ul className="incidencias-intento">
                        {i.incidencias.map((inc, k) => (
                          <li key={k}>
                            <Insignia tono={inc.severidad === 'bloqueante' ? 'rojo' : 'gris'}>{inc.validador}</Insignia>{' '}
                            {inc.mensaje}
                            {inc.ubicacion && <span className="nota"> · {inc.ubicacion}</span>}
                            {inc.propuesta && <p className="nota">Propuesta: {inc.propuesta}</p>}
                          </li>
                        ))}
                      </ul>
                    )}
                    {leyendo === i.id && <TextoDelIntento id={id} intento={i.id} />}
                  </li>
                )
              })}
            </ol>
          )}
        </Seccion>
      ))}
    </>
  )
}

function TextoDelIntento({ id, intento }: { id: string; intento: number }) {
  const carga = useCarga(() => cargarIntento(id, intento), [id, intento])
  if (carga.estado === 'cargando') return <EstadoCarga que="el texto" />
  if (carga.estado === 'error') return <EstadoError error={carga.error} onReintentar={carga.reintentar} />
  return (
    <div className="texto-intento libro">
      {carga.datos.tokens_de_contexto != null && (
        <p className="nota">Escrito con un paquete de contexto de {carga.datos.tokens_de_contexto} tokens.</p>
      )}
      <div className="texto-capitulo">
        {parrafos(carga.datos.texto).map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
    </div>
  )
}
