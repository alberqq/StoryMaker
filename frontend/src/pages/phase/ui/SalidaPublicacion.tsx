import { Link } from 'react-router'
import { type SalidaPublicacion as Salida, urlDelPdf } from '@/shared/api'
import { rutaImprimir, rutaIndice } from '@/shared/config'
import { formatearFecha, formatearPuntuacion } from '@/shared/lib'
import { EstadoVacio, Insignia, Progreso, Seccion } from '@/shared/ui'

const CRITERIOS: Record<string, string> = {
  continuidad: 'Continuidad',
  arco: 'Arco',
  coherencia_de_personajes: 'Coherencia de personajes',
  ritmo: 'Ritmo',
  prosa: 'Prosa',
  naturalidad_de_la_personalizacion: 'Naturalidad de la personalización',
  autenticidad_de_epoca: 'Autenticidad de época',
}

/** Las versiones publicadas con su manifiesto, y la rúbrica del juez por criterio. */
export function SalidaPublicacion({ id, salida }: { id: string; salida: Salida }) {
  if (salida.versiones.length === 0 && salida.rubricas.length === 0)
    return <EstadoVacio>Todavía no se ha publicado ninguna versión.</EstadoVacio>
  return (
    <>
      {salida.rubricas.length > 0 && (
        <Seccion titulo="La rúbrica del juez">
          {salida.rubricas.map((r, i) => (
            <div key={i} className="pila rubrica">
              <div className="fila">
                <strong>Juicio {i + 1}</strong>
                <Insignia tono={r.media >= 6 ? 'verde' : 'ambar'}>media {formatearPuntuacion(r.media)}</Insignia>
              </div>
              <ul className="criterios">
                {r.criterios.map((c) => (
                  <li key={c.criterio}>
                    <span>{CRITERIOS[c.criterio] ?? c.criterio}</span>
                    <Progreso valor={c.valor} max={10} tono={c.valor >= 6 ? 'verde' : 'ambar'} etiqueta={CRITERIOS[c.criterio] ?? c.criterio} />
                    <span className="mono">{c.valor}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </Seccion>
      )}
      {salida.versiones.map((v) => (
        <Seccion
          key={v.numero}
          titulo={`Versión ${v.numero}`}
          extra={
            <div className="fila">
              <Link className="boton boton-secundario boton-pequeno" to={rutaIndice(id, v.numero)}>Leer</Link>
              <Link className="boton boton-fantasma boton-pequeno" to={rutaImprimir(id, v.numero)}>Imprimir</Link>
              <a className="boton boton-fantasma boton-pequeno" href={urlDelPdf(id, v.numero)} download>PDF</a>
            </div>
          }
        >
          <p className="nota">Publicada el {formatearFecha(v.creada_en)} · {v.capitulos} capítulos</p>
          {v.manifiesto && (
            <dl className="pares">
              <div><dt>Brief</dt><dd className="mono">{v.manifiesto.brief_hash.slice(0, 16)}…</dd></div>
              <div><dt>Sello del corpus</dt><dd className="mono">{v.manifiesto.sello_corpus_hash.slice(0, 16)}…</dd></div>
              <div><dt>Modelos</dt><dd className="mono">{v.manifiesto.modelos}</dd></div>
              <div><dt>Embeddings</dt><dd className="mono">{v.manifiesto.embeddings}</dd></div>
              <div><dt>Gates</dt><dd>{v.manifiesto.gates_enabled ? 'activados' : 'desactivados (batch)'}</dd></div>
            </dl>
          )}
        </Seccion>
      ))}
    </>
  )
}
