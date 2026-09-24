import { Link, useParams } from 'react-router'
import { FASES, faseDeSegmento } from '@/entities/novela'
import { rutaBiblioteca, rutaFase, rutaPanel } from '@/shared/config'
import { useCarga } from '@/shared/lib'
import { EstadoCarga, EstadoError, NoExiste, Pestanas, Seccion } from '@/shared/ui'
import { cargarSalida } from '../api/fase'
import { Ejecuciones } from './Ejecuciones'
import { SalidaEncargo } from './SalidaEncargo'
import { SalidaEscritura } from './SalidaEscritura'
import { SalidaInvestigacion } from './SalidaInvestigacion'
import { SalidaPublicacion } from './SalidaPublicacion'
import { SalidaRegeneracion } from './SalidaRegeneracion'
import { SalidaTrama } from './SalidaTrama'
import './fase.css'

/** La salida de cada fase, una pestaña por fase (spec §4.5). */
export function Fase() {
  const { id = '', fase: segmento = '' } = useParams()
  const fase = faseDeSegmento(segmento)
  const carga = useCarga(() => cargarSalida(id, segmento), [id, segmento])

  if (!fase) return <div className="contenido"><NoExiste /></div>

  return (
    <div className="contenido">
      <header className="cabecera-pagina">
        <div>
          <p className="miga">
            <Link to={rutaBiblioteca()}>Taller</Link> / <Link to={rutaPanel(id)}>{id}</Link> / Salidas
          </p>
          <h1>{fase.nombre}</h1>
          <p className="subtitulo">Lo que la fase dejó escrito en el fichero de la novela.</p>
        </div>
      </header>
      <Pestanas
        etiqueta="Fases"
        pestanas={FASES.map((f) => ({ a: rutaFase(id, f.segmento), texto: f.nombre, activa: f.segmento === segmento }))}
      />
      {carga.estado === 'cargando' && <EstadoCarga que={`la salida de ${fase.nombre}`} />}
      {carga.estado === 'error' && <EstadoError error={carga.error} onReintentar={carga.reintentar} />}
      {carga.estado === 'listo' && (
        <>
          <Seccion titulo="Ejecuciones y decisiones" plegable plegada={carga.datos.ejecuciones.length === 0}>
            <Ejecuciones salida={carga.datos} />
          </Seccion>
          {carga.datos.encargo && <SalidaEncargo salida={carga.datos.encargo} />}
          {carga.datos.investigacion && <SalidaInvestigacion salida={carga.datos.investigacion} />}
          {carga.datos.trama && <SalidaTrama salida={carga.datos.trama} />}
          {carga.datos.escritura && <SalidaEscritura id={id} salida={carga.datos.escritura} />}
          {carga.datos.publicacion && <SalidaPublicacion id={id} salida={carga.datos.publicacion} />}
          {carga.datos.regeneracion && <SalidaRegeneracion salida={carga.datos.regeneracion} />}
        </>
      )}
    </div>
  )
}
