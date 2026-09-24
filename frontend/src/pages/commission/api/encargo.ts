import { encargar, leerEjemplos, validarEncargo, type Encargo, type ModoDeInvestigacion } from '@/shared/api'

export const cargarEjemplos = () => leerEjemplos()

/** La validación la hace el backend, con el mismo lector que `storymaker nueva`. */
export const comprobar = (encargo: Encargo) => validarEncargo(encargo)

export const lanzar = (encargo: Encargo, nombre: string, batch: boolean, exhaustiva: boolean) =>
  encargar(encargo, nombre, batch, (exhaustiva ? 'exhaustiva' : 'estandar') satisfies ModoDeInvestigacion)
