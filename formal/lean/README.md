# Validador formal de la historia — Lean 4

Comprueba que **la cronología de una novela concreta es coherente**: que nadie participa en un evento antes de nacer o después de morir, que nadie está en dos sitios a la vez, y que ningún objeto aparece antes de existir.

No verifica el arnés —eso es [`formal/tla/`](../tla/)— sino su producto. Son dos preguntas distintas y ninguna de las dos responde a la otra.

## La forma del proyecto

| Fichero | Qué es | Quién lo escribe |
|---|---|---|
| [`Cronologia/Basico.lean`](Cronologia/Basico.lean) | El modelo y los cuatro invariantes | A mano, una vez |
| [`Cronologia/Generado.lean`](Cronologia/Generado.lean) | Los datos de **una** novela | El generador, en cada invocación |
| [`Verificar.lean`](Verificar.lean) | El ejecutable que el arnés llama | A mano |

**El generador emite datos y nada más.** Si emitiera también los teoremas, cada novela traería su propia definición de «coherente» y la palabra dejaría de significar nada: se podría hacer pasar cualquier cosa generando el invariante que le convenga. Generando solo datos, lo que se verifica es siempre lo mismo contra material distinto.

## El contrato con el arnés

```bash
lake build
lake exe verificar        # 0 = coherente · 1 = incoherente, con los eventos culpables
```

**El código de salida es el contrato, no la salida de texto.** El nodo del grafo lee un entero y decide la arista; si tuviera que parsear prosa, un cambio de redacción aquí rompería la validación allí sin que nada se quejara.

Si sale 1, la versión **no se publica** y el fallo vuelve al editor con los eventos concretos. Es la puerta G5, que no admite excepción.

> **Estado en este entorno.** No construido. No hay `lake` ni `elan` en la máquina (`lake` → *command not found*), así que el proyecto está escrito pero **no compilado**. La garantía es de clase **A por inspección**, no por demostración. Lo dice fila por fila [`docs/requirements-audit.md`](../../docs/requirements-audit.md) (LEAN-01 a LEAN-04).

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

El requisito pide «un caso real detectado solo por Lean, **o** su justificación». Como el arnés no ha generado ninguna novela todavía, lo que sigue es la justificación, construida sobre el brief [`evals/briefs/03-incoherencia-temporal.yaml`](../../evals/briefs/03-incoherencia-temporal.yaml) y volcada en `Generado.lean` para que el ejecutable tenga material.

**El caso.** El brief pide que aparezca Federico Gravina, que murió el 9 de marzo de 1806, y fija un tono de «epílogo sereno, años después de la batalla». El arquitecto, razonablemente, sitúa el desenlace en 1808. Gravina es un personaje importante de la novela, así que aparece en el desenlace.

**Por qué no lo ve nadie más:**

- Los **validadores deterministas** no lo ven. `nombres_exactos` comprueba cómo se escribe «Gravina», no cuándo está vivo. `anacronismo_fechado` mira `mundo_entidad`, que cubre objetos, términos y conceptos — no el solape entre la vida de un personaje y la fecha de una escena. Ninguno de los once cruza dos tablas por su eje temporal.
- El **juez** no lo ve. Su rúbrica evalúa continuidad, tono, calidad narrativa y personalización, y el capítulo es impecable en las cuatro: Gravina habla como Gravina, la escena es coherente con la anterior, el tono es el pedido. Para detectarlo tendría que recordar una fecha de muerte y compararla con la fecha narrativa de esa escena, a cien mil tokens de distancia de donde se declaró.
- El **Autor** no lo ve, o no siempre. En el gate de Writing lee diez capítulos. Que el capítulo 9 transcurra en 1808 y que Gravina muriera en 1806 son dos datos ciertos que hay que tener a la vez en la cabeza, y el segundo está en la biblia, no en el texto.

**Por qué Lean sí.** Porque no lee la novela: lee dos listas y compara enteros. `I2_NadieDespuesDeMorir` recorre los participantes de cada evento y pregunta si `e.momento ≤ q.muerte`. La comprobación no depende de la longitud de la novela, ni de cuánto contexto quepa en un prompt, ni de que alguien se acuerde.

Ahí está el argumento entero para tener un método formal en un sistema de generación larga: **hay una clase de error que no es de calidad sino de consistencia global**, y la consistencia global es exactamente lo que se pierde cuando un texto se escribe por partes. Un juez con toda la novela delante lo vería; ningún juez tiene toda la novela delante.

El fichero `Generado.lean` del repositorio contiene además una violación de **I1** —el homenajeado nace en 1831 y presencia Trafalgar en 1805— y una de **I4** —un telégrafo eléctrico en 1805—, ambas tomadas del mismo brief. La de I1 debería cazarla antes el `@model_validator` de Intake, y que Lean la vea también es deliberado: es la red de seguridad de una comprobación que ocurre mucho antes.

## Dónde mirar

- [`architecture.md` §11c](../../docs/architecture.md#11-validación) y el esquema de `cronologia_*` en [`diagramas.md`](../../docs/diagramas.md#esquema-sqlite)
- El explainer: [`docs/explainers/verificacion-formal.md`](../../docs/explainers/verificacion-formal.md)
