import { useState } from 'react'
import { Link } from 'react-router'
import type { Panel } from '@/shared/api'
import { rutaGate } from '@/shared/config'
import { Boton, Dialogo, EstadoError } from '@/shared/ui'
import { lanzarContinuar, lanzarReintento, romperCerrojo } from '../api/panel'
import { type Accion, accionesDe, pideConfirmacion } from '../model/acciones'

interface Props {
  panel: Panel
  onHecho: (mensaje: string) => void
}

const TEXTOS: Record<Exclude<Accion, 'decidir'>, string> = {
  continuar: 'Continuar',
  reintentar: 'Reintentar el capítulo',
  desbloquear: 'Desbloquear',
}

/** Las acciones que el estado de la novela admite, y solo esas. */
export function Acciones({ panel, onHecho }: Props) {
  const [enCurso, setEnCurso] = useState<Accion | null>(null)
  const [confirmando, setConfirmando] = useState<Accion | null>(null)
  const [fallo, setFallo] = useState<unknown>(null)
  const acciones = accionesDe(panel)

  const ejecutar = async (accion: Accion) => {
    setConfirmando(null)
    setEnCurso(accion)
    setFallo(null)
    try {
      if (accion === 'continuar') onHecho((await lanzarContinuar(panel.nombre)).mensaje)
      if (accion === 'reintentar') onHecho((await lanzarReintento(panel.nombre)).mensaje)
      if (accion === 'desbloquear') onHecho((await romperCerrojo(panel.nombre)).mensaje)
    } catch (error) {
      setFallo(error)
    } finally {
      setEnCurso(null)
    }
  }

  if (acciones.length === 0) return null
  return (
    <div className="pila acciones">
      <div className="fila">
        {acciones.map((accion, i) =>
          accion === 'decidir' ? (
            <Link key={accion} className="boton boton-primario" to={rutaGate(panel.nombre)}>
              Decidir el gate
            </Link>
          ) : (
            <Boton
              key={accion}
              variante={i === 0 ? 'primario' : 'secundario'}
              disabled={enCurso !== null}
              onClick={() => (pideConfirmacion(accion) ? setConfirmando(accion) : ejecutar(accion))}
            >
              {enCurso === accion ? 'Lanzando…' : TEXTOS[accion]}
            </Boton>
          ),
        )}
      </div>
      {fallo !== null && <EstadoError error={fallo} />}
      <Dialogo
        abierto={confirmando === 'desbloquear'}
        titulo="Desbloquear la novela"
        onCerrar={() => setConfirmando(null)}
        acciones={
          <>
            <Boton variante="fantasma" onClick={() => setConfirmando(null)}>
              Cancelar
            </Boton>
            <Boton variante="peligro" onClick={() => ejecutar('desbloquear')}>
              Romper el cerrojo
            </Boton>
          </>
        }
      >
        <p>
          El proceso que tenía el cerrojo de esta novela ya no vive
          {panel.proceso.pid ? ` (PID ${panel.proceso.pid})` : ''}. Romperlo permite continuarla desde su último
          checkpoint. Solo se rompe un cerrojo huérfano.
        </p>
      </Dialogo>
    </div>
  )
}
