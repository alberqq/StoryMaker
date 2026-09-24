import type { SalidaEncargo as Salida } from '@/shared/api'
import { formatearHora } from '@/shared/lib'
import { EstadoVacio, Insignia, Seccion, Tabla } from '@/shared/ui'

function Valor({ valor }: { valor: unknown }) {
  if (valor == null || valor === '') return <span className="tenue">—</span>
  if (Array.isArray(valor))
    return (
      <ul className="lista-simple">
        {valor.map((v, i) => (
          <li key={i}>
            <Valor valor={v} />
          </li>
        ))}
      </ul>
    )
  if (typeof valor === 'object')
    return (
      <dl className="pares">
        {Object.entries(valor as Record<string, unknown>).map(([k, v]) => (
          <div key={k}>
            <dt>{k.replaceAll('_', ' ')}</dt>
            <dd>
              <Valor valor={v} />
            </dd>
          </div>
        ))}
      </dl>
    )
  return <span>{String(valor)}</span>
}

/** El brief, los datos del encargo y lo que entró en cuarentena. */
export function SalidaEncargo({ salida }: { salida: Salida }) {
  const vacio = !salida.brief && !salida.encargo && salida.datos.length === 0
  if (vacio) return <EstadoVacio>La fase de Encargo todavía no ha dejado nada escrito.</EstadoVacio>
  return (
    <>
      {salida.brief && (
        <Seccion titulo="El brief, tal como lo cerró el entrevistador">
          <Valor valor={salida.brief} />
        </Seccion>
      )}
      <Seccion titulo={`Datos del encargo (${salida.datos.length})`}>
        {salida.datos.length === 0 ? (
          <p className="nota">Ninguno todavía.</p>
        ) : (
          <Tabla columnas={['Tipo', 'Valor', 'Origen', '']}>
            {salida.datos.map((d) => (
              <tr key={d.id}>
                <td>{d.tipo}</td>
                <td>{d.valor}</td>
                <td>{d.origen === 'entrevista' ? 'entrevista' : 'texto libre'}</td>
                <td>{d.obligatorio && <Insignia tono="acento">obligatorio</Insignia>}</td>
              </tr>
            ))}
          </Tabla>
        )}
      </Seccion>
      {salida.cuarentena.length > 0 && (
        <Seccion titulo="Texto en cuarentena" plegable plegada>
          {salida.cuarentena.map((t, i) => (
            <div key={i} className="pila">
              <p className="nota">
                Recibido {formatearHora(t.recibido_en)}
                {t.procesado_en ? ` · extraído ${formatearHora(t.procesado_en)}` : ' · sin extraer'}
              </p>
              <pre className="bloque-texto">{t.texto}</pre>
            </div>
          ))}
        </Seccion>
      )}
      {salida.encargo && (
        <Seccion titulo="El encargo que se lanzó" plegable plegada>
          <Valor valor={salida.encargo} />
        </Seccion>
      )}
    </>
  )
}
