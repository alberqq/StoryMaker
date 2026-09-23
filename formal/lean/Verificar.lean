/-
  El punto de entrada que el arnés invoca.

  Contrato con `commons/formal/`:
    - Código de salida 0  -> la cronología cumple los cuatro invariantes.
    - Código de salida 1  -> no los cumple; por stdout van los eventos culpables,
                             uno por línea, agrupados por invariante.

  El código de salida es el contrato, y no la salida de texto. El nodo del grafo lee
  un entero y decide la arista; si tuviera que parsear prosa, un cambio de redacción
  aquí rompería la validación allí sin que nada se quejara.
-/
import Cronologia.Basico
import Cronologia.Generado

open Cronologia

def informar (titulo : String) (eventos : List Evento) : IO Unit := do
  if eventos.isEmpty then
    pure ()
  else
    IO.println s!"✗ {titulo}"
    for e in eventos do
      IO.println s!"    evento {e.id} · {e.clave} · momento {e.momento} · lugar {e.lugar}"

def main : IO UInt32 := do
  let n := Cronologia.Generado.novela

  if n.Coherente then
    IO.println s!"✓ Cronología coherente: {n.eventos.length} eventos, {n.personas.length} personas."
    return 0

  IO.println "Cronología incoherente."
  informar "I1 · participa antes de nacer" n.eventosConNoNacido
  informar "I2 · participa después de morir" n.eventosConMuerto
  informar "I3 · en dos lugares a la vez" n.eventosUbicuos
  informar "I4 · objeto anacrónico" n.eventosAnacronicos
  return 1
