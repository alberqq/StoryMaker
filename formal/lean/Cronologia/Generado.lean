/-
  GENERADO AUTOMÁTICAMENTE — no editar a mano.

  Lo emite `commons/formal/` volcando las tablas `cronologia_evento`,
  `cronologia_participante`, `canon_personaje` y `mundo_entidad` del fichero SQLite
  de una novela. Se regenera entero en cada invocación del validador.

  Este fichero, el que está en el repositorio, es el EJEMPLO que acompaña a la
  especificación: corresponde al brief de `evals/briefs/03-incoherencia-temporal.yaml`
  y contiene a propósito dos violaciones, para que el ejecutable tenga algo que
  detectar mientras el generador no exista. Ver el apartado "El caso que solo Lean
  ve" del README de este directorio.

  Los momentos son días desde 1800-01-01.
-/
import Cronologia.Basico

namespace Cronologia.Generado

open Cronologia

/-- Personas. `muerte = none` significa que no hay restricción por ese lado, no que
    el personaje sea inmortal. -/
def personas : List Persona := [
  -- Histórico. Gravina muere el 09-03-1806 de las heridas de Trafalgar.
  { id := 1, nombre := "Federico Gravina",
    nacimiento := -4988,   -- 1786-08-12 es posterior; valor de ejemplo
    muerte := some 2259 },  -- 1806-03-09

  -- El homenajeado, tal como lo declara el brief de eval-03: nace en 1831.
  { id := 2, nombre := "Cosme Aldecoa Barrenetxea",
    nacimiento := 11493,    -- 1831-06-20
    muerte := none },

  { id := 3, nombre := "Manuela Aldecoa",
    nacimiento := 1000,
    muerte := none }
]

/-- Objetos con existencia fechada, volcados de `mundo_entidad`. -/
def objetos : List Objeto := [
  { id := 10, nombre := "catalejo", aparece := -60000, desaparece := none },
  -- El telégrafo eléctrico no existe hasta los años treinta del XIX.
  { id := 11, nombre := "telégrafo eléctrico", aparece := 12419, desaparece := none },
  { id := 12, nombre := "carta náutica", aparece := -100000, desaparece := none }
]

/-- Eventos, históricos y narrativos mezclados a propósito en la misma lista. -/
def eventos : List Evento := [
  -- Histórico: Trafalgar, 21-10-1805.
  { id := 100, clave := "trafalgar", momento := 2120, lugar := 1,
    participantes := [1], objetos := [12], origen := Origen.historico },

  -- VIOLA I1: Cosme nace en 1831 (11493) y participa en 1805 (2120).
  { id := 101, clave := "cosme-ve-la-batalla", momento := 2120, lugar := 1,
    participantes := [2, 3], objetos := [10], origen := Origen.narrativo },

  -- VIOLA I4: telégrafo eléctrico en 1805.
  { id := 102, clave := "noticia-por-telegrafo", momento := 2125, lugar := 2,
    participantes := [3], objetos := [11], origen := Origen.narrativo },

  -- Correcto: Gravina en su lecho, antes de morir.
  { id := 103, clave := "gravina-convaleciente", momento := 2200, lugar := 2,
    participantes := [1], objetos := [], origen := Origen.historico }
]

def novela : Novela :=
  { personas := personas, objetos := objetos, eventos := eventos }

end Cronologia.Generado
