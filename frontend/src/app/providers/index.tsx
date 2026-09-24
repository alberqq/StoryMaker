import { StrictMode, type ReactNode } from 'react'

/**
 * Los proveedores de la aplicación. No hay almacén global de la novela ni caché de
 * respuestas (spec §1): el frontend no tiene verdad propia, y lo que enseña se pide a la API.
 */
export function Proveedores({ children }: { children: ReactNode }) {
  return <StrictMode>{children}</StrictMode>
}
