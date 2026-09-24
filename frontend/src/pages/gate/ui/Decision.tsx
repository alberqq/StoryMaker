import { useState } from 'react'
import { Boton, Dialogo, EstadoError } from '@/shared/ui'
import { enviarDecision } from '../api/gate'

interface Props {
  id: string
  decisiones: string[]
  /**
   * Lo que se envía al aprobar en lugar de la casilla: en Regeneración, la fila elegida y su
   * valor nuevo. La casilla queda para rehacer.
   */
  comentarioAlAprobar?: string
  onHecho: (mensaje: string) => void
}

/**
 * Aprobar o rehacer con comentario, en todos los gates; abortar, solo donde el backend lo
 * ofrece —el gate de Intake— y con confirmación. Editar no está aquí: es el editor de filas.
 */
export function Decision({ id, decisiones, comentarioAlAprobar, onHecho }: Props) {
  const [comentario, setComentario] = useState('')
  const [enviando, setEnviando] = useState<string | null>(null)
  const [confirmarAbortar, setConfirmarAbortar] = useState(false)
  const [fallo, setFallo] = useState<unknown>(null)

  const enviar = async (decision: 'aprobar' | 'rehacer' | 'abortar') => {
    setConfirmarAbortar(false)
    setEnviando(decision)
    setFallo(null)
    try {
      const texto = decision === 'aprobar' && comentarioAlAprobar !== undefined ? comentarioAlAprobar : comentario.trim()
      await enviarDecision(id, decision, texto)
      onHecho(
        decision === 'aprobar'
          ? 'Gate aprobado. La novela se reanuda.'
          : decision === 'rehacer'
            ? 'Pedido rehacer la fase con tu comentario.'
            : 'Ejecución abortada.',
      )
    } catch (error) {
      setFallo(error)
      setEnviando(null)
    }
  }

  return (
    <div className="pila decision">
      <label className="campo">
        <span className="campo-etiqueta">Comentario</span>
        <textarea
          className="entrada"
          value={comentario}
          onChange={(e) => setComentario(e.target.value)}
          placeholder="Para rehacer: qué hay que cambiar. Se inyecta en el prompt de la fase y dirige el reintento."
        />
      </label>
      <div className="fila">
        <Boton onClick={() => enviar('aprobar')} disabled={enviando !== null}>
          {enviando === 'aprobar' ? 'Enviando…' : 'Aprobar'}
        </Boton>
        <Boton variante="secundario" onClick={() => enviar('rehacer')} disabled={enviando !== null}>
          {enviando === 'rehacer' ? 'Enviando…' : 'Rehacer con el comentario'}
        </Boton>
        {decisiones.includes('abortar') && (
          <Boton variante="peligro" onClick={() => setConfirmarAbortar(true)} disabled={enviando !== null}>
            Abortar
          </Boton>
        )}
      </div>
      {fallo !== null && <EstadoError error={fallo} />}
      <Dialogo
        abierto={confirmarAbortar}
        titulo="Abortar la novela"
        onCerrar={() => setConfirmarAbortar(false)}
        acciones={
          <>
            <Boton variante="fantasma" onClick={() => setConfirmarAbortar(false)}>
              Cancelar
            </Boton>
            <Boton variante="peligro" onClick={() => enviar('abortar')}>
              Sí, abortar
            </Boton>
          </>
        }
      >
        <p>La ejecución termina con estado de error. No se deshace: habría que encargar la novela otra vez.</p>
      </Dialogo>
    </div>
  )
}
