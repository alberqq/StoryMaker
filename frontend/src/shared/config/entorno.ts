// Las dos únicas variables de configuración del frontend (spec §2.2), y ninguna es un
// secreto: la API de lectura no lleva autenticación (U-17), así que no hay nada que guardar.

/** Base del cliente de la API. Vacía significa el mismo origen, que es lo normal. */
export const API_URL: string = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

/** Prefijo de rutas cuando FastAPI monta la aplicación bajo un camino. */
export const BASE_PATH: string = import.meta.env.VITE_BASE_PATH || '/'
