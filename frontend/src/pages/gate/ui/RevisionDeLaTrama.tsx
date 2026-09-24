import type { RevisionDeLaTrama as Revision } from '@/shared/api'
import { Insignia } from '@/shared/ui'

const ETIQUETAS: Record<string, string> = {
  cobertura_anclada: 'Elemento sin anclar',
  cobertura_reparada: 'Anclado por el arnés',
  arco_anclado: 'Arco',
  escenas_por_capitulo: 'Escenas por capítulo',
  anclaje_resuelto: 'Anclaje sin resolver',
  cronologia_escaleta: 'Cronología',
  lean_cronologia: 'Cronología',
}

const RESULTADOS: Record<string, { texto: string; tono: 'verde' | 'azul' }> = {
  encontrado: { texto: 'encontrado', tono: 'verde' },
  inventado: { texto: 'inventado', tono: 'azul' },
}

/**
 * Lo que la revisión encontró en la escaleta y cómo se cubrieron los huecos (trama-rehacible
 * §3). No cierra el gate: explica por qué merecería la pena rehacer, y dice que rehacer ya
 * lleva estos avisos al arquitecto aunque el comentario quede vacío.
 */
export function RevisionDeLaTrama({ revision }: { revision: Revision }) {
  const { avisos, huecos, escenas_poco_firmes: pocoFirmes } = revision
  return (
    <div className="pila revision-trama">
      {avisos.length === 0 ? (
        <p className="aviso aviso-info">Cobertura, arcos y cronología en verde: la escaleta puede sellarse.</p>
      ) : (
        <>
          <ul className="lista-avisos">
            {avisos.map((a, i) => (
              <li key={i} className={a.grave ? 'aviso-grave' : undefined}>
                <Insignia tono={a.grave ? 'rojo' : 'ambar'}>{ETIQUETAS[a.validador] ?? a.validador}</Insignia>
                <span>{a.mensaje}</span>
              </li>
            ))}
          </ul>
          <p className="nota">
            Ninguno impide aprobar. Si rehaces, el arquitecto recibe estos avisos además de tu comentario.
          </p>
        </>
      )}

      {huecos.length > 0 && (
        <div className="pila-compacta">
          <h3>Huecos de la escaleta</h3>
          <ul className="lista-huecos">
            {huecos.map((h, i) => {
              const resultado = h.resultado ? RESULTADOS[h.resultado] : undefined
              return (
                <li key={i}>
                  <strong>{h.pregunta}</strong>{' '}
                  <span className="nota">
                    {h.capitulo != null ? `cap. ${h.capitulo} esc. ${h.escena}` : 'sin escena'}
                  </span>{' '}
                  <Insignia tono={resultado?.tono ?? 'gris'}>{resultado?.texto ?? 'sin cubrir'}</Insignia>
                  {h.enunciado && <p className="nota">{h.enunciado}</p>}
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {pocoFirmes.length > 0 && (
        <p className="nota">
          Solo se apoyan en hechos inferidos o desconocidos: {pocoFirmes.join(', ')}. Si alguna sostiene un giro,
          merece un ancla documentado.
        </p>
      )}
    </div>
  )
}
