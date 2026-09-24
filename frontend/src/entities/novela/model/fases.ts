// Las seis fases, con el nombre que llevan en el backend, el que ve el Autor y el segmento
// castellano de su URL. La interfaz va en castellano (spec §14).

export interface Fase {
  clave: string
  nombre: string
  segmento: string
}

export const FASES: readonly Fase[] = [
  { clave: 'intake', nombre: 'Encargo', segmento: 'encargo' },
  { clave: 'investigation', nombre: 'Investigación', segmento: 'investigacion' },
  { clave: 'plotting', nombre: 'Trama', segmento: 'trama' },
  { clave: 'writing', nombre: 'Escritura', segmento: 'escritura' },
  { clave: 'publication', nombre: 'Publicación', segmento: 'publicacion' },
  { clave: 'regeneration', nombre: 'Regeneración', segmento: 'regeneracion' },
]

export const faseDeClave = (clave: string): Fase =>
  FASES.find((f) => f.clave === clave) ?? { clave, nombre: clave, segmento: clave }

export const faseDeSegmento = (segmento: string): Fase | undefined =>
  FASES.find((f) => f.segmento === segmento)

export const nombreDeFase = (clave: string) => faseDeClave(clave).nombre
