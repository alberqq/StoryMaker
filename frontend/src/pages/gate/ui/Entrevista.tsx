import type { Conversacion } from '@/shared/api'
import { Boton } from '@/shared/ui'
import { Preguntas } from './Preguntas'

interface Ronda {
  pares: { pregunta: string; respuesta: string }[]
  libre: string | null
}

/**
 * Una ronda tal como quedó en el comentario de «rehacer»: «1. pregunta» y debajo, sangrada,
 * la respuesta. Si el comentario no tiene esa forma —se escribió a mano en la CLI—, se
 * enseña entero como respuesta libre.
 */
export function leerRonda(comentario: string): Ronda {
  const pares: Ronda['pares'] = []
  for (const linea of comentario.split('\n')) {
    const numerada = /^\s*\d+\.\s+(.*)$/.exec(linea)
    if (numerada) pares.push({ pregunta: numerada[1] ?? '', respuesta: '' })
    else if (pares.length > 0 && linea.trim()) {
      const ultimo = pares[pares.length - 1]!
      ultimo.respuesta = [ultimo.respuesta, linea.trim()].filter(Boolean).join(' ')
    }
  }
  return pares.length > 0 && pares.every((p) => p.respuesta) ? { pares, libre: null } : { pares: [], libre: comentario }
}

const TITULOS_DEL_BRIEF: Record<string, string> = {
  nombre_homenajeado: 'Homenajeado',
  ocasion: 'Ocasión',
  rol_epoca: 'Su papel',
  lugar: 'Lugar',
  genero: 'Género',
  tono: 'Tono',
  evento_ancla: 'Evento ancla',
  n_capitulos: 'Capítulos',
}

function Burbuja({ quien, children }: { quien: 'agente' | 'autor'; children: React.ReactNode }) {
  return (
    <div className={`burbuja burbuja-${quien}`}>
      <span className="burbuja-autor">{quien === 'agente' ? 'Entrevistador' : 'Tú'}</span>
      {children}
    </div>
  )
}

interface Props {
  id: string
  conversacion: Conversacion
  preguntas: string[]
  /** Se acaban de enviar respuestas y el entrevistador todavía no ha contestado. */
  pensando: boolean
  onEnviadas: () => void
  onAprobar: () => void
}

/**
 * La entrevista de Intake como conversación (spec §4.4): lo que se contó, cada ronda con sus
 * respuestas y las preguntas nuevas con su casilla. Sin preguntas, el brief cerrado.
 */
export function Entrevista({ id, conversacion, preguntas, pensando, onEnviadas, onAprobar }: Props) {
  const brief = conversacion.brief
  return (
    <div className="chat" aria-label="Conversación con el entrevistador">
      {conversacion.descripcion && (
        <Burbuja quien="autor">
          <p className="texto-libre">{conversacion.descripcion}</p>
        </Burbuja>
      )}
      {conversacion.rondas.map((comentario, i) => {
        const ronda = leerRonda(comentario)
        return ronda.libre !== null ? (
          <Burbuja key={i} quien="autor">
            <p className="texto-libre">{ronda.libre}</p>
          </Burbuja>
        ) : (
          <div key={i} className="pila ronda">
            <Burbuja quien="agente">
              <ol>
                {ronda.pares.map((p, j) => (
                  <li key={j}>{p.pregunta}</li>
                ))}
              </ol>
            </Burbuja>
            <Burbuja quien="autor">
              <ol>
                {ronda.pares.map((p, j) => (
                  <li key={j}>{p.respuesta}</li>
                ))}
              </ol>
            </Burbuja>
          </div>
        )
      })}

      {pensando ? (
        <div className="burbuja burbuja-agente burbuja-pensando" role="status">
          <span className="burbuja-autor">Entrevistador</span>
          <span className="puntos" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span>está leyendo tus respuestas…</span>
        </div>
      ) : preguntas.length > 0 ? (
        <Burbuja quien="agente">
          <p>Para cerrar el encargo necesito saber:</p>
          <Preguntas id={id} preguntas={preguntas} onHecho={onEnviadas} />
        </Burbuja>
      ) : (
        <Burbuja quien="agente">
          <p>
            <strong>Tengo todo lo que necesito.</strong>{' '}
            {brief ? 'Este es el encargo tal como lo he cerrado:' : 'Puedes aprobar para pasar a la Investigación.'}
          </p>
          {brief && (
            <dl className="pares-brief">
              {Object.entries(TITULOS_DEL_BRIEF)
                .filter(([clave]) => brief[clave] != null && brief[clave] !== '')
                .map(([clave, titulo]) => (
                  <div key={clave}>
                    <dt>{titulo}</dt>
                    <dd>{String(brief[clave])}</dd>
                  </div>
                ))}
            </dl>
          )}
          <div className="fila">
            <Boton onClick={onAprobar}>Aprobar y pasar a la Investigación</Boton>
          </div>
        </Burbuja>
      )}
    </div>
  )
}
