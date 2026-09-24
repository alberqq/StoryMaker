import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router'
import { rutaGate } from '@/shared/config'
import { Boton, Campo, EstadoError } from '@/shared/ui'
import { comprobar, lanzar } from '../api/encargo'
import { CasillaExhaustiva } from './CasillaExhaustiva'
import { campoDelError, encargoDeConversacion } from '../model/brief'

/**
 * El encargo por conversación (spec §4.2): a quién se regala y la novela contada con tus
 * palabras. El entrevistador lo lee y pregunta solo por lo que falta; la conversación sigue
 * en la pantalla del gate. Sin gates no hay entrevista, así que este modo nunca va en batch.
 */
export function Conversacion() {
  const navegar = useNavigate()
  const [homenajeado, setHomenajeado] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [nombre, setNombre] = useState('')
  const [exhaustiva, setExhaustiva] = useState(false)
  const [errores, setErrores] = useState<Record<string, string>>({})
  const [enviando, setEnviando] = useState(false)
  const [fallo, setFallo] = useState<unknown>(null)

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault()
    setEnviando(true)
    setFallo(null)
    const encargo = encargoDeConversacion(homenajeado, descripcion)
    try {
      const validacion = await comprobar(encargo)
      if (!validacion.valido) {
        setErrores(Object.fromEntries(validacion.errores.map((e) => [campoDelError(e.campo), e.mensaje])))
        setEnviando(false)
        return
      }
      const lanzada = await lanzar(encargo, nombre.trim(), false, exhaustiva)
      navegar(rutaGate(lanzada.nombre))
    } catch (error) {
      setFallo(error)
      setEnviando(false)
    }
  }

  return (
    <form className="seccion conversacion-encargo" onSubmit={enviar} noValidate>
      <div className="seccion-cuerpo pila">
        <div className="burbuja burbuja-agente">
          <span className="burbuja-autor">Entrevistador</span>
          <p>
            Cuéntame la novela que quieres regalar: a quién, por qué, en qué época y lugar te la imaginas, qué de su vida
            no puede faltar, qué tono… Con tus palabras y sin orden. Lo que no digas te lo preguntaré yo.
          </p>
        </div>
        <Campo etiqueta="¿A quién se regala?" obligatorio error={errores.nombre_homenajeado}>
          <input
            value={homenajeado}
            onChange={(e) => setHomenajeado(e.target.value)}
            placeholder="Su nombre, tal como debe escribirse en la novela"
          />
        </Campo>
        <Campo etiqueta="La novela, con tus palabras" ayuda="Cuanto más cuentes, menos te preguntará.">
          <textarea
            className="descripcion-encargo"
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
            placeholder="Mi padre se jubila tras cuarenta años en el puerto de Cádiz. Me gustaría una novela de aventuras en el Cádiz de 1812, con él como piloto de un barco… No puede faltar su perro Nala."
          />
        </Campo>
        <Campo etiqueta="Nombre de la novela" ayuda="Su carpeta en proyectos/. Si lo dejas vacío, el del homenajeado.">
          <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="cadiz" />
        </Campo>
        <CasillaExhaustiva marcada={exhaustiva} cambiar={setExhaustiva} />
        {fallo !== null && <EstadoError error={fallo} />}
        <div className="fila">
          <Boton type="submit" disabled={enviando}>
            {enviando ? 'Enviando…' : 'Empezar la entrevista'}
          </Boton>
          <span className="nota">Corre con gates: la conversación sigue en la pantalla del gate de Encargo.</span>
        </div>
      </div>
    </form>
  )
}
