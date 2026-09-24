import { type FormEvent, type RefObject, useState } from 'react'
import { tipoDeError } from '@/shared/api'
import { Boton, Tarjeta } from '@/shared/ui'
import { useSeleccion } from '@/shared/lib'
import { enviarPeticion } from '../api/pedir-cambio'

interface Props {
  id: string
  version: number
  capitulo: number
  /** El elemento que contiene el texto del capítulo: solo cuenta lo seleccionado ahí. */
  texto: RefObject<HTMLElement | null>
}

type Envio =
  | { estado: 'editando' }
  | { estado: 'enviando' }
  | { estado: 'registrada' }
  | { estado: 'rechazada'; ocupada: boolean; mensaje: string }

/**
 * La petición de cambio del lector (spec §5). No resuelve nada: la registra, y quien decide
 * es el Autor en su gate. No hay espera ni sondeo, y un rechazo por novela ocupada se cuenta
 * tal cual, sin reintento automático ni cola.
 */
export function PeticionCambio({ id, version, capitulo, texto }: Props) {
  const seleccion = useSeleccion(texto)
  const [peticion, setPeticion] = useState('')
  const [envio, setEnvio] = useState<Envio>({ estado: 'editando' })

  const hayFragmento = seleccion.fragmento !== ''
  const puedeEnviar = hayFragmento && peticion.trim() !== '' && envio.estado !== 'enviando'

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (!puedeEnviar) return
    setEnvio({ estado: 'enviando' })
    try {
      await enviarPeticion(id, {
        texto: peticion.trim(),
        fragmento: seleccion.fragmento,
        capitulo: Number(seleccion.origen ?? capitulo),
        version,
      })
      setEnvio({ estado: 'registrada' })
      setPeticion('')
      seleccion.limpiar()
    } catch (error) {
      setEnvio({
        estado: 'rechazada',
        ocupada: tipoDeError(error) === 'ocupada',
        mensaje: error instanceof Error ? error.message : '',
      })
    }
  }

  return (
    <Tarjeta titulo="Pedir un cambio" className="no-imprimir">
      {envio.estado === 'registrada' && (
        <p role="status">
          Tu petición ha quedado registrada. El Autor la revisará antes de que nada cambie; la
          novela cambiará cuando aparezca una versión nueva en el historial.
        </p>
      )}
      {envio.estado === 'rechazada' && (
        <p role="alert">
          {envio.ocupada
            ? 'Hay una ejecución en curso sobre esta novela y la petición no se ha registrado. Vuelve a enviarla más tarde.'
            : `La petición no se ha podido registrar. ${envio.mensaje}`}
        </p>
      )}
      <form onSubmit={enviar}>
        {hayFragmento ? (
          <blockquote aria-label="Fragmento seleccionado">{seleccion.fragmento}</blockquote>
        ) : (
          <p className="nota">Selecciona en el texto el fragmento que quieres cambiar.</p>
        )}
        <label>
          <span className="nota">Qué quieres cambiar</span>
          <textarea
            value={peticion}
            onChange={(e) => setPeticion(e.target.value)}
            disabled={!hayFragmento}
            placeholder="Por ejemplo: el perro se llama Nala, no Toby"
          />
        </label>
        <Boton type="submit" disabled={!puedeEnviar}>
          {envio.estado === 'enviando' ? 'Enviando…' : 'Enviar petición'}
        </Boton>
      </form>
    </Tarjeta>
  )
}
