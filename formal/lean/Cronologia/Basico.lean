/-
  Cronologia.Basico — el modelo de la cronología de una novela y sus invariantes.

  Esta parte se escribe a mano una vez y no cambia. Lo que se genera por novela es
  `Cronologia.Generado`, que solo contiene datos: la lista de personas, la de lugares
  y la de eventos volcadas desde las tablas `cronologia_*` y `mundo_entidad` del
  fichero SQLite de esa novela.

  La separación importa. Si el generador emitiera también los teoremas, cada novela
  traería su propia definición de "coherente" y la palabra dejaría de significar algo.
  Generando solo datos, lo que se verifica es siempre lo mismo contra material distinto.
-/

namespace Cronologia

/-- Un instante, en días desde una época arbitraria pero común a toda la novela.

    Se usa un entero y no una fecha estructurada a propósito: la aritmética de
    calendario es una fuente de fallos que no aporta nada a lo que aquí se comprueba,
    y el generador ya sabe convertir. Puede ser negativo (antes de la época). -/
abbrev Momento := Int

/-- Identificadores. Son los mismos que las claves primarias de SQLite, de modo que
    un contraejemplo se puede seguir hasta la fila que lo produjo. -/
abbrev PersonaId := Nat
abbrev LugarId := Nat
abbrev EventoId := Nat
abbrev ObjetoId := Nat

/-- Una persona de la novela: histórica o inventada, da igual a estos efectos.

    `muerte` es opcional porque de muchos personajes inventados no se decide cuándo
    mueren, y de algunos históricos tampoco se sabe. Un `none` no es un hueco que
    rellenar: es la afirmación de que no hay restricción por ese lado. -/
structure Persona where
  id : PersonaId
  nombre : String
  nacimiento : Momento
  muerte : Option Momento
  deriving Repr, DecidableEq

/-- Un objeto, término o concepto con existencia fechada: sale de `mundo_entidad`,
    con sus columnas `fecha_inicio` y `fecha_fin`. Es lo que sostiene el detector
    de anacronismos. -/
structure Objeto where
  id : ObjetoId
  nombre : String
  aparece : Momento
  desaparece : Option Momento
  deriving Repr, DecidableEq

/-- El origen de un evento. Se conservan mezclados en la misma lista, igual que en
    la tabla `cronologia_evento`, porque es justo en la mezcla donde aparecen las
    incoherencias que ningún validador semántico detecta: el personaje inventado
    que asiste a un acontecimiento histórico antes de que ocurra. -/
inductive Origen where
  | historico
  | narrativo
  deriving Repr, DecidableEq

/-- Un evento de la cronología: cuándo, dónde, quién estuvo y qué objetos aparecen. -/
structure Evento where
  id : EventoId
  clave : String
  momento : Momento
  lugar : LugarId
  participantes : List PersonaId
  objetos : List ObjetoId
  origen : Origen
  deriving Repr

/-- Todo lo que hace falta para juzgar una novela. -/
structure Novela where
  personas : List Persona
  objetos : List Objeto
  eventos : List Evento

namespace Novela

variable (n : Novela)

def persona? (p : PersonaId) : Option Persona :=
  n.personas.find? (·.id == p)

def objeto? (o : ObjetoId) : Option Objeto :=
  n.objetos.find? (·.id == o)

/-! ## Los cuatro invariantes

    Cada uno se enuncia como predicado decidible sobre la novela entera, de modo que
    `decide` los evalúa y el fallo señala el evento concreto. No se busca elegancia:
    se busca que un contraejemplo sea legible por quien no sabe Lean. -/

/-- **I1 · Nadie participa en un evento antes de nacer.**

    Es el invariante que justifica el resto del esfuerzo: es exactamente el error que
    un lector humano no comete al escribir un capítulo suelto, y que sí comete un
    sistema que escribe diez capítulos sin tener delante las fechas a la vez. -/
def participanteNacido (e : Evento) (p : PersonaId) : Bool :=
  match n.persona? p with
  | none => true          -- Persona desconocida: no hay nada que afirmar.
  | some q => q.nacimiento ≤ e.momento

def I1_NadieAntesDeNacer : Bool :=
  n.eventos.all fun e => e.participantes.all (n.participanteNacido e)

/-- **I2 · Nadie participa en un evento después de morir.**

    El gemelo del anterior, y no es redundante: los dos fallan por caminos distintos.
    El primero lo rompe una fecha de nacimiento mal elegida por el arquitecto; el
    segundo, un personaje histórico que el escritor mantiene vivo porque le venía bien
    para la escena. -/
def participanteVivo (e : Evento) (p : PersonaId) : Bool :=
  match n.persona? p with
  | none => true
  | some q => match q.muerte with
              | none => true      -- Sin fecha de muerte no hay restricción.
              | some m => e.momento ≤ m

def I2_NadieDespuesDeMorir : Bool :=
  n.eventos.all fun e => e.participantes.all (n.participanteVivo e)

/-- **I3 · Nadie está en dos lugares a la vez.**

    Dos eventos en el mismo momento, en lugares distintos, con una persona en ambos.

    Se compara por igualdad exacta de `momento` y no por solape de intervalos, y es
    una simplificación consciente: la granularidad de la cronología es el día, así que
    esto detecta "el mismo día en Cádiz y en Madrid" y no detecta "dos horas después
    a cuatrocientos kilómetros". Lo segundo exigiría modelar distancias y velocidades
    de época, que es un proyecto entero y no cabe en el presupuesto de este. Queda
    anotado como limitación, no como olvido. -/
def conflictoDeLugar (e f : Evento) : Bool :=
  e.id != f.id &&
  e.momento == f.momento &&
  e.lugar != f.lugar &&
  e.participantes.any (fun p => f.participantes.contains p)

def I3_NoEnDosLugares : Bool :=
  n.eventos.all fun e => n.eventos.all fun f => !(conflictoDeLugar e f)

/-- **I4 · Ningún objeto aparece antes de existir ni después de desaparecer.**

    Este es el que el dominio histórico regala. `mundo_entidad.fecha_inicio` dice
    cuándo empieza a existir un objeto, un término o un concepto, así que un catalejo
    en 1750 o un telégrafo eléctrico en 1805 son comprobables sin que nadie opine. -/
def objetoDisponible (e : Evento) (o : ObjetoId) : Bool :=
  match n.objeto? o with
  | none => true
  | some x => x.aparece ≤ e.momento &&
              (match x.desaparece with
               | none => true
               | some d => e.momento ≤ d)

def I4_SinAnacronismos : Bool :=
  n.eventos.all fun e => e.objetos.all (n.objetoDisponible e)

/-- La novela es coherente si cumple los cuatro.

    `PublishVersion` no publica si esto es `false`: el fallo vuelve al editor con el
    evento que lo produjo. Es la puerta G5, que no admite excepción. -/
def Coherente : Bool :=
  n.I1_NadieAntesDeNacer &&
  n.I2_NadieDespuesDeMorir &&
  n.I3_NoEnDosLugares &&
  n.I4_SinAnacronismos

/-! ## Diagnóstico

    Que el invariante sea `false` no sirve de nada por sí solo: el editor necesita
    saber qué evento arreglar. Estas funciones devuelven los culpables. -/

def eventosConNoNacido : List Evento :=
  n.eventos.filter fun e => !(e.participantes.all (n.participanteNacido e))

def eventosConMuerto : List Evento :=
  n.eventos.filter fun e => !(e.participantes.all (n.participanteVivo e))

def eventosUbicuos : List Evento :=
  n.eventos.filter fun e => n.eventos.any fun f => conflictoDeLugar e f

def eventosAnacronicos : List Evento :=
  n.eventos.filter fun e => !(e.objetos.all (n.objetoDisponible e))

end Novela

end Cronologia
