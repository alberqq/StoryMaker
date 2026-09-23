-------------------------------- MODULE harness --------------------------------
(***************************************************************************)
(* Especificación del comportamiento del arnés de StoryMaker.              *)
(*                                                                         *)
(* Modela las seis fases —configuración, investigación, planificación,     *)
(* escritura, publicación y regeneración— incluidas la reanudación desde   *)
(* checkpoint y la regeneración por cambio del lector. No modela el        *)
(* contenido de la novela: modela cuándo el arnés puede avanzar, cuándo se *)
(* detiene a esperar al Autor y qué no puede ocurrir nunca.                *)
(*                                                                         *)
(* Si solo se modelara el bucle de generación, los invariantes             *)
(* interesantes quedarían fuera, porque viven precisamente en lo que se    *)
(* habría excluido: `ResumeIsExactlyOnce` vive en la reanudación y         *)
(* `PreviousVersionPreserved` vive en la regeneración.                     *)
(*                                                                         *)
(* Los nombres de los estados son los nombres de los nodos de LangGraph.   *)
(* La tabla de correspondencia del README no es una narración: es una      *)
(* lista de identidades, y hay una prueba que la comprueba comparando      *)
(* además el conjunto de aristas del StateGraph con la definición Aristas  *)
(* de este módulo.                                                         *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    NCapitulos,     \* Capítulos de la novela. El modelo pequeño usa 5.
    MaxIntentos,    \* Reintentos por capítulo. El modelo pequeño usa 2.
    GatesActivos,   \* TRUE en interactivo; FALSE en modo batch.
    MaxRechazosJuez \* Veces que el juez puede devolver la novela al gate.

ASSUME NCapitulos \in Nat /\ NCapitulos > 0
ASSUME MaxIntentos \in Nat
ASSUME GatesActivos \in BOOLEAN
ASSUME MaxRechazosJuez \in Nat

VARIABLES
    pc,                 \* El nodo en el que está la invocación.
    capitulo,           \* El capítulo que se está escribiendo.
    intentos,           \* Reintentos consumidos por el capítulo en curso.
    aprobados,          \* Conjunto de capítulos aprobados.
    validados,          \* Conjunto de capítulos que pasaron todos los validadores.
    versiones,          \* Secuencia de versiones publicadas. Append-only.
    huecos,             \* Huecos de micro-investigación que le quedan al arquitecto.
    sellado,            \* TRUE cuando el corpus quedó sellado al cerrar Plotting.
    regenerando,        \* TRUE mientras se rehacen capítulos por cambio del lector.
    rechazosJuez,       \* Veces que el juez ha devuelto la novela. Lo descubrió TLC:
                        \* sin tope, Judge y el gate se pasan la novela para siempre.
    publicoSinValidar   \* Variable de historia: TRUE si alguna publicación incluyó
                        \* un capítulo no validado. Ver NoPublishUnvalidated.

vars == <<pc, capitulo, intentos, aprobados, validados, versiones,
          huecos, sellado, regenerando, rechazosJuez, publicoSinValidar>>

(***************************************************************************)
(* Las transiciones, declaradas una sola vez.                              *)
(*                                                                         *)
(* De aquí se deriva el Next: ninguna acción puede mover el pc por una     *)
(* arista que no esté en este conjunto. Eso es lo que permite que la       *)
(* prueba de identidad compare cableado y no solo nombres, sin parsear el  *)
(* modelo, y garantiza que la relación que la prueba lee es exactamente    *)
(* la que TLC exploró. Si esta definición solo acompañara al modelo en vez *)
(* de gobernarlo, sería una tercera copia más que mantener a mano.         *)
(***************************************************************************)
Aristas ==
    {   \* Fase 1 · Intake
        <<"Configure", "AwaitApproval">>,
        <<"AwaitApproval", "Research">>,
        <<"AwaitApproval", "Configure">>,
        <<"AwaitApproval", "Fail">>,

        \* Fase 2 · Investigation
        <<"Research", "VerifyCorpus">>,
        <<"VerifyCorpus", "AwaitApproval2">>,
        <<"AwaitApproval2", "Plan">>,
        <<"AwaitApproval2", "Research">>,

        \* Fase 3 · Plotting
        <<"Plan", "FillGap">>,
        <<"FillGap", "Plan">>,
        <<"Plan", "AwaitApproval3">>,
        <<"AwaitApproval3", "SealCorpus">>,
        <<"AwaitApproval3", "Plan">>,

        \* Fase 4 · Writing
        <<"SealCorpus", "WriteChapter">>,
        <<"WriteChapter", "Validate">>,
        <<"Validate", "Repair">>,
        <<"Validate", "Extract">>,
        <<"Extract", "Repair">>,
        <<"Repair", "Validate">>,
        <<"Validate", "Fail">>,
        <<"Extract", "Fail">>,
        <<"Extract", "ApproveChapter">>,
        <<"ApproveChapter", "Checkpoint">>,
        <<"Checkpoint", "WriteChapter">>,
        <<"Checkpoint", "AwaitApproval4">>,

        \* Fase 5 · Publication
        <<"AwaitApproval4", "Judge">>,
        <<"AwaitApproval4", "WriteChapter">>,
        <<"Judge", "PublishVersion">>,
        <<"Judge", "AwaitApproval4">>,
        <<"Judge", "Fail">>,
        <<"PublishVersion", "Idle">>,

        \* Fase 6 · Regeneration
        <<"Idle", "RequestChange">>,
        <<"RequestChange", "Invalidate">>,
        <<"Invalidate", "RegenerateAffected">>,
        <<"RegenerateAffected", "Validate">>,
        <<"Idle", "Branch">>
    }

Estados == {"Configure", "AwaitApproval", "Research", "VerifyCorpus",
            "AwaitApproval2", "Plan", "FillGap", "AwaitApproval3", "SealCorpus",
            "WriteChapter", "Validate", "Extract", "Repair", "ApproveChapter",
            "Checkpoint", "AwaitApproval4", "Judge", "PublishVersion", "Idle",
            "RequestChange", "Invalidate", "RegenerateAffected", "Branch", "Fail"}

Terminales == {"Branch", "Fail"}

(***************************************************************************)
(* Mover el pc es siempre lo mismo: comprobar que la arista existe.        *)
(***************************************************************************)
Mueve(de, a) ==
    /\ pc = de
    /\ <<de, a>> \in Aristas
    /\ pc' = a

Capitulos == 1 .. NCapitulos

TypeOK ==
    /\ pc \in Estados
    /\ capitulo \in 1 .. (NCapitulos + 1)
    /\ intentos \in 0 .. MaxIntentos
    /\ aprobados \subseteq Capitulos
    /\ validados \subseteq Capitulos
    /\ versiones \in Seq(SUBSET Capitulos)
    /\ huecos \in Nat
    /\ sellado \in BOOLEAN
    /\ regenerando \in BOOLEAN
    /\ rechazosJuez \in 0 .. MaxRechazosJuez
    /\ publicoSinValidar \in BOOLEAN

Init ==
    /\ pc = "Configure"
    /\ capitulo = 1
    /\ intentos = 0
    /\ aprobados = {}
    /\ validados = {}
    /\ versiones = << >>
    /\ huecos = 2
    /\ sellado = FALSE
    /\ regenerando = FALSE
    /\ rechazosJuez = 0
    /\ publicoSinValidar = FALSE

(***************************************************************************)
(* Fase 1 · Intake                                                         *)
(***************************************************************************)
Configure ==
    /\ Mueve("Configure", "AwaitApproval")
    /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                   huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

(***************************************************************************)
(* El Autor. Se modela como entorno no determinista: en cada gate puede    *)
(* aprobar, pedir que se rehaga o abortar. En modo batch no hay gate y el  *)
(* arnés pasa de largo, que es lo que `gates.enabled = false` hace.        *)
(***************************************************************************)
Aprobar(de, a) ==
    /\ Mueve(de, a)
    /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                   huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

Rehacer(de, a) ==
    /\ GatesActivos
    /\ Mueve(de, a)
    /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                   huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

(***************************************************************************)
(* Rehacer desde el gate de Writing es un caso aparte, y lo descubrió TLC.  *)
(*                                                                         *)
(* Los otros tres gates rehacen una fase que todavía no ha producido        *)
(* capítulos, así que volver atrás no deja nada aprobado colgando. El de    *)
(* Writing sí: cuando el Autor pide rehacer, los N capítulos ya están       *)
(* escritos y aprobados, y la ejecución vuelve a `WriteChapter`.            *)
(*                                                                         *)
(* Modelado como `Rehacer` a secas, eso violaba `ResumeIsExactlyOnce`: la   *)
(* pasada inicial exige que los aprobados sean exactamente los anteriores   *)
(* al capítulo en curso, y tras el rehacer eran todos. La violación no era  *)
(* del invariante sino del modelo, porque §8 de la arquitectura dice que    *)
(* «rehacer, reanudar, ramificar y regenerar son la misma operación con     *)
(* distinto punto de entrada» — y regenerar marca `regenerando`.            *)
(*                                                                         *)
(* Así que rehacer Writing entra en modo regeneración, que es lo que era    *)
(* desde el principio. Ver el registro de contraejemplos del README.        *)
(***************************************************************************)
RehacerWriting ==
    /\ GatesActivos
    /\ Mueve("AwaitApproval4", "WriteChapter")
    /\ regenerando' = TRUE
    /\ intentos' = 0
    /\ UNCHANGED <<capitulo, aprobados, validados, versiones,
                   huecos, sellado, publicoSinValidar, rechazosJuez>>

Abortar ==
    /\ GatesActivos
    /\ Mueve("AwaitApproval", "Fail")
    /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                   huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

(***************************************************************************)
(* Fase 2 · Investigation                                                  *)
(*                                                                         *)
(* VerifyCorpus es un nodo y no una herramienta que el investigador decida *)
(* invocar: lo que un agente puede olvidarse de llamar no es una           *)
(* comprobación.                                                           *)
(***************************************************************************)
Research ==
    /\ Mueve("Research", "VerifyCorpus")
    /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                   huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

VerifyCorpus ==
    /\ Mueve("VerifyCorpus", "AwaitApproval2")
    /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                   huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

(***************************************************************************)
(* Fase 3 · Plotting                                                       *)
(*                                                                         *)
(* FillGap también es un nodo, y además por una razón práctica: el         *)
(* contador de huecos vive en el estado del grafo, que es el único sitio   *)
(* donde un tope se puede imponer de verdad.                               *)
(***************************************************************************)
Plan ==
    \/ /\ Mueve("Plan", "FillGap")
       /\ huecos > 0
       /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                      huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>
    \/ /\ Mueve("Plan", "AwaitApproval3")
       /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                      huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

FillGap ==
    /\ Mueve("FillGap", "Plan")
    /\ huecos > 0
    /\ huecos' = huecos - 1
    /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                   sellado, regenerando, publicoSinValidar, rechazosJuez>>

SealCorpus ==
    /\ Mueve("SealCorpus", "WriteChapter")
    /\ sellado' = TRUE
    /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                   huecos, regenerando, publicoSinValidar, rechazosJuez>>

(***************************************************************************)
(* Fase 4 · Writing                                                        *)
(*                                                                         *)
(* Extract es una acción propia y no un detalle interno de Validate, y eso *)
(* hace que Repair tenga dos aristas de entrada que comparten un único     *)
(* contador de intentos. Es exactamente la interacción por la que          *)
(* RetriesBounded existe.                                                  *)
(***************************************************************************)
WriteChapter ==
    /\ Mueve("WriteChapter", "Validate")
    /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                   huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

Validate ==
    \/ \* Pasada determinista limpia.
       /\ Mueve("Validate", "Extract")
       /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                      huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>
    \/ \* Incidencias, y quedan reintentos.
       /\ Mueve("Validate", "Repair")
       /\ intentos < MaxIntentos
       /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                      huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>
    \/ \* Reintentos agotados.
       /\ Mueve("Validate", "Fail")
       /\ intentos >= MaxIntentos
       /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                      huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

Extract ==
    \/ \* Sin incidencias bloqueantes: el capítulo queda validado.
       /\ Mueve("Extract", "ApproveChapter")
       /\ validados' = validados \cup {capitulo}
       /\ UNCHANGED <<capitulo, intentos, aprobados, versiones,
                      huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>
    \/ \* Incidencias bloqueantes, y quedan reintentos.
       /\ Mueve("Extract", "Repair")
       /\ intentos < MaxIntentos
       /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                      huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>
    \/ \* Reintentos agotados.
       /\ Mueve("Extract", "Fail")
       /\ intentos >= MaxIntentos
       /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                      huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

Repair ==
    /\ Mueve("Repair", "Validate")
    /\ intentos < MaxIntentos
    /\ intentos' = intentos + 1
    /\ UNCHANGED <<capitulo, aprobados, validados, versiones,
                   huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

ApproveChapter ==
    /\ Mueve("ApproveChapter", "Checkpoint")
    /\ aprobados' = aprobados \cup {capitulo}
    /\ UNCHANGED <<capitulo, intentos, validados, versiones,
                   huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

(***************************************************************************)
(* El checkpoint y el capítulo aprobado se escriben en la misma            *)
(* transacción. No existe el instante en que el grafo cree que el capítulo *)
(* está hecho y la biblia no lo tenga: por eso ApproveChapter y Checkpoint *)
(* son consecutivos y nada puede colarse entre ellos.                      *)
(***************************************************************************)
Checkpoint ==
    \/ /\ Mueve("Checkpoint", "WriteChapter")
       /\ capitulo < NCapitulos
       /\ ~regenerando
       /\ capitulo' = capitulo + 1
       /\ intentos' = 0
       /\ UNCHANGED <<aprobados, validados, versiones, huecos, sellado,
                      regenerando, publicoSinValidar, rechazosJuez>>
    \/ /\ Mueve("Checkpoint", "AwaitApproval4")
       /\ \/ capitulo = NCapitulos
          \/ regenerando
       /\ intentos' = 0
       /\ regenerando' = FALSE
       /\ UNCHANGED <<capitulo, aprobados, validados, versiones, huecos,
                      sellado, publicoSinValidar, rechazosJuez>>

(***************************************************************************)
(* Fase 5 · Publication                                                    *)
(*                                                                         *)
(* PublishVersion no lleva guarda de validación a propósito. Si la         *)
(* llevara, NoPublishUnvalidated sería una tautología: comprobaría la      *)
(* guarda que acabamos de escribir en lugar de comprobar el grafo. Sin     *)
(* ella, TLC explora si existe algún camino que llegue a publicar con un   *)
(* capítulo sin validar, que es la pregunta que el invariante hace.        *)
(***************************************************************************)
(***************************************************************************)
(* Los rechazos del juez están acotados, y el tope lo pidió TLC.           *)
(*                                                                         *)
(* Sin él, `Judge --> AwaitApproval4 --> Judge` es un ciclo que TLC        *)
(* recorre indefinidamente: el Autor aprueba cada vez —la equidad débil se *)
(* lo garantiza— y el juez vuelve a rechazar. `Termina` era falsa, y no    *)
(* por un defecto del modelo: nada en el sistema acotaba ese bucle,        *)
(* mientras que `intentos` y `huecos` sí lo estaban. Era el único tope que *)
(* faltaba, y ninguna lectura del documento lo había echado en falta.      *)
(***************************************************************************)
Judge ==
    \/ /\ Mueve("Judge", "PublishVersion")
       /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                      huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>
    \/ \* Umbral no superado, y quedan rechazos: vuelve al gate de Writing.
       /\ Mueve("Judge", "AwaitApproval4")
       /\ rechazosJuez < MaxRechazosJuez
       /\ rechazosJuez' = rechazosJuez + 1
       /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                      huecos, sellado, regenerando, publicoSinValidar>>
    \/ \* Rechazos agotados: se detiene e informa, como con los reintentos.
       /\ Mueve("Judge", "Fail")
       /\ rechazosJuez >= MaxRechazosJuez
       /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                      huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

PublishVersion ==
    /\ Mueve("PublishVersion", "Idle")
    /\ versiones' = Append(versiones, aprobados)
    /\ publicoSinValidar' = (publicoSinValidar \/ (aprobados \ validados # {}))
    /\ UNCHANGED <<capitulo, intentos, aprobados, validados, huecos,
                   sellado, regenerando, rechazosJuez>>

(***************************************************************************)
(* Fase 6 · Regeneration                                                   *)
(*                                                                         *)
(* Rehacer, reanudar, ramificar y regenerar son la misma operación con     *)
(* distinto punto de entrada. Regenerar no toca las versiones ya           *)
(* publicadas: escribe capítulos nuevos y publica una versión nueva, de    *)
(* modo que conservar la anterior es una propiedad de la estructura y no   *)
(* una disciplina que alguien deba recordar.                               *)
(***************************************************************************)
RequestChange ==
    /\ Mueve("RequestChange", "Invalidate")
    /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                   huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

IdleRequest ==
    /\ Mueve("Idle", "RequestChange")
    /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                   huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

(***************************************************************************)
(* Se invalidan los capítulos que usan el hecho cambiado, que la tabla de  *)
(* hechos sabe cuáles son. Aquí se modela como una elección no             *)
(* determinista de un capítulo afectado: lo que importa al modelo no es    *)
(* cuál, sino que deja de estar validado hasta que se reescriba.           *)
(***************************************************************************)
Invalidate ==
    /\ Mueve("Invalidate", "RegenerateAffected")
    /\ \E c \in aprobados :
        /\ capitulo' = c
        /\ validados' = validados \ {c}
    /\ regenerando' = TRUE
    /\ intentos' = 0
    /\ UNCHANGED <<aprobados, versiones, huecos, sellado, publicoSinValidar, rechazosJuez>>

RegenerateAffected ==
    /\ Mueve("RegenerateAffected", "Validate")
    /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                   huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

Branch ==
    /\ Mueve("Idle", "Branch")
    /\ UNCHANGED <<capitulo, intentos, aprobados, validados, versiones,
                   huecos, sellado, regenerando, publicoSinValidar, rechazosJuez>>

(***************************************************************************)
(* Los gates, según el modo.                                               *)
(***************************************************************************)
GateIntake ==
    \/ Aprobar("AwaitApproval", "Research")
    \/ Rehacer("AwaitApproval", "Configure")
    \/ Abortar

GateInvestigation ==
    \/ Aprobar("AwaitApproval2", "Plan")
    \/ Rehacer("AwaitApproval2", "Research")

GatePlotting ==
    \/ Aprobar("AwaitApproval3", "SealCorpus")
    \/ Rehacer("AwaitApproval3", "Plan")

GateWriting ==
    \/ Aprobar("AwaitApproval4", "Judge")
    \/ RehacerWriting

(***************************************************************************)
(* Las aprobaciones, por separado, para poder exigirles equidad débil.     *)
(***************************************************************************)
AutorAprueba ==
    \/ Aprobar("AwaitApproval", "Research")
    \/ Aprobar("AwaitApproval2", "Plan")
    \/ Aprobar("AwaitApproval3", "SealCorpus")
    \/ Aprobar("AwaitApproval4", "Judge")

Terminado == pc \in Terminales /\ UNCHANGED vars

Next ==
    \/ Configure
    \/ GateIntake
    \/ Research
    \/ VerifyCorpus
    \/ GateInvestigation
    \/ Plan
    \/ FillGap
    \/ GatePlotting
    \/ SealCorpus
    \/ WriteChapter
    \/ Validate
    \/ Extract
    \/ Repair
    \/ ApproveChapter
    \/ Checkpoint
    \/ GateWriting
    \/ Judge
    \/ PublishVersion
    \/ IdleRequest
    \/ RequestChange
    \/ Invalidate
    \/ RegenerateAffected
    \/ Branch
    \/ Terminado

(***************************************************************************)
(* La hipótesis de equidad sobre el Autor, y una corrección que hizo TLC.  *)
(*                                                                         *)
(* Que haga falta una hipótesis no es un truco para esquivar el requisito  *)
(* de liveness: es la forma correcta de especificar un sistema con         *)
(* intervención humana bloqueante. Sin ella la propiedad es sencillamente  *)
(* falsa —el Autor puede no contestar nunca— y no hay diseño que la salve. *)
(*                                                                         *)
(* Lo que TLC corrigió es **cuál** hipótesis. §11d de la arquitectura decía *)
(* «equidad débil», y la equidad débil NO BASTA: solo obliga a una acción  *)
(* que esté *continuamente* habilitada, y `Aprobar` en el gate de Writing  *)
(* no lo está — se deshabilita en cuanto el Autor pide rehacer y el bucle  *)
(* de escritura arranca. TLC encontró la traza: gate, rehacer, escribir    *)
(* los capítulos, gate, rehacer, indefinidamente.                          *)
(*                                                                         *)
(* La hipótesis correcta es la **equidad fuerte**: si la aprobación está   *)
(* habilitada infinitas veces, acaba ocurriendo. En castellano llano: el   *)
(* Autor puede pedir que se rehaga tantas veces como quiera, pero no       *)
(* infinitas. Que la distinción importe aquí y no en los otros tres gates  *)
(* es justamente lo que un lector humano no ve.                            *)
(***************************************************************************)
Spec == Init /\ [][Next]_vars /\ WF_vars(Next) /\ SF_vars(AutorAprueba)

(***************************************************************************)
(* Invariantes de seguridad                                                *)
(***************************************************************************)

\* Nunca se publica una versión que contenga un capítulo que no pasó todos los
\* validadores. Se comprueba sobre una variable de historia y no sobre una guarda,
\* para que el invariante interrogue al grafo y no a sí mismo.
NoPublishUnvalidated == publicoSinValidar = FALSE

\* La reanudación desde checkpoint no duplica ni pierde capítulos. Durante la
\* pasada inicial de escritura, el conjunto de aprobados es exactamente el de los
\* capítulos anteriores al que se está escribiendo: ni un hueco (pérdida) ni un
\* capítulo repetido (duplicación).
EscribiendoPasadaInicial ==
    /\ ~regenerando
    /\ pc \in {"WriteChapter", "Validate", "Extract", "Repair"}

ResumeIsExactlyOnce ==
    EscribiendoPasadaInicial => aprobados = 1 .. (capitulo - 1)

\* El número de reintentos por capítulo nunca supera el límite, ni siquiera
\* entrando en Repair por sus dos aristas.
RetriesBounded == intentos <= MaxIntentos

\* El corpus no se escribe después de sellarse: durante Writing nadie añade
\* hechos históricos, solo ancla a los existentes o declara una Licencia.
CorpusSelladoNoSeToca ==
    sellado => pc \notin {"Research", "FillGap"}

(***************************************************************************)
(* Propiedades temporales                                                  *)
(***************************************************************************)

\* Tras una regeneración, la versión anterior sigue siendo íntegramente
\* recuperable: la secuencia de versiones es append-only, y ningún elemento ya
\* publicado cambia nunca. Es una propiedad de acción, no de estado.
PreviousVersionPreserved ==
    [][ \A i \in 1 .. Len(versiones) :
            /\ i \in 1 .. Len(versiones')
            /\ versiones'[i] = versiones[i] ]_vars

\* Toda generación termina: publicando una versión, ramificando, o parando con
\* error. En batch la propiedad es directa; en interactivo vale bajo la equidad
\* débil que Spec declara sobre la respuesta del Autor.
Termina == <>(pc \in {"Idle", "Fail", "Branch"})

================================================================================
