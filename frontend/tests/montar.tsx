import { render } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router'
import { rutas } from '@/app/router'

/** Monta la aplicación entera, con su mapa de rutas real, en una URL. */
export function montar(url: string) {
  const router = createMemoryRouter(rutas, { initialEntries: [url] })
  return { router, ...render(<RouterProvider router={router} />) }
}
