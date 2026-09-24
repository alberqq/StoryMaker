import { useState } from 'react'
import { Corpus } from '@/entities/hecho'
import type { Hecho } from '@/shared/api'
import { useCarga } from '@/shared/lib'
import { Boton, Dialogo, EstadoCarga, EstadoError } from '@/shared/ui'
import { cargarCorpus, descartar, guardarEdicion } from '../api/gate'

interface Props {
  id: string
  corpusSellado: boolean
}

/**
 * El corpus en el gate de Investigation, como en su salida y con dos acciones por hecho:
 * corregir el enunciado y descartarlo. Las dos se escriben en el acto y quedan trazadas;
 * después se aprueba o se rehace (spec gate-investigacion §2).
 */
export function CorpusDelGate({ id, corpusSellado }: Props) {
  const carga = useCarga(() => cargarCorpus(id), [id])
  const [editando, setEditando] = useState<number | null>(null)
  const [texto, setTexto] = useState('')
  const [aDescartar, setADescartar] = useState<Hecho | null>(null)
  const [motivo, setMotivo] = useState('')
  const [aviso, setAviso] = useState<string | null>(null)
  const [fallo, setFallo] = useState<unknown>(null)
  // Lo hecho desde que se cargó: se aplica en el sitio, sin recargar, para no perder la
  // pestaña en la que está el Autor.
  const [descartados, setDescartados] = useState<ReadonlySet<number>>(new Set())
  const [corregidos, setCorregidos] = useState<Record<number, string>>({})

  if (carga.estado === 'cargando') return <EstadoCarga que="el corpus" />
  if (carga.estado === 'error') return <EstadoError error={carga.error} onReintentar={carga.reintentar} />

  const hecho = async (accion: () => Promise<unknown>, mensaje: string, despues: () => void) => {
    setFallo(null)
    try {
      await accion()
      despues()
      setAviso(mensaje)
      setEditando(null)
      setADescartar(null)
      setMotivo('')
    } catch (error) {
      setFallo(error)
    }
  }

  const corregir = (h: Hecho) => {
    const valor = texto.trim()
    return hecho(
      () => guardarEdicion(id, { objeto: 'hecho', fila_id: h.id, campo: 'enunciado', valor, motivo }),
      'Hecho corregido.',
      () => setCorregidos((c) => ({ ...c, [h.id]: valor })),
    )
  }

  const quitar = (h: Hecho) =>
    hecho(
      () => descartar(id, h.id, motivo.trim()),
      'Hecho descartado.',
      () => setDescartados((d) => new Set(d).add(h.id)),
    )

  const hechos = carga.datos
    .filter((h) => !descartados.has(h.id))
    .map((h) => (corregidos[h.id] != null ? { ...h, enunciado: corregidos[h.id]! } : h))

  const acciones = (h: Hecho) =>
    corpusSellado || editando === h.id ? null : (
      <>
        <Boton
          tamano="pequeno"
          variante="secundario"
          onClick={() => {
            setEditando(h.id)
            setTexto(h.enunciado)
            setMotivo('')
          }}
        >
          Corregir
        </Boton>
        <Boton tamano="pequeno" variante="peligro" onClick={() => setADescartar(h)}>
          Descartar
        </Boton>
      </>
    )

  const enunciado = (h: Hecho) =>
    editando !== h.id ? undefined : (
      <div className="pila">
        <textarea
          className="entrada"
          aria-label="Enunciado"
          rows={3}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
        />
        <input
          className="entrada"
          placeholder="Motivo del cambio (opcional)"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        />
        <div className="fila">
          <Boton tamano="pequeno" onClick={() => corregir(h)} disabled={!texto.trim() || texto.trim() === h.enunciado}>
            Guardar
          </Boton>
          <Boton tamano="pequeno" variante="fantasma" onClick={() => setEditando(null)}>
            Cancelar
          </Boton>
        </div>
      </div>
    )

  return (
    <div className="pila">
      {corpusSellado ? (
        <p className="aviso aviso-info">El corpus está sellado: sus hechos se consultan pero ya no se tocan.</p>
      ) : (
        <p className="nota">
          Corrige un enunciado que el investigador adornó o descarta lo que no quieras en la novela. Cada cambio se
          guarda al momento; luego apruebas para seguir con el corpus así, o rehaces la investigación entera.
        </p>
      )}
      {aviso && (
        <p className="aviso aviso-ok" role="status">
          {aviso}
        </p>
      )}
      {fallo !== null && <EstadoError error={fallo} />}
      <Corpus hechos={hechos} acciones={acciones} enunciado={enunciado} />
      <Dialogo
        abierto={aDescartar !== null}
        titulo="Descartar el hecho"
        onCerrar={() => setADescartar(null)}
        acciones={
          <>
            <Boton variante="fantasma" onClick={() => setADescartar(null)}>
              Cancelar
            </Boton>
            <Boton
              variante="peligro"
              onClick={() => aDescartar && quitar(aDescartar)}
            >
              Sí, descartar
            </Boton>
          </>
        }
      >
        <p>«{aDescartar?.enunciado}»</p>
        <p className="nota">Sale del corpus y no llegará a la Trama ni a la Escritura. Queda trazado quién lo quitó y por qué.</p>
        <input
          className="entrada"
          placeholder="Por qué lo descartas (opcional)"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        />
      </Dialogo>
    </div>
  )
}
