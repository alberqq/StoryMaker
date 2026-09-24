import type { GateDeNovela } from '@/shared/api'

/** La petición que abrió la Fase 6 y los candidatos que se calcularon al registrarla. */
export function Regeneracion({ peticion }: { peticion: NonNullable<GateDeNovela['peticion']> }) {
  return (
    <div className="pila">
      <blockquote className="cita-peticion">
        {peticion.texto}
        {peticion.fragmento && <span className="nota"> — sobre «{peticion.fragmento}»</span>}
      </blockquote>
      {peticion.candidatos.length === 0 ? (
        <p className="nota">La búsqueda no encontró ningún candidato. Puedes afinar la petición con la forma campo=valor.</p>
      ) : (
        <ol className="candidatos">
          {peticion.candidatos.map((c, i) => (
            <li key={i}>
              <strong>{c.descripcion}</strong>
              <p className="nota">
                Regenera {c.capitulos_a_regenerar.length ? `los capítulos ${c.capitulos_a_regenerar.join(', ')}` : 'ningún capítulo'}
                {c.capitulos_a_revisar.length > 0 && ` · revisa ${c.capitulos_a_revisar.join(', ')}`}
              </p>
              <p className="nota">{c.coste}</p>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
