// Un recurso que se pide al montar la pantalla, con sus tres estados.
//
// Los estados de carga, error y vacío son parte del contrato de cada pantalla (spec §4): un
// esqueleto de carga eterno es un render roto, y `render_visual` lo juzgaría como tal. No
// hay caché: lo que el lector ve se pide a la API cada vez que se monta la pantalla, y con
// la API caída se enseña el aviso, no la última lectura (spec §9). Este hook no emite red:
// recibe la función que la emite, que vive en `shared/api`.

import { useCallback, useEffect, useState } from 'react'

export type Carga<T> =
  | { estado: 'cargando' }
  | { estado: 'listo'; datos: T }
  | { estado: 'error'; error: unknown }

export function useCarga<T>(
  cargar: () => Promise<T>,
  claves: readonly unknown[],
): Carga<T> & { reintentar: () => void } {
  const [carga, setCarga] = useState<Carga<T>>({ estado: 'cargando' })
  const [intento, setIntento] = useState(0)

  useEffect(() => {
    let vigente = true
    setCarga({ estado: 'cargando' })
    cargar().then(
      (datos) => vigente && setCarga({ estado: 'listo', datos }),
      (error: unknown) => vigente && setCarga({ estado: 'error', error }),
    )
    return () => {
      vigente = false
    }
    // `cargar` cambia en cada render; lo que decide si hay que volver a pedir son las claves.
  }, [...claves, intento])

  const reintentar = useCallback(() => setIntento((i) => i + 1), [])
  return { ...carga, reintentar }
}
