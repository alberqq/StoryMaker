import type { SalidaTrama as Salida } from '@/shared/api'
import { EstadoVacio, Insignia, Seccion, Tabla } from '@/shared/ui'

const TIPOS: Record<string, string> = {
  inventado: 'Inventado',
  historico_ficcionalizado: 'Histórico ficcionalizado',
  historico_de_fondo: 'Histórico de fondo',
}

/** El canon y la escaleta: lo que el arquitecto dejó escrito para que la novela se escriba. */
export function SalidaTrama({ salida }: { salida: Salida }) {
  if (!salida.obra && salida.escaleta.length === 0)
    return <EstadoVacio>La Trama todavía no ha dejado canon ni escaleta.</EstadoVacio>
  const obra = salida.obra
  return (
    <>
      {obra && (
        <Seccion titulo={obra.titulo ?? 'La obra'}>
          <dl className="pares">
            {obra.premisa && (<div><dt>Premisa</dt><dd>{obra.premisa}</dd></div>)}
            {obra.tema && (<div><dt>Tema</dt><dd>{obra.tema}</dd></div>)}
            {obra.genero && (<div><dt>Género</dt><dd>{obra.genero}</dd></div>)}
            {obra.voz && (<div><dt>Voz</dt><dd>{obra.voz}</dd></div>)}
            <div><dt>Extensión</dt><dd>{obra.n_capitulos} capítulos de unas {obra.palabras_por_capitulo} palabras</dd></div>
            {obra.estilo && Object.entries(obra.estilo).map(([k, v]) => (<div key={k}><dt>{k.replaceAll('_', ' ')}</dt><dd>{String(v)}</dd></div>))}
          </dl>
        </Seccion>
      )}

      <Seccion titulo={`La escaleta (${salida.escaleta.length} capítulos)`}>
        <ol className="escaleta">
          {salida.escaleta.map((c) => (
            <li key={c.numero}>
              <details>
                <summary>
                  <strong>Capítulo {c.numero}{c.titulo ? `. ${c.titulo}` : ''}</strong>
                  <span className="nota"> · {c.escenas.length} escenas</span>
                </summary>
                {c.funcion && <p className="nota">Función: {c.funcion}</p>}
                {c.gancho && <p className="nota">Gancho: {c.gancho}</p>}
                <ol className="escenas">
                  {c.escenas.map((e) => (
                    <li key={e.orden} className="escena">
                      <div className="fila">
                        <strong>Escena {e.orden}</strong>
                        {e.escenario && <Insignia>{e.escenario}</Insignia>}
                        {e.fecha_narrativa && <span className="nota">{e.fecha_narrativa}</span>}
                        {e.punto_de_vista && <span className="nota">· punto de vista de {e.punto_de_vista}</span>}
                      </div>
                      {(e.objetivo || e.conflicto || e.resultado) && (
                        <p>
                          {e.objetivo && <><em>Objetivo:</em> {e.objetivo}. </>}
                          {e.conflicto && <><em>Conflicto:</em> {e.conflicto}. </>}
                          {e.resultado && <><em>Resultado:</em> {e.resultado}.</>}
                        </p>
                      )}
                      {e.personajes.length > 0 && <p className="nota">Con {e.personajes.join(', ')}</p>}
                      {e.beats.length > 0 && (
                        <ol className="beats">
                          {e.beats.map((b) => (
                            <li key={b.orden}>{b.accion}{b.cambio_de_valor && <span className="nota"> ({b.cambio_de_valor})</span>}</li>
                          ))}
                        </ol>
                      )}
                      {e.anclajes.length > 0 && (
                        <div className="fila anclajes">
                          {e.anclajes.map((a, i) => (
                            <Insignia key={i} tono="acento">{a.tipo_vinculo}: {a.descripcion}</Insignia>
                          ))}
                        </div>
                      )}
                    </li>
                  ))}
                </ol>
              </details>
            </li>
          ))}
        </ol>
      </Seccion>

      <Seccion titulo={`Personajes (${salida.personajes.length})`}>
        <div className="rejilla-fichas">
          {salida.personajes.map((p) => (
            <article key={p.id} className="ficha">
              <div className="fila-entre">
                <h3>{p.nombre}</h3>
                {p.es_homenajeado && <Insignia tono="acento">homenajeado</Insignia>}
              </div>
              <p className="nota">{TIPOS[p.tipo] ?? p.tipo}{p.estatus ? ` · ${p.estatus}` : ''}</p>
              {p.rasgos.length > 0 && <p>{p.rasgos.join(' · ')}</p>}
              {p.objetivo && <p><em>Quiere:</em> {p.objetivo}</p>}
              {p.miedo && <p><em>Teme:</em> {p.miedo}</p>}
              {p.arcos.map((a, i) => (
                <div key={i} className="arco">
                  <p className="nota">Arco {a.tipo}{a.estado_inicial && a.estado_final ? `: de ${a.estado_inicial} a ${a.estado_final}` : ''}</p>
                  {a.hitos.length > 0 && (
                    <ol className="beats">{a.hitos.map((h) => <li key={h.orden}>{h.descripcion}</li>)}</ol>
                  )}
                </div>
              ))}
            </article>
          ))}
        </div>
      </Seccion>

      {salida.relaciones.length > 0 && (
        <Seccion titulo="Relaciones" plegable plegada>
          <Tabla columnas={['', 'Relación', '', 'Intensidad']}>
            {salida.relaciones.map((r, i) => (
              <tr key={i}><td>{r.a}</td><td>{r.tipo}</td><td>{r.b}</td><td>{r.intensidad ?? '—'}</td></tr>
            ))}
          </Tabla>
        </Seccion>
      )}

      <Seccion titulo={`Escenarios (${salida.escenarios.length})`} plegable plegada>
        <ul className="lista-simple">
          {salida.escenarios.map((e) => (
            <li key={e.id}><strong>{e.nombre}</strong>{e.nombre_epoca && ` (${e.nombre_epoca})`}{e.descripcion && e.descripcion !== e.nombre && <span className="nota"> — {e.descripcion}</span>}</li>
          ))}
        </ul>
      </Seccion>

      <Seccion titulo={`Licencias (${salida.licencias.length})`} plegable plegada>
        {salida.licencias.length === 0 ? <p className="nota">Ninguna: la novela no altera los hechos.</p> : (
          <ul className="lista-simple">
            {salida.licencias.map((l, i) => (
              <li key={i}>{l.alteracion}. <span className="nota">{l.justificacion}</span>{!l.declarada && <Insignia tono="ambar">sin declarar</Insignia>}</li>
            ))}
          </ul>
        )}
      </Seccion>

      <Seccion titulo={`Glosario (${salida.glosario.length})`} plegable plegada>
        <dl className="pares">
          {salida.glosario.map((g) => (<div key={g.termino}><dt>{g.termino}</dt><dd>{g.significado}{g.registro && <span className="nota"> · {g.registro}</span>}</dd></div>))}
        </dl>
      </Seccion>
    </>
  )
}
