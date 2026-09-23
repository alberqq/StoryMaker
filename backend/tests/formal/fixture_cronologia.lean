/-
  GENERADO AUTOMATICAMENTE por `commons/formal/generador.py` — no editar a mano.

  Vuelca las tablas `cronologia_evento`, `cronologia_participante`, `canon_personaje` y
  `mundo_entidad` del fichero SQLite de una novela. Se regenera entero en cada invocacion
  del validador, de modo que lo que hay aqui es siempre el estado actual de esa novela.

  Los momentos son dias desde 1800-01-01.
-/
import Cronologia.Basico

namespace Cronologia.Generado

open Cronologia

/-- Personas. `muerte = none` significa que no hay restriccion por ese lado. -/
def personas : List Persona := [
  { id := 1, nombre := "Federico Gravina",
    nacimiento := -15847, muerte := some 2258 },

  { id := 2, nombre := "Manuel Ferrer",
    nacimiento := -14549, muerte := none }
]

/-- Objetos con existencia fechada, volcados de `mundo_entidad`. -/
def objetos : List Objeto := [
  { id := 10, nombre := "catalejo", aparece := -70127, desaparece := none },
  { id := 11, nombre := "telegrafo electrico", aparece := 13514, desaparece := none }
]

/-- Eventos, historicos y narrativos mezclados a proposito en la misma lista. -/
def eventos : List Evento := [
  { id := 100, clave := "trafalgar", momento := 2119, lugar := 1,
    participantes := [1], objetos := [10],
    origen := Origen.historico },

  { id := 101, clave := "manuel-en-el-muelle", momento := 1926, lugar := 2,
    participantes := [2], objetos := [],
    origen := Origen.narrativo }
]

def novela : Novela :=
  { personas := personas, objetos := objetos, eventos := eventos }

end Cronologia.Generado
