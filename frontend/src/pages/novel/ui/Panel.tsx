import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { InsigniaEstado, LineaDeFases, nombreDeFase, trabaja } from '@/entities/novela'
import { urlDelPdf } from '@/shared/api'
import { rutaBiblioteca, rutaGate, rutaIndice, rutaVersiones } from '@/shared/config'
import { formatearDinero, formatearFecha, formatearHace, formatearTokens, useSondeo } from '@/shared/lib'
import { EstadoCarga, EstadoError, Insignia, Metrica, Progreso, Seccion } from '@/shared/ui'
import { cargarPanel } from '../api/panel'
import { Acciones } from './Acciones'
import { Actividad } from './Actividad'
import { Capitulos } from './Capitulos'
import { Registro } from './Registro'
import './panel.css'

/** El panel de una novela: desde aquí se sigue una ejecución entera (spec §4.3). */
export function Panel() {
  const { id = '' } = useParams()
  const [aviso, setAviso] = useState<string | null>(null)
  const sondeo = useSondeo(() => cargarPanel(id), [id])
  const panel = sondeo.datos

  if (sondeo.cargando) return <div className="contenido"><EstadoCarga que="la novela" /></div>
  if (!panel) return <div className="contenido"><EstadoError error={sondeo.error} onReintentar={sondeo.refrescar} /></div>

  const ultima = panel.versiones_publicadas[panel.versiones_publicadas.length - 1]
  const incidenciasBloqueantes = panel.incidencias.filter((i) => i.severidad === 'bloqueante')

  return (
    <div className="contenido">
      <header className="cabecera-panel">
        <p className="miga">
          <Link to={rutaBiblioteca()}>Taller</Link> / {panel.titulo}
        </p>
        <div className="fila-entre">
          <div className="pila titulo-panel">
            <div className="fila">
              <h1>{panel.titulo}</h1>
              <InsigniaEstado estado={panel.estado} />
            </div>
            <p className="subtitulo">
              {panel.homenajeado ? `Para ${panel.homenajeado} · ` : ''}
              Fase actual: {nombreDeFase(panel.fase)}
              {panel.actualizada ? ` · actualizada ${formatearHace(panel.actualizada)}` : ''}
            </p>
          </div>
          <Acciones
            panel={panel}
            onHecho={(mensaje) => {
              setAviso(mensaje)
              sondeo.refrescar()
            }}
          />
        </div>
      </header>

      {aviso && <p className="aviso aviso-ok" role="status">{aviso}</p>}
      {sondeo.error !== null && (
        <p className="aviso aviso-error" role="alert">
          El servidor no responde; se sigue intentando. Lo que ves es lo último que llegó.
        </p>
      )}
      {panel.gate && (
        <p className="aviso aviso-espera">
          La novela espera tu decisión en el gate de {nombreDeFase(panel.gate.fase)} desde {formatearHace(panel.gate.abierto_en)}.{' '}
          <Link to={rutaGate(panel.nombre)}>Ir al gate →</Link>
        </p>
      )}
      {panel.estado === 'detenida' && (
        <p className="aviso aviso-error">
          El proceso que tenía esta novela ya no vive, pero dejó su cerrojo. Desbloquéala para poder continuar.
        </p>
      )}
      {trabaja(panel.estado) && (
        <div className="ahora">
          <Insignia tono="azul" punto vivo>
            Trabajando
          </Insignia>
          <span>{panel.trabajando_en ?? 'Arrancando el proceso…'}</span>
        </div>
      )}

      <LineaDeFases id={panel.nombre} fases={panel.fases} />

      <div className="rejilla-2 cuerpo-panel">
        <div>
          <Seccion
            titulo="Capítulos"
            extra={
              panel.capitulos_total > 0 && (
                <span className="nota">
                  {panel.capitulos_aprobados} de {panel.capitulos_total} aprobados
                </span>
              )
            }
          >
            {panel.capitulos_total > 0 && (
              <div className="progreso-panel">
                <Progreso
                  valor={panel.capitulos_aprobados}
                  max={panel.capitulos_total}
                  tono={panel.capitulos_aprobados === panel.capitulos_total ? 'verde' : 'acento'}
                  etiqueta="Capítulos aprobados"
                />
              </div>
            )}
            <Capitulos id={panel.nombre} capitulos={panel.capitulos} />
          </Seccion>
          <Seccion titulo="Actividad">
            <Actividad sucesos={panel.actividad} />
          </Seccion>
        </div>

        <div>
          <Seccion titulo="Consumo">
            <div className="rejilla-metricas">
              <Metrica etiqueta="Coste" valor={formatearDinero(panel.consumo.coste_usd)} />
              <Metrica etiqueta="Tokens de entrada" valor={formatearTokens(panel.consumo.tokens_in)} />
              <Metrica etiqueta="Tokens de salida" valor={formatearTokens(panel.consumo.tokens_out)} />
            </div>
          </Seccion>
          <Seccion titulo="Versiones publicadas">
            {panel.versiones_publicadas.length === 0 ? (
              <p className="nota">Todavía ninguna: se publica al cerrar la Publicación.</p>
            ) : (
              <ul className="lista-versiones">
                {[...panel.versiones_publicadas].reverse().map((v) => (
                  <li key={v.numero} className="fila-entre">
                    <Link to={rutaIndice(panel.nombre, v.numero)}>Versión {v.numero}</Link>
                    <span className="fila">
                      <span className="nota">{formatearFecha(v.creada_en)}</span>
                      {v.pdf ? (
                        <a className="boton boton-secundario boton-pequeno" href={urlDelPdf(panel.nombre, v.numero)} download>
                          PDF
                        </a>
                      ) : (
                        <span className="nota" title="La publicación no llegó a imprimirlo">sin PDF</span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {ultima && (
              <div className="fila">
                <Link className="boton boton-secundario boton-pequeno" to={rutaIndice(panel.nombre, ultima.numero)}>
                  Leer la última
                </Link>
                <Link className="boton boton-fantasma boton-pequeno" to={rutaVersiones(panel.nombre)}>
                  Historial
                </Link>
              </div>
            )}
          </Seccion>
          <Seccion
            titulo="Incidencias recientes"
            extra={incidenciasBloqueantes.length > 0 && <Insignia tono="rojo">{incidenciasBloqueantes.length} bloqueantes</Insignia>}
          >
            {panel.incidencias.length === 0 ? (
              <p className="nota">Ninguna.</p>
            ) : (
              <ul className="incidencias">
                {panel.incidencias.map((inc, i) => (
                  <li key={i}>
                    <Insignia tono={inc.severidad === 'bloqueante' ? 'rojo' : 'gris'}>{inc.validador}</Insignia>{' '}
                    {inc.capitulo ? <span className="nota">cap. {inc.capitulo} · </span> : null}
                    {inc.mensaje}
                  </li>
                ))}
              </ul>
            )}
          </Seccion>
          <Seccion titulo="Registro del proceso" plegable plegada={panel.estado !== 'fallida'}>
            <Registro id={panel.nombre} registros={panel.registros} />
          </Seccion>
        </div>
      </div>
    </div>
  )
}
