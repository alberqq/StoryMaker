import type { EstadoDeNovela } from '@/shared/api'
import { Insignia } from '@/shared/ui'
import { ESTADOS_DE_NOVELA } from '../model/estado'

/** El estado de una novela, con su color y siempre con su texto. */
export function InsigniaEstado({ estado }: { estado: EstadoDeNovela }) {
  const { texto, tono, vivo } = ESTADOS_DE_NOVELA[estado]
  return (
    <Insignia tono={tono} punto vivo={vivo}>
      {texto}
    </Insignia>
  )
}
