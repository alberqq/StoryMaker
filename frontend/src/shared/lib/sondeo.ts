// Un recurso que se vuelve a pedir cada pocos segundos mientras la pestaña está visible.
//
// Es el seguimiento de arq. §16.5: el servidor no empuja nada, la pantalla pregunta. Los
// datos anteriores se conservan mientras llega la respuesta nueva —un refresco no desmonta
// el contenido ni vacía lo que el Autor está escribiendo— y un fallo pasajero no borra lo
// último que se vio: se marca como error y se sigue intentando, sin apilar avisos.

import { useCallback, useEffect, useRef, useState } from 'react'

export const INTERVALO_DE_SONDEO_MS = 3000

export interface Sondeo<T> {
  datos: T | undefined
  error: unknown
  cargando: boolean
  refrescar: () => void
}

export function useSondeo<T>(
  cargar: () => Promise<T>,
  claves: readonly unknown[],
  opciones: { pausado?: boolean; intervalo?: number } = {},
): Sondeo<T> {
  const { pausado = false, intervalo = INTERVALO_DE_SONDEO_MS } = opciones
  const [datos, setDatos] = useState<T | undefined>(undefined)
  const [error, setError] = useState<unknown>(null)
  const [cargando, setCargando] = useState(true)
  const cargarRef = useRef(cargar)
  cargarRef.current = cargar
  const vigente = useRef(0)

  const pedir = useCallback(() => {
    const turno = ++vigente.current
    cargarRef.current().then(
      (nuevos) => {
        if (turno !== vigente.current) return
        setDatos(nuevos)
        setError(null)
        setCargando(false)
      },
      (fallo: unknown) => {
        if (turno !== vigente.current) return
        setError(fallo)
        setCargando(false)
      },
    )
  }, [])

  // Al cambiar de recurso se empieza de cero: los datos de otra novela no se enseñan.
  useEffect(() => {
    setDatos(undefined)
    setError(null)
    setCargando(true)
    pedir()
    return () => {
      vigente.current++
    }
    // Las claves deciden cuándo es otro recurso.
  }, [...claves, pedir])

  useEffect(() => {
    if (pausado) return
    const temporizador = setInterval(() => {
      if (!document.hidden) pedir()
    }, intervalo)
    const alVolver = () => {
      if (!document.hidden) pedir()
    }
    document.addEventListener('visibilitychange', alVolver)
    return () => {
      clearInterval(temporizador)
      document.removeEventListener('visibilitychange', alVolver)
    }
  }, [pausado, intervalo, pedir])

  return { datos, error, cargando, refrescar: pedir }
}
