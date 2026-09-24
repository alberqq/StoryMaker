import type { Paratexto } from '@/shared/api'

const conMotivoDe = (ocasion: string) =>
  /\bsu\b/.test(ocasion) ? `con motivo de ${ocasion}` : `con motivo de su ${ocasion}`

/**
 * La portada y la dedicatoria, cada una en su página, y la nota del autor si hay Licencias
 * declaradas. Las dos primeras van en la misma región `data-render="portada"`, que es lo que
 * `render_visual` comprueba: portada con dedicatoria.
 */
export function Portada({ paratexto }: { paratexto: Paratexto }) {
  return (
    <>
      <section className="portada" data-render="portada">
        <div className="pagina-portada">
          <span className="ornamento" aria-hidden="true">
            ❦
          </span>
          <h1 className="titulo-obra">{paratexto.titulo}</h1>
          <span className="filete" aria-hidden="true" />
          <p className="genero-obra">Novela</p>
        </div>
        {paratexto.homenajeado && (
          <div className="pagina-dedicatoria">
            <div className="dedicatoria">
              <p>Para {paratexto.homenajeado},</p>
              {paratexto.ocasion && <p>{conMotivoDe(paratexto.ocasion)}.</p>}
            </div>
          </div>
        )}
      </section>
      {paratexto.licencias.length > 0 && (
        <section className="nota-del-autor">
          <h2>Nota del autor</h2>
          <p>
            Esta novela es ficción sobre un fondo histórico. Sus personajes y sus escenas son invención, pero el
            mundo en que viven se ha documentado con cuidado. Estas son las libertades que se ha tomado con los hechos:
          </p>
          <ul>
            {paratexto.licencias.map((l, i) => (
              <li key={i}>
                <strong>{l.alteracion}.</strong> {l.justificacion}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  )
}
