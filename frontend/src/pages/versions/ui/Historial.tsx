import { useState } from 'react'
import { useParams } from 'react-router'
import type { VersionPublicada } from '@/shared/api'
import {
  EnlaceCapitulo,
  EstadoCarga,
  EstadoError,
  EstadoVacio,
  Pagina,
  Tabla,
  Tarjeta,
} from '@/shared/ui'
import { rutaCapitulo, rutaIndice } from '@/shared/config'
import { formatearFecha, formatearPuntuacion, useCarga } from '@/shared/lib'
import { cargarDiff } from '../api/diff'
import { cargarHistorial } from '../api/historial'

const ESTADOS: Record<string, string> = {
  regenerado: 'reescrito',
  nuevo: 'nuevo',
  retirado: 'retirado',
}

/**
 * Las versiones publicadas y qué capítulos cambian entre dos cualesquiera (spec §4.5). Desde
 * aquí se abre cualquier versión anterior, que sigue entera: es la prueba visible de que la
 * versión previa se conserva por construcción.
 */
export function Historial() {
  const { id = '' } = useParams()
  const carga = useCarga(() => cargarHistorial(id), [id])

  if (carga.estado === 'cargando')
    return (
      <Pagina titulo="Historial">
        <EstadoCarga que="el historial" />
      </Pagina>
    )
  if (carga.estado === 'error')
    return (
      <Pagina titulo="Historial">
        <EstadoError error={carga.error} onReintentar={carga.reintentar} />
      </Pagina>
    )

  const { titulo, historial } = carga.datos
  return (
    <Pagina titulo={`Historial de «${titulo}»`}>
      {historial.length === 0 ? (
        <EstadoVacio>Esta novela todavía no tiene ninguna versión publicada.</EstadoVacio>
      ) : (
        <>
          <Tabla columnas={['Versión', 'Publicada', 'Puntuación del juez']}>
            {historial.map((v) => (
              <tr key={v.numero}>
                <td>
                  <EnlaceCapitulo a={rutaIndice(id, v.numero)}>Versión {v.numero}</EnlaceCapitulo>
                </td>
                <td>{formatearFecha(v.creada_en)}</td>
                <td>{formatearPuntuacion(v.puntuacion)}</td>
              </tr>
            ))}
          </Tabla>
          <Comparador id={id} historial={historial} />
        </>
      )}
    </Pagina>
  )
}

function Comparador({ id, historial }: { id: string; historial: VersionPublicada[] }) {
  const numeros = historial.map((v) => v.numero)
  const ultima = numeros[numeros.length - 1] ?? 1
  const penultima = numeros[numeros.length - 2] ?? ultima
  const [a, setA] = useState(penultima)
  const [b, setB] = useState(ultima)

  if (numeros.length < 2)
    return (
      <Tarjeta titulo="Qué cambia">
        <p className="nota">Solo hay una versión publicada: no hay nada que comparar.</p>
      </Tarjeta>
    )

  const selector = (valor: number, cambiar: (n: number) => void, etiqueta: string) => (
    <label>
      {etiqueta}{' '}
      <select value={valor} onChange={(e) => cambiar(Number(e.target.value))}>
        {numeros.map((n) => (
          <option key={n} value={n}>
            versión {n}
          </option>
        ))}
      </select>
    </label>
  )

  return (
    <Tarjeta titulo="Qué cambia">
      <p>
        {selector(a, setA, 'Entre la')} {selector(b, setB, 'y la')}
      </p>
      {a === b ? (
        <p className="nota">Es la misma versión.</p>
      ) : (
        <Diferencias key={`${a}-${b}`} id={id} a={a} b={b} />
      )}
    </Tarjeta>
  )
}

function Diferencias({ id, a, b }: { id: string; a: number; b: number }) {
  const carga = useCarga(() => cargarDiff(id, a, b), [id, a, b])
  if (carga.estado === 'cargando') return <EstadoCarga que="las diferencias" />
  if (carga.estado === 'error')
    return <EstadoError error={carga.error} onReintentar={carga.reintentar} />
  if (carga.datos.cambios.length === 0)
    return <p className="nota">Las dos versiones tienen los mismos capítulos.</p>
  return (
    <ul>
      {carga.datos.cambios.map((c) => (
        <li key={c.capitulo}>
          {c.estado === 'retirado' ? (
            `Capítulo ${c.capitulo}`
          ) : (
            <EnlaceCapitulo a={rutaCapitulo(id, b, c.capitulo)}>Capítulo {c.capitulo}</EnlaceCapitulo>
          )}
          : {ESTADOS[c.estado] ?? c.estado}
        </li>
      ))}
    </ul>
  )
}
