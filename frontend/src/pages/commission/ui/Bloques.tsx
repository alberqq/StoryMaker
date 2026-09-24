import type { ChangeEvent } from 'react'
import { Boton, Campo, Seccion } from '@/shared/ui'
import { ARCAISMOS, type Formulario, GRADOS_DE_LICENCIA } from '../model/brief'

interface Props {
  formulario: Formulario
  errores: Record<string, string>
  cambiar: (cambio: Partial<Formulario>) => void
}

type Clave = keyof Omit<Formulario, 'elementos'>

/** Los tres bloques del encargo: a quién se regala, en qué mundo y con qué reglas. */
export function Bloques({ formulario: f, errores, cambiar }: Props) {
  const enlazar = (clave: Clave) => ({
    value: f[clave],
    onChange: (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      cambiar({ [clave]: e.target.value } as Partial<Formulario>),
  })
  const error = (clave: string) => errores[clave]

  return (
    <>
      <Seccion titulo="1 · El homenajeado">
        <div className="formulario-rejilla">
          <Campo etiqueta="Nombre, tal como debe escribirse" obligatorio error={error('nombre_homenajeado')} ancho="completo">
            <input {...enlazar('nombre_homenajeado')} placeholder="Tomás Aldecoa Villarreal" />
          </Campo>
          <Campo etiqueta="Fecha de nacimiento" ayuda="AAAA-MM-DD">
            <input {...enlazar('fecha_nacimiento')} placeholder="1961-11-09" />
          </Campo>
          <Campo etiqueta="Ocasión" ayuda="Jubilación, aniversario, cumpleaños…">
            <input {...enlazar('ocasion')} placeholder="jubilación tras treinta años" />
          </Campo>
          <div className="campo-completo">
            <Campo etiqueta="Su papel en la novela">
              <input {...enlazar('rol_epoca')} placeholder="impresor con taller junto a las Escuelas Mayores" />
            </Campo>
          </div>
        </div>
        <div className="pila elementos">
          <span className="campo-etiqueta">Elementos de su vida que la novela incorpora</span>
          {f.elementos.map((el, i) => (
            <div className="fila elemento" key={i}>
              <input
                className="entrada"
                aria-label={`Elemento ${i + 1}`}
                value={el.texto}
                onChange={(e) =>
                  cambiar({ elementos: f.elementos.map((x, j) => (j === i ? { ...x, texto: e.target.value } : x)) })
                }
              />
              <label className="fila nota">
                <input
                  type="checkbox"
                  checked={el.obligatorio}
                  onChange={(e) =>
                    cambiar({
                      elementos: f.elementos.map((x, j) => (j === i ? { ...x, obligatorio: e.target.checked } : x)),
                    })
                  }
                />
                obligatorio
              </label>
              <Boton
                variante="fantasma"
                tamano="pequeno"
                aria-label={`Quitar el elemento ${i + 1}`}
                onClick={() => cambiar({ elementos: f.elementos.filter((_, j) => j !== i) })}
              >
                Quitar
              </Boton>
            </div>
          ))}
          <div>
            <Boton
              variante="secundario"
              tamano="pequeno"
              onClick={() => cambiar({ elementos: [...f.elementos, { texto: '', obligatorio: false }] })}
            >
              + Añadir elemento
            </Boton>
          </div>
        </div>
      </Seccion>

      <Seccion titulo="2 · El mundo">
        <div className="formulario-rejilla">
          <Campo etiqueta="Periodo" ayuda="Siglo de Oro, Cortes de Cádiz…">
            <input {...enlazar('denominacion')} />
          </Campo>
          <Campo etiqueta="Lugar">
            <input {...enlazar('lugar')} placeholder="Salamanca" />
          </Campo>
          <Campo etiqueta="Desde el año">
            <input {...enlazar('inicio')} inputMode="numeric" placeholder="1572" />
          </Campo>
          <Campo etiqueta="Hasta el año">
            <input {...enlazar('fin')} inputMode="numeric" placeholder="1576" />
          </Campo>
          <div className="campo-completo">
            <Campo etiqueta="Evento ancla" ayuda="Un hecho histórico en el que conviene anclar la novela">
              <input {...enlazar('evento_ancla')} />
            </Campo>
          </div>
          <Campo etiqueta="Personajes históricos que aparecen" ayuda="Uno por línea">
            <textarea {...enlazar('aparecen')} />
          </Campo>
          <Campo etiqueta="Personajes históricos que no aparecen" ayuda="Uno por línea">
            <textarea {...enlazar('se_evitan')} />
          </Campo>
        </div>
      </Seccion>

      <Seccion titulo="3 · La obra y su frontera con la historia">
        <div className="formulario-rejilla">
          <Campo etiqueta="Género">
            <input {...enlazar('genero')} />
          </Campo>
          <Campo etiqueta="Subgénero">
            <input {...enlazar('subgenero')} placeholder="intriga, aventura, costumbrista…" />
          </Campo>
          <Campo etiqueta="Tono">
            <input {...enlazar('tono')} placeholder="sereno, con final esperanzado" />
          </Campo>
          <Campo etiqueta="Punto de vista">
            <input {...enlazar('punto_de_vista')} placeholder="tercera persona con focalización en el homenajeado" />
          </Campo>
          <Campo etiqueta="Grado de licencia histórica" ayuda="Cuánto puede la ficción alterar los hechos">
            <select {...enlazar('grado_licencia')}>
              {GRADOS_DE_LICENCIA.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </Campo>
          <Campo etiqueta="Arcaísmo del lenguaje">
            <select {...enlazar('arcaismo')}>
              {ARCAISMOS.map((a) => (
                <option key={a} value={a}>
                  {a === 'minimo' ? 'mínimo' : a}
                </option>
              ))}
            </select>
          </Campo>
          <div className="campo-completo">
            <Campo etiqueta="Contenido admisible">
              <input {...enlazar('contenido_admisible')} placeholder="sin violencia explícita" />
            </Campo>
          </div>
          <Campo etiqueta="Palabras prohibidas en la novela" ayuda="Una por línea">
            <textarea {...enlazar('prohibidas_novela')} />
          </Campo>
          <Campo etiqueta="Palabras que el homenajeado no quiere leer" ayuda="Una por línea">
            <textarea {...enlazar('prohibidas_destinatario')} />
          </Campo>
          <Campo etiqueta="Capítulos" error={error('n_capitulos')}>
            <input {...enlazar('n_capitulos')} inputMode="numeric" />
          </Campo>
          <Campo etiqueta="Palabras por capítulo" error={error('palabras_por_capitulo')}>
            <input {...enlazar('palabras_por_capitulo')} inputMode="numeric" />
          </Campo>
          <div className="campo-completo">
            <Campo
              etiqueta="Texto libre del comprador"
              ayuda="Lo que quiera contar con sus palabras. Entra en cuarentena: se extraen datos tipados, nunca llega tal cual al escritor."
            >
              <textarea {...enlazar('texto_libre')} />
            </Campo>
          </div>
        </div>
      </Seccion>
    </>
  )
}
