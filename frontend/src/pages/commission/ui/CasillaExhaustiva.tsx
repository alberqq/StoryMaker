/**
 * El modo de investigación de arq. §4, Fase 2, que se elige al crear la novela: más
 * búsquedas y más fuentes para una novela que vive dentro de un oficio o alrededor de
 * figuras reales, a cambio de tiempo y coste.
 */
export function CasillaExhaustiva({ marcada, cambiar }: { marcada: boolean; cambiar: (v: boolean) => void }) {
  return (
    <label className={`opcion casilla-exhaustiva${marcada ? ' elegida' : ''}`}>
      <input type="checkbox" checked={marcada} onChange={(e) => cambiar(e.target.checked)} />
      <span>
        <strong>Investigación exhaustiva</strong>
        <span className="nota">
          Más búsquedas y más fuentes antes de escribir. Tarda y cuesta más; se decide ahora y no se cambia después.
        </span>
      </span>
    </label>
  )
}
