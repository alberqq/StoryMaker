import { useState } from 'react'
import type { FilaEditable } from '@/shared/api'
import { Boton, EstadoError, Insignia } from '@/shared/ui'
import { guardarEdicion } from '../api/gate'

const FAMILIAS: Record<FilaEditable['objeto'], string> = {
  hecho: 'Hechos del corpus',
  personaje: 'Personajes',
  escenario: 'Escenarios',
  glosario: 'Glosario',
}

interface Props {
  id: string
  filas: FilaEditable[]
  corpusSellado: boolean
}

/**
 * La edición humana directa (arq. §8 y §16.5): cada cambio se guarda en el acto, con su
 * motivo, y queda trazado. Después se aprueba o se rehace; la pantalla no envía «editar».
 */
export function Editor({ id, filas, corpusSellado }: Props) {
  const [familia, setFamilia] = useState<FilaEditable['objeto']>('personaje')
  const visibles = filas.filter((f) => f.objeto === familia)
  return (
    <div className="pila editor">
      <div className="fila">
        {(Object.keys(FAMILIAS) as FilaEditable['objeto'][]).map((f) => (
          <Boton
            key={f}
            tamano="pequeno"
            variante={f === familia ? 'primario' : 'secundario'}
            onClick={() => setFamilia(f)}
          >
            {FAMILIAS[f]} ({filas.filter((x) => x.objeto === f).length})
          </Boton>
        ))}
      </div>
      {familia === 'hecho' && corpusSellado && (
        <p className="aviso aviso-info">El corpus está sellado: sus hechos se consultan pero ya no se editan.</p>
      )}
      {visibles.length === 0 ? (
        <p className="nota">Nada que editar en esta familia.</p>
      ) : (
        <ul className="filas-editables">
          {visibles.map((fila) => (
            <FilaDelEditor key={`${fila.objeto}-${fila.fila_id}`} id={id} fila={fila} />
          ))}
        </ul>
      )}
    </div>
  )
}

function FilaDelEditor({ id, fila }: { id: string; fila: FilaEditable }) {
  const [valores, setValores] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(fila.campos).map(([k, v]) => [k, v ?? ''])),
  )
  const [motivo, setMotivo] = useState('')
  const [guardado, setGuardado] = useState<string | null>(null)
  const [fallo, setFallo] = useState<unknown>(null)
  const cambiados = Object.entries(valores).filter(([k, v]) => v !== (fila.campos[k] ?? '') && v.trim())

  const guardar = async () => {
    setFallo(null)
    try {
      for (const [campo, valor] of cambiados) {
        await guardarEdicion(id, { objeto: fila.objeto, fila_id: fila.fila_id, campo, valor, motivo })
      }
      setGuardado(`Guardado: ${cambiados.map(([c]) => c).join(', ')}`)
    } catch (error) {
      setFallo(error)
    }
  }

  return (
    <li className="fila-editable">
      <div className="fila-entre">
        <strong>{fila.etiqueta}</strong>
        {!fila.editable && <Insignia>solo lectura</Insignia>}
      </div>
      {Object.keys(valores).map((campo) => (
        <label className="campo" key={campo}>
          <span className="campo-etiqueta">{campo}</span>
          {campo === 'enunciado' || campo === 'significado' || campo === 'descripcion' ? (
            <textarea
              className="entrada"
              value={valores[campo]}
              disabled={!fila.editable}
              onChange={(e) => setValores((v) => ({ ...v, [campo]: e.target.value }))}
            />
          ) : (
            <input
              className="entrada"
              value={valores[campo]}
              disabled={!fila.editable}
              onChange={(e) => setValores((v) => ({ ...v, [campo]: e.target.value }))}
            />
          )}
        </label>
      ))}
      {fila.editable && cambiados.length > 0 && (
        <div className="fila">
          <input
            className="entrada motivo"
            placeholder="Motivo del cambio (queda en la traza)"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
          <Boton tamano="pequeno" onClick={guardar}>
            Guardar
          </Boton>
        </div>
      )}
      {guardado && <p className="nota">{guardado}</p>}
      {fallo !== null && <EstadoError error={fallo} />}
    </li>
  )
}
