// El mapa de rutas de la spec (§3), y el único sitio donde vive. Las páginas no se conocen
// entre sí: enlazan con los constructores de `shared/config`, y este fichero solo importa la
// API pública de cada slice.

import { Outlet, createBrowserRouter, type RouteObject } from 'react-router'
import { Tablero } from '@/pages/library'
import { Encargo } from '@/pages/commission'
import { Panel } from '@/pages/novel'
import { Gate } from '@/pages/gate'
import { Fase } from '@/pages/phase'
import { Capitulo, Indice } from '@/pages/reading'
import { Fichas } from '@/pages/characters'
import { Portada } from '@/pages/cover'
import { Historial } from '@/pages/versions'
import { Documento } from '@/pages/print'
import { BASE_PATH, PATRONES, rutaBiblioteca, rutaEncargo } from '@/shared/config'
import { Marco, NoExiste } from '@/shared/ui'

/** Todas las pantallas llevan el marco con su barra, salvo el documento de impresión. */
function ConMarco() {
  return (
    <Marco
      enlaces={[
        { a: rutaBiblioteca(), texto: 'Taller' },
        { a: rutaEncargo(), texto: 'Nuevo encargo' },
      ]}
    >
      <Outlet />
    </Marco>
  )
}

export const rutas: RouteObject[] = [
  {
    element: <ConMarco />,
    children: [
      { path: PATRONES.biblioteca, element: <Tablero /> },
      { path: PATRONES.encargo, element: <Encargo /> },
      { path: PATRONES.novela, element: <Panel /> },
      { path: PATRONES.gate, element: <Gate /> },
      { path: PATRONES.fase, element: <Fase /> },
      { path: PATRONES.indice, element: <Indice /> },
      { path: PATRONES.capitulo, element: <Capitulo /> },
      { path: PATRONES.portada, element: <Portada /> },
      { path: PATRONES.personajes, element: <Fichas /> },
      { path: PATRONES.versiones, element: <Historial /> },
      {
        path: '*',
        element: (
          <div className="contenido">
            <NoExiste />
          </div>
        ),
      },
    ],
  },
  { path: PATRONES.imprimir, element: <Documento /> },
]

export const crearRouter = () => createBrowserRouter(rutas, { basename: BASE_PATH })
