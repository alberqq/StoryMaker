/// <reference types="vitest/config" />
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// Los alias se declaran con el mismo mapa aquí y en `tsconfig.json::paths`, para que el
// resolutor de TypeScript y el de Vite no puedan discrepar (spec §2.2). Una prueba de
// estructura compara los dos.
export const ALIAS = {
  '@/app': fileURLToPath(new URL('./src/app', import.meta.url)),
  '@/pages': fileURLToPath(new URL('./src/pages', import.meta.url)),
  '@/entities': fileURLToPath(new URL('./src/entities', import.meta.url)),
  '@/shared': fileURLToPath(new URL('./src/shared', import.meta.url)),
}

// En desarrollo la API es FastAPI en su puerto de siempre, alcanzada por el proxy: así no
// se paga CORS. Fuera de desarrollo no hay proxy, porque FastAPI sirve este `dist/`.
const API_EN_DESARROLLO = 'http://127.0.0.1:8000'

export default defineConfig(({ mode }) => {
  const entorno = loadEnv(mode, process.cwd(), 'VITE_')
  return {
    base: entorno.VITE_BASE_PATH || '/',
    plugins: [react()],
    resolve: { alias: ALIAS },
    server: {
      proxy: { '/api': { target: API_EN_DESARROLLO, changeOrigin: true } },
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./tests/preparacion.ts'],
      include: ['tests/**/*.test.{ts,tsx}'],
      // En Node no hay origen al que resolver `/api/...`: las pruebas le dan uno, y MSW
      // responde en él.
      env: { VITE_API_URL: 'http://localhost' },
    },
  }
})
