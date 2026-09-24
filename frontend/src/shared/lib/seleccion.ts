// El texto que el lector ha seleccionado dentro de un contenedor, y de dónde.
//
// No sabe qué es un capítulo: devuelve el fragmento y el valor del atributo `data-origen`
// del elemento más cercano que lo lleve, y quien usa el hook decide qué significa. La última
// selección hecha **dentro** del contenedor se conserva aunque el foco se vaya —si no, al
// pulsar en el formulario para escribir la petición se perdería el fragmento—, y `limpiar`
// la descarta. Sin selección, el fragmento es la cadena vacía.

import { type RefObject, useCallback, useEffect, useState } from 'react'

export interface Seleccion {
  fragmento: string
  origen: string | null
}

const VACIA: Seleccion = { fragmento: '', origen: null }

function origenDe(nodo: Node | null): string | null {
  const elemento = nodo instanceof Element ? nodo : (nodo?.parentElement ?? null)
  return elemento?.closest('[data-origen]')?.getAttribute('data-origen') ?? null
}

export function useSeleccion(contenedor: RefObject<HTMLElement | null>) {
  const [seleccion, setSeleccion] = useState<Seleccion>(VACIA)

  useEffect(() => {
    const leer = () => {
      const actual = document.getSelection()
      const raiz = contenedor.current
      if (!actual || actual.isCollapsed || !raiz) return
      if (!raiz.contains(actual.anchorNode) || !raiz.contains(actual.focusNode)) return
      const fragmento = actual.toString().trim()
      if (fragmento) setSeleccion({ fragmento, origen: origenDe(actual.anchorNode) })
    }
    document.addEventListener('selectionchange', leer)
    document.addEventListener('mouseup', leer)
    document.addEventListener('keyup', leer)
    return () => {
      document.removeEventListener('selectionchange', leer)
      document.removeEventListener('mouseup', leer)
      document.removeEventListener('keyup', leer)
    }
  }, [contenedor])

  const limpiar = useCallback(() => setSeleccion(VACIA), [])
  return { ...seleccion, limpiar }
}
