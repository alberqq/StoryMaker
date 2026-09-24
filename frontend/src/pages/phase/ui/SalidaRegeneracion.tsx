import type { SalidaRegeneracion as Salida } from '@/shared/api'
import { formatearHora } from '@/shared/lib'
import { EstadoVacio, Seccion, Tabla } from '@/shared/ui'

/** Las peticiones de cambio y las ediciones humanas que quedaron trazadas. */
export function SalidaRegeneracion({ salida }: { salida: Salida }) {
  if (salida.peticiones.length === 0 && salida.ediciones.length === 0)
    return <EstadoVacio>Nadie ha pedido todavía ningún cambio sobre esta novela.</EstadoVacio>
  return (
    <>
      <Seccion titulo={`Peticiones (${salida.peticiones.length})`}>
        {salida.peticiones.length === 0 ? <p className="nota">Ninguna.</p> : (
          <ul className="lista-simple">
            {salida.peticiones.map((p, i) => (
              <li key={i}>
                <blockquote className="comentario">{p.texto}</blockquote>
                <p className="nota">
                  {formatearHora(p.momento)}{p.capitulo ? ` · capítulo ${p.capitulo}` : ''}{p.fragmento ? ` · sobre «${p.fragmento}»` : ''}
                </p>
              </li>
            ))}
          </ul>
        )}
      </Seccion>
      <Seccion titulo={`Ediciones humanas (${salida.ediciones.length})`}>
        {salida.ediciones.length === 0 ? <p className="nota">Ninguna.</p> : (
          <Tabla columnas={['Fila', 'Campo', 'Antes', 'Después', 'Motivo']}>
            {salida.ediciones.map((e, i) => (
              <tr key={i}>
                <td className="mono">{e.tabla}:{e.fila_id}</td>
                <td>{e.campo}</td>
                <td className="tenue">{e.antes ?? '—'}</td>
                <td>{e.despues ?? '—'}</td>
                <td>{e.motivo || '—'}</td>
              </tr>
            ))}
          </Tabla>
        )}
      </Seccion>
    </>
  )
}
