import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { faseDeClave, nombreDeFase, trabaja } from '@/entities/novela'
import type { Conversacion } from '@/shared/api'
import { rutaBiblioteca, rutaFase, rutaPanel } from '@/shared/config'
import { formatearHace, useSondeo } from '@/shared/lib'
import { EstadoCarga, EstadoError, Insignia, Metrica, Seccion } from '@/shared/ui'
import { cargarGate, enviarDecision } from '../api/gate'
import { comentarioDeEleccion, elegible } from '../model/eleccion'
import { CorpusDelGate } from './CorpusDelGate'
import { Decision } from './Decision'
import { Editor } from './Editor'
import { Entrevista } from './Entrevista'
import { Regeneracion } from './Regeneracion'
import { RevisionDeLaTrama } from './RevisionDeLaTrama'
import './gate.css'

/** El gate que espera: qué fase, su resumen, sus preguntas, el editor y la decisión (spec §4.4). */
export function Gate() {
  const { id = '' } = useParams()
  const navegar = useNavigate()
  const sondeo = useSondeo(() => cargarGate(id), [id])
  // El gate en el que se enviaron las últimas respuestas: mientras siga siendo el mismo, el
  // entrevistador todavía no ha contestado.
  const [enviadoEn, setEnviadoEn] = useState<number | null>(null)
  // La última conversación vista, para seguir enseñándola mientras el entrevistador piensa
  // y no hay gate abierto.
  const [ultimaConversacion, setUltimaConversacion] = useState<Conversacion | null>(null)
  const gate = sondeo.datos?.gate ?? null
  const novela = sondeo.datos?.novela

  useEffect(() => {
    if (gate?.conversacion) setUltimaConversacion(gate.conversacion)
  }, [gate?.conversacion])

  // El candidato elegido en Regeneración y su valor nuevo. Se precargan al abrirse el gate
  // y no con cada sondeo, que borraría lo que el Autor está escribiendo.
  const [elegido, setElegido] = useState<number | null>(null)
  const [valor, setValor] = useState('')
  const candidatos = gate?.peticion?.candidatos
  const elegir = (indice: number | null) => {
    setElegido(indice)
    setValor(indice != null ? (candidatos?.[indice]?.valor ?? '') : '')
  }
  useEffect(() => {
    const primero = candidatos?.findIndex(elegible) ?? -1
    elegir(primero >= 0 ? primero : null)
  }, [gate?.id, candidatos?.length])

  const alDecidir = () => navegar(rutaPanel(id))
  const aprobar = async () => {
    await enviarDecision(id, 'aprobar', '')
    alDecidir()
  }

  if (sondeo.cargando)
    return (
      <div className="contenido">
        <EstadoCarga que="el gate" />
      </div>
    )
  if (!sondeo.datos)
    return (
      <div className="contenido">
        <EstadoError error={sondeo.error} onReintentar={sondeo.refrescar} />
      </div>
    )

  const cabecera = (titulo: string, subtitulo?: React.ReactNode) => (
    <header className="cabecera-pagina">
      <div>
        <p className="miga">
          <Link to={rutaBiblioteca()}>Taller</Link> / <Link to={rutaPanel(id)}>{id}</Link> / Gate
        </p>
        <h1>{titulo}</h1>
        {subtitulo && <p className="subtitulo">{subtitulo}</p>}
      </div>
    </header>
  )

  // Sin gate abierto: la novela está trabajando, o no espera nada.
  if (!gate || (gate.fase === 'intake' && gate.id === enviadoEn)) {
    const trabajando = novela && trabaja(novela.estado)
    const entrevistando = (trabajando && novela?.fase === 'intake') || enviadoEn !== null
    if (entrevistando && ultimaConversacion)
      return (
        <div className="contenido contenido-gate">
          {cabecera('Encargo', 'La conversación con el entrevistador')}
          <Entrevista
            id={id}
            conversacion={ultimaConversacion}
            preguntas={[]}
            pensando
            onEnviadas={() => {}}
            onAprobar={aprobar}
          />
        </div>
      )
    if (trabajando)
      return (
        <div className="contenido contenido-gate">
          {cabecera('La novela está trabajando')}
          <div className="estado estado-vacio" role="status">
            <Insignia tono="azul" punto vivo>
              {novela?.trabajando_en ?? nombreDeFase(novela?.fase ?? '')}
            </Insignia>
            <p>
              {novela?.fase === 'intake'
                ? 'El entrevistador está leyendo el encargo. Sus preguntas aparecerán aquí en cuanto termine.'
                : 'El gate se abrirá aquí cuando la fase termine.'}
            </p>
          </div>
        </div>
      )
    return (
      <div className="contenido">
        <div className="estado estado-vacio">
          <h2>No hay ningún gate esperando</h2>
          <p>Esta novela no espera ninguna decisión ahora mismo.</p>
          <Link to={rutaPanel(id)}>Ir al panel de la novela</Link>
        </div>
      </div>
    )
  }

  const fase = faseDeClave(gate.fase)
  const enlaceSalida = <Link to={rutaFase(id, fase.segmento)}>Leer la salida completa de {fase.nombre} →</Link>

  if (gate.fase === 'intake' && gate.conversacion)
    return (
      <div className="contenido contenido-gate">
        {cabecera('Encargo', <>La conversación con el entrevistador · {enlaceSalida}</>)}
        <Entrevista
          id={id}
          conversacion={gate.conversacion}
          preguntas={gate.preguntas}
          pensando={false}
          onEnviadas={() => setEnviadoEn(gate.id)}
          onAprobar={aprobar}
        />
        <Seccion titulo="Otras decisiones" plegable plegada>
          <p className="nota">
            Aprobar con preguntas sin contestar sigue con el brief que haya. Abortar termina la novela.
          </p>
          <Decision id={id} decisiones={gate.decisiones} onHecho={alDecidir} />
        </Seccion>
      </div>
    )

  return (
    <div className="contenido contenido-gate">
      {cabecera(
        `${fase.nombre} espera tu decisión`,
        <>
          Abierto {formatearHace(gate.abierto_en)} · {enlaceSalida}
        </>,
      )}

      {gate.recuentos.length > 0 && (
        <div className="rejilla-metricas recuentos">
          {gate.recuentos.map((r) => (
            <Metrica key={r.etiqueta} etiqueta={r.etiqueta} valor={r.valor} />
          ))}
        </div>
      )}

      {gate.fase === 'investigation' && (
        <Seccion titulo="El corpus">
          <CorpusDelGate id={id} corpusSellado={gate.corpus_sellado} />
        </Seccion>
      )}

      {gate.trama && (
        <Seccion titulo="La revisión de la escaleta">
          <RevisionDeLaTrama revision={gate.trama} />
        </Seccion>
      )}

      {gate.peticion && (
        <Seccion titulo="La petición del lector">
          <Regeneracion peticion={gate.peticion} elegido={elegido} valor={valor} onElegir={elegir} onValor={setValor} />
        </Seccion>
      )}

      <Seccion titulo="Decidir">
        <Decision
          id={id}
          decisiones={gate.decisiones}
          comentarioAlAprobar={
            gate.peticion
              ? comentarioDeEleccion(elegido != null ? gate.peticion.candidatos[elegido] : undefined, valor)
              : undefined
          }
          onHecho={alDecidir}
        />
      </Seccion>

      {gate.fase !== 'investigation' && (
        <Seccion titulo="Editar antes de decidir" plegable plegada>
          <p className="nota">
            Corrige filas del corpus, del canon o del glosario. Cada cambio se guarda al momento y queda trazado;
            después apruebas para seguir con tus correcciones o rehaces con un comentario.
          </p>
          <Editor id={id} filas={gate.editables} corpusSellado={gate.corpus_sellado} />
        </Seccion>
      )}
    </div>
  )
}
