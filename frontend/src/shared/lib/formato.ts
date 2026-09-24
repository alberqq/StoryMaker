// Formateo sin dominio: fechas y puntuaciones, en castellano.

const FECHA = new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'long', year: 'numeric' })
const NOTA = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 1, minimumFractionDigits: 1 })

/** `2026-09-24 10:00:00` (lo que escribe SQLite) → «24 de septiembre de 2026». */
export function formatearFecha(valor: string): string {
  const fecha = new Date(valor.includes('T') ? valor : `${valor.replace(' ', 'T')}Z`)
  return Number.isNaN(fecha.getTime()) ? valor : FECHA.format(fecha)
}

/** Una nota sobre diez, o un guion si no hay. */
export function formatearPuntuacion(valor: number | null | undefined): string {
  return valor == null ? '—' : `${NOTA.format(valor)} / 10`
}

const DINERO = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'USD', maximumFractionDigits: 2, minimumFractionDigits: 2 })
const ENTERO = new Intl.NumberFormat('es-ES')

/** Dólares, que es en lo que cuenta el consumo el Agent SDK. */
export function formatearDinero(valor: number): string {
  return DINERO.format(valor)
}

/** Tokens en forma corta: 1.234, 45,1 mil, 1,2 M. */
export function formatearTokens(valor: number): string {
  if (valor < 10_000) return ENTERO.format(valor)
  if (valor < 1_000_000) return `${new Intl.NumberFormat('es-ES', { maximumFractionDigits: 1 }).format(valor / 1000)} mil`
  return `${new Intl.NumberFormat('es-ES', { maximumFractionDigits: 1 }).format(valor / 1_000_000)} M`
}

function comoFecha(valor: string): Date {
  return new Date(valor.includes('T') ? valor : `${valor.replace(' ', 'T')}Z`)
}

/** Lo que duró algo, entre dos momentos de SQLite; si sigue abierto, hasta ahora. */
export function formatearDuracion(inicio: string | null | undefined, fin?: string | null): string {
  if (!inicio) return '—'
  const desde = comoFecha(inicio).getTime()
  const hasta = fin ? comoFecha(fin).getTime() : Date.now()
  if (Number.isNaN(desde) || Number.isNaN(hasta)) return '—'
  const segundos = Math.max(0, Math.round((hasta - desde) / 1000))
  if (segundos < 60) return `${segundos} s`
  const minutos = Math.round(segundos / 60)
  if (minutos < 60) return `${minutos} min`
  const horas = Math.floor(minutos / 60)
  return `${horas} h ${minutos % 60} min`
}

/** Hace cuánto: «hace 3 min», «hace 2 h», o la fecha si es de otro día. */
export function formatearHace(valor: string | null | undefined): string {
  if (!valor) return '—'
  const momento = comoFecha(valor)
  if (Number.isNaN(momento.getTime())) return valor
  const segundos = Math.round((Date.now() - momento.getTime()) / 1000)
  if (segundos < 45) return 'ahora mismo'
  if (segundos < 3600) return `hace ${Math.round(segundos / 60)} min`
  if (segundos < 86_400) return `hace ${Math.round(segundos / 3600)} h`
  return formatearFecha(valor)
}

/** La hora de un momento, para la línea de actividad. */
export function formatearHora(valor: string): string {
  const momento = comoFecha(valor)
  if (Number.isNaN(momento.getTime())) return valor
  return new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(momento)
}

/**
 * Los párrafos de un texto en prosa. Descarta las líneas vacías y los encabezados de
 * Markdown que a veces deja el modelo al principio del capítulo: el título ya lo pone la
 * página, y repetido como «# Capítulo 1» rompe la maqueta.
 */
export function parrafos(texto: string): string[] {
  return texto
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !/^#{1,6}\s/.test(l))
}
