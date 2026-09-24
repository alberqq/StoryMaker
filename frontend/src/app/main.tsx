// Las hojas globales van antes que el router: así las de cada página, que llegan con sus
// componentes, se aplican después y pueden precisar lo que las globales dejan en general.
import './styles/tokens.css'
import './styles/global.css'
import './styles/libro.css'
import './styles/print.css'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router'
import { Proveedores } from './providers'
import { crearRouter } from './router'

const raiz = document.getElementById('raiz')
if (!raiz) throw new Error('Falta el elemento #raiz en index.html')

createRoot(raiz).render(
  <Proveedores>
    <RouterProvider router={crearRouter()} />
  </Proveedores>,
)
