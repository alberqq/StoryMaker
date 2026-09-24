import { useState } from 'react'
import { Boton, EstadoError } from '@/shared/ui'
import { enviarDecision } from '../api/gate'

interface Props {
  id: string
  preguntas: string[]
  onHecho: (mensaje: string) => void
}

/** Las respuestas numeradas como comentario de «rehacer», que es como se contesta la entrevista. */
export const comoComentario = (preguntas: string[], respuestas: string[]) =>
  preguntas
    .map((p, i) => ({ p, r: (respuestas[i] ?? '').trim(), i }))
    .filter(({ r }) => r)
    .map(({ p, r, i }) => `${i + 1}. ${p}\n   ${r}`)
    .join('\n')

/**
 * La entrevista del gate de Intake (arq. §4, Fase 1): cada pregunta con su casilla. Contestar
 * es rehacer con las respuestas como comentario; `Configure` vuelve a correr con todas.
 */
export function Preguntas({ id, preguntas, onHecho }: Props) {
  const [respuestas, setRespuestas] = useState<string[]>(() => preguntas.map(() => ''))
  const [enviando, setEnviando] = useState(false)
  const [fallo, setFallo] = useState<unknown>(null)
  const contestadas = respuestas.filter((r) => r.trim()).length

  const enviar = async () => {
    setEnviando(true)
    setFallo(null)
    try {
      await enviarDecision(id, 'rehacer', comoComentario(preguntas, respuestas))
      onHecho('Respuestas enviadas. La entrevista vuelve a correr con ellas.')
    } catch (error) {
      setFallo(error)
      setEnviando(false)
    }
  }

  return (
    <div className="pila preguntas">
      <p className="nota">
        El entrevistador pregunta solo por lo que falta o es ambiguo. Contesta lo que sepas; si apruebas con preguntas
        pendientes, la novela sigue con el brief que haya.
      </p>
      <ol className="lista-preguntas">
        {preguntas.map((pregunta, i) => (
          <li key={i}>
            <label className="campo">
              <span className="campo-etiqueta">{pregunta}</span>
              <textarea
                className="entrada"
                value={respuestas[i] ?? ''}
                onChange={(e) => setRespuestas((r) => r.map((x, j) => (j === i ? e.target.value : x)))}
              />
            </label>
          </li>
        ))}
      </ol>
      <div className="fila">
        <Boton onClick={enviar} disabled={enviando || contestadas === 0}>
          {enviando ? 'Enviando…' : `Enviar ${contestadas} respuesta(s)`}
        </Boton>
      </div>
      {fallo !== null && <EstadoError error={fallo} />}
    </div>
  )
}
