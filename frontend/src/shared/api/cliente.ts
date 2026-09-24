// El cliente único de la API, y **el único punto del código que emite una petición de red**.
//
// No es higiene: es condición de G5 (spec §6). `render_visual` corre dentro de
// `PublishVersion`, con la transacción abierta, sobre una versión candidata que la API no
// puede ver. El navegador que conduce la publicación intercepta estas peticiones y las
// sirve desde el manifiesto que tiene en memoria; un `fetch` suelto en una pantalla no se
// podría interceptar, y lo juzgado dejaría de ser lo que se publica.
//
// No lleva cabecera de autenticación ni guarda credenciales (U-17), no cachea nada, y
// devuelve los cuerpos **tal cual**: ninguna regla de negocio baja a este segmento.

import { API_URL } from '@/shared/config'
import { SinRespuesta, traducir } from './errores'

const BASE = `${API_URL}/api`

async function pedir(ruta: string, init?: RequestInit): Promise<Response> {
  let respuesta: Response
  try {
    respuesta = await fetch(`${BASE}${ruta}`, {
      ...init,
      cache: 'no-store',
      headers: { Accept: 'application/json', ...init?.headers },
    })
  } catch (causa) {
    throw new SinRespuesta('El servidor no responde.', { cause: causa })
  }
  if (!respuesta.ok) {
    const cuerpo: unknown = await respuesta.json().catch(() => null)
    throw traducir(respuesta.status, cuerpo)
  }
  return respuesta
}

async function json<T>(ruta: string, init?: RequestInit): Promise<T> {
  const respuesta = await pedir(ruta, init)
  return (await respuesta.json().catch(() => null)) as T
}

export const cliente = {
  get: <T>(ruta: string) => json<T>(ruta),
  texto: async (ruta: string) => (await pedir(ruta)).text(),
  post: <T>(ruta: string, datos: unknown) =>
    json<T>(ruta, {
      method: 'POST',
      body: JSON.stringify(datos),
      headers: { 'Content-Type': 'application/json' },
    }),
}
