// Los contratos de `shared/api` servidos por MSW.
//
// Los datos se tipan con los tipos de transporte generados: si el backend cambia un campo,
// estas fixtures dejan de compilar a la vez que las pantallas.

import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import type {
  Diferencias,
  FichaConHistorial,
  Fichas,
  GateDeNovela,
  Panel,
  SalidaDeFase,
  TarjetaNovela,
  TextoDeCapitulo,
  VersionDeNovela,
} from '@/shared/api'

export const API = 'http://localhost/api'

// --- Taller y panel ----------------------------------------------------------------

const baseTarjeta = {
  capitulos_aprobados: 0,
  capitulos_total: 0,
  coste_usd: 0,
  versiones: 0,
  gate: null,
  actualizada: '2026-09-24 09:00:00',
} satisfies Partial<TarjetaNovela>

export const tarjetas: TarjetaNovela[] = [
  {
    ...baseTarjeta,
    nombre: 'mar',
    titulo: 'La mar de Cádiz',
    homenajeado: 'Elvira Ponce',
    fase: 'publication',
    estado: 'terminada',
    capitulos_aprobados: 3,
    capitulos_total: 3,
    coste_usd: 1.23,
    versiones: 2,
  },
  {
    ...baseTarjeta,
    nombre: 'rio',
    titulo: 'El río de Sevilla',
    homenajeado: 'Luis Vera',
    fase: 'plotting',
    estado: 'esperando_autor',
    gate: { id: 4, fase: 'plotting', abierto_en: '2026-09-24 08:00:00' },
    coste_usd: 0.4,
  },
  {
    ...baseTarjeta,
    nombre: 'lago',
    titulo: 'lago',
    homenajeado: 'Ana Ruiz',
    fase: 'intake',
    estado: 'esperando_autor',
    gate: { id: 1, fase: 'intake', abierto_en: '2026-09-24 08:30:00' },
  },
  {
    ...baseTarjeta,
    nombre: 'nueva',
    titulo: 'nueva',
    homenajeado: 'Pedro Gil',
    fase: 'intake',
    estado: 'arrancando',
  },
]

const fase = (clave: string, estado: Panel['fases'][number]['estado'], extra: Partial<Panel['fases'][number]> = {}) => ({
  fase: clave,
  estado,
  deducida: false,
  tiene_salida: estado === 'completada',
  ejecuciones: [],
  tokens_in: 0,
  tokens_out: 0,
  coste_usd: 0,
  inicio: null,
  fin: null,
  ...extra,
})

export const panel = (nombre: string): Panel => {
  const tarjeta = tarjetas.find((t) => t.nombre === nombre)!
  return {
    ...tarjeta,
    fases: [
      fase('intake', 'completada', { deducida: true }),
      fase('investigation', 'completada', {
        ejecuciones: [
          {
            id: 2,
            fase: 'investigation',
            estado: 'completada',
            inicio: '2026-09-24 08:00:00',
            fin: '2026-09-24 08:05:00',
            tokens_in: 12000,
            tokens_out: 3000,
            coste_usd: 0.2,
            modelo: 'haiku',
          },
        ],
        tokens_in: 12000,
        tokens_out: 3000,
        coste_usd: 0.2,
        inicio: '2026-09-24 08:00:00',
        fin: '2026-09-24 08:05:00',
      }),
      fase('plotting', nombre === 'rio' ? 'esperando_gate' : 'completada'),
      fase('writing', nombre === 'mar' ? 'completada' : 'pendiente'),
      fase('publication', nombre === 'mar' ? 'completada' : 'pendiente'),
      fase('regeneration', 'pendiente'),
    ],
    capitulos: [
      { numero: 1, titulo: 'Uno', estado: 'aprobado', intentos: 1, palabras: 1200 },
      { numero: 2, titulo: 'Dos', estado: 'en_curso', intentos: 2, palabras: 1100 },
      { numero: 3, titulo: 'Tres', estado: 'pendiente', intentos: 0, palabras: null },
    ],
    actividad: [
      { momento: '2026-09-24 08:05:00', tipo: 'fase', texto: 'Investigación: completada', detalle: null },
      { momento: '2026-09-24 08:10:00', tipo: 'capitulo', texto: 'Capítulo 2, intento 2: borrador', detalle: '1100 palabras' },
    ],
    incidencias: [{ capitulo: 2, validador: 'longitud', severidad: 'bloqueante', mensaje: 'Demasiado corto' }],
    consumo: { tokens_in: 12000, tokens_out: 3000, coste_usd: tarjeta.coste_usd },
    proceso: { cerrojo: false, pid: null, vivo: false },
    registros: [],
    versiones_publicadas:
      nombre === 'mar'
        ? [
            { numero: 1, creada_en: '2026-09-20 10:00:00', pdf: true },
            { numero: 2, creada_en: '2026-09-22 10:00:00', pdf: false },
          ]
        : [],
    trabajando_en: null,
  }
}

export const gateDe = (nombre: string): GateDeNovela =>
  nombre === 'lago'
    ? {
        id: 1,
        fase: 'intake',
        abierto_en: '2026-09-24 08:30:00',
        recuentos: [{ etiqueta: 'datos del encargo', valor: 3 }],
        preguntas: ['¿Cómo se llama su perro?', '¿Dónde nació?'],
        peticion: null,
        conversacion: {
          descripcion: 'Una novela de piratas en Cádiz para mi madre.',
          rondas: ['1. ¿En qué año?\n   En 1812'],
          brief: null,
        },
        editables: [],
        corpus_sellado: false,
        decisiones: ['aprobar', 'rehacer', 'abortar'],
      }
    : {
        id: 4,
        fase: 'plotting',
        abierto_en: '2026-09-24 08:00:00',
        recuentos: [
          { etiqueta: 'capitulos en la escaleta', valor: 10 },
          { etiqueta: 'personajes', valor: 5 },
        ],
        preguntas: [],
        peticion: null,
        conversacion: null,
        editables: [
          {
            objeto: 'personaje',
            fila_id: 2,
            etiqueta: 'Tomás Ruiz',
            campos: { nombre: 'Tomás Ruiz', estatus: 'piloto', objetivo: null, miedo: null, voz: null },
            editable: true,
          },
          { objeto: 'hecho', fila_id: 9, etiqueta: 'lugar', campos: { enunciado: 'El muelle existía' }, editable: false },
        ],
        corpus_sellado: true,
        decisiones: ['aprobar', 'rehacer'],
      }

export const salidaTrama: SalidaDeFase = {
  fase: 'plotting',
  ejecuciones: [],
  decisiones: [{ gate_id: 3, estado: 'decidido', decision: 'rehacer', comentario: 'Más mar', decidido_en: '2026-09-24 07:00:00' }],
  trama: {
    obra: {
      titulo: 'El río de Sevilla',
      premisa: 'Un cartógrafo…',
      tema: 'la memoria',
      genero: 'histórica',
      voz: null,
      estilo: null,
      n_capitulos: 1,
      palabras_por_capitulo: 1200,
    },
    personajes: [
      { id: 1, nombre: 'Luis Vera', tipo: 'inventado', rasgos: ['tenaz'], objetivo: 'cartografiar', miedo: null, voz: null, estatus: 'cartógrafo', es_homenajeado: true, arcos: [] },
    ],
    relaciones: [],
    escenarios: [],
    licencias: [],
    glosario: [],
    escaleta: [
      {
        numero: 1,
        titulo: 'El puerto',
        funcion: null,
        gancho: null,
        escenas: [
          {
            orden: 1,
            escenario: 'Sevilla',
            fecha_narrativa: '1519',
            punto_de_vista: 'Luis Vera',
            objetivo: 'embarcar',
            conflicto: null,
            resultado: null,
            personajes: ['Luis Vera'],
            beats: [{ orden: 1, accion: 'Llega al muelle', cambio_de_valor: null }],
            anclajes: [{ tipo_vinculo: 'ambienta', descripcion: 'La Casa de Contratación' }],
          },
        ],
      },
    ],
  },
}

// --- Lectura -----------------------------------------------------------------------

export const ficha: FichaConHistorial = {
  nombre: 'mar',
  titulo: 'La mar de Cádiz',
  fase: 'publication',
  versiones: 2,
  ocupada: false,
  historial: [
    { numero: 1, creada_en: '2026-09-20 10:00:00', puntuacion: 7.25 },
    { numero: 2, creada_en: '2026-09-22 18:30:00', puntuacion: null },
  ],
}

const paratexto = {
  titulo: 'La mar de Cádiz',
  homenajeado: 'Elvira Ponce',
  ocasion: 'jubilación tras cuarenta años en el puerto',
  licencias: [{ alteracion: 'Se adelanta la botadura un año', justificacion: 'Para que coincida con la boda' }],
}

const capitulos = [1, 2, 3].map((n) => ({ id: n * 10, numero: n, titulo: `Titulo ${n}`, palabras: 1200, resumen: null }))

export const version = (n: number): VersionDeNovela => ({
  numero: n,
  anterior: n > 1 ? n - 1 : null,
  capitulos,
  paratexto,
  manifiesto: { brief_hash: 'h', sello_corpus_hash: 's', embeddings: null },
})

export const capitulo = (n: number, k: number): TextoDeCapitulo => ({
  orden: k,
  titulo: `Titulo ${k}`,
  texto: `Texto del capitulo ${k} en la version ${n}.\nSegundo parrafo del capitulo ${k}.`,
  palabras: 12,
  total: 3,
})

export const fichas: Fichas = {
  personajes: [
    { id: 1, nombre: 'Elvira Ponce', tipo: 'inventado', estatus: 'armadora', rasgos: ['tenaz'], es_homenajeado: true, relacion_con_homenajeado: null, capitulos: [1, 2, 3] },
    { id: 2, nombre: 'Tomás Ruiz', tipo: 'historico_de_fondo', estatus: 'piloto', rasgos: [], es_homenajeado: false, relacion_con_homenajeado: 'hermano', capitulos: [2] },
    { id: 3, nombre: 'Sin Escena', tipo: 'inventado', estatus: '', rasgos: [], es_homenajeado: false, relacion_con_homenajeado: null, capitulos: [] },
  ],
  escenarios: [{ id: 1, nombre: 'Cádiz', lugar: 'Cádiz', lugar_de_epoca: 'Cádiz de las Cortes', descripcion: 'El muelle', capitulos: [1] },
    { id: 2, nombre: 'Taller de imprenta', lugar: null, lugar_de_epoca: null, descripcion: 'Taller de imprenta con máquinas de prensa y cajas de tipos', capitulos: [] }],
}

export const diff = (a: number, b: number): Diferencias => ({
  version_a: a,
  version_b: b,
  cambios: [{ capitulo: 2, estado: 'regenerado' }],
  resumen: '',
})

const noExiste = () =>
  HttpResponse.json({ error: 'NovelaNoEncontrada', mensaje: 'No existe', codigo: 404 }, { status: 404 })

/** Lo que el servidor recibió, para comprobar qué se pidió y qué no. */
export const recibidas: string[] = []
/** Los cuerpos de las acciones, por ruta. */
export const enviados: { ruta: string; cuerpo: unknown }[] = []

const lanzada = (nombre: string) => HttpResponse.json({ nombre, registro: 'x.log', mensaje: 'Lanzado.' }, { status: 202 })

export const manejadores = [
  http.get(`${API}/novelas`, () => HttpResponse.json(tarjetas)),
  http.get(`${API}/novelas/:id/panel`, ({ params }) =>
    tarjetas.some((t) => t.nombre === params.id) ? HttpResponse.json(panel(String(params.id))) : noExiste(),
  ),
  http.get(`${API}/novelas/:id/gate`, ({ params }) =>
    params.id === 'rio' || params.id === 'lago' ? HttpResponse.json(gateDe(String(params.id))) : noExiste(),
  ),
  http.get(`${API}/novelas/:id/fases/:fase`, ({ params }) =>
    params.fase === 'trama'
      ? HttpResponse.json(salidaTrama)
      : HttpResponse.json({ fase: String(params.fase), ejecuciones: [], decisiones: [] } satisfies SalidaDeFase),
  ),
  http.get(`${API}/ejemplos`, () =>
    HttpResponse.json([
      { nombre: 'brief-salamanca', encargo: { homenajeado: { nombre_homenajeado: 'Tomás Aldecoa', ocasion: 'cierre de su librería' }, obra: { n_capitulos: 10 } } },
    ]),
  ),
  http.post(`${API}/encargos/validar`, async ({ request }) => {
    const { encargo } = (await request.json()) as { encargo: { homenajeado?: { nombre_homenajeado?: string } } }
    const nombre = encargo.homenajeado?.nombre_homenajeado
    return HttpResponse.json(
      nombre
        ? { valido: true, errores: [], nombre_sugerido: 'ana-ruiz' }
        : { valido: false, errores: [{ campo: 'homenajeado.nombre_homenajeado', mensaje: 'Falta el nombre del homenajeado.' }], nombre_sugerido: null },
    )
  }),
  http.post(`${API}/novelas`, async ({ request }) => {
    enviados.push({ ruta: 'encargar', cuerpo: await request.json() })
    return lanzada('ana-ruiz')
  }),
  http.post(`${API}/novelas/:id/:accion`, async ({ params, request }) => {
    if (params.accion === 'cambios')
      return HttpResponse.json({ peticion: 'x', gate_abierto: 7, candidatos: [], nota: 'Nada se ha cambiado' })
    enviados.push({ ruta: `${params.id}/${params.accion}`, cuerpo: await request.json().catch(() => null) })
    if (params.accion === 'desbloquear' || params.accion === 'ediciones')
      return HttpResponse.json({ nombre: String(params.id), mensaje: 'Hecho.' })
    return lanzada(String(params.id))
  }),
  http.get(`${API}/novelas/:id`, ({ params }) => (params.id === 'mar' ? HttpResponse.json(ficha) : noExiste())),
  http.get(`${API}/novelas/:id/versiones/:n`, ({ params }) => {
    const n = Number(params.n)
    return params.id === 'mar' && n >= 1 && n <= 2 ? HttpResponse.json(version(n)) : noExiste()
  }),
  http.get(`${API}/novelas/:id/versiones/:n/capitulos/:k`, ({ params }) => {
    const k = Number(params.k)
    return k >= 1 && k <= 3 ? HttpResponse.json(capitulo(Number(params.n), k)) : noExiste()
  }),
  http.get(`${API}/novelas/:id/versiones/:n/personajes`, () => HttpResponse.json(fichas)),
  http.get(`${API}/novelas/:id/versiones/:a/diff/:b`, ({ params }) =>
    HttpResponse.json(diff(Number(params.a), Number(params.b))),
  ),
]

export const servidor = setupServer(...manejadores)
servidor.events.on('request:start', ({ request }) => {
  recibidas.push(`${request.method} ${new URL(request.url).pathname}`)
})
