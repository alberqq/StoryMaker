// Las preferencias de presentación: el tema de la aplicación y los ajustes de lectura
// (spec §4.6 y §8).
//
// Es **el único módulo que toca el almacenamiento del navegador**, y solo para esto: las
// preferencias son de quien mira, no de la novela, así que no rompen la regla de que el
// cliente no guarda estado de dominio (spec §1). Si el navegador no deja guardar, se aplican
// igual durante la visita.
//
// Es un almacén y no un estado de componente porque lo leen a la vez la barra, que elige el
// tema de la aplicación, y el libro, que aplica los ajustes de lectura.

import { useSyncExternalStore } from 'react'

export type FuenteDeLectura = 'garamond' | 'georgia' | 'inter'
export type TemaDeLaApp = 'sistema' | 'claro' | 'oscuro'
/** `app` sigue el tema de la aplicación; los otros dos lo fijan solo para el libro. */
export type TemaDelLibro = 'app' | 'claro' | 'oscuro'

export interface PreferenciasDeLectura {
  /** Paso de tamaño, de 0 a `TAMANOS.length - 1`. */
  tamano: number
  fuente: FuenteDeLectura
  /** Paso de interlineado, de 0 a `INTERLINEADOS.length - 1`. */
  interlineado: number
  negrita: boolean
  temaLibro: TemaDelLibro
  temaApp: TemaDeLaApp
}

/** El tamaño de letra de cada paso, en `rem`. El paso 2 es el de siempre. */
export const TAMANOS = [0.95, 1.05, 1.2, 1.35, 1.55] as const

export const INTERLINEADOS: readonly { valor: number; nombre: string }[] = [
  { valor: 1.4, nombre: 'Compacto' },
  { valor: 1.65, nombre: 'Normal' },
  { valor: 1.95, nombre: 'Amplio' },
]

export const FUENTES: readonly { clave: FuenteDeLectura; nombre: string; familia: string }[] = [
  { clave: 'garamond', nombre: 'Garamond', familia: "'EB Garamond', Georgia, serif" },
  { clave: 'georgia', nombre: 'Georgia', familia: "Georgia, 'Times New Roman', serif" },
  { clave: 'inter', nombre: 'Inter', familia: 'Inter, system-ui, sans-serif' },
]

export const POR_DEFECTO: PreferenciasDeLectura = {
  tamano: 2,
  fuente: 'garamond',
  interlineado: 1,
  negrita: false,
  temaLibro: 'app',
  temaApp: 'sistema',
}

const CLAVE = 'storymaker.preferencias'

const paso = (valor: unknown, cuantos: number, defecto: number) => {
  const n = Number(valor)
  return Number.isInteger(n) && n >= 0 && n < cuantos ? n : defecto
}
const uno = <T extends string>(valor: unknown, validos: readonly T[], defecto: T): T =>
  validos.includes(valor as T) ? (valor as T) : defecto

function leer(): PreferenciasDeLectura {
  try {
    const crudo = (JSON.parse(window.localStorage.getItem(CLAVE) ?? 'null') ?? {}) as Record<string, unknown>
    return {
      tamano: paso(crudo.tamano, TAMANOS.length, POR_DEFECTO.tamano),
      fuente: uno(crudo.fuente, FUENTES.map((f) => f.clave), POR_DEFECTO.fuente),
      interlineado: paso(crudo.interlineado, INTERLINEADOS.length, POR_DEFECTO.interlineado),
      negrita: crudo.negrita === true,
      temaLibro: uno(crudo.temaLibro, ['app', 'claro', 'oscuro'] as const, POR_DEFECTO.temaLibro),
      temaApp: uno(crudo.temaApp, ['sistema', 'claro', 'oscuro'] as const, POR_DEFECTO.temaApp),
    }
  } catch {
    return POR_DEFECTO
  }
}

function guardar(preferencias: PreferenciasDeLectura) {
  try {
    window.localStorage.setItem(CLAVE, JSON.stringify(preferencias))
  } catch {
    // Sin almacenamiento, la preferencia dura lo que la visita.
  }
}

const sistemaOscuro = () =>
  typeof window !== 'undefined' && (window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false)

/** Pone `data-tema` en `<html>`: «sistema» se resuelve aquí, y `tokens.css` solo mira el atributo. */
function aplicarTema(tema: TemaDeLaApp) {
  if (typeof document === 'undefined') return
  const oscuro = tema === 'oscuro' || (tema === 'sistema' && sistemaOscuro())
  document.documentElement.dataset.tema = oscuro ? 'oscuro' : 'claro'
}

let actuales: PreferenciasDeLectura = typeof window === 'undefined' ? POR_DEFECTO : leer()
const oyentes = new Set<() => void>()

aplicarTema(actuales.temaApp)
if (typeof window !== 'undefined')
  window.matchMedia?.('(prefers-color-scheme: dark)').addEventListener?.('change', () => aplicarTema(actuales.temaApp))

export function cambiarPreferencias(cambio: Partial<PreferenciasDeLectura>) {
  actuales = { ...actuales, ...cambio }
  guardar(actuales)
  aplicarTema(actuales.temaApp)
  oyentes.forEach((avisar) => avisar())
}

const suscribir = (avisar: () => void) => {
  oyentes.add(avisar)
  return () => oyentes.delete(avisar)
}

export function usePreferenciasDeLectura() {
  const preferencias = useSyncExternalStore(suscribir, () => actuales)
  return { preferencias, cambiar: cambiarPreferencias }
}

/** Las variables CSS con las que el registro de libro aplica los ajustes de lectura. */
export function estiloDeLectura(preferencias: PreferenciasDeLectura): Record<string, string> {
  return {
    '--lectura-tamano': `${TAMANOS[preferencias.tamano] ?? TAMANOS[POR_DEFECTO.tamano]}rem`,
    '--lectura-fuente': (FUENTES.find((f) => f.clave === preferencias.fuente) ?? FUENTES[0]!).familia,
    '--lectura-interlineado': String((INTERLINEADOS[preferencias.interlineado] ?? INTERLINEADOS[1]!).valor),
    '--lectura-peso': preferencias.negrita ? '600' : '400',
  }
}
