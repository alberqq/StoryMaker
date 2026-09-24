import { type TemaDeLaApp, usePreferenciasDeLectura } from '@/shared/lib'

const TEMAS: readonly { clave: TemaDeLaApp; nombre: string; icono: string }[] = [
  { clave: 'sistema', nombre: 'Tema del sistema', icono: '◐' },
  { clave: 'claro', nombre: 'Tema claro', icono: '☀' },
  { clave: 'oscuro', nombre: 'Tema oscuro', icono: '☾' },
]

/** El tema de toda la aplicación, en la barra (spec §8). El libro puede fijar el suyo aparte. */
export function SelectorDeTema() {
  const { preferencias, cambiar } = usePreferenciasDeLectura()
  return (
    <div className="selector-tema" role="radiogroup" aria-label="Tema de la aplicación">
      {TEMAS.map((t) => (
        <button
          key={t.clave}
          type="button"
          role="radio"
          aria-checked={preferencias.temaApp === t.clave}
          aria-label={t.nombre}
          title={t.nombre}
          className={preferencias.temaApp === t.clave ? 'elegido' : ''}
          onClick={() => cambiar({ temaApp: t.clave })}
        >
          {t.icono}
        </button>
      ))}
    </div>
  )
}
