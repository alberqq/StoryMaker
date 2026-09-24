import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router'
import { rutaPanel } from '@/shared/config'
import { useCarga } from '@/shared/lib'
import { Boton, Campo, EstadoError, Seccion } from '@/shared/ui'
import { cargarEjemplos, comprobar, lanzar } from '../api/encargo'
import { aEncargo, aFormulario, campoDelError, type Formulario, VACIO } from '../model/brief'
import { Bloques } from './Bloques'
import { CasillaExhaustiva } from './CasillaExhaustiva'
import { Conversacion } from './Conversacion'
import './encargo.css'

type Modo = 'conversacion' | 'formulario'

/**
 * El encargo de una novela nueva (spec §4.2). Empieza por la conversación con el
 * entrevistador; el formulario completo queda para quien ya lo tiene todo decidido.
 */
export function Encargo() {
  const [modo, setModo] = useState<Modo>('conversacion')
  return (
    <div className="contenido contenido-encargo">
      <header className="cabecera-pagina">
        <div>
          <p className="miga">Taller / Nuevo encargo</p>
          <h1>Nuevo encargo</h1>
          <p className="subtitulo">
            {modo === 'conversacion'
              ? 'Cuéntale la novela al entrevistador: pregunta solo lo que falta.'
              : 'Todo el encargo de una vez. Solo el nombre del homenajeado es imprescindible.'}
          </p>
        </div>
        <div className="selector-modo" role="tablist" aria-label="Cómo quieres hacer el encargo">
          <button type="button" role="tab" aria-selected={modo === 'conversacion'} className={modo === 'conversacion' ? 'activo' : ''} onClick={() => setModo('conversacion')}>
            Conversación
          </button>
          <button type="button" role="tab" aria-selected={modo === 'formulario'} className={modo === 'formulario' ? 'activo' : ''} onClick={() => setModo('formulario')}>
            Formulario completo
          </button>
        </div>
      </header>
      {modo === 'conversacion' ? <Conversacion /> : <FormularioCompleto />}
    </div>
  )
}

function FormularioCompleto() {
  const navegar = useNavigate()
  const ejemplos = useCarga(cargarEjemplos, [])
  const [formulario, setFormulario] = useState<Formulario>(VACIO)
  const [nombre, setNombre] = useState('')
  const [batch, setBatch] = useState(false)
  const [exhaustiva, setExhaustiva] = useState(false)
  const [errores, setErrores] = useState<Record<string, string>>({})
  const [enviando, setEnviando] = useState(false)
  const [fallo, setFallo] = useState<unknown>(null)

  const cambiar = (cambio: Partial<Formulario>) => setFormulario((f) => ({ ...f, ...cambio }))

  const partirDe = (clave: string) => {
    if (ejemplos.estado !== 'listo') return
    const ejemplo = ejemplos.datos.find((e) => e.nombre === clave)
    if (ejemplo) {
      setFormulario(aFormulario(ejemplo.encargo))
      setErrores({})
    }
  }

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault()
    setEnviando(true)
    setFallo(null)
    const encargo = aEncargo(formulario)
    try {
      const validacion = await comprobar(encargo)
      if (!validacion.valido) {
        setErrores(Object.fromEntries(validacion.errores.map((e) => [campoDelError(e.campo), e.mensaje])))
        setEnviando(false)
        return
      }
      setErrores({})
      const lanzada = await lanzar(encargo, nombre.trim(), batch, exhaustiva)
      navegar(rutaPanel(lanzada.nombre))
    } catch (error) {
      setFallo(error)
      setEnviando(false)
    }
  }

  const hayErrores = Object.keys(errores).length > 0

  return (
    <>
      {ejemplos.estado === 'listo' && ejemplos.datos.length > 0 && (
        <label className="campo partir-de">
          <span className="campo-etiqueta">Partir de un ejemplo</span>
          <select className="entrada" defaultValue="" onChange={(e) => partirDe(e.target.value)}>
            <option value="" disabled>
              Elige un brief de ejemplo…
            </option>
            {ejemplos.datos.map((e) => (
              <option key={e.nombre} value={e.nombre}>
                {e.nombre}
              </option>
            ))}
          </select>
        </label>
      )}

      <form onSubmit={enviar} noValidate>
        {hayErrores && (
          <p className="aviso aviso-error" role="alert">
            Revisa los campos marcados antes de lanzar.
          </p>
        )}
        <Bloques formulario={formulario} errores={errores} cambiar={cambiar} />

        <Seccion titulo="4 · Lanzar">
          <div className="formulario-rejilla">
            <Campo etiqueta="Nombre de la novela" ayuda="Su carpeta en proyectos/. Si lo dejas vacío, el del homenajeado.">
              <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="salamanca" />
            </Campo>
            <fieldset className="modo">
              <legend className="campo-etiqueta">Cómo corre</legend>
              <label className={`opcion${!batch ? ' elegida' : ''}`}>
                <input type="radio" name="modo" checked={!batch} onChange={() => setBatch(false)} />
                <span>
                  <strong>Con gates</strong>
                  <span className="nota">Se detiene al cerrar cada fase y espera tu decisión.</span>
                </span>
              </label>
              <label className={`opcion${batch ? ' elegida' : ''}`}>
                <input type="radio" name="modo" checked={batch} onChange={() => setBatch(true)} />
                <span>
                  <strong>En batch</strong>
                  <span className="nota">Corre de principio a fin sin preguntar. El encargo tiene que venir completo.</span>
                </span>
              </label>
            </fieldset>
          </div>
          <CasillaExhaustiva marcada={exhaustiva} cambiar={setExhaustiva} />
          {fallo !== null && <EstadoError error={fallo} />}
          <div className="fila lanzar">
            <Boton type="submit" disabled={enviando}>
              {enviando ? 'Lanzando…' : 'Encargar y lanzar'}
            </Boton>
            <span className="nota">La novela aparecerá en el taller en unos segundos.</span>
          </div>
        </Seccion>
      </form>
    </>
  )
}
