// El formulario del encargo y su traducción, en los dos sentidos, a la forma del fichero
// de encargo: la de `ejemplos/*.yaml`, con los bloques homenajeado, mundo y obra. Esa forma
// es la que lee `storymaker nueva`, así que el formulario no inventa otra (spec §4.2).

import type { Encargo } from '@/shared/api'

export interface Elemento {
  texto: string
  obligatorio: boolean
}

export interface Formulario {
  nombre_homenajeado: string
  fecha_nacimiento: string
  rol_epoca: string
  ocasion: string
  elementos: Elemento[]
  denominacion: string
  inicio: string
  fin: string
  lugar: string
  evento_ancla: string
  aparecen: string
  se_evitan: string
  genero: string
  subgenero: string
  tono: string
  punto_de_vista: string
  grado_licencia: string
  arcaismo: string
  contenido_admisible: string
  prohibidas_novela: string
  prohibidas_destinatario: string
  n_capitulos: string
  palabras_por_capitulo: string
  texto_libre: string
}

export const GRADOS_DE_LICENCIA = ['estricto', 'moderado', 'amplio'] as const
export const ARCAISMOS = ['minimo', 'moderado', 'marcado'] as const

export const VACIO: Formulario = {
  nombre_homenajeado: '',
  fecha_nacimiento: '',
  rol_epoca: '',
  ocasion: '',
  elementos: [],
  denominacion: '',
  inicio: '',
  fin: '',
  lugar: '',
  evento_ancla: '',
  aparecen: '',
  se_evitan: '',
  genero: 'histórica',
  subgenero: '',
  tono: '',
  punto_de_vista: '',
  grado_licencia: 'moderado',
  arcaismo: 'moderado',
  contenido_admisible: '',
  prohibidas_novela: '',
  prohibidas_destinatario: '',
  n_capitulos: '10',
  palabras_por_capitulo: '1200',
  texto_libre: '',
}

const texto = (valor: unknown) => (valor == null ? '' : String(valor))
const lineas = (valor: unknown) => (Array.isArray(valor) ? valor.map(String).join('\n') : texto(valor))
const lista = (valor: string) =>
  valor
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
const bloque = (valor: unknown): Record<string, unknown> =>
  valor && typeof valor === 'object' && !Array.isArray(valor) ? (valor as Record<string, unknown>) : {}

/** Un encargo del fichero —por ejemplo, uno de `ejemplos/`— al formulario. */
export function aFormulario(encargo: Encargo): Formulario {
  const raiz = bloque(encargo.brief ?? encargo)
  const homenajeado = bloque(raiz.homenajeado)
  const mundo = bloque(raiz.mundo)
  const periodo = bloque(mundo.periodo)
  const historicos = bloque(mundo.personajes_historicos)
  const obra = bloque(raiz.obra)
  const genero = obra.genero
  const prohibidas = bloque(obra.palabras_prohibidas)
  const elementos = Array.isArray(homenajeado.elementos_personalizacion)
    ? homenajeado.elementos_personalizacion.map((e) => {
        const el = bloque(e)
        return { texto: texto(el.texto), obligatorio: Boolean(el.obligatorio) }
      })
    : []
  return {
    ...VACIO,
    nombre_homenajeado: texto(homenajeado.nombre_homenajeado),
    fecha_nacimiento: texto(homenajeado.fecha_nacimiento),
    rol_epoca: texto(homenajeado.rol_epoca),
    ocasion: texto(homenajeado.ocasion),
    elementos,
    denominacion: texto(periodo.denominacion),
    inicio: texto(periodo.inicio),
    fin: texto(periodo.fin),
    lugar: texto(mundo.lugar),
    evento_ancla: texto(mundo.evento_ancla),
    aparecen: lineas(historicos.aparecen),
    se_evitan: lineas(historicos.se_evitan),
    genero: typeof genero === 'object' ? texto(bloque(genero).principal) : texto(genero) || VACIO.genero,
    subgenero: typeof genero === 'object' ? texto(bloque(genero).subgenero) : '',
    tono: texto(obra.tono),
    punto_de_vista: texto(obra.punto_de_vista),
    grado_licencia: texto(obra.grado_licencia) || VACIO.grado_licencia,
    arcaismo: texto(obra.arcaismo) || VACIO.arcaismo,
    contenido_admisible: texto(obra.contenido_admisible),
    prohibidas_novela: lineas(prohibidas.novela),
    prohibidas_destinatario: lineas(prohibidas.destinatario),
    n_capitulos: texto(obra.n_capitulos) || VACIO.n_capitulos,
    palabras_por_capitulo: texto(obra.palabras_por_capitulo) || VACIO.palabras_por_capitulo,
    texto_libre: texto(raiz.texto_libre),
  }
}

/** Quita las claves vacías: lo que no se rellenó no se menciona en la premisa. */
function limpio(objeto: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(objeto).filter(([, v]) => {
      if (v === '' || v == null) return false
      if (Array.isArray(v)) return v.length > 0
      if (typeof v === 'object') return Object.keys(v as object).length > 0
      return true
    }),
  )
}

const numero = (valor: string) => (valor.trim() === '' ? '' : Number.isNaN(Number(valor)) ? valor : Number(valor))

/** El formulario a la forma del fichero de encargo. */
export function aEncargo(f: Formulario): Encargo {
  return limpio({
    homenajeado: limpio({
      nombre_homenajeado: f.nombre_homenajeado.trim(),
      fecha_nacimiento: f.fecha_nacimiento.trim(),
      rol_epoca: f.rol_epoca.trim(),
      ocasion: f.ocasion.trim(),
      elementos_personalizacion: f.elementos
        .filter((e) => e.texto.trim())
        .map((e) => ({ texto: e.texto.trim(), obligatorio: e.obligatorio })),
    }),
    mundo: limpio({
      periodo: limpio({ denominacion: f.denominacion.trim(), inicio: numero(f.inicio), fin: numero(f.fin) }),
      lugar: f.lugar.trim(),
      evento_ancla: f.evento_ancla.trim(),
      personajes_historicos: limpio({ aparecen: lista(f.aparecen), se_evitan: lista(f.se_evitan) }),
    }),
    obra: limpio({
      genero: limpio({ principal: f.genero.trim(), subgenero: f.subgenero.trim() }),
      tono: f.tono.trim(),
      punto_de_vista: f.punto_de_vista.trim(),
      grado_licencia: f.grado_licencia,
      arcaismo: f.arcaismo,
      contenido_admisible: f.contenido_admisible.trim(),
      palabras_prohibidas: limpio({
        novela: lista(f.prohibidas_novela),
        destinatario: lista(f.prohibidas_destinatario),
      }),
      n_capitulos: numero(f.n_capitulos),
      palabras_por_capitulo: numero(f.palabras_por_capitulo),
    }),
    texto_libre: f.texto_libre.trim(),
  })
}

/** El campo del formulario al que se refiere un error del backend (`obra.n_capitulos`…). */
export function campoDelError(campo: string): string {
  const ultimo = campo.split('.').pop() ?? campo
  return ultimo === 'encargo' ? 'nombre_homenajeado' : ultimo
}

/**
 * El encargo del modo conversación: a quién se regala y la novela contada con sus palabras.
 * La descripción entra en la premisa que lee el entrevistador, que pregunta el resto.
 */
export function encargoDeConversacion(nombre: string, descripcion: string): Encargo {
  return limpio({
    descripcion: descripcion.trim(),
    homenajeado: limpio({ nombre_homenajeado: nombre.trim() }),
  })
}
