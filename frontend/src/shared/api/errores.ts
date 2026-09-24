// Los errores de la API, traducidos desde el código HTTP **una sola vez** (spec §7).
//
// Cada página decide qué enseña ante un `NoEncontrado`, pero ninguna vuelve a mirar un
// código HTTP: eso es transporte, y el transporte no sube de capa.

/** Novela, versión o capítulo inexistente. */
export class NoEncontrado extends Error {
  override name = 'NoEncontrado'
}

/** Hay una invocación en curso sobre la novela: la petición se rechaza, no se encola. */
export class NovelaOcupada extends Error {
  override name = 'NovelaOcupada'
}

/** La acción no procede ahora: brief inválido, sin gate que decidir, cliente no local… */
export class Rechazada extends Error {
  override name = 'Rechazada'
}

/** El servidor no responde. La lectura no se cachea para fingir que sigue vivo. */
export class SinRespuesta extends Error {
  override name = 'SinRespuesta'
}

/** Cualquier otra avería del servidor. */
export class ErrorDelServidor extends Error {
  override name = 'ErrorDelServidor'
}

/** El cuerpo de error que devuelve el backend (`api/manejadores.py::cuerpo_de`). */
interface CuerpoDeError {
  mensaje?: string
  detalle?: string
  /** Lo que devuelve FastAPI para un `HTTPException` o un cuerpo que no valida. */
  detail?: string | { msg?: string }[]
}

export function traducir(codigo: number, cuerpo: unknown): Error {
  const { mensaje, detalle, detail } = (cuerpo ?? {}) as CuerpoDeError
  const deFastapi = typeof detail === 'string' ? detail : detail?.map((d) => d.msg).join('; ')
  const texto = detalle || deFastapi || mensaje || `El servidor respondió ${codigo}`
  if (codigo === 404) return new NoEncontrado(texto)
  if (codigo === 409) return new NovelaOcupada(texto)
  if (codigo === 403 || codigo === 415 || codigo === 422) return new Rechazada(texto)
  return new ErrorDelServidor(texto)
}

export type TipoDeError = 'no_encontrado' | 'ocupada' | 'rechazada' | 'sin_respuesta' | 'servidor'

/** El tipo de un error cualquiera, para que la interfaz elija qué decir sin mirar HTTP. */
export function tipoDeError(error: unknown): TipoDeError {
  if (error instanceof NoEncontrado) return 'no_encontrado'
  if (error instanceof NovelaOcupada) return 'ocupada'
  if (error instanceof Rechazada) return 'rechazada'
  if (error instanceof SinRespuesta) return 'sin_respuesta'
  return 'servidor'
}
