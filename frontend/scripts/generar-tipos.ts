// Genera `src/shared/api/transporte.ts` desde el OpenAPI que FastAPI publica (spec §7).
//
// Los tipos de transporte no se escriben a mano: así un cambio de contrato en el backend
// rompe `tsc` en lugar de romper la pantalla el día de la demo. El esquema se pide a la
// propia aplicación con `uv`, sin levantar el servidor; con `--desde <fichero|url>` se lee
// de otro sitio.
//
// Uso: `npm run tipos` o `npm run tipos -- --desde http://127.0.0.1:8000/openapi.json`

import { execFileSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import openapiTS, { astToString } from 'openapi-typescript'

const aqui = dirname(fileURLToPath(import.meta.url))
const backend = resolve(aqui, '..', '..', 'backend')
const destino = resolve(aqui, '..', 'src', 'shared', 'api', 'transporte.ts')

const CABECERA = `// GENERADO por \`npm run tipos\` desde el OpenAPI de FastAPI. NO SE EDITA A MANO.
// Si un tipo no encaja, el cambio va en el modelo de respuesta del backend, y se regenera.
`

function esquemaDelBackend(): Record<string, unknown> {
  const salida = execFileSync(
    'uv',
    [
      'run',
      '--project',
      backend,
      'python',
      '-c',
      'import json; from storymaker.api.app import crear_app; print(json.dumps(crear_app().openapi()))',
    ],
    { cwd: backend, encoding: 'utf-8', maxBuffer: 16 * 1024 * 1024 },
  )
  return JSON.parse(salida) as Record<string, unknown>
}

const indice = process.argv.indexOf('--desde')
const origen = indice > -1 ? process.argv[indice + 1] : undefined

const esquema = origen
  ? /^https?:/.test(origen)
    ? new URL(origen)
    : new URL(`file://${resolve(origen)}`)
  : esquemaDelBackend()

const ast = await openapiTS(esquema as Parameters<typeof openapiTS>[0])
writeFileSync(destino, CABECERA + astToString(ast), 'utf-8')
console.log(`Tipos de transporte escritos en ${destino}`)
