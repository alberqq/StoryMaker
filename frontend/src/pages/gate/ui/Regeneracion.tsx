import type { GateDeNovela } from '@/shared/api'
import { type CandidatoDeRegeneracion, elegible } from '../model/eleccion'

interface Props {
  peticion: NonNullable<GateDeNovela['peticion']>
  /** El índice del candidato elegido, o `null` si no hay ninguno elegible. */
  elegido: number | null
  valor: string
  onElegir: (indice: number) => void
  onValor: (valor: string) => void
}

const ETIQUETA_DEL_OBJETO: Record<string, string> = {
  hecho: 'Hecho',
  personaje: 'Personaje',
  escenario: 'Lugar',
  glosario: 'Glosario',
}

function alcance(c: CandidatoDeRegeneracion) {
  const regenera = c.capitulos_a_regenerar.length
  return (
    <>
      Regenera {regenera ? `${regenera === 1 ? 'el capítulo' : `${regenera} capítulos:`} ${c.capitulos_a_regenerar.join(', ')}` : 'ningún capítulo'}
      {c.capitulos_a_revisar.length > 0 && ` · revisa ${c.capitulos_a_revisar.join(', ')}`}
    </>
  )
}

/**
 * La petición que abrió la Fase 6 y los candidatos que se calcularon al registrarla, como
 * opciones: el Autor elige la fila y escribe su valor nuevo (spec §4.4).
 */
export function Regeneracion({ peticion, elegido, valor, onElegir, onValor }: Props) {
  const candidato = elegido != null ? peticion.candidatos[elegido] : undefined
  return (
    <div className="pila">
      <blockquote className="cita-peticion">
        {peticion.texto}
        {peticion.fragmento && <span className="nota"> — sobre «{peticion.fragmento}»</span>}
      </blockquote>
      {peticion.candidatos.length === 0 ? (
        <p className="nota">La búsqueda no encontró ningún candidato: aprobar deja pasar la regeneración sin tocar nada.</p>
      ) : (
        <fieldset className="candidatos">
          <legend className="campo-etiqueta">¿Qué fila hay que cambiar?</legend>
          {peticion.candidatos.map((c, i) => (
            <label key={i} className={`candidato${elegido === i ? ' candidato-elegido' : ''}`}>
              <input
                type="radio"
                name="candidato"
                checked={elegido === i}
                disabled={!elegible(c)}
                onChange={() => onElegir(i)}
              />
              <span className="pila-compacta">
                <strong>
                  {c.objeto && <span className="nota">{ETIQUETA_DEL_OBJETO[c.objeto] ?? c.objeto} · </span>}
                  {c.descripcion}
                </strong>
                <span className="nota">{alcance(c)}</span>
                {c.coste && <span className="nota">{c.coste}</span>}
                {!elegible(c) && <span className="nota">Registrado sin su fila: no se puede elegir.</span>}
              </span>
            </label>
          ))}
        </fieldset>
      )}
      {candidato && (
        <label className="campo">
          <span className="campo-etiqueta">Valor nuevo · {candidato.campo}</span>
          <textarea
            className="entrada"
            rows={candidato.campo === 'nombre' || candidato.campo === 'termino' ? 1 : 3}
            value={valor}
            onChange={(e) => onValor(e.target.value)}
          />
          <span className="nota">
            {valor.trim() === candidato.valor.trim()
              ? 'Sin cambiar el valor, aprobar no toca nada.'
              : `Al aprobar: ${candidato.objeto}:${candidato.fila_id} ${candidato.campo}=${valor.trim()}`}
          </span>
        </label>
      )}
    </div>
  )
}
