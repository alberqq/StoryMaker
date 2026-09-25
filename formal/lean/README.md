# Validador formal de la historia — Lean 4

Comprueba que **la cronología de una novela concreta es coherente**: que nadie participa en un evento antes de nacer o después de morir, que nadie está en dos sitios a la vez, y que ningún objeto aparece antes de existir.

No verifica el arnés —eso es [`formal/tla/`](../tla/)— sino su producto. Son dos preguntas distintas y ninguna de las dos responde a la otra.

## La forma del proyecto

| Fichero | Qué es | Quién lo escribe |
|---|---|---|
| [`Cronologia/Basico.lean`](Cronologia/Basico.lean) | El modelo y los cuatro invariantes | A mano, una vez |
| [`Cronologia/Generado.lean`](Cronologia/Generado.lean) | Los datos de **una** novela. El del repositorio es un ejemplo | El generador, en cada verificación, sobre una copia temporal del proyecto |
| [`Verificar.lean`](Verificar.lean) | El ejecutable que el arnés llama | A mano |

**El generador emite datos y nada más.** Si emitiera también los teoremas, cada novela traería su propia definición de «coherente» y la palabra dejaría de significar nada: se podría hacer pasar cualquier cosa generando el invariante que le convenga. Generando solo datos, lo que se verifica es siempre lo mismo contra material distinto.

## El contrato con el arnés

```bash
lake build
lake exe verificar        # 0 = coherente · 1 = incoherente, con los eventos culpables
```

**El código de salida es el contrato, no la salida de texto.** El nodo del grafo lee un entero y decide la arista; si tuviera que parsear prosa, un cambio de redacción aquí rompería la validación allí sin que nada se quejara.

Si sale 1, la versión **no se publica** y el fallo vuelve al editor con los eventos concretos. Es la puerta G5, que no admite excepción.

> **Estado en este entorno.** Construido y en uso. Con elan y el toolchain que fija `lean-toolchain` (v4.15.0), `lake build` compila los diez objetivos y `lake exe verificar` sale con 1 sobre el ejemplo del repositorio, que viola tres invariantes a propósito. Con `lake` en el PATH el arnés verifica con Lean en los tres puntos de §11c de la arquitectura; sin él, con la misma evaluación en Python.

## Los cuatro invariantes

| | Enunciado | Qué lo rompe en la práctica |
|---|---|---|
| **I1** | Nadie participa en un evento antes de nacer | Una fecha de nacimiento que el arquitecto eligió sin cruzarla con el período |
| **I2** | Nadie participa después de morir | Un personaje histórico que el escritor mantiene vivo porque le venía bien para la escena |
| **I3** | Nadie está en dos lugares a la vez | Dos capítulos escritos por separado que sitúan a alguien el mismo día en dos sitios |
| **I4** | Ningún objeto aparece antes de existir | Un anacronismo material: un telégrafo eléctrico en 1805 |

`Option` se usa con intención en dos sitios. `Persona.muerte = none` **no** significa que el personaje sea inmortal: significa que no hay restricción por ese lado, que es el caso de casi todo personaje inventado. Igual con `Objeto.desaparece`.

### Una limitación declarada, no olvidada

**I3 compara igualdad exacta de momento, no solape de intervalos.** La granularidad de `cronologia_evento.momento` es el día, así que detecta «el mismo día en Cádiz y en Madrid» y no detecta «dos horas después, a cuatrocientos kilómetros». Modelar lo segundo exigiría distancias y velocidades de transporte de época, que es un proyecto entero.

Queda escrito aquí porque una limitación que no se declara se lee como una garantía.

## El caso que solo Lean ve

### El caso real: `metro`

`metro` es una novela generada y publicada por el arnés: cinco capítulos en el Madrid de 1917 a 1919, con una telegrafista como protagonista y la homenajeada del encargo como ese personaje. El canon guarda para ella **su fecha de nacimiento real, de 1967**, porque es un personaje *histórico ficcionalizado* y el arquitecto la copió del brief. La novela la sitúa cincuenta años antes.

Lean, ejecutado sobre la base de la novela tal como quedó publicada, lo rechaza dos veces:

- sobre la **cronología de la prosa**, I1 (`I1_NadieAntesDeNacer`) cae en los veintiséis eventos narrativos en que participa la homenajeada, del capítulo 1 al 4;
- sobre la **cronología de la escaleta**, I1 cae en las nueve escenas que la ponen en escena.

**Qué vieron los demás cuando la novela se generó:**

- El gate de Plotting enseñó seis avisos de `cronologia_escaleta`, que es la evaluación en Python de los mismos invariantes y solo avisa en ese punto. El Autor aprobó la escaleta.
- Los **validadores deterministas** no lo vieron. `nombres_exactos` comprueba cómo se escribe un nombre, no cuándo vive su dueño, y ninguno de los once cruza la fecha de una escena con la de nacimiento de sus personajes.
- El **juez** no lo vio. Encontró que la edad de la homenajeada cambiaba diez años entre el capítulo 1 y el 5, que es una contradicción *interna* de la prosa, pero no que el canon la hiciera nacer medio siglo después de todo lo que cuenta la novela: para eso tendría que tener delante una fecha que está en la biblia y no en el texto.
- La versión 1 **se publicó**.

**Con Lean en la publicación, no se habría publicado.** La cronología completa corre ahora dentro de `PublishVersion` antes de escribir la versión, y con esa base rechaza la candidata y la devuelve al gate de Writing citando los capítulos 1 a 4. Es el caso que el requisito pide: una incoherencia real, en una novela real, que el método formal detecta y los otros validadores dejaron pasar.

En la misma pasada, `lozoya` dio otro caso, más pequeño: en su escaleta un personaje está el mismo día de junio de 1858 en dos escenarios distintos (I3). Ahí Python lo vio igual, y la prosa lo resolvió: sobre la cronología de lo escrito, Lean aprueba.

### El ejemplo del repositorio

`Generado.lean` lleva un ejemplo construido a mano para que el ejecutable tenga material sin una novela delante. Federico Gravina, que murió el 9 de marzo de 1806, aparece en un desenlace situado en 1808 —un epílogo «años después de la batalla»—, y el ejemplo incluye además una violación de **I1** —el homenajeado nace en 1831 y presencia Trafalgar en 1805— y una de **I4** —un telégrafo eléctrico en 1805—.

El ejemplo enseña lo mismo que `metro`, y por qué ocurre. Lean no lee la novela: lee dos listas y compara enteros. `I2_NadieDespuesDeMorir` recorre los participantes de cada evento y pregunta si `e.momento ≤ q.muerte`. La comprobación no depende de la longitud de la novela, ni de cuánto contexto quepa en un prompt, ni de que alguien se acuerde.

Ahí está el argumento entero para tener un método formal en un sistema de generación larga: **hay una clase de error que no es de calidad sino de consistencia global**, y la consistencia global es exactamente lo que se pierde cuando un texto se escribe por partes. Un juez con toda la novela delante lo vería; ningún juez tiene toda la novela delante.

El arnés no escribe sobre este fichero: cada verificación trabaja en una copia temporal del proyecto (arq. §11c), así que el ejemplo versionado sigue siendo el que es.

## Dónde mirar

- [`architecture.md` §11c](../../docs/architecture.md#11-validación) y el esquema de `cronologia_*` en [`diagramas.md`](../../docs/diagramas.md#esquema-sqlite)
- El explainer: [`docs/explainers/verificacion-formal.md`](../../docs/explainers/verificacion-formal.md)
