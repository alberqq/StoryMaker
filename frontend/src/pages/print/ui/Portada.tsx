import type { Paratexto } from '@/shared/api'

const conMotivoDe = (ocasion: string) =>
  /\bsu\b/.test(ocasion) ? `con motivo de ${ocasion}` : `con motivo de su ${ocasion}`

/** Portada con dedicatoria, y la nota del autor si hay Licencias declaradas. */
export function Portada({ paratexto }: { paratexto: Paratexto }) {
  return (
    <>
      <section className="portada" data-render="portada">
        <h1 className="titulo-obra">{paratexto.titulo}</h1>
        {paratexto.homenajeado && (
          <div className="dedicatoria">
            <p>Para {paratexto.homenajeado}</p>
            {paratexto.ocasion && <p>{conMotivoDe(paratexto.ocasion)}</p>}
          </div>
        )}
      </section>
      {paratexto.licencias.length > 0 && (
        <section className="nota-del-autor">
          <h2>Nota del autor</h2>
          <p>
            Esta novela es ficción sobre un fondo histórico. Estas son las libertades que se ha
            tomado con los hechos:
          </p>
          <ul>
            {paratexto.licencias.map((l, i) => (
              <li key={i}>
                {l.alteracion}. <span className="nota">{l.justificacion}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  )
}
