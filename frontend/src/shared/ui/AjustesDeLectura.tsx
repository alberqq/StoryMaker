import { useEffect, useRef, useState } from 'react'
import { FUENTES, INTERLINEADOS, type PreferenciasDeLectura, TAMANOS, type TemaDelLibro } from '@/shared/lib'

interface Props {
  preferencias: PreferenciasDeLectura
  onCambiar: (cambio: Partial<PreferenciasDeLectura>) => void
}

const FONDOS: readonly { clave: TemaDelLibro; nombre: string }[] = [
  { clave: 'app', nombre: 'Como la app' },
  { clave: 'claro', nombre: 'Claro' },
  { clave: 'oscuro', nombre: 'Oscuro' },
]

/** Tres rayas cuya separación dibuja el interlineado. */
function IconoInterlineado({ separacion }: { separacion: number }) {
  const y = [12 - separacion, 12, 12 + separacion]
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
      {y.map((v) => (
        <line key={v} x1="4" x2="20" y1={v} y2={v} stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      ))}
    </svg>
  )
}

/**
 * La pestaña «Aa» del lector, como en un lector electrónico: tamaño, fuente, interlineado,
 * negrita y fondo del libro, en vivo (spec §4.6). Se cierra al pulsar fuera o con Escape.
 */
export function AjustesDeLectura({ preferencias, onCambiar }: Props) {
  const [abierta, setAbierta] = useState(false)
  const raiz = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!abierta) return
    const fuera = (e: MouseEvent) => {
      if (raiz.current && !raiz.current.contains(e.target as Node)) setAbierta(false)
    }
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && setAbierta(false)
    document.addEventListener('mousedown', fuera)
    document.addEventListener('keydown', tecla)
    return () => {
      document.removeEventListener('mousedown', fuera)
      document.removeEventListener('keydown', tecla)
    }
  }, [abierta])

  const { tamano, fuente, interlineado, negrita, temaLibro } = preferencias
  return (
    <div className="ajustes-lectura" ref={raiz}>
      <button
        type="button"
        className="ajustes-boton"
        aria-label="Ajustes de lectura"
        aria-expanded={abierta}
        onClick={() => setAbierta((a) => !a)}
      >
        <span className="aa-pequena">A</span>
        <span className="aa-grande">a</span>
      </button>
      {abierta && (
        <div className="ajustes-panel" role="dialog" aria-label="Ajustes de lectura">
          <div className="ajustes-grupo">
            <span className="ajustes-etiqueta">Tamaño</span>
            <div className="ajustes-tamano">
              <button
                type="button"
                aria-label="Letra más pequeña"
                disabled={tamano <= 0}
                onClick={() => onCambiar({ tamano: tamano - 1 })}
              >
                A−
              </button>
              <div className="ajustes-pasos" aria-hidden="true">
                {TAMANOS.map((_, i) => (
                  <span key={i} className={i <= tamano ? 'paso lleno' : 'paso'} />
                ))}
              </div>
              <button
                type="button"
                aria-label="Letra más grande"
                disabled={tamano >= TAMANOS.length - 1}
                onClick={() => onCambiar({ tamano: tamano + 1 })}
              >
                A+
              </button>
            </div>
          </div>

          <div className="ajustes-grupo" role="radiogroup" aria-label="Fuente">
            <span className="ajustes-etiqueta">Fuente</span>
            <div className="ajustes-opciones">
              {FUENTES.map((f) => (
                <button
                  key={f.clave}
                  type="button"
                  role="radio"
                  aria-checked={fuente === f.clave}
                  className={fuente === f.clave ? 'opcion elegida' : 'opcion'}
                  style={{ fontFamily: f.familia }}
                  onClick={() => onCambiar({ fuente: f.clave })}
                >
                  <span className="opcion-muestra">Aa</span>
                  {f.nombre}
                </button>
              ))}
            </div>
          </div>

          <div className="ajustes-grupo" role="radiogroup" aria-label="Interlineado">
            <span className="ajustes-etiqueta">Interlineado</span>
            <div className="ajustes-opciones">
              {INTERLINEADOS.map((l, i) => (
                <button
                  key={l.nombre}
                  type="button"
                  role="radio"
                  aria-checked={interlineado === i}
                  aria-label={l.nombre}
                  title={l.nombre}
                  className={interlineado === i ? 'opcion elegida' : 'opcion'}
                  onClick={() => onCambiar({ interlineado: i })}
                >
                  <IconoInterlineado separacion={4 + i * 2} />
                  {l.nombre}
                </button>
              ))}
            </div>
          </div>

          <label className="ajustes-interruptor">
            <span>
              <strong>Negrita</strong>
              <span className="nota"> · texto con más peso</span>
            </span>
            <input
              type="checkbox"
              role="switch"
              checked={negrita}
              onChange={(e) => onCambiar({ negrita: e.target.checked })}
            />
          </label>

          <div className="ajustes-grupo" role="radiogroup" aria-label="Fondo del libro">
            <span className="ajustes-etiqueta">Fondo del libro</span>
            <div className="ajustes-opciones">
              {FONDOS.map((f) => (
                <button
                  key={f.clave}
                  type="button"
                  role="radio"
                  aria-checked={temaLibro === f.clave}
                  className={`opcion fondo-${f.clave}${temaLibro === f.clave ? ' elegida' : ''}`}
                  onClick={() => onCambiar({ temaLibro: f.clave })}
                >
                  <span className="opcion-muestra muestra-fondo" data-tema-libro={f.clave === 'app' ? undefined : f.clave}>
                    Aa
                  </span>
                  {f.nombre}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
