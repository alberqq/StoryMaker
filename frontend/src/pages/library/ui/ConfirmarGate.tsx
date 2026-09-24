import { useState } from 'react'
import { Link } from 'react-router'
import { nombreDeFase } from '@/entities/novela'
import type { TarjetaNovela } from '@/shared/api'
import { rutaGate } from '@/shared/config'
import { useCarga } from '@/shared/lib'
import { Boton, Dialogo, EstadoCarga, EstadoError, Metrica } from '@/shared/ui'
import { cargarResumenDelGate, confirmarDecision } from '../api/decidir'
import { columnaSiguiente, type Decision } from '../model/columnas'

interface Props {
  tarjeta: TarjetaNovela
  decision: Decision
  onCerrar: () => void
  onHecho: (mensaje: string) => void
}

/**
 * La confirmación que sigue a soltar una tarjeta (spec §4.1). Nada se decide al soltar: el
 * gate se decide leyendo, y aquí está su resumen y el enlace a su pantalla completa.
 */
export function ConfirmarGate({ tarjeta, decision, onCerrar, onHecho }: Props) {
  const resumen = useCarga(() => cargarResumenDelGate(tarjeta.nombre), [tarjeta.nombre])
  const [comentario, setComentario] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [fallo, setFallo] = useState<unknown>(null)
  const fase = nombreDeFase(tarjeta.gate?.fase ?? '')
  const siguiente = columnaSiguiente(tarjeta)

  const confirmar = async () => {
    setEnviando(true)
    setFallo(null)
    try {
      await confirmarDecision(tarjeta.nombre, decision, comentario.trim())
      onHecho(
        decision === 'aprobar'
          ? `Aprobado el gate de ${fase} de «${tarjeta.titulo}». La novela se reanuda.`
          : `Pedido rehacer ${fase} de «${tarjeta.titulo}».`,
      )
    } catch (error) {
      setFallo(error)
      setEnviando(false)
    }
  }

  const titulo =
    decision === 'aprobar'
      ? `Aprobar ${fase}${siguiente ? ` y pasar a ${siguiente.titulo}` : ''}`
      : `Rehacer ${fase}`

  return (
    <Dialogo
      abierto
      titulo={titulo}
      onCerrar={onCerrar}
      acciones={
        <>
          <Boton variante="fantasma" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton onClick={confirmar} disabled={enviando}>
            {enviando ? 'Enviando…' : decision === 'aprobar' ? 'Confirmar aprobación' : 'Confirmar rehacer'}
          </Boton>
        </>
      }
    >
      <p>
        <strong>{tarjeta.titulo}</strong> espera tu decisión en el gate de {fase}.
      </p>
      {resumen.estado === 'cargando' && <EstadoCarga que="el resumen del gate" />}
      {resumen.estado === 'error' && <EstadoError error={resumen.error} onReintentar={resumen.reintentar} />}
      {resumen.estado === 'listo' && (
        <>
          <div className="rejilla-metricas">
            {resumen.datos.recuentos.map((r) => (
              <Metrica key={r.etiqueta} etiqueta={r.etiqueta} valor={r.valor} />
            ))}
          </div>
          {resumen.datos.preguntas.length > 0 && (
            <p className="aviso aviso-espera">
              El entrevistador tiene {resumen.datos.preguntas.length} pregunta(s) sin contestar. Se contestan en
              la pantalla del gate.
            </p>
          )}
        </>
      )}
      <p className="nota">
        <Link to={rutaGate(tarjeta.nombre)}>Leer el gate completo antes de decidir →</Link>
      </p>
      {decision === 'rehacer' && (
        <label className="campo">
          <span className="campo-etiqueta">Qué hay que cambiar</span>
          <textarea
            className="entrada"
            value={comentario}
            onChange={(e) => setComentario(e.target.value)}
            placeholder="El comentario se inyecta en el prompt de la fase: dirige el reintento."
          />
        </label>
      )}
      {fallo !== null && <EstadoError error={fallo} />}
    </Dialogo>
  )
}
